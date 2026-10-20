"""
Dimensiones semanticas auxiliares para puntuacion EM.

NO contienen puntuaciones.
NO interpretan lenguaje natural.
NO sustituyen los componentes propios del indicador.

Su unica funcion es definir propiedades semanticas observables
necesarias para distinguir fielmente las fronteras ordinales
de la rubrica sin usar conteos arbitrarios.
"""

from __future__ import annotations


EM_SCORING_DIMENSIONS_VERSION = "EM-SCORING-DIMENSIONS-1.0.0"


QUALITY_STATES = (
    "absent",
    "generic",
    "specific",
    "contextualized",
    "unknown",
)

LIMITATION_STATES = (
    "none",
    "secondary",
    "material",
    "unknown",
)


SCORING_DIMENSIONS = {

    "EM1": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM2": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM3": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM4": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM5": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM6": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM7": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM8": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM9": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM10": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM11": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM12": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },

    "EM13": {
        "execution_quality": QUALITY_STATES,
        "limitation_materiality": LIMITATION_STATES,
    },
}


DIMENSION_MEANINGS = {

    "execution_quality": {
        "absent":
            "No existe una ejecucion reconocible del constructo exigido.",

        "generic":
            "Existe una ejecucion reconocible, pero permanece generica "
            "o insuficientemente desarrollada para realizar plenamente "
            "la funcion del indicador.",

        "specific":
            "La funcion central del indicador esta realizada de forma "
            "concreta y sustentada, aunque puede existir una limitacion "
            "secundaria.",

        "contextualized":
            "La funcion del indicador esta realizada de forma clara, "
            "especifica y suficientemente adaptada al contexto disponible, "
            "sin exigir formulaciones literales ni contenido adicional "
            "fuera del constructo.",

        "unknown":
            "La evidencia disponible no permite resolver responsablemente "
            "la calidad de ejecucion.",
    },

    "limitation_materiality": {
        "none":
            "No existe defecto observable relevante dentro del constructo.",

        "secondary":
            "Existe un defecto identificable, pero la funcion central del "
            "indicador permanece realizada.",

        "material":
            "Existe una contradiccion, omision o defecto que compromete "
            "sustancialmente la funcion propia del indicador.",

        "unknown":
            "No puede determinarse responsablemente la materialidad.",
    },
}


def validate_scoring_dimensions_registry() -> None:
    expected = {f"EM{i}" for i in range(1, 14)}

    if set(SCORING_DIMENSIONS) != expected:
        missing = expected - set(SCORING_DIMENSIONS)
        extra = set(SCORING_DIMENSIONS) - expected

        raise ValueError(
            f"Registro incompleto. missing={missing}, extra={extra}"
        )

    for indicator, dimensions in SCORING_DIMENSIONS.items():

        if set(dimensions) != {
            "execution_quality",
            "limitation_materiality",
        }:
            raise ValueError(
                f"{indicator}: dimensiones inesperadas"
            )

        if dimensions["execution_quality"] != QUALITY_STATES:
            raise ValueError(
                f"{indicator}: QUALITY_STATES alterado"
            )

        if dimensions["limitation_materiality"] != LIMITATION_STATES:
            raise ValueError(
                f"{indicator}: LIMITATION_STATES alterado"
            )


validate_scoring_dimensions_registry()
