"""Build the frozen JSON Schema from the same enums as the runtime validator."""
import json
from pathlib import Path
from gateway.typed_event_graph import VERSION, ROLES, ACTIONS, LINKS, UNITS


def object_of(properties):
    return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": 128}


def ref(name):
    return {"$ref": f"#/$defs/{name}"}


def make_schema():
    string = {"type": "string", "minLength": 1, "maxLength": 1024}
    nullable = {"anyOf": [string, {"type": "null"}]}
    boolean = {"type": "boolean"}
    evidence = array(ref("span"), 1)
    defs = {"span": object_of({"start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1}, "quote": string})}
    defs["annotation"] = object_of({"value": string, "evidence": evidence})
    defs["entity"] = object_of({"id": string, "name": string, "mentions": evidence})
    defs["predicate"] = object_of({"id": string, "subject": string, "comparator": {"enum": ["LT", "LE", "EQ", "NE", "GE", "GT"]},
                                  "value": {"type": "string", "maxLength": 80, "pattern": r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$"},
                                  "unit": {"enum": list(UNITS)}, "negated": boolean, "evidence": evidence})
    defs["condition"] = object_of({"id": string, "operator": {"enum": ["all", "any", "not"]}, "args": array(string, 1), "evidence": evidence})
    defs["event"] = object_of({"id": string, "action": {"enum": list(ACTIONS)}, "roles": object_of(dict.fromkeys(ROLES, nullable)),
                              "modality": {"enum": ["obligation", "permission", "assertion", "hypothetical"]}, "negated": boolean,
                              "condition": nullable, "exception": nullable, "complement": nullable,
                              "revision": {"anyOf": [ref("annotation"), {"type": "null"}]},
                              "time": {"anyOf": [ref("annotation"), {"type": "null"}]}, "evidence": evidence})
    defs["link"] = object_of({"id": string, "kind": {"enum": list(LINKS)}, "source": string, "target": string, "evidence": evidence})
    defs["unresolved"] = object_of({"reason": string, "evidence": evidence})
    schema = object_of({"version": {"const": VERSION}, **{k: array(ref(v)) for k, v in {
        "entities": "entity", "predicates": "predicate", "conditions": "condition", "events": "event", "links": "link", "unresolved": "unresolved"}.items()}})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": defs, **schema}

if __name__ == "__main__":
    Path(__file__).with_name("schema.json").write_text(json.dumps(make_schema(), indent=2) + "\n")
