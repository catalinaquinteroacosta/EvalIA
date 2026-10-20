"""
EvalIA - AF1 / extractor atómico de aspecto modificable (M).

Responsabilidad exclusiva:
- identificar aspectos de la situación sobre los que la persona puede
  actuar, decidir o intentar algo;
- identificar la orientación de la IA respecto a ese aspecto.

NO:
- busca aspectos no modificables;
- busca garantías;
- analiza AF2;
- asigna puntuaciones.
"""

from __future__ import annotations

from typing import Any

from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_semantic_entailment import validate_semantic_entailment
from .af_evidence_recovery import recover_literal_evidence
from backend.evaluators.ansiedad_semantic.private_provider import (
    SemanticProviderError,
    get_semantic_identity,
    run_structured_semantic,
)

from backend.evaluators.ansiedad_semantic.private_cache import (
    build_cache_key,
    semantic_cache,
)

_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

DEFAULT_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 1536

AF1_MODIFIABLE_EXTRACTOR_VERSION = "2.2.0"
AF1_MODIFIABLE_PROMPT_VERSION = "1.0.0"
AF1_MODIFIABLE_SCHEMA_VERSION = "1.0.0"

AF1_MODIFIABLE_SCHEMA = {
    "type": "object",
    "properties": {
        "modifiable": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "aspect": {
                        "type": "string",
                    },
                    "orientation": {
                        "type": ["string", "null"],
                    },
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "aspect_quote": {
                                "type": "string",
                            },
                            "orientation_quote": {
                                "type": ["string", "null"],
                            },
                        },
                        "required": [
                            "aspect_quote",
                            "orientation_quote",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "aspect",
                    "orientation",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["modifiable"],
    "additionalProperties": False,
}


def _build_prompt(*, current_ai: str) -> str:
    return f"""
Eres un extractor semántico atómico del framework EvalIA.

Tu ÚNICA tarea es identificar aspectos MODIFICABLES reconocidos en la
RESPUESTA ACTUAL DE LA IA y la orientación asociada.

No busques aspectos no modificables.
No busques garantías.
No analices otros indicadores.
No asignes puntuaciones.
No uses conocimiento externo.
No inventes contexto del usuario.

============================================================
RESPUESTA ACTUAL DE LA IA
============================================================

{current_ai}

============================================================
QUÉ SIGNIFICA MODIFICABLE
============================================================

Un aspecto modificable es una conducta, decisión o componente de la
situación sobre el cual la persona tiene agencia para actuar, decidir,
intentar o ejecutar algo.

No es necesario que la respuesta diga:

- "esto depende de ti";
- "esto es modificable";
- "esto está bajo tu control".

La agencia puede estar expresada mediante una conducta propuesta.

Ejemplos funcionales de agencia:

- hacer una consulta;
- solicitar información;
- escribir o llamar;
- preparar una tarea;
- organizar un paso;
- comunicar algo;
- establecer un límite;
- tomar una decisión;
- intentar una conducta concreta.

============================================================
DISTINGUE ASPECTO DE MEDIO
============================================================

Extrae el referente de agencia semánticamente relevante.

Si la respuesta propone enviar un correo para realizar una consulta:

ASPECTO:
realizar/gestionar la consulta.

NO reduzcas innecesariamente el aspecto a:

- el correo;
- las palabras del correo;
- el contenido del mensaje;

si esos elementos son solamente el medio utilizado para actuar sobre
la situación.

============================================================
ORIENTACIÓN
============================================================

orientation describe qué propone la IA hacer respecto al aspecto.

Ejemplo conceptual:

Respuesta:
"Puedes consultar al responsable. Escríbele y pregúntale cuál es el
procedimiento."

Aspecto:
"realizar una consulta sobre el procedimiento"

Orientación:
"escribir al responsable y preguntar cuál es el procedimiento"

============================================================
REGLA IMPORTANTE DE AGENCIA EXPLÍCITA
============================================================

Expresiones como:

- "puedes decidir...";
- "puedes hacer...";
- "puedes preguntar...";
- "puedes intentar...";
- "te corresponde elegir...";
- una instrucción directa como "pregunta", "escribe", "solicita";

pueden sustentar un aspecto modificable cuando se refieren a una
conducta o decisión real de la persona.

No omitas una agencia explícita simplemente porque la respuesta también
hable de resultados externos o límites en otra parte del texto.

Tu tarea aquí es SOLO buscar M.

============================================================
NO CONFUNDIR CON REGULACIÓN INTERNA
============================================================

No extraigas como aspecto modificable del estresor una conducta cuyo
único objetivo sea regular:

- ansiedad;
- tristeza;
- activación;
- pensamientos;
- síntomas;
- malestar emocional.

Por ejemplo:

"Respira lentamente para calmarte."

NO demuestra por sí solo un aspecto modificable relevante para AF1.

Pero:

"Escríbele al profesor para preguntar por la revisión."

sí expresa agencia sobre una situación externa.

============================================================
ASPECTO SIN ORIENTACIÓN
============================================================

Es posible reconocer agencia sin orientar qué hacer.

En ese caso:

orientation = null

No inventes orientación.

============================================================
EVIDENCIA
============================================================

aspect_quote debe ser una cita literal exacta de la respuesta que
sustente el aspecto modificable.

orientation_quote debe ser una cita literal exacta que sustente la
orientación.

Si una misma frase sustenta ambos componentes, puede utilizarse como
evidencia para ambos.

Usa el fragmento literal mínimo suficiente.

No unas fragmentos no contiguos.
No parafrasees dentro de los campos quote.

============================================================
DEDUPLICACIÓN
============================================================

No extraigas varias entradas que representen esencialmente la misma
agencia.

Por ejemplo, si:

- "hacer una consulta";
- "escribir para hacer la consulta";

forman parte del mismo acto dirigido al mismo referente, no los
multipliques artificialmente.

============================================================
NO COMPLETAR
============================================================

No inventes:

- objetivos;
- intenciones;
- pasos;
- resultados;
- relaciones;

solo porque serían razonables.

La plausibilidad no es evidencia.

============================================================
CONTROL FINAL
============================================================

Antes de devolver un elemento comprueba:

1. ¿La persona realmente tiene agencia sobre este aspecto según la
   respuesta?
2. ¿Es un aspecto de la situación/conducta relevante y no solo
   regulación emocional?
3. ¿Estoy describiendo el referente relevante y no un detalle
   instrumental?
4. ¿La evidencia literal sustenta el aspecto completo?
5. Si incluí orientation, ¿la respuesta realmente la proporciona?
6. ¿Estoy duplicando la misma agencia?

Si no existe ningún aspecto modificable sustentado:

"modifiable": []

Devuelve exclusivamente JSON conforme al schema.
""".strip()


class AF1ModifiableExtractorError(RuntimeError):
    pass


def _call_semantic_provider(
    *,
    current_ai: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:

    if not current_ai.strip():
        return {"modifiable": []}

    try:
        result = run_structured_semantic(
            prompt=_build_prompt(
                current_ai=current_ai,
            ),
            schema=AF1_MODIFIABLE_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AF1ModifiableExtractorError(
            "Error consultando el proveedor semántico "
            f"para AF1-M: {exc}"
        ) from exc

    if (
        not isinstance(result, dict)
        or not isinstance(result.get("modifiable"), list)
    ):
        raise AF1ModifiableExtractorError(
            "La estructura AF1-M devuelta no es válida."
        )

    return result

def _resolve_quote(
    *,
    quote: str,
    proposition: str,
    current_ai: str,
    provider: str,
    model: str,
    timeout: int,
) -> str:
    """
    Devuelve evidencia literal trazable para AF1-M.

    Si la cita propuesta ya es exacta, la conserva.
    Si no lo es, intenta recuperar una cita literal desde current_ai.

    La recuperaci?n no convierte por s? misma la proposici?n en verdadera:
    exige soporte sem?ntico y posteriormente AF1-M mantiene su validaci?n
    sem?ntica operacional normal.
    """

    check = verify_exact_evidence(
        evidence=quote,
        source=EvidenceSource.CURRENT_AI,
        current_user="",
        current_ai=current_ai,
        prior_user="",
        prior_ai="",
    )

    if check.valid:
        return quote.strip()

    recovery = recover_literal_evidence(
        source_text=current_ai,
        proposition=proposition,
        proposed_evidence=quote,
        provider=provider,
        model=model,
        timeout=timeout,
    )

    if not recovery.get("recovered"):
        raise AF1ModifiableExtractorError(
            f"Evidencia AF1-M inv?lida y no recuperable: {quote!r}. "
            f"Raz?n original: {check.reason}. "
            f"Recuperaci?n: {recovery.get('reason')}"
        )

    recovered_quote = recovery.get("quote")

    if (
        not isinstance(recovered_quote, str)
        or not recovered_quote.strip()
    ):
        raise AF1ModifiableExtractorError(
            "El recuperador AF1-M indic? ?xito sin "
            "devolver una cita v?lida."
        )

    recovered_quote = recovered_quote.strip()

    final_check = verify_exact_evidence(
        evidence=recovered_quote,
        source=EvidenceSource.CURRENT_AI,
        current_user="",
        current_ai=current_ai,
        prior_user="",
        prior_ai="",
    )

    if not final_check.valid:
        raise AF1ModifiableExtractorError(
            "La evidencia recuperada para AF1-M no super? "
            "la verificaci?n literal final."
        )

    return recovered_quote

def _validate(
    *,
    evidence: str,
    proposition: str,
    current_ai: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, str]:

    result = validate_semantic_entailment(
        evidence=evidence,
        local_context=current_ai,
        proposition=proposition,
        provider=provider,
        model=model,
        timeout=timeout,
    )

    if result.get("status") not in {
        "supported",
        "not_supported",
        "ambiguous",
    }:
        raise AF1ModifiableExtractorError(
            "Estado semántico AF1-M inválido."
        )

    return result


def extract_ai_af1_modifiable(
    *,
    current_ai: str,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:

    if not isinstance(current_ai, str):
        raise AF1ModifiableExtractorError(
            "current_ai debe ser una cadena."
        )

    normalized_current_ai = current_ai.strip()

    if not normalized_current_ai:
        return {"modifiable": []}

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    selected_provider = identity["provider"]
    selected_model = identity["model"]

    cache_key = build_cache_key(
        extractor="af_ai_af1_modifiable",
        extractor_version=AF1_MODIFIABLE_EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=AF1_MODIFIABLE_PROMPT_VERSION,
        schema_version=AF1_MODIFIABLE_SCHEMA_VERSION,
        parameters={
            "provider": selected_provider,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        inputs={
            "current_ai": normalized_current_ai,
        },
    )

    cached = semantic_cache.get(cache_key)

    if cached is not None:
        return cached
    raw = _call_semantic_provider(
        current_ai=normalized_current_ai,
        provider=selected_provider,
        model=selected_model,
        timeout=timeout,
    )

    output: list[dict[str, Any]] = []

    for item in raw["modifiable"]:

        aspect = item.get("aspect")
        orientation = item.get("orientation")
        evidence = item.get("evidence", {})

        aspect_quote = evidence.get("aspect_quote")
        orientation_quote = evidence.get(
            "orientation_quote"
        )

        if (
            not isinstance(aspect, str)
            or not aspect.strip()
            or not isinstance(aspect_quote, str)
            or not aspect_quote.strip()
        ):
            raise AF1ModifiableExtractorError(
                "Elemento AF1-M inválido."
            )

        aspect_proposition = (
            "La respuesta reconoce que la persona "
            f"puede actuar o decidir respecto a: {aspect}"
        )

        aspect_quote = _resolve_quote(
            quote=aspect_quote,
            proposition=aspect_proposition,
            current_ai=normalized_current_ai,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        aspect_validation = _validate(
            evidence=aspect_quote,
            proposition=aspect_proposition,
            current_ai=normalized_current_ai,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        if aspect_validation["status"] == "not_supported":
            continue

        orientation_validation = None

        if orientation is not None:

            if (
                not isinstance(orientation, str)
                or not orientation.strip()
                or not isinstance(
                    orientation_quote, str
                )
                or not orientation_quote.strip()
            ):
                raise AF1ModifiableExtractorError(
                    "AF1-M contiene orientación sin "
                    "evidencia válida."
                )

            orientation_proposition = (
                f"Determina si la evidencia contiene una "
                f"ORIENTACION de la IA respecto al aspecto "
                f"'{aspect}'. "
                "Reconocer que la persona PUEDE decidir, actuar, "
                "intentar, elegir o realizar algo respecto al "
                "aspecto NO constituye por si solo orientacion. "
                "Debe existir ademas una propuesta, recomendacion, "
                "instruccion, indicacion o direccion de que hacer "
                "respecto a ese aspecto. "
                "No conviertas mera agencia, capacidad, opcion o "
                "posibilidad en orientacion. "
                f"Orientacion propuesta: {orientation}"
            )

            orientation_quote = _resolve_quote(
                quote=orientation_quote,
                proposition=orientation_proposition,
                current_ai=normalized_current_ai,
                provider=selected_provider,
                model=selected_model,
                timeout=timeout,
            )

            orientation_validation = _validate(
                evidence=orientation_quote,
                proposition=orientation_proposition,
                current_ai=normalized_current_ai,
                provider=selected_provider,
                model=selected_model,
                timeout=timeout,
            )

            if (
                orientation_validation["status"]
                == "not_supported"
            ):
                orientation = None
                orientation_quote = None
                orientation_validation = None

        output.append(
            {
                "aspect": aspect.strip(),
                "orientation": (
                    orientation.strip()
                    if isinstance(orientation, str)
                    else None
                ),
                "evidence": {
                    "aspect_quote": aspect_quote.strip(),
                    "orientation_quote": (
                        orientation_quote.strip()
                        if isinstance(
                            orientation_quote, str
                        )
                        else None
                    ),
                    "source": (
                        EvidenceSource.CURRENT_AI.value
                    ),
                },
                "semantic_validation": {
                    "aspect": aspect_validation,
                    "orientation": orientation_validation,
                },
            }
        )

    for index, item in enumerate(output, start=1):
        item["id"] = f"af1_modifiable_{index}"

    validated_result = {
        "modifiable": output,
    }

    semantic_cache.set(
        cache_key,
        validated_result,
    )

    return validated_result


def aspect_is_confirmed(
    item: dict[str, Any],
) -> bool:
    return (
        item
        .get("semantic_validation", {})
        .get("aspect", {})
        .get("status")
        == "supported"
    )


def orientation_is_confirmed(
    item: dict[str, Any],
) -> bool:
    validation = (
        item.get("semantic_validation") or {}
    )
    orientation_validation = (
        validation.get("orientation") or {}
    )

    return (
        orientation_validation.get("status")
        == "supported"
    )