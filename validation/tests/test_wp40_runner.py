from validation.calibration.wp40_runner import _pair_diagnostic


def test_failed_arm_makes_candidate_digest_change_not_comparable():
    case = {
        "sequence": 1,
        "test_id": "case",
        "family": "CONSTRAINT",
        "source_text": "The phase lattice is fixed.",
        "glossary": {"terms": ["phase lattice"]},
    }
    result = _pair_diagnostic(
        case,
        {
            "glossary_off": {
                "candidate_sha256": "sha256:" + "a" * 64,
                "directed_graph_sha256": "sha256:" + "b" * 64,
            },
            "glossary_on": {
                "candidate_sha256": None,
                "directed_graph_sha256": None,
            },
        },
        {"glossary_off": {}, "glossary_on": None},
    )
    assert result["changed"] is None
    assert result["change_size"] is None
    assert result["directed_graph_agrees"] is None
    assert result["glossary_term_present_in_source"] is True
