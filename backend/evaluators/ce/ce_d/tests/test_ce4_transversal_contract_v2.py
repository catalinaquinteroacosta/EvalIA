
import pytest

from backend.evaluators.ce.pilot.integrate_ce2_ce5 import evaluate


USER = "Necesito una explicacion extensa con varias partes."
RESPONSE = (
    "Primero identifica el problema principal. "
    "Despues revisa las posibles causas. "
    "Luego compara las alternativas. "
    "Finalmente elige una accion y comprueba el resultado."
)


def draft(*, applicable=True, execution="omitted_or_opposite"):
    return {
        "analysis_complete": True,
        "full_response_audited": True,
        "applicable": applicable,
        "applicability_evidence": {
            "source": "response",
            "quote": RESPONSE,
            "interpretation": (
                "La extension requiere evaluar la organizacion visual."
            ),
        },
        "rubric_execution": execution,
        "claims": [
            {
                "source": "response",
                "quote": RESPONSE,
                "interpretation": (
                    "La respuesta presenta varias instrucciones sin "
                    "separacion visual."
                ),
            }
        ] if applicable else [],
    }


@pytest.mark.parametrize("execution,expected", [
    ("omitted_or_opposite", 0),
    ("minimal_generic", 1),
    ("adequate_limited", 2),
    ("clear_contextual_verifiable", 3),
])
def test_ce4_scoring_contract_with_verified_mock(execution, expected):
    result = evaluate(
        indicator="CE4",
        user_text=USER,
        response_text=RESPONSE,
        semantic_runner=lambda **kwargs: draft(execution=execution),
        verify_claim=lambda *args: "supported",
    )
    assert result["status"] == "scored"
    assert result["score"] == expected


def test_ce4_ambiguity_never_scores():
    result = evaluate(
        indicator="CE4",
        user_text=USER,
        response_text=RESPONSE,
        semantic_runner=lambda **kwargs: draft(),
        verify_claim=lambda *args: "ambiguous",
    )
    assert result["score"] is None
    assert result["status"] in ("BLOCKED", "insufficient_evidence")


def test_ce4_unsupported_never_scores():
    result = evaluate(
        indicator="CE4",
        user_text=USER,
        response_text=RESPONSE,
        semantic_runner=lambda **kwargs: draft(),
        verify_claim=lambda *args: "not_supported",
    )
    assert result["score"] is None
    assert result["status"] in ("BLOCKED", "insufficient_evidence")
