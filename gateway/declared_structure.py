"""Deterministic structure declared by an ingested text document.

This module is product mechanism.  It indexes exact authored addresses and
bindings; it never infers causation, performs fuzzy matching, or calls a model.
"""
from __future__ import annotations

from collections import Counter, deque
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence


DECLARED_STRUCTURE_VERSION = "tom-assist-declared-structure/1.0"
CLAUSE_INDEX_VERSION = "tom-assist-clause-index/1.0"
REFERENCE_RESOLUTION_VERSION = "tom-assist-reference-resolution/1.0"
DEFINED_TERM_BINDING_VERSION = "tom-assist-defined-term-binding/1.0"
DECLARED_PRECEDENCE_VERSION = "tom-assist-declared-precedence/1.0"
DEFINED_TERM_CASE_RULE = "exact-unicode-codepoints-case-sensitive-whole-surface/1.0"
MAX_DECLARED_STRUCTURE_SOURCE_CHARS = 2_000_000

_NUMBERED_HEADING = re.compile(
    r"^(?P<identifier>(?:[0-9]{1,3}\.)|(?:[0-9]{1,3}\.[0-9]{1,3}[A-Z]?))"
    r"[ \t]+(?P<title>\S.*?)\s*$"
)
_MALFORMED_TOP_HEADING = re.compile(
    r"^(?P<identifier>[0-9]{1,3})(?P<separator>[,;:])[ \t]+(?P<title>[A-Z][A-Z &/\-]+)\s*$"
)
_MARKER = re.compile(r"^\((?P<marker>[^)\s]{1,8})\)[ \t]+(?P<title>\S.*?)\s*$")
_SCHEDULE_HEADING = re.compile(
    r"^(?P<kind>Schedule|SCHEDULE|Exhibit|EXHIBIT|Appendix|APPENDIX|Attachment|ATTACHMENT)"
    r"[ \t]+(?P<identifier>[A-Z][0-9]{1,3}[A-Z]?|[0-9]{1,3})"
    r"(?:[ \t]*[-—:][ \t]*|[ \t]{2,})(?P<title>\S.*?)\s*$"
)
_DEFINITION_DELIMITER = re.compile(
    r"\s+(?:means|has the meaning(?: given)?(?: to that term)?(?: given)?"
    r"(?: in| under| set out| assigned)?|includes|is the process)\b",
    flags=re.IGNORECASE,
)
_REFERENCE_KEYWORD = re.compile(
    r"\b(?P<keyword>clauses?|schedules?|sections?|exhibits?|appendices|attachments?)\b",
    flags=re.IGNORECASE,
)
_CLAUSE_IDENTIFIER = re.compile(
    r"[0-9]{1,3}(?:\.[0-9]{1,3}[A-Z]?)*(?:\([A-Za-z0-9]{1,4}\))*"
)
_SCHEDULE_IDENTIFIER = re.compile(r"(?:[A-Z][0-9]{1,3}[A-Z]?|[0-9]{1,3})")
_SECTION_IDENTIFIER = re.compile(
    r"[0-9]{1,3}(?:\.[0-9]{1,3})*(?:\([A-Za-z0-9]{1,4}\))*"
)
_EXTERNAL_SECTION_DOCUMENT = re.compile(
    r"[ \t]+of[ \t]+the[ \t]+(?P<document>"
    r"[A-Z][A-Za-z0-9 &'’/\-]{1,100}?"
    r"(?:Specification|Act(?:[ \t]+[0-9]{4})?)(?:[ \t]+\([A-Za-z]+\))?"
    r")"
)
_REFERENCE_SEPARATOR = re.compile(r"[ \t]*(?:,|and|or|to)[ \t]*", re.IGNORECASE)


class DeclaredStructureError(ValueError):
    """A deterministic, fail-closed declared-structure error."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def text_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_id(prefix: str, *values: Any) -> str:
    encoded = "\u241f".join(str(value) for value in values).encode("utf-8")
    return f"{prefix}-" + hashlib.sha256(encoded).hexdigest()[:24]


def _line_rows(text: str, start: int = 0) -> list[dict[str, Any]]:
    rows = []
    cursor = start
    while cursor < len(text):
        newline = text.find("\n", cursor)
        end = len(text) if newline < 0 else newline
        raw = text[cursor:end].rstrip("\r")
        prefix = len(raw) - len(raw.lstrip("\f"))
        visible = raw[prefix:]
        indent = len(visible) - len(visible.lstrip(" \t"))
        logical = visible[indent:].rstrip()
        rows.append({
            "line_start": cursor,
            "line_end": end,
            "token_start": cursor + prefix + indent,
            "indent": indent,
            "logical": logical,
        })
        if newline < 0:
            break
        cursor = newline + 1
    return rows


def _document_start(text: str) -> int:
    marker = text.find("THIS DEED is made")
    return marker if marker >= 0 else 0


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _entry(
    *, kind: str, identifier: str, display_identifier: str, title: str,
    start: int, depth: int, parent_entry_id: str | None,
    status: str = "valid", malformed_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "entry_id": _stable_id("address", kind, identifier, start),
        "kind": kind,
        "identifier": identifier,
        "display_identifier": display_identifier,
        "title": title,
        "span": {"start": start, "end": start},
        "parent_entry_id": parent_entry_id,
        "status": status,
        "malformed_reason": malformed_reason,
        "_depth": depth,
    }


def _preliminary_headings(text: str) -> list[dict[str, Any]]:
    start = _document_start(text)
    events: list[dict[str, Any]] = []
    named_counts: Counter[str] = Counter()
    current_section: str | None = None
    top_level_by_number: dict[str, str] = {}
    for row in _line_rows(text, start):
        logical = row["logical"]
        if not logical:
            continue
        schedule = _SCHEDULE_HEADING.fullmatch(logical)
        if schedule is not None and row["indent"] <= 4:
            label = schedule.group("kind").title()
            identifier = f"{label} {schedule.group('identifier')}"
            event = _entry(
                kind=label.casefold(), identifier=identifier,
                display_identifier=f"{schedule.group('kind')} {schedule.group('identifier')}",
                title=schedule.group("title"), start=row["token_start"], depth=1,
                parent_entry_id=current_section,
            )
            events.append(event)
            continue
        heading = _NUMBERED_HEADING.fullmatch(logical)
        if heading is not None and row["indent"] <= 4:
            raw_identifier = heading.group("identifier")
            identifier = raw_identifier[:-1] if raw_identifier.endswith(".") else raw_identifier
            title = heading.group("title")
            if "." not in identifier:
                status = "valid" if title.upper() == title else "malformed"
                reason = None if status == "valid" else "top_level_title_is_not_uppercase"
                event = _entry(
                    kind="clause", identifier=identifier,
                    display_identifier=raw_identifier, title=title,
                    start=row["token_start"], depth=1,
                    parent_entry_id=current_section, status=status,
                    malformed_reason=reason,
                )
                top_level_by_number[identifier] = event["entry_id"]
            else:
                parent_identifier = identifier.split(".", 1)[0]
                parent = top_level_by_number.get(parent_identifier)
                event = _entry(
                    kind="clause", identifier=identifier,
                    display_identifier=identifier, title=title,
                    start=row["token_start"], depth=2,
                    parent_entry_id=parent,
                    status="valid" if parent else "malformed",
                    malformed_reason=None if parent else "numbered_parent_is_absent",
                )
            events.append(event)
            continue
        malformed_top = _MALFORMED_TOP_HEADING.fullmatch(logical)
        if malformed_top is not None and row["indent"] <= 4:
            identifier = malformed_top.group("identifier")
            event = _entry(
                kind="clause", identifier=identifier,
                display_identifier=identifier + malformed_top.group("separator"),
                title=malformed_top.group("title"), start=row["token_start"], depth=1,
                parent_entry_id=current_section, status="malformed",
                malformed_reason="top_level_separator_is_not_period",
            )
            top_level_by_number[identifier] = event["entry_id"]
            events.append(event)
            continue
        named = logical.rstrip(":")
        is_named = (
            row["indent"] <= 4
            and (
                logical.endswith(":") and len(named) >= 3
                and any(character.isalpha() for character in named)
                and named.upper() == named
                or logical.upper().startswith("EXECUTED")
            )
        )
        if is_named:
            slug = re.sub(r"[^a-z0-9]+", "-", named.casefold()).strip("-")[:64]
            slug = slug or "section"
            named_counts[slug] += 1
            suffix = "" if named_counts[slug] == 1 else f":{named_counts[slug]}"
            identifier = f"section:{slug}{suffix}"
            event = _entry(
                kind="named_section", identifier=identifier,
                display_identifier=logical, title=named,
                start=row["token_start"], depth=0, parent_entry_id=None,
            )
            events.append(event)
            current_section = event["entry_id"]
    _close_spans(events, len(text))
    return events


def _containing_heading(
    headings: Sequence[Mapping[str, Any]], position: int,
) -> Mapping[str, Any] | None:
    candidates = [
        row for row in headings
        if row["span"]["start"] <= position < row["span"]["end"]
        and row["kind"] in {"clause", "schedule", "exhibit", "appendix", "attachment"}
    ]
    return max(candidates, key=lambda row: row["_depth"], default=None)


def _block_ranges(text: str, start: int) -> Iterable[tuple[int, int]]:
    cursor = start
    for separator in re.finditer(r"\n[ \t]*\n", text[start:]):
        end = start + separator.start()
        if end > cursor:
            yield cursor, end
        cursor = start + separator.end()
    if cursor < len(text):
        yield cursor, len(text)


def _definition_candidates(
    text: str, headings: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates = []
    for block_start, block_end in _block_ranges(text, _document_start(text)):
        block = text[block_start:block_end]
        match = _DEFINITION_DELIMITER.search(block)
        if match is None:
            continue
        prefix = block[:match.start()]
        line_starts = [0]
        line_starts.extend(index + 1 for index, character in enumerate(prefix) if character == "\n")
        surface_candidates = []
        for relative_start in line_starts[-3:]:
            fragment = prefix[relative_start:]
            leading = len(fragment) - len(fragment.lstrip())
            trailing = len(fragment.rstrip())
            if trailing <= leading:
                continue
            start = block_start + relative_start + leading
            end = block_start + relative_start + trailing
            surface = _collapse(text[start:end])
            if (
                1 <= len(surface) <= 160
                and surface[0].isupper()
                and "ME_" not in surface
                and not re.match(r"^\([A-Za-z0-9]+\)", surface)
                and not any(character in surface for character in ".;:")
            ):
                surface_candidates.append((start, end, surface))
        if not surface_candidates:
            continue
        start, end, surface = min(surface_candidates, key=lambda row: row[0])
        heading = _containing_heading(headings, start)
        if heading is None or "definition" not in heading["title"].casefold():
            continue
        candidates.append({
            "term_id": _stable_id("term", surface, start),
            "surface": surface,
            "surface_span": {"start": start, "end": end},
            "_delimiter_start": block_start + match.start(),
            "_block_end": block_end,
            "defining_clause_entry_id": heading["entry_id"],
            "defining_clause_identifier": heading["identifier"],
        })
    surfaces = [row["surface"] for row in candidates]
    duplicates = sorted(surface for surface, count in Counter(surfaces).items() if count > 1)
    if duplicates:
        raise DeclaredStructureError(
            "duplicate exact defined-term surfaces: " + ", ".join(duplicates[:5])
        )
    candidates.sort(key=lambda row: row["surface_span"]["start"])
    by_clause: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        by_clause.setdefault(row["defining_clause_entry_id"], []).append(row)
    heading_by_id = {row["entry_id"]: row for row in headings}
    result = []
    for rows in by_clause.values():
        clause_end = heading_by_id[rows[0]["defining_clause_entry_id"]]["span"]["end"]
        for index, row in enumerate(rows):
            next_start = (
                rows[index + 1]["surface_span"]["start"]
                if index + 1 < len(rows) else clause_end
            )
            body_start = row.pop("_delimiter_start")
            body_end = min(next_start, clause_end)
            while body_end > body_start and text[body_end - 1].isspace():
                body_end -= 1
            row.pop("_block_end")
            row["definition_span"] = {"start": body_start, "end": body_end}
            row["definition_body"] = text[body_start:body_end]
            unsigned = dict(row)
            row["entry_digest"] = digest(unsigned)
            result.append(row)
    return sorted(result, key=lambda row: row["surface_span"]["start"])


def _marker_level(indent: int, marker: str, base_kind: str) -> int:
    if indent <= 4 and base_kind == "clause":
        if re.fullmatch(r"[ivxlcdm]+", marker):
            return 2
        if re.fullmatch(r"[A-Z]{1,3}", marker):
            return 3
        return 1
    if indent <= 10:
        return 1
    if indent <= 20:
        return 2
    if indent <= 28:
        return 3
    if indent <= 34:
        return 4
    return 5


def _definition_at(
    definitions: Sequence[Mapping[str, Any]], position: int,
) -> Mapping[str, Any] | None:
    for row in definitions:
        if row["surface_span"]["start"] <= position < row["definition_span"]["end"]:
            return row
    return None


def _close_spans(events: Sequence[dict[str, Any]], source_end: int) -> None:
    opened: list[dict[str, Any]] = []
    for event in sorted(events, key=lambda row: (row["span"]["start"], row["_depth"])):
        while opened and opened[-1]["_depth"] >= event["_depth"]:
            opened.pop()["span"]["end"] = event["span"]["start"]
        opened.append(event)
    while opened:
        opened.pop()["span"]["end"] = source_end


def build_clause_index(
    text: str, definitions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    headings = _preliminary_headings(text)
    definitions = list(definitions or ())
    events = list(headings)
    heading_spans = sorted(headings, key=lambda row: row["span"]["start"])
    marker_stacks: dict[str, list[dict[str, Any]]] = {}
    for row in _line_rows(text, _document_start(text)):
        marker = _MARKER.fullmatch(row["logical"])
        if marker is None:
            continue
        base = _containing_heading(heading_spans, row["token_start"])
        if base is None:
            named = [
                item for item in headings
                if item["kind"] == "named_section"
                and item["span"]["start"] <= row["token_start"] < item["span"]["end"]
            ]
            base = max(named, key=lambda item: item["span"]["start"], default=None)
        if base is None:
            continue
        definition = _definition_at(definitions, row["token_start"])
        scope = (
            f"{base['identifier']}::definition:{definition['term_id']}"
            if definition is not None else base["identifier"]
        )
        level = _marker_level(row["indent"], marker.group("marker"), base["kind"])
        stack = marker_stacks.setdefault(scope, [])
        malformed_reason = None
        if level > len(stack) + 1:
            malformed_reason = "marker_indentation_level_jump"
            level = len(stack) + 1
        del stack[level - 1:]
        marker_text = marker.group("marker")
        if not re.fullmatch(r"[A-Za-z]{1,4}|[0-9]{1,3}", marker_text):
            malformed_reason = malformed_reason or "marker_form_unrecognised"
        parent = stack[-1]["entry_id"] if stack else base["entry_id"]
        identifier = scope + "".join(
            [f"({item['marker']})" for item in stack] + [f"({marker_text})"]
        )
        event = _entry(
            kind="subclause", identifier=identifier,
            display_identifier=f"({marker_text})", title=marker.group("title"),
            start=row["token_start"], depth=base["_depth"] + level,
            parent_entry_id=parent,
            status="malformed" if malformed_reason else "valid",
            malformed_reason=malformed_reason,
        )
        event["_marker"] = marker_text
        stack.append({"marker": marker_text, "entry_id": event["entry_id"]})
        events.append(event)

    groups: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        groups.setdefault(event["identifier"], []).append(event)
    for rows in groups.values():
        if len(rows) > 1:
            for event in rows:
                event["status"] = "malformed"
                event["malformed_reason"] = "duplicate_identifier"
    _close_spans(events, len(text))
    public = []
    for event in sorted(events, key=lambda row: (row["span"]["start"], row["_depth"])):
        row = {
            key: value for key, value in event.items()
            if not key.startswith("_")
        }
        public.append(row)
    payload = {
        "version": CLAUSE_INDEX_VERSION,
        "entries": public,
        "entry_count": len(public),
        "valid_count": sum(row["status"] == "valid" for row in public),
        "malformed_count": sum(row["status"] == "malformed" for row in public),
    }
    payload["index_digest"] = digest(payload)
    return payload


def _resolvable_targets(clause_index: Mapping[str, Any]) -> dict[str, str]:
    targets = {}
    for row in clause_index["entries"]:
        if row["status"] != "valid" or "::definition:" in row["identifier"]:
            continue
        if row["identifier"] in targets:
            continue
        targets[row["identifier"]] = row["entry_id"]
    return targets


def _unparsed_reference(
    text: str, keyword: re.Match[str], line_end: int, kind: str,
) -> dict[str, Any]:
    end = keyword.end()
    limit = min(line_end, keyword.end() + 120)
    while end < limit and text[end] not in ";,.\n":
        end += 1
    while end > keyword.end() and text[end - 1].isspace():
        end -= 1
    if end == keyword.end():
        end = keyword.end()
    return {
        "reference_id": _stable_id("reference", keyword.start(), kind, "unparsed"),
        "kind": kind,
        "reference_text": text[keyword.start():end],
        "span": {"start": keyword.start(), "end": end},
        "named_identifier": None,
        "outcome": "unparsed",
        "target_entry_id": None,
    }


def _reference_item(
    text: str, kind: str, start: int, end: int, identifier: str,
    targets: Mapping[str, str],
) -> dict[str, Any]:
    target = targets.get(identifier)
    return {
        "reference_id": _stable_id("reference", start, kind, identifier),
        "kind": kind,
        "reference_text": text[start:end],
        "span": {"start": start, "end": end},
        "named_identifier": identifier,
        "outcome": "resolved" if target is not None else "unresolved_absent",
        "target_entry_id": target,
    }


def _parse_identifier_sequence(
    text: str, keyword: re.Match[str], line_end: int,
    pattern: re.Pattern[str], kind: str, prefix: str,
    targets: Mapping[str, str],
) -> list[dict[str, Any]]:
    cursor = keyword.end()
    while cursor < line_end and text[cursor] in " \t":
        cursor += 1
    items = []
    first = True
    while cursor < line_end:
        match = pattern.match(text, cursor, line_end)
        if match is None:
            break
        raw = match.group(0)
        identifier = f"{prefix}{raw}"
        start = keyword.start() if first else match.start()
        items.append(_reference_item(text, kind, start, match.end(), identifier, targets))
        first = False
        separator = _REFERENCE_SEPARATOR.match(text, match.end(), line_end)
        if separator is None or separator.end() == match.end():
            break
        cursor = separator.end()
    return items


def resolve_references(text: str, clause_index: Mapping[str, Any]) -> dict[str, Any]:
    targets = _resolvable_targets(clause_index)
    references = []
    occupied: set[tuple[int, int]] = set()
    for line in _line_rows(text, _document_start(text)):
        line_start, line_end = line["line_start"], line["line_end"]
        for keyword in _REFERENCE_KEYWORD.finditer(text, line_start, line_end):
            token = keyword.group("keyword").casefold()
            if token.startswith("clause"):
                kind = "clause"
                parsed = _parse_identifier_sequence(
                    text, keyword, line_end, _CLAUSE_IDENTIFIER, kind, "", targets,
                )
            elif token.startswith("schedule"):
                kind = "schedule"
                parsed = _parse_identifier_sequence(
                    text, keyword, line_end, _SCHEDULE_IDENTIFIER, kind, "Schedule ", targets,
                )
            elif token.startswith("exhibit"):
                kind = "exhibit"
                parsed = _parse_identifier_sequence(
                    text, keyword, line_end, _SCHEDULE_IDENTIFIER, kind, "Exhibit ", targets,
                )
            elif token.startswith("append"):
                kind = "appendix"
                parsed = _parse_identifier_sequence(
                    text, keyword, line_end, _SCHEDULE_IDENTIFIER, kind, "Appendix ", targets,
                )
            elif token.startswith("attachment"):
                kind = "attachment"
                parsed = _parse_identifier_sequence(
                    text, keyword, line_end, _SCHEDULE_IDENTIFIER, kind, "Attachment ", targets,
                )
            else:
                kind = "section"
                cursor = keyword.end()
                while cursor < line_end and text[cursor] in " \t":
                    cursor += 1
                section = _SECTION_IDENTIFIER.match(text, cursor, line_end)
                parsed = []
                if section is not None:
                    external = _EXTERNAL_SECTION_DOCUMENT.match(text, section.end(), line_end)
                    identifier = section.group(0)
                    end = section.end()
                    if external is not None:
                        identifier = f"{external.group('document')}§{identifier}"
                        end = external.end()
                    parsed.append(_reference_item(
                        text, kind, keyword.start(), end, identifier, targets,
                    ))
            if not parsed:
                parsed = [_unparsed_reference(text, keyword, line_end, kind)]
            for row in parsed:
                span_key = (row["span"]["start"], row["span"]["end"])
                if span_key not in occupied:
                    occupied.add(span_key)
                    references.append(row)
    references.sort(key=lambda row: (row["span"]["start"], row["span"]["end"]))
    counts = Counter(row["outcome"] for row in references)
    return {
        "version": REFERENCE_RESOLUTION_VERSION,
        "references": references,
        "reference_count": len(references),
        "resolved_count": counts["resolved"],
        "unresolved_absent_count": counts["unresolved_absent"],
        "unparsed_count": counts["unparsed"],
    }


def _is_word_character(character: str) -> bool:
    return character == "_" or character.isalnum()


def _term_trie(terms: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, int]], list[int], list[list[int]]]:
    transitions: list[dict[str, int]] = [{}]
    failure = [0]
    output: list[list[int]] = [[]]
    for index, row in enumerate(terms):
        state = 0
        for character in row["surface"]:
            next_state = transitions[state].get(character)
            if next_state is None:
                next_state = len(transitions)
                transitions[state][character] = next_state
                transitions.append({})
                failure.append(0)
                output.append([])
            state = next_state
        output[state].append(index)
    queue = deque(transitions[0].values())
    while queue:
        state = queue.popleft()
        for character, next_state in transitions[state].items():
            queue.append(next_state)
            fallback = failure[state]
            while fallback and character not in transitions[fallback]:
                fallback = failure[fallback]
            failure[next_state] = transitions[fallback].get(character, 0)
            output[next_state].extend(output[failure[next_state]])
    return transitions, failure, output


def bind_defined_terms(
    text: str, definitions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not definitions:
        return []
    transitions, failure, output = _term_trie(definitions)
    state = 0
    bindings = []
    for end, character in enumerate(text, 1):
        while state and character not in transitions[state]:
            state = failure[state]
        state = transitions[state].get(character, 0)
        for term_index in output[state]:
            term = definitions[term_index]
            start = end - len(term["surface"])
            if start > 0 and _is_word_character(text[start - 1]):
                continue
            if end < len(text) and _is_word_character(text[end]):
                continue
            bindings.append({
                "binding_id": _stable_id("binding", term["term_id"], start, end),
                "term_id": term["term_id"],
                "surface": term["surface"],
                "span": {"start": start, "end": end},
            })
    return sorted(bindings, key=lambda row: (row["span"]["start"], -row["span"]["end"], row["surface"]))


def build_defined_terms(
    text: str, definitions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    terms = [dict(row) for row in definitions]
    bindings = bind_defined_terms(text, terms)
    return {
        "version": DEFINED_TERM_BINDING_VERSION,
        "case_rule": DEFINED_TERM_CASE_RULE,
        "surface_forms_only_for_prompt": True,
        "terms": terms,
        "term_count": len(terms),
        "bindings": bindings,
        "binding_count": len(bindings),
    }


def _entry_text(text: str, entry: Mapping[str, Any]) -> str:
    return text[entry["span"]["start"]:entry["span"]["end"]]


def _item_name(text: str, entry: Mapping[str, Any]) -> str:
    value = _entry_text(text, entry)
    marker_end = value.find(")")
    if marker_end >= 0:
        value = value[marker_end + 1:]
    value = _collapse(value)
    value = re.sub(r"(?:;|,)?\s+(?:and|or)\s*$", "", value, flags=re.IGNORECASE)
    return value.rstrip(";,. ")


def extract_declared_precedence(
    text: str, clause_index: Mapping[str, Any], references: Mapping[str, Any],
) -> dict[str, Any]:
    entries = clause_index["entries"]
    by_parent: dict[str, list[Mapping[str, Any]]] = {}
    for row in entries:
        if row["parent_entry_id"] is not None:
            by_parent.setdefault(row["parent_entry_id"], []).append(row)
    relations = []
    precedence_clauses = [
        row for row in entries
        if row["kind"] == "clause" and "order of precedence" in row["title"].casefold()
    ]
    for clause in precedence_clauses:
        descendants = [
            row for row in entries
            if clause["span"]["start"] <= row["span"]["start"] < clause["span"]["end"]
        ]
        for parent in descendants:
            children = [
                row for row in by_parent.get(parent["entry_id"], [])
                if row["kind"] == "subclause" and row["status"] == "valid"
            ]
            children.sort(key=lambda row: row["span"]["start"])
            prefix_end = children[0]["span"]["start"] if children else parent["span"]["end"]
            prefix = _collapse(text[parent["span"]["start"]:prefix_end]).casefold()
            if (
                len(children) < 2
                or re.search(r"\bfollowing(?:\s+(?:order|priority))?\s*:\s*$", prefix) is None
            ):
                continue
            for higher, lower in zip(children, children[1:]):
                relation = {
                    "relation_id": _stable_id("precedence", higher["entry_id"], lower["entry_id"]),
                    "relation_kind": "precedes",
                    "source_entry_id": parent["entry_id"],
                    "higher_identifier": _item_name(text, higher),
                    "lower_identifier": _item_name(text, lower),
                    "target_identifier": None,
                    "target_outcome": None,
                    "span": {
                        "start": higher["span"]["start"],
                        "end": lower["span"]["end"],
                    },
                }
                relations.append(relation)
    targets = _resolvable_targets(clause_index)
    notwithstanding = re.compile(
        r"\b[Nn]otwithstanding[ \t]+(?P<kind>clause|Schedule|section)[ \t]+"
        r"(?P<identifier>[0-9]{1,3}(?:\.[0-9]{1,3}[A-Z]?)*(?:\([A-Za-z0-9]{1,4}\))*|[A-Z][0-9]{1,3}[A-Z]?)"
    )
    for match in notwithstanding.finditer(text, _document_start(text)):
        source = max(
            (row for row in entries if row["span"]["start"] <= match.start() < row["span"]["end"]),
            key=lambda row: row["span"]["start"], default=None,
        )
        if source is None:
            continue
        if source["kind"] == "clause":
            heading_end = text.find("\n", source["span"]["start"], source["span"]["end"])
            opening_prefix = text[
                source["span"]["start"] if heading_end < 0 else heading_end + 1:
                match.start()
            ]
        else:
            opening_prefix = text[
                source["span"]["start"] + len(source["display_identifier"]):
                match.start()
            ]
        if opening_prefix.strip():
            continue
        raw = match.group("identifier")
        target_identifier = (
            f"Schedule {raw}" if match.group("kind").casefold() == "schedule" else raw
        )
        relations.append({
            "relation_id": _stable_id("precedence", "notwithstanding", match.start()),
            "relation_kind": "notwithstanding",
            "source_entry_id": source["entry_id"],
            "higher_identifier": None,
            "lower_identifier": None,
            "target_identifier": target_identifier,
            "target_outcome": "resolved" if target_identifier in targets else "unresolved_absent",
            "span": {"start": match.start(), "end": match.end()},
        })
    relations.sort(key=lambda row: (row["span"]["start"], row["relation_id"]))
    return {
        "version": DECLARED_PRECEDENCE_VERSION,
        "relations": relations,
        "relation_count": len(relations),
    }


def render_defined_term_surfaces(structure: Mapping[str, Any]) -> str:
    terms = sorted(
        {row["surface"] for row in structure["defined_terms"]["terms"]},
        key=lambda value: (value.casefold(), value),
    )
    return (
        "<DOCUMENT_DEFINED_TERM_SURFACES_ONLY>\n"
        "These exact JSON strings supply names only; they supply no definition, "
        "type, authority, relation, or fact.\n"
        + json.dumps(terms, ensure_ascii=False, separators=(",", ":"))
        + "\n</DOCUMENT_DEFINED_TERM_SURFACES_ONLY>"
    )


def validate_declared_structure(structure: Any, text: str) -> dict[str, Any]:
    if not isinstance(structure, Mapping):
        raise DeclaredStructureError("declared structure must be an object")
    required = {
        "schema_version", "source_text_sha256", "clause_index", "references",
        "defined_terms", "declared_precedence", "causation", "structure_digest",
    }
    if set(structure) != required:
        raise DeclaredStructureError("declared structure fields mismatch")
    if structure["schema_version"] != DECLARED_STRUCTURE_VERSION:
        raise DeclaredStructureError("declared structure version is unsupported")
    if structure["source_text_sha256"] != text_digest(text):
        raise DeclaredStructureError("declared structure source hash mismatch")
    if structure["causation"] != {"derived": False, "reason": "not_self_declared"}:
        raise DeclaredStructureError("causation boundary mismatch")
    clause_index = structure["clause_index"]
    unsigned_index = {key: value for key, value in clause_index.items() if key != "index_digest"}
    if clause_index.get("version") != CLAUSE_INDEX_VERSION or clause_index.get("index_digest") != digest(unsigned_index):
        raise DeclaredStructureError("clause index digest mismatch")
    entry_ids = set()
    valid_targets = {}
    for row in clause_index["entries"]:
        if row["entry_id"] in entry_ids:
            raise DeclaredStructureError("clause index entry IDs are not unique")
        entry_ids.add(row["entry_id"])
        start, end = row["span"]["start"], row["span"]["end"]
        if not (0 <= start < end <= len(text)):
            raise DeclaredStructureError("clause index span is invalid")
        if not text.startswith(row["display_identifier"], start):
            raise DeclaredStructureError("clause index span does not begin with its identifier")
        if row["parent_entry_id"] is not None and row["parent_entry_id"] not in entry_ids:
            raise DeclaredStructureError("clause index parent does not precede its child")
        if row["status"] == "valid" and "::definition:" not in row["identifier"]:
            valid_targets[row["identifier"]] = row["entry_id"]
    if clause_index["entry_count"] != len(clause_index["entries"]):
        raise DeclaredStructureError("clause index entry count mismatch")
    if clause_index["valid_count"] != sum(row["status"] == "valid" for row in clause_index["entries"]):
        raise DeclaredStructureError("clause index valid count mismatch")
    if clause_index["malformed_count"] != sum(row["status"] == "malformed" for row in clause_index["entries"]):
        raise DeclaredStructureError("clause index malformed count mismatch")

    reference_payload = structure["references"]
    if reference_payload.get("version") != REFERENCE_RESOLUTION_VERSION:
        raise DeclaredStructureError("reference-resolution version mismatch")
    counts = Counter()
    reference_ids = set()
    for row in reference_payload["references"]:
        if row["reference_id"] in reference_ids:
            raise DeclaredStructureError("reference IDs are not unique")
        reference_ids.add(row["reference_id"])
        start, end = row["span"]["start"], row["span"]["end"]
        if not (0 <= start < end <= len(text)) or text[start:end] != row["reference_text"]:
            raise DeclaredStructureError("reference span is invalid")
        target = valid_targets.get(row["named_identifier"])
        expected = (
            "unparsed" if row["named_identifier"] is None
            else "resolved" if target is not None else "unresolved_absent"
        )
        if row["outcome"] != expected or row["target_entry_id"] != target:
            raise DeclaredStructureError("reference outcome does not match the exact index")
        counts[row["outcome"]] += 1
    if reference_payload["reference_count"] != len(reference_payload["references"]):
        raise DeclaredStructureError("reference count mismatch")
    if (
        reference_payload["resolved_count"] != counts["resolved"]
        or reference_payload["unresolved_absent_count"] != counts["unresolved_absent"]
        or reference_payload["unparsed_count"] != counts["unparsed"]
    ):
        raise DeclaredStructureError("reference outcome counts mismatch")

    term_payload = structure["defined_terms"]
    if (
        term_payload.get("version") != DEFINED_TERM_BINDING_VERSION
        or term_payload["case_rule"] != DEFINED_TERM_CASE_RULE
        or term_payload["surface_forms_only_for_prompt"] is not True
    ):
        raise DeclaredStructureError("defined-term case/prompt policy mismatch")
    term_ids = set()
    for row in term_payload["terms"]:
        if row["term_id"] in term_ids:
            raise DeclaredStructureError("defined-term IDs are not unique")
        term_ids.add(row["term_id"])
        surface_quote = text[row["surface_span"]["start"]:row["surface_span"]["end"]]
        body = text[row["definition_span"]["start"]:row["definition_span"]["end"]]
        if _collapse(surface_quote) != row["surface"] or body != row["definition_body"]:
            raise DeclaredStructureError("defined-term source spans are invalid")
        unsigned = {key: value for key, value in row.items() if key != "entry_digest"}
        if row["entry_digest"] != digest(unsigned):
            raise DeclaredStructureError("defined-term digest mismatch")
    binding_ids = set()
    for row in term_payload["bindings"]:
        if row["binding_id"] in binding_ids:
            raise DeclaredStructureError("defined-term binding IDs are not unique")
        binding_ids.add(row["binding_id"])
        if row["term_id"] not in term_ids:
            raise DeclaredStructureError("defined-term binding target is absent")
        if text[row["span"]["start"]:row["span"]["end"]] != row["surface"]:
            raise DeclaredStructureError("defined-term binding is not exact")
    if term_payload["term_count"] != len(term_payload["terms"]) or term_payload["binding_count"] != len(term_payload["bindings"]):
        raise DeclaredStructureError("defined-term counts mismatch")

    precedence = structure["declared_precedence"]
    if precedence.get("version") != DECLARED_PRECEDENCE_VERSION:
        raise DeclaredStructureError("declared-precedence version mismatch")
    relation_ids = set()
    for row in precedence["relations"]:
        if row["relation_id"] in relation_ids:
            raise DeclaredStructureError("declared-precedence relation IDs are not unique")
        relation_ids.add(row["relation_id"])
        start, end = row["span"]["start"], row["span"]["end"]
        if not (0 <= start < end <= len(text)) or row["source_entry_id"] not in entry_ids:
            raise DeclaredStructureError("declared-precedence span/source is invalid")
        if row["relation_kind"] == "precedes":
            if not row["higher_identifier"] or not row["lower_identifier"] or row["target_identifier"] is not None:
                raise DeclaredStructureError("ordered-precedence relation fields mismatch")
        elif row["relation_kind"] == "notwithstanding":
            expected = "resolved" if row["target_identifier"] in valid_targets else "unresolved_absent"
            if row["target_outcome"] != expected or row["higher_identifier"] is not None or row["lower_identifier"] is not None:
                raise DeclaredStructureError("notwithstanding relation fields mismatch")
        else:
            raise DeclaredStructureError("declared-precedence relation kind is unsupported")
    if precedence["relation_count"] != len(precedence["relations"]):
        raise DeclaredStructureError("declared-precedence count mismatch")

    unsigned = {key: value for key, value in structure.items() if key != "structure_digest"}
    if structure["structure_digest"] != digest(unsigned):
        raise DeclaredStructureError("declared structure digest mismatch")
    return dict(structure)


def build_declared_structure(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise DeclaredStructureError("declared structure requires non-empty text")
    if len(text) > MAX_DECLARED_STRUCTURE_SOURCE_CHARS:
        raise DeclaredStructureError(
            f"declared structure source exceeds {MAX_DECLARED_STRUCTURE_SOURCE_CHARS} characters"
        )
    headings = _preliminary_headings(text)
    definitions = _definition_candidates(text, headings)
    clause_index = build_clause_index(text, definitions)
    references = resolve_references(text, clause_index)
    defined_terms = build_defined_terms(text, definitions)
    precedence = extract_declared_precedence(text, clause_index, references)
    structure = {
        "schema_version": DECLARED_STRUCTURE_VERSION,
        "source_text_sha256": text_digest(text),
        "clause_index": clause_index,
        "references": references,
        "defined_terms": defined_terms,
        "declared_precedence": precedence,
        "causation": {"derived": False, "reason": "not_self_declared"},
    }
    structure["structure_digest"] = digest(structure)
    return validate_declared_structure(structure, text)
