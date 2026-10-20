"""Puntuación IR: decisión determinística y rúbrica oficial."""

import json
from pathlib import Path

RUBRIC_PATH = Path(
    "database/rubrics/ansiedad_depresion.json"
)

CODES = tuple(f"IR{i}" for i in range(1, 9))

LEVELS = {
    "absent": 0,
    "low": 1,
    "adequate": 2,
    "high": 3,
}


def load_ir_rubric(path=RUBRIC_PATH):
    with Path(path).open(encoding="utf-8-sig") as stream:
        rubric = json.load(stream)

    criterion = next(
        item for item in rubric["criteria"]
        if item["code"] == "AD-03"
    )

    indicators = {
        item["code"]: item
        for item in criterion["indicators"]
    }

    if set(indicators) != set(CODES):
        raise ValueError("La familia IR oficial no coincide")

    return {
        "version": rubric["version"],
        "scale": rubric["scale"],
        "criterion": criterion,
        "indicators": indicators,
    }


def score_indicator(
    code,
    *,
    applicability,
    verified_level=None,
    evidence_valid=False,
    unresolved=False,
):
    """
    verified_level representa un juicio semántico ya verificado,
    no una puntuación emitida por OpenAI.

    La conversión numérica es determinística.
    """

    rubric = load_ir_rubric()

    if code not in rubric["indicators"]:
        raise ValueError("Indicador IR desconocido")

    indicator = rubric["indicators"][code]
    official_applicability = indicator["applicability"]

    if applicability not in (
        "applicable", "not_applicable", "ambiguous"
    ):
        raise ValueError("Aplicabilidad inválida")

    if official_applicability == "general":
        if applicability == "not_applicable":
            return {
                "code": code,
                "status": "BLOCKED",
                "score": None,
                "reason": "N/A incompatible con aplicabilidad general",
            }

    if applicability == "ambiguous":
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Aplicabilidad no resuelta",
        }

    if applicability == "not_applicable":
        return {
            "code": code,
            "status": "N/A",
            "score": None,
            "reason": "Indicador condicional no aplicable",
        }

    if unresolved:
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Discrepancia semántica no resuelta",
        }

    if verified_level not in LEVELS:
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Nivel de cumplimiento no verificado",
        }

    if verified_level != "absent" and not evidence_valid:
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Evidencia positiva sin validación",
        }

    score = LEVELS[verified_level]

    return {
        "code": code,
        "status": "SCORED",
        "score": score,
        "label": rubric["scale"]["labels"][str(score)],
    }