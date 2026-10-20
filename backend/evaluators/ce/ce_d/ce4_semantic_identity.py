
"""Identidad de operaciones semanticas CE4."""

from backend.evaluators.ansiedad_semantic.private_cache import (
    build_cache_key,
)

IDENTITY_VERSION = "ce4-semantic-identity-1.0.0"

STAGES = (
    "extraction",
    "verification",
    "reconciliation",
)


def ce4_cache_key(
    *,
    stage,
    provider,
    model,
    rubric_version,
    prompt_version,
    schema_version,
    inputs,
):
    if stage not in STAGES:
        raise ValueError("Etapa CE4 desconocida")

    if not isinstance(inputs, dict):
        raise ValueError("Entradas CE4 invalidas")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (
            provider,
            model,
            rubric_version,
            prompt_version,
            schema_version,
        )
    ):
        raise ValueError("Identidad CE4 incompleta")

    return build_cache_key(
        extractor="ce4-" + stage,
        extractor_version=IDENTITY_VERSION,
        model=model,
        prompt_version=prompt_version,
        schema_version=schema_version,
        parameters={
            "indicator": "CE4",
            "provider": provider,
            "rubric_version": rubric_version,
            "stage": stage,
        },
        inputs=inputs,
    )
