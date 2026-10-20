import pytest

from backend.evaluators.ce.ce_a import evidence_verifier as ev


def test_supported_paraphrase(monkeypatch):
    def fake_provider(**kwargs):
        return {
            "verdict": "supported",
            "reason": "La cita describe esa acci?n.",
        }

    monkeypatch.setattr(
        ev,
        "run_structured_semantic",
        fake_provider,
    )

    result = ev.verify_interpretation(
        "Recomienda preparar anticipadamente la ropa.",
        "Puedes preparar tu ropa.",
        "Puedes preparar tu ropa.",
        use_cache=False,
    )

    assert result["verdict"] == "supported"


def test_rejects_invented_quote():
    with pytest.raises(ev.CEAEvidenceError):
        ev.verify_interpretation(
            "Recomienda respirar.",
            "Respira lentamente.",
            "Puedes preparar tu ropa.",
            use_cache=False,
        )


def test_rejects_invalid_verdict():
    with pytest.raises(ev.CEAEvidenceError):
        ev.validate_verdict({
            "verdict": "score_3",
            "reason": "No permitido",
        })


def test_accepts_ambiguous():
    result = ev.validate_verdict({
        "verdict": "ambiguous",
        "reason": "La cita no permite concluirlo.",
    })

    assert result["verdict"] == "ambiguous"
