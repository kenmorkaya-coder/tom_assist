"""Pure, text-free diagnostics for project document research.

The product packet may contain exact source excerpts.  This module never does:
its output is safe to retain as a local diagnostic because it contains only
document/chunk IDs, authored addresses, offsets, digests, scores and bounded
decision codes.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence


DOCUMENT_RESEARCH_TRACE_VERSION = "tom-assist-document-research-trace/1.1"
DOCUMENT_RESEARCH_INTENT_VERSION = "tom-assist-document-research-intent/1.0"
MAX_COMPOSITE_EVIDENCE_UNIT_CHARS = 2_400


def text_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_research_intent(query: str) -> dict[str, Any]:
    """Describe only explicit query orientation; never infer legal meaning."""
    folded = " ".join(str(query).casefold().split())
    actors = []
    for role, pattern in (
        ("contractor", r"\b(?:scaw\s+)?contractor\b"),
        ("principal", r"\bprincipal\b"),
        ("parties", r"\bpart(?:y|ies)\b"),
    ):
        if re.search(pattern, folded):
            actors.append(role)
    pre_start = bool(re.search(
        r"\b(?:before|prior|pre[- ]?start|prerequisite|commenc\w*|start\w*)\b",
        folded,
    ))
    broad = bool(
        pre_start
        and re.search(r"\b(?:under|in accordance with)\s+(?:this|the)\s+(?:deed|contract)\b", folded)
        and re.search(r"\b(?:what|all|requirements?|prerequisites?|must)\b", folded)
    )
    return {
        "version": DOCUMENT_RESEARCH_INTENT_VERSION,
        "query_sha256": text_digest(query),
        "actor_scope": actors or ["unspecified"],
        "temporal_scope": "pre_start" if pre_start else "unspecified",
        "coverage_scope": (
            ["project_wide", "activity_conditional"] if broad
            else ["activity_conditional"] if pre_start else ["unspecified"]
        ),
        "broad_document_research": broad,
    }


def _safe_reference_identifier(row: Mapping[str, Any]) -> str | None:
    named = row.get("named_identifier")
    if isinstance(named, str) and 0 < len(named) <= 120:
        return named
    raw = row.get("reference_text")
    if not isinstance(raw, str):
        return None
    match = re.match(
        r"(?i)\s*(Schedule\s+[A-Z][A-Za-z0-9.]*|Attachment\s+[A-Z0-9.]+|"
        r"Appendix\s+[A-Z0-9.]+|Annexure\s+[A-Z0-9.]+|"
        r"section\s+[0-9]+(?:\.[0-9]+)*\s+of\s+the\s+[A-Za-z ]{1,50}Specification)",
        raw,
    )
    return None if match is None else " ".join(match.group(1).split())


def safe_reference_record(row: Mapping[str, Any], *, via: str) -> dict[str, Any]:
    span = row.get("span") if isinstance(row.get("span"), Mapping) else {}
    label = _safe_reference_identifier(row)
    return {
        "reference_id": str(row.get("reference_id") or ""),
        "via": via,
        "span": {
            "start": int(span.get("start", -1)),
            "end": int(span.get("end", -1)),
        },
        "named_identifier": label,
        "outcome": str(row.get("outcome") or "unclassified"),
        "reference_form_sha256": text_digest(str(row.get("reference_text") or "")),
    }


def inventory_trace(document_sources: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    documents = []
    all_missing = []
    for document_id in sorted(document_sources):
        source = document_sources[document_id]
        structure = source.get("declared_structure")
        structure = structure if isinstance(structure, Mapping) else {}
        clause_index = structure.get("clause_index")
        clause_index = clause_index if isinstance(clause_index, Mapping) else {}
        entries = clause_index.get("entries")
        entries = entries if isinstance(entries, list) else []
        references = structure.get("references")
        references = references if isinstance(references, Mapping) else {}
        reference_rows = references.get("references")
        reference_rows = reference_rows if isinstance(reference_rows, list) else []
        outcomes: dict[str, int] = {}
        missing = []
        for row in reference_rows:
            if not isinstance(row, Mapping):
                continue
            outcome = str(row.get("outcome") or "unclassified")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            if outcome != "resolved":
                record = safe_reference_record(row, via="document_inventory")
                if record["named_identifier"] is not None:
                    missing.append(record)
                    all_missing.append({"document_id": document_id, **record})
        by_kind: dict[str, int] = {}
        malformed = 0
        for row in entries:
            if not isinstance(row, Mapping):
                continue
            kind = str(row.get("kind") or "unknown")
            by_kind[kind] = by_kind.get(kind, 0) + 1
            malformed += int(row.get("status") == "malformed")
        documents.append({
            "document_id": document_id,
            "content_sha256": str(source.get("content_sha256") or ""),
            "byte_length": int(source.get("byte_length") or 0),
            "declared_structure_digest": str(structure.get("structure_digest") or ""),
            "declared_address_counts": by_kind,
            "malformed_address_count": malformed,
            "reference_outcome_counts": outcomes,
            "unresolved_external_reference_count": len(missing),
            "unresolved_external_references": missing,
        })
    return {
        "active_document_count": len(documents),
        "active_chunk_count": sum(
            int(source.get("chunk_count") or 0) for source in document_sources.values()
        ),
        "documents": documents,
        "unresolved_external_reference_count": len(all_missing),
    }


def entry_maps(structure: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    index = structure.get("clause_index")
    rows = index.get("entries", []) if isinstance(index, Mapping) else []
    by_id = {
        str(row["entry_id"]): dict(row)
        for row in rows if isinstance(row, Mapping) and row.get("entry_id")
    }
    by_identifier = {
        str(row["identifier"]): dict(row)
        for row in rows
        if isinstance(row, Mapping)
        and row.get("identifier")
        and row.get("status") == "valid"
        and row.get("kind") in {"clause", "subclause", "schedule", "named_section"}
    }
    return by_id, by_identifier


def _span(row: Mapping[str, Any]) -> tuple[int, int]:
    return int(row["span"]["start"]), int(row["span"]["end"])


def evidence_unit_for_position(
    source: Mapping[str, Any], absolute_position: int,
) -> dict[str, Any] | None:
    """Choose an authored composite duty unit without cutting a child duty."""
    structure = source.get("declared_structure")
    if not isinstance(structure, Mapping):
        return None
    by_id, _ = entry_maps(structure)
    candidates = [
        row for row in by_id.values()
        if row.get("status") == "valid"
        and row.get("kind") in {"clause", "subclause"}
        and _span(row)[0] <= absolute_position < _span(row)[1]
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda row: (_span(row)[1] - _span(row)[0], _span(row)[0]))
    selected = candidates[0]
    # A nested leaf often expresses only item (ii) of one compound obligation.
    # Promote exactly one authored parent when it remains a bounded subclause.
    parent = by_id.get(str(selected.get("parent_entry_id") or ""))
    if (
        selected.get("kind") == "subclause"
        and isinstance(parent, Mapping)
        and parent.get("kind") in {"clause", "subclause"}
        and _span(parent)[1] - _span(parent)[0] <= MAX_COMPOSITE_EVIDENCE_UNIT_CHARS
    ):
        selected = dict(parent)
    start, end = _span(selected)
    return {
        "entry_id": str(selected.get("entry_id") or ""),
        "identifier": str(selected.get("identifier") or ""),
        "kind": str(selected.get("kind") or ""),
        "start": start,
        "end": end,
        "char_count": end - start,
        "oversize": end - start > MAX_COMPOSITE_EVIDENCE_UNIT_CHARS,
    }


def references_touching_span(
    source: Mapping[str, Any], start: int, end: int,
) -> list[dict[str, Any]]:
    structure = source.get("declared_structure")
    if not isinstance(structure, Mapping):
        return []
    references = structure.get("references")
    rows = references.get("references", []) if isinstance(references, Mapping) else []
    result = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        span = row.get("span")
        if not isinstance(span, Mapping):
            continue
        if int(span.get("start", -1)) < end and int(span.get("end", -1)) > start:
            result.append(dict(row))
    return result


def defined_term_reference_rows(
    source: Mapping[str, Any], start: int, end: int,
) -> list[dict[str, Any]]:
    """Follow exact term bindings to references in their definition bodies."""
    structure = source.get("declared_structure")
    if not isinstance(structure, Mapping):
        return []
    defined = structure.get("defined_terms")
    if not isinstance(defined, Mapping):
        return []
    bindings = defined.get("bindings") if isinstance(defined.get("bindings"), list) else []
    term_ids = {
        str(row.get("term_id"))
        for row in bindings if isinstance(row, Mapping)
        and isinstance(row.get("span"), Mapping)
        and int(row["span"].get("start", -1)) < end
        and int(row["span"].get("end", -1)) > start
    }
    terms = defined.get("terms") if isinstance(defined.get("terms"), list) else []
    spans = [
        row.get("definition_span") for row in terms
        if isinstance(row, Mapping) and str(row.get("term_id")) in term_ids
        and isinstance(row.get("definition_span"), Mapping)
    ]
    result = []
    for span in spans:
        result.extend(references_touching_span(
            source, int(span["start"]), int(span["end"]),
        ))
    unique = {}
    for row in result:
        unique[str(row.get("reference_id") or text_digest(str(row)))] = row
    return [unique[key] for key in sorted(unique)]


def redacted_ranked_chunk(row: Mapping[str, Any]) -> dict[str, Any]:
    """Remove source prose and retain every mechanical ranking fact."""
    allowed = (
        "id", "document_id", "chunk_index", "start", "end", "text_sha256",
        "semantic_score", "best_chunk_score", "lexical_score", "dense_rank",
        "lexical_rank", "semantic_hybrid_rank", "semantic_hybrid_score",
        "prestart_relation_rank", "rrf_score", "structural_rank",
        "structural_resonance", "matched_document_branch_id",
        "structural_channel_informative", "score_space", "packet_eligible",
        "clause_identifiers", "matched_clause_identifier", "rank",
        "excerpt_start", "excerpt_end", "excerpt_sha256", "truncated",
        "document_tree_address",
    )
    return {key: row.get(key) for key in allowed if key in row}


def redacted_relations(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "relation": str(row.get("relation") or ""),
        "weight": float(row.get("weight") or 0.0),
        "start": int(row.get("start") or 0),
        "end": int(row.get("end") or 0),
        "actor_role": str(row.get("actor_role") or "unknown"),
        "text_sha256": str(row.get("text_sha256") or ""),
        "decision": str(row.get("decision") or "included"),
        "reason_code": str(row.get("reason_code") or "INCLUDED_TEMPORAL_RELATION"),
        "conditionality": str(row.get("conditionality") or "unspecified"),
    } for row in rows]
