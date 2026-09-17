import pytest

from gateway.project_identity_matrix_compiler import prepare_identity_candidate
from gateway.typed_matrix_compiler import UnsupportedTypedEvent, compile_prepared, prepare_candidate
from gateway.tests.test_typed_matrix_compiler import candidate, fake_embeddings


REGISTRY = "project_id,entity_id,kind,label\nalpha,cab-a,cabinet,Cabinet Elm\nalpha,cab-a,cabinet,Archive West\nalpha,cab-b,cabinet,Cabinet Pine\nbeta,cab-a,cabinet,Cabinet Elm\n"


def prepare(label, project="alpha", registry=REGISTRY):
    text, event = candidate("the custodian", "store samples in " + label)
    return prepare_identity_candidate(event, text, project_id=project, registry_csv=registry)


def test_alias_is_same_identity_and_matrix():
    a, b = prepare("Cabinet Elm"), prepare("Archive West")
    assert a["events"][0]["fields"]["target"]["semantic_text"] == b["events"][0]["fields"]["target"]["semantic_text"]
    assert a["events"][0]["fields"]["target"]["symbols"] == b["events"][0]["fields"]["target"]["symbols"]
    assert compile_prepared(a, fake_embeddings(a))["matrix"] == compile_prepared(b, fake_embeddings(b))["matrix"]


def test_namespace_is_part_of_identity_not_label():
    a, b = prepare("Cabinet Elm", "alpha"), prepare("Cabinet Elm", "beta")
    assert a["events"][0]["fields"]["target"]["semantic_text"] == b["events"][0]["fields"]["target"]["semantic_text"]
    assert a["events"][0]["fields"]["target"]["symbols"] != b["events"][0]["fields"]["target"]["symbols"]
    assert compile_prepared(a, fake_embeddings(a))["matrix"] != compile_prepared(b, fake_embeddings(b))["matrix"]


def test_distinct_identity_codes_require_registry_rows():
    a, b = prepare("Cabinet Elm"), prepare("Cabinet Pine")
    assert a["events"][0]["fields"]["target"]["symbols"] != b["events"][0]["fields"]["target"]["symbols"]


@pytest.mark.parametrize("label,project,registry", [
    ("Cabinet Birch", "alpha", REGISTRY),
    ("Cabinet Elm", "gamma", REGISTRY),
    ("Cabinet Elm", "alpha", REGISTRY + "alpha,cab-z,cabinet,Cabinet Elm\n"),
    ("Cabinet Elm", "alpha", REGISTRY + "alpha,cab-a,valve,Valve Elm\n"),
    ("Cabinet Elm", "alpha", "entity_id,label\ncab-a,Cabinet Elm\n"),
])
def test_unbound_ambiguous_or_conflicting_identity_rejected(label, project, registry):
    with pytest.raises(UnsupportedTypedEvent):
        prepare(label, project, registry)


def test_unannotated_events_unchanged():
    text, event = candidate("the operator", "stop when pressure exceeds 5 kPa")
    assert prepare_identity_candidate(event, text) == prepare_candidate(event, text)


def test_identity_evidence_bound_to_field_and_registry():
    p = prepare("Cabinet Elm")
    evidence = p["identity_evidence"][0]
    field = p["events"][0]["fields"][evidence["field"]]
    assert field["text"][evidence["start"]:evidence["end"]] == evidence["quote"]
    assert evidence["registry_record_ordinal"] == 0
    assert evidence["identity"]["entity_id"] == "cab-a"


def test_trace_instrument_accepts_array_stages_and_matches_compiler():
    from validation.calibration.project_identity_compiler_runner import assembly_error, trace
    p = prepare("Cabinet Elm")
    _, stages = trace(p, fake_embeddings(p))
    assert assembly_error(stages) <= 1e-12
