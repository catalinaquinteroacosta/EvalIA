"""Pruebas de limites pendientes para el contrato CE1."""

import pytest

from backend.evaluators.ce.ce_a.ce1_classification_contract import (
    CE1ContractError,
    validate_ce1_classification,
)

RESPONSE = "Prepara tus documentos. Por cierto, compra flores."


def valid_data():
    return {
        "primary_need_addressed": "partially",
        "primary_need_reason": "Atiende parcialmente la solicitud.",
        "issues": [{
            "description": "Digresion innecesaria.",
            "evidence": "compra flores",
            "impact": "major",
            "context_justification": (
                "No contribuye a la necesidad principal."
            ),
        }],
        "analysis_complete": True,
    }


def test_ambiguous_primary_need_cannot_be_complete():
    data = valid_data()
    data["primary_need_addressed"] = "ambiguous"

    with pytest.raises(CE1ContractError):
        validate_ce1_classification(data, RESPONSE)


def test_ambiguous_impact_cannot_be_complete():
    data = valid_data()
    data["issues"][0]["impact"] = "ambiguous"

    with pytest.raises(CE1ContractError):
        validate_ce1_classification(data, RESPONSE)


def test_no_issues_cannot_coexist_with_partial_need():
    data = valid_data()
    data["issues"] = []

    with pytest.raises(CE1ContractError):
        validate_ce1_classification(data, RESPONSE)


def test_no_impact_issue_cannot_justify_total_deviation():
    data = valid_data()
    data["primary_need_addressed"] = "no"
    data["issues"][0]["impact"] = "none"

    with pytest.raises(CE1ContractError):
        validate_ce1_classification(data, RESPONSE)


def test_incomplete_analysis_is_preserved_for_review():
    data = valid_data()
    data["analysis_complete"] = False

    result = validate_ce1_classification(data, RESPONSE)

    assert result["analysis_complete"] is False
