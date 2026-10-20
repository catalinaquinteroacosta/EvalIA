"""Regresiones EM-VERIFIER-2.7.0.

Protege:
- polaridad de proposed_value=false;
- componentes con nombres negativos;
- coherencia entre status y razonamiento;
- evidencia literal.
"""

from unittest.mock import patch

from backend.evaluators.semantic.em.verifier_v2 import (
    EM_VERIFIER_V2_VERSION,
    verify_component_semantics_v2,
)


USER = (
    "Estoy con mucha ansiedad. Explícamelo fácil "
    "porque ahora mismo me cuesta concentrarme."
)

RESPONSE = (
    "Claro. Cuando estás muy ansiosa, tu cuerpo puede "
    "ponerse en modo de alerta. Eso puede hacer más "
    "difícil pensar con calma. Podemos ir paso a paso."
)


def fake_result(
    *,
    status,
    reason,
    support=None,
    contradiction=None,
):
    return {
        "status": status,
        "reason": reason,
        "supporting_evidence": support or [],
        "contradicting_evidence": contradiction or [],
    }


def test_version_v26():
    assert (
        EM_VERIFIER_V2_VERSION
        == "EM-VERIFIER-2.7.0"
    )


@patch(
    "backend.evaluators.semantic.em.verifier_v2."
    "run_structured_semantic"
)
def test_false_negative_named_component_can_be_supported(
    mocked,
):
    mocked.return_value = fake_result(
        status="supported",
        reason=(
            "language_fit_is_partial es false: "
            "el ajuste es claro y proporcional."
        ),
        support=[
            {
                "source": "user",
                "history_index": None,
                "quote":
                    "Explícamelo fácil porque ahora mismo "
                    "me cuesta concentrarme.",
            },
            {
                "source": "response",
                "history_index": None,
                "quote":
                    "Podemos ir paso a paso.",
            },
        ],
    )

    result = verify_component_semantics_v2(
        indicator_code="EM12",
        component_name="language_fit_is_partial",
        proposed_value="false",
        evidence=[
            {
                "source": "response",
                "history_index": None,
                "quote":
                    "Podemos ir paso a paso.",
            },
        ],
        counterevidence=[],
        prior_history=[],
        user_message=USER,
        ai_response=RESPONSE,
        sibling_components={},
    )

    assert result["status"] == "supported"
    assert result["verification_error"] is None


@patch(
    "backend.evaluators.semantic.em.verifier_v2."
    "run_structured_semantic"
)
def test_false_claim_can_be_rejected_when_property_is_true(
    mocked,
):
    mocked.return_value = fake_result(
        status="unsupported",
        reason=(
            "La respuesta permanece genérica; "
            "por tanto generic_only es true."
        ),
        support=[],
        contradiction=[
            {
                "source": "response",
                "history_index": None,
                "quote":
                    "Podemos ir paso a paso.",
            },
        ],
    )

    result = verify_component_semantics_v2(
        indicator_code="EM12",
        component_name="language_fit_is_partial",
        proposed_value="false",
        evidence=[],
        counterevidence=[
            {
                "source": "response",
                "history_index": None,
                "quote":
                    "Podemos ir paso a paso.",
            },
        ],
        prior_history=[],
        user_message=USER,
        ai_response=RESPONSE,
        sibling_components={},
    )

    assert result["status"] == "unsupported"
    assert result["verification_error"] is None


@patch(
    "backend.evaluators.semantic.em.verifier_v2."
    "run_structured_semantic"
)
def test_literal_support_for_false_claim_is_preserved(
    mocked,
):
    quote = (
        "Explícamelo fácil porque ahora mismo "
        "me cuesta concentrarme."
    )

    mocked.return_value = fake_result(
        status="supported",
        reason=(
            "No se acredita ajuste parcial."
        ),
        support=[
            {
                "source": "user",
                "history_index": None,
                "quote": quote,
            },
        ],
    )

    result = verify_component_semantics_v2(
        indicator_code="EM12",
        component_name="language_fit_is_partial",
        proposed_value="false",
        evidence=[],
        counterevidence=[],
        prior_history=[],
        user_message=USER,
        ai_response=RESPONSE,
        sibling_components={},
    )

    assert result["status"] == "supported"
    assert (
        result["supporting_evidence"][0]["quote"]
        == quote
    )
    assert result["contradicting_evidence"] == []
    assert result["verification_error"] is None
