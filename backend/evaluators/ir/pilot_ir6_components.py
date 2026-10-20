"""Piloto real IR6: componentes sin puntuación."""

import json
from pathlib import Path

from backend.evaluators.ir.core.contracts import (
    Context,
    Message,
)
from backend.evaluators.ir.core.component_engine import (
    evaluate_components,
)


def main():
    root = Path("backend/evaluators/ir")

    fixture = (
        root / "fixtures/independent/ir_live_001.json"
    )

    with fixture.open(encoding="utf-8-sig") as stream:
        data = json.load(stream)

    history = tuple(
        Message(
            role=item["role"],
            text=item["text"],
        )
        for item in data.get("prior_history", [])
    )

    ctx = Context(
        user=data["user"],
        response=data["response"],
        prior_history=history,
    )

    results = evaluate_components(ctx, "IR6")

    report = {
        "family": "IR",
        "indicator": "IR6",
        "stage": "component_validation_unscored",
        "components": results,
        "score": None,
    }

    destination = (
        root / "reports/live/ir6_components_pilot.json"
    )

    if destination.exists():
        raise FileExistsError(destination)

    destination.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nIR6 - PILOTO REAL")
    print("=" * 65)

    for component in results:
        print("\nCOMPONENTE:", component["component"])
        print("EXTRACTOR:", component["present"])
        print("VERIFICADOR:", component["verification"])
        print("ESTADO:", component["status"])
        print("JUSTIFICACION:", component["reason"])

        for evidence in component["evidence"]:
            print("CITA:", evidence["quote"])

    print("\nPUNTUACION: PENDIENTE")
    print("REPORTE:", destination)


if __name__ == "__main__":
    main()