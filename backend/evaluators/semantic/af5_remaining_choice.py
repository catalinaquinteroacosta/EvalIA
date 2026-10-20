"""
EvalIA - AF5 / extractor atomico de margen de accion restante (C).

Responsabilidad exclusiva:
- dado un limite L ya identificado, detectar en current_ai una accion
  o eleccion concreta que permanece disponible;
- exigir que esa accion sea compatible con L, no un intento de
  deshacer, negar o controlar el limite;
- exigir evidencia literal exacta de current_ai.

Este modulo NO:
- decide aplicabilidad;
- asigna puntuaciones;
- detecta L;
- detecta A;
- detecta resignacion o indefension;
- usa texto del usuario como conducta de la IA.
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


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

DEFAULT_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 768

AF5_REMAINING_CHOICE_EXTRACTOR_VERSION = "1.2.1"
AF5_REMAINING_CHOICE_PROMPT_VERSION = "1.1.0"
AF5_REMAINING_CHOICE_SCHEMA_VERSION = "1.0.0"


AF5_REMAINING_CHOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "choices": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "choice": {"type": "string"},
                    "evidence_quote": {"type": "string"},
                },
                "required": [
                    "choice",
                    "evidence_quote",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["choices"],
    "additionalProperties": False,
}


class AF5RemainingChoiceError(RuntimeError):
    pass


class AF5RemainingChoiceLiteralEvidenceError(
    AF5RemainingChoiceError
):
    pass


def _build_prompt(
    *,
    current_ai: str,
    limit_description: str,
) -> str:
    return f"""
Eres un extractor semantico atomico del framework EvalIA.

Tu UNICA tarea es detectar el componente C de AF5:
una ACCION O ELECCION CONCRETA que permanece disponible para la
persona y es COMPATIBLE con el limite L ya identificado.

LIMITE L YA IDENTIFICADO:

{limit_description}

RESPUESTA ACTUAL DE LA IA:

{current_ai}

C existe cuando CURRENT_AI expresa una accion o eleccion concreta
que la persona todavia puede realizar o decidir pese al limite L.

La accion debe:
- ser concreta y reconocible;
- permanecer disponible para la persona;
- ser compatible con L;
- no consistir en deshacer, negar o controlar como reversible
  aquello que L presenta como limite, hecho pasado o incertidumbre;
- representar un margen de accion o eleccion distinto de simplemente
  aceptar, permitir, tolerar, sostener o dejar estar el propio limite.
  La conducta de aceptacion/tolerancia pertenece al componente A y,
  por si sola, NO constituye C.

Ejemplo conceptual:

L:
"La nota todavia no se conoce."

CURRENT_AI:
"No sabemos aun la nota; puedes preparar la siguiente clase
mientras esperas."

C:
"puedes preparar la siguiente clase mientras esperas"

NO extraigas como C:
- deseos vagos sin accion reconocible;
- descripciones sin eleccion o conducta disponible;
- acciones imposibles bajo L;
- intentos de deshacer un hecho pasado;
- intentos de controlar como seguro un resultado incierto;
- texto aportado solamente por el usuario;
- inferencias que no aparezcan en CURRENT_AI.

No eval?es A.
No decidas puntuacion AF5.
No decidas aplicabilidad.
No completes componentes ausentes.

EVIDENCIA:

evidence_quote debe ser una cita LITERAL EXACTA y CONTIGUA de
CURRENT_AI.

Usa el fragmento literal minimo suficiente.
No parafrasees.
No unas fragmentos separados.
No inventes texto.

Si no existe ningun C sustentado:

"choices": []

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
            AF5RemainingChoiceLiteralEvidenceError
            if check.reason == "not_exact_substring"
            else AF5RemainingChoiceError
        )
        raise error_class(
            f"Evidencia AF5-C invalida: {quote!r}. "
            f"Razon: {check.reason}"
        )


def _call_provider(
    *,
    current_ai: str,
    limit_description: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    try:
        result = run_structured_semantic(
            prompt=_build_prompt(
                current_ai=current_ai,
                limit_description=limit_description,
            ),
            schema=AF5_REMAINING_CHOICE_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
    except SemanticProviderError as exc:
        raise AF5RemainingChoiceError(
            "Error consultando proveedor semantico para AF5-C: "
            f"{exc}"
        ) from exc

    if (
        not isinstance(result, dict)
        or not isinstance(result.get("choices"), list)
    ):
        raise AF5RemainingChoiceError(
            "La estructura AF5-C devuelta no es valida."
        )

    return result


def _process_raw(
    *,
    raw: dict[str, Any],
    current_ai: str,
    limit_description: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []

    for item in raw["choices"]:
        if not isinstance(item, dict):
            raise AF5RemainingChoiceError(
                "Elemento AF5-C invalido."
            )

        choice = item.get("choice")
        quote = item.get("evidence_quote")

        if (
            not isinstance(choice, str)
            or not choice.strip()
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            raise AF5RemainingChoiceError(
                "Elemento AF5-C incompleto."
            )

        _verify_quote(
            quote=quote,
            current_ai=current_ai,
        )

        validation = validate_semantic_entailment(
            evidence=quote,
            local_context=current_ai,
            proposition=(
                "El fragmento expresa una accion o eleccion concreta "
                "que permanece disponible para la persona y es "
                "compatible con el limite identificado. La accion "
                "NO puede consistir en deshacer, negar, eliminar, "
                "determinar o hacer controlable aquello que L presenta "
                "como hecho pasado o resultado incierto. "
                "Si L establece que un resultado todavia es incierto "
                "o desconocido, una accion que pretenda hacer que ese "
                "resultado aparezca, se determine, se conozca o quede "
                "asegurado mediante la propia accion NO es C. "
                "Si la accion permite actuar en paralelo mientras el "
                "resultado permanece incierto, puede ser C. "
                "Ademas, C debe representar un margen de accion o "
                "eleccion distinto de simplemente aceptar, permitir, "
                "tolerar, sostener o dejar estar el propio limite. "
                "Una conducta cuya funcion sea solamente aceptar o "
                "tolerar L pertenece a A y, por si sola, NO constituye "
                "C, aunque este formulada como algo que la persona "
                "puede hacer. "
                f"Limite: {limit_description}"
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
            raise AF5RemainingChoiceError(
                "Estado semantico AF5-C invalido."
            )

        if status == "not_supported":
            continue

        output.append(
            {
                "id": f"af5_remaining_choice_{len(output) + 1}",
                "choice": choice.strip(),
                "evidence": {
                    "quote": quote.strip(),
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "semantic_validation": validation,
            }
        )

    return {"choices": output}


def extract_ai_af5_remaining_choice(
    *,
    current_ai: str,
    limit_description: str,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(current_ai, str):
        raise AF5RemainingChoiceError(
            "current_ai debe ser una cadena."
        )

    if not isinstance(limit_description, str):
        raise AF5RemainingChoiceError(
            "limit_description debe ser una cadena."
        )

    normalized_current_ai = current_ai.strip()
    normalized_limit = limit_description.strip()

    if not normalized_current_ai or not normalized_limit:
        return {"choices": []}

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )
    selected_provider = identity["provider"]
    selected_model = identity["model"]

    def execute() -> dict[str, Any]:
        last_literal_error: Exception | None = None
        empty_results = 0

        for attempt in range(2):
            raw = _call_provider(
                current_ai=normalized_current_ai,
                limit_description=normalized_limit,
                provider=selected_provider,
                model=selected_model,
                timeout=timeout,
            )

            try:
                processed = _process_raw(
                    raw=raw,
                    current_ai=normalized_current_ai,
                    limit_description=normalized_limit,
                    provider=selected_provider,
                    model=selected_model,
                    timeout=timeout,
                )
            except AF5RemainingChoiceLiteralEvidenceError as exc:
                last_literal_error = exc
                if attempt == 1:
                    raise
                continue

            if processed.get("choices"):
                return processed

            empty_results += 1

            if empty_results == 2:
                return {"choices": []}

        if last_literal_error is not None:
            raise last_literal_error

        raise AF5RemainingChoiceError(
            "AF5-C no produjo un resultado validado."
        )

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("choices"), list)
        ):
            raise AF5RemainingChoiceError(
                "Resultado final AF5-C invalido."
            )
        return result

    return cached_semantic_operation(
        extractor="af_ai_af5_remaining_choice",
        extractor_version=AF5_REMAINING_CHOICE_EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=AF5_REMAINING_CHOICE_PROMPT_VERSION,
        schema_version=AF5_REMAINING_CHOICE_SCHEMA_VERSION,
        parameters={
            "provider": selected_provider,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        inputs={
            "current_ai": normalized_current_ai,
            "limit_description": normalized_limit,
        },
        execute=execute,
        validate_result=validate_result,
    )


def remaining_choice_is_confirmed(
    item: dict[str, Any],
) -> bool:
    return (
        item
        .get("semantic_validation", {})
        .get("status")
        == "supported"
    )
