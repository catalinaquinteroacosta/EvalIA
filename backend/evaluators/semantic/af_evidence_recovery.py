"""
EvalIA - Recuperación controlada de evidencia literal.

Responsabilidad:
- Recuperar una cita literal desde un texto fuente cuando un extractor
  semántico identificó correctamente un componente pero propuso una
  evidencia que no es una subcadena exacta.
- Mantener la evidencia final completamente trazable.

Este módulo NO:
- asigna puntuaciones;
- decide aplicabilidad;
- interpreta rúbricas AF;
- acepta evidencia aproximada como evidencia literal;
- modifica el texto fuente.
"""

from __future__ import annotations

from typing import Any

from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_semantic_entailment import validate_semantic_entailment
from backend.evaluators.ansiedad_semantic.private_cache import cached_semantic_operation
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)


EVIDENCE_RECOVERY_EXTRACTOR_VERSION = "1.1.0"
EVIDENCE_RECOVERY_PROMPT_VERSION = "1.0.0"
EVIDENCE_RECOVERY_SCHEMA_VERSION = "1.0.0"

DEFAULT_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 1024


class AFEvidenceRecoveryError(RuntimeError):
    """Error controlado de recuperación de evidencia."""


EVIDENCE_RECOVERY_SCHEMA = {
    "type": "object",
    "properties": {
        "found": {
            "type": "boolean",
        },
        "quote": {
            "type": ["string", "null"],
        },
        "reason": {
            "type": "string",
        },
    },
    "required": [
        "found",
        "quote",
        "reason",
    ],
    "additionalProperties": False,
}


def _build_prompt(
    *,
    source_text: str,
    proposition: str,
    proposed_evidence: str,
) -> str:
    return f"""
Eres un localizador de evidencia textual para EvalIA.

NO evalúas indicadores.
NO asignas puntuaciones.
NO completas información ausente.
NO parafraseas evidencia.

Tu única tarea es localizar dentro del TEXTO FUENTE una cita literal
que sustente la PROPOSICIÓN.

La evidencia propuesta por otro extractor puede ser inexacta y se
proporciona únicamente como pista semántica. NO debes copiarla si no
existe literalmente en el TEXTO FUENTE.

REGLAS OBLIGATORIAS:

1. quote debe ser una subcadena CONTIGUA y EXACTA del TEXTO FUENTE.
2. Está prohibido usar "..." o "…".
3. Está prohibido combinar fragmentos separados.
4. Está prohibido reconstruir, corregir o parafrasear el texto.
5. Usa la cita literal más corta que sustente completamente la
   PROPOSICIÓN.
6. Si no existe una cita literal suficiente, devuelve:
   found=false y quote=null.
7. Nunca inventes una cita para satisfacer la proposición.
8. El TEXTO FUENTE es la única fuente autorizada.

TEXTO FUENTE:
<<<
{source_text}
>>>

PROPOSICIÓN:
<<<
{proposition}
>>>

EVIDENCIA PROPUESTA COMO PISTA:
<<<
{proposed_evidence}
>>>

Devuelve exclusivamente JSON conforme al schema.
""".strip()


def _validate_raw_result(
    result: Any,
    *,
    source_text: str,
) -> dict[str, Any]:

    if not isinstance(result, dict):
        raise AFEvidenceRecoveryError(
            "La recuperación no produjo un objeto JSON."
        )

    found = result.get("found")
    quote = result.get("quote")
    reason = result.get("reason")

    if not isinstance(found, bool):
        raise AFEvidenceRecoveryError(
            "found debe ser boolean."
        )

    if not isinstance(reason, str) or not reason.strip():
        raise AFEvidenceRecoveryError(
            "reason debe ser texto no vacío."
        )

    if not found:
        if quote is not None:
            raise AFEvidenceRecoveryError(
                "Si found=false, quote debe ser null."
            )

        return {
            "found": False,
            "quote": None,
            "reason": reason.strip(),
        }

    if not isinstance(quote, str) or not quote.strip():
        raise AFEvidenceRecoveryError(
            "Si found=true, quote debe ser texto no vacío."
        )

    normalized_quote = quote.strip()

    check = verify_exact_evidence(
        evidence=normalized_quote,
        source=EvidenceSource.CURRENT_AI,
        current_user="",
        current_ai=source_text,
        prior_user="",
        prior_ai="",
    )

    if not check.valid:
        raise AFEvidenceRecoveryError(
            "El recuperador devolvió una cita no literal: "
            f"{normalized_quote!r}. Razón: {check.reason}"
        )

    return {
        "found": True,
        "quote": normalized_quote,
        "reason": reason.strip(),
    }


from backend.evaluators.semantic.af_literal_markdown_recovery import recover_markdown_literal

def recover_literal_evidence(
    *,
    source_text: str,
    proposition: str,
    proposed_evidence: str,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Recupera evidencia literal y exige además sustentación semántica.

    Solo status='supported' produce recovered=True.
    ambiguous y not_supported NO cuentan como evidencia positiva.
    """

    if not isinstance(source_text, str) or not source_text.strip():
        raise AFEvidenceRecoveryError(
            "source_text debe ser texto no vacío."
        )

    if not isinstance(proposition, str) or not proposition.strip():
        raise AFEvidenceRecoveryError(
            "proposition debe ser texto no vacío."
        )

    if not isinstance(proposed_evidence, str):
        raise AFEvidenceRecoveryError(
            "proposed_evidence debe ser str."
        )

    source_text = source_text.strip()
    proposition = proposition.strip()
    proposed_evidence = proposed_evidence.strip()

    deterministic_quote = recover_markdown_literal(
        source_text,
        proposed_evidence,
    )

    if deterministic_quote is not None:
        identity = get_semantic_identity(
            provider=provider,
            model=model,
        )

        semantic_validation = validate_semantic_entailment(
            evidence=deterministic_quote,
            local_context=source_text,
            proposition=proposition,
            provider=identity["provider"],
            model=identity["model"],
            timeout=timeout,
        )

        if semantic_validation["status"] == "supported":
            return {
                "recovered": True,
                "quote": deterministic_quote,
                "semantic_validation": semantic_validation,
                "reason": (
                    "Cita literal recuperada "
                    "determin?sticamente con Markdown."
                ),
            }

        return {
            "recovered": False,
            "quote": deterministic_quote,
            "semantic_validation": semantic_validation,
            "reason": (
                "Cita literal encontrada, pero sin "
                "sustentaci?n sem?ntica confirmada."
            ),
        }


    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    selected_provider = identity["provider"]
    selected_model = identity["model"]

    def execute() -> dict[str, Any]:
        try:
            return run_structured_semantic(
                prompt=_build_prompt(
                    source_text=source_text,
                    proposition=proposition,
                    proposed_evidence=proposed_evidence,
                ),
                schema=EVIDENCE_RECOVERY_SCHEMA,
                provider=selected_provider,
                model=selected_model,
                timeout=timeout,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )

        except SemanticProviderError as exc:
            raise AFEvidenceRecoveryError(
                "Error consultando el proveedor durante "
                f"la recuperación de evidencia: {exc}"
            ) from exc

    raw = cached_semantic_operation(
        extractor="af_evidence_recovery",
        extractor_version=EVIDENCE_RECOVERY_EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=EVIDENCE_RECOVERY_PROMPT_VERSION,
        schema_version=EVIDENCE_RECOVERY_SCHEMA_VERSION,
        parameters={
            "provider": selected_provider,
        },
        inputs={
            "source_text": source_text,
            "proposition": proposition,
            "proposed_evidence": proposed_evidence,
        },
        execute=execute,
        validate_result=lambda result: _validate_raw_result(
            result,
            source_text=source_text,
        ),
    )

    if not raw["found"]:
        return {
            "recovered": False,
            "quote": None,
            "semantic_validation": None,
            "reason": raw["reason"],
        }

    quote = raw["quote"]

    semantic_validation = validate_semantic_entailment(
        evidence=quote,
        local_context=source_text,
        proposition=proposition,
        provider=selected_provider,
        model=selected_model,
        timeout=timeout,
    )

    if semantic_validation["status"] != "supported":
        return {
            "recovered": False,
            "quote": quote,
            "semantic_validation": semantic_validation,
            "reason": (
                "La cita recuperada es literal, pero no quedó "
                "semánticamente confirmada."
            ),
        }

    return {
        "recovered": True,
        "quote": quote,
        "semantic_validation": semantic_validation,
        "reason": raw["reason"],
    }