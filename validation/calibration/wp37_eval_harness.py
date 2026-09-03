#!/usr/bin/env python3
"""Score two retrieval rankings against separately supplied external labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


RANKING_SCHEMA = "tom-assist-wp37-ranking-input/1.0"
LABEL_SCHEMA = "tom-assist-wp37-external-relevance-labels/1.0"
RESULT_SCHEMA = "tom-assist-wp37-relevance-evaluation/1.0"


def _ids(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of record IDs")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} contains duplicate record IDs")
    return value


def _precision(ranking: Sequence[str], relevant: set[str], k: int) -> float:
    return len(set(ranking[:k]) & relevant) / float(k)


def _reciprocal_rank(ranking: Sequence[str], relevant: set[str]) -> float:
    for rank, record_id in enumerate(ranking, 1):
        if record_id in relevant:
            return 1.0 / rank
    return 0.0


def evaluate_external_labels(
    rankings: Mapping[str, Any], labels: Mapping[str, Any],
    *, precision_at: Sequence[int] = (1, 3, 5),
) -> dict[str, Any]:
    if rankings.get("schema_version") != RANKING_SCHEMA:
        raise ValueError("unsupported ranking schema")
    if labels.get("schema_version") != LABEL_SCHEMA:
        raise ValueError("unsupported external-label schema")
    provenance = str(labels.get("provenance") or "").strip()
    if not provenance:
        raise ValueError("external labels require nonempty provenance")
    cutoffs = sorted(set(int(value) for value in precision_at))
    if not cutoffs or any(value <= 0 for value in cutoffs):
        raise ValueError("precision cutoffs must be positive")

    ranking_rows = rankings.get("queries")
    label_rows = labels.get("queries")
    if not isinstance(ranking_rows, list) or not isinstance(label_rows, list):
        raise ValueError("rankings and labels require query lists")
    relevance: dict[str, set[str]] = {}
    for row in label_rows:
        query_id = str(row.get("query_id") or "")
        if not query_id or query_id in relevance:
            raise ValueError("external labels require unique nonempty query IDs")
        relevant = set(_ids(row.get("relevant_ids"), f"labels[{query_id}].relevant_ids"))
        if not relevant:
            raise ValueError(f"labels[{query_id}] must contain at least one relevant ID")
        relevance[query_id] = relevant

    per_query = []
    seen: set[str] = set()
    for row in ranking_rows:
        query_id = str(row.get("query_id") or "")
        if not query_id or query_id in seen:
            raise ValueError("rankings require unique nonempty query IDs")
        seen.add(query_id)
        if query_id not in relevance:
            raise ValueError(f"missing external labels for query {query_id}")
        current = _ids(row.get("current"), f"rankings[{query_id}].current")
        proposed = _ids(row.get("proposed"), f"rankings[{query_id}].proposed")
        relevant = relevance[query_id]
        current_precision = {
            str(k): _precision(current, relevant, k) for k in cutoffs
        }
        proposed_precision = {
            str(k): _precision(proposed, relevant, k) for k in cutoffs
        }
        current_rr = _reciprocal_rank(current, relevant)
        proposed_rr = _reciprocal_rank(proposed, relevant)
        per_query.append({
            "query_id": query_id,
            "current": {
                "precision_at_k": current_precision,
                "reciprocal_rank": current_rr,
            },
            "proposed": {
                "precision_at_k": proposed_precision,
                "reciprocal_rank": proposed_rr,
            },
            "delta_proposed_minus_current": {
                "precision_at_k": {
                    str(k): proposed_precision[str(k)] - current_precision[str(k)]
                    for k in cutoffs
                },
                "reciprocal_rank": proposed_rr - current_rr,
            },
        })
    extra = sorted(relevance.keys() - seen)
    if extra:
        raise ValueError(f"external labels have queries absent from rankings: {extra}")
    if not per_query:
        raise ValueError("at least one labelled query is required")

    count = len(per_query)
    aggregate = {
        "query_count": count,
        "current": {
            "mean_precision_at_k": {
                str(k): sum(row["current"]["precision_at_k"][str(k)] for row in per_query) / count
                for k in cutoffs
            },
            "mean_reciprocal_rank": sum(
                row["current"]["reciprocal_rank"] for row in per_query
            ) / count,
        },
        "proposed": {
            "mean_precision_at_k": {
                str(k): sum(row["proposed"]["precision_at_k"][str(k)] for row in per_query) / count
                for k in cutoffs
            },
            "mean_reciprocal_rank": sum(
                row["proposed"]["reciprocal_rank"] for row in per_query
            ) / count,
        },
    }
    aggregate["delta_proposed_minus_current"] = {
        "mean_precision_at_k": {
            str(k): (
                aggregate["proposed"]["mean_precision_at_k"][str(k)]
                - aggregate["current"]["mean_precision_at_k"][str(k)]
            )
            for k in cutoffs
        },
        "mean_reciprocal_rank": (
            aggregate["proposed"]["mean_reciprocal_rank"]
            - aggregate["current"]["mean_reciprocal_rank"]
        ),
    }
    return {
        "schema_version": RESULT_SCHEMA,
        "label_provenance": provenance,
        "precision_cutoffs": cutoffs,
        "per_query": per_query,
        "aggregate": aggregate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rankings", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--precision-at", type=int, nargs="+", default=[1, 3, 5])
    args = parser.parse_args()
    result = evaluate_external_labels(
        json.loads(args.rankings.read_text(encoding="utf-8")),
        json.loads(args.labels.read_text(encoding="utf-8")),
        precision_at=args.precision_at,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
