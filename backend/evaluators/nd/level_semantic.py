"""Evaluacion semantica independiente de descriptores ND.

Las consultas no devuelven puntuacion final.
Python valida los descriptores y resuelve el acuerdo.
"""

from __future__ import annotations

import json

from .contracts import ND_CODES, ND_QUESTIONS, TurnContext
from .level_contract import NDLevelFinding
from .level_agreement import (
    NDLevelAgreement,
    reconcile_level_findings,
)
from .official_rubric import load_official_nd_rubric
from .scoring_semantic import NDScoringEvidenceReport
from .semantic_engine import _context_payload


LEVEL_FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "level": {
            "type": "string",
            "enum": ["0", "1", "2", "3"],
        },
        "descriptor": {"type": "string"},
        "evidence_component_ids": {
            "type": "array",
            "items": {"type": "integer"},
        },
        "verification": {
            "type": "string",
            "enum": [
                "supported",
                "not_supported",
                "ambiguous",
            ],
        },
        "reason": {"type": "string"},
    },
    "required": [
        "level",
        "descriptor",
        "evidence_component_ids",
        "verification",
        "reason",
    ],
    "additionalProperties": False,
}


def _one_level_analysis(
    engine,
    indicator: str,
    context: TurnContext,
    report: NDScoringEvidenceReport,
    *,
    stage: str,
) -> NDLevelFinding:
    rubric = load_official_nd_rubric()

    components = [
        {
            "id": index,
            "claim": component.claim,
            "evidence": [
                {
                    "source": evidence.source,
                    "quote": evidence.quote,
                    "history_index": evidence.history_index,
                }
                for evidence in component.evidence
            ],
        }
        for index, component in enumerate(report.confirmed)
    ]

    payload = {
        "context": _context_payload(context),
        "indicator": indicator,
        "question": ND_QUESTIONS[indicator],
        "official_levels": rubric.levels,
        "verified_components": components,
    }

    if stage == "level_extract":
        instruction = (
            "Analiza la correspondencia entre los componentes "
            "verificados y los descriptores oficiales. "
            "No asignes una puntuacion final. "
            "No inventes evidencia ni criterios. "
            "Si no existe respaldo suficiente, indica "
            "verification=ambiguous."
        )
    elif stage == "level_verify":
        instruction = (
            "Realiza una comprobacion independiente de la "
            "correspondencia con los descriptores oficiales. "
            "No conoces el resultado de otra evaluacion. "
            "No asignes una puntuacion final. "
            "Examina contradicciones y explicaciones alternativas. "
            "Si no puedes demostrar la correspondencia, "
            "indica verification=ambiguous."
        )
    else:
        raise ValueError("Etapa de nivel invalida")

    prompt = (
        instruction
        + "\nResponde exclusivamente con el esquema JSON."
        + "\nDatos: "
        + json.dumps(payload, ensure_ascii=False)
    )

    result = engine._run(
        stage=stage,
        indicator=indicator,
        prompt=prompt,
        schema=LEVEL_FINDING_SCHEMA,
        inputs=payload,
    )

    raw = result.get("_uncached", result)

    if not isinstance(raw, dict):
        raise ValueError("Analisis de nivel invalido")

    finding = NDLevelFinding(
        indicator=indicator,
        level=raw["level"],
        descriptor=rubric.levels[raw["level"]],
        evidence_component_ids=tuple(
            raw["evidence_component_ids"]
        ),
        verification=raw["verification"],
        reason=raw["reason"],
    )

    from .level_contract import validate_level_finding

    valid = validate_level_finding(
        finding,
        confirmed_component_count=len(report.confirmed),
    )

    if valid:
        validated = {
            "level": finding.level,
            "descriptor": finding.descriptor,
            "evidence_component_ids": list(
                finding.evidence_component_ids
            ),
            "verification": finding.verification,
            "reason": finding.reason,
        }
        if "_uncached" in result:
            commit = getattr(engine, "_commit", None)
            if not callable(commit):
                raise RuntimeError(
                    "El motor produjo un resultado nuevo "
                    "pero no permite persistencia validada"
                )
            commit(result, validated)

    return finding


def assess_nd_level(
    engine,
    indicator: str,
    context: TurnContext,
    report: NDScoringEvidenceReport,
) -> NDLevelAgreement:
    if indicator not in ND_CODES:
        raise ValueError("Indicador ND invalido")

    if report.indicator != indicator:
        raise ValueError("Reporte de otro indicador")

    if report.status != "VERIFIED" or not report.confirmed:
        return NDLevelAgreement(
            indicator=indicator,
            status="BLOCKED",
            level=None,
            reason="No hay componentes confirmados suficientes",
            component_ids=(),
        )

    first = _one_level_analysis(
        engine, indicator, context, report,
        stage="level_extract",
    )

    second = _one_level_analysis(
        engine, indicator, context, report,
        stage="level_verify",
    )

    return reconcile_level_findings(
        first,
        second,
        confirmed_component_count=len(report.confirmed),
    )
