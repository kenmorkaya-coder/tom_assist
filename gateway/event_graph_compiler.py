"""Experimental typed-only graph compiler: one signed load per event/link.

No raw-prose interpretation, model, embeddings, Tree access or paragraph pooling.
The frozen outer-product equation retains weights 1, 0.5 and 0.25. Hash codes
represent identity, not numeric order, logical execution or collision freedom.
"""
import hashlib
import math
from gateway.typed_event_graph import canonical, digest, semantic_graph, validate_graph

VERSION = "tom-assist-graph-loads/1-experimental"
SEED = 539362568


def normalize(values):
    norm = math.sqrt(sum(v * v for v in values))
    if norm < 1e-12 or not math.isfinite(norm):
        raise ValueError("collapsed or nonfinite load")
    return [v / norm for v in values]


def code(value):
    payload = f"{VERSION}\0{SEED}\0{canonical(value)}".encode()
    raw = b"".join(hashlib.sha256(payload + i.to_bytes(4, "big")).digest() for i in range(4))
    return normalize([(int.from_bytes(raw[i:i + 4], "big") + .5) / 2**32 - .5 for i in range(0, 128, 4)])


def compile_graph(graph, text, *, ablate_symbols=False):
    graph = validate_graph(graph, text)
    if graph["unresolved"]:
        raise ValueError("unresolved extraction cannot be compiled")
    semantics = semantic_graph(graph)
    loads = []
    def emit(identifier, kind, ordinal, source, target, relation, context):
        # Ablation removes structured content while retaining source/target roles.
        if ablate_symbols:
            relation, context = {"kind": kind}, {"ablated": True}
        s, t, r, c = map(code, (source, target, relation, context))
        values = normalize([s[i] * t[j] + .5 * r[i] * r[j] + .25 * c[i] * c[j]
                            for i in range(32) for j in range(32)])
        loads.append({"id": identifier, "kind": kind, "ordinal": ordinal,
                      "matrix": [values[i:i + 32] for i in range(0, 1024, 32)],
                      "matrix_sha256": digest(values)})
    for ordinal, (original, event) in enumerate(zip(graph["events"], semantics["events"], strict=True)):
        roles = event["roles"]
        source = {k: roles[k] for k in ("actor", "source", "authority")}
        target = {k: roles[k] for k in ("object", "target", "recipient")}
        emit(original["id"], "event", ordinal, source, target,
             {k: event[k] for k in ("action", "modality", "negated")},
             {k: event[k] for k in ("condition", "exception", "complement", "revision", "time")})
    for ordinal, (original, link) in enumerate(zip(graph["links"], semantics["links"], strict=True)):
        emit(original["id"], "link", ordinal,
             {"event": link["source"], "meaning": semantics["events"][link["source"]]},
             {"event": link["target"], "meaning": semantics["events"][link["target"]]},
             {"kind": link["kind"]}, {"kind": "explicit_link"})
    return {"version": VERSION, "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "graph_sha256": digest(graph), "semantic_sha256": digest(semantics),
            "ablate_symbols": ablate_symbols, "loads": loads,
            "event_order": [e["id"] for e in graph["events"]], "links": graph["links"]}
