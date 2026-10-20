"""Casos de aceptacion semantica para PA7.

La finalidad debe estar comunicada en la respuesta.
No se exige una expresion gramatical especifica.
"""

import pytest


CASES = [
    (
        "Divide tus tareas en pasos pequenos.",
        False,
    ),
    (
        "Divide tus tareas en pasos pequenos. "
        "Asi podras comenzar sin resolver todo de una vez.",
        True,
    ),
    (
        "Puedes hacer una lista de tus pendientes "
        "para identificar cual atender primero.",
        True,
    ),
    (
        "Haz una lista de tus pendientes.",
        False,
    ),
]


@pytest.mark.parametrize(
    "response, purpose_explained", CASES
)
def test_pa7_acceptance_cases(
    response, purpose_explained
):
    assert response.strip()
    assert isinstance(purpose_explained, bool)


def test_pa7_requires_explanation_not_keywords():
    assert CASES[1][1] is True
    assert "para " not in CASES[1][0].lower()
    assert CASES[0][1] is False
