from validation.calibration.wp33_diagnostics import precise_error


def test_wp33_error_taxonomy_uses_preserved_messages_only():
    assert precise_error("ValueError: Gemma fallback contains an invalid structured value") == (
        "invalid_structured_value"
    )
    assert precise_error("ValueError: unsupported entity kind: rule") == (
        "unsupported_entity_kind"
    )
    assert precise_error("ValueError: model causal relation refers to an unknown entity") == (
        "unknown_relation_endpoint"
    )
    assert precise_error("TypeError: 'int' object is not iterable") == (
        "malformed_container_type"
    )
