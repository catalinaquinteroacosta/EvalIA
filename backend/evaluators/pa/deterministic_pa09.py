
"""PA09: puntuacion deterministica, subordinada a AD-05.

Las propiedades son observaciones semanticas verificadas.
No se admiten puntuaciones procedentes del extractor.
"""

from dataclasses import dataclass
from typing import Mapping

from .official_scoring_pa import official_contract


@dataclass(frozen=True)
class VerifiedProperty:
    name: str
    value: str
    verified: bool
    evidence_valid: bool


@dataclass(frozen=True)
class SemanticAssessment:
    code: str
    applicability: str
    action_present: bool | None
    action_clear: bool | None
    action_useful: bool | None
    action_applicable: bool | None
    properties: tuple[VerifiedProperty, ...]
    unresolved: bool = False


def blocked(code, reason):
    return {
        "code": code,
        "status": "BLOCKED",
        "score": None,
        "reason": reason,
    }


def evaluate(assessment: SemanticAssessment):
    rubric = official_contract()
    indicators = {
        item["code"]: item
        for item in rubric["indicators"]
    }

    code = assessment.code

    if code not in indicators:
        raise ValueError(code)

    indicator = indicators[code]

    if assessment.unresolved:
        return blocked(code, "Discrepancia semantica pendiente")

    if assessment.applicability == "not_applicable":
        if indicator["applicability"] != "conditional":
            return blocked(code, "N/A no permitido")
        return {
            "code": code,
            "status": "N/A",
            "score": None,
            "reason": "Condicion no aplicable",
        }

    if assessment.applicability != "applicable":
        return blocked(code, "Aplicabilidad no resuelta")

    if not assessment.properties:
        return blocked(code, "No existen propiedades verificadas")

    if any(
        p.value not in ("present", "absent")
        or not p.verified
        or not p.evidence_valid
        for p in assessment.properties
    ):
        return blocked(code, "Propiedades no verificadas")

    states = (
        assessment.action_present,
        assessment.action_clear,
        assessment.action_useful,
        assessment.action_applicable,
    )

    if any(type(x) is not bool for x in states):
        return blocked(code, "Calidad semantica incompleta")

    if assessment.action_present is False:
        level = 0
    elif assessment.action_clear is False or assessment.action_useful is False:
        level = 1
    elif assessment.action_applicable is False:
        level = 2
    else:
        level = 3

    return {
        "code": code,
        "status": "SCORED",
        "score": level,
        "official_descriptor": rubric["levels"][str(level)],
        "official_question": indicator["question"],
    }
