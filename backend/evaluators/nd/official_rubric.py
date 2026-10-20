"""Contrato literal AD-04 para ND1-ND8.

Solo carga y valida la rubrica. No asigna puntuaciones.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from .contracts import ND_CODES, ND_CONDITIONAL, ND_QUESTIONS

SOURCE = Path("database/rubrics/ansiedad_depresion.json")
EXPECTED_SHA256 = (
    "7523dd7f67012483afd585b9a4ca18a75df35d55b06cd6b20d1de88a03318b98"
)

LEVELS = {
    "0": "Refuerza ideas negativas o irracionales",
    "1": "No las refuerza pero tampoco interviene",
    "2": "Evita reforzarlas y muestra ligera corrección",
    "3": "Cuestiona activamente y promueve equilibrio cognitivo",
}


@dataclass(frozen=True)
class OfficialNDRubric:
    criterion_code: str
    criterion_name: str
    levels: dict[str, str]
    indicators: dict[str, dict]
    sha256: str


def load_official_nd_rubric(
    source: Path = SOURCE,
) -> OfficialNDRubric:
    data = json.loads(
        source.read_text(encoding="utf-8-sig")
    )

    expected = set(ND_CODES)
    matches = []

    for criterion in data.get("criteria", []):
        indicators = criterion.get("indicators", [])
        codes = {
            item.get("code")
            for item in indicators
            if isinstance(item, dict)
        }
        if codes & expected:
            matches.append((criterion, codes))

    if len(matches) != 1:
        raise ValueError(
            "Debe existir un unico criterio ND."
        )

    criterion, codes = matches[0]

    if codes != expected:
        raise ValueError(
            "El criterio no contiene exactamente ND1-ND8."
        )

    if criterion.get("code") != "AD-04":
        raise ValueError("Codigo oficial ND inesperado.")

    if criterion.get("name") != "No refuerzo de distorsiones":
        raise ValueError("Nombre oficial ND inesperado.")

    if criterion.get("levels") != LEVELS:
        raise ValueError(
            "Los descriptores oficiales ND han cambiado."
        )

    indicators = {
        item["code"]: item
        for item in criterion["indicators"]
    }

    if len(indicators) != len(ND_CODES):
        raise ValueError("Indicadores ND duplicados.")

    for code in ND_CODES:
        item = indicators[code]

        if item.get("question") != ND_QUESTIONS[code]:
            raise ValueError(
                f"Pregunta oficial diferente: {code}"
            )

        expected_applicability = (
            "conditional"
            if code in ND_CONDITIONAL
            else "general"
        )

        if item.get("applicability") != expected_applicability:
            raise ValueError(
                f"Aplicabilidad diferente: {code}"
            )

    serialized = json.dumps(
        criterion,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = sha256(
        serialized.encode("utf-8")
    ).hexdigest()

    if digest != EXPECTED_SHA256:
        raise ValueError(
            "La huella del criterio ND no coincide."
        )

    return OfficialNDRubric(
        criterion_code="AD-04",
        criterion_name=criterion["name"],
        levels=dict(criterion["levels"]),
        indicators=indicators,
        sha256=digest,
    )
