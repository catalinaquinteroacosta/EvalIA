
import pytest

from backend.evaluators.ce.ce_d.ce4_evidence import (
    validate_ce4_evidence,
)

RESPONSE = (
    "Preparacion: identifica lo ocurrido. "
    "Conversacion: explica tus necesidades. "
    "Cierre: revisa los acuerdos."
)


def extraction():
    return {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": True,
        "applicability_evidence": {
            "source": "response",
            "quote": "Preparacion:",
            "interpretation": "La extension requiere estructura",
        },
        "claims": [{
            "source": "response",
            "quote": "Conversacion:",
            "interpretation": "Hay organizacion funcional",
        }],
        "rubric_execution": "clear_contextual_verifiable",
    }


@pytest.mark.parametrize("verdict", ["unsupported", "ambiguous"])
def test_disagreement_is_blocked(verdict):
    result = validate_ce4_evidence(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction=extraction(),
        verify_claim=lambda *_: verdict,
    )
    assert result["status"] == "BLOCKED"
    assert result["score"] is None
    assert result["blocked_components"] == ["applicability"]


def test_reconciliation_only_after_disagreement():
    calls = []

    def verifier(*args):
        calls.append("verify")
        return "ambiguous" if len(calls) == 1 else "supported"

    def reconciler(*args):
        calls.append("reconcile")
        return "supported"

    result = validate_ce4_evidence(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction=extraction(),
        verify_claim=verifier,
        reconcile_claim=reconciler,
    )

    assert result["status"] == "scored"
    assert result["score"] == 3
    assert calls[:2] == ["verify", "reconcile"]


def test_unresolved_reconciliation_stays_blocked():
    result = validate_ce4_evidence(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction=extraction(),
        verify_claim=lambda *_: "unsupported",
        reconcile_claim=lambda *_: "ambiguous",
    )
    assert result["status"] == "BLOCKED"
    assert result["score"] is None
