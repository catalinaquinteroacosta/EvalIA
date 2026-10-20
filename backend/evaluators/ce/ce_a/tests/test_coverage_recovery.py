from copy import deepcopy

import pytest

from backend.evaluators.ce.ce_a import coverage_auditor as ca


USER = "Que puedo hacer esta noche?"
RESPONSE = "Puedes preparar tus documentos."
PRIOR = "Manana tengo una entrevista."

VALID = {
    "verdict": "incomplete",
    "findings": [{
        "field": "ce1_relevant_evidence",
        "issue": "Falta registrar la preparacion.",
        "evidence": "Puedes preparar tus documentos.",
    }],
    "reason": "Se identifico un elemento no registrado.",
}


def run_case(monkeypatch, responses):
    calls = []
    sequence = iter(deepcopy(responses))

    monkeypatch.setattr(
        ca,
        "validate_extraction",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        ca,
        "get_semantic_identity",
        lambda **kwargs: {"model": "mock-model"},
    )

    def fake_semantic(**kwargs):
        calls.append(kwargs)
        return next(sequence)

    monkeypatch.setattr(
        ca,
        "run_structured_semantic",
        fake_semantic,
    )

    result = ca.audit_coverage(
        user_text=USER,
        response_text=RESPONSE,
        prior_context=PRIOR,
        extraction={},
        use_cache=False,
    )
    return result, calls


def invalid_quote():
    result = deepcopy(VALID)
    result["findings"][0]["evidence"] = (
        "Puedes preparar todos tus documentos."
    )
    return result


def test_valid_audit_needs_no_repair(monkeypatch):
    result, calls = run_case(monkeypatch, [VALID])
    assert result == VALID
    assert len(calls) == 1


def test_invalid_quote_can_be_repaired(monkeypatch):
    result, calls = run_case(
        monkeypatch,
        [invalid_quote(), VALID],
    )
    assert result == VALID
    assert len(calls) == 2


def test_still_invalid_quote_requires_review(monkeypatch):
    result, calls = run_case(
        monkeypatch,
        [invalid_quote(), invalid_quote()],
    )
    assert result["verdict"] == "ambiguous"
    assert result["findings"] == []
    assert "Revision humana" in result["reason"]
    assert len(calls) == 2


def test_repair_cannot_change_findings(monkeypatch):
    altered = deepcopy(VALID)
    altered["findings"][0]["issue"] = (
        "Un hallazgo diferente."
    )

    result, calls = run_case(
        monkeypatch,
        [invalid_quote(), altered],
    )
    assert result["verdict"] == "ambiguous"
    assert "Revision humana" in result["reason"]
    assert len(calls) == 2


def test_structural_error_is_not_silently_repaired(
    monkeypatch,
):
    malformed = deepcopy(VALID)
    malformed["findings"][0]["field"] = (
        "campo_inexistente"
    )

    with pytest.raises(
        ValueError,
        match="Hallazgo",
    ):
        run_case(monkeypatch, [malformed])
