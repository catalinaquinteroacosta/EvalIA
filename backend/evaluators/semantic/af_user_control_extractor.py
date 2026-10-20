# -*- coding: utf-8 -*-
"""
EvalIA — Extractor semántico del bloque de Controlabilidad.

Analiza únicamente:
- componentes modificables del estresor;
- aspectos no modificables en el momento actual;
- resultados externos o futuros no garantizables.

No asigna puntuaciones AF.
No decide N/A.
No analiza evitación, activación, regulación ni recursos previos.
"""

from __future__ import annotations

from typing import Any

from .af_user_control_prompt import build_user_control_prompt
from .af_user_control_schema import AF_USER_CONTROL_SCHEMA
from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_semantic_entailment import validate_semantic_entailment
from backend.evaluators.ansiedad_semantic.private_cache import cached_semantic_operation
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)


DEFAULT_TIMEOUT_SECONDS = 600

USER_CONTROL_EXTRACTOR_VERSION = "3.2.0"
USER_CONTROL_PROMPT_VERSION = "2.0.0"
USER_CONTROL_SCHEMA_VERSION = "2.0.0"

MAX_OUTPUT_TOKENS = 4096

_SEMANTIC_IDENTITY = get_semantic_identity()

SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]


class AFUserControlExtractorError(RuntimeError):
    """Error controlado del extractor semántico de Controlabilidad."""


def _verify_control_evidence(
    *,
    result: dict[str, Any],
    current_user: str,
    prior_user: str,
) -> dict[str, Any]:
    """
    Verifica programáticamente toda la evidencia literal producida
    por el bloque de Controlabilidad.

    Una extracción con evidencia inválida no puede continuar
    silenciosamente hacia las reglas de EvalIA.
    """

    categories = (
        "modifiable_components",
        "unmodifiable_now",
        "uncertain_outcomes",
    )

    for category in categories:
        items = result.get(category)

        if not isinstance(items, list):
            raise AFUserControlExtractorError(
                f"La categoría {category!r} no contiene una lista válida."
            )

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise AFUserControlExtractorError(
                    f"Elemento inválido en {category}[{index}]."
                )

            evidence = item.get("evidence")

            if not isinstance(evidence, dict):
                raise AFUserControlExtractorError(
                    f"Falta evidencia estructurada en {category}[{index}]."
                )

            quote = evidence.get("quote", "")
            source_value = evidence.get("source", "")

            try:
                source = EvidenceSource(source_value)

            except ValueError as exc:
                raise AFUserControlExtractorError(
                    f"Fuente de evidencia inválida en "
                    f"{category}[{index}]: {source_value!r}."
                ) from exc

            if source not in (
                EvidenceSource.CURRENT_USER,
                EvidenceSource.PRIOR_USER,
            ):
                raise AFUserControlExtractorError(
                    f"Fuente no permitida para contexto del usuario en "
                    f"{category}[{index}]: {source.value!r}."
                )

            check = verify_exact_evidence(
                evidence=quote,
                source=source,
                current_user=current_user,
                current_ai="",
                prior_user=prior_user,
                prior_ai="",
            )

            if not check.valid:
                raise AFUserControlExtractorError(
                    f"Evidencia literal inválida en {category}[{index}]. "
                    f"Razón: {check.reason}. "
                    f"Evidencia: {quote!r}."
                )

    return result


def _local_context_for_user_evidence(
    *,
    evidence: dict[str, Any],
    current_user: str,
    prior_user: str,
    category: str,
    index: int,
) -> str:
    """
    Devuelve únicamente el texto fuente autorizado de la evidencia.

    No mezcla current_user y prior_user.
    No incorpora respuestas de IA.
    No incorpora turnos futuros.
    """

    source_value = evidence.get("source")

    if source_value == EvidenceSource.CURRENT_USER.value:
        return current_user

    if source_value == EvidenceSource.PRIOR_USER.value:
        return prior_user

    raise AFUserControlExtractorError(
        f"Fuente inválida para contexto local en "
        f"{category}[{index}]: {source_value!r}."
    )


def _validate_control_semantics(
    *,
    result: dict[str, Any],
    current_user: str,
    prior_user: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Valida que la evidencia literal sustente realmente la
    clasificación semántica asignada por el extractor.

    Política:
    - supported: puede utilizarse como evidencia positiva;
    - ambiguous: se conserva para auditoría, pero NO confirma;
    - not_supported: se conserva para auditoría, pero NO confirma.

    No decide aplicabilidad ni puntuaciones AF.
    """

    propositions = {
        "modifiable_components": (
            "El referente identificado es una acci?n, decisi?n, "
            "conducta deliberada o circunstancia concreta relacionada "
            "con el problema descrito sobre la que existe un margen "
            "de actuaci?n sustentado por el texto. "
            "La evidencia debe identificar el referente. "
            "No se exige una declaraci?n literal de controlabilidad, "
            "pero tampoco se puede suponer una capacidad de actuaci?n "
            "que el contexto no sustenta. "
            "Realizar una conducta deliberada puede sustentar margen "
            "para decidir c?mo realizarla. "
            "Una dificultad para concentrarse, dormir, recordar u otra "
            "funci?n afectada no demuestra por s? sola capacidad "
            "voluntaria para modificar esa funci?n. "
            "No confundas intervenir sobre una conducta con garantizar "
            "sus resultados."
        ),
        "unmodifiable_now": (
            "El referente identificado es un hecho, l?mite o estado "
            "que el contexto establece como no modificable "
            "en el momento actual. "
            "No basta con que el referente sea una emoci?n, "
            "una dificultad o un acontecimiento mencionado."
        ),
        "uncertain_outcomes": (
            "El referente identificado es un resultado, desenlace "
            "o evaluaci?n futura cuya ocurrencia no est? establecida "
            "en el texto. La evidencia debe identificar el resultado "
            "concreto, no solamente la emoci?n asociada. "
            "Una evaluaci?n externa futura puede constituir "
            "un resultado incierto sin que el usuario declare "
            "literalmente que no puede garantizarla. "
            "No conviertas una preocupaci?n gen?rica en un resultado "
            "que el usuario no haya identificado. "
            "No confundas una predicci?n subjetiva con un hecho "
            "ya consumado."
        ),
    }

    for category, proposition_base in propositions.items():
        items = result.get(category)

        if not isinstance(items, list):
            raise AFUserControlExtractorError(
                f"La categoría {category!r} no contiene una lista válida."
            )

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise AFUserControlExtractorError(
                    f"Elemento inválido en {category}[{index}]."
                )

            description = item.get("description")
            evidence = item.get("evidence")

            if (
                not isinstance(description, str)
                or not description.strip()
                or not isinstance(evidence, dict)
            ):
                raise AFUserControlExtractorError(
                    f"Estructura inválida en {category}[{index}]."
                )

            quote = evidence.get("quote")

            if not isinstance(quote, str) or not quote.strip():
                raise AFUserControlExtractorError(
                    f"Evidencia vacía en {category}[{index}]."
                )

            local_context = _local_context_for_user_evidence(
                evidence=evidence,
                current_user=current_user,
                prior_user=prior_user,
                category=category,
                index=index,
            )

            validation = validate_semantic_entailment(
                evidence=quote.strip(),
                local_context=local_context,
                proposition=(
                    f"{proposition_base} "
                    f"El componente identificado es: {description.strip()}"
                ),
                provider=provider,
                model=model,
                timeout=timeout,
            )

            status = validation.get("status")

            if status not in {
                "supported",
                "ambiguous",
                "not_supported",
            }:
                raise AFUserControlExtractorError(
                    f"Estado semántico inválido en "
                    f"{category}[{index}]: {status!r}."
                )

            item["semantic_validation"] = validation

    return result


def control_item_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Solo supported constituye evidencia positiva para reglas AF.

    ambiguous y not_supported NO activan componentes.
    """

    validation = item.get("semantic_validation")

    return bool(
        isinstance(validation, dict)
        and validation.get("status") == "supported"
    )


def extract_user_control(
    *,
    current_user: str,
    prior_user: str = "",
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    provider: str = SEMANTIC_PROVIDER,
    model: str = SEMANTIC_MODEL,
) -> dict[str, Any]:
    """
    Extrae y valida semánticamente información de controlabilidad.

    El proveedor semántico identifica candidatos.
    EvalIA verifica evidencia literal y entailment semántico.
    No asigna puntuaciones ni decide N/A.
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
        raise AFUserControlExtractorError(
            "provider no puede estar vacío."
        )

    if not selected_model:
        raise AFUserControlExtractorError(
            "model no puede estar vacío."
        )

    empty_result = {
        "modifiable_components": [],
        "unmodifiable_now": [],
        "uncertain_outcomes": [],
    }

    if not normalized_current and not normalized_prior:
        return empty_result

    def execute() -> dict[str, Any]:
        prompt = build_user_control_prompt(
            current_user=normalized_current,
            prior_user=normalized_prior,
        )

        try:
            result = run_structured_semantic(
                prompt=prompt,
                schema=AF_USER_CONTROL_SCHEMA,
                provider=selected_provider,
                model=selected_model,
                timeout=timeout,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )

        except SemanticProviderError as exc:
            raise AFUserControlExtractorError(
                "No fue posible ejecutar el proveedor semántico "
                f"{selected_provider!r} con el modelo "
                f"{selected_model!r}: {exc}"
            ) from exc

        if not isinstance(result, dict):
            raise AFUserControlExtractorError(
                "La extracción de Controlabilidad debe ser un objeto JSON."
            )

        result = _verify_control_evidence(
            result=result,
            current_user=normalized_current,
            prior_user=normalized_prior,
        )

        return _validate_control_semantics(
            result=result,
            current_user=normalized_current,
            prior_user=normalized_prior,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(result, dict):
            raise AFUserControlExtractorError(
                "El resultado validado debe ser un objeto."
            )

        expected = {
            "modifiable_components",
            "unmodifiable_now",
            "uncertain_outcomes",
        }

        if set(result) != expected:
            raise AFUserControlExtractorError(
                "El resultado contiene categorías inesperadas."
            )

        for category in expected:
            items = result[category]

            if not isinstance(items, list):
                raise AFUserControlExtractorError(
                    f"{category} debe ser una lista."
                )

            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    raise AFUserControlExtractorError(
                        f"Elemento inválido en {category}[{index}]."
                    )

                validation = item.get("semantic_validation")

                if not isinstance(validation, dict):
                    raise AFUserControlExtractorError(
                        f"Falta validación semántica en "
                        f"{category}[{index}]."
                    )

                if validation.get("status") not in {
                    "supported",
                    "ambiguous",
                    "not_supported",
                }:
                    raise AFUserControlExtractorError(
                        f"Estado semántico inválido en "
                        f"{category}[{index}]."
                    )

        return result

    return cached_semantic_operation(
        extractor="af_user_control",
        extractor_version=USER_CONTROL_EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=USER_CONTROL_PROMPT_VERSION,
        schema_version=USER_CONTROL_SCHEMA_VERSION,
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