
import json
from pathlib import Path

from backend.evaluators.nd.official_rubric import (
    load_official_nd_rubric,
)

ROOT = Path("backend/evaluators/nd")
MATRIX = ROOT / "reports/nd99_scoring_matrix.json"
OUTPUT = ROOT / "reports/nd99_fact_batch_results.json"

FACT_NAMES = (
    "reinforces_negative_idea",
    "intervention_present",
    "correction_present",
    "active_questioning",
    "cognitive_balance_promoted",
)

def prepare_fact_tasks():
    official = load_official_nd_rubric()
    matrix = json.loads(MATRIX.read_text(encoding="utf-8-sig"))
    tasks = []

    for case in matrix["cases"]:
        indicator = case["indicator"]
        question = official.indicators[indicator].get("question")

        if not question:
            raise ValueError(
                f"Pregunta oficial no encontrada: {indicator}"
            )

        tasks.append({
            "case_id": case["case_id"],
            "indicator": indicator,
            "official_question": question,
            "official_levels": official.levels,
            "user": case["user"],
            "response": case["response"],
            "verified_components": case["verified_components"],
            "required_facts": list(FACT_NAMES),
            "status": "PENDING_INDEPENDENT_FACT_VERIFICATION",
        })

    return tasks

def main():
    tasks = prepare_fact_tasks()

    if len(tasks) != 32:
        raise ValueError("Lote incompleto")

    output = {
        "step": "99/105",
        "criterion": "AD-04",
        "tasks": tasks,
        "scoring_performed": False,
        "experiment_072": "PENDING",
    }

    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=== PASO 99/105: LOTE DE HECHOS ===")
    print("CASOS PREPARADOS:", len(tasks))
    print("INDICADORES:", len(set(t["indicator"] for t in tasks)))
    print("TAREAS SEMANTICAS:", len(tasks) * len(FACT_NAMES))
    print("RESULTADOS SEMANTICOS OBTENIDOS: 0")
    print("PUNTUACIONES ASIGNADAS: 0")
    print("REPORTE:", OUTPUT)
    print("OTRAS FAMILIAS: SIN MODIFICACIONES")
    print("CACHE COMPARTIDA: SIN MODIFICACIONES")

if __name__ == "__main__":
    main()
