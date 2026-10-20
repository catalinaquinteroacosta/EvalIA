
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


@pytest.mark.parametrize(
    "verdict", ["error", None, {}, "unexpected"]
)
def test_unknown_verdict_never_scores(verdict):
    result = validate_ce4_evidence(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction=extraction(),
        verify_claim=lambda *_: verdict,
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None


def test_reconciliation_exception_never_scores():
    def reconciler(*args):
        raise RuntimeError("Simulated semantic failure")

    try:
        result = validate_ce4_evidence(
            user_text="Ayudame a preparar una conversacion.",
            response_text=RESPONSE,
            extraction=extraction(),
            verify_claim=lambda *_: "ambiguous",
            reconcile_claim=reconciler,
        )
    except RuntimeError:
        return

    assert result["status"] == "BLOCKED"
    assert result["score"] is None


def test_execution_disagreement_is_blocked():
    calls = []

    def verifier(*args):
        calls.append(args)
        return (
            "ambiguous"
            if len(calls) == 3
            else "supported"
        )

    result = validate_ce4_evidence(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction=extraction(),
        verify_claim=verifier,
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None
    assert result["blocked_components"] == ["rubric_execution"]
