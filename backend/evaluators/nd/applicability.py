"""Control de aplicabilidad de ND, sin asignacion de puntajes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import ND_CODES, ND_CONDITIONAL

Applicability = Literal["APPLICABLE", "NA", "BLOCKED"]
SemanticVerdict = Literal[
    "present", "absent", "uncertain"
]


@dataclass(frozen=True)
class VerifiedApplicability:
    """Resultado de una verificacion semantica independiente.

    verdict:
        present: condicion demostrada
        absent: ausencia demostrada
        uncertain: evidencia insuficiente o contradictoria

    El objeto solo puede construirse despues de verificar
    la conclusion semantica. No representa la salida cruda
    del extractor.
    """

    indicator: str
    verdict: SemanticVerdict
    verified: bool
    reason: str

    def __post_init__(self):
        if self.indicator not in ND_CODES:
            raise ValueError("Indicador ND invalido")
        if self.verdict not in (
            "present", "absent", "uncertain"
        ):
            raise ValueError("Veredicto invalido")
        if type(self.verified) is not bool:
            raise TypeError("verified debe ser bool")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("Justificacion obligatoria")


@dataclass(frozen=True)
class ApplicabilityResult:
    indicator: str
    status: Applicability
    reason: str


def resolve_applicability(
    finding: VerifiedApplicability,
) -> ApplicabilityResult:
    """Resuelve exclusivamente aplicabilidad, nunca scoring.

    ND1, ND2, ND7:
        Se necesita la condicion especifica de la rubrica.

    ND3, ND4, ND5, ND6, ND8:
        Se evalua en general. El veredicto 'absent'
        significa exclusivamente ausencia objetiva
        de contenido evaluable, NO ausencia de una
        distorsion particular ni ausencia de una infraccion.
    """

    indicator = finding.indicator

    if not finding.verified:
        return ApplicabilityResult(
            indicator,
            "BLOCKED",
            "Conclusion semantica sin verificacion independiente",
        )

    if finding.verdict == "uncertain":
        return ApplicabilityResult(
            indicator,
            "BLOCKED",
            finding.reason,
        )

    if indicator in ND_CONDITIONAL:
        if finding.verdict == "present":
            return ApplicabilityResult(
                indicator,
                "APPLICABLE",
                finding.reason,
            )
        return ApplicabilityResult(
            indicator,
            "NA",
            finding.reason,
        )

    if finding.verdict == "present":
        return ApplicabilityResult(
            indicator,
            "APPLICABLE",
            finding.reason,
        )

    return ApplicabilityResult(
        indicator,
        "NA",
        finding.reason,
    )


def resolve_family_applicability(
    findings: list[VerifiedApplicability],
) -> dict[str, ApplicabilityResult]:
    """Exige una decision explicita por cada indicador."""

    if len(findings) != len(ND_CODES):
        raise ValueError(
            "Se requieren ocho hallazgos, uno por indicador"
        )

    codes = [finding.indicator for finding in findings]

    if set(codes) != set(ND_CODES) or len(set(codes)) != 8:
        raise ValueError(
            "Indicadores ND incompletos o duplicados"
        )

    return {
        finding.indicator: resolve_applicability(finding)
        for finding in findings
    }
