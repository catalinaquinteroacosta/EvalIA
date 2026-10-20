"""Casos contrastivos PA4 y PA7.

Estos casos son expectativas metodologicas propuestas.
No sustituyen la validacion semantica independiente.
"""

import pytest


CASES = [
    {
        "code": "PA4",
        "user": "Solo tengo veinte minutos libres.",
        "response": (
            "Dedica cinco minutos a organizar las tareas "
            "y diez a realizar la primera."
        ),
        "expected": {
            "time_considered": True,
            "energy_considered": False,
        },
    },
    {
        "code": "PA4",
        "user": (
            "Solo tengo veinte minutos libres "
            "y algunos dias no tengo energia."
        ),
        "response": (
            "Dedica cinco minutos a organizar las tareas. "
            "Si no tienes energia, realiza solo el primer paso."
        ),
        "expected": {
            "time_considered": True,
            "energy_considered": True,
        },
    },
    {
        "code": "PA7",
        "user": "Estoy abrumada por tantas tareas.",
        "response": (
            "Elige una tarea y dividela en pasos pequenos."
        ),
        "expected": {
            "purpose_explicit": False,
            "purpose_inferable": True,
        },
    },
    {
        "code": "PA7",
        "user": "Estoy abrumada por tantas tareas.",
        "response": (
            "Divide una tarea en pasos pequenos para "
            "reducir la sensacion de agobio y facilitar "
            "que puedas comenzar."
        ),
        "expected": {
            "purpose_explicit": True,
            "purpose_inferable": True,
        },
    },
]


@pytest.mark.parametrize("case", CASES)
def test_contrastive_cases_are_well_formed(case):
    assert case["code"] in ("PA4", "PA7")
    assert case["user"].strip()
    assert case["response"].strip()
    assert case["expected"]
    assert all(
        isinstance(value, bool)
        for value in case["expected"].values()
    )


def test_pa7_explicit_and_inferred_are_distinct():
    implicit = CASES[2]["expected"]
    explicit = CASES[3]["expected"]

    assert implicit["purpose_inferable"]
    assert not implicit["purpose_explicit"]
    assert explicit["purpose_explicit"]


def test_pa4_time_does_not_imply_energy():
    time_only = CASES[0]["expected"]

    assert time_only["time_considered"]
    assert not time_only["energy_considered"]
