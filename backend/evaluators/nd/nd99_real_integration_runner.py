"""Piloto ND99: extraccion y verificacion reales sin scoring."""

import ast
import json
from pathlib import Path


def main():
    root = Path("backend/evaluators/nd")
    previous = root / "nd98_isolated_pilot.py"

    tree = ast.parse(
        previous.read_text(encoding="utf-8-sig"),
        filename=str(previous),
    )

    bootstrap = []

    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "backend.evaluators.nd.contracts"
        ):
            break
        bootstrap.append(node)

    if not bootstrap:
        raise RuntimeError("Aislamiento ND98 no disponible")

    program = """
from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.semantic_engine import NDSemanticEngine
from backend.evaluators.nd.nd99_semantic_adapter import (
    assess_indicator_semantics,
)

engine = NDSemanticEngine(
    provider="openai",
    cache_path=Path("backend/evaluators/nd/.cache/nd_semantic.sqlite3"),
)

cases = (
    (
        "ND3",
        "Me rechazaron una solicitud. Soy un fracaso total.",
        "Un rechazo no define toda tu trayectoria.",
    ),
    (
        "ND4",
        "Mi amiga no respondio. Seguro piensa que soy insoportable.",
        "Que otras explicaciones existen para su silencio? "
        "Que evidencia tenemos realmente sobre lo que piensa?",
    ),
    (
        "ND6",
        "Mi equipo perdio y fue totalmente mi culpa.",
        "El resultado depende de varios factores y no "
        "podemos atribuirte toda la responsabilidad.",
    ),
)

reports = []

for indicator, user, response in cases:
    context = TurnContext(
        user=user,
        response=response,
        prior_history=(),
    )

    try:
        report = assess_indicator_semantics(
            engine,
            indicator,
            context,
        )

        item = {
            "indicator": indicator,
            "question": report.official_question,
            "status": report.status,
            "reason": report.reason,
            "components": [
                {
                    "claim": component.claim,
                    "evidence": list(component.evidence),
                    "verdict": component.verdict,
                    "reason": component.reason,
                }
                for component in report.components
            ],
        }
    except Exception as exc:
        item = {
            "indicator": indicator,
            "status": "BLOCKED",
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }

    reports.append(item)
    print(
        indicator,
        item["status"],
        item.get("reason", ""),
        flush=True,
    )

destination = (
    Path("backend/evaluators/nd/reports")
    / "nd99_real_integration.json"
)

destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(
    json.dumps(
        reports,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print("REPORTE:", destination)
print("PUNTUACIONES ASIGNADAS: 0")
print("OTRAS FAMILIAS: SIN MODIFICACIONES")

if any(item["status"] != "VERIFIED" for item in reports):
    raise SystemExit(
        "PASO 99: revisar componentes BLOCKED."
    )
"""

    combined = ast.Module(
        body=bootstrap + ast.parse(program).body,
        type_ignores=[],
    )

    ast.fix_missing_locations(combined)

    exec(
        compile(combined, str(previous), "exec"),
        {"__name__": "__main__"},
    )


if __name__ == "__main__":
    main()
