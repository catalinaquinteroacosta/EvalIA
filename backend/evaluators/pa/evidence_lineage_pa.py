"""Validacion estricta de procedencia de evidencia PA."""


def validate_evidence(context, evidence):
    if not isinstance(evidence, dict):
        return False

    source = evidence.get("source")
    quote = evidence.get("quote")
    history_index = evidence.get("history_index")

    if not isinstance(quote, str) or not quote.strip():
        return False

    if source == "response":
        return (
            history_index is None
            and quote in context["current_response"]
        )

    if source == "user":
        return (
            history_index is None
            and quote in context["current_user"]
        )

    if source == "history":
        history = context.get("prior_history", [])

        if (
            not isinstance(history_index, int)
            or isinstance(history_index, bool)
            or history_index < 0
            or history_index >= len(history)
        ):
            return False

        message = history[history_index]

        return (
            message.get("role") in {"user", "assistant"}
            and quote in message.get("text", "")
        )

    return False


def validate_response_quotes(context, quotes):
    if not isinstance(quotes, list):
        return False

    return all(
        validate_evidence(
            context,
            {
                "source": "response",
                "quote": quote,
                "history_index": None,
            },
        )
        for quote in quotes
    )
