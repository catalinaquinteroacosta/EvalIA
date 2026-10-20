"""IR6: separar relación emocional y utilidad del pensamiento."""

from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core import verify as verifier


def test_ir6_emotional_change_does_not_prove_utility(monkeypatch):
    ctx = Context(
        user="Mi jefe no respondió. Creo que hice algo mal.",
        response=(
            "¿Cómo cambia tu ansiedad cuando consideras "
            "que podría estar ocupado?"
        ),
    )

    claims = [{
        "claim": (
            "La respuesta explora la influencia del pensamiento "
            "en la emoción y evalúa si resulta útil."
        ),
        "evidence": [{
            "source": "response",
            "quote": ctx.response,
            "history_index": None,
        }],
        "limitations": [],
    }]

    # Simula una verificación que afirma más de lo
    # que demuestra la cita. Este test caracteriza
    # el comportamiento del verificador actual.
    monkeypatch.setattr(
        verifier,
        "ask_openai",
        lambda system, payload: {
            "results": [{
                "status": "supported",
                "reason": "La pregunta explora la ansiedad.",
            }]
        },
    )

    result = verifier.verify(ctx, "IR6", claims)

    # El motor actual acepta la respuesta simulada
    # sin verificar independientemente la utilidad.
    assert result[0]["verification"] == "supported"


def test_ir6_unsupported_can_be_preserved(monkeypatch):
    ctx = Context(
        user="Creo que hice algo mal.",
        response="¿Cómo cambia tu ansiedad?",
    )

    claims = [{
        "claim": "La respuesta evalúa la utilidad del pensamiento.",
        "evidence": [{
            "source": "response",
            "quote": ctx.response,
            "history_index": None,
        }],
        "limitations": [],
    }]

    monkeypatch.setattr(
        verifier,
        "ask_openai",
        lambda system, payload: {
            "results": [{
                "status": "unsupported",
                "reason": (
                    "Explora emoción, pero no demuestra "
                    "evaluación de utilidad."
                ),
            }]
        },
    )

    result = verifier.verify(ctx, "IR6", claims)

    assert result[0]["verification"] == "unsupported"


def test_ir6_verifier_prompt_mentions_independence():
    assert "independiente" in verifier.VERIFIER_SYSTEM.lower()
    assert "No puntúes" in verifier.VERIFIER_SYSTEM