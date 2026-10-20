"""Validación exacta de evidencia IR."""

from .contracts import Context, Evidence


def source_text(ctx: Context, ev: Evidence) -> str:
    if ev.source == "user":
        return ctx.user

    if ev.source == "response":
        return ctx.response

    if ev.source == "history":
        index = ev.history_index
        if index is None or index >= len(ctx.prior_history):
            raise ValueError("history_index fuera de rango")
        return ctx.prior_history[index].text

    raise ValueError("Fuente no autorizada")


def verify_exact_evidence(
    ctx: Context,
    ev: Evidence
) -> bool:
    """Comprueba literalidad, no soporte semántico."""
    try:
        text = source_text(ctx, ev)
    except ValueError:
        return False

    return ev.quote in text