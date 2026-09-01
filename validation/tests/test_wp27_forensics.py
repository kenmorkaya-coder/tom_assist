import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "validation/runs/wp27-pilot-forensics"
FROZEN = ROOT / "validation/runs/wp25-pilot-frozen-v2"


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_wp27_preserves_frozen_outcome_and_capture_accounting():
    report = json.loads((AUDIT / "report.json").read_text(encoding="utf-8"))
    assert report["zero_generations"] is True
    assert report["frozen_outcome_unchanged"] == {
        "H0": "HOLDS",
        "H1": "DOES_NOT_HOLD",
        "H2": "NOT_TRIGGERED_REQUIRES_H1",
        "H3": "NOT_OBSERVED",
        "gate_verdict": None,
    }
    assert report["capture_lineage"] == {
        "accepted_mismatch_rows": 22,
        "captures": 165,
        "citation_exact_rows": 0,
        "rows_captured_once": 165,
        "taxonomy_definition": "emitted when cited_state_ids exact match is false after exact/accepted-mismatch early return",
        "taxonomy_rows": 143,
    }
    assert report["sources"]["raw_matrix"]["sha256"] == (
        "sha256:f30e87a6ccfed975228a2ac346f2fc178d549c13b5c6624b28cbf1f652d16454"
    )


def test_wp27_native_import_and_rerank_are_accounted_without_commits():
    report = json.loads((AUDIT / "native_report.json").read_text(encoding="utf-8"))
    assert report["zero_generations"] is True
    assert report["native_import"]["runtime_commit_receipts"] == 0
    assert report["native_import"]["stored_state_objects"] == 2310
    assert report["native_import"]["input_objects"] == 2310
    assert report["native_import"]["stored_edges"] == 1155
    assert report["native_import"]["complete_id_sets"] == 165
    assert report["cohort"]["uniform_axis_fallback_count"] == 0
    assert report["cohort"]["stiffness_usage_supported_total"] == 132
    assert report["cohort"]["alignment_displaced_total"] == 396
    assert report["cohort"]["three_axis_vs_8d_overlap_total"] == 0
    assert report["retrieval_attribution"]["sub_d_focus_state_object_hits"] == 33
    assert report["retrieval_attribution"]["failures_attributable_to_three_axis_selection"] == 0
    assert len(jsonl(AUDIT / "native_case_analysis.jsonl")) == 165
    assert len(jsonl(AUDIT / "commit_projection_analysis.jsonl")) == 165
    assert len(jsonl(AUDIT / "cohort_rerank_analysis.jsonl")) == 33


def test_wp27_packet_manifest_and_provider_visible_ids_are_separate():
    report = json.loads((AUDIT / "report.json").read_text(encoding="utf-8"))
    packet = report["sub_d_packet_summary"]
    assert packet["focus_retrieval_hits"] == 33
    assert packet["expected_current_admitted"] == packet["expected_current_objects"] == 207
    assert packet["expected_current_rendered_in_state_block"] == 3
    assert packet["expected_historical_admitted"] == 0
    assert packet["packet_budget_exclusions"] == 0
    assert packet["excluded_reasons"] == {"superseded-positive": 66}
    assert len(jsonl(AUDIT / "sub_d_packet_analysis.jsonl")) == 33


def test_wp27_response_sha_correction_is_raw_text_not_canonical_string():
    rows = jsonl(AUDIT / "response_sha_audit.jsonl")
    assert len(rows) == 165
    assert all(row["reported_matches_canonical_json_string"] for row in rows)
    assert not any(row["reported_matches_raw_utf8"] for row in rows)
    source = json.loads((FROZEN / "raw_matrix.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert rows[0]["raw_utf8_response_sha"] == "sha256:" + hashlib.sha256(
        source["response_text"].encode("utf-8")
    ).hexdigest()
