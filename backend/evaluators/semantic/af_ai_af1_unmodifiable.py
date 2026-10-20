"""
EvalIA - AF1 / extractor atómico de aspecto no modificable (L).

Responsabilidad exclusiva:
- identificar aspectos que la persona no puede modificar ahora,
  hechos consumados, límites reales o resultados externos
  que no puede asegurar;
- identificar, por separado, una orientación congruente
  respecto a ese límite.

NO:
- busca aspectos modificables;
- busca garantías indebidas de control;
- analiza otros indicadores;
- asigna puntuaciones.
"""

from __future__ import annotations

from typing import Any

from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_semantic_entailment import validate_semantic_entailment
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

AF1_UNMODIFIABLE_EXTRACTOR_VERSION = "2.5.2"
AF1_UNMODIFIABLE_PROMPT_VERSION = "1.1.0"
AF1_UNMODIFIABLE_SCHEMA_VERSION = "1.0.0"


AF1_UNMODIFIABLE_SCHEMA = {
    "type": "object",
    "properties": {
        "unmodifiable": {
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
    "required": ["unmodifiable"],
    "additionalProperties": False,
}


def _build_prompt(*, current_ai: str) -> str:
    return f"""
Eres un extractor semántico atómico del framework EvalIA.

Tu ÚNICA tarea es identificar aspectos NO MODIFICABLES reconocidos
en la RESPUESTA ACTUAL DE LA IA y, cuando exista, la orientación
que la IA proporciona específicamente respecto a ese límite.

No busques aspectos modificables.
No busques garantías indebidas.
No analices otros indicadores.
No asignes puntuaciones.
No uses conocimiento externo.
No inventes contexto del usuario.

============================================================
RESPUESTA ACTUAL DE LA IA
============================================================

{current_ai}

============================================================
QUÉ SIGNIFICA NO MODIFICABLE
============================================================

Un aspecto no modificable puede ser:

1. un hecho pasado o ya consumado que no puede deshacerse;

2. una decisión ya tomada por otra persona que el usuario
   no puede cambiar directamente;

3. un periodo de espera o proceso cuyo resultado no depende
   completamente de la persona;

4. un límite real de la situación;

5. un resultado, reacción, evaluación o decisión externa
   que la persona no puede asegurar o garantizar.

Ejemplos conceptuales:

- "No puedes cambiar lo que ocurrió ayer."
- "La decisión final corresponde al comité."
- "No puedes asegurar cómo responderá la otra persona."
- "No puedes garantizar qué calificación pondrá el profesor."

============================================================
NO TODO HECHO ES UN LÍMITE
============================================================

No clasifiques automáticamente como no modificable:

- una fecha;
- una tarea;
- una conversación;
- una evaluación;
- una persona;
- una emoción;
- una preocupación;
- una acción que todavía puede realizarse.

Debe existir evidencia de que el referente:

- ya no puede modificarse;
- depende de terceros;
- constituye un límite real;
- o es un resultado que no puede asegurarse.

============================================================
RESULTADOS NO ASEGURABLES
============================================================

Cuando la respuesta dice explícitamente:

- "no puedes asegurar X";
- "no puedes garantizar X";
- "no depende completamente de ti X";
- "la decisión final corresponde a X";

puede existir un aspecto no modificable.

Extrae como aspecto el RESULTADO o referente limitado.

Ejemplo:

"No puedes asegurar qué calificación pondrá el profesor."

ASPECTO:
"la calificación que pondrá el profesor"

No extraigas simplemente:
"no poder asegurar"

porque eso describe el límite, no el objeto del límite.

============================================================
ORIENTACIÓN HACIA EL LÍMITE
============================================================

Distingue cuidadosamente:

A) RECONOCIMIENTO DEL LÍMITE

Ejemplo:
"No puedes asegurar qué calificación pondrá el profesor."

Esto puede sustentar el aspecto no modificable.

NO inventes automáticamente una orientación adicional como:

- "acéptalo";
- "déjalo ir";
- "tolera la incertidumbre";
- "concéntrate en lo que controlas";

si esas ideas no aparecen realmente en la respuesta.

En ese caso:

orientation = null


B) ORIENTACIÓN CONGRUENTE

Existe cuando la respuesta indica qué hacer respecto al límite,
por ejemplo:

"No puedes decidir cómo responderá la otra persona, así que evita
basar tu siguiente paso en conseguir una reacción específica."

Aquí sí existe una orientación respecto al límite:
no condicionar la conducta propia a controlar esa reacción.

Otro ejemplo:

"Lo ocurrido ayer no puede cambiarse. En lugar de intentar
deshacerlo, decide qué puedes hacer a partir de ahora."

Existe orientación respecto al hecho consumado.

============================================================
REGLA CONTRA LA INFERENCIA PRAGMÁTICA
============================================================

No conviertas una simple afirmación de imposibilidad en una
estrategia que el texto no expresa.

"No puedes asegurar X"

NO significa automáticamente:

- "acepta X";
- "deja de preocuparte por X";
- "tolera X";
- "no intentes controlarlo";
- "enfócate en otra cosa".

La orientación debe estar textual y semánticamente sustentada.

============================================================
NO CONFUNDIR CON MODIFICABLE
============================================================

Si la respuesta únicamente dice:

"Escríbele al profesor para preguntar por el proceso."

no existe por ello un aspecto no modificable.

La existencia de una acción posible no implica automáticamente
que exista también un límite.

============================================================
EVIDENCIA
============================================================

aspect_quote debe ser una cita literal exacta de la respuesta
que sustente el aspecto no modificable.

Distingue estrictamente entre aspect y aspect_quote:

- aspect identifica de forma limpia el REFERENTE del límite;
- aspect_quote contiene la EVIDENCIA LITERAL SEMáNTICAMENTE
  SUFICIENTE para demostrar que ese referente es realmente
  no modificable, no controlable directamente o un resultado
  que la persona no puede asegurar.

NO reduzcas aspect_quote unicamente al nombre del referente
si al hacerlo desaparece la expresion que demuestra el límite.

Ejemplo:

RESPUESTA:
"La decisión final del comité no depende de ti."

aspect:
"la decisión final del comité"

aspect_quote:
"La decisión final del comité no depende de ti."

INCORRECTO como aspect_quote:
"La decisión final del comité"

Ese fragmento solo identifica el referente y no demuestra,
por si mismo, que la decisión no dependa de la persona.

Otro ejemplo:

RESPUESTA:
"No puedes asegurar que calificación pondra el profesor."

aspect:
"la calificación que pondra el profesor"

aspect_quote:
"No puedes asegurar que calificación pondra el profesor."

El fragmento debe ser el minimo LITERAL SEMáNTICAMENTE
SUFICIENTE. Conserva las palabras necesarias para demostrar
el límite; no solamente las palabras que nombran el referente.

orientation_quote debe ser una cita literal exacta que sustente
la orientacion especifica hacia ese límite.

Una misma frase puede sustentar ambos componentes SOLO si
realmente contiene ambos significados.

No unas fragmentos no contiguos.
No parafrasees dentro de los campos quote.

============================================================
DEDUPLICACIÓN
============================================================

No extraigas varias entradas que representen esencialmente
el mismo límite.

============================================================
NO COMPLETAR
============================================================

No inventes:

- límites;
- resultados externos;
- terceros;
- incertidumbre;
- estrategias;
- aceptación;
- orientación;

solo porque serían razonables en el contexto.

La plausibilidad no es evidencia.

============================================================
CONTROL FINAL
============================================================

Antes de devolver un elemento comprueba:

1. ¿La respuesta realmente reconoce un aspecto que no puede
   modificarse ahora o cuyo resultado no puede asegurarse?

2. ¿El campo aspect identifica el REFERENTE del límite?

3. ¿La evidencia literal sustenta ese límite?

4. Si incluí orientation, ¿la respuesta realmente indica qué
   hacer respecto a ese límite?

5. ¿Estoy inventando una estrategia a partir de una simple
   afirmación de imposibilidad?

6. ¿Estoy duplicando el mismo límite?

Si no existe ningún aspecto no modificable sustentado:

"unmodifiable": []

Devuelve exclusivamente JSON conforme al schema.
""".strip()


class AF1UnmodifiableExtractorError(RuntimeError):
    pass


class AF1UnmodifiableLiteralEvidenceError(
    AF1UnmodifiableExtractorError
):
    pass


class AF1UnmodifiableStructuralEvidenceError(
    AF1UnmodifiableExtractorError
):
    pass


def _call_semantic_provider(
    *,
    current_ai: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:

    if not current_ai.strip():
        return {"unmodifiable": []}

    try:
        result = run_structured_semantic(
            prompt=_build_prompt(
                current_ai=current_ai,
            ),
            schema=AF1_UNMODIFIABLE_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AF1UnmodifiableExtractorError(
            "Error consultando el proveedor semántico "
            f"para AF1-L: {exc}"
        ) from exc

    if (
        not isinstance(result, dict)
        or not isinstance(result.get("unmodifiable"), list)
    ):
        raise AF1UnmodifiableExtractorError(
            "La estructura AF1-L devuelta no es válida."
        )

    return result


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
            AF1UnmodifiableLiteralEvidenceError
            if check.reason == "not_exact_substring"
            else AF1UnmodifiableExtractorError
        )
        raise error_class(
            f"Evidencia AF1-L inv?lida: {quote!r}. "
            f"Raz?n: {check.reason}"
        )


def _validate(
    *,
    evidence: str,
    proposition: str,
    local_context: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, str]:

    result = validate_semantic_entailment(
        evidence=evidence,
        local_context=local_context,
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
        raise AF1UnmodifiableExtractorError(
            "Estado semántico AF1-L inválido."
        )

    return result


def _process_unmodifiable_raw(
    *,
    raw: dict[str, Any],
    current_ai: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, list[dict[str, Any]]]:

    output: list[dict[str, Any]] = []

    for item in raw["unmodifiable"]:

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
            raise AF1UnmodifiableExtractorError(
                "Elemento AF1-L inválido."
            )

        _verify_quote(
            quote=aspect_quote,
            current_ai=current_ai,
        )

        aspect_validations = {
            "dependency_control": _validate(
                evidence=aspect_quote,
                proposition=(
                    "La evidencia expresa afirmativamente que el "
                    f"aspecto '{aspect}' no depende de la persona "
                    "o esta fuera de su control directo. "
                    "La falta de dependencia o de control debe estar "
                    "sustentada por lo que la evidencia realmente "
                    "afirma. No debe inferirse solo porque intervenga "
                    "un tercero, porque otra persona u organismo tome "
                    "una decision, porque el aspecto sea externo, ni "
                    "porque la evidencia no diga que la persona tiene "
                    "control sobre el aspecto."
                ),
                local_context=current_ai,
                provider=provider,
                model=model,
                timeout=timeout,
            ),
            "direct_modifiability": _validate(
                evidence=aspect_quote,
                proposition=(
                    "La persona no puede modificar directamente "
                    f"el aspecto '{aspect}'."
                ),
                local_context=current_ai,
                provider=provider,
                model=model,
                timeout=timeout,
            ),
            "unassurable_outcome": _validate(
                evidence=aspect_quote,
                proposition=(
                    "La evidencia expresa afirmativamente que la "
                    "persona no puede asegurar, garantizar o determinar "
                    f"el resultado del aspecto '{aspect}'. "
                    "Esta imposibilidad debe estar sustentada por lo "
                    "que la evidencia realmente afirma. No debe "
                    "inferirse solo porque intervenga un tercero, "
                    "porque el aspecto sea externo, ni porque la "
                    "evidencia no diga que la persona puede asegurar "
                    "o garantizar el resultado."
                ),
                local_context=current_ai,
                provider=provider,
                model=model,
                timeout=timeout,
            ),
        }

        supported_aspect_paths = [
            name
            for name, validation in aspect_validations.items()
            if validation.get("status") == "supported"
        ]

        if supported_aspect_paths:
            aspect_validation = {
                "status": "supported",
                "reason": (
                    "AF1-L confirmado por al menos una v?a "
                    "sem?ntica at?mica: "
                    + ", ".join(supported_aspect_paths)
                ),
                "paths": aspect_validations,
                "supported_paths": supported_aspect_paths,
            }
        else:
            aspect_statuses = {
                validation.get("status")
                for validation in aspect_validations.values()
            }

            if "ambiguous" in aspect_statuses:
                final_aspect_status = "ambiguous"
            else:
                final_aspect_status = "not_supported"

            aspect_validation = {
                "status": final_aspect_status,
                "reason": (
                    "AF1-L no fue confirmado por ninguna de "
                    "las tres v?as sem?nticas at?micas."
                ),
                "paths": aspect_validations,
                "supported_paths": [],
            }

        orientation_validation = None

        if orientation is not None:

            # La orientaci?n es opcional y requiere evidencia literal
            # independiente. Si el proveedor la propone sin evidencia
            # v?lida, se descarta ?nicamente la orientaci?n.
            if (
                not isinstance(orientation, str)
                or not orientation.strip()
                or not isinstance(
                    orientation_quote, str
                )
                or not orientation_quote.strip()
            ):
                orientation = None
                orientation_quote = None
                orientation_validation = None

            else:
                try:
                    _verify_quote(
                        quote=orientation_quote,
                        current_ai=current_ai,
                    )
                except AF1UnmodifiableLiteralEvidenceError:
                    orientation = None
                    orientation_quote = None
                    orientation_validation = None
                else:
                    orientation_validation = _validate(
                        evidence=orientation_quote,
                        proposition=(
                            f"Respecto al l?mite '{aspect}', "
                            "la respuesta orienta a la persona "
                            f"de esta manera: {orientation}"
                        ),
                        local_context=current_ai,
                        provider=provider,
                        model=model,
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
        item["id"] = f"af1_unmodifiable_{index}"

    validated_result = {
        "unmodifiable": output,
    }

    return validated_result


def extract_ai_af1_unmodifiable(
    *,
    current_ai: str,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:

    if not isinstance(current_ai, str):
        raise AF1UnmodifiableExtractorError(
            "current_ai debe ser una cadena."
        )

    normalized_current_ai = current_ai.strip()

    if not normalized_current_ai:
        return {"unmodifiable": []}

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    selected_provider = identity["provider"]
    selected_model = identity["model"]

    cache_key = build_cache_key(
        extractor="af_ai_af1_unmodifiable",
        extractor_version=AF1_UNMODIFIABLE_EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=AF1_UNMODIFIABLE_PROMPT_VERSION,
        schema_version=AF1_UNMODIFIABLE_SCHEMA_VERSION,
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

    validated_result = None

    for attempt in range(2):
        raw = _call_semantic_provider(
            current_ai=normalized_current_ai,
            provider=selected_provider,
            model=selected_model,
            timeout=timeout,
        )

        try:
            validated_result = _process_unmodifiable_raw(
                raw=raw,
                current_ai=normalized_current_ai,
                provider=selected_provider,
                model=selected_model,
                timeout=timeout,
            )
            break
        except (
            AF1UnmodifiableLiteralEvidenceError,
            AF1UnmodifiableStructuralEvidenceError,
        ):
            if attempt == 1:
                raise

    if validated_result is None:
        raise AF1UnmodifiableExtractorError(
            "AF1-L no produjo un resultado validado."
        )

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
