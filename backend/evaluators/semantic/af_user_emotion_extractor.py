# -*- coding: utf-8 -*-
"""
EvalIA — Extractor semántico del Estado Emocional del usuario.

Arquitectura:
- CURRENT_USER y PRIOR_USER se analizan por separado.
- El proveedor semántico interpreta únicamente el contenido de una fuente.
- Python asigna de forma determinista:
    - source;
    - identificadores;
    - verificación de evidencia literal.
- El entailment utiliza únicamente la fuente correspondiente como
  contexto local autorizado.

NO:
- asigna puntuaciones EvalIA;
- decide aplicabilidad de AF3 o AF7;
- determina interferencia activación -> acción.
"""

from __future__ import annotations

from typing import Any

from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_literal_evidence import recover_literal_quote
from .af_semantic_entailment import validate_semantic_entailment
from .af_user_emotion_prompt import build_user_emotion_prompt
from .af_user_emotion_schema import AF_USER_EMOTION_SCHEMA
from backend.evaluators.ansiedad_semantic.private_cache import cached_semantic_operation
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)


DEFAULT_TIMEOUT_SECONDS = 600

USER_EMOTION_EXTRACTOR_VERSION = "3.2.0"
USER_EMOTION_PROMPT_VERSION = "2.1.0"
USER_EMOTION_SCHEMA_VERSION = "2.0.0"

MAX_OUTPUT_TOKENS = 4096

_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]


class AFUserEmotionExtractorError(RuntimeError):
    """Error controlado del extractor semántico de Estado Emocional."""


def _extract_single_source(
    *,
    text: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Extrae distress y activation de UNA sola fuente textual.

    El modelo no conoce ni decide si la fuente corresponde a
    CURRENT_USER o PRIOR_USER.
    """

    if not text.strip():
        return {
            "distress": [],
            "activation": [],
        }

    prompt = build_user_emotion_prompt(text=text)

    try:
        result = run_structured_semantic(
            prompt=prompt,
            schema=AF_USER_EMOTION_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AFUserEmotionExtractorError(
            "Error ejecutando el proveedor semántico "
            f"{provider!r} con el modelo {model!r} "
            f"para Estado Emocional: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise AFUserEmotionExtractorError(
            "La extracción de Estado Emocional no produjo un objeto JSON."
        )

    for category in ("distress", "activation"):
        items = result.get(category)

        if not isinstance(items, list):
            raise AFUserEmotionExtractorError(
                f"La categoría {category!r} no contiene una lista válida."
            )

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise AFUserEmotionExtractorError(
                    f"Elemento inválido en {category}[{index}]."
                )

            description = item.get("description")
            evidence = item.get("evidence")

            if not isinstance(description, str) or not description.strip():
                raise AFUserEmotionExtractorError(
                    f"Descripción inválida en {category}[{index}]."
                )

            if not isinstance(evidence, dict):
                raise AFUserEmotionExtractorError(
                    f"Falta evidencia estructurada en {category}[{index}]."
                )

            quote = evidence.get("quote")

            if not isinstance(quote, str) or not quote.strip():
                raise AFUserEmotionExtractorError(
                    f"Cita vacía o inválida en {category}[{index}]."
                )

    return result


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
    A?ade la procedencia conocida por Python.

    Conserva evidencia exacta cuando ya es literal. Si no lo es,
    intenta recuperar exclusivamente una cita literal de la fuente
    que sostenga el mismo hecho material. Toda evidencia recuperada
    vuelve a verificarse literalmente antes de continuar.
    """

    output: dict[str, list[dict[str, Any]]] = {
        "distress": [],
        "activation": [],
    }

    for category in ("distress", "activation"):
        for index, item in enumerate(result[category]):
            quote = item["evidence"]["quote"]

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

            if not check.valid:
                recovered = recover_literal_quote(
                    quote=quote,
                    context=source_text,
                    provider=provider,
                    model=model,
                    timeout=timeout,
                )

                if recovered is None:
                    raise AFUserEmotionExtractorError(
                        f"Evidencia literal inv?lida en {category}[{index}] "
                        "y no pudo recuperarse con equivalencia sem?ntica "
                        "estricta. "
                        f"Fuente real: {source.value!r}. "
                        f"Raz?n original: {check.reason}. "
                        f"Evidencia: {quote!r}."
                    )

                final_check = verify(recovered)

                if not final_check.valid:
                    raise AFUserEmotionExtractorError(
                        f"Evidencia recuperada inv?lida en "
                        f"{category}[{index}]. "
                        f"Fuente real: {source.value!r}. "
                        f"Raz?n: {final_check.reason}. "
                        f"Evidencia recuperada: {recovered!r}."
                    )

                quote = recovered

            output[category].append(
                {
                    "description": item["description"].strip(),
                    "evidence": {
                        "quote": quote.strip(),
                        "source": source.value,
                    },
                }
            )

    return output


def _local_context_for_emotion_item(
    *,
    item: dict[str, Any],
    current_user: str,
    prior_user: str,
) -> str:
    """
    Obtiene únicamente la fuente textual correspondiente a la evidencia.

    No mezcla turnos.
    No incorpora respuestas de IA.
    No incorpora información futura.
    """

    evidence = item.get("evidence")

    if not isinstance(evidence, dict):
        raise AFUserEmotionExtractorError(
            "El elemento emocional no contiene evidencia estructurada."
        )

    source_value = evidence.get("source")

    if source_value == EvidenceSource.CURRENT_USER.value:
        return current_user

    if source_value == EvidenceSource.PRIOR_USER.value:
        return prior_user

    raise AFUserEmotionExtractorError(
        f"Fuente emocional no permitida: {source_value!r}."
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
    Valida que la evidencia literal sustente semánticamente la
    descripción propuesta por el extractor.

    Política:
    - supported:
        conserva el candidato como evidencia confirmada;
    - not_supported:
        excluye el candidato;
    - ambiguous:
        conserva el candidato, marcado como ambiguo.

    Esta función NO:
    - asigna puntuaciones AF;
    - decide aplicabilidad;
    - convierte ambigüedad en evidencia confirmada.
    """

    output: dict[str, list[dict[str, Any]]] = {
        "distress": [],
        "activation": [],
    }

    for category in ("distress", "activation"):
        for item in result[category]:
            quote = item["evidence"]["quote"]
            description = item["description"]

            local_context = _local_context_for_emotion_item(
                item=item,
                current_user=current_user,
                prior_user=prior_user,
            )

            validation = validate_semantic_entailment(
                evidence=quote,
                local_context=local_context,
                proposition=description,
                provider=provider,
                model=model,
                timeout=timeout,
            )

            status = validation["status"]
            reason = validation["reason"]

            if status == "not_supported":
                continue

            output[category].append(
                {
                    "description": description,
                    "evidence": item["evidence"],
                    "semantic_validation": {
                        "status": status,
                        "reason": reason,
                    },
                }
            )

    return output


def _assign_ids(
    result: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """
    Asigna identificadores consecutivos de forma determinista después
    de combinar las fuentes.
    """

    output: dict[str, list[dict[str, Any]]] = {
        "distress": [],
        "activation": [],
    }

    for category in ("distress", "activation"):
        for number, item in enumerate(result[category], start=1):
            output[category].append(
                {
                    "id": f"{category}_{number}",
                    "description": item["description"],
                    "evidence": item["evidence"],
                    "semantic_validation": item["semantic_validation"],
                }
            )

    return output


def extract_user_emotion(
    *,
    current_user: str,
    prior_user: str = "",
    provider: str = SEMANTIC_PROVIDER,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Extrae Estado Emocional del usuario.

    Pipeline:
    fuente -> extracción -> evidencia literal -> entailment contextual V2
           -> IDs deterministas -> caché.

    Solo la información ya verificada y validada se almacena.
    Esta función NO decide aplicabilidad ni puntuaciones AF.
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
        raise AFUserEmotionExtractorError(
            "provider no puede estar vacío."
        )

    if not selected_model:
        raise AFUserEmotionExtractorError(
            "model no puede estar vacío."
        )

    empty_result = {
        "distress": [],
        "activation": [],
    }

    if not normalized_current and not normalized_prior:
        return empty_result

    def execute() -> dict[str, Any]:
        current_raw = _extract_single_source(
            text=normalized_current,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        current_verified = _attach_source_and_verify(
            result=current_raw,
            source=EvidenceSource.CURRENT_USER,
            source_text=normalized_current,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        prior_raw = _extract_single_source(
            text=normalized_prior,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        prior_verified = _attach_source_and_verify(
            result=prior_raw,
            source=EvidenceSource.PRIOR_USER,
            source_text=normalized_prior,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        combined = {
            "distress": (
                current_verified["distress"]
                + prior_verified["distress"]
            ),
            "activation": (
                current_verified["activation"]
                + prior_verified["activation"]
            ),
        }

        semantically_validated = _validate_semantic_support(
            result=combined,
            current_user=normalized_current,
            prior_user=normalized_prior,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        return _assign_ids(semantically_validated)

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(result, dict):
            raise AFUserEmotionExtractorError(
                "El resultado validado debe ser un objeto."
            )

        expected = {
            "distress",
            "activation",
        }

        if set(result) != expected:
            raise AFUserEmotionExtractorError(
                "El resultado contiene categorías inesperadas."
            )

        for category in expected:
            items = result[category]

            if not isinstance(items, list):
                raise AFUserEmotionExtractorError(
                    f"{category} debe ser una lista."
                )

            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    raise AFUserEmotionExtractorError(
                        f"Elemento inválido en {category}[{index}]."
                    )

                validation = item.get("semantic_validation")

                if not isinstance(validation, dict):
                    raise AFUserEmotionExtractorError(
                        f"Falta validación semántica en "
                        f"{category}[{index}]."
                    )

                if validation.get("status") not in {
                    "supported",
                    "ambiguous",
                }:
                    raise AFUserEmotionExtractorError(
                        f"Estado semántico inválido en "
                        f"{category}[{index}]."
                    )

        return result

    return cached_semantic_operation(
        extractor="af_user_emotion",
        extractor_version=USER_EMOTION_EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=USER_EMOTION_PROMPT_VERSION,
        schema_version=USER_EMOTION_SCHEMA_VERSION,
        parameters={
            "provider": selected_provider,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "entailment_contract": "local_context_v2",
        },
        inputs={
            "current_user": normalized_current,
            "prior_user": normalized_prior,
        },
        execute=execute,
        validate_result=validate_result,
    )


def emotion_item_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Solo supported constituye evidencia positiva.

    ambiguous se conserva para trazabilidad,
    pero NO activa aplicabilidad AF.
    """

    validation = item.get("semantic_validation")

    return bool(
        isinstance(validation, dict)
        and validation.get("status") == "supported"
    )