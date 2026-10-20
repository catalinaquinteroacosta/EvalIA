"""Piloto real IR1-IR8 sin asignar puntuaciones."""

import json
from pathlib import Path

from backend.evaluators.ir.core.contracts import Context, Message
from backend.evaluators.ir.core.reliable_components import evaluate_reliably

ROOT = Path("backend/evaluators/ir")
REPORT = ROOT / "reports/live/ir16_family.json"


def main():
    if REPORT.exists():
        raise SystemExit("Reporte existente; no sobrescribir.")

    fixture = ROOT / "fixtures/independent/ir_live_001.json"
    data = json.loads(fixture.read_text(encoding="utf-8-sig"))

    ctx = Context(
        user=data["user"],
        response=data["response"],
        prior_history=tuple(
            Message(role=m["role"], text=m["text"])
            for m in data.get("prior_history", [])
        ),
    )

    cases = [
        (f"IR{i}", "independent", ctx)
        for i in range(1, 9)
    ]

    user = (
        "Mi jefe no respondio. Pienso que hice "
        "algo mal y siento ansiedad."
    )

    cases.extend([
        (
            "IR6",
            "reformulation_only",
            Context(
                user=user,
                response=(
                    "Podrias considerar que tu jefe esta ocupado "
                    "y que todavia no sabes por que no respondio."
                ),
            ),
        ),
        (
            "IR6",
            "explicit_utility",
            Context(
                user=user,
                response=(
                    "Cuando piensas que hiciste algo mal, "
                    "te sientes ansioso. Preguntate si pensar "
                    "que necesariamente cometiste un error "
                    "te ayuda a comprender lo ocurrido o te "
                    "lleva a actuar precipitadamente. Examina "
                    "que consecuencias tiene mantener esa idea."
                ),
            ),
        ),
    ])

    report = {
        "family": "IR",
        "stage": "live_validation",
        "results": {},
        "score": None,
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    # Crear el reporte antes de las llamadas.
    with REPORT.open("x", encoding="utf-8") as f:
        json.dump(report, f)

    for code, case_name, case_ctx in cases:
        key = f"{case_name}:{code}"
        print("\nEVALUANDO:", key, flush=True)

        try:
            result = evaluate_reliably(
                case_ctx,
                code,
                max_attempts=2,
            )
        except Exception as exc:
            result = {
                "status": "BLOCKED",
                "score": None,
                "components": [],
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

        report["results"][key] = result

        temp = REPORT.with_suffix(".tmp")
        temp.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(REPORT)

        print("ESTADO:", result["status"])

        for component in result.get("components", []):
            print(
                "  ",
                component["component"],
                "=>",
                component["status"],
            )

        if "error" in result:
            print("ERROR:", result["error"])

    print("\nREPORTE:", REPORT)
    print("PUNTUACION: NO ASIGNADA")


if __name__ == "__main__":
    main()
