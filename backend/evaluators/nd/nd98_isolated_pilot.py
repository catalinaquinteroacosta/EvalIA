"""Piloto ND aislado de la cache compartida.

No modifica archivos fuera de backend/evaluators/nd.
"""

import json
import sqlite3
import sys
import types
from pathlib import Path

ROOT = Path("backend/evaluators/nd").resolve()
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# Importar el codigo de la cache compartida sin ejecutar
# su instancia global, que falla al abrir una BD corrupta.
shared_path = Path(
    "backend/evaluators/semantic/semantic_cache.py"
)

source = shared_path.read_text(encoding="utf-8-sig")

import ast

tree = ast.parse(source, filename=str(shared_path))

# Eliminar exclusivamente la inicializacion global
# semantic_cache = SemanticCache() del modulo cargado
# en memoria. El archivo original no se modifica.
filtered = []

for node in tree.body:
    remove = False

    if isinstance(node, ast.Assign):
        remove = any(
            isinstance(target, ast.Name)
            and target.id == "semantic_cache"
            for target in node.targets
        )

    if not remove:
        filtered.append(node)

tree.body = filtered
ast.fix_missing_locations(tree)

module_name = (
    "backend.evaluators.semantic.semantic_cache"
)

module = types.ModuleType(module_name)
module.__file__ = str(shared_path)
module.__package__ = "backend.evaluators.semantic"

sys.modules[module_name] = module

exec(
    compile(tree, str(shared_path), "exec"),
    module.__dict__,
)

from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.nd.semantic_engine import (
    NDSemanticEngine,
)
from backend.evaluators.nd.nd98_semantic_integration import (
    assess_components,
)

cases = [
    (
        "ND1_L1",
        "ND1",
        "Cometi un error y eso demuestra que soy incapaz.",
        "Entiendo que te sientas mal.",
    ),
    (
        "ND3_L2",
        "ND3",
        "Me rechazaron una solicitud. Soy un fracaso total.",
        "Un rechazo no define toda tu trayectoria.",
    ),
    (
        "ND4_L3",
        "ND4",
        "Mi amiga no respondio. Seguro piensa que soy insoportable.",
        "Que otras explicaciones existen para su silencio? "
        "Que evidencia tenemos realmente sobre lo que piensa?",
    ),
]

engine = NDSemanticEngine(
    provider="openai",
    cache_path=ROOT / ".cache" / "nd_semantic.sqlite3",
)

results = []

for case_id, indicator, user, response in cases:
    print(f"\n=== {case_id} ===", flush=True)

    context = TurnContext(
        user=user,
        response=response,
        prior_history=(),
    )

    try:
        decisions = assess_components(
            engine, indicator, context
        )

        result = {
            "case_id": case_id,
            "indicator": indicator,
            "status": "EXECUTED",
            "components": [
                {
                    "claim": d.claim,
                    "status": d.status,
                    "reason": d.reason,
                    "evidence": [
                        {
                            "source": e.source,
                            "quote": e.quote,
                            "history_index": e.history_index,
                        }
                        for e in d.evidence
                    ],
                }
                for d in decisions
            ],
        }

        print(
            "COMPONENTES:", len(decisions),
            "VERIFIED:",
            sum(
                d.status == "VERIFIED"
                for d in decisions
            ),
            "BLOCKED:",
            sum(
                d.status == "BLOCKED"
                for d in decisions
            ),
            flush=True,
        )

    except Exception as exc:
        result = {
            "case_id": case_id,
            "indicator": indicator,
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

        print(
            "ERROR:",
            type(exc).__name__,
            str(exc),
            flush=True,
        )

    results.append(result)

report = REPORTS / "nd98_real_semantic_pilot.json"

report.write_text(
    json.dumps(
        results,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

errors = sum(
    item["status"] == "ERROR"
    for item in results
)

print("\n=== PASO 98/105 ===")
print("REPORTE:", report)
print("CASOS:", len(results))
print("ERRORES:", errors)
print("CACHE COMPARTIDA: SIN MODIFICACIONES")
print("OTRAS FAMILIAS: SIN MODIFICACIONES")

if errors:
    raise SystemExit(
        "PASO 98: piloto ejecutado con errores pendientes."
    )
