#!/usr/bin/env python3
"""Run the frozen retrieval test on the actual matrix-native research Tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gateway.document_ingestion import (  # noqa: E402
    DocumentEmbeddingWorkerClient,
    build_document_query_profile,
)
from validation.calibration.matrix_tree_32sq_runner import (  # noqa: E402
    MODEL_PATH,
    MODEL_REVISION,
    cosine,
    event_matrix,
)


FIXTURE_PATH = ROOT / "validation" / "calibration" / "dynamic_matrix_tree_fixture.json"
PREREGISTRATION_PATH = (
    ROOT / "validation" / "calibration" / "DYNAMIC_MATRIX_TREE_PREREGISTRATION.md"
)
EXPECTED_FIXTURE_SHA256 = (
    "3dffeab09d1c0db5d33294a5e8a78da50ac652b46414431282b23e6075342439"
)
TOLERANCE = 1e-10
ROUTE_MATCH_TOLERANCE = 1e-12


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(value: Any, message: str) -> None:
    if not value:
        raise AssertionError(message)


def git_output(root: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=root, text=True, stderr=subprocess.STDOUT,
    )


def validate_fixture(value: Any) -> dict[str, Any]:
    required = {
        "version", "purpose", "matrix_native", "minilm", "matrix", "load",
        "readout", "passages", "queries", "diagnostic_expectations",
    }
    require(isinstance(value, Mapping) and set(value) == required, "fixture inventory changed")
    fixture = dict(value)
    native = fixture["matrix_native"]
    require(native["dimension"] == 32, "matrix-native dimension changed")
    require(native["starting_branches"] == 4000, "starting Tree size changed")
    require(native["prior_matrix_growth_events"] == 505, "growth lineage changed")
    require(native["preparation_scheduler_must_be_disabled"] is True, "preparation boundary changed")
    require(fixture["minilm"] == {"revision": MODEL_REVISION, "dimension": 384}, "MiniLM pin changed")
    require(fixture["readout"]["fixed_k"] == [1, 3, 5], "fixed depths changed")
    require(fixture["readout"]["hybrid_minilm_weight"] == 0.5, "hybrid weight changed")
    require(fixture["readout"]["hybrid_tree_weight"] == 0.5, "hybrid weight changed")
    require(len(fixture["passages"]) == 16, "passage inventory changed")
    require(len(fixture["queries"]) == 8, "query inventory changed")
    passage_ids = [row["id"] for row in fixture["passages"]]
    require(len(set(passage_ids)) == len(passage_ids), "duplicate passage ID")
    for row in [*fixture["passages"], *fixture["queries"]]:
        require(set(row["event"]) == {"source", "target", "relation", "context"}, "event shape changed")
    for row in fixture["queries"]:
        relevant = row["relevant_passage_ids"]
        require(len(relevant) == 1 and relevant[0] in passage_ids, "query relevance changed")
    return fixture


def copy_runtime_source(
    source_root: Path,
    destination: Path,
    checkpoint_sources: Mapping[str, str],
    apparatus_sources: Mapping[str, str],
) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError("runtime source snapshot already exists")
    destination.mkdir(parents=True)
    inventory = dict(checkpoint_sources)
    inventory.update(apparatus_sources)
    for relative, expected in sorted(inventory.items()):
        source = (source_root / relative).resolve()
        require(source.is_relative_to(source_root), "source path escapes repository")
        require(source.is_file(), f"missing matrix-native source: {relative}")
        require(sha256_file(source) == expected, f"matrix-native source drift: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        require(sha256_file(target) == expected, f"source snapshot mismatch: {relative}")
    return {
        "file_count": len(inventory),
        "manifest_sha256": sha256_bytes(canonical_json(dict(sorted(inventory.items())))),
        "checkpoint_bound_file_count": len(checkpoint_sources),
        "apparatus_file_count": len(apparatus_sources),
    }


def embedding_worker() -> DocumentEmbeddingWorkerClient:
    script = ROOT / "gateway" / "document_embedding_worker.py"
    return DocumentEmbeddingWorkerClient([
        sys.executable,
        str(script.resolve()),
        "--model",
        str(MODEL_PATH.resolve()),
    ])


def embed_all(fixture: Mapping[str, Any]) -> dict[str, list[float]]:
    texts = {
        str(row["text"])
        for row in [*fixture["passages"], *fixture["queries"]]
    }
    texts.update(
        str(text)
        for row in [*fixture["passages"], *fixture["queries"]]
        for text in row["event"].values()
    )
    provider = embedding_worker()
    try:
        return {
            text: [
                float(item)
                for item in build_document_query_profile(text, provider)["passage_vector"]
            ]
            for text in sorted(texts)
        }
    finally:
        provider.close()


def matrix_from_row(
    row: Mapping[str, Any],
    embeddings: Mapping[str, Sequence[float]],
    matrix_config: Mapping[str, Any],
) -> np.ndarray:
    result = np.asarray(
        event_matrix(row["event"], embeddings, matrix_config), dtype=np.float64,
    ).reshape(32, 32)
    require(np.isfinite(result).all(), "compiled matrix is nonfinite")
    require(not np.any(result == 0.0), "compiled matrix contains an exact zero")
    require(abs(float(np.vdot(result, result).real) - 1.0) <= 1e-12, "compiled matrix is not unit energy")
    require(np.any(result > 0.0) and np.any(result < 0.0), "compiled matrix lost signed content")
    return result


def receipt_digest(receipt: Mapping[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for branch_id, matrix in receipt.items():
        digest.update(branch_id.encode("utf-8") + b"\0")
        digest.update(np.ascontiguousarray(matrix, dtype=np.float64).tobytes())
    return digest.hexdigest()


def receipt_energy(receipt: Mapping[str, np.ndarray]) -> float:
    return math.fsum(float(np.vdot(value, value).real) for value in receipt.values())


def tree_receipt_cosine(
    receipt: Mapping[str, np.ndarray], query_local: Mapping[str, np.ndarray],
) -> tuple[float, float, int]:
    passage_energy = receipt_energy(receipt)
    surviving = [branch_id for branch_id in receipt if branch_id in query_local]
    surviving_passage_energy = math.fsum(
        float(np.vdot(receipt[branch_id], receipt[branch_id]).real)
        for branch_id in surviving
    )
    query_energy = math.fsum(
        float(np.vdot(query_local[branch_id], query_local[branch_id]).real)
        for branch_id in surviving
    )
    require(passage_energy > 0.0, "empty passage receipt")
    require(query_energy > 0.0, "query has no energy in surviving receipt branches")
    numerator = math.fsum(
        float(np.vdot(receipt[branch_id], query_local[branch_id]).real)
        for branch_id in surviving
    )
    score = numerator / math.sqrt(passage_energy * query_energy)
    require(math.isfinite(score) and -1.000000000001 <= score <= 1.000000000001, "invalid Tree receipt cosine")
    return max(-1.0, min(1.0, score)), surviving_passage_energy / passage_energy, len(surviving)


def rank_scores(scores: Mapping[str, float]) -> list[dict[str, Any]]:
    return [
        {"passage_id": passage_id, "rank": rank, "score": float(score)}
        for rank, (passage_id, score) in enumerate(
            sorted(scores.items(), key=lambda item: (-item[1], item[0])), 1,
        )
    ]


def stage_result(
    scores: Mapping[str, float], relevant: str, fixed_k: Sequence[int],
) -> dict[str, Any]:
    ranked = rank_scores(scores)
    relevant_rank = next(row["rank"] for row in ranked if row["passage_id"] == relevant)
    return {
        "relevant_passage_id": relevant,
        "relevant_rank": relevant_rank,
        "correct_at_k": {str(k): relevant_rank <= k for k in fixed_k},
        "ranking": ranked,
    }


def import_native_snapshot(runtime_root: Path, checkpoint: Path) -> tuple[Any, Any]:
    sys.path.insert(0, str(runtime_root / "src"))
    sys.path.insert(0, str(runtime_root))
    from CODEX_TEST_FILES.real_tree_capability_recovery import common
    from experiments.distributed_readout_repair_v1.readout import route

    common.CHECKPOINT = checkpoint
    return common, route


def source_files_unchanged(source_root: Path, expected: Mapping[str, str]) -> bool:
    return all(
        (source_root / relative).is_file()
        and sha256_file(source_root / relative) == digest
        for relative, digest in expected.items()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--frozen-runtime-source",
        type=Path,
        help="Previously verified source snapshot to reuse after the owner branch moves.",
    )
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit("output already exists; frozen runs are append-forbidden")

    require(sha256_file(FIXTURE_PATH) == EXPECTED_FIXTURE_SHA256, "frozen fixture digest mismatch")
    preregistration = PREREGISTRATION_PATH.read_text(encoding="utf-8")
    require("FROZEN FOR LOCAL DIAGNOSTIC" in preregistration, "pre-registration is not frozen")
    require(EXPECTED_FIXTURE_SHA256 in preregistration, "pre-registration fixture digest mismatch")
    require(MODEL_PATH.is_dir(), "cached MiniLM revision is unavailable")
    fixture = validate_fixture(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    native = fixture["matrix_native"]
    source_root = Path(native["source_repository"]).resolve()
    checkpoint = Path(native["checkpoint"]).resolve()
    checkpoint_sidecar = checkpoint.with_suffix(checkpoint.suffix + ".json")
    source_head_before = git_output(source_root, "rev-parse", "HEAD").strip()
    status_before = git_output(source_root, "status", "--short")
    checkpoint_stat_before = checkpoint.stat()
    require(sha256_file(checkpoint) == native["checkpoint_sha256"], "matrix-native checkpoint drift")
    require(sha256_file(checkpoint_sidecar) == native["checkpoint_sidecar_sha256"], "checkpoint sidecar drift")
    checkpoint_metadata = json.loads(checkpoint_sidecar.read_text(encoding="utf-8"))
    checkpoint_sources = checkpoint_metadata["sources"]
    require(
        sha256_bytes(canonical_json(checkpoint_sources))
        == native["checkpoint_source_manifest_sha256"],
        "checkpoint source manifest drift",
    )

    output.mkdir(parents=True)
    runtime_root = output / "runtime-source"
    frozen_runtime_source = (
        args.frozen_runtime_source.expanduser().resolve()
        if args.frozen_runtime_source is not None else None
    )
    if frozen_runtime_source is None:
        require(source_head_before == native["git_head_at_freeze"], "matrix-native HEAD moved without a frozen source snapshot")
        snapshot_source = source_root
        snapshot_origin = "owner_checkout_at_frozen_head"
    else:
        require(frozen_runtime_source.is_dir(), "frozen runtime source snapshot is absent")
        snapshot_source = frozen_runtime_source
        snapshot_origin = "previously_verified_frozen_runtime_snapshot"
    snapshot = copy_runtime_source(
        snapshot_source, runtime_root, checkpoint_sources, native["apparatus_sources"],
    )
    snapshot["origin"] = snapshot_origin
    snapshot["frozen_git_head"] = native["git_head_at_freeze"]
    snapshot["owner_git_head_at_run_start"] = source_head_before
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    embeddings = embed_all(fixture)
    passage_matrices = {
        row["id"]: matrix_from_row(row, embeddings, fixture["matrix"])
        for row in fixture["passages"]
    }
    query_matrices = {
        row["id"]: matrix_from_row(row, embeddings, fixture["matrix"])
        for row in fixture["queries"]
    }
    passage_embeddings = {
        row["id"]: embeddings[row["text"]] for row in fixture["passages"]
    }

    common, native_route = import_native_snapshot(runtime_root, checkpoint)
    tree = common.fresh()
    require(tree.state_hash() != native["checkpoint_state_hash"], "preparation-disable transition was not recorded")
    require(len(tree.nodes) == native["starting_branches"], "wrong actual Tree size")
    require(tree.engine._balanced_preparation is False, "preparation scheduler remains enabled")
    initial_capability_state_hash = tree.state_hash()
    receipts: dict[str, dict[str, np.ndarray]] = {}
    loads = []
    for index, row in enumerate(fixture["passages"]):
        passage_id = row["id"]
        value = passage_matrices[passage_id]
        state_before = tree.state_hash()
        path = native_route(tree, value)
        require(tree.state_hash() == state_before, "pre-load native route mutated the Tree")
        terminals = [branch_id for branch_id in path.order if not path.children[branch_id]]
        receipt = {branch_id: path.local[branch_id].copy() for branch_id in terminals}
        require(abs(receipt_energy(receipt) - 1.0) <= TOLERANCE, "terminal route energy is not conserved")
        record = common.memory_tick(tree, value, f"tom-assist-document:{passage_id}", index)
        actual = tree.engine._matrix_last_event
        require(np.array_equal(actual["input"], value), "compiled passage matrix did not reach the Tree")
        actual_by_id = {
            str(branch_id): actual["routed"][position]
            for position, branch_id in enumerate(actual["ids"])
        }
        require(set(path.order) == set(actual_by_id), "native route inventory differs from accepted load")
        route_error = max(
            float(np.max(np.abs(
                path.frames[branch_id].to_global(path.local[branch_id])
                - actual_by_id[branch_id]
            )))
            for branch_id in path.order
        )
        require(route_error <= ROUTE_MATCH_TOLERANCE, "read-only route differs from accepted load route")
        require(record["recipients"] == len(path.order), "not every pre-event branch received the load")
        require(tree.state_hash() != state_before, "passage load did not change Tree state")
        require(record["updated_predictors"] == 0, "unobserved passage trained a predictor")
        receipts[passage_id] = receipt
        loads.append({
            "passage_id": passage_id,
            "matrix_sha256": sha256_bytes(value.tobytes()),
            "matrix_exact_zero_count": int(np.count_nonzero(value == 0.0)),
            "state_hash_before": state_before,
            "state_hash_after": tree.state_hash(),
            "branches_before": len(path.order),
            "branches_after": len(tree.nodes),
            "born": record["born"],
            "removed": record["removed"],
            "actual_route_max_abs_error": route_error,
            "receipt_sha256": receipt_digest(receipt),
            "terminal_count": len(receipt),
            "terminal_energy": receipt_energy(receipt),
            "native_invariant_errors": {
                key: record[key]
                for key in (
                    "fork_error", "root_leaf_energy_error", "force_balance_error",
                    "moment_balance_error", "applied_matrix_error",
                )
            },
            "memory_recurrence_errors": record["memory_errors"],
            "predictor_updates": record["updated_predictors"],
        })
        print(json.dumps({
            "stage": "passage_load",
            "passage": passage_id,
            "completed": index + 1,
            "total": len(fixture["passages"]),
            "branches_before": len(path.order),
            "branches_after": len(tree.nodes),
            "recipients": record["recipients"],
            "route_error": route_error,
        }, sort_keys=True), flush=True)

    loaded_state_hash = tree.state_hash()
    query_state_before = loaded_state_hash
    observations = []
    for row in fixture["queries"]:
        query_id = row["id"]
        query_matrix = query_matrices[query_id]
        state_before = tree.state_hash()
        path = native_route(tree, query_matrix)
        require(tree.state_hash() == state_before, "native query route mutated the Tree")
        direct_scores = {
            passage_id: cosine(
                query_matrix.ravel().tolist(), matrix.ravel().tolist(),
            )
            for passage_id, matrix in passage_matrices.items()
        }
        minilm_scores = {
            passage_id: cosine(embeddings[row["text"]], vector)
            for passage_id, vector in passage_embeddings.items()
        }
        tree_scores: dict[str, float] = {}
        receipt_coverage = {}
        for passage_id, receipt in receipts.items():
            score, coverage, surviving = tree_receipt_cosine(receipt, path.local)
            tree_scores[passage_id] = score
            receipt_coverage[passage_id] = {
                "retained_energy_fraction": coverage,
                "surviving_historical_terminals": surviving,
                "historical_terminal_count": len(receipt),
            }
        hybrid_scores = {
            passage_id: (
                0.5 * ((tree_scores[passage_id] + 1.0) / 2.0)
                + 0.5 * ((minilm_scores[passage_id] + 1.0) / 2.0)
            )
            for passage_id in passage_matrices
        }
        relevant = row["relevant_passage_ids"][0]
        observations.append({
            "query_id": query_id,
            "family": row["family"],
            "query_text": row["text"],
            "relevant_passage_id": relevant,
            "matrix_sha256": sha256_bytes(query_matrix.tobytes()),
            "native_route_node_count": len(path.order),
            "native_route_terminal_count": sum(not path.children[item] for item in path.order),
            "receipt_coverage": receipt_coverage,
            "stages": {
                "direct_matrix": stage_result(direct_scores, relevant, fixture["readout"]["fixed_k"]),
                "minilm": stage_result(minilm_scores, relevant, fixture["readout"]["fixed_k"]),
                "actual_matrix_tree": stage_result(tree_scores, relevant, fixture["readout"]["fixed_k"]),
                "matrix_tree_plus_minilm": stage_result(hybrid_scores, relevant, fixture["readout"]["fixed_k"]),
            },
        })
        require(tree.state_hash() == state_before, "query scoring mutated the Tree")
        print(json.dumps({
            "stage": "query",
            "query": query_id,
            "completed": len(observations),
            "total": len(fixture["queries"]),
            "ranks": {
                stage: observations[-1]["stages"][stage]["relevant_rank"]
                for stage in observations[-1]["stages"]
            },
        }, sort_keys=True), flush=True)
    require(tree.state_hash() == query_state_before, "query set mutated loaded Tree state")

    fixed_k = fixture["readout"]["fixed_k"]
    stages = tuple(observations[0]["stages"])
    aggregate = {
        stage: {
            "correct_at_k": {
                str(k): sum(
                    observation["stages"][stage]["correct_at_k"][str(k)]
                    for observation in observations
                )
                for k in fixed_k
            },
            "observations": len(observations),
            "relevant_ranks": {
                observation["query_id"]: observation["stages"][stage]["relevant_rank"]
                for observation in observations
            },
        }
        for stage in stages
    }

    status_after = git_output(source_root, "status", "--short")
    source_head_after = git_output(source_root, "rev-parse", "HEAD").strip()
    checkpoint_stat_after = checkpoint.stat()
    all_source_hashes = dict(checkpoint_sources)
    all_source_hashes.update(native["apparatus_sources"])
    protection = {
        "frozen_source_head": native["git_head_at_freeze"],
        "owner_source_head_before": source_head_before,
        "owner_source_head_after": source_head_after,
        "owner_source_head_exact_during_run": source_head_before == source_head_after,
        "source_status_line_count": len(status_before.splitlines()),
        "source_status_sha256_before": sha256_bytes(status_before.encode("utf-8")),
        "source_status_sha256_after": sha256_bytes(status_after.encode("utf-8")),
        "source_status_exact": status_before == status_after,
        "frozen_snapshot_files_exact_after": source_files_unchanged(runtime_root, all_source_hashes),
        "checkpoint_sha256_before": native["checkpoint_sha256"],
        "checkpoint_sha256_after": sha256_file(checkpoint),
        "checkpoint_size_before": checkpoint_stat_before.st_size,
        "checkpoint_size_after": checkpoint_stat_after.st_size,
        "checkpoint_mtime_ns_before": checkpoint_stat_before.st_mtime_ns,
        "checkpoint_mtime_ns_after": checkpoint_stat_after.st_mtime_ns,
        "checkpoint_identity_exact": (
            checkpoint_stat_before.st_size == checkpoint_stat_after.st_size
            and checkpoint_stat_before.st_mtime_ns == checkpoint_stat_after.st_mtime_ns
        ),
    }
    require(protection["source_status_exact"], "owner matrix-native checkout status changed")
    require(protection["owner_source_head_exact_during_run"], "owner matrix-native HEAD changed during the run")
    require(protection["frozen_snapshot_files_exact_after"], "frozen runtime source changed")
    require(
        protection["checkpoint_sha256_after"] == native["checkpoint_sha256"]
        and protection["checkpoint_identity_exact"],
        "owner matrix-native checkpoint changed",
    )

    report = {
        "version": "tom-assist-actual-matrix-native-tree-retrieval/1.0",
        "status": "completed_local_diagnostic_not_a_gate",
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "preregistration_sha256": sha256_file(PREREGISTRATION_PATH),
        "runner_sha256": sha256_file(Path(__file__)),
        "provider_generations": 0,
        "gemma_generations": 0,
        "gpt_generations": 0,
        "oauth_calls": 0,
        "cloud_calls": 0,
        "minilm": {
            "revision": MODEL_REVISION,
            "embedding_count": len(embeddings),
            "generation_count": 0,
        },
        "tree": {
            "kind": "actual_matrix_native_balanced_preparation_tree",
            "historical_8d_17d_tree_used": False,
            "static_prototype_used": False,
            "invented_growth_rule_used": False,
            "initial_checkpoint_state_hash": native["checkpoint_state_hash"],
            "capability_state_hash_before_passages": initial_capability_state_hash,
            "loaded_state_hash": loaded_state_hash,
            "starting_branches": native["starting_branches"],
            "branches_after_passages": len(tree.nodes),
            "passage_load_count": len(loads),
            "prior_matrix_growth_events": native["prior_matrix_growth_events"],
            "preparation_scheduler_disabled": tree.engine._balanced_preparation is False,
            "query_state_hash_before": query_state_before,
            "query_state_hash_after": tree.state_hash(),
            "queries_state_pure": query_state_before == tree.state_hash(),
        },
        "runtime_snapshot": snapshot,
        "loads": loads,
        "observations": observations,
        "aggregate": aggregate,
        "protection": protection,
        "claim_boundary": (
            "Small frozen teacher-event retrieval diagnostic only. It tests actual "
            "matrix-native Tree loading and read-only receipt ranking; it is not a "
            "parser evaluation, production switch, statistical claim or G-gate verdict."
        ),
    }
    (output / "report.json").write_bytes(canonical_json(report) + b"\n")
    print(json.dumps({
        "report": str(output / "report.json"),
        "aggregate": aggregate,
        "starting_branches": native["starting_branches"],
        "branches_after_passages": len(tree.nodes),
        "all_passages_loaded": len(loads),
        "query_state_pure": report["tree"]["queries_state_pure"],
        "source_untouched": protection["source_status_exact"] and protection["owner_source_head_exact_during_run"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
