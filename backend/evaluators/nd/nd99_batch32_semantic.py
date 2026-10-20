"""PASO 99/105: lote semantico de 32 contrastes, sin scoring."""

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
    found = False

    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "backend.evaluators.nd.contracts"
        ):
            found = True
            break
        bootstrap.append(node)

    if not found:
        raise RuntimeError("Aislamiento ND98 no encontrado")

    program = r"""
from backend.evaluators.nd.contracts import (
    HistoryTurn,
    TurnContext,
)
from backend.evaluators.nd.semantic_engine import NDSemanticEngine
from backend.evaluators.nd.nd99_semantic_adapter import (
    assess_indicator_semantics,
)

root = Path("backend/evaluators/nd")
fixture = root / "fixtures" / "nd_contrastive_32.json"
output = root / "reports" / "nd99_batch32_semantic.json"

data = json.loads(fixture.read_text(encoding="utf-8"))
cases = data["cases"]

if len(cases) != 32:
    raise ValueError("Se esperaban exactamente 32 casos")

if len({case["id"] for case in cases}) != 32:
    raise ValueError("Identificadores duplicados")

engine = NDSemanticEngine(
    provider="openai",
    cache_path=root / ".cache" / "nd_semantic.sqlite3",
)

results = {}

if output.exists():
    saved = json.loads(output.read_text(encoding="utf-8"))
    if isinstance(saved, dict):
        results = saved.get("results", {})

for number, case in enumerate(cases, 1):
    case_id = case["id"]
    indicator = case["indicator"]

    if (
        case_id in results
        and results[case_id].get("status") == "VERIFIED"
    ):
        print(
            f"[{number}/32] {case_id}: VERIFIED previo",
            flush=True,
        )
        continue

    print(
        f"[{number}/32] {case_id}: evaluando",
        flush=True,
    )

    try:
        history = tuple(
            HistoryTurn(**turn)
            for turn in case.get("prior_history", [])
        )

        context = TurnContext(
            user=case["user"],
            response=case["response"],
            prior_history=history,
        )

        report = assess_indicator_semantics(
            engine,
            indicator,
            context,
        )

        results[case_id] = {
            "indicator": indicator,
            "status": report.status,
            "official_question": report.official_question,
            "reason": report.reason,
            "components": [
                {
                    "claim": component.claim,
                    "verdict": component.verdict,
                    "reason": component.reason,
                    "evidence": [
                        {
                            "source": evidence["source"],
                            "quote": evidence["quote"],
                            "history_index": evidence.get("history_index"),
                        }
                        for evidence in component.evidence
                    ],
                }
                for component in report.components
            ],
        }

    except Exception as exc:
        results[case_id] = {
            "indicator": indicator,
            "status": "BLOCKED",
            "error_type": type(exc).__name__,
            "reason": str(exc),
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "step": "99/105",
                "criterion": "AD-04",
                "scoring_performed": False,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"[{number}/32] {case_id}: "
        f"{results[case_id]['status']}",
        flush=True,
    )

verified = sum(
    item["status"] == "VERIFIED"
    for item in results.values()
)

blocked = sum(
    item["status"] == "BLOCKED"
    for item in results.values()
)

print("\\n=== RESUMEN PASO 99/105 ===")
print("CASOS REGISTRADOS:", len(results))
print("VERIFIED:", verified)
print("BLOCKED:", blocked)
print("PUNTUACIONES ASIGNADAS: 0")
print("REPORTE:", output)
print("CACHE COMPARTIDA: SIN MODIFICACIONES")
print("OTRAS FAMILIAS: SIN MODIFICACIONES")
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
