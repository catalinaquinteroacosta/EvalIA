"""Recuperacion selectiva de casos IR bloqueados."""

import json
from pathlib import Path

from backend.evaluators.ir.core.contracts import Context, Message
from backend.evaluators.ir.core.reliable_components import evaluate_reliably

ROOT = Path("backend/evaluators/ir")
SOURCE = ROOT / "reports/live/ir16_family.json"
DEST = ROOT / "reports/live/ir19_recovery.json"

TARGETS = (
    "independent:IR1",
    "independent:IR3",
    "independent:IR6",
    "reformulation_only:IR6",
)


def independent_context():
    path = ROOT / "fixtures/independent/ir_live_001.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))

    return Context(
        user=data["user"],
        response=data["response"],
        prior_history=tuple(
            Message(role=m["role"], text=m["text"])
            for m in data.get("prior_history", [])
        ),
    )


def negative_context():
    return Context(
        user=(
            "Mi jefe no respondio. Pienso que hice "
            "algo mal y siento ansiedad."
        ),
        response=(
            "Podrias considerar que tu jefe esta "
            "ocupado y que todavia no sabes "
            "por que no respondio."
        ),
    )


def save(report):
    temp = DEST.with_suffix(".tmp")
    temp.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(DEST)


def main():
    if DEST.exists():
        raise SystemExit(
            "Reporte IR19 existente; no sobrescribir."
        )

    original = json.loads(
        SOURCE.read_text(encoding="utf-8-sig")
    )

    contexts = {
        "independent": independent_context(),
        "reformulation_only": negative_context(),
    }

    report = {
        "family": "IR",
        "stage": "selective_recovery",
        "source": str(SOURCE),
        "results": {},
        "score": None,
    }

    with DEST.open("x", encoding="utf-8") as stream:
        json.dump(report, stream)

    for key in TARGETS:
        previous = original["results"][key]

        if previous.get("status") != "BLOCKED":
            print("CONSERVADO:", key)
            continue

        case_name, code = key.split(":")
        ctx = contexts[case_name]

        print("\n" + "=" * 68)
        print("RECUPERANDO:", key, flush=True)

        try:
            result = evaluate_reliably(
                ctx,
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
        save(report)

        print("ESTADO:", result["status"])

        for component in result.get("components", []):
            print(
                " -",
                component["component"],
                "=>",
                component["status"],
                "| extractor:",
                component["present"],
                "| verificador:",
                component["verification"],
            )

        for error in result.get("errors", []):
            print("ERROR:", error)

        if result.get("error"):
            print("ERROR TECNICO:", result["error"])

    print("\nREPORTE:", DEST)
    print("ORIGINAL IR16: INTACTO")
    print("PUNTUACIONES: NO ASIGNADAS")


if __name__ == "__main__":
    main()
