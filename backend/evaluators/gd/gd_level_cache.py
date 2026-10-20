
"""Cach? sem?ntica aislada para niveles GD."""

from backend.evaluators.ansiedad_semantic.private_cache import (
    build_cache_key,
    semantic_cache,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
)

from .gd_level_semantic import (
    validate_levels,
    validate_level_verification,
)


CACHE_VERSION = "GD-LEVEL-CACHE-1.0.0"


def make_level_key(
    *,
    stage,
    context,
    provider,
    model,
    rubric,
    schema_version,
    prompt_version,
    classification=None,
):
    if stage not in ("classification", "verification"):
        raise ValueError("Etapa de cach? inv?lida.")

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    inputs = {
        "context": {
            "current_user": context.current_user,
            "current_response": context.current_response,
            "prior_history": [
                {"role": m.role, "text": m.text}
                for m in context.prior_history
            ],
        },
    }

    if stage == "verification":
        if classification is None:
            raise ValueError(
                "La verificaci?n requiere clasificaci?n."
            )
        inputs["classification"] = classification

    return build_cache_key(
        extractor="gd.level." + stage,
        extractor_version=CACHE_VERSION,
        model=identity["provider"] + ":" + identity["model"],
        prompt_version=prompt_version,
        schema_version=schema_version,
        parameters={"rubric": rubric},
        inputs=inputs,
    )


def get_validated_level(
    key,
    *,
    stage,
    context=None,
):
    cached = semantic_cache.get(key)

    if cached is None:
        return None

    try:
        if stage == "classification":
            if context is None:
                raise ValueError("Contexto requerido.")
            return validate_levels(cached, context)

        if stage == "verification":
            validated = validate_level_verification(cached)
            if not all(
                item["verdict"] == "supported"
                for item in validated["verdicts"]
            ):
                semantic_cache.delete(key)
                return None
            return validated

        raise ValueError("Etapa inv?lida.")

    except (ValueError, TypeError, KeyError):
        semantic_cache.delete(key)
        return None


def set_validated_level(
    key,
    value,
    *,
    stage,
    context=None,
):
    if stage == "classification":
        if context is None:
            raise ValueError("Contexto requerido.")
        validated = validate_levels(value, context)

    elif stage == "verification":
        validated = validate_level_verification(value)

        if not all(
            item["verdict"] == "supported"
            for item in validated["verdicts"]
        ):
            return False

    else:
        raise ValueError("Etapa inv?lida.")

    semantic_cache.set(key, validated)
    return True
