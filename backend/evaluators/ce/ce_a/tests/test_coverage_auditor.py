import copy
import pytest

from backend.evaluators.ce.ce_a import coverage_auditor as ca
from backend.evaluators.ce.ce_a.tests.test_semantic_contract import (
    USER, RESPONSE, example,
)


def test_complete_coverage(monkeypatch):
    monkeypatch.setattr(
        ca, "run_structured_semantic",
        lambda **kwargs: {
            "verdict": "complete",
            "findings": [],
            "reason": "No se identificaron faltantes.",
        },
    )
    result = ca.audit_coverage(
        user_text=USER,
        response_text=RESPONSE,
        extraction=example(),
        use_cache=False,
    )
    assert result["verdict"] == "complete"


def test_detects_missing_component(monkeypatch):
    monkeypatch.setattr(
        ca, "run_structured_semantic",
        lambda **kwargs: {
            "verdict": "incomplete",
            "findings": [{
                "field": "ce1_relevant_evidence",
                "issue": "Falta registrar una recomendaci?n.",
                "evidence": RESPONSE,
            }],
            "reason": "Hay contenido no registrado.",
        },
    )
    result = ca.audit_coverage(
        user_text=USER,
        response_text=RESPONSE,
        extraction=example(),
        use_cache=False,
    )
    assert len(result["findings"]) == 1


def test_rejects_invented_quote():
    with pytest.raises(ValueError):
        ca.validate_audit(
            {
                "verdict": "incomplete",
                "findings": [{
                    "field": "ce1_digressions",
                    "issue": "Digresi?n inventada.",
                    "evidence": "Una cita que nunca existi?.",
                }],
                "reason": "Se encontr? una digresi?n.",
            },
            user_text=USER,
            response_text=RESPONSE,
            prior_context="",
        )


def test_rejects_contradictory_complete():
    with pytest.raises(ValueError):
        ca.validate_audit(
            {
                "verdict": "complete",
                "findings": [{
                    "field": "ce1_relevant_evidence",
                    "issue": "Falta contenido.",
                    "evidence": RESPONSE,
                }],
                "reason": "Contradicci?n.",
            },
            user_text=USER,
            response_text=RESPONSE,
            prior_context="",
        )


def test_ambiguous_coverage(monkeypatch):
    monkeypatch.setattr(
        ca, "run_structured_semantic",
        lambda **kwargs: {
            "verdict": "ambiguous",
            "findings": [],
            "reason": "Contexto insuficiente.",
        },
    )
    result = ca.audit_coverage(
        user_text=USER,
        response_text=RESPONSE,
        extraction=copy.deepcopy(example()),
        use_cache=False,
    )
    assert result["verdict"] == "ambiguous"
