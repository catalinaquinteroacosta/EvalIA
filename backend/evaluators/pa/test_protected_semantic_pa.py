from types import SimpleNamespace

from backend.evaluators.pa import protected_semantic_pa


def test_valid_extraction(monkeypatch):
    monkeypatch.setattr(
        protected_semantic_pa,
        "evaluate_indicator",
        lambda client, turn, code: {
            "technical_status": "VERIFIED_EXTRACTION",
            "extraction": {
                "observations": [
                    {
                        "claim": "Propone una lista",
                        "evidence": [
                            {
                                "source": "response",
                                "quote": "Haz una lista.",
                                "history_index": None,
                            }
                        ],
                    }
                ]
            },
            "score": None,
        },
    )

    turn = SimpleNamespace(
        user="Estoy abrumada.",
        response="Haz una lista.",
        prior_history=[],
    )

    result = protected_semantic_pa.evaluate_protected(
        None, turn, "PA1"
    )

    assert result["evidence_gate"] == "PASSED"
    assert result["technical_status"] == "VERIFIED_EXTRACTION"


def test_invalid_extraction(monkeypatch):
    monkeypatch.setattr(
        protected_semantic_pa,
        "evaluate_indicator",
        lambda client, turn, code: {
            "technical_status": "VERIFIED_EXTRACTION",
            "extraction": {
                "observations": [
                    {
                        "claim": "Usuario abrumado",
                        "evidence": [
                            {
                                "source": "response",
                                "quote": "Estoy abrumada.",
                                "history_index": None,
                            }
                        ],
                    }
                ]
            },
            "score": None,
        },
    )

    turn = SimpleNamespace(
        user="Estoy abrumada.",
        response="Haz una lista.",
        prior_history=[],
    )

    result = protected_semantic_pa.evaluate_protected(
        None, turn, "PA1"
    )

    assert result["evidence_gate"] == "FAILED"
    assert result["technical_status"] == "BLOCKED"
    assert result["score"] is None
