from copy import deepcopy

import pytest

from backend.evaluators.ce.ce_a.ce1_classification_contract import (
    CE1ContractError,
    validate_ce1_classification,
)

RESPONSE = "Prepara tus documentos. Por cierto, compra flores."


def sample():
    return {
        "primary_need_addressed": "partially",
        "primary_need_reason": "Atiende parcialmente la solicitud.",
        "issues": [{
            "description": "Digresion ajena a la solicitud.",
            "evidence": "compra flores",
            "impact": "major",
            "context_justification": (
                "No contribuye a la necesidad principal."
            ),
        }],
        "analysis_complete": True,
    }


def test_valid_contract():
    data = sample()
    before = deepcopy(data)
    assert validate_ce1_classification(data, RESPONSE) == before
    assert data == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("primary_need_addressed", "unknown"),
        ("primary_need_reason", ""),
        ("analysis_complete", "yes"),
        ("issues", "none"),
    ],
)
def test_invalid_top_level(field, value):
    data = sample()
    data[field] = value
    with pytest.raises(CE1ContractError):
        validate_ce1_classification(data, RESPONSE)


@pytest.mark.parametrize(
    "field,value",
    [
        ("impact", "extreme"),
        ("description", ""),
        ("context_justification", ""),
        ("evidence", "cita inventada"),
    ],
)
def test_invalid_issue(field, value):
    data = sample()
    data["issues"][0][field] = value
    with pytest.raises(CE1ContractError):
        validate_ce1_classification(data, RESPONSE)


def test_total_deviation_requires_documentation():
    data = sample()
    data["primary_need_addressed"] = "no"
    data["issues"] = []
    with pytest.raises(CE1ContractError):
        validate_ce1_classification(data, RESPONSE)


def test_unknown_fields_rejected():
    data = sample()
    data["score"] = 3
    with pytest.raises(CE1ContractError):
        validate_ce1_classification(data, RESPONSE)
