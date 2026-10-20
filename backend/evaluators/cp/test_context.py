"""Pruebas del contexto temporal CP."""

import pytest

from backend.evaluators.cp.context import (
    CPEvaluationContext,
    PriorTurn,
)


def test_context_accepts_prior_history():
    ctx = CPEvaluationContext(
        prior_history=(
            PriorTurn(
                role="user",
                text="Antes dije que me preocupaban las exposiciones.",
            ),
            PriorTurn(
                role="assistant",
                text="Entiendo que las exposiciones te preocupan.",
            ),
        ),
        current_user_message=(
            "Hoy volvió a pasar."
        ),
        current_response=(
            "Parece relacionado con lo que contaste antes."
        ),
    )

    assert len(ctx.prior_history) == 2


def test_context_has_no_future_history_field():
    fields = CPEvaluationContext.__dataclass_fields__

    assert "future_history" not in fields
    assert "future_turns" not in fields


def test_history_source_only_returns_prior_history():
    ctx = CPEvaluationContext(
        prior_history=(
            PriorTurn(
                role="user",
                text="HISTORIAL UNO",
            ),
            PriorTurn(
                role="assistant",
                text="HISTORIAL DOS",
            ),
        ),
        current_user_message="MENSAJE ACTUAL",
        current_response="RESPUESTA ACTUAL",
    )

    assert ctx.source_texts(
        "history"
    ) == (
        "HISTORIAL UNO",
        "HISTORIAL DOS",
    )


def test_user_source_is_only_current_user_message():
    ctx = CPEvaluationContext(
        prior_history=(
            PriorTurn(
                role="user",
                text="USUARIO ANTERIOR",
            ),
        ),
        current_user_message="USUARIO ACTUAL",
        current_response="RESPUESTA ACTUAL",
    )

    assert ctx.source_texts(
        "user"
    ) == (
        "USUARIO ACTUAL",
    )


def test_response_source_is_only_current_response():
    ctx = CPEvaluationContext(
        prior_history=(),
        current_user_message="USUARIO ACTUAL",
        current_response="RESPUESTA ACTUAL",
    )

    assert ctx.source_texts(
        "response"
    ) == (
        "RESPUESTA ACTUAL",
    )


def test_invalid_source_fails_closed():
    ctx = CPEvaluationContext(
        prior_history=(),
        current_user_message="USUARIO",
        current_response="RESPUESTA",
    )

    with pytest.raises(ValueError):
        ctx.source_texts(
            "future"
        )


def test_empty_current_user_rejected():
    with pytest.raises(ValueError):
        CPEvaluationContext(
            prior_history=(),
            current_user_message=" ",
            current_response="RESPUESTA",
        )


def test_empty_current_response_rejected():
    with pytest.raises(ValueError):
        CPEvaluationContext(
            prior_history=(),
            current_user_message="USUARIO",
            current_response=" ",
        )
