import copy
import pytest

from backend.evaluators.ce.ce_a import citation_repair as cr
from backend.evaluators.ce.ce_a.tests.test_semantic_contract import (
    USER,
    RESPONSE,
    example,
)


def test_repairs_discontinuous_quote(monkeypatch):
    broken = copy.deepcopy(example())
    broken["ce1_relevant_evidence"][0]["evidence"] = (
        "Puedes preparar ... los documentos"
    )

    monkeypatch.setattr(
        cr,
        "run_structured_semantic",
        lambda **kwargs: copy.deepcopy(example()),
    )

    result = cr.repair_citations(
        broken,
        user_text=USER,
        response_text=RESPONSE,
        model="test-model",
    )

    assert result["ce1_relevant_evidence"][0][
        "evidence"
    ] in RESPONSE


def test_rejects_failed_repair(monkeypatch):
    broken = copy.deepcopy(example())
    broken["ce1_relevant_evidence"][0]["evidence"] = (
        "Una cita completamente inventada."
    )

    monkeypatch.setattr(
        cr,
        "run_structured_semantic",
        lambda **kwargs: copy.deepcopy(broken),
    )

    with pytest.raises(cr.CEACitationRepairError):
        cr.repair_citations(
            broken,
            user_text=USER,
            response_text=RESPONSE,
            model="test-model",
        )


def test_repair_does_not_assign_scores(monkeypatch):
    captured = {}

    def fake_provider(**kwargs):
        captured.update(kwargs)
        return copy.deepcopy(example())

    monkeypatch.setattr(
        cr,
        "run_structured_semantic",
        fake_provider,
    )

    cr.repair_citations(
        example(),
        user_text=USER,
        response_text=RESPONSE,
        model="test-model",
    )

    assert captured["provider"] == "openai"
    assert "No asignes puntuaciones" in captured["prompt"]
