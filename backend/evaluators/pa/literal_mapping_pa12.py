
"""Correspondencia literal PA1-PA8 con preguntas AD-05.

Este componente NO asigna niveles ordinales.
"""

import unicodedata

from .official_scoring_pa import official_contract


def normalize(value):
    value = unicodedata.normalize(
        "NFKD", str(value).casefold()
    )
    normalized = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )
    return " ".join(normalized.split())


# Nombres correspondientes a propiedades ya extraidas.
# La pregunta oficial sigue siendo la autoridad.
PROPERTY_GROUPS = {
    "PA1": (
        ("propuesta de accion especifica",),
        ("accion observable",),
        ("relacion con el problema",),
    ),
    "PA2": (
        ("organizacion en pasos pequenos",),
        ("accion realizable",),
    ),
    "PA3": (
        ("explicacion de que hacer",),
        ("explicacion de como hacerlo",),
    ),
    "PA4": (
        ("consideracion de capacidades",),
        ("consideracion de recursos",),
        ("consideracion del tiempo",),
        ("consideracion de restricciones",),
    ),
    "PA5": (
        ("dependencia de comportamientos realizables por la persona",),
    ),
    "PA6": (
        ("ofrece alternativas", "permite adaptar la accion"),
    ),
    "PA7": (
        ("finalidad explicada",),
        ("coherencia con la necesidad",),
    ),
    "PA8": (
        ("forma de revisar resultados", "forma de ajustar el plan"),
    ),
}


def evaluate_mapping(code, properties, *, blocked=False):
    rubric = official_contract()
    indicators = {
        item["code"]: item
        for item in rubric["indicators"]
    }

    if code not in indicators:
        raise ValueError(code)

    if blocked:
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Discrepancia semantica sin resolver",
        }

    if not isinstance(properties, list):
        raise TypeError("properties debe ser una lista")

    observed = {}

    for prop in properties:
        if not isinstance(prop, dict):
            return {
                "code": code,
                "status": "BLOCKED",
                "score": None,
                "reason": "Propiedad mal formada",
            }

        name = normalize(prop.get("name", ""))
        value = prop.get("value")

        if value not in ("present", "absent"):
            return {
                "code": code,
                "status": "BLOCKED",
                "score": None,
                "reason": "Propiedad no resuelta",
            }

        if name in observed and observed[name] != value:
            return {
                "code": code,
                "status": "BLOCKED",
                "score": None,
                "reason": "Propiedades contradictorias",
            }

        observed[name] = value

    groups = PROPERTY_GROUPS[code]
    group_results = []

    for alternatives in groups:
        values = [
            observed.get(name)
            for name in alternatives
        ]

        if "present" in values:
            group_results.append(True)
        elif all(v == "absent" for v in values):
            group_results.append(False)
        else:
            group_results.append(None)

    if any(v is None for v in group_results):
        status = "BLOCKED"
    elif all(group_results):
        status = "QUESTION_SUPPORTED"
    else:
        status = "QUESTION_NOT_FULLY_SUPPORTED"

    return {
        "code": code,
        "status": status,
        "score": None,
        "official_question": indicators[code]["question"],
        "group_results": group_results,
    }
