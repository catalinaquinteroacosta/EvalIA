import pytest

from backend.evaluators.ce.ce_a import coverage_auditor as ca


def validate(result):
    return ca.validate_audit(
        result,
        user_text="Que puedo hacer esta noche?",
        response_text="Puedes preparar tus documentos.",
        prior_context="Manana tengo una entrevista.",
    )


def test_complete_without_findings():
    result = validate({
        "verdict": "complete",
        "findings": [],
        "reason": "No hay faltantes relevantes.",
    })
    assert result["verdict"] == "complete"


def test_complete_with_explanatory_finding_rejected():
    with pytest.raises(ValueError):
        validate({
            "verdict": "complete",
            "findings": [{
                "field": "ce2_essential_omissions",
                "issue": "Un horario detallado es opcional.",
                "evidence": "",
            }],
            "reason": "No hay faltantes relevantes.",
        })


def test_incomplete_without_findings_rejected():
    with pytest.raises(ValueError):
        validate({
            "verdict": "incomplete",
            "findings": [],
            "reason": "Falta informacion.",
        })


def test_invented_quote_rejected():
    with pytest.raises(
        ValueError,
        match="cita inventada",
    ):
        validate({
            "verdict": "incomplete",
            "findings": [{
                "field": "ce1_relevant_evidence",
                "issue": "Falta registrar una accion.",
                "evidence": "Una cita inexistente.",
            }],
            "reason": "Falta una accion.",
        })
