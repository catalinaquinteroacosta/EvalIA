
"""Extraccion CE4 con cache persistente validado."""

import json

from backend.evaluators.ansiedad_semantic.private_cache import (
    cached_semantic_operation,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
)

from .ce4_provider_bridge import (
    SCHEMA,
    VERSION,
    extract_ce4_draft,
)
from .ce4_semantic_identity import IDENTITY_VERSION


class CE4ExtractionError(ValueError):
    pass


def validate_extraction(raw):
    if not isinstance(raw, dict):
        raise CE4ExtractionError("Extraccion invalida")

    if set(raw) != set(SCHEMA["required"]):
        raise CE4ExtractionError("Campos incorrectos")

    for field in (
        "analysis_complete",
        "full_response_audited",
        "applicable",
    ):
        if type(raw[field]) is not bool:
            raise CE4ExtractionError("Estado invalido")

    evidence = raw["applicability_evidence"]

    if (
        not isinstance(evidence, dict)
        or set(evidence) != {
            "source", "quote", "interpretation"
        }
    ):
        raise CE4ExtractionError(
            "Evidencia de aplicabilidad invalida"
        )

    if evidence["source"] != "response":
        raise CE4ExtractionError("Fuente invalida")

    for field in ("quote", "interpretation"):
        if not isinstance(evidence[field], str):
            raise CE4ExtractionError("Texto invalido")

    claims = raw["claims"]

    if not isinstance(claims, list):
        raise CE4ExtractionError("Claims invalidas")

    for claim in claims:
        if (
            not isinstance(claim, dict)
            or set(claim) != {
                "source", "quote", "interpretation"
            }
        ):
            raise CE4ExtractionError("Claim invalida")

        if claim["source"] not in ("user", "response"):
            raise CE4ExtractionError("Fuente invalida")

        for field in ("quote", "interpretation"):
            if not isinstance(claim[field], str):
                raise CE4ExtractionError("Texto invalido")

    if raw["rubric_execution"] not in (
        "omitted_or_opposite",
        "minimal_generic",
        "adequate_limited",
        "clear_contextual_verifiable",
    ):
        raise CE4ExtractionError(
            "Descriptor invalido"
        )

    return dict(raw)


def extract_ce4_cached(
    *,
    user_text,
    response_text,
    prior_context="",
    provider="openai",
    model=None,
    runner=None,
    cache_operation=None,
):
    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    inputs = {
        "user_text": user_text,
        "response_text": response_text,
        "prior_context": prior_context,
    }

    def execute():
        draft = extract_ce4_draft(
            user_text=user_text,
            response_text=response_text,
            prior_context=prior_context,
            provider=identity["provider"],
            model=identity["model"],
            semantic_runner=runner,
        )

        return draft["extraction"]

    operation = cache_operation or cached_semantic_operation

    result = operation(
        extractor="ce4-extraction",
        extractor_version=IDENTITY_VERSION,
        model=identity["model"],
        prompt_version=VERSION,
        schema_version="ce4-extraction-schema-1",
        parameters={
            "provider": identity["provider"],
            "rubric_version": VERSION,
            "stage": "extraction",
        },
        inputs=inputs,
        execute=execute,
        validate_result=validate_extraction,
    )

    return validate_extraction(result)
