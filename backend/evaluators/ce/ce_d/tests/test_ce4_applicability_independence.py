
import pytest

from backend.evaluators.ce.ce_d.ce4_evidence import (
    validate_ce4_evidence,
)


def extraction(applicable):
    return {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": applicable,
        "applicability_evidence": {
            "source": "response",
            "quote": "Preparaci?n:",
            "interpretation": (
                "La extensi?n requiere organizaci?n visual"
                if applicable
                else "La extensi?n no requiere organizaci?n visual"
            ),
        },
        "rubric_execution": "clear_contextual_verifiable",
        "claims": (
            [{
                "source": "response",
                "quote": "Preparaci?n:",
                "interpretation": (
                    "Existe organizaci?n visual contextualizada"
                ),
            }]
            if applicable else []
        ),
    }


RESPONSE = (
    "Preparaci?n: identifica qu? ocurri? y qu? necesitas.\n\n"
    "Conversaci?n: explica los hechos y escucha la respuesta.\n\n"
    "Cierre: revisa los acuerdos y decide qu? hacer despu?s."
)


@pytest.mark.parametrize("applicable", [True, False])
def test_applicability_is_independently_verified(applicable):
    calls = []

    def verifier(original, quote, claim):
        calls.append(claim)
        return "supported"

    result = validate_ce4_evidence(
        user_text="Ay?dame a preparar una conversaci?n.",
        response_text=RESPONSE,
        extraction=extraction(applicable),
        verify_claim=verifier,
    )

    assert calls
    assert "APLICABILIDAD" in calls[0]
    assert (
        "S\u00cd necesita" if applicable else "NO necesita"
    ) in calls[0]

    if applicable:
        assert result["score"] == 3
    else:
        assert result["status"] == "not_applicable"


@pytest.mark.parametrize(
    "verdict", ["unsupported", "ambiguous"]
)
def test_applicability_disagreement_never_scores(verdict):
    result = validate_ce4_evidence(
        user_text="Ay?dame a preparar una conversaci?n.",
        response_text=RESPONSE,
        extraction=extraction(True),
        verify_claim=lambda *_: verdict,
    )

    assert result["score"] is None
    assert result["status"] != "scored"


def test_existing_paragraphs_do_not_force_not_applicable():
    result = validate_ce4_evidence(
        user_text="Ay?dame a preparar una conversaci?n.",
        response_text=RESPONSE,
        extraction=extraction(True),
        verify_claim=lambda *_: "supported",
    )

    assert result["status"] == "scored"
    assert result["score"] == 3
