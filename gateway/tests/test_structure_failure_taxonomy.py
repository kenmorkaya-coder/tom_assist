from __future__ import annotations

import ast
from pathlib import Path
import re

from gateway.structure_failures import (
    FAILURE_DEFINITIONS,
    MAX_FAILURE_DETAIL_CHARACTERS,
    ClassifiedStructureError,
    classify_failure,
    record_for_code,
    taxonomy_summary,
    validate_worker_telemetry,
)
from gateway.structure_worker import attempt_all_chunks
from gateway.structural_analysis import CANDIDATE_VERSION, SIGNAL_NAMES, text_digest


ROOT = Path(__file__).resolve().parents[2]

# These functions are the unlabelled exception origins that can feed the
# parser/evaluation classifier. "dynamic" means the test reads the preceding
# ``stage = "..."`` assignment from that same function in the real source.
SOURCE_STAGES = {
    "gateway/project_glossary.py": {
        "_surface": "worker_request",
        "_document_phrases": "worker_request",
        "build_project_glossary": "worker_request",
        "validate_glossary": "worker_request",
    },
    "gateway/semantic_chunks.py": {
        "build_token_chunks": "chunk_plan",
        "_unit_vector": "semantic_profile",
        "_normalize": "semantic_profile",
        "build_semantic_profile": "semantic_profile",
        "validate_semantic_profile": "merge",
    },
    "gateway/structural_analysis.py": {
        "_require_object": "candidate_validation",
        "_finite_unit": "candidate_validation",
        "_validate_span": "candidate_validation",
        "_identifier": "candidate_validation",
        "_label": "candidate_validation",
        "validate_candidate": "candidate_validation",
        "canonicalize_candidate_ids": "candidate_canonicalization",
        "canonicalize_candidate_spans.bind": "candidate_canonicalization",
        "merge_chunk_candidates": "merge",
        "validate_parser_model": "analysis",
    },
    "gateway/structure_provider.py": {
        "StructureWorkerClient.__init__": "provider_config",
    },
    "gateway/structure_worker.py": {
        "GemmaChild.analyze": "gemma_transport",
        "main": "dynamic",
    },
    "gateway/gemma_structure_worker.py": {
        "_balanced_call_object": "tool_parse",
        "_gemma4_arguments": "tool_parse",
        "parse_generated_tool_call": "tool_parse",
        "main": "dynamic",
    },
}

# These messages belong to post-parse load construction/history replay rather
# than the WP-40 parse and validation chain. Listing the functions makes an
# accidental new omission visible instead of silently skipping the file.
OUT_OF_SCOPE_PLAIN_RAISE_FUNCTIONS = {
    "gateway/semantic_chunks.py": {"_cosine", "profile_similarity"},
    "gateway/structural_analysis.py": {
        "render_channel_reason",
        "require_strictly_positive_load",
        "_validate_record_scalar",
        "_finite_positive",
        "_validate_support_item",
        "require_evidenced_load",
        "compile_load",
        "compile_load.classify_zero",
        "validate_frozen_analysis",
    },
}

# Generic validators receive these names from real validate_candidate
# callsites. Expanding the real source f-string over each context proves the
# distinct candidate/entity/relation/signal patterns rather than weakening
# them to one generic bucket.
SOURCE_CONTEXTS = {
    ("gateway/structural_analysis.py", "_require_object"): [
        {"name": name} for name in (
            "candidate", "entities[0]", "orientations[0]",
            "causal_relations[0]", "signals", "signals.rules[0]",
            "entities[0].evidence",
        )
    ],
    ("gateway/structural_analysis.py", "_finite_unit"): [
        {"name": "candidate.confidence"},
    ],
    ("gateway/structural_analysis.py", "_validate_span"): [
        {"name": "entities[0].evidence"},
    ],
    ("gateway/structural_analysis.py", "_identifier"): [
        {"name": "entities[0].id"},
    ],
    ("gateway/structural_analysis.py", "_label"): [
        {"name": "entities[0].label"},
    ],
    ("gateway/structural_analysis.py", "canonicalize_candidate_spans.bind"): [
        {"name": "entities[0]"},
    ],
}


def _formatted_value(value: ast.AST, context: dict[str, str]) -> str:
    key = ast.unparse(value)
    if isinstance(value, ast.Name):
        key = value.id
    defaults = {
        "source": "project",
        "name": "semantic chunk 0",
        "max_source_chars": "48000",
        "index": "0",
        "max_chunks": "128",
        "EMBEDDING_DIMENSION": "384",
        "MAX_CHUNKS": "128",
        "MAX_SOURCE_CHARS": "48000",
        "norm": "0",
        "max_entities": "64",
        "entity_id": "entity_1",
        "kind": "unsupported",
        "max_relations": "64",
        "relation_id": "r1",
        "signal_name": "rules",
        "max_signals": "32",
        "error": "source failure",
        "len(values)": "12",
        "code": "1",
    }
    return str(context.get(key, defaults.get(key, "value")))


def _render_source_message(node: ast.AST, context: dict[str, str]) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            item.value
            if isinstance(item, ast.Constant)
            else _formatted_value(item.value, context)
            for item in node.values
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return (
            _render_source_message(node.left, context)
            + _render_source_message(node.right, context)
        )
    # Only a dynamic suffix is needed for the real prefix to select a code.
    if isinstance(node, ast.Call):
        return "source failure"
    raise AssertionError(f"unsupported source message AST: {ast.dump(node)}")


def _source_failures():
    rows = []
    seen_functions: dict[str, set[str]] = {}
    for relative, scopes in SOURCE_STAGES.items():
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        stack: list[str] = []
        stage_assignments: list[tuple[str, int, str]] = []
        plain_raise_functions: set[str] = set()

        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node):
                stack.append(node.name)
                self.generic_visit(node)
                stack.pop()

            def visit_FunctionDef(self, node):
                stack.append(node.name)
                qualified = ".".join(stack)
                for child in ast.walk(node):
                    if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                        continue
                    targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                    if not any(
                        isinstance(target, ast.Name) and target.id == "stage"
                        for target in targets
                    ):
                        continue
                    if isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
                        stage_assignments.append((qualified, child.lineno, child.value.value))
                self.generic_visit(node)
                stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Raise(self, node):
                qualified = ".".join(stack)
                error = node.exc
                if not (
                    isinstance(error, ast.Call)
                    and isinstance(error.func, ast.Name)
                    and error.func.id in {"ValueError", "RuntimeError"}
                    and error.args
                ):
                    self.generic_visit(node)
                    return
                plain_raise_functions.add(qualified)
                if qualified not in scopes:
                    self.generic_visit(node)
                    return
                stage = scopes[qualified]
                if stage == "dynamic":
                    preceding = [
                        item for item in stage_assignments
                        if item[0] == qualified and item[1] < node.lineno
                    ]
                    assert preceding, (relative, qualified, node.lineno)
                    stage = max(preceding, key=lambda item: item[1])[2]
                contexts = SOURCE_CONTEXTS.get((relative, qualified), [{}])
                for context in contexts:
                    rows.append({
                        "path": relative,
                        "function": qualified,
                        "line": node.lineno,
                        "stage": stage,
                        "message": _render_source_message(error.args[0], context),
                    })
                self.generic_visit(node)

        Visitor().visit(tree)
        seen_functions[relative] = plain_raise_functions
    return rows, seen_functions


def _empty_candidate(text: str) -> dict:
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": [],
        "orientations": [],
        "causal_relations": [],
        "signals": {name: [] for name in SIGNAL_NAMES},
        "unknown_fields": [],
        "confidence": 1.0,
    }


def test_every_enumerated_raise_family_triggers_its_unique_category():
    assert len({item.code for item in FAILURE_DEFINITIONS}) == len(FAILURE_DEFINITIONS)
    records = []
    for definition in FAILURE_DEFINITIONS:
        record = classify_failure(
            ValueError(definition.example), stage=definition.stage,
        )
        assert record["category"] == definition.code, definition
        assert definition.source
        records.append(record)
    summary = taxonomy_summary(records)
    assert summary["unclassified_count"] == 0
    assert summary["taxonomy_complete"] is True


def test_real_source_error_literals_match_exactly_one_taxonomy_pattern():
    rows, seen_functions = _source_failures()
    assert len(rows) >= 140
    matched_codes = set()
    for row in rows:
        matches = [
            definition.code for definition in FAILURE_DEFINITIONS
            if definition.stage == row["stage"] and re.search(
                definition.pattern, row["message"], flags=re.IGNORECASE,
            )
        ]
        assert matches == list(dict.fromkeys(matches))
        assert len(matches) == 1, {**row, "matches": matches}
        matched_codes.update(matches)

    for relative, functions in seen_functions.items():
        accounted = set(SOURCE_STAGES[relative]) | set(
            OUT_OF_SCOPE_PLAIN_RAISE_FUNCTIONS.get(relative, set())
        )
        assert functions == accounted, {
            "path": relative,
            "unaccounted": sorted(functions - accounted),
            "stale_scope_entries": sorted(accounted - functions),
        }
    assert matched_codes


def test_every_explicit_source_category_is_a_declared_taxonomy_code():
    declared = {definition.code for definition in FAILURE_DEFINITIONS}
    observed = set()
    for relative in (*SOURCE_STAGES, "validation/calibration/wp40_runner.py"):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in {"record_for_code", "_provider_error"}:
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            observed.add(node.args[0].value)
    assert observed
    assert observed <= declared


def test_every_taxonomy_code_is_tied_to_source_literal_or_explicit_raise():
    rows, _ = _source_failures()
    source_matched = {
        definition.code
        for row in rows
        for definition in FAILURE_DEFINITIONS
        if definition.stage == row["stage"]
        and re.search(definition.pattern, row["message"], flags=re.IGNORECASE)
    }
    explicit = set()
    for relative in (*SOURCE_STAGES, "validation/calibration/wp40_runner.py"):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id not in {"record_for_code", "_provider_error"}:
                continue
            if node.args and isinstance(node.args[0], ast.Constant):
                explicit.add(node.args[0].value)
    assert source_matched | explicit == {
        definition.code for definition in FAILURE_DEFINITIONS
    }


def test_all_chunks_are_attempted_and_one_failure_fails_the_passage():
    class FixtureGemma:
        def __init__(self):
            self.calls = []

        def analyze(self, request_id, source_text, glossary):
            self.calls.append((request_id, source_text, glossary))
            if request_id.endswith(":1"):
                raise ClassifiedStructureError(record_for_code(
                    "tool.name", "Gemma called the wrong structure tool",
                ))
            return {
                "candidate": _empty_candidate(source_text),
                "boundary_telemetry": {"tool_parse_mode": "fixture"},
            }

    gemma = FixtureGemma()
    result = attempt_all_chunks(gemma, "request", ["one", "two", "three"])
    candidates = result.pop("chunk_candidates")
    telemetry = validate_worker_telemetry({"planned_chunks": 3, **result})
    assert len(gemma.calls) == 3
    assert [row["attempt_ordinal"] for row in telemetry["attempts"]] == [1, 2, 3]
    assert [row["outcome"] for row in telemetry["attempts"]] == [
        "succeeded", "failed", "succeeded",
    ]
    assert telemetry["attempted_chunks"] == 3
    assert telemetry["successful_chunks"] == 2
    assert telemetry["passage_failed"] is True
    assert telemetry["failed_chunk_index"] == 1
    assert telemetry["failures"][0]["chunk_index"] == 1
    assert telemetry["failures"][0]["attempt_ordinal"] == 2
    assert telemetry["taxonomy"]["unclassified_count"] == 0
    assert [row["chunk_index"] for row in candidates] == [0, 2]


def test_failure_detail_is_bounded_without_losing_its_ends():
    detail = "CAUSE-FIRST " + "x" * 1000 + " CAUSE-LAST"
    record = record_for_code("model.invoke", detail, chunk_index=4, attempt_ordinal=5)
    assert len(record["detail"]) == MAX_FAILURE_DETAIL_CHARACTERS
    assert record["detail"].startswith("CAUSE-FIRST")
    assert record["detail"].endswith("CAUSE-LAST")
    assert record["chunk_index"] == 4
    assert record["attempt_ordinal"] == 5


def test_unclassified_is_never_absorbed_and_is_reported_loudly():
    record = classify_failure(
        RuntimeError("entirely new failure"), stage="candidate_validation",
    )
    summary = taxonomy_summary([record])
    assert record["category"] == "unclassified"
    assert summary["unclassified_count"] == 1
    assert summary["taxonomy_complete"] is False
