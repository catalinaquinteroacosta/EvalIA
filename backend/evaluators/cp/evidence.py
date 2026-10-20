"""EvalIA CP — validación determinística de evidencia literal.

Responsabilidades:
- resolver la fuente exacta de una evidencia;
- validar history_index;
- comprobar literalidad exacta;
- mantener separación entre literalidad y soporte semántico.

NO:
- interpreta lenguaje;
- puntúa;
- decide aplicabilidad;
- decide si una cita respalda semánticamente una afirmación.
"""

from __future__ import annotations

from .context import CPEvaluationContext


def evidence_haystack(
    *,
    context: CPEvaluationContext,
    source: str,
    history_index: int | None,
) -> str:
    """Devuelve exactamente el texto autorizado por la fuente."""

    if not isinstance(context, CPEvaluationContext):
        raise TypeError(
            "context debe ser CPEvaluationContext."
        )

    if source == "history":
        if (
            isinstance(history_index, bool)
            or not isinstance(history_index, int)
        ):
            raise ValueError(
                "source='history' requiere history_index entero."
            )

        if not 0 <= history_index < len(context.prior_history):
            raise ValueError(
                "history_index fuera del historial autorizado."
            )

        return context.prior_history[history_index].text

    if source == "user":
        if history_index is not None:
            raise ValueError(
                "source='user' requiere history_index=None."
            )

        return context.current_user_message

    if source == "response":
        if history_index is not None:
            raise ValueError(
                "source='response' requiere history_index=None."
            )

        return context.current_response

    raise ValueError(
        f"Fuente de evidencia desconocida: {source!r}"
    )


def verify_literal_evidence(
    *,
    context: CPEvaluationContext,
    source: str,
    history_index: int | None,
    quote: str,
) -> bool:
    """Comprueba únicamente literalidad exacta.

    True significa:
        la cita existe literalmente en la fuente declarada.

    True NO significa:
        la cita respalda semánticamente la interpretación.
    """

    if not isinstance(quote, str):
        raise TypeError("quote debe ser str.")

    if not quote:
        raise ValueError("quote no puede estar vacía.")

    haystack = evidence_haystack(
        context=context,
        source=source,
        history_index=history_index,
    )

    return quote in haystack


def require_literal_evidence(
    *,
    context: CPEvaluationContext,
    source: str,
    history_index: int | None,
    quote: str,
) -> None:
    """Gate fail-closed de literalidad."""

    if not verify_literal_evidence(
        context=context,
        source=source,
        history_index=history_index,
        quote=quote,
    ):
        raise ValueError(
            "La quote no existe literalmente en "
            "la fuente declarada."
        )
