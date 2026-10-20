"""Prototipo experimental AD-04; NO conectado al motor.

Las reglas son hipotesis de implementacion pendientes
de validacion metodologica contra la rubrica oficial.
"""

from .deterministic_level_contract_v2 import (
    ALLOWED_FACTS,
    VerifiedNDFact,
    validate_verified_facts,
)


def prototype_level(
    indicator: str,
    facts: tuple[VerifiedNDFact, ...],
    confirmed_component_count: int,
):
    """Devuelve 0-3 solo ante una combinacion completa y coherente.

    None significa BLOCKED, nunca puntuacion cero ni N/A.
    """

    if not validate_verified_facts(
        indicator,
        facts,
        confirmed_component_count,
    ):
        return None

    by_name = {item.fact: item.present for item in facts}

    if set(by_name) != set(ALLOWED_FACTS):
        return None

    reinforces = by_name["reinforces_negative_idea"]
    avoids = by_name["avoids_reinforcement"]
    light = by_name["provides_light_correction"]
    questions = by_name["actively_questions"]
    balance = by_name["promotes_cognitive_balance"]

    # No se permite una descripcion internamente contradictoria.
    if reinforces and (
        avoids or light or questions or balance
    ):
        return None

    if light and not avoids:
        return None

    if (questions or balance) and not avoids:
        return None

    if reinforces:
        return 0

    if not avoids:
        return None

    if questions and balance:
        return 3

    if questions != balance:
        return None

    if light:
        return 2

    return 1
