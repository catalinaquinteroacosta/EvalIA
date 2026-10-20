import pytest

from backend.evaluators.gd.gd_schemas import (
    GDContext,
    GDResult,
    Evidence,
    HistoryMessage,
    validate_applicability_decision,
    validate_evidence,
    verify_exact_quote,
)


def context():
    return GDContext(
        current_user="Me cuesta decidir.",
        current_response="Puedes comparar tus alternativas.",
        prior_history=(
            HistoryMessage(role="user", text="Tengo dos opciones."),
            HistoryMessage(role="assistant", text="¿Qué prefieres?"),
        ),
    )


@pytest.mark.parametrize(
    "source,quote,index",
    [
        ("CURRENT_USER", "Me cuesta decidir.", None),
        ("CURRENT_RESPONSE", "comparar tus alternativas", None),
        ("PRIOR_HISTORY", "Tengo dos opciones.", 0),
        ("PRIOR_HISTORY", "¿Qué prefieres?", 1),
    ],
)
def test_literal_evidence(source, quote, index):
    assert verify_exact_quote(Evidence(quote, source, index), context())


@pytest.mark.parametrize(
    "source,quote,index",
    [
        ("CURRENT_USER", "Me cuesta decidir.", 0),
        ("CURRENT_RESPONSE", "comparar tus alternativas", 0),
        ("PRIOR_HISTORY", "Tengo dos opciones.", 1),
        ("PRIOR_HISTORY", "Tengo dos opciones.", -1),
        ("PRIOR_HISTORY", "Tengo dos opciones.", 2),
        ("CURRENT_RESPONSE", "texto inventado", None),
    ],
)
def test_reject_invalid_evidence(source, quote, index):
    item = Evidence(quote, source, index)
    assert not verify_exact_quote(item, context())
    with pytest.raises(ValueError):
        validate_evidence((item,), context())


@pytest.mark.parametrize("code", ["GD1", "GD2", "GD3", "GD4", "GD6", "GD8"])
def test_general_not_arbitrarily_na(code):
    with pytest.raises(ValueError):
        validate_applicability_decision(code, False)


@pytest.mark.parametrize("code", ["GD5", "GD7"])
def test_conditional_requires_verified_condition(code):
    with pytest.raises(ValueError):
        validate_applicability_decision(code, False)


@pytest.mark.parametrize("code", ["GD5", "GD7"])
def test_conditional_allows_na_when_condition_absent(code):
    validate_applicability_decision(
        code, False, condition_present=False
    )


def test_conditional_rejects_inconsistent_decision():
    with pytest.raises(ValueError):
        validate_applicability_decision(
            "GD5", False, condition_present=True
        )


def test_scored_result():
    result = GDResult(
        code="GD1", status="SCORED", score=3, reason="Prueba"
    )
    assert result.score == 3


@pytest.mark.parametrize("score", [-1, 4, None, True])
def test_invalid_score(score):
    with pytest.raises(ValueError):
        GDResult(
            code="GD1", status="SCORED", score=score, reason="Prueba"
        )


def test_blocked_cannot_have_score():
    with pytest.raises(ValueError):
        GDResult(
            code="GD2", status="BLOCKED", score=0, reason="Conflicto"
        )
