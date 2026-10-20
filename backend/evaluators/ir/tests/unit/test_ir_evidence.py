import pytest

from backend.evaluators.ir.core.contracts import (
    Context, Evidence, Message
)
from backend.evaluators.ir.core.evidence import (
    verify_exact_evidence
)


@pytest.fixture
def ctx():
    return Context(
        user="Creo que siempre fracaso.",
        response="Pensar eso puede hacerte sentir triste.",
        prior_history=(
            Message("user", "Me preocupa el examen."),
            Message("assistant", "Entiendo tu preocupación."),
            Message("user", "Me preocupa el examen."),
        )
    )


def test_current_user(ctx):
    assert verify_exact_evidence(
        ctx, Evidence("user", "siempre fracaso")
    )


def test_current_response(ctx):
    assert verify_exact_evidence(
        ctx, Evidence("response", "sentir triste")
    )


def test_valid_history(ctx):
    assert verify_exact_evidence(
        ctx, Evidence("history", "el examen", 0)
    )


def test_wrong_history_index(ctx):
    assert not verify_exact_evidence(
        ctx, Evidence("history", "Entiendo", 0)
    )


def test_repeated_quote_index(ctx):
    assert verify_exact_evidence(
        ctx, Evidence("history", "Me preocupa", 2)
    )


def test_history_not_current_user(ctx):
    assert not verify_exact_evidence(
        ctx, Evidence("user", "Me preocupa el examen.")
    )


def test_assistant_history_not_response(ctx):
    assert not verify_exact_evidence(
        ctx, Evidence("response", "Entiendo tu preocupación.")
    )


def test_without_history():
    c = Context(user="Hola", response="Hola")
    assert not verify_exact_evidence(
        c, Evidence("history", "Hola", 0)
    )


def test_no_future_history_contract():
    assert "future_history" not in Context.__dataclass_fields__


def test_exact_accents(ctx):
    assert not verify_exact_evidence(
        ctx, Evidence("user", "Creo que siempre fracasó.")
    )


def test_exact_punctuation(ctx):
    assert not verify_exact_evidence(
        ctx, Evidence("user", "Creo que siempre fracaso!")
    )


def test_no_cross_source_join(ctx):
    assert not verify_exact_evidence(
        ctx, Evidence(
            "user",
            "siempre fracaso. Pensar eso"
        )
    )


def test_history_requires_index():
    with pytest.raises(ValueError):
        Evidence("history", "texto")


def test_current_forbids_index():
    with pytest.raises(ValueError):
        Evidence("user", "texto", 0)


def test_invalid_role():
    with pytest.raises(ValueError):
        Message("system", "texto")


def test_invalid_history_container():
    with pytest.raises(TypeError):
        Context("Hola", "Hola", [])


def test_quote_does_not_prove_semantics(ctx):
    """Literalidad no equivale a soporte semántico."""
    ev = Evidence("user", "siempre fracaso")
    assert verify_exact_evidence(ctx, ev)
    # La afirmación semántica todavía debe verificarse
    # mediante una operación independiente.