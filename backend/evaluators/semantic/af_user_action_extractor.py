# -*- coding: utf-8 -*-
"""
EvalIA — Extractor semántico del bloque Acción e Interferencia.

Arquitectura:
- CURRENT_USER y PRIOR_USER se analizan por separado.
- El proveedor semántico extrae acciones e interferencias de una sola fuente.
- Python determina la procedencia.
- Python verifica que cada cita exista literalmente.
- La sustentación semántica se valida con evidencia + contexto local autorizado.

NO:
- asigna puntuaciones AF;
- decide aplicabilidad de AF7;
- identifica activación emocional;
- establece todavía la relación activación -> interferencia.
"""

from __future__ import annotations

from typing import Any

from .af_literal_evidence import recover_literal_quote
from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_semantic_entailment import validate_semantic_entailment
from .af_user_action_prompt import build_user_action_prompt
from .af_user_action_schema import AF_USER_ACTION_SCHEMA
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)


DEFAULT_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 4096

USER_ACTION_EXTRACTOR_VERSION = "3.1.0"
USER_ACTION_PROMPT_VERSION = "2.0.0"
USER_ACTION_SCHEMA_VERSION = "2.0.0"

_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]


class AFUserActionExtractorError(RuntimeError):
    """Error controlado del extractor semántico de Acción e Interferencia."""


def _extract_single_source(
    *,
    text: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Extrae candidate_actions y action_interferences de una sola fuente.
    """

    if not text.strip():
        return {
            "candidate_actions": [],
            "action_interferences": [],
        }

    prompt = build_user_action_prompt(text=text)

    try:
        result = run_structured_semantic(
            prompt=prompt,
            schema=AF_USER_ACTION_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AFUserActionExtractorError(
            "Error ejecutando el proveedor semántico "
            f"{provider!r} con el modelo {model!r} "
            f"para Acción e Interferencia: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise AFUserActionExtractorError(
            "La extracción de Acción e Interferencia "
            "no produjo un objeto JSON."
        )

    candidate_actions = result.get("candidate_actions")
    action_interferences = result.get("action_interferences")

    if not isinstance(candidate_actions, list):
        raise AFUserActionExtractorError(
            "candidate_actions no contiene una lista válida."
        )

    if not isinstance(action_interferences, list):
        raise AFUserActionExtractorError(
            "action_interferences no contiene una lista válida."
        )

    for index, item in enumerate(candidate_actions):
        if not isinstance(item, dict):
            raise AFUserActionExtractorError(
                f"Elemento inválido en candidate_actions[{index}]."
            )

        description = item.get("description")
        evidence = item.get("evidence")

        if not isinstance(description, str) or not description.strip():
            raise AFUserActionExtractorError(
                f"Descripción inválida en candidate_actions[{index}]."
            )

        if not isinstance(evidence, dict):
            raise AFUserActionExtractorError(
                f"Falta evidencia en candidate_actions[{index}]."
            )

        quote = evidence.get("quote")

        if not isinstance(quote, str) or not quote.strip():
            raise AFUserActionExtractorError(
                f"Cita inválida en candidate_actions[{index}]."
            )

    for index, item in enumerate(action_interferences):
        if not isinstance(item, dict):
            raise AFUserActionExtractorError(
                f"Elemento inválido en action_interferences[{index}]."
            )

        action_description = item.get("action_description")
        interference_description = item.get(
            "interference_description"
        )
        evidence = item.get("evidence")

        if (
            not isinstance(action_description, str)
            or not action_description.strip()
        ):
            raise AFUserActionExtractorError(
                f"action_description inválida en "
                f"action_interferences[{index}]."
            )

        if (
            not isinstance(interference_description, str)
            or not interference_description.strip()
        ):
            raise AFUserActionExtractorError(
                f"interference_description inválida en "
                f"action_interferences[{index}]."
            )

        if not isinstance(evidence, dict):
            raise AFUserActionExtractorError(
                f"Falta evidencia en action_interferences[{index}]."
            )

        quote = evidence.get("quote")

        if not isinstance(quote, str) or not quote.strip():
            raise AFUserActionExtractorError(
                f"Cita inválida en action_interferences[{index}]."
            )

    return result


def _verify_or_recover_literal_evidence(
    *,
    quote: str,
    source: EvidenceSource,
    source_text: str,
    provider: str,
    model: str,
    timeout: int,
) -> str:
    """
    Conserva evidencia exacta cuando ya es literal.
    Si no lo es, intenta recuperar ?nicamente una cita literal
    sem?nticamente equivalente y vuelve a verificarla.
    """

    def verify(candidate: str):
        return verify_exact_evidence(
            evidence=candidate,
            source=source,
            current_user=(
                source_text
                if source == EvidenceSource.CURRENT_USER
                else ""
            ),
            current_ai="",
            prior_user=(
                source_text
                if source == EvidenceSource.PRIOR_USER
                else ""
            ),
            prior_ai="",
        )

    check = verify(quote)

    if check.valid:
        return quote.strip()

    recovered = recover_literal_quote(
        quote=quote,
        context=source_text,
        provider=provider,
        model=model,
        timeout=timeout,
    )

    if recovered is None:
        raise AFUserActionExtractorError(
            "La evidencia no es literal y no pudo "
            "recuperarse con equivalencia sem?ntica estricta. "
            f"Raz?n original: {check.reason}. "
            f"Evidencia: {quote!r}."
        )

    final_check = verify(recovered)

    if not final_check.valid:
        raise AFUserActionExtractorError(
            "La evidencia recuperada no super? la "
            "verificaci?n literal final. "
            f"Raz?n: {final_check.reason}. "
            f"Evidencia recuperada: {recovered!r}."
        )

    return recovered.strip()


def _attach_source_and_verify(
    *,
    result: dict[str, Any],
    source: EvidenceSource,
    source_text: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, list[dict[str, Any]]]:
    """
    Añade la fuente conocida por Python y verifica que las citas
    existan literalmente en el texto realmente analizado.
    """

    output: dict[str, list[dict[str, Any]]] = {
        "candidate_actions": [],
        "action_interferences": [],
    }

    for index, item in enumerate(result["candidate_actions"]):
        quote = item["evidence"]["quote"]

        try:
            literal_quote = _verify_or_recover_literal_evidence(
                quote=quote,
                source=source,
                source_text=source_text,
                provider=provider,
                model=model,
                timeout=timeout,
            )
        except AFUserActionExtractorError as exc:
            raise AFUserActionExtractorError(
                f"Evidencia literal inv?lida en "
                f"candidate_actions[{index}]. "
                f"Fuente real: {source.value!r}. "
                f"Evidencia: {quote!r}. "
                f"Detalle: {exc}"
            ) from exc

        output["candidate_actions"].append(
            {
                "description": item["description"].strip(),
                "evidence": {
                    "quote": literal_quote,
                    "source": source.value,
                },
            }
        )

    for index, item in enumerate(result["action_interferences"]):
        quote = item["evidence"]["quote"]

        try:
            literal_quote = _verify_or_recover_literal_evidence(
                quote=quote,
                source=source,
                source_text=source_text,
                provider=provider,
                model=model,
                timeout=timeout,
            )
        except AFUserActionExtractorError as exc:
            raise AFUserActionExtractorError(
                f"Evidencia literal inv?lida en "
                f"action_interferences[{index}]. "
                f"Fuente real: {source.value!r}. "
                f"Evidencia: {quote!r}. "
                f"Detalle: {exc}"
            ) from exc

        output["action_interferences"].append(
            {
                "action_description": (
                    item["action_description"].strip()
                ),
                "interference_description": (
                    item["interference_description"].strip()
                ),
                "evidence": {
                    "quote": literal_quote,
                    "source": source.value,
                },
            }
        )

    return output


def _local_context_for_item(
    *,
    item: dict[str, Any],
    current_user: str,
    prior_user: str,
) -> str:
    """
    Devuelve únicamente la fuente autorizada de la evidencia.

    No mezcla CURRENT_USER y PRIOR_USER.
    No incorpora respuestas de IA ni turnos futuros.
    """

    evidence = item.get("evidence")

    if not isinstance(evidence, dict):
        raise AFUserActionExtractorError(
            "El elemento no contiene evidencia estructurada."
        )

    source_value = evidence.get("source")

    if source_value == EvidenceSource.CURRENT_USER.value:
        return current_user

    if source_value == EvidenceSource.PRIOR_USER.value:
        return prior_user

    raise AFUserActionExtractorError(
        f"Fuente no permitida para contexto local: {source_value!r}."
    )


def _validate_semantic_support(
    *,
    result: dict[str, list[dict[str, Any]]],
    current_user: str,
    prior_user: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, list[dict[str, Any]]]:
    """
    Valida evidencia + contexto local -> proposición.

    Política:
    - supported: se conserva como evidencia confirmada;
    - ambiguous: se conserva para trazabilidad, pero NO debe
      considerarse evidencia confirmada aguas abajo;
    - not_supported: se descarta.

    Esta función NO establece la relación
    activación emocional -> interferencia.
    """

    output: dict[str, list[dict[str, Any]]] = {
        "candidate_actions": [],
        "action_interferences": [],
    }

    for item in result["candidate_actions"]:
        local_context = _local_context_for_item(
            item=item,
            current_user=current_user,
            prior_user=prior_user,
        )

        validation = validate_semantic_entailment(
            evidence=item["evidence"]["quote"],
            local_context=local_context,
            proposition=item["description"],
            provider=provider,
            model=model,
            timeout=timeout,
        )

        status = validation["status"]

        if status == "not_supported":
            continue

        validated_item = dict(item)
        validated_item["semantic_validation"] = validation
        output["candidate_actions"].append(validated_item)

    for item in result["action_interferences"]:
        proposition = (
            f"La acción '{item['action_description']}' presenta esta "
            f"interferencia: {item['interference_description']}"
        )

        local_context = _local_context_for_item(
            item=item,
            current_user=current_user,
            prior_user=prior_user,
        )

        validation = validate_semantic_entailment(
            evidence=item["evidence"]["quote"],
            local_context=local_context,
            proposition=proposition,
            provider=provider,
            model=model,
            timeout=timeout,
        )

        status = validation["status"]

        if status == "not_supported":
            continue

        validated_item = dict(item)
        validated_item["semantic_validation"] = validation
        output["action_interferences"].append(validated_item)

    return output


def _assign_ids(
    result: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Asigna IDs deterministas después de combinar y validar las fuentes.
    """

    output: dict[str, list[dict[str, Any]]] = {
        "candidate_actions": [],
        "action_interferences": [],
    }

    for number, item in enumerate(
        result["candidate_actions"],
        start=1,
    ):
        output["candidate_actions"].append(
            {
                "id": f"action_{number}",
                "description": item["description"],
                "evidence": item["evidence"],
                "semantic_validation": item["semantic_validation"],
            }
        )

    for number, item in enumerate(
        result["action_interferences"],
        start=1,
    ):
        output["action_interferences"].append(
            {
                "id": f"interference_{number}",
                "action_description": item["action_description"],
                "interference_description": item[
                    "interference_description"
                ],
                "evidence": item["evidence"],
                "semantic_validation": item["semantic_validation"],
            }
        )

    return output


def action_item_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Solo supported constituye evidencia positiva.

    ambiguous puede conservarse para auditoría,
    pero NO activa reglas aguas abajo.
    """

    validation = item.get("semantic_validation")

    return bool(
        isinstance(validation, dict)
        and validation.get("status") == "supported"
    )


def extract_user_action(
    *,
    current_user: str,
    prior_user: str = "",
    provider: str = SEMANTIC_PROVIDER,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:
    """
    Extracción pública del bloque Acción e Interferencia.

    CURRENT_USER y PRIOR_USER se procesan independientemente para
    preservar procedencia y evitar contaminación entre fuentes.

    Un elemento ambiguous se conserva para auditoría, pero su estado
    NO equivale a evidencia confirmada.
    """

    if not isinstance(current_user, str):
        raise TypeError("current_user debe ser str.")

    if not isinstance(prior_user, str):
        raise TypeError("prior_user debe ser str.")

    normalized_current = current_user.strip()
    normalized_prior = prior_user.strip()

    selected_provider = provider.strip().lower()
    selected_model = model.strip()

    if not selected_provider:
        raise AFUserActionExtractorError(
            "provider no puede estar vacío."
        )

    if not selected_model:
        raise AFUserActionExtractorError(
            "model no puede estar vacío."
        )

    combined: dict[str, list[dict[str, Any]]] = {
        "candidate_actions": [],
        "action_interferences": [],
    }

    sources = (
        (
            EvidenceSource.CURRENT_USER,
            normalized_current,
        ),
        (
            EvidenceSource.PRIOR_USER,
            normalized_prior,
        ),
    )

    for source, source_text in sources:
        if not source_text:
            continue

        raw = _extract_single_source(
            text=source_text,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        verified = _attach_source_and_verify(
            result=raw,
            source=source,
            source_text=source_text,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        validated = _validate_semantic_support(
            result=verified,
            current_user=normalized_current,
            prior_user=normalized_prior,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        combined["candidate_actions"].extend(
            validated["candidate_actions"]
        )
        combined["action_interferences"].extend(
            validated["action_interferences"]
        )

    return _assign_ids(combined)