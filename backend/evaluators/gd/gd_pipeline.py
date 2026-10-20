"""Orquestación aislada de la familia GD.

Las discrepancias se bloquean por indicador.
No altera módulos de otras familias ni usa regex.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .gd_schemas import GDContext, GDResult
from .gd_extractor import extract_gd
from .gd_verifier import verify_gd, verification_status
from .gd_applicability_semantic import (
    review_gd_applicability,
    reconcile_conditional_gd,
)
from .gd_level_semantic import (
    classify_gd_levels,
    verify_gd_levels,
    resolve_verified_levels,
)
from .gd_rubric import GD_RUBRIC
from .gd_level_cache import (
    make_level_key,
    get_validated_level,
    set_validated_level,
)


@dataclass(frozen=True)
class GDPipelineReport:
    results: dict[str, GDResult]
    extraction: dict[str, Any]
    component_verification: dict[str, Any]
    component_status: dict[str, str]
    applicability_reviews: tuple
    applicability: dict[str, str]
    classification: dict[str, Any]
    level_verification: dict[str, Any]


def run_gd_pipeline(
    context: GDContext,
    *,
    provider: str = "openai",
    model: str | None = None,
    use_cache: bool = True,
) -> GDPipelineReport:
    """Primera pasada GD con bloqueo por discrepancia."""

    extraction = extract_gd(
        context,
        provider=provider,
        model=model,
        use_cache=use_cache,
    )

    component_verification = verify_gd(
        context,
        extraction,
        provider=provider,
        model=model,
        use_cache=use_cache,
    )

    component_status = verification_status(
        extraction,
        component_verification,
    )

    reviews = review_gd_applicability(
        context,
        provider=provider,
        model=model,
        use_cache=use_cache,
    )

    applicability = reconcile_conditional_gd(
        extraction,
        reviews,
    )

    rubric_identity = {
        code: {
            'question': item.question,
            'applicability': item.applicability,
            'scoring_type': item.scoring_type,
        }
        for code, item in GD_RUBRIC.items()
    }
    level_key = make_level_key(
        stage='classification',
        context=context,
        provider=provider,
        model=model,
        rubric=rubric_identity,
        schema_version='GD-LEVEL-SCHEMA-2',
        prompt_version='GD-LEVEL-PROMPT-1',
    )
    classification = (
        get_validated_level(
            level_key,
            stage='classification',
            context=context,
        ) if use_cache else None
    )
    if classification is None:
            classification = classify_gd_levels(
                context,
                provider=provider,
                model=model,
            )
    verification_key = make_level_key(
        stage='verification',
        context=context,
        provider=provider,
        model=model,
        rubric=rubric_identity,
        schema_version='GD-LEVEL-VERIFY-1',
        prompt_version='GD-LEVEL-VERIFY-PROMPT-1',
        classification=classification,
    )
    level_verification = (
        get_validated_level(
            verification_key,
            stage='verification',
        ) if use_cache else None
    )
    if level_verification is None:
            level_verification = verify_gd_levels(
                context,
                classification,
                provider=provider,
                model=model,
            )
    try:
        if use_cache and all(
            item['verdict'] == 'supported'
            for item in level_verification['verdicts']
        ):
            set_validated_level(
                level_key,
                classification,
                stage='classification',
                context=context,
            )
            set_validated_level(
                verification_key,
                level_verification,
                stage='verification',
            )
    except (ValueError, TypeError, KeyError):
        # Una entrada no cacheable no altera la evaluaci?n.
        pass

    results = resolve_verified_levels(
        context,
        classification,
        level_verification,
        applicability=applicability,
    )

    for code in GD_RUBRIC:
        result = results[code]

        # N/A condicional verificado no necesita
        # evidencia de cumplimiento de m?rito.
        if (
            code in ("GD5", "GD7")
            and applicability.get(code) == "NA"
            and result.status == "NA"
        ):
            continue

        if component_status.get(code) != "VERIFIED":
            results[code] = GDResult(
                code=code,
                status="BLOCKED",
                score=None,
                reason=(
                    "Verificaci?n independiente de componentes "
                    "no confirmada."
                ),
            )

    return GDPipelineReport(
        results=results,
        extraction=extraction,
        component_verification=component_verification,
        component_status=component_status,
        applicability_reviews=reviews,
        applicability=applicability,
        classification=classification,
        level_verification=level_verification,
    )
