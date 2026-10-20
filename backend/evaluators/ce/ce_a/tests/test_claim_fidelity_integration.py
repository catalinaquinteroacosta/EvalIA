import pytest

from backend.evaluators.ce.ce_a import claim_verifier as cv
from backend.evaluators.ce.ce_a import claim_fidelity_auditor as fa


INTERPRETATION = (
    "La respuesta valida los nervios y reduce "
    "la exigencia de perfeccion."
)
EVIDENCE = "Es comprensible estar nerviosa."
CLAIMS = [
    "La respuesta valida los nervios.",
    "La respuesta reduce la exigencia de perfeccion.",
]


@pytest.mark.parametrize(
    "verdict",
    ["faithful", "unfaithful", "ambiguous"],
)
def test_audit_accepts_valid_verdicts(verdict):
    result = fa.validate_audit({
        "verdict": verdict,
        "reason": "Independent audit result.",
        "findings": (
            [] if verdict == "faithful"
            else ["Fidelity requires attention."]
        ),
    })
    assert result["verdict"] == verdict


def test_audit_rejects_invalid_structure():
    with pytest.raises(ValueError):
        fa.validate_audit({
            "verdict": "faithful",
            "reason": "",
            "findings": [],
        })


def configure(monkeypatch, audit_verdict, claims=None):
    selected = CLAIMS if claims is None else claims
    calls = []

    monkeypatch.setattr(
        cv,
        "get_semantic_identity",
        lambda **kwargs: {"model": "mock-model"},
    )

    monkeypatch.setattr(
        cv,
        "run_structured_semantic",
        lambda **kwargs: {
            "claims": selected,
            "decomposition_complete": True,
            "reason": "Decomposition generated.",
        },
    )

    monkeypatch.setattr(
        cv,
        "audit_claim_fidelity",
        lambda *args, **kwargs: {
            "verdict": audit_verdict,
            "reason": "Independent fidelity decision.",
            "findings": (
                [] if audit_verdict == "faithful"
                else ["A claim may be missing."]
            ),
        },
    )

    def mock_verify(**kwargs):
        calls.append(kwargs["interpretation"])
        return {
            "verdict": "supported",
            "reason": "Exact quotation supports the claim.",
        }

    monkeypatch.setattr(cv, "verify_interpretation", mock_verify)
    return calls


def test_faithful_decomposition_proceeds(monkeypatch):
    calls = configure(monkeypatch, "faithful")

    result = cv.verify_claims(
        INTERPRETATION,
        EVIDENCE,
        EVIDENCE,
        use_cache=False,
    )

    assert result["verdict"] == "supported"
    assert calls == CLAIMS
    assert len(result["claims"]) == 2


@pytest.mark.parametrize(
    "audit_verdict",
    ["unfaithful", "ambiguous"],
)
def test_failed_fidelity_blocks_claim_verification(
    monkeypatch, audit_verdict
):
    calls = configure(
        monkeypatch,
        audit_verdict,
        claims=[CLAIMS[0]],
    )

    result = cv.verify_claims(
        INTERPRETATION,
        EVIDENCE,
        EVIDENCE,
        use_cache=False,
    )

    assert result["verdict"] == "ambiguous"
    assert result["fidelity"]["verdict"] == audit_verdict
    assert calls == []


def test_incomplete_decomposition_blocks_audit(
    monkeypatch,
):
    calls = configure(monkeypatch, "faithful")

    monkeypatch.setattr(
        cv,
        "run_structured_semantic",
        lambda **kwargs: {
            "claims": [CLAIMS[0]],
            "decomposition_complete": False,
            "reason": "Could not preserve every assertion.",
        },
    )

    result = cv.verify_claims(
        INTERPRETATION,
        EVIDENCE,
        EVIDENCE,
        use_cache=False,
    )

    assert result["verdict"] == "ambiguous"
    assert result["decomposition_complete"] is False
    assert calls == []
