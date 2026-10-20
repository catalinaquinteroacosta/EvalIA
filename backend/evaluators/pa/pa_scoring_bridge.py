"""Puente seguro entre propiedades verificadas y scoring PA.

No asigna puntuaciones por conteo ni recibe niveles externos.
"""
import json
from pathlib import Path

SOURCE = Path(
    "backend/evaluators/pa/reports/"
    "pa_scoring_input_safe_v1.json"
)

def prepare():
    data = json.loads(
        SOURCE.read_text(encoding="utf-8-sig")
    )

    output = {}

    for code, item in data["results"].items():
        properties = item.get("properties", [])

        blocked = (
            item.get("scoring_status") != "READY_FOR_RULE_MAPPING"
            or any(
                p.get("value") not in ("present", "absent")
                or p.get("technical_status") == "BLOCKED"
                for p in properties
            )
        )

        output[code] = {
            "status": (
                "BLOCKED" if blocked
                else "READY_FOR_DETERMINISTIC_SCORING"
            ),
            "score": None,
            "official_question": item["official_question"],
            "applicability": item["applicability"],
            "properties": properties,
            "material_omissions": item.get(
                "material_omissions", []
            ),
        }

    return output
