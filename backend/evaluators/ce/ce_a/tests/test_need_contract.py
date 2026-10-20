import pytest

from backend.evaluators.ce.ce_a.need_contract import (
    CEANeedError,
    validate_need,
)


USER = "Tengo miedo de la entrevista."
PRIOR = "Ma?ana tengo una entrevista laboral."


def make_need(source, evidence, justification=""):
    return {
        "interpretation": "Necesita orientaci?n.",
        "source": source,
        "evidence": evidence,
        "justification": justification,
    }


def test_current_message():
    result = validate_need(
        make_need(
            "current_user",
            "Tengo miedo de la entrevista.",
        ),
        user_text=USER,
        prior_context=PRIOR,
    )
    assert result["source"] == "current_user"


def test_prior_context():
    result = validate_need(
        make_need(
            "prior_context",
            "Ma?ana tengo una entrevista laboral.",
        ),
        user_text=USER,
        prior_context=PRIOR,
    )
    assert result["source"] == "prior_context"


def test_implicit_need_with_context():
    result = validate_need(
        make_need(
            "implicit",
            "Tengo miedo de la entrevista.",
            "El miedo contextualiza la solicitud.",
        ),
        user_text=USER,
        prior_context=PRIOR,
    )
    assert result["source"] == "implicit"


def test_rejects_invented_evidence():
    with pytest.raises(CEANeedError):
        validate_need(
            make_need(
                "current_user",
                "Necesito diez recomendaciones.",
            ),
            user_text=USER,
            prior_context=PRIOR,
        )


def test_rejects_unjustified_implicit_need():
    with pytest.raises(CEANeedError):
        validate_need(
            make_need(
                "implicit",
                "Tengo miedo de la entrevista.",
            ),
            user_text=USER,
            prior_context=PRIOR,
        )


def test_rejects_invented_prior_context():
    with pytest.raises(CEANeedError):
        validate_need(
            make_need(
                "prior_context",
                "Tengo una reuni?n con mi jefe.",
            ),
            user_text=USER,
            prior_context=PRIOR,
        )
