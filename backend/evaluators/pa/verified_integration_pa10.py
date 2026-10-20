
"""PA10: entrada real verificada; sin puntuacion inferida."""

from .pa_scoring_bridge import prepare
from .official_scoring_pa import official_contract


def evaluate_existing():
    source = prepare()
    official = official_contract()

    indicators = {
        item["code"]: item
        for item in official["indicators"]
    }

    if set(source) != set(indicators):
        raise ValueError("Indicadores PA incompletos")

    output = {}

    for code, item in source.items():
        indicator = indicators[code]

        if item["official_question"] != indicator["question"]:
            raise ValueError(
                f"Pregunta oficial inconsistente: {code}"
            )

        if item["status"] == "BLOCKED":
            output[code] = {
                "status": "BLOCKED",
                "score": None,
                "reason": "Discrepancia semantica pendiente",
            }
            continue

        output[code] = {
            "status": "READY_FOR_SEMANTIC_MAPPING",
            "score": None,
            "official_question": indicator["question"],
            "properties": item["properties"],
            "applicability": item["applicability"],
            "reason": (
                "Propiedades disponibles; falta validar "
                "su correspondencia con los niveles oficiales"
            ),
        }

    return output
