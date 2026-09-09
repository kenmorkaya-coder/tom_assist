import hashlib
import math

import pytest

from gateway.typed_matrix_compiler import (
    UnsupportedTypedEvent, canonical_decimal, compile_prepared, field_record,
    parse_number, prepare_candidate, project, semantic_texts, symbol_vector,
)


def candidate(source, target, context="the inspection", *, negated=False, relation="obligation"):
    text = f"During {context}, {source} must {target}."
    return text, {"events": [{
        "source_evidence": {"quote": source}, "target_evidence": {"quote": target},
        "context_evidence": None, "relation_evidence": {"quote": text},
        "relation_kind": relation, "modality": "asserted", "negated": negated,
        "confidence": 1.0,
    }], "unknown_relations": []}


def fake_embeddings(prepared):
    return {text: [int.from_bytes(hashlib.sha256((text + str(i)).encode()).digest()[:4], "big") / 2**32 - 0.5
                   for i in range(384)] for text in semantic_texts(prepared)}


@pytest.mark.parametrize("left,right", [("1 m", "1000 mm"), ("600 kg", "600.0 kilograms"), ("600 kg", "six hundred kilograms"), ("1 tonne", "1000 kg"), ("0.5 MPa", "500 kPa")])
def test_equivalent_quantity_records_and_masked_text(left, right):
    a, b = field_record("retain " + left), field_record("retain " + right)
    assert a["symbols"] == b["symbols"]
    assert a["semantic_text"] == b["semantic_text"]
    assert symbol_vector(a["symbols"]) == symbol_vector(b["symbols"])


@pytest.mark.parametrize("phrase,operator", [("above", "GT"), ("at least", "GE"), ("below", "LT"), ("at most", "LE"), ("equals", "EQ"), (">=", "GE"), ("<=", "LE"), ("<", "LT"), (">", "GT")])
def test_strict_inclusive_comparators(phrase, operator):
    record = field_record(f"stop when pressure {phrase} 5 kPa")
    assert record["symbols"][0] == {"kind": "comparator", "operator": operator}
    for atom in record["evidence"]:
        assert record["text"][atom["start"]:atom["end"]] == atom["quote"]


@pytest.mark.parametrize("symbol,operator", [("<", "LT"), ("<=", "LE"), (">", "GT"), (">=", "GE"), ("=", "EQ")])
def test_symbolic_comparator_and_unit_without_spaces(symbol, operator):
    record = field_record(f"stop when pressure{symbol}5kPa")
    assert record["symbols"] == [{"kind": "comparator", "operator": operator}, {"kind": "quantity", "value": "5000", "unit": "Pa"}]


@pytest.mark.parametrize("text,result", [("minus five", "-5"), ("negative zero", "0"), ("six hundred", "600"), ("twenty-one", "21"), ("one hundred and five", "105"), ("five point zero five", "5.05")])
def test_exact_number_normalization(text, result):
    assert canonical_decimal(parse_number(text)) == result


@pytest.mark.parametrize("text", ["one two", "twenty forty", "hundred five", "one point ten"])
def test_ambiguous_number_rejected(text):
    with pytest.raises(UnsupportedTypedEvent):
        parse_number(text)


def test_precision_bound_rejects_instead_of_rounding():
    with pytest.raises(UnsupportedTypedEvent, match="PRECISION_BOUND"):
        parse_number("9" * 65)
    record = field_record("retain " + "9" * 50 + " kg")
    assert record["symbols"][0]["value"] == "9" * 50


@pytest.mark.parametrize("text", ["hold between 1 and 5 kg", "hold 1-5 kg", "hold 5 kg and 8 kg", "hold around 5 kg", "use revision B", "use 2026-09-09", "hold five stone", "hold 42 widgets"])
def test_unsupported_values_not_silently_embedded(text):
    with pytest.raises(UnsupportedTypedEvent):
        field_record(text)


def test_context_comes_from_actual_condition_not_whole_sentence():
    text, raw = candidate("the operator", "stop when vibration exceeds 5.5 mm/s")
    prepared = prepare_candidate(raw, text)
    context = prepared["events"][0]["context"]
    assert context["quote"] == "when vibration exceeds 5.5 mm/s"
    assert text[context["start"]:context["end"]] == context["quote"]
    assert prepared["events"][0]["fields"]["context"]["symbols"][1]["value"] == "0.0055"


def test_compound_condition_rejected_not_flattened():
    text, raw = candidate("the operator", "stop when pressure exceeds 5 kPa and temperature exceeds 20 degrees Celsius")
    with pytest.raises(UnsupportedTypedEvent):
        prepare_candidate(raw, text)


def test_no_full_sentence_fallback():
    text = "The operator must stop."
    _, raw = candidate("The operator", "stop")
    raw["events"][0]["relation_evidence"] = {"quote": text}
    with pytest.raises(UnsupportedTypedEvent, match="MISSING_EXACT_CONTEXT"):
        prepare_candidate(raw, text)


def test_matrix_changes_for_exact_values_and_ablation_removes_difference():
    results = []
    for value in ("600 kg", "900 kg"):
        text, raw = candidate("the controller", "retain " + value)
        p = prepare_candidate(raw, text)
        vectors = fake_embeddings(p)
        result = compile_prepared(p, vectors)
        assert result == compile_prepared(p, vectors)
        assert len(result["matrix"]) == 1024
        assert math.isclose(sum(x*x for x in result["matrix"]), 1, abs_tol=1e-12)
        results.append((result, compile_prepared(p, vectors, ablate_symbols=True)))
    assert results[0][0]["matrix"] != results[1][0]["matrix"]
    assert results[0][1]["matrix"] == results[1][1]["matrix"]


def test_projection_and_outer_products_keep_existing_mechanics():
    from validation.calibration.matrix_tree_32sq_runner import project_384_to_32
    vector = [math.sin(i + 0.5) for i in range(384)]
    assert project(vector) == project_384_to_32(vector, 539362568)
    matrices = []
    for source, target in (("Atlas", "Beacon"), ("Beacon", "Atlas")):
        text, raw = candidate(source, target, relation="enables")
        p = prepare_candidate(raw, text)
        matrices.append(compile_prepared(p, fake_embeddings(p))["matrix"])
    assert max(abs(matrices[0][i*32+j] - matrices[1][j*32+i]) for i in range(32) for j in range(32)) < 1e-12


def test_identical_units_produce_identical_matrix():
    outputs = []
    for value in ("1 m", "1000 mm"):
        text, raw = candidate("the controller", "retain " + value)
        p = prepare_candidate(raw, text)
        outputs.append(compile_prepared(p, fake_embeddings(p))["matrix"])
    assert outputs[0] == outputs[1]
