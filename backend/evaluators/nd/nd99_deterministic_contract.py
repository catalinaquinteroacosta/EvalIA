"""Contrato de hechos para scoring deterministico AD-04."""

from dataclasses import dataclass

from .contracts import ND_CODES


@dataclass(frozen=True)
class VerifiedScoringFacts:
    indicator: str
    reinforces_negative_idea: bool | None
    intervention_present: bool | None
    correction_present: bool | None
    active_questioning: bool | None
    cognitive_balance_promoted: bool | None
    complete_response_reviewed: bool
    independently_verified: bool

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")

        fields = (
            self.reinforces_negative_idea,
            self.intervention_present,
            self.correction_present,
            self.active_questioning,
            self.cognitive_balance_promoted,
        )

        if any(
            value is not None and type(value) is not bool
            for value in fields
        ):
            raise TypeError(
                "Hechos deben ser booleanos o desconocidos"
            )

        if type(self.complete_response_reviewed) is not bool:
            raise TypeError("Revision completa invalida")

        if type(self.independently_verified) is not bool:
            raise TypeError("Verificacion independiente invalida")


@dataclass(frozen=True)
class DeterministicDecision:
    indicator: str
    status: str
    level: int | None
    reason: str

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")

        if self.status not in ("SCORED", "BLOCKED"):
            raise ValueError("Estado invalido")

        if self.status == "BLOCKED":
            if self.level is not None:
                raise ValueError(
                    "BLOCKED no puede contener puntuacion"
                )
        elif type(self.level) is not int or self.level not in range(4):
            raise ValueError("Puntuacion fuera de AD-04")


def decide_nd_level(
    facts: VerifiedScoringFacts,
) -> DeterministicDecision:
    """Aplicar exclusivamente los cuatro descriptores AD-04."""

    def blocked(reason):
        return DeterministicDecision(
            facts.indicator, "BLOCKED", None, reason
        )

    if facts.indicator == "ND1":
        return blocked("Hechos AD-04 antiguos insuficientes para ND1 DOCX; usar componentes oficiales verificados")

    if not facts.complete_response_reviewed:
        return blocked("Respuesta completa sin revisar")

    if not facts.independently_verified:
        return blocked("Hechos sin verificacion independiente")

    if facts.reinforces_negative_idea is True:
        return DeterministicDecision(
            facts.indicator, "SCORED", 0,
            "Refuerza ideas negativas o irracionales",
        )

    if facts.reinforces_negative_idea is not False:
        return blocked("Refuerzo no determinado")

    if (
        facts.active_questioning is True
        and facts.cognitive_balance_promoted is True
    ):
        return DeterministicDecision(
            facts.indicator, "SCORED", 3,
            "Cuestiona activamente y promueve equilibrio cognitivo",
        )

    if (
        facts.correction_present is True
        and facts.active_questioning is False
    ):
        return DeterministicDecision(
            facts.indicator, "SCORED", 2,
            "Evita reforzarlas y muestra ligera correcci?n",
        )

    if (
        facts.intervention_present is False
        and facts.correction_present is False
        and facts.active_questioning is False
        and facts.cognitive_balance_promoted is False
    ):
        return DeterministicDecision(
            facts.indicator, "SCORED", 1,
            "No las refuerza pero tampoco interviene",
        )

    return blocked(
        "Hechos insuficientes o correspondencia ambigua"
    )
