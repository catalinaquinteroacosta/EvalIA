"""Piloto IR6: contraste semantico con reintentos estrictos."""

import json
from pathlib import Path

from backend.evaluators.ir.core.contracts import Context
from backend.evaluators.ir.core.reliable_components import (
    evaluate_reliably,
)


def main():
    root = Path("backend/evaluators/ir")
    destination = (
        root / "reports/live/ir6_boundary_ir14a.json"
    )

    if destination.exists():
        raise FileExistsError(destination)

    cases = {
        "reformulation_only": Context(
            user=(
                "Mi jefe no respondio. Pienso que hice "
                "algo mal y siento ansiedad."
            ),
            response=(
                "Podrias considerar que tu jefe esta "
                "ocupado y que todavia no sabes "
                "por que no respondio."
            ),
        ),
        "explicit_utility": Context(
            user=(
                "Mi jefe no respondio. Pienso que hice "
                "algo mal y siento ansiedad."
            ),
            response=(
                "Cuando piensas que hiciste algo mal, "
                "te sientes ansioso. Preguntate si "
                "pensar que necesariamente cometiste "
                "un error te ayuda a comprender lo "
                "ocurrido o te lleva a actuar "
                "precipitadamente. Examina que "
                "consecuencias tiene mantener esa idea."
            ),
        ),
    }

    report = {
        "family": "IR",
        "indicator": "IR6",
        "stage": "real_boundary_validation",
        "cases": {},
    }

    for name, ctx in cases.items():
        print("\n" + "=" * 65)
        print("CASO:", name)

        result = evaluate_reliably(
            ctx,
            "IR6",
            max_attempts=2,
        )

        report["cases"][name] = {
            "user": ctx.user,
            "response": ctx.response,
            **result,
        }

        print("ESTADO GENERAL:", result["status"])
        print("INTENTOS:", result["attempts"])

        for component in result["components"]:
            print("\nCOMPONENTE:", component["component"])
            print("EXTRACTOR:", component["present"])
            print("VERIFICADOR:", component["verification"])
            print("ESTADO:", component["status"])
            print("JUSTIFICACION:", component["reason"])

        if result["errors"]:
            print("ERRORES:", result["errors"])

    destination.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nREPORTE:", destination)
    print("PUNTUACION: NO ASIGNADA")


if __name__ == "__main__":
    main()
