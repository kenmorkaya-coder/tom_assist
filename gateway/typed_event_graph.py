"""Source-bound candidate graph. Validation checks form and references, not truth.

Language interpretation belongs exclusively to the extraction model. This module
never infers a role, comparator, condition or missing event from prose.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
import re

VERSION = "tom-assist-event-graph/1"
ROLES = ("actor", "object", "source", "target", "recipient", "authority")
ACTIONS = ("stop", "continue", "notify", "discharge", "approve", "inspect", "cause", "use", "replace")
LINKS = ("before", "after", "supersedes", "conflicts", "causes", "depends_on")
# Exact rational conversion, including rate units. No prose or unit guessing.
UNITS = {"L": ("m3", Fraction(1, 1000)), "m3": ("m3", Fraction(1)),
         "L/min": ("m3/s", Fraction(1, 60000)), "L/s": ("m3/s", Fraction(1, 1000)),
         "m3/s": ("m3/s", Fraction(1)), "mm/s": ("m/s", Fraction(1, 1000)),
         "m/s": ("m/s", Fraction(1)), "mm": ("m", Fraction(1, 1000)),
         "m": ("m", Fraction(1)), "g": ("kg", Fraction(1, 1000)),
         "kg": ("kg", Fraction(1)), "s": ("s", Fraction(1)), "min": ("s", Fraction(60))}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def obj(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"expected fields {sorted(keys)}")


def string(value):
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ValueError("expected bounded nonempty string")


def quantity(value, unit):
    if not isinstance(value, str) or len(value) > 80 or not re.fullmatch(r"-?(?:0|[1-9]\d*)(?:\.\d+)?", value):
        raise ValueError("quantity must be an exact decimal string")
    if unit not in UNITS:
        raise ValueError("unsupported unit")
    try:
        amount = Fraction(Decimal(value)) * UNITS[unit][1]
    except (InvalidOperation, ValueError):
        raise ValueError("invalid quantity") from None
    return {"numerator": amount.numerator, "denominator": amount.denominator, "unit": UNITS[unit][0]}


def validate_graph(graph, text):
    """Fail closed on malformed, dangling, cyclic or unsupported structures."""
    obj(graph, ("version", "entities", "predicates", "conditions", "events", "links", "unresolved"))
    if graph["version"] != VERSION or not isinstance(text, str) or not 0 < len(text) <= 64000:
        raise ValueError("unsupported version or source length")
    tables = {}
    seen = set()

    def evidence(value):
        if not isinstance(value, list) or not value:
            raise ValueError("evidence required")
        for span in value:
            obj(span, ("start", "end", "quote"))
            start, end = span["start"], span["end"]
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
                raise ValueError("invalid evidence offsets")
            if span["quote"] != text[start:end]:
                raise ValueError("evidence mismatch")

    fields = {
        "entities": ("id", "name", "mentions"),
        "predicates": ("id", "subject", "comparator", "value", "unit", "negated", "evidence"),
        "conditions": ("id", "operator", "args", "evidence"),
        "events": ("id", "action", "roles", "modality", "negated", "condition", "exception", "complement", "revision", "time", "evidence"),
        "links": ("id", "kind", "source", "target", "evidence"),
    }
    for table, keys in fields.items():
        rows = graph[table]
        if not isinstance(rows, list) or len(rows) > 128:
            raise ValueError("invalid graph size")
        tables[table] = {}
        for row in rows:
            obj(row, keys)
            string(row["id"])
            if row["id"] in seen:
                raise ValueError("duplicate id")
            seen.add(row["id"])
            tables[table][row["id"]] = row
            evidence(row["mentions"] if table == "entities" else row["evidence"])
    if not isinstance(graph["unresolved"], list):
        raise ValueError("unresolved must be a list")
    for row in graph["unresolved"]:
        obj(row, ("reason", "evidence"))
        string(row["reason"])
        evidence(row["evidence"])

    def ref(value, kinds, nullable=False):
        if value is None and nullable:
            return
        if not isinstance(value, str) or not any(value in tables[kind] for kind in kinds):
            raise ValueError("dangling or mistyped reference")

    for row in graph["entities"]:
        string(row["name"])
    for row in graph["predicates"]:
        ref(row["subject"], ("entities",))
        if row["comparator"] not in ("LT", "LE", "EQ", "NE", "GE", "GT") or type(row["negated"]) is not bool:
            raise ValueError("invalid comparison")
        quantity(row["value"], row["unit"])
    for row in graph["conditions"]:
        if row["operator"] not in ("all", "any", "not") or not isinstance(row["args"], list):
            raise ValueError("invalid Boolean condition")
        if not row["args"] or len(set(row["args"])) != len(row["args"]) or (row["operator"] == "not" and len(row["args"]) != 1):
            raise ValueError("invalid Boolean arity")
        for arg in row["args"]:
            ref(arg, ("conditions", "predicates", "events"))
    for row in graph["events"]:
        obj(row["roles"], ROLES)
        for value in row["roles"].values():
            ref(value, ("entities",), nullable=True)
        if row["action"] not in ACTIONS or row["modality"] not in ("obligation", "permission", "assertion", "hypothetical") or type(row["negated"]) is not bool:
            raise ValueError("unsupported action, modality or negation")
        for key in ("condition", "exception"):
            ref(row[key], ("conditions", "predicates", "events"), nullable=True)
        ref(row["complement"], ("events",), nullable=True)
        for key in ("revision", "time"):
            if row[key] is not None:
                obj(row[key], ("value", "evidence"))
                string(row[key]["value"])
                evidence(row[key]["evidence"])
    for row in graph["links"]:
        if row["kind"] not in LINKS or row["source"] == row["target"]:
            raise ValueError("invalid link")
        ref(row["source"], ("events",))
        ref(row["target"], ("events",))
    # Conditions may refer to state/events, but recursive activation is unsupported.
    active, complete = set(), set()
    def visit(key):
        if key in active:
            raise ValueError("cyclic condition")
        if key in complete:
            return
        active.add(key)
        if key in tables["conditions"]:
            children = tables["conditions"][key]["args"]
        elif key in tables["events"]:
            children = [tables["events"][key][k] for k in ("condition", "exception", "complement")]
        else:
            children = []
        for child in children:
            if child is not None:
                visit(child)
        active.remove(key)
        complete.add(key)
    for key in seen:
        visit(key)
    # A successful graph cannot carry unused facts which numerical compilation
    # would silently discard. Unresolved graphs are inspectable but not loadable.
    referenced = set()
    for row in graph["events"]:
        referenced.update(v for v in row["roles"].values() if v is not None)
        referenced.update(row[k] for k in ("condition", "exception", "complement") if row[k] is not None)
    for row in graph["conditions"]:
        referenced.update(row["args"])
    for row in graph["predicates"]:
        referenced.add(row["subject"])
    required = set(tables["entities"]) | set(tables["conditions"]) | set(tables["predicates"])
    if not graph["unresolved"] and not required <= referenced:
        raise ValueError("unreferenced graph content")
    if not graph["events"] and not graph["unresolved"]:
        raise ValueError("empty successful extraction")
    return deepcopy(graph)


def semantic_graph(graph):
    """ID/evidence-independent meaning; input must have passed validate_graph.

    Array event order is source order. Explicit temporal links remain separate.
    Shared references are encoded by source-order event index.
    """
    entities = {r["id"]: r["name"] for r in graph["entities"]}
    predicates = {r["id"]: r for r in graph["predicates"]}
    conditions = {r["id"]: r for r in graph["conditions"]}
    events = {r["id"]: i for i, r in enumerate(graph["events"])}
    def condition(key):
        if key is None:
            return None
        if key in events:
            return {"event": events[key]}
        if key in predicates:
            row = predicates[key]
            return {"subject": entities[row["subject"]], "comparator": row["comparator"],
                    "quantity": quantity(row["value"], row["unit"]), "negated": row["negated"]}
        row = conditions[key]
        return {"operator": row["operator"], "args": sorted([condition(k) for k in row["args"]], key=canonical)}
    result = []
    for row in graph["events"]:
        result.append({"action": row["action"], "roles": {k: entities[v] if v else None for k, v in row["roles"].items()},
                       "modality": row["modality"], "negated": row["negated"],
                       "condition": condition(row["condition"]), "exception": condition(row["exception"]),
                       "complement": condition(row["complement"]),
                       "revision": row["revision"]["value"] if row["revision"] else None,
                       "time": row["time"]["value"] if row["time"] else None})
    return {"events": result, "links": [{"kind": r["kind"], "source": events[r["source"]], "target": events[r["target"]]} for r in graph["links"]]}
