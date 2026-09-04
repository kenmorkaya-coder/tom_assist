"""Explicit project-document chunking and local MiniLM embedding boundary."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import struct
import subprocess
import threading
import uuid

from gateway.semantic_chunks import (
    EMBEDDING_DIMENSION,
    EMBEDDING_VERSION,
    build_semantic_profile,
    profile_similarity,
)
from gateway.document_research import (
    DOCUMENT_RESEARCH_TRACE_VERSION,
    defined_term_reference_rows,
    entry_maps,
    evidence_unit_for_position,
    inventory_trace,
    parse_research_intent,
    redacted_ranked_chunk,
    redacted_relations,
    references_touching_span,
    safe_reference_record,
)
from gateway.declared_structure import MAX_DECLARED_STRUCTURE_SOURCE_CHARS
from gateway.structure_provider import isolated_worker_environment


DOCUMENT_CHUNKING_VERSION = "minilm-document-token-sentence-max188-overlap32/1.1"
SUPPORTED_DOCUMENT_CHUNKING_VERSIONS = frozenset({
    "minilm-document-token-sentence-max192-overlap32/1.0",
    DOCUMENT_CHUNKING_VERSION,
})
DOCUMENT_EMBEDDING_VERSION = EMBEDDING_VERSION
DOCUMENT_WORKER_PROTOCOL = "tom-assist-document-embedding/1.0"
DOCUMENT_PACKET_ADMISSION_VERSION = "minilm-document-hybrid-packet-admission/1.2"
MAX_DOCUMENT_SOURCE_CHARS = MAX_DECLARED_STRUCTURE_SOURCE_CHARS
MAX_DOCUMENT_CHUNKS = 4_096
MAX_DOCUMENT_PACKET_CANDIDATES = 64
MAX_DOCUMENT_PACKET_EXCERPT_CHARS = 680
PRESTART_PACKET_EXCERPT_CHARS = 320
DOCUMENT_MAX_CHUNK_TOKENS = 188
DOCUMENT_DENSE_RRF_WEIGHT = 0.50
DOCUMENT_LEXICAL_RRF_WEIGHT = 0.50
DOCUMENT_RRF_K = 60
DOCUMENT_TREE_SEMANTIC_COHORT = 64
ALLOWED_DOCUMENT_MEDIA_TYPES = frozenset({
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/html",
    "text/xml",
    "application/xml",
    "application/json",
})

_PRESTART_QUERY_ORIENTATION = re.compile(
    r"\b(?:before|prior|pre[- ]?start|prerequisites?|commenc\w*|start\w*)\b",
    re.IGNORECASE,
)
_PRESTART_QUERY_DUTY = re.compile(
    r"\b(?:must|required?|requirements?|conditions?|prerequisites?|do)\b",
    re.IGNORECASE,
)
_PRESTART_RELATIONS = (
    ("parties_commencement_condition", 1.00, re.compile(
        r"\b(?:rights\s+and\s+obligations|obligations)\b.{0,120}?"
        r"\b(?:will|must|shall)\s+not\s+commence\b.{0,160}?\bunless\s+and\s+until\b",
        re.IGNORECASE | re.DOTALL,
    )),
    ("noncommencement_until", 1.00, re.compile(
        r"\b(?:must|may|shall|will)\s+not\s+commence\b.{0,220}?\b(?:until|unless)\b",
        re.IGNORECASE | re.DOTALL,
    )),
    ("before_commencing", 1.00, re.compile(
        r"\bbefore\s+(?:commencing|starting|undertaking)\b.{0,220}",
        re.IGNORECASE | re.DOTALL,
    )),
    ("prior_to_commencing", 0.98, re.compile(
        r"\bprior\s+to\s+(?:the\s+)?(?:commencement|start|performance|"
        r"commencing|starting|undertaking|performing)\b.{0,220}",
        re.IGNORECASE | re.DOTALL,
    )),
    ("access_withheld_until", 0.97, re.compile(
        r"\bnot\s+obliged\s+to\s+give\b.{0,140}?\baccess\b.{0,100}?"
        r"\buntil\s+(?:the\s+)?(?:SCAW\s+)?Contractor\s+has\b.{0,220}",
        re.IGNORECASE | re.DOTALL,
    )),
    ("deadline_prerequisite", 0.94, re.compile(
        r"\bon\s+or\s+before\b.{0,100}?\b(?:deadline|commencement|start)\b.{0,220}",
        re.IGNORECASE | re.DOTALL,
    )),
    ("in_force_before_work", 0.94, re.compile(
        r"\b(?:in\s+force|completed|satisfied|approved)\b.{0,100}?\bbefore\b.{0,100}?"
        r"\b(?:work|activities|construction|access|commenc\w*)\b.{0,180}",
        re.IGNORECASE | re.DOTALL,
    )),
    ("condition_precedent_to_start", 0.92, re.compile(
        r"\bcondition\s+precedent\s+to\s+(?:the\s+)?"
        r"(?:commenc\w*|access|(?:[^.;]{0,80}\s)?obligations?|activities|work)\b.{0,220}",
        re.IGNORECASE | re.DOTALL,
    )),
    ("before_access_or_work", 0.90, re.compile(
        r"\bbefore\b.{0,160}?\b(?:access|work|commenc\w*|start\w*)\b.{0,220}",
        re.IGNORECASE | re.DOTALL,
    )),
    ("unless_until_commencement", 0.88, re.compile(
        r"\bunless\s+and\s+until\b.{0,220}?\b(?:commenc\w*|activities|work|access)\b",
        re.IGNORECASE | re.DOTALL,
    )),
)
_PRESTART_RELATION_PACKET_QUOTAS = (
    ("deadline_prerequisite", 4),
    ("parties_commencement_condition", 1),
    ("before_commencing", 2),
    ("noncommencement_until", 5),
    ("prior_to_commencing", 5),
    ("access_withheld_until", 1),
    ("in_force_before_work", 2),
    ("condition_precedent_to_start", 2),
    ("before_access_or_work", 3),
    ("unless_until_commencement", 1),
)
_LOCAL_CLAUSE_HEADING = re.compile(
    r"(?m)^[ \t]*(?P<identifier>[0-9]{1,3}(?:\.[0-9]{1,3}[A-Z]?)+)[ \t]+\S"
)
_OBLIGATION_ACTOR = re.compile(
    r"\b(?P<actor>the\s+SCAW\s+Contractor|SCAW\s+Contractor|the\s+Contractor|Contractor|"
    r"the\s+Principal|Principal|the\s+parties|parties|a\s+party|party)\b"
    r"[^.;]{0,120}?\b(?:must|may\s+not|shall|will\s+not|acknowledges?\s+that)\b",
    re.IGNORECASE,
)


def _actor_role(value):
    folded = " ".join(value.casefold().split())
    if "contractor" in folded:
        return "contractor"
    if "principal" in folded:
        return "principal"
    if "part" in folded:
        return "parties"
    return "unknown"


def _relation_actor(text, start, end):
    paragraph_start = text.rfind("\n\n", 0, start)
    paragraph_end = text.find("\n\n", start)
    window_start = max(0, paragraph_start + 2 if paragraph_start >= 0 else start - 280)
    window_end = min(
        len(text), paragraph_end if paragraph_end >= 0 else end + 280,
    )
    candidates = []
    for match in _OBLIGATION_ACTOR.finditer(text, window_start, window_end):
        absolute_start = window_start + match.start()
        absolute_end = window_start + match.end()
        distance = 0 if absolute_start <= start <= absolute_end else min(
            abs(start - absolute_start), abs(start - absolute_end),
        )
        candidates.append((distance, absolute_start, match.group("actor")))
    if not candidates:
        return "unknown", None
    _, _, source = min(candidates, key=lambda item: (item[0], -item[1], item[2]))
    return _actor_role(source), source


def prestart_requirement_query(text):
    """Identify a broad, directed pre-start duty question without inference."""
    return bool(
        isinstance(text, str)
        and _PRESTART_QUERY_ORIENTATION.search(text)
        and _PRESTART_QUERY_DUTY.search(text)
    )


def scan_prestart_relations(text):
    """Return every exact relation match and its deterministic disposition."""
    rows = []
    for relation, weight, pattern in _PRESTART_RELATIONS:
        for match in pattern.finditer(text):
            matched = match.group(0)
            # Completion and warranty duties answer a different temporal
            # question. They remain stored and retrievable for that question,
            # but cannot masquerade as pre-start evidence here.
            stops = [
                position for marker in (".", ";")
                if (position := text.find(marker, match.start(), match.end())) >= 0
            ]
            classification_span = text[
                match.start():(min(stops) + 1 if stops else match.end())
            ]
            excluded_post_start = bool(re.search(
                r"\bcondition\s+precedent\s+to\s+(?:substantial\s+)?completion\b|"
                r"\b(?:substantial|final)\s+completion|\bdefects?\s+correction\b|\bwarrant",
                classification_span,
                re.IGNORECASE,
            ))
            actor_role, actor_surface = _relation_actor(
                text, match.start(), match.end(),
            )
            if relation == "access_withheld_until":
                # The grammatical subject is the Principal, but the explicit
                # unsatisfied conditions are things the Contractor "has" to do.
                actor_role, actor_surface = "contractor", "Contractor"
            project_wide = bool(
                relation in {
                    "parties_commencement_condition", "deadline_prerequisite",
                    "access_withheld_until", "condition_precedent_to_start",
                }
                or re.search(
                    r"\bany\s+construction\s+work\s+under\s+(?:this|the)\s+(?:deed|contract)\b",
                    matched,
                    re.IGNORECASE,
                )
            )
            rows.append({
                "relation": relation,
                "weight": weight,
                "start": match.start(),
                "end": match.end(),
                "actor_role": actor_role,
                "actor_surface": actor_surface,
                "text_sha256": "sha256:" + hashlib.sha256(
                    matched.encode("utf-8")
                ).hexdigest(),
                "relation_key": relation + ":" + hashlib.sha256(
                    " ".join(matched.split())[:160].casefold().encode("utf-8")
                ).hexdigest(),
                "decision": "excluded" if excluded_post_start else "included",
                "reason_code": (
                    "EXCLUDED_POST_START_COMPLETION_WARRANTY"
                    if excluded_post_start else "INCLUDED_TEMPORAL_RELATION"
                ),
                "conditionality": (
                    "project_wide" if project_wide else "activity_conditional"
                ),
            })
    rows.sort(key=lambda row: (-row["weight"], row["start"], row["relation"]))
    strongest_by_start = {}
    for row in rows:
        if row["decision"] != "included":
            continue
        if row["start"] in strongest_by_start:
            row["decision"] = "excluded"
            row["reason_code"] = "EXCLUDED_WEAKER_RELATION_AT_SAME_START"
        else:
            strongest_by_start[row["start"]] = row
    return sorted(rows, key=lambda row: (row["start"], -row["weight"], row["relation"]))


def prestart_relation_details(text):
    """Return exact authored pre-start relations, never guessed labels."""
    return [row for row in scan_prestart_relations(text) if row["decision"] == "included"]


def _prestart_packet_order(ranked):
    """Diversify an exhaustive pre-start packet across exact relation forms."""
    selected = []
    selected_ids = set()
    relation_hashes = set()

    def admit(row):
        relations = row["prestart_relations"]
        identity = (
            f"{row['document_id']}:clause:{row['matched_clause_identifier']}"
            if row.get("matched_clause_identifier") else
            f"{row['document_id']}:{row['start'] + relations[0]['start']}"
            if relations else row["text_sha256"]
        )
        if row["id"] in selected_ids or identity in relation_hashes:
            return False
        selected.append(row)
        selected_ids.add(row["id"])
        relation_hashes.add(identity)
        return True

    for relation, quota in _PRESTART_RELATION_PACKET_QUOTAS:
        used = 0
        for row in ranked:
            if not any(item["relation"] == relation for item in row["prestart_relations"]):
                continue
            if admit(row):
                used += 1
                if used >= quota:
                    break
    for row in ranked:
        if row["prestart_relations"]:
            admit(row)
    return selected


def _apply_query_relation_filters(scan, query_text):
    """Apply only explicit actor orientation and retain every disposition."""
    contractor_directed = bool(re.search(r"\bcontractor\b", query_text, re.IGNORECASE))
    for row in scan:
        if row["decision"] != "included":
            continue
        if contractor_directed and row["actor_role"] not in {
            "contractor", "parties", "unknown",
        }:
            row["decision"] = "excluded"
            row["reason_code"] = "EXCLUDED_ACTOR_PRINCIPAL"
    return [row for row in scan if row["decision"] == "included"]


def _explicit_contractor_support(source, unit, text, relations):
    """Resolve actor orientation from the unit, then its exact authored parents."""
    explicit_roles = {
        str(row.get("actor_role") or "unknown") for row in relations
        if row.get("actor_role") != "unknown"
    }
    if explicit_roles & {"contractor", "parties"}:
        return True, {"kind": "relation_actor", "roles": sorted(explicit_roles)}
    if "principal" in explicit_roles:
        return False, {"kind": "relation_actor", "roles": sorted(explicit_roles)}

    own_matches = list(_OBLIGATION_ACTOR.finditer(text))
    if own_matches:
        role = _actor_role(own_matches[-1].group("actor"))
        return role == "contractor", {
            "kind": "same_authored_unit", "role": role,
            "entry_id": str(unit.get("entry_id") or ""),
        }

    structure = source.get("declared_structure") or {}
    by_id, _ = entry_maps(structure)
    current = by_id.get(str(unit.get("entry_id") or ""))
    child_start = int(unit["start"])
    visited = set()
    while isinstance(current, dict):
        parent_id = str(current.get("parent_entry_id") or "")
        if not parent_id or parent_id in visited:
            break
        visited.add(parent_id)
        parent = by_id.get(parent_id)
        if not isinstance(parent, dict):
            break
        parent_start = int(parent["span"]["start"])
        prefix = str(source["content"])[max(parent_start, child_start - 1_200):child_start]
        matches = list(_OBLIGATION_ACTOR.finditer(prefix))
        if matches:
            role = _actor_role(matches[-1].group("actor"))
            return role == "contractor", {
                "kind": "authored_parent", "role": role,
                "entry_id": parent_id,
            }
        current = parent
        child_start = parent_start
    return False, {"kind": "none", "role": "unknown"}


def _materialize_evidence_unit(row, document_sources, *, linked_from=None):
    source = document_sources.get(str(row["document_id"]))
    relations = row.get("prestart_relations") or []
    if source is None or not relations:
        return None, "MISSING_DOCUMENT_SOURCE_OR_RELATION"
    absolute_position = int(row["start"]) + int(relations[0]["start"])
    unit = evidence_unit_for_position(source, absolute_position)
    if unit is None:
        unit = {
            "entry_id": "",
            "identifier": str(row.get("matched_clause_identifier") or "unresolved"),
            "kind": "chunk_fallback",
            "start": int(row["start"]),
            "end": int(row["end"]),
            "char_count": int(row["end"]) - int(row["start"]),
            "oversize": False,
        }
        decision = "CHUNK_FALLBACK_NO_AUTHORED_UNIT"
    else:
        decision = "EXPANDED_TO_AUTHORED_COMPOSITE_UNIT"
    result = dict(row)
    result["_origin_candidate_id"] = row["id"]
    if unit["entry_id"]:
        result["id"] = f"{row['document_id']}:unit:{unit['entry_id']}"
    result["matched_clause_identifier"] = unit["identifier"]
    result["_evidence_unit"] = unit
    result["_linked_from"] = linked_from
    result["_expansion_decision"] = decision
    return result, decision


def _ranked_row_at_position(ranked, document_id, position):
    rows = [
        row for row in ranked
        if row["document_id"] == document_id
        and int(row["start"]) <= position < int(row["end"])
    ]
    return max(rows, key=lambda row: (row["rrf_score"], -row["chunk_index"]), default=None)


def _expanded_prestart_packet_rows(ranked, document_sources, query_text):
    """Expand direct hits and one-hop declared links into authored units."""
    direct = _prestart_packet_order(ranked)
    expanded = []
    expansion_trace = []
    dedup_trace = []
    link_trace = []
    authored_unit_trace = []
    missing_sources = []
    seen = {}
    globally_addressable_identifiers = set()
    for source in document_sources.values():
        _, identifiers = entry_maps(source.get("declared_structure") or {})
        globally_addressable_identifiers.update(identifiers)

    def admit(row, *, linked_from=None):
        materialized, decision = _materialize_evidence_unit(
            row, document_sources, linked_from=linked_from,
        )
        if materialized is None:
            expansion_trace.append({
                "candidate_id": row["id"], "decision": decision,
            })
            return None
        unit = materialized["_evidence_unit"]
        unit_text = str(document_sources[materialized["document_id"]]["content"])[
            int(unit["start"]):int(unit["end"])
        ]
        normalized_unit = " ".join(unit_text.split()).casefold()
        unit_content_sha256 = "sha256:" + hashlib.sha256(
            normalized_unit.encode("utf-8")
        ).hexdigest()
        materialized["_unit_content_sha256"] = unit_content_sha256
        actor_supported, actor_support = _explicit_contractor_support(
            document_sources[materialized["document_id"]],
            unit,
            unit_text,
            materialized.get("prestart_relations") or [],
        )
        materialized["_actor_support"] = actor_support
        if (
            re.search(r"\bcontractor\b", query_text, re.IGNORECASE)
            and not actor_supported
        ):
            expansion_trace.append({
                "candidate_id": materialized["id"],
                "document_id": materialized["document_id"],
                "clause_identifier": unit["identifier"],
                "unit_start": unit["start"],
                "unit_end": unit["end"],
                "unit_content_sha256": unit_content_sha256,
                "linked_from": linked_from,
                "actor_support": actor_support,
                "decision": "EXCLUDED_NO_EXPLICIT_CONTRACTOR_DUTY",
            })
            return None
        identity = ("normalized_authored_unit", unit_content_sha256)
        if identity in seen:
            dedup_trace.append({
                "candidate_id": materialized["id"],
                "kept_candidate_id": seen[identity]["id"],
                "document_id": materialized["document_id"],
                "clause_identifier": unit["identifier"],
                "unit_start": unit["start"],
                "unit_end": unit["end"],
                "unit_content_sha256": unit_content_sha256,
                "reason_code": "DEDUP_SAME_NORMALIZED_AUTHORED_UNIT",
            })
            return seen[identity]
        seen[identity] = materialized
        expanded.append(materialized)
        expansion_trace.append({
            "candidate_id": materialized["id"],
            "document_id": materialized["document_id"],
            "clause_identifier": unit["identifier"],
            "entry_id": unit["entry_id"],
            "unit_start": unit["start"],
            "unit_end": unit["end"],
            "unit_char_count": unit["char_count"],
            "unit_content_sha256": unit_content_sha256,
            "oversize": unit["oversize"],
            "linked_from": linked_from,
            "document_tree_address": materialized["document_tree_address"],
            "actor_support": actor_support,
            "decision": decision,
        })
        return materialized

    for row in direct:
        admit(row)

    # Chunk boundaries exist for embeddings, not for legal meaning. For a broad
    # document-research question, scan every authored clause/subclause as one
    # bounded unit so an explicit temporal duty cannot disappear merely because
    # its actor and orientation landed in adjacent embedding chunks.
    for document_id in sorted(document_sources):
        source = document_sources[document_id]
        _, by_identifier = entry_maps(source.get("declared_structure") or {})
        entries = sorted(
            by_identifier.values(),
            key=lambda entry: (
                int(entry["span"]["start"]),
                int(entry["span"]["end"]),
                str(entry.get("entry_id") or ""),
            ),
        )
        for entry in entries:
            if entry.get("kind") not in {"clause", "subclause"}:
                continue
            unit_start = int(entry["span"]["start"])
            unit_end = int(entry["span"]["end"])
            if unit_end <= unit_start:
                continue
            unit_text = str(source["content"])[unit_start:unit_end]
            relation_scan = scan_prestart_relations(unit_text)
            if not relation_scan:
                continue
            relations = _apply_query_relation_filters(relation_scan, query_text)
            trace_row = {
                "document_id": document_id,
                "entry_id": str(entry.get("entry_id") or ""),
                "clause_identifier": str(entry.get("identifier") or ""),
                "unit_start": unit_start,
                "unit_end": unit_end,
                "relations": redacted_relations(relation_scan),
                "recall_basis": "tree_addressed_project_inventory",
                "admitted_candidate_ids": [],
                "decision": (
                    "RETAINED_DIRECT_AUTHORED_TEMPORAL_DUTY"
                    if relations else "EXCLUDED_DIRECT_AUTHORED_ACTOR_MISMATCH"
                ),
            }
            for relation in relations:
                absolute = unit_start + int(relation["start"])
                ranked_row = _ranked_row_at_position(ranked, document_id, absolute)
                if ranked_row is None:
                    trace_row["decision"] = (
                        "EXCLUDED_DIRECT_AUTHORED_DUTY_ABSENT_FROM_CHUNK_INVENTORY"
                    )
                    continue
                direct_row = dict(ranked_row)
                relative_relation = dict(relation)
                relative_relation["start"] = absolute - int(ranked_row["start"])
                relative_relation["end"] = (
                    unit_start + int(relation["end"]) - int(ranked_row["start"])
                )
                direct_row["prestart_relations"] = [relative_relation]
                materialized = admit(direct_row)
                if materialized is not None:
                    trace_row["admitted_candidate_ids"].append(materialized["id"])
            trace_row["admitted_candidate_ids"] = sorted(set(
                trace_row["admitted_candidate_ids"]
            ))
            authored_unit_trace.append(trace_row)

    # Traverse exactly one authored reference hop. Resolved targets only become
    # evidence when their own text independently carries a qualifying temporal
    # duty; a reference alone is never treated as evidence of one.
    for source_row in list(expanded):
        source = document_sources[source_row["document_id"]]
        unit = source_row["_evidence_unit"]
        direct_refs = references_touching_span(source, unit["start"], unit["end"])
        term_refs = defined_term_reference_rows(source, unit["start"], unit["end"])
        refs = [(row, "direct_clause_reference") for row in direct_refs]
        refs += [(row, "defined_term_definition") for row in term_refs]
        unique_refs = {}
        for reference, via in refs:
            key = str(reference.get("reference_id") or f"{via}:{reference.get('span')}")
            unique_refs.setdefault(key, (reference, via))
        _, by_identifier = entry_maps(source.get("declared_structure") or {})
        for key in sorted(unique_refs):
            reference, via = unique_refs[key]
            safe = safe_reference_record(reference, via=via)
            if reference.get("outcome") != "resolved":
                target_is_addressable = (
                    safe["named_identifier"] in globally_addressable_identifiers
                )
                if safe["named_identifier"] is not None and not target_is_addressable:
                    missing_sources.append({
                        "document_id": source_row["document_id"],
                        "source_clause_identifier": unit["identifier"],
                        **safe,
                        "reason_code": "MISSING_REFERENCED_SOURCE",
                    })
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "decision": (
                        "UNPARSED_REFERENCE_TARGET_ADDRESS_PRESENT"
                        if target_is_addressable else
                        "MISSING_OR_UNPARSED_REFERENCE"
                    ),
                })
                continue
            target_identifier = str(reference.get("named_identifier") or "")
            target = by_identifier.get(target_identifier)
            if target is None:
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "decision": "RESOLVED_REFERENCE_TARGET_NOT_ADDRESSABLE",
                })
                continue
            target_start = int(target["span"]["start"])
            target_end = int(target["span"]["end"])
            narrower_targets = [
                entry for identifier, entry in by_identifier.items()
                if identifier != target_identifier
                and isinstance(entry, dict)
                and isinstance(entry.get("span"), dict)
                and target_start <= int(entry["span"]["start"])
                and int(entry["span"]["end"]) <= target_end
                and (
                    int(entry["span"]["start"]) > target_start
                    or int(entry["span"]["end"]) < target_end
                )
            ]
            if narrower_targets:
                # A reference to a whole parent clause does not identify which
                # of its many authored children is relevant. Following it into
                # the first temporal sentence would be a guess, so keep the
                # resolved reference in telemetry but admit no evidence from it.
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "narrower_target_count": len(narrower_targets),
                    "decision": "RESOLVED_REFERENCE_TARGET_TOO_BROAD",
                })
                continue
            target_text = str(source["content"])[target_start:target_end]
            target_scan = scan_prestart_relations(target_text)
            target_relations = _apply_query_relation_filters(target_scan, query_text)
            if not target_relations:
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "decision": "RESOLVED_TARGET_HAS_NO_QUALIFYING_TEMPORAL_DUTY",
                })
                continue
            for relation in target_relations:
                absolute = target_start + int(relation["start"])
                ranked_row = _ranked_row_at_position(
                    ranked, source_row["document_id"], absolute,
                )
                if ranked_row is None:
                    link_trace.append({
                        "source_candidate_id": source_row["id"],
                        **safe,
                        "target_identifier": target_identifier,
                        "target_start": target_start,
                        "target_end": target_end,
                        "decision": "RESOLVED_TARGET_ABSENT_FROM_CHUNK_INVENTORY",
                    })
                    continue
                linked = dict(ranked_row)
                relative_relation = dict(relation)
                relative_relation["start"] = absolute - int(ranked_row["start"])
                relative_relation["end"] = (
                    target_start + int(relation["end"]) - int(ranked_row["start"])
                )
                linked["prestart_relations"] = [relative_relation]
                admitted = admit(linked, linked_from=source_row["id"])
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "target_candidate_id": ranked_row["id"],
                    "target_clause_identifier": (
                        admitted["_evidence_unit"]["identifier"] if admitted else None
                    ),
                    "decision": "ADMITTED_LINKED_TEMPORAL_DUTY",
                })
    return expanded, {
        "clause_expansion": expansion_trace,
        "authored_unit_scan": authored_unit_trace,
        "cross_reference_traversal": link_trace,
        "overlap_deduplication": dedup_trace,
        "missing_sources": missing_sources,
    }


def validate_document_input(display_name, content, media_type):
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("document display_name is required")
    if len(display_name) > 512:
        raise ValueError("document display_name exceeds 512 characters")
    if not isinstance(content, str):
        raise ValueError("document content must be UTF-8 text, not binary")
    try:
        encoded = content.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueError("document content must be valid UTF-8") from None
    if not content.strip():
        raise ValueError("document content is empty")
    if len(content) > MAX_DOCUMENT_SOURCE_CHARS:
        raise ValueError(
            f"document content exceeds {MAX_DOCUMENT_SOURCE_CHARS} characters"
        )
    if media_type not in ALLOWED_DOCUMENT_MEDIA_TYPES:
        raise ValueError(
            "document media_type must be plain text or UTF-8 markup; binary formats are unsupported"
        )
    return display_name.strip(), content, media_type, len(encoded)


def encode_vector_f32(values):
    vector = _validate_vector(values)
    raw = struct.pack(f"<{EMBEDDING_DIMENSION}f", *vector)
    return base64.b64encode(raw).decode("ascii")


def decode_vector_f32(value):
    if not isinstance(value, str):
        raise ValueError("document passage vector must be base64 text")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("document passage vector is not canonical base64") from None
    if len(raw) != 4 * EMBEDDING_DIMENSION:
        raise ValueError("document passage vector has the wrong float32 dimension")
    canonical = base64.b64encode(raw).decode("ascii")
    if canonical != value:
        raise ValueError("document passage vector is not canonical base64")
    return _validate_vector(list(struct.unpack(f"<{EMBEDDING_DIMENSION}f", raw)))


def _validate_vector(values):
    if not isinstance(values, list) or len(values) != EMBEDDING_DIMENSION:
        raise ValueError(f"document vector must contain {EMBEDDING_DIMENSION} values")
    result = []
    for value in values:
        if isinstance(value, bool):
            raise ValueError("document vector values must be finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("document vector values must be finite numbers")
        result.append(number)
    norm = math.sqrt(sum(number * number for number in result))
    if abs(norm - 1.0) > 2e-3:
        raise ValueError(f"document vector must be unit normalized, got norm {norm}")
    return result


def validate_embedding_result(source_text, payload):
    if not isinstance(payload, dict) or set(payload) != {
        "model", "revision", "chunks",
    }:
        raise ValueError("document embedding result fields mismatch")
    if not isinstance(payload["model"], str) or not payload["model"].strip():
        raise ValueError("document embedding model is required")
    if not isinstance(payload["revision"], str) or not payload["revision"].strip():
        raise ValueError("document embedding revision is required")
    chunks = payload["chunks"]
    if not isinstance(chunks, list) or not 1 <= len(chunks) <= MAX_DOCUMENT_CHUNKS:
        raise ValueError(
            f"document embedding must contain 1..{MAX_DOCUMENT_CHUNKS} chunks"
        )
    validated = []
    previous_end = 0
    for index, row in enumerate(chunks):
        if not isinstance(row, dict) or set(row) != {"index", "start", "end", "values"}:
            raise ValueError(f"document chunk {index} fields mismatch")
        start, end = row["start"], row["end"]
        if row["index"] != index or type(start) is not int or type(end) is not int:
            raise ValueError("document chunk index/offset types are invalid")
        if not (0 <= start < end <= len(source_text)):
            raise ValueError("document chunk offsets are invalid")
        if index == 0 and start != 0:
            raise ValueError("document chunks must begin at source offset zero")
        if index and (start >= previous_end or end <= previous_end):
            raise ValueError("document chunks must overlap and advance")
        if index == len(chunks) - 1 and end != len(source_text):
            raise ValueError("document chunks must cover the source ending")
        validated.append({
            "index": index,
            "start": start,
            "end": end,
            "vector_f32_le_base64": encode_vector_f32(row["values"]),
        })
        previous_end = end
    return {
        "model": payload["model"].strip(),
        "revision": payload["revision"].strip(),
        "chunks": validated,
    }


def build_document_query_profile(source_text, provider):
    """Embed a draft without mutating document, tree, or memory state."""
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("document retrieval query is required")
    embedded = validate_embedding_result(
        source_text, provider.embed_document(source_text),
    )
    return build_semantic_profile(
        source_text,
        [
            {
                "start": row["start"],
                "end": row["end"],
                "values": decode_vector_f32(row["vector_f32_le_base64"]),
            }
            for row in embedded["chunks"]
        ],
        model=embedded["model"],
        revision=embedded["revision"],
    )


def rank_document_chunks_for_packet(
    query_text, query_profile, document_chunks, *, k, max_chars,
    structural_scores=None, structural_telemetry=None,
    document_sources=None, return_trace=False,
):
    """Return bounded, exact source excerpts from immutable active chunks."""
    if type(k) is not int or k <= 0:
        raise ValueError("document packet k must be a positive integer")
    if type(max_chars) is not int or max_chars <= 0:
        raise ValueError("document packet max_chars must be a positive integer")
    ranked = []
    relation_filter_trace = []
    query_terms = _retrieval_terms(query_text)
    prestart_query = prestart_requirement_query(query_text)
    for row in document_chunks:
        text = row.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError("document chunk text is required for packet admission")
        vector = decode_vector_f32(row["passage_vector"])
        scores = profile_similarity(
            query_profile, {"chunks": [{"values": vector}]},
        )
        document_id = str(row["document_id"])
        chunk_index = int(row["chunk_index"])
        relation_scan = scan_prestart_relations(text) if prestart_query else []
        relations = _apply_query_relation_filters(relation_scan, query_text)
        absolute_relation_start = (
            int(row["start"]) + relations[0]["start"] if relations else None
        )
        provenance = row.get("clause_provenance")
        if not isinstance(provenance, list):
            provenance = []
        containing = [
            item for item in provenance
            if isinstance(item, dict)
            and item.get("kind") == "clause"
            and item.get("status") == "valid"
            and absolute_relation_start is not None
            and int(item["span"]["start"]) <= absolute_relation_start < int(item["span"]["end"])
        ]
        containing.sort(key=lambda item: (
            int(item["span"]["end"]) - int(item["span"]["start"]),
            str(item["identifier"]),
        ))
        matched_clause = str(containing[0]["identifier"]) if containing else None
        if relations:
            authored_headings = [
                match for match in _LOCAL_CLAUSE_HEADING.finditer(
                    text, 0, relations[0]["start"] + 1,
                )
            ]
            if authored_headings:
                # The closest exact heading in the chunk beats a broader
                # overlapping parent from the whole-document index.
                matched_clause = authored_headings[-1].group("identifier")
        if prestart_query and re.search(r"\bcontractor\b", query_text, re.IGNORECASE):
            matched_entry = next(
                (
                    item for item in containing
                    if str(item.get("identifier")) == str(matched_clause)
                ),
                containing[0] if containing else None,
            )
            title = str(matched_entry.get("title") or "") if matched_entry else ""
            if "principal" in title.casefold() and "contractor" not in title.casefold():
                for relation in relation_scan:
                    if relation["decision"] == "included" and relation["actor_role"] != "contractor":
                        relation["decision"] = "excluded"
                        relation["reason_code"] = "EXCLUDED_PRINCIPAL_ONLY_CLAUSE_TITLE"
                relations = [row for row in relation_scan if row["decision"] == "included"]
        relation_filter_trace.append({
            "candidate_id": f"{document_id}:chunk:{chunk_index}",
            "document_id": document_id,
            "chunk_index": chunk_index,
            "chunk_start": int(row["start"]),
            "chunk_end": int(row["end"]),
            "chunk_text_sha256": str(row["text_sha256"]),
            "relations": redacted_relations(relation_scan),
            "decision": (
                "RETAINED_TEMPORAL_CANDIDATE" if relations
                else "EXCLUDED_NO_QUALIFYING_TEMPORAL_RELATION"
            ),
        })
        ranked.append({
            "id": f"{document_id}:chunk:{chunk_index}",
            "document_id": document_id,
            "display_name": str(row["display_name"]),
            "chunk_index": chunk_index,
            "start": int(row["start"]),
            "end": int(row["end"]),
            "text": text,
            "text_sha256": str(row["text_sha256"]),
            "semantic_score": float(scores["query_relevance_score"]),
            "best_chunk_score": float(scores["best_chunk_score"]),
            "lexical_score": _lexical_query_coverage(query_terms, text),
            "prestart_relations": relations,
            "clause_identifiers": sorted({
                str(item["identifier"]) for item in provenance
                if isinstance(item, dict) and item.get("kind") == "clause"
                and item.get("status") == "valid" and item.get("identifier")
            }),
            "matched_clause_identifier": matched_clause,
            "document_tree_address": {
                "receipt_analysis_digest": str(row.get("analysis_digest") or ""),
                "branch_ids": [
                    str(branch.get("branch_id") or "")
                    for branch in row.get("address_branches", [])
                    if isinstance(branch, dict) and branch.get("branch_id")
                ],
                "branch_count": len(row.get("address_branches", [])),
                "basis": "pinned_10k_8d17d_document_tree_receipt",
            },
            "score_space": "minilm_dense_plus_exact_term_rrf",
            "packet_eligible": True,
            "structural_signature": None,
        })
    ranked.sort(
        key=lambda row: (
            -row["semantic_score"],
            row["document_id"],
            row["chunk_index"],
        )
    )
    for dense_rank, row in enumerate(ranked, 1):
        row["dense_rank"] = dense_rank
    lexical_rows = sorted(
        (row for row in ranked if row["lexical_score"] > 0.0),
        key=lambda row: (
            -row["lexical_score"],
            -row["semantic_score"],
            row["document_id"],
            row["chunk_index"],
        ),
    )
    lexical_ranks = {row["id"]: rank for rank, row in enumerate(lexical_rows, 1)}
    relation_rows = sorted(
        (row for row in ranked if row["prestart_relations"]),
        key=lambda row: (
            -row["prestart_relations"][0]["weight"],
            -len(row["prestart_relations"]),
            -row["semantic_score"],
            row["id"],
        ),
    )
    relation_ranks = {row["id"]: rank for rank, row in enumerate(relation_rows, 1)}
    for row in ranked:
        lexical_rank = lexical_ranks.get(row["id"])
        row["lexical_rank"] = lexical_rank
        relation_rank = relation_ranks.get(row["id"])
        row["prestart_relation_rank"] = relation_rank
        if prestart_query:
            row["semantic_hybrid_score"] = (
                0.25 / (DOCUMENT_RRF_K + row["dense_rank"])
                + (0.25 / (DOCUMENT_RRF_K + lexical_rank) if lexical_rank else 0.0)
                + (0.50 / (DOCUMENT_RRF_K + relation_rank) if relation_rank else 0.0)
            )
        else:
            row["semantic_hybrid_score"] = (
                DOCUMENT_DENSE_RRF_WEIGHT / (DOCUMENT_RRF_K + row["dense_rank"])
                + (
                    DOCUMENT_LEXICAL_RRF_WEIGHT / (DOCUMENT_RRF_K + lexical_rank)
                    if lexical_rank is not None else 0.0
                )
            )
    semantic_hybrid_rows = sorted(
        ranked,
        key=lambda row: (
            -row["semantic_hybrid_score"],
            -row["lexical_score"],
            -row["semantic_score"],
            row["id"],
        ),
    )
    semantic_hybrid_ranks = {
        row["id"]: rank for rank, row in enumerate(semantic_hybrid_rows, 1)
    }
    for row in ranked:
        row["semantic_hybrid_rank"] = semantic_hybrid_ranks[row["id"]]
    structural_ranks = {}
    tree_informative = (
        structural_scores is not None
        and isinstance(structural_telemetry, dict)
        and structural_telemetry.get("informative") is True
    )
    if structural_scores is not None:
        if not isinstance(structural_scores, dict):
            raise ValueError("document structural scores must be an object")
        structural_rows = []
        # The Tree is the dominant ranker *inside* a semantically plausible
        # region. Structural similarity is not authority to introduce a chunk
        # whose subject is unrelated to the draft.
        structural_cohort_ids = {
            row["id"] for row in semantic_hybrid_rows[:DOCUMENT_TREE_SEMANTIC_COHORT]
        }
        for row in ranked:
            if row["id"] not in structural_cohort_ids:
                continue
            score = structural_scores.get(row["id"])
            if not isinstance(score, dict):
                raise ValueError("every indexed document chunk requires a structural score")
            structural_rows.append((
                row["id"], float(score["score"]), str(score["matched_branch_id"]),
            ))
        structural_rows.sort(key=lambda item: (-item[1], item[0]))
        structural_ranks = {
            row_id: (rank, score, branch_id)
            for rank, (row_id, score, branch_id) in enumerate(structural_rows, 1)
        }
    for row in ranked:
        structural = structural_ranks.get(row["id"])
        if structural is None or not tree_informative:
            row["rrf_score"] = row["semantic_hybrid_score"]
            if structural is not None:
                structural_rank, structural_score, branch_id = structural
                row["structural_rank"] = None
                row["structural_resonance"] = structural_score
                row["matched_document_branch_id"] = branch_id or None
                row["structural_channel_informative"] = False
                row["score_space"] = (
                    "minilm_dense_plus_exact_relation_rrf_document_tree_flat"
                    if prestart_query else
                    "minilm_dense_plus_exact_term_rrf_document_tree_flat"
                )
        else:
            structural_rank, structural_score, branch_id = structural
            # The existing product retrieval prior remains unchanged: Tree 0.60,
            # dense semantic address 0.40. Exact terms remain visible telemetry
            # and a deterministic tie-break, not a third force.
            row["structural_rank"] = structural_rank
            row["structural_resonance"] = structural_score
            row["matched_document_branch_id"] = branch_id
            row["structural_channel_informative"] = True
            row["score_space"] = (
                "minilm_dense_plus_exact_relation_plus_document_tree_rrf"
                if prestart_query else "minilm_dense_plus_document_tree_rrf"
            )
            row["rrf_score"] = (
                0.40 / (DOCUMENT_RRF_K + row["semantic_hybrid_rank"])
                + 0.60 / (DOCUMENT_RRF_K + structural_rank)
            )
    ranked.sort(
        key=lambda row: (
            -row["rrf_score"],
            -row["lexical_score"],
            -row["semantic_score"],
            row["document_id"],
            row["chunk_index"],
        )
    )
    expansion_trace = {
        "clause_expansion": [],
        "cross_reference_traversal": [],
        "overlap_deduplication": [],
        "missing_sources": [],
    }
    if prestart_query and document_sources is not None:
        packet_rows, expansion_trace = _expanded_prestart_packet_rows(
            ranked, document_sources, query_text,
        )
    else:
        packet_rows = _prestart_packet_order(ranked) if prestart_query else ranked
    admitted = []
    used_chars = 0
    limit = min(k, MAX_DOCUMENT_PACKET_CANDIDATES)
    packet_decisions = []
    for packet_rank, row in enumerate(packet_rows, 1):
        unit = row.get("_evidence_unit")
        source = (
            document_sources.get(row["document_id"])
            if document_sources is not None else None
        )
        if len(admitted) >= limit:
            packet_decisions.append({
                "candidate_id": row["id"],
                "document_id": row["document_id"],
                "clause_identifier": row.get("matched_clause_identifier"),
                "decision": "EXCLUDED_GATEWAY_ITEM_LIMIT",
            })
            continue
        if unit is not None and source is not None:
            relative_start = int(unit["start"])
            relative_end = int(unit["end"])
            excerpt = str(source["content"])[relative_start:relative_end]
            if len(excerpt) > max_chars - used_chars:
                packet_decisions.append({
                    "candidate_id": row["id"],
                    "document_id": row["document_id"],
                    "clause_identifier": unit["identifier"],
                    "unit_start": relative_start,
                    "unit_end": relative_end,
                    "unit_char_count": len(excerpt),
                    "remaining_chars": max_chars - used_chars,
                    "decision": "EXCLUDED_GATEWAY_CHAR_BUDGET",
                })
                continue
            excerpt_start = relative_start
            excerpt_end = relative_end
            truncated = False
        else:
            excerpt_length = min(
                len(row["text"]),
                PRESTART_PACKET_EXCERPT_CHARS if prestart_query
                else MAX_DOCUMENT_PACKET_EXCERPT_CHARS,
                max_chars - used_chars,
            )
            if excerpt_length <= 0:
                packet_decisions.append({
                    "candidate_id": row["id"],
                    "document_id": row["document_id"],
                    "clause_identifier": row.get("matched_clause_identifier"),
                    "decision": "EXCLUDED_GATEWAY_CHAR_BUDGET",
                })
                continue
            if row["prestart_relations"]:
                relation_start = row["prestart_relations"][0]["start"]
                preceding_headings = [
                    match for match in _LOCAL_CLAUSE_HEADING.finditer(
                        row["text"], 0, relation_start + 1,
                    )
                ]
                if preceding_headings and relation_start - preceding_headings[-1].start() <= 400:
                    relative_start = preceding_headings[-1].start()
                else:
                    relative_start = max(0, relation_start - min(100, excerpt_length // 4))
                relative_start = min(relative_start, len(row["text"]) - excerpt_length)
            else:
                relative_start = _evidence_excerpt_start(
                    row["text"], query_text, excerpt_length,
                )
            relative_end = relative_start + excerpt_length
            clause_pattern = re.compile(r"(?m)^[ \t]*\d+(?:\.\d+)+(?:[ \t]|$)")
            if clause_pattern.match(row["text"], relative_start):
                next_clause = next(
                    (
                        match.start() for match in clause_pattern.finditer(
                            row["text"], relative_start + 1, relative_end,
                        )
                    ),
                    None,
                )
                if next_clause is not None:
                    relative_end = next_clause
            excerpt = row["text"][relative_start:relative_end].rstrip()
            relative_end = relative_start + len(excerpt)
            excerpt_start = int(row["start"]) + relative_start
            excerpt_end = int(row["start"]) + relative_end
            truncated = relative_start > 0 or relative_end < len(row["text"])
        admitted.append({
            **{
                key: value for key, value in row.items()
                if key != "text" and not key.startswith("_")
            },
            "text": excerpt,
            "rank": len(admitted) + 1,
            "excerpt_start": excerpt_start,
            "excerpt_end": excerpt_end,
            "excerpt_sha256": "sha256:" + hashlib.sha256(
                excerpt.encode("utf-8")
            ).hexdigest(),
            "truncated": truncated,
        })
        used_chars += len(excerpt)
        packet_decisions.append({
            "candidate_id": row["id"],
            "document_id": row["document_id"],
            "clause_identifier": row.get("matched_clause_identifier"),
            "excerpt_start": excerpt_start,
            "excerpt_end": excerpt_end,
            "excerpt_sha256": admitted[-1]["excerpt_sha256"],
            "decision": "ADMITTED_GATEWAY_PACKET_CANDIDATE",
        })

    if not return_trace:
        return admitted
    selected_ids = {row["id"] for row in admitted}
    discovered = []
    for row in packet_rows:
        unit = row.get("_evidence_unit") or {}
        discovered.append({
            "evidence_id": row["id"],
            "origin_candidate_id": row.get("_origin_candidate_id", row["id"]),
            "document_id": row["document_id"],
            "clause_identifier": row.get("matched_clause_identifier"),
            "unit_start": unit.get("start", row["start"]),
            "unit_end": unit.get("end", row["end"]),
            "relation_types": sorted({
                item["relation"] for item in row.get("prestart_relations", [])
            }),
            "conditionality": sorted({
                item["conditionality"] for item in row.get("prestart_relations", [])
            }),
            "source_digests": sorted({
                item["text_sha256"] for item in row.get("prestart_relations", [])
            }),
            "document_tree_address": row.get("document_tree_address", {}),
            "actor_support": row.get("_actor_support", {}),
            "gateway_selected": row["id"] in selected_ids,
        })
    unique_missing_sources = {}
    for row in expansion_trace["missing_sources"]:
        identity = (
            row.get("document_id"), row.get("named_identifier"),
            row.get("outcome"), row.get("via"),
        )
        unique_missing_sources.setdefault(identity, row)
    missing_sources = list(unique_missing_sources.values())
    expansion_trace["missing_sources"] = missing_sources
    trace = {
        "version": DOCUMENT_RESEARCH_TRACE_VERSION,
        "intent": parse_research_intent(query_text),
        "inventory": inventory_trace(document_sources or {}),
        "candidate_recall": [redacted_ranked_chunk(row) for row in ranked],
        "semantic_cohort": [
            {
                "candidate_id": row["id"],
                "semantic_hybrid_rank": row["semantic_hybrid_rank"],
                "admitted_to_structural_cohort": row["semantic_hybrid_rank"]
                <= DOCUMENT_TREE_SEMANTIC_COHORT,
                "reason_code": (
                    "ADMITTED_SEMANTIC_COHORT" if row["semantic_hybrid_rank"]
                    <= DOCUMENT_TREE_SEMANTIC_COHORT else
                    "EXCLUDED_SEMANTIC_COHORT_LIMIT"
                ),
            }
            for row in ranked
        ],
        "actor_temporal_filters": relation_filter_trace,
        **expansion_trace,
        "gateway_packet_selection": {
            "requested_k": k,
            "effective_item_limit": limit,
            "requested_max_chars": max_chars,
            "selected_chars": used_chars,
            "decisions": packet_decisions,
        },
        "final_evidence_coverage": {
            "discovered_units": discovered,
            "selected_evidence_ids": [row["id"] for row in admitted],
            "missing_sources": missing_sources,
            "exhaustiveness": (
                "limited_by_missing_referenced_sources" if missing_sources
                else "complete_within_declared_document_inventory_and_rules"
            ),
        },
        "document_tree": {
            "structural_telemetry": structural_telemetry or {},
        },
    }
    return admitted, trace


def _evidence_excerpt_start(text, query_text, limit):
    """Centre an exact excerpt on the densest shared-term window after dense rank."""
    if len(text) <= limit:
        return 0
    terms = _retrieval_terms(query_text)
    folded = text.casefold()
    occurrences = []
    for term in terms:
        occurrences.extend(
            (match.start(), term)
            for match in re.finditer(re.escape(term), folded)
        )
    if not occurrences:
        return 0
    starts = {
        min(max(0, position - limit // 3), len(text) - limit)
        for position, _ in occurrences
    }
    best = None
    for start in sorted(starts):
        end = start + limit
        within = [(position, term) for position, term in occurrences if start <= position < end]
        score = (len({term for _, term in within}), len(within), -start)
        if best is None or score > best[0]:
            best = (score, start)
    start = best[1]
    within = [
        (position, term) for position, term in occurrences
        if start <= position < start + limit
    ]
    focus, _ = min(within, key=lambda item: (-len(item[1]), item[0]))
    boundaries = [
        match.start()
        for match in re.finditer(
            r"(?m)^[ \t]*\d+(?:\.\d+)+(?:[ \t]|$)", text,
        )
        if match.start() <= focus
    ]
    if boundaries and focus - boundaries[-1] <= limit // 2:
        return min(boundaries[-1], len(text) - limit)
    return start


def _retrieval_terms(query_text):
    return sorted({
        term.casefold()
        for term in re.findall(r"[\w'-]+", str(query_text), flags=re.UNICODE)
        if len(term) >= 4
    })


def _lexical_query_coverage(query_terms, text):
    if not query_terms:
        return 0.0
    folded = text.casefold()
    return sum(term in folded for term in query_terms) / len(query_terms)


class DocumentEmbeddingWorkerClient:
    """Persistent, local-only MiniLM client; it never starts Gemma."""

    def __init__(self, command, timeout_seconds=600.0):
        if not command or not all(isinstance(value, str) and value for value in command):
            raise ValueError("document embedding worker command is required")
        self.command = list(command)
        self.timeout_seconds = float(timeout_seconds)
        self._process = None
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls):
        python = os.environ.get("TOM_ASSIST_STRUCTURE_PYTHON", "")
        model = os.environ.get("TOM_ASSIST_MINILM_MODEL", "")
        missing = [name for name, value in (
            ("TOM_ASSIST_STRUCTURE_PYTHON", python),
            ("TOM_ASSIST_MINILM_MODEL", model),
        ) if not value]
        if missing:
            raise ValueError(
                "local document embedding is not configured: " + ", ".join(missing)
            )
        paths = [Path(python).expanduser(), Path(model).expanduser()]
        if any(not path.is_absolute() or not path.exists() for path in paths):
            raise ValueError("document embedding paths must be existing absolute paths")
        script = Path(__file__).with_name("document_embedding_worker.py").resolve()
        return cls([str(paths[0].resolve()), str(script), "--model", str(paths[1].resolve())])

    def _start(self):
        if self._process is not None and self._process.poll() is None:
            return self._process
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=isolated_worker_environment(),
        )
        return self._process

    def embed_document(self, source_text):
        request_id = str(uuid.uuid4())
        request = {
            "protocol": DOCUMENT_WORKER_PROTOCOL,
            "request_id": request_id,
            "source_text": source_text,
        }
        with self._lock:
            process = self._start()
            if process.stdin is None or process.stdout is None:
                raise ValueError("document embedding worker has no pipes")
            try:
                process.stdin.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                self.close()
                raise ValueError("document embedding worker stopped before accepting input") from None
            selector = selectors.DefaultSelector()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(self.timeout_seconds):
                    self.close()
                    raise ValueError("document embedding worker timed out")
                line = process.stdout.readline()
            finally:
                selector.close()
            if not line:
                self.close()
                raise ValueError("document embedding worker ended unexpectedly")
            response = json.loads(line)
            if response.get("protocol") != DOCUMENT_WORKER_PROTOCOL:
                raise ValueError("document embedding worker protocol mismatch")
            if response.get("request_id") != request_id:
                raise ValueError("document embedding worker response ID mismatch")
            if "error" in response:
                raise ValueError(str(response["error"])[:500])
            if set(response) != {"protocol", "request_id", "model", "revision", "chunks"}:
                raise ValueError("document embedding worker response shape mismatch")
            return {key: response[key] for key in ("model", "revision", "chunks")}

    def close(self):
        process, self._process = self._process, None
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
