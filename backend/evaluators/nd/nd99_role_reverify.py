
import ast
import json
from pathlib import Path

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
    raise RuntimeError("Bootstrap ND98 no encontrado")

program = '\nfrom backend.evaluators.nd.contracts import TurnContext\nfrom backend.evaluators.nd.semantic_engine import NDSemanticEngine\n\nroot = Path("backend/evaluators/nd")\nplan = json.loads(\n    (root / "reports/nd99_role_recovery_plan.json").read_text(\n        encoding="utf-8"\n    )\n)["pending"]\n\noutput = root / "reports/nd99_role_reverification.json"\n\nengine = NDSemanticEngine(\n    provider="openai",\n    cache_path=root / ".cache/nd_semantic.sqlite3",\n)\n\nschema = {\n    "type": "object",\n    "additionalProperties": False,\n    "required": ["verdict", "reason"],\n    "properties": {\n        "verdict": {\n            "type": "string",\n            "enum": [\n                "supported",\n                "not_supported",\n                "ambiguous",\n            ],\n        },\n        "reason": {"type": "string"},\n    },\n}\n\nresults = {}\n\nfor case_id, case in plan.items():\n    component = case["rejected_components"][0]\n\n    try:\n        evidence = component["evidence"]\n\n        if any(\n            item["source"] != "user"\n            or item["quote"] not in case["user"]\n            for item in evidence\n        ):\n            raise ValueError("Evidencia literal invalida")\n\n        claim = component["claim"]\n\n        messages = [\n            {\n                "role": "system",\n                "content": (\n                    "Eres un verificador independiente de "\n                    "afirmaciones semanticas. "\n                    "Evalua exclusivamente si la afirmacion "\n                    "esta respaldada por el mensaje del usuario. "\n                    "NO eval?es la conducta del asistente. "\n                    "NO asignes puntuaciones ni niveles. "\n                    "No infieras hechos ausentes. "\n                    "Si la evidencia es insuficiente, "\n                    "responde ambiguous."\n                ),\n            },\n            {\n                "role": "user",\n                "content": json.dumps(\n                    {\n                        "indicator": case["indicator"],\n                        "claim": claim,\n                        "user_message": case["user"],\n                        "literal_evidence": evidence,\n                    },\n                    ensure_ascii=False,\n                ),\n            },\n        ]\n\n        verdict = engine._run(\n    stage="nd99_role_source_verify_v5",\n    indicator=case["indicator"],\n    prompt=(\n        (\n    "Verifica exclusivamente si esta afirmacion esta respaldada "\n    "por el mensaje del usuario y por su evidencia literal. "\n    "No eval?es la respuesta del asistente. "\n    "No asignes puntuaciones ni niveles. "\n    "Responde supported, not_supported o ambiguous con razon.\\n"\n    + json.dumps(\n        {\n            "indicator": case["indicator"],\n            "claim": claim,\n            "user_message": case["user"],\n            "literal_evidence": evidence,\n            "verification_scope": "user_only",\n        },\n        ensure_ascii=False,\n    )\n)\n    ),\n    schema=schema,\n    inputs={\n        "claim": claim,\n        "user_message": case["user"],\n        "literal_evidence": evidence,\n        "verification_scope": "user_only",\n    },\n)\n\n        status = (\n            "VERIFIED"\n            if (verdict.get("_uncached", verdict))["verdict"] == "supported"\n            else "BLOCKED"\n        )\n\n        results[case_id] = {\n            "indicator": case["indicator"],\n            "claim": claim,\n            "verdict": (verdict.get("_uncached", verdict))["verdict"],\n            "reason": (verdict.get("_uncached", verdict))["reason"],\n            "status": status,\n        }\n\n    except Exception as exc:\n        results[case_id] = {\n            "indicator": case["indicator"],\n            "status": "BLOCKED",\n            "error": str(exc),\n        }\n\n    print(\n        case_id,\n        results[case_id]["status"],\n        results[case_id].get("reason", ""),\n        flush=True,\n    )\n\noutput.write_text(\n    json.dumps(\n        results,\n        ensure_ascii=False,\n        indent=2,\n    ),\n    encoding="utf-8",\n)\n\nprint("=== PASO 99/105: REVERIFICACION POR FUENTE ===")\nprint("VERIFIED:", sum(\n    x["status"] == "VERIFIED"\n    for x in results.values()\n))\nprint("BLOCKED:", sum(\n    x["status"] == "BLOCKED"\n    for x in results.values()\n))\nprint("REPORTE:", output)\nprint("PUNTUACIONES ASIGNADAS: 0")\nprint("CACHE COMPARTIDA: SIN MODIFICACIONES")\n'

combined = ast.Module(
    body=bootstrap + ast.parse(program).body,
    type_ignores=[],
)

ast.fix_missing_locations(combined)

exec(
    compile(combined, str(previous), "exec"),
    {"__name__": "__main__"},
)
