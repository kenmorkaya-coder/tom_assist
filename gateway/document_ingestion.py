"""Explicit project-document chunking and local MiniLM embedding boundary."""
from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import hmac
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
    MAX_COMPOSITE_EVIDENCE_UNIT_CHARS,
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


RGM_CORPUS_VERSION = "tom-assist-rgm-lossless-sections/1"


def _rgm_json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def build_rgm_document_corpus(source_text, heading_text, provenance, *, max_chunk_chars=4000):
    """Use native RGM heading detection without discarding original source text.

    heading_text is the unchanged detector output, not a second document. Map
    its headings back to the immutable extraction; even headers the detector
    removed remain in the source ranges. All major sections are retained, and
    oversized sections are partitioned rather than truncated. No embedding,
    summary, retrieval score or tree load is authored here.
    """
    if not isinstance(source_text, str) or not source_text.strip() or not isinstance(heading_text, str):
        raise ValueError("source extraction and native heading text required")
    if type(max_chunk_chars) is not int or max_chunk_chars < 1:
        raise ValueError("positive chunk size required")
    if not isinstance(provenance, dict) or not provenance:
        raise ValueError("source provenance required")
    # Match the detector's newline definition, including literal form-feed cells.
    raw_lines = source_text.split("\n")
    offsets, offset = [], 0
    for line in raw_lines:
        offsets.append(offset)
        offset += len(line) + 1
    headings, cursor = [], 0
    for line in heading_text.split("\n"):
        if not line.strip():
            continue
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        while cursor < len(raw_lines):
            raw = raw_lines[cursor]
            if raw == line or (match and raw.strip() == match.group(2)):
                break
            cursor += 1
        if cursor == len(raw_lines):
            raise ValueError("native heading text cannot be aligned to the source")
        if match:
            headings.append(dict(start=offsets[cursor], level=len(match.group(1)), title=match.group(2)))
        cursor += 1
    major = [h for h in headings if h["level"] <= 2]
    if not major or major[0]["start"] != 0:
        major.insert(0, dict(start=0, level=0, title="Introduction"))
    source_hash = hashlib.sha256(source_text.encode()).hexdigest()
    corpus = dict(schema=RGM_CORPUS_VERSION, source_text_sha256=source_hash,
                  source_chars=len(source_text), provenance=provenance,
                  max_chunk_chars=max_chunk_chars, sections=[], chunks=[])
    for index, section in enumerate(major):
        start = section["start"]
        end = major[index + 1]["start"] if index + 1 < len(major) else len(source_text)
        if start >= end:
            continue
        section_id = f"section_{index}"
        corpus["sections"].append(dict(section_id=section_id, title=section["title"], start=start, end=end))
        pos = start
        while pos < end:
            stop = min(pos + max_chunk_chars, end)
            if stop < end:
                # Prefer a native subsection boundary near the end of this part.
                candidates = [h["start"] for h in headings if pos + max_chunk_chars // 2 < h["start"] <= stop]
                if candidates:
                    stop = candidates[-1]
                else:
                    boundary = source_text.rfind("\n", pos + max_chunk_chars // 2, stop)
                    if boundary >= pos:
                        stop = boundary + 1
            text = source_text[pos:stop]
            corpus["chunks"].append(dict(chunk_id=f"chunk_{len(corpus['chunks'])}", section_id=section_id,
                start=pos, end=stop, start_line=source_text.count("\n", 0, pos) + 1,
                end_line=source_text.count("\n", 0, stop - 1) + 1,
                text_sha256=hashlib.sha256(text.encode()).hexdigest()))
            pos = stop
    assert "".join(source_text[c["start"]:c["end"]] for c in corpus["chunks"]) == source_text
    return corpus


def retain_rgm_document_corpus(library, source_text, corpus):
    """Keep one immutable extraction plus range references in the existing shelf.

    This explicit corpus import is separate from the legacy runtime/RGM archive
    format. It adds no database tables and does not replace existing imports.
    """
    from types import SimpleNamespace
    digest = _rgm_json_hash(corpus)
    if corpus.get("schema") != RGM_CORPUS_VERSION or hashlib.sha256(source_text.encode()).hexdigest() != corpus["source_text_sha256"]:
        raise ValueError("corpus source mismatch")
    cursor = 0
    for chunk in corpus["chunks"]:
        if type(chunk["start"]) is not int or type(chunk["end"]) is not int or not cursor == chunk["start"] < chunk["end"] <= len(source_text):
            raise ValueError("corpus ranges must partition the complete source")
        if hashlib.sha256(source_text[chunk["start"]:chunk["end"]].encode()).hexdigest() != chunk["text_sha256"]:
            raise ValueError("corpus chunk checksum mismatch")
        cursor = chunk["end"]
    if cursor != len(source_text) or corpus["source_chars"] != len(source_text):
        raise ValueError("corpus omits source text")
    record_id = "rgm-corpus-" + digest
    existing = library.get(record_id)
    if existing is not None and (existing["record"] != corpus or existing["content"] != source_text):
        raise ValueError("immutable corpus changed")
    library.retain(SimpleNamespace(id=record_id, content=source_text, content_summary="",
        content_hash=corpus["source_text_sha256"]), corpus)
    return [dict(corpus_id=record_id, corpus_sha256=digest, **chunk) for chunk in corpus["chunks"]]


def resolve_rgm_document_chunk(library, reference):
    """Resolve an authenticated extraction range, never raw PDF file bytes."""
    record = library.get(reference["corpus_id"])
    if record is None:
        raise ValueError("document corpus missing")
    corpus, text = record["record"], record["content"]
    if (corpus.get("schema") != RGM_CORPUS_VERSION or _rgm_json_hash(corpus) != reference["corpus_sha256"]
        or reference["corpus_id"] != "rgm-corpus-" + reference["corpus_sha256"]
        or hashlib.sha256(text.encode()).hexdigest() != corpus["source_text_sha256"]
        or record["content_hash"] != corpus["source_text_sha256"]):
        raise ValueError("document corpus integrity mismatch")
    chunk = {k:v for k,v in reference.items() if k not in ("corpus_id", "corpus_sha256")}
    if chunk not in corpus["chunks"]:
        raise ValueError("chunk reference is not bound to this corpus")
    result = text[chunk["start"]:chunk["end"]]
    if hashlib.sha256(result.encode()).hexdigest() != chunk["text_sha256"]:
        raise ValueError("resolved chunk checksum mismatch")
    return result


def _align_rgm_pdf_quote(source_text, quote, pdf_text):
    """Locate a quote using independent PDF spacing and unchanged source letters.

    The compact strings only locate a unique contextual span. Acceptance still
    requires the quote's word boundaries in the independent PDF extraction.
    Never use this helper with model-generated or unverified reference text.
    """
    import re

    def compact(text):
        positions = [i for i, c in enumerate(text) if not c.isspace()]
        return "".join(text[i] for i in positions), positions

    src, src_positions = compact(source_text)
    proposed, _ = compact(quote)
    pdf, pdf_positions = compact(pdf_text)
    if not proposed or src.count(proposed) != 1:
        raise ValueError("spacing repair requires one source occurrence")
    start = src.index(proposed); end = start + len(proposed)
    # Context authenticates location, not merely the existence of the same
    # letters somewhere in the document. At least 32 context characters needed.
    left, right = max(0, start - 64), min(len(src), end + 64)
    if start - left + right - end < 32:
        raise ValueError("insufficient source context for spacing repair")
    anchor = src[left:right]
    if pdf.count(anchor) != 1:
        raise ValueError("source context is absent or ambiguous in the PDF")
    pdf_start = pdf.index(anchor) + start - left
    pdf_end = pdf_start + len(proposed)
    a, b = pdf_positions[pdf_start], pdf_positions[pdf_end - 1] + 1
    original_start, original_end = src_positions[start], src_positions[end - 1] + 1
    if (" ".join(pdf_text[a:b].split()) != " ".join(quote.split())
        or (a and pdf_text[a-1].isalnum() and pdf_text[a].isalnum())
        or (b < len(pdf_text) and pdf_text[b-1].isalnum() and pdf_text[b].isalnum())):
        raise ValueError("quote word boundaries differ from the PDF")
    return dict(start=original_start, end=original_end,
        pdf_text_start=a, pdf_text_end=b, pdf_quote=pdf_text[a:b],
        context_chars=start-left+right-end,
        policy="unique source span plus 64-character flanks; PDF word boundaries required")


def make_rgm_pdf_quote_resolver(pdf_path, expected_sha256):
    """Optional read-only PDF spacing check; does not rewrite the corpus.

    Requires pdfplumber in the caller's environment. Failure remains a quotation
    refusal. This callable belongs to the source layer, never the language model.
    """
    import io
    import pdfplumber
    data = Path(pdf_path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("spacing verification PDF checksum mismatch")
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    text = "\n".join(pages)
    proof = dict(source_pdf=str(pdf_path), source_pdf_sha256=expected_sha256,
        extractor="pdfplumber", extractor_version=pdfplumber.__version__,
        pdf_text_sha256=hashlib.sha256(text.encode()).hexdigest())

    def resolve(source, quote):
        provenance = (source.get("provenance") or {}).get("provenance") or {}
        if provenance.get("source_pdf_sha256") != expected_sha256:
            raise ValueError("source is not bound to the verified PDF")
        aligned = _align_rgm_pdf_quote(source["text"], quote, text)
        page = 1; cursor = 0
        while page < len(pages) and aligned["pdf_text_start"] >= cursor + len(pages[page-1]) + 1:
            cursor += len(pages[page-1]) + 1; page += 1
        return dict(aligned, **proof, pdf_page=page)

    return resolve


def build_rgm_evidence_context(library, selected_memories, references_by_source, *, max_context_chars=None,
                               original_anchors_by_source=None):
    """Restore selected document chunks for evidence checking and answer context.

    references_by_source is the ingestion-owned (document ID, chunk ID) registry
    of retained corpus references. Retrieval excerpts are never evidence here.
    Preserve candidate order and scores; resolve only the selected source ranges.
    If a caller supplies a context budget, refuse overflow instead of cutting text
    or dropping candidates. This function establishes source integrity, not that
    a passage answers the question. Optional original_anchors_by_source is the
    trusted pre-fusion ingestion registry, keyed by (document ID, chunk ID).
    Only the diagnosed vector-only omission can recover references from it;
    malformed/present references are never replaced.
    """
    if max_context_chars is not None and (type(max_context_chars) is not int or max_context_chars < 1):
        raise ValueError("positive context budget required")
    restored, blocks = [], []
    for memory in selected_memories:
        sources = memory.get("source_refs")
        recovery = None
        if ("source_refs" not in memory and memory.get("source") == "vector_only"
            and original_anchors_by_source is not None):
            tags = memory.get("semantic_tags")
            if not isinstance(tags, (list, tuple, set)) or not all(isinstance(t, str) for t in tags):
                raise ValueError("vector-only candidate has invalid document tags")
            documents = {t[4:] for t in tags if t.startswith("DOC:")}
            if len(documents) != 1 or "" in documents or memory.get("anchor_type") != "reference_doc":
                raise ValueError("vector-only candidate requires one document identity")
            key = (next(iter(documents)), memory.get("id"))
            anchor = original_anchors_by_source.get(key)
            if (not isinstance(anchor, dict) or anchor.get("id") != memory.get("id")
                or anchor.get("anchor_type") != "reference_doc"
                or memory.get("content") != anchor.get("content")):
                raise ValueError("vector-only candidate differs from original document anchor")
            sources = anchor.get("source_refs")
            if (not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict)
                or (sources[0].get("doc_id"), sources[0].get("chunk_id")) != key):
                raise ValueError("original document anchor has no unique source binding")
            recovery = dict(method="original_document_anchor", doc_id=key[0], chunk_id=key[1])
        if not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict):
            raise ValueError("selected document chunk requires one source reference")
        source = sources[0]
        doc_id, chunk_id = source.get("doc_id"), source.get("chunk_id")
        if not isinstance(doc_id, str) or not doc_id or not isinstance(chunk_id, str) or memory.get("id") != chunk_id:
            raise ValueError("selected document identity mismatch")
        reference = references_by_source.get((doc_id, chunk_id))
        if reference is None:
            raise ValueError("selected document source is not registered")
        if (reference.get("chunk_id") != chunk_id
            or any(source.get(k) != reference.get(k) for k in ("start", "end"))
            or source.get("source_text_sha256") != reference.get("text_sha256")):
            raise ValueError("selected document source binding mismatch")
        text = resolve_rgm_document_chunk(library, reference)
        if recovery is not None and memory.get("content") != text:
            raise ValueError("vector-only content differs from authenticated full source")
        corpus = library.get(reference["corpus_id"])["record"]
        evidence_reference = dict(doc_id=doc_id, **reference, provenance=corpus["provenance"])
        # Native retrieval metadata can include sets; preserve its types and
        # keep the payload independent of the caller's mutable source registry.
        item = copy.deepcopy(dict(memory, content=text, evidence_reference=evidence_reference))
        if recovery is not None:
            item.update(source_refs=copy.deepcopy(sources), source_reference_recovery=recovery)
        restored.append(item)
        label = json.dumps(evidence_reference, ensure_ascii=False, sort_keys=True)
        blocks.append(f"Source: {label}\n{text}")
    context = "## Retrieved source evidence\n\n" + "\n\n".join(blocks) if blocks else ""
    if max_context_chars is not None and len(context) > max_context_chars:
        raise ValueError(f"complete source context requires {len(context)} characters; budget is {max_context_chars}")
    return dict(memories=restored, context=context, source_count=len(restored),
                source_chars=sum(len(m["content"]) for m in restored), context_chars=len(context))


DOCUMENT_CHUNKING_VERSION = "minilm-document-token-sentence-max188-overlap32/1.1"
SUPPORTED_DOCUMENT_CHUNKING_VERSIONS = frozenset({
    "minilm-document-token-sentence-max192-overlap32/1.0",
    DOCUMENT_CHUNKING_VERSION,
})
DOCUMENT_EMBEDDING_VERSION = EMBEDDING_VERSION
DOCUMENT_WORKER_PROTOCOL = "tom-assist-document-embedding/1.0"
DOCUMENT_PACKET_ADMISSION_VERSION = "minilm-document-hybrid-packet-admission/1.8"
DOCUMENT_RESEARCH_CURSOR_VERSION = "tom-assist-document-research-cursor/1.0"
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
BROAD_DOCUMENT_RESEARCH_BATCH_SIZE = 128
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
    r"\b(?P<actor>the\s+Principal\s+and\s+the\s+(?:SCAW\s+)?Contractor|"
    r"the\s+SCAW\s+Contractor\s+and\s+the\s+Principal|"
    r"the\s+SCAW\s+Contractor|SCAW\s+Contractor|the\s+Contractor|Contractor|"
    r"the\s+Principal|Principal|the\s+parties|parties|a\s+party|party)\b"
    r"(?!['’]s)"
    r"[^.;]{0,120}?\b(?:must|may\s+not|shall|will\s+not|"
    r"(?:is|are|will(?:\s+also)?)\s+be\s+required\s+to|acknowledges?\s+that)\b",
    re.IGNORECASE,
)
_EXPLICIT_ACTOR_SURFACE = re.compile(
    r"\b(?P<actor>the\s+Principal\s+and\s+the\s+(?:SCAW\s+)?Contractor|"
    r"the\s+SCAW\s+Contractor\s+and\s+the\s+Principal|"
    r"the\s+SCAW\s+Contractor|SCAW\s+Contractor|the\s+Contractor|Contractor|"
    r"the\s+Principal|Principal|the\s+parties|parties|a\s+party|party)\b"
    r"(?!['’]s)",
    re.IGNORECASE,
)
_GOVERNING_COLON_ACTOR = re.compile(
    r"\b(?P<actor>the\s+SCAW\s+Contractor|SCAW\s+Contractor|the\s+Contractor|Contractor|"
    r"the\s+Principal|Principal|the\s+parties|parties|a\s+party|party)\s*:\s*$",
    re.IGNORECASE,
)
_GOVERNING_PRONOUN_ACTOR = re.compile(
    r"\b(?P<actor>the\s+(?:SCAW\s+)?Contractor|(?:SCAW\s+)?Contractor|"
    r"the\s+Principal|Principal|the\s+parties|parties)\b"
    r"(?!['’]s)"
    r".{0,600}?\b(?:it|they)\s+must\b",
    re.IGNORECASE | re.DOTALL,
)
_ACKNOWLEDGEMENT_FRAME = re.compile(
    r"\backnowledg(?:e|es|ed|ing)\s+that\b",
    re.IGNORECASE,
)
_DEONTIC_MODAL = re.compile(
    r"\b(?:must|shall|may\s+not|will\s+not)\b",
    re.IGNORECASE,
)
_BASELINE_TEMPORAL_PREFIX = re.compile(
    r"\b(?:state|condition|position|status|level|baseline)\b"
    r"[^.;:]{0,180}\b(?:agreed|existing|prevailing|was|were)\b[^.;:]{0,100}$",
    re.IGNORECASE | re.DOTALL,
)
_AUTHORED_BOUNDARY_INSIDE_MATCH = re.compile(
    r"\n[ \t]*\n[ \t]*(?:\([A-Za-z0-9]{1,5}\)|"
    r"[0-9]{1,3}(?:\.[0-9]{1,3}[A-Z]?)+)[ \t]+",
)
_PRESTART_EVENT_TERMS = re.compile(
    r"\b(?:construction|work|activities|access|performance|obligations?|rights?)\b",
    re.IGNORECASE,
)


def _actor_role(value):
    folded = " ".join(value.casefold().split())
    if "contractor" in folded and "principal" in folded:
        return "parties"
    if "contractor" in folded:
        return "contractor"
    if "principal" in folded:
        return "principal"
    if "part" in folded:
        return "parties"
    return "unknown"


def _nearest_authored_modal_actor(text, before):
    """Return the explicit subject nearest the last deontic modal.

    Actor names occurring as conditions or objects before a later subject must
    not capture that subject.  For example, in "if requested by the Principal,
    the Contractor must ... before work", the Contractor governs ``must``.
    """
    modals = [match for match in _DEONTIC_MODAL.finditer(text, 0, before)]
    for modal in reversed(modals):
        boundary = max(
            text.rfind(".", 0, modal.start()),
            text.rfind(";", 0, modal.start()),
            text.rfind("\n\n", 0, modal.start()),
        )
        actors = list(_EXPLICIT_ACTOR_SURFACE.finditer(
            text, max(boundary + 1, modal.start() - 600), modal.start(),
        ))
        if actors:
            actor = actors[-1].group("actor")
            return _actor_role(actor), actor
    return "unknown", None


def _relation_actor(text, start, end):
    paragraph_start = text.rfind("\n\n", 0, start)
    paragraph_end = text.find("\n\n", start)
    window_start = max(0, paragraph_start + 2 if paragraph_start >= 0 else start - 280)
    window_end = min(
        len(text), paragraph_end if paragraph_end >= 0 else end + 280,
    )
    window = text[window_start:window_end]
    modal_role, modal_actor = _nearest_authored_modal_actor(
        window, max(0, start - window_start),
    )
    if modal_actor is not None:
        return modal_role, modal_actor
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


def _relation_exclusion_reason(text, relation, match):
    """Reject a temporal phrase that does not govern a pre-start duty.

    The rules use only authored grammar around the exact match.  They do not
    infer legal meaning, and each rejection has a stable diagnostic code.
    """
    matched = match.group(0)
    paragraph_start = text.rfind("\n\n", 0, match.start())
    frame_start = paragraph_start + 2 if paragraph_start >= 0 else max(0, match.start() - 320)
    prefix = text[frame_start:match.start()]

    if relation in {"before_access_or_work", "unless_until_commencement"}:
        orientation = re.search(
            r"\b(?:before|unless\s+and\s+until)\b", matched, re.IGNORECASE,
        )
        event = (
            _PRESTART_EVENT_TERMS.search(matched, orientation.end())
            if orientation is not None else None
        )
        core = matched[:event.end()] if event is not None else matched
        if _AUTHORED_BOUNDARY_INSIDE_MATCH.search(core):
            return "EXCLUDED_RELATION_CROSSES_AUTHORED_BOUNDARY"

    acknowledgement = list(_ACKNOWLEDGEMENT_FRAME.finditer(prefix))
    if acknowledgement:
        last_acknowledgement = acknowledgement[-1]
        if not _DEONTIC_MODAL.search(prefix, last_acknowledgement.end()):
            return "EXCLUDED_ACKNOWLEDGEMENT_NOT_DUTY"

    if relation in {"prior_to_commencing", "before_access_or_work"}:
        baseline_prefix = text[max(frame_start, match.start() - 320):match.start()]
        if _BASELINE_TEMPORAL_PREFIX.search(baseline_prefix):
            return "EXCLUDED_BASELINE_OR_REFERENCE_TIME"

    if relation == "noncommencement_until":
        commence = re.search(r"\bcommence\b", matched, re.IGNORECASE)
        until = re.search(r"\b(?:until|unless)\b", matched, re.IGNORECASE)
        subject_start = max(frame_start, match.start() - 180)
        target_end = match.end() if until is None else match.start() + until.start()
        if commence is not None:
            target_window = text[subject_start:target_end]
            if not _PRESTART_EVENT_TERMS.search(target_window):
                return "EXCLUDED_NONCONSTRUCTION_TEMPORAL_TARGET"

    return None


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
            exclusion_reason = _relation_exclusion_reason(
                text, relation, match,
            )
            if exclusion_reason is None and excluded_post_start:
                exclusion_reason = "EXCLUDED_POST_START_COMPLETION_WARRANTY"
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
                "decision": "excluded" if exclusion_reason else "included",
                "reason_code": exclusion_reason or "INCLUDED_TEMPORAL_RELATION",
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
    project_gates = [
        row for row in rows
        if row["decision"] == "included"
        and row["relation"] == "parties_commencement_condition"
    ]
    for row in rows:
        if row["decision"] != "included" or row in project_gates:
            continue
        if any(gate["start"] <= row["start"] < gate["end"] for gate in project_gates):
            row["decision"] = "excluded"
            row["reason_code"] = "EXCLUDED_WEAKER_RELATION_INSIDE_PROJECT_GATE"
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


def _explicit_contractor_support(source, unit, relations):
    """Resolve the nearest authored subject governing the matched relation."""
    structure = source.get("declared_structure") or {}
    by_id, _ = entry_maps(structure)
    source_text = str(source["content"])
    relation_entry = by_id.get(str(unit.get("relation_entry_id") or ""))
    if relation_entry is None:
        relation_entry = by_id.get(str(unit.get("entry_id") or ""))
    relation_end = min(
        int(unit.get("relation_absolute_end") or unit["end"]),
        int(relation_entry["span"]["end"]) if relation_entry else int(unit["end"]),
    )
    relation_start = (
        int(relation_entry["span"]["start"]) if relation_entry else int(unit["start"])
    )
    relation_text = source_text[relation_start:relation_end]
    role, actor = _nearest_authored_modal_actor(
        relation_text, len(relation_text),
    )
    if actor is not None:
        return role in {"contractor", "parties"}, {
            "kind": "same_relation_unit_nearest_modal_subject", "role": role,
            "entry_id": str(
                (relation_entry or {}).get("entry_id") or unit.get("entry_id") or ""
            ),
        }

    explicit_roles = {
        str(row.get("actor_role") or "unknown") for row in relations
        if row.get("actor_role") != "unknown"
    }
    if explicit_roles & {"contractor", "parties"}:
        return True, {"kind": "relation_actor", "roles": sorted(explicit_roles)}
    if "principal" in explicit_roles:
        return False, {"kind": "relation_actor", "roles": sorted(explicit_roles)}

    children_by_parent = {}
    for entry in by_id.values():
        parent_id = str(entry.get("parent_entry_id") or "")
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(entry)
    current = relation_entry
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
        children = children_by_parent.get(parent_id, [])
        lead_end = min(
            (int(child["span"]["start"]) for child in children),
            default=int(parent["span"]["end"]),
        )
        lead = source_text[parent_start:lead_end]
        candidates = [
            (match.start(), match.group("actor"), "authored_parent_modal")
            for match in _OBLIGATION_ACTOR.finditer(lead)
        ]
        candidates.extend(
            (match.start(), match.group("actor"), "authored_parent_colon")
            for match in _GOVERNING_COLON_ACTOR.finditer(lead)
        )
        candidates.extend(
            (match.start(), match.group("actor"), "authored_parent_pronoun_modal")
            for match in _GOVERNING_PRONOUN_ACTOR.finditer(lead)
        )
        if candidates:
            _, actor, kind = max(candidates, key=lambda item: item[0])
            role = _actor_role(actor)
            return role in {"contractor", "parties"}, {
                "kind": kind, "role": role,
                "entry_id": parent_id,
            }
        current = parent
    return False, {"kind": "none", "role": "unknown"}


def _malformed_numbering_in_unit(source, unit):
    """Return a fail-closed structural issue without exposing source prose."""
    structure = source.get("declared_structure") or {}
    index = structure.get("clause_index") if isinstance(structure, dict) else None
    entries = index.get("entries", []) if isinstance(index, dict) else []
    source_segments = unit.get("source_segments") or [{
        "start": int(unit["start"]), "end": int(unit["end"]),
    }]
    child_counts = {}
    for entry in entries:
        if isinstance(entry, dict):
            parent_id = str(entry.get("parent_entry_id") or "")
            if parent_id:
                child_counts[parent_id] = child_counts.get(parent_id, 0) + 1
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("span"), dict):
            continue
        start, end = int(entry["span"]["start"]), int(entry["span"]["end"])
        if not any(
            int(segment["start"]) <= start < end <= int(segment["end"])
            for segment in source_segments
        ):
            continue
        label = str(entry.get("display_identifier") or "")
        token_match = re.fullmatch(r"\(([A-Za-z]+)\)", label)
        mixed_case_label = bool(
            token_match
            and not token_match.group(1).islower()
            and not token_match.group(1).isupper()
        )
        if mixed_case_label and child_counts.get(str(entry.get("entry_id") or ""), 0):
            return {
                "entry_id": str(entry.get("entry_id") or ""),
                "identifier": str(entry.get("identifier") or ""),
                "reason_code": "MIXED_CASE_ENUMERATOR",
            }
    return None


def _evidence_unit_text(source, unit):
    segments = unit.get("source_segments") or [{
        "start": int(unit["start"]), "end": int(unit["end"]),
        "role": "authored_unit",
    }]
    content = str(source["content"])
    return "\n\n".join(
        content[int(segment["start"]):int(segment["end"])]
        for segment in segments
    )


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
    result["_evidence_unit"]["relation_absolute_start"] = absolute_position
    result["_evidence_unit"]["relation_absolute_end"] = (
        int(row["start"]) + int(relations[0]["end"])
    )
    result["_relation_witnesses"] = [
        {
            **{
                key: value for key, value in relation.items()
                if key not in {"text_sha256"}
            },
            "absolute_start": int(row["start"]) + int(relation["start"]),
            "absolute_end": int(row["start"]) + int(relation["end"]),
            "source_text_sha256": relation.get("text_sha256"),
            "origin_candidate_id": row["id"],
        }
        for relation in relations
    ]
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


def _expanded_prestart_packet_rows(
    ranked, document_sources, query_text, *, reference_inventory=None,
):
    """Expand direct hits and one-hop declared links into authored units."""
    direct = _prestart_packet_order(ranked)
    reference_inventory = reference_inventory or ranked
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
        if unit.get("oversize") is True:
            expansion_trace.append({
                "candidate_id": materialized["id"],
                "document_id": materialized["document_id"],
                "clause_identifier": unit["identifier"],
                "unit_start": unit["start"],
                "unit_end": unit["end"],
                "unit_char_count": unit["char_count"],
                "source_segments": unit.get("source_segments", []),
                "linked_from": linked_from,
                "decision": "EXCLUDED_COMPOSITE_EVIDENCE_UNIT_TOO_LARGE",
            })
            return None
        unit_text = _evidence_unit_text(
            document_sources[materialized["document_id"]], unit,
        )
        normalized_unit = " ".join(unit_text.split()).casefold()
        unit_content_sha256 = "sha256:" + hashlib.sha256(
            normalized_unit.encode("utf-8")
        ).hexdigest()
        materialized["_unit_content_sha256"] = unit_content_sha256
        numbering_issue = _malformed_numbering_in_unit(
            document_sources[materialized["document_id"]], unit,
        )
        if numbering_issue is not None:
            expansion_trace.append({
                "candidate_id": materialized["id"],
                "document_id": materialized["document_id"],
                "clause_identifier": unit["identifier"],
                "unit_start": unit["start"],
                "unit_end": unit["end"],
                "unit_content_sha256": unit_content_sha256,
                "linked_from": linked_from,
                "numbering_issue": numbering_issue,
                "decision": "EXCLUDED_MALFORMED_AUTHORED_NUMBERING",
            })
            return None
        actor_supported, actor_support = _explicit_contractor_support(
            document_sources[materialized["document_id"]],
            unit,
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
            existing = seen[identity]
            witnesses = {
                (
                    item["absolute_start"], item["absolute_end"],
                    item["relation"],
                ): item
                for item in existing.get("_relation_witnesses", [])
            }
            for item in materialized.get("_relation_witnesses", []):
                witnesses.setdefault((
                    item["absolute_start"], item["absolute_end"],
                    item["relation"],
                ), item)
            existing["_relation_witnesses"] = [
                witnesses[key] for key in sorted(witnesses)
            ]
            dedup_trace.append({
                "candidate_id": materialized["id"],
                "kept_candidate_id": existing["id"],
                "document_id": materialized["document_id"],
                "clause_identifier": unit["identifier"],
                "unit_start": unit["start"],
                "unit_end": unit["end"],
                "unit_content_sha256": unit_content_sha256,
                "reason_code": "DEDUP_SAME_NORMALIZED_AUTHORED_UNIT",
            })
            return existing
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
            "source_segments": unit.get("source_segments", []),
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

    # Expand only authored units actually touched by a retrieved Tree hit.
    # A receipt elsewhere in this project's inventory is not query retrieval.
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
        document_ranked = [
            row for row in ranked if row["document_id"] == document_id
        ]
        unit_witnesses = {}
        for entry in entries:
            entry_start = int(entry["span"]["start"])
            entry_end = int(entry["span"]["end"])
            witness = next((
                row for row in document_ranked
                if int(row["start"]) < entry_end and int(row["end"]) > entry_start
            ), None)
            if witness is not None:
                unit_witnesses[str(entry.get("entry_id") or "")] = witness
        for entry in entries:
            if entry.get("kind") not in {"clause", "subclause"}:
                continue
            unit_start = int(entry["span"]["start"])
            unit_end = int(entry["span"]["end"])
            if unit_end <= unit_start:
                continue
            witness = unit_witnesses.get(str(entry.get("entry_id") or ""))
            if witness is None:
                authored_unit_trace.append({
                    "document_id": document_id,
                    "entry_id": str(entry.get("entry_id") or ""),
                    "clause_identifier": str(entry.get("identifier") or ""),
                    "unit_start": unit_start, "unit_end": unit_end,
                    "decision": "EXCLUDED_NO_TREE_RETRIEVED_UNIT_WITNESS",
                    "admitted_candidate_ids": [],
                })
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
                "recall_basis": "tree_retrieved_authored_unit_expansion",
                "retrieval_witness_candidate_id": witness["id"],
                "document_tree_address": witness["document_tree_address"],
                "admitted_candidate_ids": [],
                "decision": (
                    "RETAINED_DIRECT_AUTHORED_TEMPORAL_DUTY"
                    if relations else "EXCLUDED_DIRECT_AUTHORED_ACTOR_MISMATCH"
                ),
            }
            for relation in relations:
                absolute = unit_start + int(relation["start"])
                ranked_row = _ranked_row_at_position(ranked, document_id, absolute) or witness
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

    # Traverse resolved authored references with a small, explicit bound.
    # References never become evidence by themselves: a target must carry its
    # own qualifying temporal duty.  Cycles and duplicate edges remain visible.
    targets_by_identifier = {}
    for target_document_id, target_source in document_sources.items():
        _, target_identifiers = entry_maps(
            target_source.get("declared_structure") or {},
        )
        for identifier, entry in target_identifiers.items():
            targets_by_identifier.setdefault(identifier, []).append((
                target_document_id, target_source, entry,
            ))
    reference_queue = [(row, 0, ()) for row in list(expanded)]
    followed_edges = set()
    queued_units = set()
    while reference_queue:
        source_row, depth, path = reference_queue.pop(0)
        source = document_sources[source_row["document_id"]]
        unit = source_row["_evidence_unit"]
        source_unit_key = (
            source_row["document_id"], int(unit["start"]), int(unit["end"]),
        )
        queue_identity = (source_unit_key, path)
        if queue_identity in queued_units:
            continue
        queued_units.add(queue_identity)
        source_segments = unit.get("source_segments") or [{
            "start": unit["start"], "end": unit["end"],
        }]
        direct_refs = []
        term_refs = []
        for segment in source_segments:
            direct_refs.extend(references_touching_span(
                source, segment["start"], segment["end"],
            ))
            term_refs.extend(defined_term_reference_rows(
                source, segment["start"], segment["end"],
            ))
        refs = [(row, "direct_clause_reference") for row in direct_refs]
        refs += [(row, "defined_term_definition") for row in term_refs]
        unique_refs = {}
        for reference, via in refs:
            key = str(reference.get("reference_id") or f"{via}:{reference.get('span')}")
            unique_refs.setdefault(key, (reference, via))
        for key in sorted(unique_refs):
            reference, via = unique_refs[key]
            safe = safe_reference_record(reference, via=via)
            edge_key = (source_unit_key, safe["reference_id"], safe["named_identifier"])
            duplicate_edge = edge_key in followed_edges
            followed_edges.add(edge_key)
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
            candidates = targets_by_identifier.get(target_identifier, [])
            local = [
                row for row in candidates if row[0] == source_row["document_id"]
            ]
            targets = local or candidates
            if len(targets) != 1:
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_candidate_count": len(targets),
                    "decision": (
                        "RESOLVED_REFERENCE_TARGET_NOT_ADDRESSABLE"
                        if not targets else "RESOLVED_REFERENCE_TARGET_AMBIGUOUS"
                    ),
                })
                continue
            target_document_id, target_source, target = targets[0]
            target_start = int(target["span"]["start"])
            target_end = int(target["span"]["end"])
            target_unit_key = (target_document_id, target_start, target_end)
            if target_unit_key in (*path, source_unit_key):
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_document_id": target_document_id,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "decision": "REFERENCE_CYCLE_DETECTED",
                })
                continue
            if duplicate_edge:
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_document_id": target_document_id,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "decision": "DUPLICATE_REFERENCE_EDGE",
                })
                continue
            if depth >= 7:
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_document_id": target_document_id,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "decision": "REFERENCE_TRAVERSAL_DEPTH_LIMIT",
                })
                continue
            if target_end - target_start > MAX_COMPOSITE_EVIDENCE_UNIT_CHARS:
                # A precise parent is a legitimate authored target, but the
                # outgoing evidence boundary remains finite.  Record the target
                # as unresolved-at-budget rather than guessing one child.
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_document_id": target_document_id,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "target_char_count": target_end - target_start,
                    "decision": "RESOLVED_REFERENCE_TARGET_EXCEEDS_BOUNDED_UNIT",
                })
                continue
            target_text = str(target_source["content"])[target_start:target_end]
            target_scan = scan_prestart_relations(target_text)
            target_relations = _apply_query_relation_filters(target_scan, query_text)
            if not target_relations:
                link_trace.append({
                    "source_candidate_id": source_row["id"],
                    **safe,
                    "target_document_id": target_document_id,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "decision": "RESOLVED_TARGET_HAS_NO_QUALIFYING_TEMPORAL_DUTY",
                })
                continue
            for relation in target_relations:
                absolute = target_start + int(relation["start"])
                ranked_row = _ranked_row_at_position(
                    reference_inventory, target_document_id, absolute,
                )
                if ranked_row is None:
                    link_trace.append({
                        "source_candidate_id": source_row["id"],
                        **safe,
                        "target_document_id": target_document_id,
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
                    "target_document_id": target_document_id,
                    "target_identifier": target_identifier,
                    "target_start": target_start,
                    "target_end": target_end,
                    "target_candidate_id": ranked_row["id"],
                    "target_clause_identifier": (
                        admitted["_evidence_unit"]["identifier"] if admitted else None
                    ),
                    "decision": "ADMITTED_LINKED_TEMPORAL_DUTY",
                })
                if admitted is not None:
                    reference_queue.append((
                        admitted, depth + 1, (*path, source_unit_key),
                    ))
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
    document_sources=None, return_trace=False, processing_cursor=None,
    cursor_auth_key=None,
):
    """Return bounded, exact source excerpts from immutable active chunks."""
    if type(k) is not int or k <= 0:
        raise ValueError("document packet k must be a positive integer")
    if type(max_chars) is not int or max_chars <= 0:
        raise ValueError("document packet max_chars must be a positive integer")
    if structural_scores is not None and not isinstance(structural_scores, dict):
        raise ValueError("document structural scores must be an object")
    ranked = []
    tree_retrieval_trace = []
    relation_filter_trace = []
    query_terms = _retrieval_terms(query_text)
    prestart_query = prestart_requirement_query(query_text)
    research_intent = parse_research_intent(query_text)
    broad_document_research = bool(
        prestart_query and research_intent.get("broad_document_research") is True
    )
    ordered_chunks = list(document_chunks)
    ordinary_tree_selection = structural_scores is not None and not broad_document_research
    if structural_scores is not None:
        for row in ordered_chunks:
            row_id = f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
            score = structural_scores.get(row_id)
            if not isinstance(score, dict) or type(score.get("native_rank")) is not int:
                raise ValueError("every indexed document chunk requires a native Tree rank")
            if (
                score["native_rank"] < 1
                or not isinstance(score.get("matched_branch_id"), str)
                or not score["matched_branch_id"]
                or not math.isfinite(float(score.get("score", float("nan"))))
            ):
                raise ValueError("every indexed document chunk requires a valid native Tree result")
        ordered_chunks.sort(key=lambda row: (
            int(structural_scores[
                f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
            ]["native_rank"]),
            str(row["document_id"]), int(row["chunk_index"]),
        ))
    processing_snapshot_identity = "sha256:" + hashlib.sha256(json.dumps(
        {
            "tree_digest": (structural_telemetry or {}).get("tree_digest"),
            "query_region_identity": (
                structural_telemetry or {}
            ).get("query_region_identity"),
            "query_sha256": research_intent["query_sha256"],
            "requested_k": k,
            "requested_max_chars": max_chars,
            "candidate_ids": [
                f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
                for row in ordered_chunks
            ],
            "source_digests": sorted(
                str(source.get("content_sha256") or "")
                for source in (document_sources or {}).values()
            ),
            "admission_version": DOCUMENT_PACKET_ADMISSION_VERSION,
            "trace_version": DOCUMENT_RESEARCH_TRACE_VERSION,
        },
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()

    cached_candidates = []
    processing_start = 0
    if processing_cursor is not None:
        if not broad_document_research:
            raise ValueError("document research cursor is only valid for broad research")
        if not isinstance(processing_cursor, str) or processing_cursor.count(".") != 1:
            raise ValueError("document research cursor shape mismatch")
        if not isinstance(cursor_auth_key, bytes) or len(cursor_auth_key) != 32:
            raise ValueError("document research cursor authentication is unavailable")
        encoded_cursor, supplied_auth_tag = processing_cursor.split(".", 1)
        try:
            cursor_bytes = base64.urlsafe_b64decode(encoded_cursor.encode("ascii"))
        except (ValueError, binascii.Error, UnicodeError):
            raise ValueError("document research cursor encoding is invalid") from None
        expected_auth_tag = hmac.new(
            cursor_auth_key, cursor_bytes, hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(supplied_auth_tag, expected_auth_tag):
            raise ValueError("document research cursor authentication failed")
        try:
            decoded_cursor = json.loads(cursor_bytes)
        except (json.JSONDecodeError, UnicodeError):
            raise ValueError("document research cursor payload is invalid") from None
        if not isinstance(decoded_cursor, dict) or set(decoded_cursor) != {
            "version", "snapshot_identity", "next_native_rank", "candidates",
        }:
            raise ValueError("document research cursor payload shape mismatch")
        if decoded_cursor["version"] != DOCUMENT_RESEARCH_CURSOR_VERSION:
            raise ValueError("document research cursor version mismatch")
        if decoded_cursor["snapshot_identity"] != processing_snapshot_identity:
            raise ValueError("document research cursor snapshot is stale")
        if type(decoded_cursor["next_native_rank"]) is not int:
            raise ValueError("document research cursor rank is invalid")
        processing_start = decoded_cursor["next_native_rank"] - 1
        if not 0 <= processing_start <= len(ordered_chunks):
            raise ValueError("document research cursor rank is out of range")
        cached_candidates = decoded_cursor["candidates"]
        if not isinstance(cached_candidates, list) or len(cached_candidates) != processing_start:
            raise ValueError("document research cursor candidate count mismatch")
        expected_ids = [
            f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
            for row in ordered_chunks[:processing_start]
        ]
        if [row.get("id") if isinstance(row, dict) else None for row in cached_candidates] != expected_ids:
            raise ValueError("document research cursor candidate prefix mismatch")
    elif not broad_document_research and processing_cursor is not None:
        raise ValueError("bounded document preview does not accept a cursor")

    processing_limit = (
        len(ordered_chunks) if broad_document_research
        else min(DOCUMENT_TREE_SEMANTIC_COHORT, len(ordered_chunks))
        if structural_scores is not None else len(ordered_chunks)
    )
    processing_end = (
        min(processing_limit, processing_start + BROAD_DOCUMENT_RESEARCH_BATCH_SIZE)
        if broad_document_research else processing_limit
    )
    processing_complete = processing_end == processing_limit
    processing_batches = []
    if processing_end:
        for start in range(0, processing_end, BROAD_DOCUMENT_RESEARCH_BATCH_SIZE):
            end = min(processing_limit, start + BROAD_DOCUMENT_RESEARCH_BATCH_SIZE)
            processing_batches.append({
                "batch_ordinal": len(processing_batches) + 1,
                "native_rank_start": start + 1,
                "native_rank_end": end,
                "unit_count": end - start,
            })
    for ordinal, row in enumerate(ordered_chunks, 1):
        row_id = f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
        if structural_scores is not None:
            tree_score = structural_scores.get(row_id)
            if not isinstance(tree_score, dict):
                raise ValueError("every indexed document chunk requires a structural score")
            native_rank = int(tree_score["native_rank"])
            retrieved = (
                bool(tree_score.get("matched_branch_id"))
                and math.isfinite(float(tree_score["score"]))
                and native_rank <= processing_end
            )
            tree_retrieval_trace.append({
                "candidate_id": row_id,
                "document_id": str(row["document_id"]),
                "chunk_index": int(row["chunk_index"]),
                "receipt_analysis_digest": str(row.get("analysis_digest") or ""),
                "matched_branch_id": tree_score.get("matched_branch_id") or None,
                "native_rank": native_rank,
                "native_raw_score": float(tree_score["score"]),
                "query_region_identity": tree_score.get("query_region_identity"),
                "receipt_id": tree_score.get("receipt_id"),
                "receipt_tick_after": tree_score.get("receipt_tick_after"),
                "receipt_batch_tree_digest": tree_score.get("receipt_batch_tree_digest"),
                "routing_basis_names": tree_score.get("routing_basis_names"),
                "routing_vector_norm": tree_score.get("routing_vector_norm"),
                "current_tree_digest": tree_score.get("current_tree_digest"),
                "historical_branch_overlap_count": tree_score.get(
                    "historical_branch_overlap_count", 0,
                ),
                "decision": (
                    "EXAMINED_TREE_NATIVE_COMPREHENSIVE"
                    if retrieved and broad_document_research else
                    "RETRIEVED_TREE_NATIVE_PAGE"
                    if retrieved else
                    "UNEXAMINED_TREE_NATIVE_PAGE_LIMIT"
                ),
            })
    source_rows_by_id = {
        f"{row['document_id']}:chunk:{int(row['chunk_index'])}": row
        for row in ordered_chunks
    }
    for cached in cached_candidates:
        if not isinstance(cached, dict) or set(cached) != {
            "id", "semantic_score", "best_chunk_score", "lexical_score",
            "prestart_relations", "relation_scan", "clause_identifiers",
            "matched_clause_identifier",
        }:
            raise ValueError("document research cursor candidate shape mismatch")
        row = source_rows_by_id[cached["id"]]
        tree_score = structural_scores[cached["id"]]
        ranked.append({
            "id": cached["id"],
            "document_id": str(row["document_id"]),
            "display_name": str(row["display_name"]),
            "chunk_index": int(row["chunk_index"]),
            "start": int(row["start"]),
            "end": int(row["end"]),
            "text": str(row["text"]),
            "text_sha256": str(row["text_sha256"]),
            "semantic_score": float(cached["semantic_score"]),
            "best_chunk_score": float(cached["best_chunk_score"]),
            "lexical_score": float(cached["lexical_score"]),
            "prestart_relations": list(cached["prestart_relations"]),
            "clause_identifiers": list(cached["clause_identifiers"]),
            "matched_clause_identifier": cached["matched_clause_identifier"],
            "document_tree_address": {
                "receipt_analysis_digest": str(row.get("analysis_digest") or ""),
                "branch_ids": [
                    str(branch.get("branch_id") or "")
                    for branch in row.get("address_branches", [])
                    if isinstance(branch, dict) and branch.get("branch_id")
                ],
                "branch_count": len(row.get("address_branches", [])),
                "basis": "pinned_10k_8d17d_document_tree_receipt",
                "query_region_match": tree_score,
            },
            "score_space": "minilm_dense_plus_exact_term_rrf",
            "packet_eligible": True,
            "structural_signature": None,
            "_relation_scan": list(cached["relation_scan"]),
        })
    for row in ordered_chunks[processing_start:processing_end]:
        row_id = f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
        tree_score = structural_scores.get(row_id) if structural_scores is not None else None
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
                "query_region_match": tree_score,
            },
            "score_space": "minilm_dense_plus_exact_term_rrf",
            "packet_eligible": True,
            "structural_signature": None,
            "_relation_scan": relation_scan,
        })
    relation_filter_trace = [
        {
            "candidate_id": row["id"],
            "document_id": row["document_id"],
            "chunk_index": row["chunk_index"],
            "chunk_start": row["start"],
            "chunk_end": row["end"],
            "chunk_text_sha256": row["text_sha256"],
            "relations": redacted_relations(row.get("_relation_scan") or []),
            "decision": (
                "RETAINED_TEMPORAL_CANDIDATE" if row["prestart_relations"]
                else "EXCLUDED_NO_QUALIFYING_TEMPORAL_RELATION"
            ),
        }
        for row in ranked
    ]
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
        for row in ranked:
            score = structural_scores.get(row["id"])
            if not isinstance(score, dict):
                raise ValueError("every indexed document chunk requires a structural score")
            structural_rows.append((
                row["id"], int(score["native_rank"]), float(score["score"]),
                str(score["matched_branch_id"]),
            ))
        structural_rows.sort(key=lambda item: (item[1], item[0]))
        structural_ranks = {
            row_id: (native_rank, score, branch_id)
            for row_id, native_rank, score, branch_id in structural_rows
        }
    for row in ranked:
        structural = structural_ranks.get(row["id"])
        if ordinary_tree_selection:
            # Ordinary retrieval follows the native Tree rank even when its
            # relevance is poor or flat. Semantic measurements are diagnostics,
            # not a replacement selector. Keep the bounded Tree-selected page.
            structural_rank, structural_score, branch_id = structural
            row["rrf_score"] = 1.0 / (DOCUMENT_RRF_K + structural_rank)
            row["structural_rank"] = structural_rank
            row["structural_resonance"] = structural_score
            row["matched_document_branch_id"] = branch_id
            row["structural_channel_informative"] = tree_informative
            row["score_space"] = "native_document_tree_rank"
        elif structural is None or not tree_informative:
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
    reference_inventory = list(ranked)
    if (
        prestart_query
        and (not broad_document_research or processing_complete)
        and structural_scores is not None
        and len(ranked) < len(ordered_chunks)
    ):
        represented = {row["id"] for row in ranked}
        for row in ordered_chunks:
            row_id = f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
            if row_id in represented:
                continue
            tree_score = structural_scores[row_id]
            # This is address-only inventory for following an exact authored
            # reference. It is never scanned for independent candidates and it
            # receives no dense, lexical or relation-derived relevance credit.
            reference_inventory.append({
                "id": row_id,
                "document_id": str(row["document_id"]),
                "display_name": str(row["display_name"]),
                "chunk_index": int(row["chunk_index"]),
                "start": int(row["start"]),
                "end": int(row["end"]),
                "text": str(row.get("text") or ""),
                "text_sha256": str(row["text_sha256"]),
                "semantic_score": 0.0,
                "best_chunk_score": 0.0,
                "lexical_score": 0.0,
                "dense_rank": 0,
                "lexical_rank": None,
                "prestart_relation_rank": None,
                "semantic_hybrid_rank": 0,
                "semantic_hybrid_score": 0.0,
                "prestart_relations": [],
                "rrf_score": 1.0 / (DOCUMENT_RRF_K + int(tree_score["native_rank"])),
                "structural_rank": int(tree_score["native_rank"]),
                "structural_resonance": float(tree_score["score"]),
                "matched_document_branch_id": tree_score.get("matched_branch_id"),
                "structural_channel_informative": True,
                "document_tree_address": {
                    "receipt_analysis_digest": str(row.get("analysis_digest") or ""),
                    "branch_ids": [
                        str(branch.get("branch_id") or "")
                        for branch in row.get("address_branches", [])
                        if isinstance(branch, dict) and branch.get("branch_id")
                    ],
                    "branch_count": len(row.get("address_branches", [])),
                    "basis": "pinned_10k_8d17d_document_tree_receipt",
                    "query_region_match": tree_score,
                    "lookup_role": "exact_authored_reference_target",
                },
                "score_space": "exact_reference_target_no_independent_relevance_score",
                "packet_eligible": True,
            })
    if (
        prestart_query
        and document_sources is not None
        and (not broad_document_research or processing_complete)
    ):
        packet_rows, expansion_trace = _expanded_prestart_packet_rows(
            ranked, document_sources, query_text,
            reference_inventory=reference_inventory,
        )
    elif broad_document_research and not processing_complete:
        packet_rows = []
        expansion_trace["partial_disposition"] = (
            "AUTHORED_UNIT_EXPANSION_DEFERRED_UNTIL_SNAPSHOT_COMPLETE"
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
            source_segments = unit.get("source_segments") or [{
                "start": int(unit["start"]), "end": int(unit["end"]),
                "role": "authored_unit",
            }]
            relative_start = min(int(row["start"]) for row in source_segments)
            relative_end = max(int(row["end"]) for row in source_segments)
            excerpt = _evidence_unit_text(source, unit)
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
            "source_segments": [
                {
                    "start": int(segment["start"]),
                    "end": int(segment["end"]),
                    "role": str(segment.get("role") or "authored_unit"),
                    "entry_id": str(segment.get("entry_id") or ""),
                    "identifier": str(segment.get("identifier") or ""),
                }
                for segment in (
                    source_segments if unit is not None else [{
                        "start": excerpt_start,
                        "end": excerpt_end,
                        "role": "chunk_excerpt",
                    }]
                )
            ],
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
            "source_segments": admitted[-1]["source_segments"],
            "decision": "ADMITTED_GATEWAY_PACKET_CANDIDATE",
        })

    if not return_trace:
        return admitted
    selected_ids = {row["id"] for row in admitted}
    discovered = []
    for row in packet_rows:
        unit = row.get("_evidence_unit") or {}
        witnesses = row.get("_relation_witnesses") or []
        classifications = set()
        for witness in witnesses:
            if witness.get("conditionality") == "project_wide":
                classifications.add("project_wide_commencement_prerequisite")
            else:
                classifications.add("activity_or_location_specific_prerequisite")
            if witness.get("relation") == "access_withheld_until":
                classifications.add("site_or_access_condition")
            if witness.get("relation") in {
                "noncommencement_until", "unless_until_commencement",
                "condition_precedent_to_start", "deadline_prerequisite",
            }:
                classifications.add("timing_condition_or_exception")
        discovered.append({
            "evidence_id": row["id"],
            "origin_candidate_id": row.get("_origin_candidate_id", row["id"]),
            "document_id": row["document_id"],
            "clause_identifier": row.get("matched_clause_identifier"),
            "unit_start": unit.get("start", row["start"]),
            "unit_end": unit.get("end", row["end"]),
            "source_segments": unit.get("source_segments", []),
            "relation_types": sorted({
                item["relation"] for item in witnesses
            }),
            "conditionality": sorted({
                item["conditionality"] for item in witnesses
            }),
            "source_digests": sorted({
                item["source_text_sha256"] for item in witnesses
                if item.get("source_text_sha256")
            }),
            "document_tree_address": row.get("document_tree_address", {}),
            "actor_support": row.get("_actor_support", {}),
            "classifications": sorted(classifications),
            "requirement_components": [
                {
                    "relation": witness.get("relation"),
                    "actor_role": witness.get("actor_role"),
                    "conditionality": witness.get("conditionality"),
                    "source_start": witness.get("absolute_start"),
                    "source_end": witness.get("absolute_end"),
                    "source_text_sha256": witness.get("source_text_sha256"),
                    "origin_candidate_id": witness.get("origin_candidate_id"),
                }
                for witness in witnesses
            ],
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
    ranked_by_native_id = {row["id"]: row for row in ranked}
    continuation = None
    if broad_document_research and not processing_complete:
        continuation_candidates = []
        for source_row in ordered_chunks[:processing_end]:
            row_id = (
                f"{source_row['document_id']}:chunk:{int(source_row['chunk_index'])}"
            )
            row = ranked_by_native_id[row_id]
            continuation_candidates.append({
                "id": row_id,
                "semantic_score": row["semantic_score"],
                "best_chunk_score": row["best_chunk_score"],
                "lexical_score": row["lexical_score"],
                "prestart_relations": row["prestart_relations"],
                "relation_scan": row.get("_relation_scan") or [],
                "clause_identifiers": row["clause_identifiers"],
                "matched_clause_identifier": row["matched_clause_identifier"],
            })
        unsigned_cursor = {
            "version": DOCUMENT_RESEARCH_CURSOR_VERSION,
            "snapshot_identity": processing_snapshot_identity,
            "next_native_rank": processing_end + 1,
            "candidates": continuation_candidates,
        }
        if not isinstance(cursor_auth_key, bytes) or len(cursor_auth_key) != 32:
            raise ValueError("document research cursor authentication is unavailable")
        cursor_bytes = json.dumps(
            unsigned_cursor, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        continuation = (
            base64.urlsafe_b64encode(cursor_bytes).decode("ascii")
            + "."
            + hmac.new(cursor_auth_key, cursor_bytes, hashlib.sha256).hexdigest()
        )
    trace = {
        "version": DOCUMENT_RESEARCH_TRACE_VERSION,
        "intent": research_intent,
        "inventory": inventory_trace(document_sources or {}),
        "candidate_recall": [redacted_ranked_chunk(row) for row in ranked],
        "tree_candidate_retrieval": tree_retrieval_trace,
        "semantic_cohort": [
            {
                "candidate_id": row["id"],
                "semantic_hybrid_rank": row["semantic_hybrid_rank"],
                "admitted_to_structural_cohort": True,
                "reason_code": (
                    "TREE_NATIVE_COMPREHENSIVE_REVIEW"
                    if broad_document_research else "TREE_NATIVE_BOUNDED_PAGE"
                    if ordinary_tree_selection else "SEMANTIC_BOUNDED_PAGE"
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
            "ready_to_send": not broad_document_research or processing_complete,
            "decisions": packet_decisions,
        },
        "processing_coverage": {
            "policy": (
                "tree_native_comprehensive_batches"
                if broad_document_research else "tree_native_bounded_page"
                if ordinary_tree_selection else "semantic_bounded_page"
            ),
            "batch_size": BROAD_DOCUMENT_RESEARCH_BATCH_SIZE,
            "snapshot": {
                "snapshot_identity": processing_snapshot_identity,
                "tree_digest": (structural_telemetry or {}).get("tree_digest"),
                "query_region_identity": (
                    structural_telemetry or {}
                ).get("query_region_identity"),
                "active_receipt_count": len(ordered_chunks),
            },
            "batches": processing_batches,
            "examined_count": len(ranked),
            "metadata_scored_count": 0,
            "included_authored_unit_count": len(packet_rows),
            "excluded_chunk_count": max(0, len(ranked) - len({
                row.get("_origin_candidate_id", row["id"]) for row in packet_rows
            })),
            "unresolved_count": len(missing_sources),
            "unexamined_count": len(ordered_chunks) - len(ranked),
            "cursor": {
                "version": DOCUMENT_RESEARCH_CURSOR_VERSION,
                "snapshot_identity": processing_snapshot_identity,
                "next_native_rank": processing_end + 1 if broad_document_research else None,
                "complete": processing_complete,
                "continuation": continuation,
            },
        },
        "final_evidence_coverage": {
            "discovered_units": discovered,
            "selected_evidence_ids": [row["id"] for row in admitted],
            "missing_sources": missing_sources,
            "exhaustiveness": (
                "limited_by_missing_referenced_sources" if missing_sources
                else "complete_within_tree_ranked_active_project_inventory"
                if broad_document_research and processing_complete
                else "partial_tree_ranked_active_project_inventory"
                if broad_document_research
                else "limited_to_tree_native_bounded_page_and_precise_references"
                if ordinary_tree_selection
                else "limited_to_semantic_selection_and_precise_references"
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
