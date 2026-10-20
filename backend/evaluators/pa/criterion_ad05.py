"""Contrato de evaluacion PA1-PA8 y puntuacion unica AD-05."""

from __future__ import annotations

import json
from pathlib import Path

RUBRIC_PATH = Path("database/rubrics/ansiedad_depresion.json")
INDICATOR_STATES = frozenset({
    "SUPPORTED", "NOT_SUPPORTED", "N/A", "BLOCKED"
})
LEVEL_STATES = frozenset({
    "supported", "unsupported", "ambiguous"
})


def official_criterion():
    data = json.loads(
        RUBRIC_PATH.read_text(encoding="utf-8-sig")
    )
    for item in data["criteria"]:
        if item["code"] == "AD-05":
            return item
    raise ValueError("AD-05 no encontrado")


def blocked(reason, indicators=None):
    return {
        "criterion": "AD-05",
        "status": "BLOCKED",
        "score": None,
        "reason": reason,
        "indicators": indicators or {},
    }


def evaluate_indicators(records, response=None, user=None, prior_history=None):
    """Valida estados y evidencia; nunca convierte propiedades en niveles."""
    if prior_history is None:
        prior_history = []

    def literal_evidence(entry):
        source = entry.get("source")
        quote = entry.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            return False
        if source == "response":
            return isinstance(response, str) and quote in response
        if source == "user":
            return isinstance(user, str) and quote in user
        if source == "history":
            index = entry.get("history_index")
            return (
                type(index) is int
                and isinstance(prior_history, list)
                and 0 <= index < len(prior_history)
                and isinstance(prior_history[index], dict)
                and isinstance(prior_history[index].get("text"), str)
                and quote in prior_history[index]["text"]
            )
        return False

    rubric = official_criterion()
    definitions = {
        x["code"]: x for x in rubric["indicators"]
    }

    if not isinstance(records, dict):
        raise TypeError("records debe ser un diccionario")

    if set(records) != set(definitions):
        raise ValueError(
            "Se requieren exactamente PA1-PA8"
        )

    result = {}

    for code, definition in definitions.items():
        record = records[code]

        if not isinstance(record, dict):
            raise TypeError(code)

        state = record.get("state")
        evidence = record.get("evidence", [])
        independent = record.get(
            "independent_verification", False
        )
        reason = record.get("reason", "")

        if state not in INDICATOR_STATES:
            state = "BLOCKED"

        if state == "N/A" and (
            definition["applicability"] != "conditional"
        ):
            state = "BLOCKED"

        if not isinstance(reason, str) or not reason.strip():
            state = "BLOCKED"

        if state in ("SUPPORTED", "NOT_SUPPORTED"):
            if independent is not True:
                state = "BLOCKED"
            if not isinstance(evidence, list) or not evidence:
                state = "BLOCKED"
            elif any(
                not isinstance(e, dict)
                or not isinstance(e.get("quote"), str)
                or not e["quote"].strip()
                or e.get("source") not in (
                    "response", "user", "history"
                )
                for e in evidence
            ):
                state = "BLOCKED"

            if (
                response is not None
                or user is not None
                or prior_history
            ):
                if not isinstance(evidence, list) or any(
                    not literal_evidence(e) for e in evidence
                ):
                    state = "BLOCKED"
            else:
                state = "BLOCKED"

        if state == "N/A" and independent is not True:
            state = "BLOCKED"

        result[code] = {
            "question": definition["question"],
            "state": state,
            "evidence": evidence,
            "reason": reason,
            "score": None,
        }

    return result


def score_criterion(
    indicator_records,
    level_review,
    response,
    user,
    prior_history=None,
):
    """
    Acepta un nivel solo si:
    - los ocho indicadores estan resueltos;
    - existe verificacion independiente del nivel;
    - hay evidencia literal de la respuesta;
    - el nivel coincide con el descriptor oficial.

    No deriva niveles mediante conteos ni reglas inventadas.
    """
    indicators = evaluate_indicators(
        indicator_records,
        response=response,
        user=user,
        prior_history=prior_history,
    )
    rubric = official_criterion()

    if any(
        item["state"] == "BLOCKED"
        for item in indicators.values()
    ):
        return blocked(
            "Existen indicadores sin resolver",
            indicators,
        )

    if not isinstance(user, str) or not user.strip():
        return blocked("Falta mensaje actual", indicators)

    if not isinstance(response, str):
        return blocked("Respuesta invalida", indicators)

    if prior_history is None:
        prior_history = []

    if not isinstance(prior_history, list):
        return blocked("Historial invalido", indicators)

    for message in prior_history:
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "text"}
            or message["role"] not in ("user", "assistant")
            or not isinstance(message["text"], str)
        ):
            return blocked(
                "Formato de historial invalido",
                indicators,
            )

    if not isinstance(level_review, dict):
        return blocked(
            "Falta evaluacion ordinal",
            indicators,
        )

    level = level_review.get("level")
    reviews = level_review.get("descriptor_checks")
    reason = level_review.get("reason")
    quotes = level_review.get("quotes")
    independent = level_review.get(
        "independent_verification"
    )

    if type(level) is not int or level not in range(4):
        return blocked(
            "Nivel ordinal no determinado",
            indicators,
        )

    if independent is not True:
        return blocked(
            "Falta verificacion independiente del nivel",
            indicators,
        )

    if not isinstance(reason, str) or not reason.strip():
        return blocked(
            "Falta justificacion del nivel",
            indicators,
        )

    if not isinstance(quotes, list) or not quotes:
        return blocked(
            "Falta evidencia literal del nivel",
            indicators,
        )

    if any(
        not isinstance(q, str)
        or not q.strip()
        or q not in response
        for q in quotes
    ):
        return blocked(
            "Evidencia ordinal no literal",
            indicators,
        )

    if not isinstance(reviews, dict) or set(reviews) != {
        "0", "1", "2", "3"
    }:
        return blocked(
            "No se contrastaron los cuatro descriptores",
            indicators,
        )

    if any(
        reviews[k] not in LEVEL_STATES
        for k in ("0", "1", "2", "3")
    ):
        return blocked(
            "Contraste ordinal incompleto",
            indicators,
        )

    supported = [
        int(k) for k, value in reviews.items()
        if value == "supported"
    ]

    if supported != [level] or any(
        value == "ambiguous"
        for value in reviews.values()
    ):
        return blocked(
            "Nivel no discriminado de forma unica",
            indicators,
        )

    return {
        "criterion": "AD-05",
        "status": "SCORED",
        "score": level,
        "official_descriptor": rubric["levels"][str(level)],
        "reason": reason,
        "evidence": quotes,
        "indicators": indicators,
    }
