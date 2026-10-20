
import json
import pytest

from backend.evaluators.cp.reconciliation import (
    _decode_component_value,
)


def test_cp7_false_boolean_json():
    assert _decode_component_value(
        code="cp7",
        field="unnecessary_jargon_present",
        value_json="false",
        draft_indicator={"unnecessary_jargon_present": False},
    ) is False


def test_cp7_complete_string_json():
    assert _decode_component_value(
        code="cp7",
        field="indispensable_terms_explanation",
        value_json=json.dumps("complete"),
        draft_indicator={
            "indispensable_terms_explanation": "complete",
        },
    ) == "complete"


def test_cp7_unquoted_string_rejected():
    with pytest.raises(ValueError):
        _decode_component_value(
            code="cp7",
            field="indispensable_terms_explanation",
            value_json="complete",
            draft_indicator={
                "indispensable_terms_explanation": "complete",
            },
        )


def test_cp7_boolean_string_rejected():
    with pytest.raises(ValueError):
        _decode_component_value(
            code="cp7",
            field="unnecessary_jargon_present",
            value_json=json.dumps("false"),
            draft_indicator={"unnecessary_jargon_present": False},
        )
