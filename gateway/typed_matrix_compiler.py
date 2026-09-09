"""Experimental evidence-bound typed compiler; not wired into the app.

No generation, Tree access or embedding invocation occurs in this module.
Callers supply local embeddings of the prepared, symbol-masked field text.
Unsupported syntax is an explicit error, never a successful omission.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from gateway.matrix_events import validate_matrix_event_candidate


VERSION = "tom-assist-typed-matrix-compiler/1-experimental"
SEED = 539362568
FIELD_NAMES = ("source", "target", "relation", "context")
MASK64 = (1 << 64) - 1


class UnsupportedTypedEvent(ValueError):
    pass


SMALL = dict(zip(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(),
    range(20), strict=True,
))
TENS = dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10), strict=True))
NUMBER_WORDS = set(SMALL) | set(TENS) | {"hundred", "thousand", "million", "and", "point", "minus", "negative"}
UNIT_TABLE = {
    "kg": ("kg", "1"), "kilogram": ("kg", "1"), "kilograms": ("kg", "1"),
    "g": ("kg", "0.001"), "gram": ("kg", "0.001"), "grams": ("kg", "0.001"),
    "t": ("kg", "1000"), "tonne": ("kg", "1000"), "tonnes": ("kg", "1000"),
    "m": ("m", "1"), "metre": ("m", "1"), "metres": ("m", "1"),
    "mm": ("m", "0.001"), "millimetre": ("m", "0.001"), "millimetres": ("m", "0.001"),
    "cm": ("m", "0.01"), "centimetres": ("m", "0.01"),
    "pa": ("Pa", "1"), "pascals": ("Pa", "1"),
    "kpa": ("Pa", "1000"), "kilopascals": ("Pa", "1000"),
    "mpa": ("Pa", "1000000"), "megapascals": ("Pa", "1000000"),
    "m/s": ("m/s", "1"), "metres per second": ("m/s", "1"),
    "mm/s": ("m/s", "0.001"), "millimetres per second": ("m/s", "0.001"),
    "l/s": ("m3/s", "0.001"), "litres per second": ("m3/s", "0.001"),
    "m3/s": ("m3/s", "1"), "cubic metres per second": ("m3/s", "1"),
    "degrees celsius": ("degC", "1"), "degree celsius": ("degC", "1"), "°c": ("degC", "1"),
}
UNIT_RE = re.compile(r"(?<![A-Za-z])(?:" + "|".join(re.escape(x) for x in sorted(UNIT_TABLE, key=len, reverse=True)) + r")(?!\w)", re.I)
NUMERIC_RE = re.compile(r"(?<![\w.])[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?![\w.])")
COMPARATORS = {
    "no more than": "LE", "at most": "LE", "not more than": "LE",
    "no less than": "GE", "at least": "GE", "not less than": "GE", "a minimum of": "GE", "minimum of": "GE",
    "greater than": "GT", "higher than": "GT", "exceeds": "GT", "above": "GT",
    "falls below": "LT", "lower than": "LT", "less than": "LT", "below": "LT",
    "equals": "EQ", "equal to": "EQ", "exactly": "EQ",
    "<=": "LE", ">=": "GE", "≤": "LE", "≥": "GE", "<": "LT", ">": "GT", "=": "EQ",
}
COMPARATOR_RE = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(x) for x in sorted(COMPARATORS, key=len, reverse=True) if x[0].isalpha())
    + r")(?!\w)|(?:<=|>=|≤|≥|<|>|=)", re.I,
)
CONDITION_RE = re.compile(r"\b(?:only if|even if|only after|even after|only with|even with|without|unless|whenever|when|before|after|if)\b", re.I)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise UnsupportedTypedEvent("NONFINITE_QUANTITY")
    with localcontext() as context:
        context.prec = 128
        return "0" if value == 0 else format(value.normalize(), "f")


def parse_number(text: str) -> Decimal:
    clean = text.strip().lower()
    if len(clean) > 128:
        raise UnsupportedTypedEvent("NUMBER_EXCEEDS_EXACT_PRECISION_BOUND")
    if re.fullmatch(r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)", clean):
        if len(re.sub(r"\D", "", clean)) > 64:
            raise UnsupportedTypedEvent("NUMBER_EXCEEDS_EXACT_PRECISION_BOUND")
        return Decimal(clean)
    words = clean.replace("-", " ").split()
    sign = -1 if words and words[0] in {"minus", "negative"} else 1
    if sign == -1:
        words = words[1:]
    if not words or any(w not in NUMBER_WORDS for w in words):
        raise UnsupportedTypedEvent("UNSUPPORTED_NUMBER")
    if "point" in words:
        if words.count("point") != 1:
            raise UnsupportedTypedEvent("AMBIGUOUS_DECIMAL")
        position = words.index("point")
        whole, fraction = words[:position], words[position + 1:]
        if not fraction or any(w not in SMALL or SMALL[w] > 9 for w in fraction):
            raise UnsupportedTypedEvent("UNSUPPORTED_DECIMAL_DIGITS")
        return sign * (parse_number(" ".join(whole or ["zero"])) + Decimal("0." + "".join(str(SMALL[w]) for w in fraction)))
    total = group = 0
    previous = None
    for word in words:
        if word == "and":
            if previous not in {"hundred", "thousand", "million"}:
                raise UnsupportedTypedEvent("AMBIGUOUS_NUMBER_SEQUENCE")
        elif word in SMALL:
            if previous in SMALL or (previous in TENS and SMALL[word] >= 10):
                raise UnsupportedTypedEvent("AMBIGUOUS_NUMBER_SEQUENCE")
            group += SMALL[word]
        elif word in TENS:
            if previous in SMALL or previous in TENS:
                raise UnsupportedTypedEvent("AMBIGUOUS_NUMBER_SEQUENCE")
            group += TENS[word]
        elif word == "hundred":
            if previous not in SMALL or not 1 <= group <= 9:
                raise UnsupportedTypedEvent("AMBIGUOUS_HUNDREDS")
            group *= 100
        elif word in {"thousand", "million"}:
            if group == 0:
                raise UnsupportedTypedEvent("AMBIGUOUS_SCALE")
            total += group * (1000 if word == "thousand" else 1000000)
            group = 0
        else:
            raise UnsupportedTypedEvent("UNSUPPORTED_NUMBER")
        previous = word
    return Decimal(sign * (total + group))


def _quantity(text: str) -> list[dict[str, Any]]:
    found = []
    for unit_match in UNIT_RE.finditer(text):
        prefix = text[:unit_match.start()].rstrip()
        digit = re.search(r"(?<![\w.])[-+]?(?:\d+(?:\.\d+)?|\.\d+)$", prefix)
        if digit:
            start = digit.start()
        else:
            tokens = list(re.finditer(r"[A-Za-z]+(?:-[A-Za-z]+)?", prefix))
            if not tokens or tokens[-1].end() != len(prefix):
                continue
            start = len(prefix)
            for token in reversed(tokens):
                if not all(w in NUMBER_WORDS for w in token.group().lower().split("-")):
                    break
                start = token.start()
            if start == len(prefix):
                continue
        number_text = prefix[start:]
        # A dash attached to another number is a range, not a negative sign.
        if start and text[start - 1].isdigit():
            raise UnsupportedTypedEvent("UNSUPPORTED_RANGE")
        value = parse_number(number_text)
        unit, factor = UNIT_TABLE[unit_match.group().lower()]
        end = unit_match.end()
        with localcontext() as context:
            context.prec = 128
            converted = canonical_decimal(value * Decimal(factor))
        found.append({"kind": "quantity", "value": converted, "unit": unit,
                      "start": start, "end": end, "quote": text[start:end]})
    if len(found) > 1:
        raise UnsupportedTypedEvent("MULTIPLE_QUANTITIES_REQUIRE_EXPLICIT_SCOPE")
    return found


def field_record(text: str) -> dict[str, Any]:
    """Bind and mask a bounded symbolic field; no source text is fabricated."""
    atoms = _quantity(text)
    for match in COMPARATOR_RE.finditer(text):
        atoms.append({"kind": "comparator", "operator": COMPARATORS[match.group().lower()],
                      "start": match.start(), "end": match.end(), "quote": match.group()})
    quantities = [a for a in atoms if a["kind"] == "quantity"]
    comparisons = [a for a in atoms if a["kind"] == "comparator"]
    if quantities and not comparisons:
        prefix = text[:quantities[0]["start"]]
        bound = re.search(r"\blimit\b[^,.;]*?\bto\s*$", prefix, re.I)
        at = re.search(r"\bat\s*$", prefix, re.I)
        if bound or at:
            match = bound or at
            end = match.start() + 5 if bound else match.end()
            atoms.append({"kind": "comparator", "operator": "LE" if bound else "EQ",
                          "start": match.start(), "end": end, "quote": text[match.start():end]})
    comparisons = [a for a in atoms if a["kind"] == "comparator"]
    if len(comparisons) > 1:
        raise UnsupportedTypedEvent("MULTIPLE_COMPARATORS_REQUIRE_EXPLICIT_SCOPE")
    if comparisons and not quantities:
        raise UnsupportedTypedEvent("COMPARATOR_WITHOUT_SUPPORTED_QUANTITY")
    if quantities and re.search(r"\b(?:approximately|about|around|between|roughly)\b", text, re.I):
        raise UnsupportedTypedEvent("UNSUPPORTED_APPROXIMATION_OR_RANGE")
    masked = text
    for atom in sorted(atoms, key=lambda a: a["start"], reverse=True):
        masked = masked[:atom["start"]] + (" typed quantity " if atom["kind"] == "quantity" else " typed comparator ") + masked[atom["end"]:]
    if NUMERIC_RE.search(masked) or re.search(r"\b(?:revision|rev\.?|asset\s+id|document\s+id)\s+\S+", masked, re.I):
        raise UnsupportedTypedEvent("UNSUPPORTED_EXACT_IDENTIFIER_OR_UNITLESS_NUMBER")
    if any(token in SMALL or token in TENS or token in {"hundred", "thousand", "million"}
           for token in re.findall(r"[a-z]+", masked.lower())):
        raise UnsupportedTypedEvent("UNSUPPORTED_UNITLESS_OR_UNKNOWN_UNIT_NUMBER")
    symbols = [{k: v for k, v in atom.items() if k not in {"start", "end", "quote"}} for atom in sorted(atoms, key=lambda a: (a["kind"], a["start"]))]
    return {"text": text, "semantic_text": " ".join(masked.split()), "symbols": symbols, "evidence": atoms}


def _bound_context(event: Mapping[str, Any], source_text: str) -> dict[str, Any]:
    explicit = event["context_evidence"]
    relation = event["relation_evidence"]
    # Prefer an actual condition in the relation span over an ambient label.
    matches = list(CONDITION_RE.finditer(relation["quote"]))
    if len(matches) > 1:
        raise UnsupportedTypedEvent("MULTIPLE_CONDITIONS_REQUIRE_EXPLICIT_SCOPE")
    if matches:
        start_local = matches[0].start()
        suffix = relation["quote"][start_local:]
        quote = re.split(r"[,;]|\.(?=\s|$)", suffix, maxsplit=1)[0].strip()
        # A paragraph cannot safely be assigned one condition by this adapter.
        if re.search(r"\b(?:and|or)\b", quote, re.I):
            raise UnsupportedTypedEvent("COMPOUND_CONDITION_REQUIRES_TYPED_SCOPE")
        start = relation["start"] + start_local
        result = {"start": start, "end": start + len(quote), "quote": quote, "binding": "bounded-condition"}
    elif explicit is not None:
        result = {**explicit, "binding": "explicit-context"}
    else:
        ambient = re.match(r"(?:During|Throughout)\s+([^,]+),", relation["quote"])
        if ambient is None:
            raise UnsupportedTypedEvent("MISSING_EXACT_CONTEXT")
        start = relation["start"] + ambient.start(1)
        result = {"start": start, "end": start + len(ambient.group(1)), "quote": ambient.group(1), "binding": "bounded-ambient"}
    if source_text[result["start"]:result["end"]] != result["quote"]:
        raise UnsupportedTypedEvent("CONTEXT_SOURCE_MISMATCH")
    return result


def prepare_candidate(candidate: Mapping[str, Any], source_text: str) -> dict[str, Any]:
    bound = validate_matrix_event_candidate(candidate, source_text)
    if bound["unknown_relations"] or not bound["events"]:
        raise UnsupportedTypedEvent("UNRESOLVED_OR_EMPTY_EVENTS")
    events = []
    for event in bound["events"]:
        if event["source_evidence"] is None or event["target_evidence"] is None:
            raise UnsupportedTypedEvent("QUERY_ENDPOINT_UNSUPPORTED_IN_COMPILER_BATTERY")
        context = _bound_context(event, source_text)
        fields = {
            "source": field_record(event["source_evidence"]["quote"]),
            "target": field_record(event["target_evidence"]["quote"]),
            "relation": {"text": event["relation_kind"], "semantic_text": event["relation_kind"],
                         "symbols": [{"kind": "modality", "value": event["modality"]}, {"kind": "polarity", "negated": event["negated"]}],
                         "evidence": [deepcopy(event["relation_evidence"])]},
            "context": field_record(context["quote"]),
        }
        events.append({"event": event, "context": context, "fields": fields})
    return {"version": VERSION, "source_digest": bound["source_text_sha256"], "events": events}


def semantic_texts(prepared: Mapping[str, Any]) -> set[str]:
    return {f["semantic_text"] for row in prepared["events"] for f in row["fields"].values()}


def normalize(values: Sequence[float]) -> list[float]:
    if not values or not all(math.isfinite(float(x)) for x in values):
        raise ValueError("invalid compiler vector")
    norm = math.sqrt(sum(float(x) ** 2 for x in values))
    if norm < 1e-12:
        raise ValueError("compiler vector collapsed")
    return [float(x) / norm for x in values]


def project(values: Sequence[float]) -> list[float]:
    """Byte-for-byte formula of the pinned projection; no calibration import."""
    if len(values) != 384:
        raise ValueError("expected 384-dimensional MiniLM vector")
    def splitmix(value: int) -> int:
        value = (value + 0x9E3779B97F4A7C15) & MASK64
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        return (value ^ (value >> 31)) & MASK64
    result = []
    for i in range(32):
        total = 0.0
        for j, value in enumerate(values):
            key = (SEED ^ ((i + 1) * 0xD6E8FEB86659FD93) ^ ((j + 1) * 0xA5A35625AA5A3563)) & MASK64
            sign = 1.0 if splitmix(key) & 1 else -1.0
            total += sign * float(value)
        result.append(total * (1.0 / math.sqrt(32.0)))
    return normalize(result)


def symbol_vector(symbols: Sequence[Mapping[str, Any]]) -> list[float]:
    payload = b"tom-assist-typed-field/1\0" + canonical_json(symbols)
    raw = b"".join(hashlib.sha256(payload + i.to_bytes(4, "big")).digest() for i in range(4))
    return normalize([(int.from_bytes(raw[i * 4:i * 4 + 4], "big") + 0.5) / 2**32 - 0.5 for i in range(32)])


def compile_prepared(prepared: Mapping[str, Any], embeddings: Mapping[str, Sequence[float]], *, ablate_symbols: bool = False) -> dict[str, Any]:
    if prepared["version"] != VERSION:
        raise ValueError("unsupported typed compiler version")
    views, telemetry = [], []
    for row in prepared["events"]:
        fields = {}
        for name in FIELD_NAMES:
            field = row["fields"][name]
            semantic = project(embeddings[field["semantic_text"]])
            symbols = field["symbols"]
            fields[name] = normalize([a + b for a, b in zip(semantic, symbol_vector(symbols), strict=True)]) if symbols and not ablate_symbols else semantic
        event_views = []
        for left, right in (("source", "target"), ("source", "context"), ("context", "target")):
            raw = [fields[left][i] * fields[right][j] + 0.5 * fields["relation"][i] * fields["relation"][j] + 0.25 * fields["context"][i] * fields["context"][j]
                   for i in range(32) for j in range(32)]
            event_views.append(normalize(raw))
        views.extend(event_views)
        telemetry.append({"event_id": row["event"]["id"], "fields32": fields, "views": event_views})
    matrix = normalize([sum(view[i] for view in views) for i in range(1024)])
    if any(x == 0 for x in matrix):
        raise ValueError("matrix contains exact zero")
    return {"version": VERSION, "matrix": matrix, "events": telemetry, "ablate_symbols": ablate_symbols,
            "matrix_sha256": hashlib.sha256(canonical_json(matrix)).hexdigest()}
