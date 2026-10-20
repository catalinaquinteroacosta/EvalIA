import pytest

from backend.evaluators.ce.ce_a.ce1_verified_needs import (
    CE1VerifiedNeedsError,
    build_verified_need,
)

USER = "Necesito preparar mis documentos y practicar respuestas."
RESPONSE = "Organiza los documentos."


def item():
    return {
        "need": "Preparar documentos y practicar respuestas.",
        "source": "current_user",
        "evidence": "preparar mis documentos y practicar respuestas",
        "explanation": "Solicitud explicita.",
    }


def original(verdict="partially_addressed"):
    return {
        "verdict": verdict,
        "reason": "Solo atiende los documentos.",
    }


def audit(action="confirmed", assessment="partially_addressed"):
    return {
        "verdict": action,
        "independent_assessment": assessment,
        "reason": "Revision independiente.",
    }


def build(need=None, first=None, second=None):
    return build_verified_need(
        item() if need is None else need,
        original() if first is None else first,
        audit() if second is None else second,
        user_text=USER,
        response_text=RESPONSE,
    )


def test_verified_partial_need():
    result = build()
    assert result["coverage"] == "partially_addressed"
    assert result["severity"] is None
    assert result["score"] is None


def test_verified_unaddressed_without_response_quote():
    result = build(
        first=original("unaddressed"),
        second=audit("confirmed", "unaddressed"),
    )
    assert result["need"]["evidence"] in USER
    assert result["coverage"] == "unaddressed"


def test_rejected_result_blocks():
    with pytest.raises(CE1VerifiedNeedsError):
        build(second=audit("rejected", "addressed"))


def test_ambiguous_result_blocks():
    with pytest.raises(CE1VerifiedNeedsError):
        build(
            first=original("ambiguous"),
            second=audit("ambiguous", "ambiguous"),
        )


def test_invalid_user_evidence_blocks():
    invalid = item()
    invalid["evidence"] = "texto inventado"

    with pytest.raises(ValueError):
        build(need=invalid)


def test_conflicting_confirmation_blocks():
    with pytest.raises(ValueError):
        build(second=audit("confirmed", "addressed"))


def test_no_severity_inference():
    result = build()
    assert result["verification"]["original"]["reason"]
    assert result["severity"] is None
