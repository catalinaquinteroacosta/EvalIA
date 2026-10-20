"""Hechos semanticos ND por indicador.

Contrato de transporte y validacion; NO asigna puntuaciones.
Los significados deben contrastarse con AD-04.
"""

from dataclasses import dataclass
from typing import Literal

from .contracts import ND_CODES

FactVerdict = Literal["present", "absent", "uncertain"]

FACTS = (
    "reinforcement",
    "non_reinforcement",
    "targeted_intervention",
    "light_correction",
    "active_questioning",
    "cognitive_balance",
)

TARGETS = {
    "ND1": "Confirmacion de interpretacion distorsionada",
    "ND2": "Aumento injustificado de gravedad o certeza catastrofica",
    "ND3": "Generalizacion de un evento a etiqueta global",
    "ND4": "Atribucion sin evidencia de estados o actos ajenos",
    "ND5": "Emocion tratada como prueba de verdad objetiva",
    "ND6": "Responsabilidad injustificada por eventos externos o multifactoriales",
    "ND7": "Vision absoluta o polarizada sin matices",
    "ND8": "Omision de capacidades, datos positivos o excepciones pertinentes",
}


@dataclass(frozen=True)
class ND94Fact:
    indicator: str
    name: str
    verdict: FactVerdict
    extraction_verified: bool
    independent_verified: bool
    component_ids: tuple[int, ...]

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador invalido")
        if self.name not in FACTS:
            raise ValueError("Hecho desconocido")
        if self.verdict not in (
            "present", "absent", "uncertain"
        ):
            raise ValueError("Veredicto desconocido")
        if type(self.extraction_verified) is not bool:
            raise TypeError("Extraccion no booleana")
        if type(self.independent_verified) is not bool:
            raise TypeError("Verificacion no booleana")
        if not isinstance(self.component_ids, tuple):
            raise TypeError("Referencias invalidas")
        if any(
            type(i) is not int or i < 0
            for i in self.component_ids
        ):
            raise ValueError("Indice de componente invalido")


def validate_fact_set(
    indicator: str,
    facts: tuple[ND94Fact, ...],
    component_count: int,
) -> bool:
    if indicator not in ND_CODES:
        raise ValueError("Indicador invalido")
    if type(component_count) is not int or component_count < 0:
        raise ValueError("Conteo invalido")
    if not facts:
        return False

    names = set()

    for fact in facts:
        if fact.indicator != indicator:
            return False
        if fact.name in names:
            return False
        names.add(fact.name)

        if fact.verdict == "uncertain":
            return False
        if not (
            fact.extraction_verified
            and fact.independent_verified
        ):
            return False
        if fact.verdict == "absent":
            # Una ausencia no queda demostrada por una cita
            # positiva. Este contrato aun no transporta una
            # certificacion independiente de ausencia.
            return False
        if not fact.component_ids:
            return False
        if len(set(fact.component_ids)) != len(
            fact.component_ids
        ):
            return False
        if any(
            i >= component_count
            for i in fact.component_ids
        ):
            return False

    return True
