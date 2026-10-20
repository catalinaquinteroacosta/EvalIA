
"""Pipeline semantico exclusivo de CE4."""

from .ce4_provider_bridge import (
    evaluate_ce4_with_verifier,
    VERSION,
)
from .ce4_cached_extraction import extract_ce4_cached
from .ce4_semantic_operations import semantic_verdict


def evaluate_ce4_semantic(
    *,
    user_text,
    response_text,
    prior_context="",
    provider="openai",
    model=None,
    extraction_runner=None,
    verdict_runner=None,
    cache_operation=None,
):
    identity = {
        "provider": provider,
        "model": model,
    }

    try:
        extraction = extract_ce4_cached(
            user_text=user_text,
            response_text=response_text,
            prior_context=prior_context,
            provider=provider,
            model=model,
            runner=extraction_runner,
            cache_operation=cache_operation,
        )
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "score": None,
            "blocked_components": ["extraction"],
            "error_type": type(exc).__name__,
        }

    trace = []

    def review(stage, original, quote, condition, component):
        result = semantic_verdict(
            stage=stage,
            original=original,
            quote=quote,
            condition=condition,
            component=component,
            rubric_version=VERSION,
            prompt_version="ce4-review-v1",
            provider=provider,
            model=model,
            runner=verdict_runner,
            cache_operation=cache_operation,
        )
        trace.append({
            "stage": stage,
            "component": component,
            "verdict": result["verdict"],
            "reason": result["reason"],
            "counterevidence": result["counterevidence"],
        })
        return result["verdict"]

    claim_counter = [0]

    def verifier(original, quote, condition):
        if condition.startswith("CE4 APLICABILIDAD"):
            component = "applicability"
        elif "Verifica independientemente" in condition:
            component = "claim:" + str(claim_counter[0])
            claim_counter[0] += 1
        else:
            component = "rubric_execution"

        return review(
            "verification",
            original,
            quote,
            condition,
            component,
        )

    def reconciler(original, quote, condition, component):
        return review(
            "reconciliation",
            original,
            quote,
            condition,
            component,
        )

    try:
        result = evaluate_ce4_with_verifier(
            user_text=user_text,
            response_text=response_text,
            extraction=extraction,
            verify_claim=verifier,
            reconcile_claim=reconciler,
        )
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "score": None,
            "blocked_components": ["verification"],
            "error_type": type(exc).__name__,
            "trace": trace,
        }

    return {
        **result,
        "indicator": "CE4",
        "extraction_version": VERSION,
        "trace": trace,
    }
