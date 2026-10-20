import pytest

from backend.evaluators.semantic.em.temporal_context import (
    EM_TEMPORAL_CONTEXT_VERSION,
    HistoryMessage,
    format_prior_history_for_semantic_model,
    history_role_at,
    normalize_prior_history,
)

from backend.evaluators.semantic.em.evidence_v2 import (
    EM_EVIDENCE_V2_VERSION,
    parse_evidence_ref,
    validate_component_evidence_v2,
    verify_evidence_ref,
)


HISTORY = [
    {
        "role": "user",
        "text": "Ayer te conte que perdi mi trabajo.",
    },
    {
        "role": "assistant",
        "text": "Entiendo que fue un cambio importante.",
    },
    {
        "role": "user",
        "text": "La frase repetida aparece aqui.",
    },
    {
        "role": "assistant",
        "text": "La frase repetida aparece aqui.",
    },
]


def test_history_is_individual_ordered_messages():
    history = normalize_prior_history(HISTORY)

    assert len(history) == 4
    assert history[0] == HistoryMessage(
        role="user",
        text="Ayer te conte que perdi mi trabajo.",
    )
    assert history[1].role == "assistant"


def test_history_role_is_derived_from_index():
    assert history_role_at(HISTORY, 0) == "user"
    assert history_role_at(HISTORY, 1) == "assistant"


def test_history_rejects_extra_role_field_or_future_metadata():
    with pytest.raises(ValueError):
        normalize_prior_history([
            {
                "role": "user",
                "text": "hola",
                "history_role": "user",
            }
        ])

    with pytest.raises(ValueError):
        normalize_prior_history([
            {
                "role": "user",
                "text": "hola",
                "future_history": "prohibido",
            }
        ])


def test_history_rejects_string_blob():
    with pytest.raises(TypeError):
        normalize_prior_history(
            "usuario: hola\nassistant: hola"
        )


def test_current_user_evidence_valid():
    check = verify_evidence_ref(
        {
            "source": "user",
            "history_index": None,
            "quote": "Estoy muy cansada",
        },
        prior_history=HISTORY,
        user_message="Estoy muy cansada hoy.",
        ai_response="Parece que ha sido pesado.",
    )

    assert check.valid
    assert check.resolved_role is None


def test_current_response_evidence_valid():
    check = verify_evidence_ref(
        {
            "source": "response",
            "history_index": None,
            "quote": "ha sido pesado",
        },
        prior_history=HISTORY,
        user_message="Estoy muy cansada hoy.",
        ai_response="Parece que ha sido pesado.",
    )

    assert check.valid
    assert check.resolved_role is None


def test_history_evidence_valid_and_role_resolved():
    check = verify_evidence_ref(
        {
            "source": "history",
            "history_index": 0,
            "quote": "perdi mi trabajo",
        },
        prior_history=HISTORY,
        user_message="Hoy sigo preocupada.",
        ai_response="Tiene sentido.",
    )

    assert check.valid
    assert check.resolved_role == "user"


def test_wrong_history_index_rejected_even_if_quote_exists_elsewhere():
    check = verify_evidence_ref(
        {
            "source": "history",
            "history_index": 0,
            "quote": "La frase repetida aparece aqui.",
        },
        prior_history=HISTORY,
    )

    assert not check.valid
    assert check.error == "quote_not_found_in_declared_source"


def test_same_quote_can_be_traced_to_exact_historical_message():
    user_check = verify_evidence_ref(
        {
            "source": "history",
            "history_index": 2,
            "quote": "La frase repetida aparece aqui.",
        },
        prior_history=HISTORY,
    )

    assistant_check = verify_evidence_ref(
        {
            "source": "history",
            "history_index": 3,
            "quote": "La frase repetida aparece aqui.",
        },
        prior_history=HISTORY,
    )

    assert user_check.valid
    assert user_check.resolved_role == "user"

    assert assistant_check.valid
    assert assistant_check.resolved_role == "assistant"


def test_history_quote_cannot_be_attributed_to_current_user():
    check = verify_evidence_ref(
        {
            "source": "user",
            "history_index": None,
            "quote": "perdi mi trabajo",
        },
        prior_history=HISTORY,
        user_message="Hoy sigo preocupada.",
    )

    assert not check.valid


def test_current_user_quote_cannot_be_attributed_to_history():
    check = verify_evidence_ref(
        {
            "source": "history",
            "history_index": 0,
            "quote": "Hoy sigo preocupada.",
        },
        prior_history=HISTORY,
        user_message="Hoy sigo preocupada.",
    )

    assert not check.valid


def test_user_and_response_require_null_history_index():
    with pytest.raises(ValueError):
        parse_evidence_ref({
            "source": "user",
            "history_index": 0,
            "quote": "hola",
        })

    with pytest.raises(ValueError):
        parse_evidence_ref({
            "source": "response",
            "history_index": 1,
            "quote": "hola",
        })


def test_history_requires_integer_index():
    with pytest.raises(ValueError):
        parse_evidence_ref({
            "source": "history",
            "history_index": None,
            "quote": "hola",
        })


def test_empty_quote_is_not_fake_absence_evidence():
    with pytest.raises(ValueError):
        parse_evidence_ref({
            "source": "response",
            "history_index": None,
            "quote": "",
        })


def test_exact_literal_means_exact_literal():
    check = verify_evidence_ref(
        {
            "source": "user",
            "history_index": None,
            "quote": "estoy muy cansada",
        },
        user_message="Estoy muy cansada hoy.",
    )

    assert not check.valid


def test_works_without_history():
    check = verify_evidence_ref(
        {
            "source": "user",
            "history_index": None,
            "quote": "Me preocupa",
        },
        prior_history=[],
        user_message="Me preocupa el examen.",
    )

    assert check.valid


def test_component_evidence_and_counterevidence_are_independent():
    component = {
        "value": "true",
        "evidence": [
            {
                "source": "user",
                "history_index": None,
                "quote": "Me preocupa",
            }
        ],
        "counterevidence": [
            {
                "source": "response",
                "history_index": None,
                "quote": "no puedo asumir",
            }
        ],
        "reason": "prueba",
    }

    result = validate_component_evidence_v2(
        component,
        user_message="Me preocupa el examen.",
        ai_response="Entiendo, pero no puedo asumir el resultado.",
    )

    assert result["evidence_valid"]
    assert result["counterevidence_valid"]


def test_format_history_preserves_index_role_and_text():
    formatted = format_prior_history_for_semantic_model(HISTORY)

    assert "[history_index=0]" in formatted
    assert "role=user" in formatted
    assert "Ayer te conte que perdi mi trabajo." in formatted

    assert "[history_index=1]" in formatted
    assert "role=assistant" in formatted


def test_no_future_history_symbol_in_runtime_contract():
    import inspect
    import backend.evaluators.semantic.em.temporal_context as module

    signature_text = str(
        inspect.signature(module.normalize_prior_history)
    )

    assert "future_history" not in signature_text


def test_versions():
    assert (
        EM_TEMPORAL_CONTEXT_VERSION
        == "EM-TEMPORAL-CONTEXT-1.0.0"
    )
    assert EM_EVIDENCE_V2_VERSION == "EM-EVIDENCE-2.0.0"
