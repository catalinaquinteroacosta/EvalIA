"""Regresiones de polaridad ND99."""

import pytest

from backend.evaluators.nd.nd99_polarity_contract import (
    PolarityFinding,
    reconcile_polarity,
)


RESPONSE = "Un rechazo no define toda tu trayectoria."


def finding(name, verdict, quote=RESPONSE):
    return PolarityFinding(
        fact_name=name,
        verdict=verdict,
        quote=quote,
        reason="Revision semantica independiente",
        complete_response_examined=True,
    )


def test_supported_maps_to_present():
    name = "correction_present"
    result = reconcile_polarity(
        name,
        finding(name, "supported"),
        finding(name, "supported"),
        RESPONSE,
    )
    assert result.extraction_value == "present"


def test_not_supported_does_not_prove_absence():
    name = "reinforces_negative_idea"
    result = reconcile_polarity(
        name,
        finding(name, "not_supported"),
        finding(name, "not_supported"),
        RESPONSE,
    )
    assert result.extraction_value == "uncertain"


def test_disagreement_blocks():
    name = "active_questioning"
    result = reconcile_polarity(
        name,
        finding(name, "supported"),
        finding(name, "not_supported"),
        RESPONSE,
    )
    assert result.extraction_value == "uncertain"


def test_ambiguous_blocks():
    name = "active_questioning"
    result = reconcile_polarity(
        name,
        finding(name, "ambiguous"),
        finding(name, "ambiguous"),
        RESPONSE,
    )
    assert result.extraction_value == "uncertain"


def test_invalid_quote_rejected():
    name = "correction_present"
    with pytest.raises(ValueError):
        reconcile_polarity(
            name,
            finding(name, "supported", "Texto inventado"),
            finding(name, "supported"),
            RESPONSE,
        )


def test_incomplete_review_rejected():
    name = "correction_present"
    first = PolarityFinding(
        fact_name=name,
        verdict="supported",
        quote=RESPONSE,
        reason="Revision parcial",
        complete_response_examined=False,
    )
    with pytest.raises(ValueError):
        reconcile_polarity(
            name,
            first,
            finding(name, "supported"),
            RESPONSE,
        )
