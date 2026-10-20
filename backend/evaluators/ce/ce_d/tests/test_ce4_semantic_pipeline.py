
from backend.evaluators.ce.ce_d.ce4_semantic_pipeline import (
    evaluate_ce4_semantic,
)


RESPONSE = (
    "Preparacion: identifica los hechos. "
    "Conversacion: expresa tus necesidades. "
    "Cierre: acuerda proximos pasos."
)


def extraction_runner(**kwargs):
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
            "interpretation": "Organizacion funcional",
        }],
        "rubric_execution": "clear_contextual_verifiable",
    }


def cache_operation(**kwargs):
    return kwargs["validate_result"](kwargs["execute"]())


def test_all_supported_scores_three():
    def runner(**kwargs):
        return {
            "verdict": "supported",
            "reason": "La proposicion esta respaldada.",
            "counterevidence": "",
        }

    result = evaluate_ce4_semantic(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction_runner=extraction_runner,
        verdict_runner=runner,
        cache_operation=cache_operation,
    )

    assert result["status"] == "scored"
    assert result["score"] == 3
    assert len(result["trace"]) == 3


def test_disagreement_triggers_reconciliation():
    stages = []

    def runner(**kwargs):
        stage = (
            "reconciliation"
            if "Etapa: reconciliation" in kwargs["prompt"]
            else "verification"
        )
        stages.append(stage)

        return {
            "verdict": "ambiguous" if stage == "verification"
            else "supported",
            "reason": "Decision controlada.",
            "counterevidence": "",
        }

    result = evaluate_ce4_semantic(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction_runner=extraction_runner,
        verdict_runner=runner,
        cache_operation=cache_operation,
    )

    assert result["status"] == "scored"
    assert "reconciliation" in stages


def test_unresolved_disagreement_is_blocked():
    def runner(**kwargs):
        return {
            "verdict": "ambiguous",
            "reason": "Evidencia insuficiente.",
            "counterevidence": "",
        }

    result = evaluate_ce4_semantic(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction_runner=extraction_runner,
        verdict_runner=runner,
        cache_operation=cache_operation,
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None


def test_provider_error_is_blocked():
    def failing_runner(**kwargs):
        raise RuntimeError("Provider unavailable")

    result = evaluate_ce4_semantic(
        user_text="Ayudame a preparar una conversacion.",
        response_text=RESPONSE,
        extraction_runner=failing_runner,
    )

    assert result["status"] == "BLOCKED"
    assert result["score"] is None
    assert result["blocked_components"] == ["extraction"]
