
from copy import deepcopy

import pytest

from backend.evaluators.ce.pilot.ce78_literal_recovery import (
    inspect_literal_claims,
)


def extraction(quote, source="response"):
    return {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "contradiction_impact": "major",
        "claims": [{
            "source": source,
            "quote": quote,
            "interpretation": "Proposicion de prueba",
        }],
    }


def test_ce7_detects_changed_verb():
    result = inspect_literal_claims(
        indicator="CE7",
        user_text="Pregunta",
        response_text="Intenta elegir el momento.",
        extraction=extraction("elige el momento"),
    )

    assert result["status"] == "repair_required"
    assert result["invalid_claims"][0]["claim_index"] == 0


def test_ce8_detects_nonliteral_user_quote():
    result = inspect_literal_claims(
        indicator="CE8",
        user_text="Con cu?l empiezo?",
        response_text="Empieza por una opcion.",
        extraction=extraction(
            "Con cual empiezo?", source="user"
        ),
    )

    assert result["status"] == "repair_required"


def test_exact_quote_passes():
    result = inspect_literal_claims(
        indicator="CE7",
        user_text="Pregunta",
        response_text="Intenta elegir el momento.",
        extraction=extraction("elegir el momento"),
    )

    assert result["status"] == "literal_valid"
    assert result["invalid_claims"] == []


def test_original_extraction_is_unchanged():
    draft = extraction("elige el momento")
    before = deepcopy(draft)

    inspect_literal_claims(
        indicator="CE7",
        user_text="Pregunta",
        response_text="Intenta elegir el momento.",
        extraction=draft,
    )

    assert draft == before


def test_other_families_are_rejected():
    with pytest.raises(ValueError):
        inspect_literal_claims(
            indicator="PA1",
            user_text="Pregunta",
            response_text="Respuesta",
            extraction=extraction("Respuesta"),
        )
