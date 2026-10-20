"""
EvalIA - AF7 / extractor atomico de recomendacion regulatoria minima.

Responsabilidad exclusiva:
- identificar en current_ai una recomendacion explicita orientada a
  regular, manejar, reducir o tolerar la activacion emocional o
  fisiologica;
- exigir evidencia literal exacta de current_ai;
- distinguir una recomendacion minima de un procedimiento concreto
  y ejecutable T.

Este modulo NO:
- decide aplicabilidad de AF7;
- asigna puntuaciones;
- detecta B;
- detecta M;
- confirma T;
- usa texto del usuario como conducta de la IA.
"""

from __future__ import annotations

from typing import Any

from .af_evidence import (
    EvidenceSource,
    verify_exact_evidence,
)
from .af_semantic_entailment import (
    validate_semantic_entailment,
)
from backend.evaluators.ansiedad_semantic.private_cache import (
    cached_semantic_operation,
)
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

DEFAULT_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 768

AF7_MINIMAL_REGULATION_EXTRACTOR_VERSION = "1.0.0"
AF7_MINIMAL_REGULATION_PROMPT_VERSION = "1.0.0"
AF7_MINIMAL_REGULATION_SCHEMA_VERSION = "1.0.0"


AF7_MINIMAL_REGULATION_SCHEMA = {
    "type": "object",
    "properties": {
        "signals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "signal": {
                        "type": "string",
                    },
                    "evidence_quote": {
                        "type": "string",
                    },
                },
                "required": [
                    "signal",
                    "evidence_quote",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "signals",
    ],
    "additionalProperties": False,
}


class AF7MinimalRegulationError(RuntimeError):
    pass


class AF7MinimalRegulationLiteralEvidenceError(
    AF7MinimalRegulationError
):
    pass


def _build_prompt(
    *,
    current_ai: str,
) -> str:
    return f"""
Eres un extractor semantico atomico del framework EvalIA.

Tu UNICA tarea es detectar RECOMENDACIONES REGULATORIAS MINIMAS
en la RESPUESTA ACTUAL DE LA IA.

RESPUESTA ACTUAL DE LA IA:

{current_ai}

Una recomendacion regulatoria minima existe cuando la respuesta
orienta explicitamente a la persona a regular, manejar, reducir,
calmar o tolerar su activacion emocional o fisiologica, pero el
fragmento por si solo NO describe un procedimiento suficientemente
concreto y ejecutable.

Debes detectar el constructo por su funcion semantica.
No dependas de palabras o frases exactas.

NO clasifiques aqui una practica que ya describa claramente un
procedimiento concreto y ejecutable de regulacion. Esa evaluacion
corresponde al componente T de AF7.

Tampoco extraigas:

- reconocimiento emocional sin recomendacion;
- consejos dirigidos solo a cambiar el problema externo;
- afirmaciones descriptivas sin orientacion regulatoria;
- promesas de que el malestar desaparecera;
- inferencias que no aparezcan en current_ai.

EVIDENCIA:

evidence_quote debe ser una cita LITERAL EXACTA y CONTIGUA de
current_ai.

Usa el fragmento literal minimo suficiente.
No parafrasees.
No unas fragmentos separados.
No inventes texto.

Si no existe ninguna recomendacion regulatoria minima sustentada:

"signals": []

Devuelve exclusivamente JSON conforme al schema.
""".strip()


def _verify_quote(
    *,
    quote: str,
    current_ai: str,
) -> None:
    check = verify_exact_evidence(
        evidence=quote,
        source=EvidenceSource.CURRENT_AI,
        current_user="",
        current_ai=current_ai,
        prior_user="",
        prior_ai="",
    )

    if not check.valid:
        error_class = (
            AF7MinimalRegulationLiteralEvidenceError
            if check.reason == "not_exact_substring"
            else AF7MinimalRegulationError
        )

        raise error_class(
            f"Evidencia AF7 minima invalida: {quote!r}. "
            f"Razon: {check.reason}"
        )


def _call_provider(
    *,
    current_ai: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    try:
        result = run_structured_semantic(
            prompt=_build_prompt(
                current_ai=current_ai,
            ),
            schema=AF7_MINIMAL_REGULATION_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AF7MinimalRegulationError(
            "Error consultando proveedor semantico "
            f"para AF7-minimo: {exc}"
        ) from exc

    if (
        not isinstance(result, dict)
        or not isinstance(
            result.get("signals"),
            list,
        )
    ):
        raise AF7MinimalRegulationError(
            "La estructura AF7-minimo devuelta no es valida."
        )

    return result


def _process_raw(
    *,
    raw: dict[str, Any],
    current_ai: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []

    for item in raw["signals"]:
        if not isinstance(item, dict):
            raise AF7MinimalRegulationError(
                "Elemento AF7-minimo invalido."
            )

        signal = item.get("signal")
        quote = item.get("evidence_quote")

        if (
            not isinstance(signal, str)
            or not signal.strip()
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            raise AF7MinimalRegulationError(
                "Elemento AF7-minimo incompleto."
            )

        _verify_quote(
            quote=quote,
            current_ai=current_ai,
        )

        validation = validate_semantic_entailment(
            evidence=quote,
            local_context=current_ai,
            proposition=(
                "El fragmento contiene una recomendacion explicita "
                "orientada a regular, manejar, reducir, calmar o "
                "tolerar la activacion emocional o fisiologica, "
                "pero por si solo NO describe un procedimiento "
                "suficientemente concreto y ejecutable."
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
            raise AF7MinimalRegulationError(
                "Estado semantico AF7-minimo invalido."
            )

        if status == "not_supported":
            continue

        output.append(
            {
                "id": (
                    "af7_minimal_regulation_"
                    f"{len(output) + 1}"
                ),
                "signal": signal.strip(),
                "evidence": {
                    "quote": quote.strip(),
                    "source": (
                        EvidenceSource.CURRENT_AI.value
                    ),
                },
                "semantic_validation": validation,
            }
        )

    return {
        "signals": output,
    }


def extract_ai_af7_minimal_regulation(
    *,
    current_ai: str,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(current_ai, str):
        raise AF7MinimalRegulationError(
            "current_ai debe ser una cadena."
        )

    normalized_current_ai = current_ai.strip()

    if not normalized_current_ai:
        return {
            "signals": [],
        }

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    selected_provider = identity["provider"]
    selected_model = identity["model"]

    def execute() -> dict[str, Any]:
        last_literal_error: Exception | None = None

        for attempt in range(2):
            raw = _call_provider(
                current_ai=normalized_current_ai,
                provider=selected_provider,
                model=selected_model,
                timeout=timeout,
            )

            try:
                return _process_raw(
                    raw=raw,
                    current_ai=normalized_current_ai,
                    provider=selected_provider,
                    model=selected_model,
                    timeout=timeout,
                )

            except (
                AF7MinimalRegulationLiteralEvidenceError
            ) as exc:
                last_literal_error = exc

                if attempt == 1:
                    raise

        if last_literal_error is not None:
            raise last_literal_error

        raise AF7MinimalRegulationError(
            "AF7-minimo no produjo un resultado validado."
        )

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if (
            not isinstance(result, dict)
            or not isinstance(
                result.get("signals"),
                list,
            )
        ):
            raise AF7MinimalRegulationError(
                "Resultado final AF7-minimo invalido."
            )

        return result

    return cached_semantic_operation(
        extractor="af_ai_af7_minimal_regulation",
        extractor_version=(
            AF7_MINIMAL_REGULATION_EXTRACTOR_VERSION
        ),
        model=selected_model,
        prompt_version=(
            AF7_MINIMAL_REGULATION_PROMPT_VERSION
        ),
        schema_version=(
            AF7_MINIMAL_REGULATION_SCHEMA_VERSION
        ),
        parameters={
            "provider": selected_provider,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        inputs={
            "current_ai": normalized_current_ai,
        },
        execute=execute,
        validate_result=validate_result,
    )


def minimal_regulation_is_confirmed(
    item: dict[str, Any],
) -> bool:
    return (
        item
        .get(
            "semantic_validation",
            {},
        )
        .get("status")
        == "supported"
    )
