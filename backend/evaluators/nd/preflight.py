"""Preflight ND antes del primer piloto semantico real."""

import inspect
import json
import os
from pathlib import Path

from backend.evaluators.nd.contracts import (
    ND_CODES,
    TurnContext,
)
from backend.evaluators.nd.semantic_engine import (
    NDSemanticEngine,
    COMPONENT_SCHEMA,
    VERIFY_SCHEMA,
    CACHE_PATH,
    ENGINE_VERSION,
)
from backend.evaluators.nd.applicability_semantic import SCHEMA
from backend.evaluators.nd.reconciliation import RECONCILE_SCHEMA
from backend.evaluators.nd.negative_validation import NEGATIVE_SCHEMA
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
    run_structured_semantic,
)

root = Path("backend/evaluators/nd")
report_path = root / "reports" / "preflight_nd.json"
report_path.parent.mkdir(parents=True, exist_ok=True)

schemas = {
    "components": COMPONENT_SCHEMA,
    "verification": VERIFY_SCHEMA,
    "applicability": SCHEMA,
    "reconciliation": RECONCILE_SCHEMA,
    "negative": NEGATIVE_SCHEMA,
}

for name, schema in schemas.items():
    assert isinstance(schema, dict), name
    assert schema.get("type") == "object", name
    assert isinstance(schema.get("properties"), dict), name

assert len(ND_CODES) == 8
assert len(set(ND_CODES)) == 8

context = TurnContext(
    user="Siempre hago todo mal",
    response="Un error no significa que todo lo hagas mal.",
)

assert context.user
assert context.response

identity = get_semantic_identity(
    provider="openai",
    model=os.getenv("EVALIA_ND_MODEL") or None,
)

report = {
    "family": "ND",
    "engine_version": ENGINE_VERSION,
    "indicators": list(ND_CODES),
    "provider_identity": identity,
    "cache_path": str(CACHE_PATH),
    "schemas": {
        name: {
            "required": schema.get("required", []),
            "properties": list(schema.get("properties", {})),
        }
        for name, schema in schemas.items()
    },
    "provider_signature": str(
        inspect.signature(run_structured_semantic)
    ),
    "api_key_present": bool(os.getenv("OPENAI_API_KEY")),
    "real_api_calls": 0,
    "experiment_72_used": False,
}

report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("PREFLIGHT ND")
print("INDICADORES:", len(ND_CODES))
print("MOTOR:", ENGINE_VERSION)
print("PROVEEDOR:", identity)
print("API KEY CONFIGURADA:", report["api_key_present"])
print("CACHÉ:", CACHE_PATH)
print("LLAMADAS REALES:", 0)
print("REPORTE:", report_path)
