"""Scoring PA: contrato estricto con rubrica AD-05.

No infiere niveles desde conteos de propiedades.
No permite puntuar evidencia no verificada.
"""
import json
from pathlib import Path

RUBRIC_PATH = Path(
    "database/rubrics/ansiedad_depresion.json"
)

def _find(obj):
    if isinstance(obj, dict):
        if obj.get("code") == "AD-05":
            return obj
        for value in obj.values():
            result = _find(value)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for value in obj:
            result = _find(value)
            if result is not None:
                return result
    return None

def official_contract():
    data = json.loads(
        RUBRIC_PATH.read_text(encoding="utf-8-sig")
    )
    criterion = _find(data)
    if criterion is None:
        raise ValueError("Rubrica AD-05 no encontrada")
    return criterion

def score_verified(
    code,
    level=None,
    verified=False,
    applicability=None,
    unresolved=False,
    level_evidence=None,
    independent_level_verification=False,
    response=None,
):
    criterion = official_contract()
    indicators = {
        item["code"]: item
        for item in criterion["indicators"]
    }

    if code not in indicators:
        raise ValueError(f"Indicador desconocido: {code}")

    indicator = indicators[code]

    if unresolved or not verified:
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Evidencia o verificacion pendiente",
        }

    if applicability == "not_applicable":
        if indicator["applicability"] != "conditional":
            return {
                "code": code,
                "status": "BLOCKED",
                "score": None,
                "reason": "N/A incompatible con rubrica",
            }
        return {
            "code": code,
            "status": "N/A",
            "score": None,
            "reason": "Condicion no aplicable verificada",
        }

    if applicability != "applicable":
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Aplicabilidad no verificada",
        }

    if type(level) is not int or level not in range(4):
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Nivel oficial no determinado",
        }

    if (
        not isinstance(level_evidence, dict)
        or not level_evidence.get("quotes")
        or not level_evidence.get("reason")
        or independent_level_verification is not True
        or not isinstance(response, str)
        or not isinstance(level_evidence.get("quotes"), list)
        or any(
            not isinstance(q, str)
            or not q.strip()
            or q not in response
            for q in level_evidence["quotes"]
        )
    ):
        return {
            "code": code,
            "status": "BLOCKED",
            "score": None,
            "reason": "Falta respaldo independiente del nivel",
        }

    return {
        "code": code,
        "status": "SCORED",
        "score": level,
        "official_descriptor": criterion["levels"][str(level)],
        "official_question": indicator["question"],
    }
