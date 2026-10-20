"""Contrato ND de extraccion semantica sin scoring."""

from dataclasses import dataclass
from typing import Literal

from .contracts import ND_CODES, TurnContext, Evidence
from .official_rubric import load_official_nd_rubric

Verdict = Literal["present", "absent", "uncertain"]


@dataclass(frozen=True)
class ND97Observation:
    indicator: str
    fact_name: str
    verdict: Verdict
    evidence: tuple[Evidence, ...]
    reason: str


def official_extraction_spec(indicator: str) -> dict:
    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    rubric = load_official_nd_rubric()

    return {
        "indicator": indicator,
        "question": rubric.indicators[indicator]["question"],
        "applicability": (
            rubric.indicators[indicator]["applicability"]
        ),
        "levels": dict(rubric.levels),
        "instruction": (
            "Extraer observaciones semanticas y evidencia "
            "literal. No asignar nivel ni puntuacion. "
            "No inventar evidencia. Distinguir hechos "
            "presentes, ausentes e inciertos."
        ),
    }


def validate_observation(
    observation: ND97Observation,
    context: TurnContext,
) -> bool:
    if observation.indicator not in ND_CODES:
        return False

    if observation.verdict not in (
        "present", "absent", "uncertain"
    ):
        return False

    if not observation.reason.strip():
        return False

    if observation.verdict == "present":
        if not observation.evidence:
            return False
        return all(
            item.verify_exact(context)
            for item in observation.evidence
        )

    # Ausencia e incertidumbre requieren verificacion
    # independiente; no se aprueban por falta de citas.
    return not observation.evidence
