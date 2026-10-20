import pytest
"""
Regresi?n de controlabilidad: experimento 72, turno 1.

Pruebas deterministas de los resultados sem?nticos observados.
No realizan consultas a OpenAI.
"""

from copy import deepcopy

from backend.evaluators.rules.af2_scorer import (
    resolve_af2_applicability,
)
from backend.evaluators.rules.af3_scorer import (
    resolve_af3_applicability,
)
from backend.evaluators.semantic.af_user_control_extractor import (
    control_item_is_confirmed,
)


def component(category, description, quote, status):
    return {
        "id": f"{category}_1",
        "description": description,
        "evidence": {
            "quote": quote,
            "source": "current_user",
        },
        "semantic_validation": {
            "status": status,
            "reason": "Referencia de regresi?n.",
        },
    }


def experiment72_control():
    return {
        "modifiable_components": [
            component(
                "modifiable",
                "Estudiar constantemente para preparar los ex?menes",
                "Aunque estudio constantemente",
                "supported",
            ),
            component(
                "modifiable",
                "Concentrarse en clase",
                "?ltimamente me resulta dif?cil concentrarme en clase",
                "not_supported",
            ),
        ],
        "unmodifiable_now": [],
        "uncertain_outcomes": [
            component(
                "uncertain",
                "Fracasar en los ex?menes",
                "siento que voy a fracasar en los ex?menes",
                "supported",
            ),
        ],
    }


def test_experiment72_controlability_reference():
    control = experiment72_control()

    assert [
        control_item_is_confirmed(item)
        for item in control["modifiable_components"]
    ] == [True, False]

    assert control_item_is_confirmed(
        control["uncertain_outcomes"][0]
    )

    assert control["unmodifiable_now"] == []


def test_experiment72_af2_applies():
    assert resolve_af2_applicability(
        experiment72_control()
    ) is True


def test_experiment72_af3_is_not_applicable():
    control = experiment72_control()

    # El resultado N/A no depende de inventar una
    # extracci?n emocional para este caso.
    assert resolve_af3_applicability(
        user_control=control,
        user_emotion={"distress": []},
    ) is False

    # Incluso con malestar confirmado, AF3 exige
    # un l?mite actualmente inmodificable.
    assert resolve_af3_applicability(
        user_control=control,
        user_emotion={
            "distress": [{
                "semantic_validation": {
                    "status": "supported"
                }
            }]
        },
    ) is False


def test_af3_rejects_unconfirmed_limit():
    control = experiment72_control()

    control["unmodifiable_now"] = [
        component(
            "unmodifiable",
            "L?mite no confirmado",
            "Cita de prueba",
            "ambiguous",
        )
    ]

    with pytest.raises(ValueError, match="aplicabilidad"):
        resolve_af3_applicability(
        user_control=control,
        user_emotion={
            "distress": [{
                "semantic_validation": {
                    "status": "supported"
                }
            }]
        },
        )


def test_af3_requires_confirmed_distress():
    control = experiment72_control()

    control["unmodifiable_now"] = [
        component(
            "unmodifiable",
            "Hecho irreversible confirmado",
            "Cita de prueba",
            "supported",
        )
    ]

    assert resolve_af3_applicability(
        user_control=control,
        user_emotion={"distress": []},
    ) is False
