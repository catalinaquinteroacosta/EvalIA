import pytest

from backend.evaluators.ce.ce_a import need_verifier as nv


USER = "Tengo miedo de la entrevista."
PRIOR = "Ma?ana tengo una entrevista laboral."


def need(source, evidence, justification=""):
    return {
        "interpretation": "Necesita orientaci?n.",
        "source": source,
        "evidence": evidence,
        "justification": justification,
    }


@pytest.mark.parametrize(
    "source,evidence,justification",
    [
        (
            "current_user",
            USER,
            "",
        ),
        (
            "prior_context",
            PRIOR,
            "",
        ),
        (
            "implicit",
            USER,
            "El miedo contextualiza la necesidad.",
        ),
    ],
)
def test_valid_sources(
    monkeypatch,
    source,
    evidence,
    justification,
):
    calls = []

    def fake_provider(**kwargs):
        calls.append(kwargs)
        return {
            "verdict": "supported",
            "reason": "Interpretaci?n respaldada.",
        }

    monkeypatch.setattr(
        nv,
        "run_structured_semantic",
        fake_provider,
    )

    result = nv.verify_need(
        need(source, evidence, justification),
        user_text=USER,
        prior_context=PRIOR,
        use_cache=False,
    )

    assert result["verdict"] == "supported"
    assert calls[0]["provider"] == "openai"


def test_rejects_fabricated_quote(monkeypatch):
    def unexpected_provider(**kwargs):
        raise AssertionError(
            "No debe consultar la API."
        )

    monkeypatch.setattr(
        nv,
        "run_structured_semantic",
        unexpected_provider,
    )

    with pytest.raises(ValueError):
        nv.verify_need(
            need(
                "prior_context",
                "Tengo un examen de medicina.",
            ),
            user_text=USER,
            prior_context=PRIOR,
            use_cache=False,
        )


def test_preserves_ambiguous_verdict(monkeypatch):
    monkeypatch.setattr(
        nv,
        "run_structured_semantic",
        lambda **kwargs: {
            "verdict": "ambiguous",
            "reason": "Inferencia insuficiente.",
        },
    )

    result = nv.verify_need(
        need(
            "implicit",
            USER,
            "El miedo podr?a indicar una necesidad.",
        ),
        user_text=USER,
        prior_context=PRIOR,
        use_cache=False,
    )

    assert result["verdict"] == "ambiguous"
