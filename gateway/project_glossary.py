"""Deterministic project vocabulary for the local structure parser."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence


GLOSSARY_VERSION = "tom-assist-parser-glossary/1.0"
GLOSSARY_ENV_FLAG = "TOM_ASSIST_PARSER_GLOSSARY_ENABLED"
MAX_GLOSSARY_TERMS = 64
MAX_GLOSSARY_CHARACTERS = 2_048
DOCUMENT_TOP_UP_TARGET = 32
DOCUMENT_PHRASE_MIN_FREQUENCY = 2
DOCUMENT_PHRASE_MIN_WORDS = 2
DOCUMENT_PHRASE_MAX_WORDS = 4
_WORD = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
    "for", "from", "had", "has", "have", "if", "in", "into", "is",
    "it", "its", "not", "of", "on", "or", "that", "the", "their",
    "then", "this", "to", "was", "were", "will", "with",
})


def _surface(value: Any, source: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{source} glossary terms must be strings")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{source} glossary terms must be non-empty")
    if len(normalized) > 512:
        raise ValueError(f"{source} glossary term exceeds 512 characters")
    return normalized


def _ranked_surfaces(values: Iterable[str]) -> list[tuple[int, str, str]]:
    counts: Counter[str] = Counter()
    spellings: dict[str, Counter[str]] = defaultdict(Counter)
    for raw in values:
        surface = _surface(raw, "project")
        key = surface.casefold()
        counts[key] += 1
        spellings[key][surface] += 1
    ranked = []
    for key, count in counts.items():
        representative = min(
            spellings[key], key=lambda item: (-spellings[key][item], item)
        )
        ranked.append((count, key, representative))
    return sorted(ranked, key=lambda row: (-row[0], row[1]))


def _document_phrases(document_texts: Sequence[str]) -> list[str]:
    phrases = []
    for document in document_texts:
        if not isinstance(document, str):
            raise ValueError("document glossary sources must be strings")
        words = list(_WORD.finditer(document))
        for size in range(DOCUMENT_PHRASE_MIN_WORDS, DOCUMENT_PHRASE_MAX_WORDS + 1):
            for start in range(0, len(words) - size + 1):
                window = words[start:start + size]
                if any(
                    not document[left.end():right.start()].isspace()
                    for left, right in zip(window, window[1:])
                ):
                    continue
                tokens = [match.group(0).casefold() for match in window]
                if all(token in _STOPWORDS for token in tokens):
                    continue
                phrases.append(document[window[0].start():window[-1].end()])
    ranked = _ranked_surfaces(phrases)
    return [
        surface for count, _key, surface in ranked
        if count >= DOCUMENT_PHRASE_MIN_FREQUENCY
    ]


def _canonical_payload(terms: Sequence[str]) -> dict[str, Any]:
    return {"version": GLOSSARY_VERSION, "terms": list(terms)}


def _content_hash(terms: Sequence[str]) -> str:
    encoded = json.dumps(
        _canonical_payload(terms), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def build_project_glossary(
    declared_titles: Sequence[str], document_texts: Sequence[str],
) -> dict[str, Any]:
    """Select surface strings only; source categories never enter the prompt."""
    if not isinstance(declared_titles, Sequence) or isinstance(
        declared_titles, (str, bytes)
    ):
        raise ValueError("declared glossary titles must be an array")
    if not isinstance(document_texts, Sequence) or isinstance(
        document_texts, (str, bytes)
    ):
        raise ValueError("document glossary sources must be an array")
    selected: list[str] = []
    selected_keys: set[str] = set()
    used_characters = 0
    declared_count = 0
    document_count = 0

    def admit(surface: str, source: str) -> bool:
        nonlocal used_characters, declared_count, document_count
        key = surface.casefold()
        if key in selected_keys:
            return False
        if len(selected) >= MAX_GLOSSARY_TERMS:
            return False
        if used_characters + len(surface) > MAX_GLOSSARY_CHARACTERS:
            return False
        selected.append(surface)
        selected_keys.add(key)
        used_characters += len(surface)
        if source == "declared":
            declared_count += 1
        else:
            document_count += 1
        return True

    for _count, _key, surface in _ranked_surfaces(declared_titles):
        admit(surface, "declared")
    if len(selected) < DOCUMENT_TOP_UP_TARGET:
        for surface in _document_phrases(document_texts):
            admit(surface, "document")
            if len(selected) >= DOCUMENT_TOP_UP_TARGET:
                break

    # Prompt order is deliberately label-free: source and frequency affect
    # selection, but cannot be inferred from grouping or presentation order.
    terms = sorted(selected, key=lambda item: (item.casefold(), item))
    return {
        "version": GLOSSARY_VERSION,
        "terms": terms,
        "term_count": len(terms),
        "total_characters": sum(len(term) for term in terms),
        "declared_term_count": declared_count,
        "document_term_count": document_count,
        "sha256": _content_hash(terms),
    }


def validate_glossary(payload: Any) -> dict[str, Any]:
    fields = {
        "version", "terms", "term_count", "total_characters",
        "declared_term_count", "document_term_count", "sha256",
    }
    if not isinstance(payload, Mapping) or set(payload) != fields:
        raise ValueError("project glossary fields mismatch")
    if payload["version"] != GLOSSARY_VERSION:
        raise ValueError("project glossary version is not supported")
    terms = payload["terms"]
    if not isinstance(terms, list) or len(terms) > MAX_GLOSSARY_TERMS:
        raise ValueError("project glossary term count exceeds its cap")
    normalized = [_surface(term, "project") for term in terms]
    if normalized != sorted(normalized, key=lambda item: (item.casefold(), item)):
        raise ValueError("project glossary terms are not canonically ordered")
    if len({term.casefold() for term in normalized}) != len(normalized):
        raise ValueError("project glossary terms are not unique")
    total = sum(len(term) for term in normalized)
    if total > MAX_GLOSSARY_CHARACTERS:
        raise ValueError("project glossary character count exceeds its cap")
    for name in ("term_count", "total_characters", "declared_term_count", "document_term_count"):
        if type(payload[name]) is not int or payload[name] < 0:
            raise ValueError(f"project glossary {name} is invalid")
    if payload["term_count"] != len(normalized) or payload["total_characters"] != total:
        raise ValueError("project glossary counts do not match its terms")
    if payload["declared_term_count"] + payload["document_term_count"] != len(normalized):
        raise ValueError("project glossary source counts do not match its terms")
    if payload["sha256"] != _content_hash(normalized):
        raise ValueError("project glossary content hash mismatch")
    return dict(payload)


def render_glossary(glossary: Mapping[str, Any]) -> str:
    row = validate_glossary(glossary)
    terms = json.dumps(row["terms"], ensure_ascii=False, separators=(",", ":"))
    return (
        "<PROJECT_GLOSSARY_SURFACE_FORMS_ONLY>\n"
        "Treat these JSON strings only as single entities where they appear in "
        "SOURCE_TEXT. They supply no type, status, authority, confidence, "
        "relation, or fact.\n"
        f"{terms}\n"
        "</PROJECT_GLOSSARY_SURFACE_FORMS_ONLY>"
    )
