
from unittest.mock import patch

import pytest

from backend.evaluators.semantic.em import verifier_v2
from backend.evaluators.semantic.em import pipeline_v2


@pytest.mark.parametrize(
    "code,component",
    [
        ("EM2", "understanding_is_generic_only"),
        ("EM12", "language_fit_is_partial"),
    ],
)
def test_negative_component_false_has_explicit_polarity(
    code, component
):
    prompt = verifier_v2.build_verification_prompt_v2(
        indicator_code=code,
        component_name=component,
        proposed_value="false",
        evidence=[],
        counterevidence=[],
        prior_history=[],
        user_message="Estoy preocupado por mis estudios.",
        ai_response=(
            "Entiendo que tu preocupaci?n por los "
            "ex?menes est? afectando tu descanso."
        ),
    )

    assert f"{component}" in prompt
    assert "VALOR PROPUESTO:" in prompt
    assert "false" in prompt
    assert "NO inviertas su significado" in prompt
    assert "Si concluyes semanticamente que el componente es false" in prompt
    assert "devuelve supported" in prompt


def test_double_unsupported_remains_blocked():
    component = {
        "value": "false",
        "evidence": [],
        "counterevidence": [],
        "reason": "Prueba adversarial",
    }

    calls = []

    def fake_verify_cached(**kwargs):
        calls.append(kwargs["pass_name"])
        return {
            "status": "unsupported",
            "reason": "Contradiccion simulada",
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "verification_error": None,
        }

    with patch.object(
        pipeline_v2,
        "_verify_cached",
        side_effect=fake_verify_cached,
    ):
        resolved, primary, reconciliation = (
            pipeline_v2._verify_component_with_reconciliation(
                indicator_code="EM2",
                component_name="understanding_is_generic_only",
                components={
                    "understanding_is_generic_only": component
                },
                prior_history=[],
                user_message="Me preocupan los ex?menes.",
                ai_response=(
                    "Tu preocupaci?n afecta el sue?o."
                ),
                provider="test",
                model="test",
            )
        )

    assert resolved is None
    assert primary["status"] == "unsupported"
    assert reconciliation["status"] == "unsupported"
    assert calls == ["primary", "reconciliation"]
