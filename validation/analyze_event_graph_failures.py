"""Post-hoc read-only diagnosis. Never changes the frozen verdict or predictions."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gateway.event_graph_extractor import bind_quotes
from gateway.typed_event_graph import semantic_graph


def diagnose(run):
    report = json.loads((run / "heldout_extraction_report.json").read_text())
    expected = {r["id"]: r for r in (json.loads(line) for line in
                (ROOT / "validation/event_graph_v1/data/heldout.jsonl").read_text().splitlines())}
    counts, examples, by_family = Counter(), {}, {}
    for line in (run / "heldout_predictions.jsonl").read_text().splitlines():
        row = json.loads(line); gold = expected[row["id"]]
        raw = row["raw"].strip()
        fence = re.fullmatch(r"```(?:json)?\s*\n(.*)\n```", raw, flags=re.DOTALL)
        if fence:
            counts["single_markdown_fence"] += 1
            raw = fence.group(1)
        try:
            graph = bind_quotes(json.loads(raw), gold["source"])
            if graph["unresolved"]:
                raise ValueError("unresolved clauses")
            actual, target = semantic_graph(graph), semantic_graph(gold["graph"])
            exact = actual == target
            category = "exact_after_presentation_only_unwrap" if exact else "semantic_mismatch"
            if not exact:
                for key in ("action", "roles", "modality", "negated", "condition", "exception", "complement", "revision", "time"):
                    if [e[key] for e in actual["events"]] != [e[key] for e in target["events"]]:
                        counts[f"semantic_difference:{key}"] += 1
                if actual["links"] != target["links"]:
                    counts["semantic_difference:links"] += 1
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            category = f"remaining_validation_failure:{exc}"
        counts[category] += 1
        by_family.setdefault(gold["family"], Counter())[category] += 1
        examples.setdefault(category, [])
        if len(examples[category]) < 3:
            examples[category].append(row["id"])
    return {"status": "POST_HOC_DIAGNOSTIC_ONLY", "frozen_verdict": report["verdict"],
            "warning": "Presentation-only unwrapping is not an authorized gate repair for this frozen run. No new model calls or numerical compilation occurred.",
            "counts": counts, "by_family": by_family, "examples": examples}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    result = diagnose(args.run)
    with (args.run / "failure_analysis.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result["counts"], indent=2))
