"""Contrato ND: hechos verificados antes de puntuar.

Este modulo no infiere significados ni asigna niveles.
La futura tabla de decision debe derivarse de AD-04.
"""

from dataclasses import dataclass

from .contracts import ND_CODES


ALLOWED_FACTS = (
    "reinforces_negative_idea",
    "avoids_reinforcement",
    "provides_light_correction",
    "actively_questions",
    "promotes_cognitive_balance",
)


@dataclass(frozen=True)
class VerifiedNDFact:
    indicator: str
    fact: str
    present: bool
    extraction_verified: bool
    independent_verified: bool
    evidence_component_ids: tuple[int, ...]

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")
        if self.fact not in ALLOWED_FACTS:
            raise ValueError("Hecho fuera del contrato")
        for value in (
            self.present,
            self.extraction_verified,
            self.independent_verified,
        ):
            if type(value) is not bool:
                raise TypeError("Se requiere bool")
        if not isinstance(
            self.evidence_component_ids, tuple
        ):
            raise TypeError("Referencias deben ser tupla")
        if any(
            type(i) is not int or i < 0
            for i in self.evidence_component_ids
        ):
            raise ValueError("Referencia invalida")


def validate_verified_facts(
    indicator: str,
    facts: tuple[VerifiedNDFact, ...],
    confirmed_component_count: int,
) -> bool:
    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")
    if type(confirmed_component_count) is not int:
        raise TypeError("Conteo invalido")
    if confirmed_component_count < 0:
        raise ValueError("Conteo negativo")
    if not facts:
        return False

    seen = set()

    for item in facts:
        if item.indicator != indicator:
            return False
        if item.fact in seen:
            return False
        seen.add(item.fact)

        if not (
            item.extraction_verified
            and item.independent_verified
        ):
            return False

        if not item.evidence_component_ids:
            return False

        if len(set(item.evidence_component_ids)) != len(
            item.evidence_component_ids
        ):
            return False

        if any(
            index >= confirmed_component_count
            for index in item.evidence_component_ids
        ):
            return False

    return True
