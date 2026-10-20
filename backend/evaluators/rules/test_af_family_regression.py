"""
EvalIA ? Regresi?n familiar AF1?AF8.

Objetivo:
- verificar invariantes metodol?gicos transversales;
- comprobar GENERAL vs CONDICIONAL;
- impedir que ambiguous cuente como supported;
- impedir mezcla de microcomponentes entre entradas;
- verificar guardrails materiales;
- mantener N/A separado de 0.

Este archivo prueba scorers deterministas.
No llama Ollama/Qwen.
"""

from backend.evaluators.rules.af1_scorer import score_af1
from backend.evaluators.rules.af2_scorer import score_af2
from backend.evaluators.rules.af3_scorer import score_af3
from backend.evaluators.rules.af4_scorer import score_af4
from backend.evaluators.rules.af5_scorer import score_af5
from backend.evaluators.rules.af6_scorer import score_af6
from backend.evaluators.rules.af7_scorer import score_af7
from backend.evaluators.rules.af8_scorer import score_af8
from backend.evaluators.rules.af7_applicability import (
    AF7ApplicabilityDecision,
)


def v(status="supported"):
    return {
        "status": status,
        "reason": "family regression",
    }


# ============================================================
# AF1 ? GENERAL
# ============================================================

def test_family_af1_general_zero_without_components():
    result = score_af1({
        "modifiable": [],
        "unmodifiable": [],
        "control_guarantees": [],
    })

    assert result.score == 0


def test_family_af1_ambiguous_does_not_count():
    result = score_af1({
        "modifiable": [
            {
                "semantic_validation": v("ambiguous"),
                "orientations": [],
            }
        ],
        "unmodifiable": [],
        "control_guarantees": [],
    })

    assert result.score == 0


# ============================================================
# AF2 ? CONDICIONAL
# ============================================================

def test_family_af2_na_is_not_zero():
    result = score_af2(
        applicable=False,
        semantic_result={
            "stressor_actions": [],
            "result_guarantees": [],
        },
    )

    assert result.score is None
    assert result.applicable is False


def test_family_af2_no_cross_item_mixing():
    result = score_af2(
        applicable=True,
        semantic_result={
            "stressor_actions": [
                {
                    "target_relation": v(),
                    "action_description": "",
                    "feasibility": "not_supported",
                    "initiation_relation": v("not_supported"),
                },
                {
                    "target_relation": v("not_supported"),
                    "action_description": "Enviar el correo",
                    "feasibility": "supported",
                    "initiation_relation": v(),
                },
            ],
            "result_guarantees": [],
        },
    )

    assert result.score < 3


# ============================================================
# AF3 ? CONDICIONAL
# ============================================================

def test_family_af3_na_is_not_zero():
    result = score_af3(
        applicable=False,
        semantic_result={
            "regulation_strategies": [],
            "problematic_claims": [],
        },
        user_control={
            "unmodifiable_now": [],
        },
        user_emotion={
            "distress": [],
        },
    )

    assert result.score is None
    assert result.applicable is False


def test_family_af3_no_cross_strategy_mixing():
    result = score_af3(
        applicable=True,
        semantic_result={
            "regulation_strategies": [
                {
                    "semantic_validation": {
                        "limit": v(),
                        "regulation": v("not_supported"),
                        "use_context": v("not_supported"),
                    }
                },
                {
                    "semantic_validation": {
                        "limit": v("not_supported"),
                        "regulation": v(),
                        "use_context": v(),
                    }
                },
            ],
            "problematic_claims": [],
        },
        user_control={
            "unmodifiable_now": [],
        },
        user_emotion={
            "distress": [],
        },
    )

    assert result.score < 3


# ============================================================
# AF4 ? CONDICIONAL
# ============================================================

def test_family_af4_na_is_not_zero():
    result = score_af4(
        applicable=False,
        semantic_result={
            "approaches": [],
            "harmful_avoidance_recommendations": [],
        },
        user_avoidance={
            "avoidance_costs": [],
        },
    )

    assert result.score is None
    assert result.applicable is False


def test_family_af4_no_cross_approach_mixing():
    result = score_af4(
        applicable=True,
        semantic_result={
            "approaches": [
                {
                    "semantic_validation": {
                        "E": v(),
                        "P": v("not_supported"),
                        "G": v("not_supported"),
                    }
                },
                {
                    "semantic_validation": {
                        "E": v("not_supported"),
                        "P": v(),
                        "G": v(),
                    }
                },
            ],
            "harmful_avoidance_recommendations": [],
        },
        user_avoidance={
            "avoidance_costs": [],
        },
    )

    assert result.score < 3


# ============================================================
# AF5 ? GENERAL
# ============================================================

def test_family_af5_general_never_na():
    result = score_af5(
        semantic_result={
            "acceptance": [],
            "resignation_or_helplessness": [],
        },
    )

    assert result.score == 0
    assert result.applicable is True


def test_family_af5_no_cross_item_mixing():
    result = score_af5(
        semantic_result={
            "acceptance": [
                {
                    "semantic_validation": {
                        "L": v(),
                        "A": v(),
                        "C": v("not_supported"),
                    }
                },
                {
                    "semantic_validation": {
                        "L": v("not_supported"),
                        "A": v("not_supported"),
                        "C": v(),
                    }
                },
            ],
            "resignation_or_helplessness": [],
        },
    )

    assert result.score < 3


# ============================================================
# AF6 ? GENERAL
# ============================================================

def test_family_af6_general_never_na():
    result = score_af6({
        "prior_resources": [],
        "confirmed_user_resources": [],
    })

    assert result.score == 0
    assert result.applicable is True


def test_family_af6_no_cross_resource_mixing():
    result = score_af6({
        "prior_resources": [
            {
                "semantic_validation": {
                    "H": v(),
                    "V": v(),
                    "R": v("not_supported"),
                }
            },
            {
                "semantic_validation": {
                    "H": v("not_supported"),
                    "V": v("not_supported"),
                    "R": v(),
                }
            },
        ],
        "confirmed_user_resources": [],
    })

    assert result.score < 3


# ============================================================
# AF7 ? CONDICIONAL
# ============================================================

def af7_applicable(value):
    return AF7ApplicabilityDecision(
        applicable=value,
        has_activation=value,
        has_action_interference=value,
        has_activation_action_relation=value,
        activation_ids=[],
        interference_ids=[],
        confirmed_relation_pairs=[],
        evaluated_relations=[],
        reason="family regression",
    )


def test_family_af7_na_is_not_zero():
    result = score_af7(
        applicability=af7_applicable(False),
        ai_result={
            "regulation_for_action": [],
            "problematic_claims": [],
        },
    )

    assert result.score is None
    assert result.applicable is False


def test_family_af7_no_cross_intervention_mixing():
    result = score_af7(
        applicability=af7_applicable(True),
        ai_result={
            "regulation_for_action": [
                {
                    "id": "a",
                    "procedure": "Respira lentamente.",
                    "semantic_validation": {
                        "B": v(),
                        "T": v(),
                        "M": v("not_supported"),
                        "SAFE": v(),
                        "PROPORTIONAL": v(),
                    },
                },
                {
                    "id": "b",
                    "procedure": "",
                    "semantic_validation": {
                        "B": v("not_supported"),
                        "T": v("not_supported"),
                        "M": v(),
                        "SAFE": v(),
                        "PROPORTIONAL": v(),
                    },
                },
            ],
            "problematic_claims": [],
        },
    )

    assert result.score < 3


# ============================================================
# AF8 ? GENERAL
# ============================================================

def test_family_af8_general_never_na():
    result = score_af8(
        ai_result={
            "agency": [],
            "problematic_claims": [],
        },
    )

    assert result.score == 0
    assert result.applicable is True


def test_family_af8_no_cross_item_mixing():
    result = score_af8(
        ai_result={
            "agency": [
                {
                    "id": "a",
                    "semantic_validation": {
                        "C": v(),
                        "L": v(),
                        "N": v("not_supported"),
                        "AGENCY_SIGNAL": v(),
                    },
                },
                {
                    "id": "b",
                    "semantic_validation": {
                        "C": v("not_supported"),
                        "L": v("not_supported"),
                        "N": v(),
                        "AGENCY_SIGNAL": v(),
                    },
                },
            ],
            "problematic_claims": [],
        },
    )

    assert result.score < 3
