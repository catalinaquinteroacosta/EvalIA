"""Lectura estricta de la rubrica oficial AD-05."""
from __future__ import annotations

import json
from pathlib import Path

from .contracts import CODES, CONDITIONAL


RUBRIC_PATH = (
    Path(__file__).resolve().parents[3]
    / "database"
    / "rubrics"
    / "ansiedad_depresion.json"
)

EXPECTED_LEVELS = {"0", "1", "2", "3"}


def load_official_pa(path: Path | None = None) -> dict:
    source = path if path is not None else RUBRIC_PATH
    data = json.loads(
        Path(source).read_text(encoding="utf-8-sig")
    )

    matches = [
        criterion
        for criterion in data["criteria"]
        if criterion.get("code") == "AD-05"
    ]

    if len(matches) != 1:
        raise ValueError(
            "Debe existir exactamente un criterio AD-05"
        )

    criterion = matches[0]
    indicators = criterion["indicators"]

    codes = tuple(item["code"] for item in indicators)

    if codes != CODES:
        raise ValueError(
            f"Indicadores PA incorrectos: {codes}"
        )

    if set(criterion["levels"]) != EXPECTED_LEVELS:
        raise ValueError(
            "Niveles oficiales incompletos o alterados"
        )

    for item in indicators:
        code = item["code"]
        expected = (
            "conditional" if code in CONDITIONAL
            else "general"
        )

        if item["applicability"] != expected:
            raise ValueError(
                f"Aplicabilidad incorrecta: {code}"
            )

        if not item["question"].strip():
            raise ValueError(
                f"Pregunta vacia: {code}"
            )

    return criterion


def indicator_definition(code: str) -> dict:
    if code not in CODES:
        raise ValueError(f"Indicador desconocido: {code}")

    criterion = load_official_pa()

    return next(
        item for item in criterion["indicators"]
        if item["code"] == code
    )
