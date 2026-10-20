from unittest.mock import patch

from backend.evaluators.semantic import af_ai_af7 as af7
from backend.evaluators.rules.af7_scorer import _score_item


def test_validacion_minima_llega_al_scorer(monkeypatch):
    item = {
        "id": "minimal_1",
        "blocked_action": "",
        "blocked_action_evidence": {
            "quote": "",
            "source": "current_ai",
        },
        "procedure": "Respira",
        "procedure_evidence": {
            "quote": "Respira",
            "source": "current_ai",
        },
        "when_or_how_evidence": {
            "quote": "",
            "source": "current_ai",
        },
        "minimal_regulation_validation": {
            "status": "supported",
        },
    }

    monkeypatch.setattr(
        af7,
        "_recover_ai_item_literal_evidence",
        lambda **kwargs: kwargs["item"],
    )

    for name in (
        "_validate_b",
        "_validate_t",
        "_validate_m",
        "_validate_safe",
        "_validate_proportional",
    ):
        monkeypatch.setattr(
            af7,
            name,
            lambda **kwargs: {"status": "not_supported"},
        )

    processed = af7._process_item(
        item=item,
        interferences=[],
        current_ai="Respira",
        activation_context="",
        model="TEST",
        timeout=1,
    )

    assert processed["minimal_regulation_validation"]["status"] == "supported"

    assert _score_item(
        processed,
        elimination_guarantee=False,
    ) == 1


def test_sin_validacion_minima_no_recibe_punto():
    item = {
        "procedure": "Respira",
        "semantic_validation": {
            name: {"status": "not_supported"}
            for name in ("B", "T", "M", "SAFE", "PROPORTIONAL")
        },
        "minimal_regulation_validation": {
            "status": "ambiguous",
        },
    }

    assert _score_item(
        item,
        elimination_guarantee=False,
    ) == 0
