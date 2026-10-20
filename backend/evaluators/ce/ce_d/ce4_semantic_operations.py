
"""Operaciones semanticas CE4 con cache validado."""

import json

from backend.evaluators.ansiedad_semantic.private_cache import (
    cached_semantic_operation,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
    run_structured_semantic,
)

from .ce4_semantic_identity import (
    IDENTITY_VERSION,
    STAGES,
)


class CE4SemanticContractError(ValueError):
    pass


VERDICT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {
            "type": "string",
            "enum": [
                "supported",
                "not_supported",
                "ambiguous",
            ],
        },
        "reason": {"type": "string"},
        "counterevidence": {"type": "string"},
    },
    "required": [
        "verdict",
        "reason",
        "counterevidence",
    ],
}


def validate_verdict(raw):
    if not isinstance(raw, dict):
        raise CE4SemanticContractError("Resultado no es objeto")

    if set(raw) != set(VERDICT_SCHEMA["required"]):
        raise CE4SemanticContractError("Campos invalidos")

    if raw["verdict"] not in (
        "supported",
        "not_supported",
        "ambiguous",
    ):
        raise CE4SemanticContractError("Veredicto invalido")

    for field in ("reason", "counterevidence"):
        if not isinstance(raw[field], str):
            raise CE4SemanticContractError(
                "Campo de texto invalido"
            )

    if not raw["reason"].strip():
        raise CE4SemanticContractError(
            "Falta justificacion"
        )

    return dict(raw)


def semantic_verdict(
    *,
    stage,
    original,
    quote,
    condition,
    component,
    rubric_version,
    prompt_version,
    provider=None,
    model=None,
    runner=None,
    cache_operation=None,
):
    if stage not in ("verification", "reconciliation"):
        raise CE4SemanticContractError("Etapa invalida")

    if not all(
        isinstance(x, str) and x.strip()
        for x in (
            original,
            quote,
            condition,
            component,
            rubric_version,
            prompt_version,
        )
    ):
        raise CE4SemanticContractError("Entrada incompleta")

    if quote not in original:
        raise CE4SemanticContractError(
            "Cita no es literal"
        )

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    prompt = (
        "EvalIA CE4. Eres un revisor semantico "
        "independiente. No asignes puntajes. "
        "Comprueba la proposicion con el texto "
        "completo, identifica contraevidencia "
        "y evita inferencias no sustentadas. "
        "Devuelve supported, not_supported "
        "o ambiguous. "
        "Etapa: " + stage
        + "\nComponente: " + component
        + "\nTexto: " + json.dumps(
            original, ensure_ascii=False
        )
        + "\nCita: " + json.dumps(
            quote, ensure_ascii=False
        )
        + "\nProposicion: " + json.dumps(
            condition, ensure_ascii=False
        )
    )

    inputs = {
        "original": original,
        "quote": quote,
        "condition": condition,
        "component": component,
        "prompt": prompt,
    }

    def execute():
        return (runner or run_structured_semantic)(
            prompt=prompt,
            schema=VERDICT_SCHEMA,
            provider=identity["provider"],
            model=identity["model"],
        )

    operation = cache_operation or cached_semantic_operation

    result = operation(
        extractor="ce4-" + stage,
        extractor_version=IDENTITY_VERSION,
        model=identity["model"],
        prompt_version=prompt_version,
        schema_version="ce4-verdict-schema-1",
        parameters={
            "provider": identity["provider"],
            "rubric_version": rubric_version,
            "component": component,
            "stage": stage,
        },
        inputs=inputs,
        execute=execute,
        validate_result=validate_verdict,
    )

    # Revalidar tambien los cache hits.
    validated = validate_verdict(result)

    if (
        stage == "reconciliation"
        and validated["verdict"] == "supported"
        and validated["counterevidence"].strip()
    ):
        raise CE4SemanticContractError(
            "Reconciliacion contradicha por contraevidencia"
        )

    return validated
