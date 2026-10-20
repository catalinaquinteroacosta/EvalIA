from backend.evaluators.pa.evidence_lineage_pa import (
    validate_evidence,
    validate_response_quotes,
)


CONTEXT = {
    "current_user": "Tengo poco tiempo y muchas tareas.",
    "current_response": "Haz una lista de tareas y empieza por una.",
    "prior_history": [
        {"role": "user", "text": "Solo tengo diez minutos."},
        {"role": "assistant", "text": "Podemos empezar poco a poco."},
    ],
}


def test_response_literal():
    assert validate_evidence(
        CONTEXT,
        {
            "source": "response",
            "quote": "Haz una lista de tareas",
            "history_index": None,
        },
    )


def test_user_quote_cannot_be_response():
    assert not validate_response_quotes(
        CONTEXT,
        ["Tengo poco tiempo y muchas tareas."],
    )


def test_user_literal():
    assert validate_evidence(
        CONTEXT,
        {
            "source": "user",
            "quote": "Tengo poco tiempo",
            "history_index": None,
        },
    )


def test_history_index():
    assert validate_evidence(
        CONTEXT,
        {
            "source": "history",
            "quote": "Solo tengo diez minutos.",
            "history_index": 0,
        },
    )


def test_wrong_history_index():
    assert not validate_evidence(
        CONTEXT,
        {
            "source": "history",
            "quote": "Solo tengo diez minutos.",
            "history_index": 1,
        },
    )


def test_boolean_index_rejected():
    assert not validate_evidence(
        CONTEXT,
        {
            "source": "history",
            "quote": "Solo tengo diez minutos.",
            "history_index": True,
        },
    )
