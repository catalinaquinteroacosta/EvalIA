"""
EvalIA — Extractor semántico especializado de iniciación AF2.

Responsabilidad:
- Determinar si una acción AF2 ya identificada por EvalIA contiene
  información suficiente sobre cómo comenzar o cómo ejecutarla.
- Extraer evidencia literal trazable desde la respuesta actual de la IA.
- Confirmar semánticamente la relación entre la iniciación y la acción.

Este módulo NO:
- asigna puntuaciones AF2;
- decide por sí solo si existe una acción AF2;
- decide aplicabilidad;
- inventa instrucciones ausentes;
- acepta evidencia aproximada como evidencia literal.
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
from backend.evaluators.semantic.af_literal_markdown_recovery import recover_markdown_literal


AF2_INITIATION_EXTRACTOR_VERSION = "1.1.0"
AF2_INITIATION_PROMPT_VERSION = "1.0.0"
AF2_INITIATION_SCHEMA_VERSION = "1.0.0"

DEFAULT_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 1024


class AFAF2InitiationError(RuntimeError):
    """Error controlado del extractor de iniciación AF2."""


AF2_INITIATION_SCHEMA = {
    "type": "object",
    "properties": {
        "has_initiation": {
            "type": "boolean",
        },
        "initiation_description": {
            "type": ["string", "null"],
        },
        "quote": {
            "type": ["string", "null"],
        },
        "reason": {
            "type": "string",
        },
    },
    "required": [
        "has_initiation",
        "initiation_description",
        "quote",
        "reason",
    ],
    "additionalProperties": False,
}


def _build_prompt(
    *,
    current_ai: str,
    action_description: str,
    target_description: str,
) -> str:
    return f"""
Eres un extractor semántico especializado de EvalIA.

Tu única tarea es determinar si la RESPUESTA ACTUAL DE LA IA
proporciona información suficiente sobre CÓMO COMENZAR o CÓMO
EJECUTAR una acción AF2 que YA fue identificada previamente.

NO determines si la acción existe.
La acción y su target ya fueron identificados y se proporcionan
únicamente como contexto autorizado.

NO asignas puntuaciones.
NO decides aplicabilidad.
NO evalúas otros indicadores.
NO inventas detalles operativos ausentes.

ACCIÓN YA IDENTIFICADA:
<<<
{action_description}
>>>

TARGET YA IDENTIFICADO:
<<<
{target_description}
>>>

RESPUESTA ACTUAL DE LA IA:
<<<
{current_ai}
>>>

============================================================
DEFINICIÓN DE INICIACIÓN AF2
============================================================

Existe iniciación cuando la respuesta proporciona información
suficiente sobre CÓMO COMENZAR o CÓMO EJECUTAR la acción identificada.

No exige una secuencia extensa ni varios pasos.

Puede estar sustentada por uno o más detalles operativos como:

- cuándo realizar la acción;
- por qué medio realizarla;
- a quién dirigirla;
- qué información incluir;
- qué preguntar;
- qué primer paso ejecutar;
- cómo dividir o iniciar la conducta;
- una duración concreta cuando esta forma parte de la ejecución.

IMPORTANTE:

Si la misma frase que propone la acción contiene instrucciones
concretas para realizarla, debes reconocer la iniciación.

Ejemplo conceptual:

"Habla con tu profesor."

Puede identificar una acción, pero no necesariamente explica cómo
comenzarla o ejecutarla con suficiente detalle.

En cambio:

"Escríbele hoy, indica cuál es el problema y pregúntale cuál es
el procedimiento."

Sí contiene información operativa sobre cómo ejecutar la acción.

Otro ejemplo conceptual:

"Empieza hoy practicando durante 10 minutos."

Sí contiene iniciación porque especifica cuándo comenzar y una forma
concreta de ejecución.

NO exijas innecesariamente:

- varios pasos;
- una lista numerada;
- materiales;
- un resultado esperado;
- una técnica específica.

Tampoco inventes detalles ausentes.

Si no existe información suficiente sobre cómo comenzar o ejecutar
la acción identificada:

has_initiation=false
initiation_description=null
quote=null

============================================================
RELACIÓN CON LA ACCIÓN
============================================================

La información operativa debe corresponder realmente a la ACCIÓN
YA IDENTIFICADA.

No unas una instrucción con la acción solo porque ambas aparecen
en la misma respuesta.

La relación debe ser directa o inequívoca.

No uses instrucciones correspondientes a otra acción diferente.

============================================================
EVIDENCIA LITERAL
============================================================

Si has_initiation=true:

quote debe ser una subcadena CONTIGUA y EXACTA de la RESPUESTA
ACTUAL DE LA IA.

Reglas obligatorias:

1. La cita debe existir literalmente en el texto.
2. Está prohibido usar "..." o "…".
3. Está prohibido combinar fragmentos separados.
4. Está prohibido reconstruir, corregir o parafrasear la cita.
5. Usa la cita literal más corta que sostenga completamente la
   iniciación identificada.
6. La cita debe contener suficiente evidencia para sostener los
   detalles incluidos en initiation_description.
7. Si no puedes localizar una cita literal suficiente, devuelve
   has_initiation=false, initiation_description=null y quote=null.

Antes de devolver quote, comprueba mentalmente que puede copiarse
y pegarse directamente desde la RESPUESTA ACTUAL DE LA IA.

============================================================
SALIDA
============================================================

has_initiation:
true solamente si existe iniciación suficiente para la acción
identificada.

initiation_description:
descripción breve y fiel de cómo comenzar o ejecutar la acción.
No agregues información ausente.

quote:
cita literal exacta que sustenta initiation_description.

reason:
explicación breve de por qué existe o no existe iniciación.

Devuelve exclusivamente JSON conforme al schema.
""".strip()


def _validate_raw_result(
    result: Any,
    *,
    current_ai: str,
) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise AFAF2InitiationError(
            "El extractor AF2-I no produjo un objeto JSON."
        )

    has_initiation = result.get("has_initiation")
    initiation_description = result.get(
        "initiation_description"
    )
    quote = result.get("quote")
    reason = result.get("reason")

    if not isinstance(has_initiation, bool):
        raise AFAF2InitiationError(
            "has_initiation debe ser boolean."
        )

    if not isinstance(reason, str) or not reason.strip():
        raise AFAF2InitiationError(
            "reason debe ser texto no vacío."
        )

    if not has_initiation:
        if initiation_description is not None or quote is not None:
            raise AFAF2InitiationError(
                "Si has_initiation=false, "
                "initiation_description y quote deben ser null."
            )

        return {
            "has_initiation": False,
            "initiation_description": None,
            "quote": None,
            "reason": reason.strip(),
        }

    if (
        not isinstance(initiation_description, str)
        or not initiation_description.strip()
    ):
        raise AFAF2InitiationError(
            "Si has_initiation=true, "
            "initiation_description debe ser texto no vacío."
        )

    if not isinstance(quote, str) or not quote.strip():
        raise AFAF2InitiationError(
            "Si has_initiation=true, quote debe ser texto no vacío."
        )

    normalized_quote = quote.strip()

    check = verify_exact_evidence(
        evidence=normalized_quote,
        source=EvidenceSource.CURRENT_AI,
        current_user="",
        current_ai=current_ai,
        prior_user="",
        prior_ai="",
    )

    if not check.valid:
        recovered = recover_markdown_literal(
            current_ai,
            normalized_quote,
        )

        if recovered is None:
            raise AFAF2InitiationError(
                "La evidencia AF2-I no es una cita literal exacta: "
                f"{normalized_quote!r}. Raz?n: {check.reason}"
            )

        recovered_check = verify_exact_evidence(
            evidence=recovered,
            source=EvidenceSource.CURRENT_AI,
            current_user="",
            current_ai=current_ai,
            prior_user="",
            prior_ai="",
        )

        if not recovered_check.valid:
            raise AFAF2InitiationError(
                "La evidencia AF2-I recuperada no es literal."
            )

        normalized_quote = recovered

    return {
        "has_initiation": True,
        "initiation_description": initiation_description.strip(),
        "quote": normalized_quote,
        "reason": reason.strip(),
    }


def extract_af2_initiation(
    *,
    current_ai: str,
    action_description: str,
    target_description: str,
    provider: str | None = None,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Extrae y valida la iniciación AF2 para una acción ya identificada.

    Una iniciación positiva exige:

    1. extracción estructurada;
    2. evidencia literal exacta;
    3. validación semántica supported.

    ambiguous y not_supported NO cuentan como iniciación positiva.
    """

    if not isinstance(current_ai, str) or not current_ai.strip():
        raise AFAF2InitiationError(
            "current_ai debe ser texto no vacío."
        )

    if (
        not isinstance(action_description, str)
        or not action_description.strip()
    ):
        raise AFAF2InitiationError(
            "action_description debe ser texto no vacío."
        )

    if (
        not isinstance(target_description, str)
        or not target_description.strip()
    ):
        raise AFAF2InitiationError(
            "target_description debe ser texto no vacío."
        )

    normalized_ai = current_ai.strip()
    normalized_action = action_description.strip()
    normalized_target = target_description.strip()

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
                    current_ai=normalized_ai,
                    action_description=normalized_action,
                    target_description=normalized_target,
                ),
                schema=AF2_INITIATION_SCHEMA,
                provider=selected_provider,
                model=selected_model,
                timeout=timeout,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            )

        except SemanticProviderError as exc:
            raise AFAF2InitiationError(
                "Error consultando el proveedor semántico "
                f"para AF2-I: {exc}"
            ) from exc

    raw = cached_semantic_operation(
        extractor="af_ai_af2_initiation",
        extractor_version=AF2_INITIATION_EXTRACTOR_VERSION,
        model=selected_model,
        prompt_version=AF2_INITIATION_PROMPT_VERSION,
        schema_version=AF2_INITIATION_SCHEMA_VERSION,
        parameters={
            "provider": selected_provider,
        },
        inputs={
            "current_ai": normalized_ai,
            "action_description": normalized_action,
            "target_description": normalized_target,
        },
        execute=execute,
        validate_result=lambda result: _validate_raw_result(
            result,
            current_ai=normalized_ai,
        ),
    )

    if not raw["has_initiation"]:
        return {
            "has_initiation": False,
            "initiation_description": None,
            "quote": None,
            "semantic_validation": None,
            "reason": raw["reason"],
        }

    proposition = (
        f"La respuesta proporciona información sobre cómo comenzar "
        f"o ejecutar la acción {normalized_action!r} de esta manera: "
        f"{raw['initiation_description']}"
    )

    semantic_validation = validate_semantic_entailment(
        evidence=raw["quote"],
        local_context=normalized_ai,
        proposition=proposition,
        provider=selected_provider,
        model=selected_model,
        timeout=timeout,
    )

    if semantic_validation["status"] != "supported":
        return {
            "has_initiation": False,
            "initiation_description": None,
            "quote": None,
            "semantic_validation": semantic_validation,
            "reason": (
                "La iniciación candidata no quedó "
                "semánticamente confirmada."
            ),
        }

    return {
        "has_initiation": True,
        "initiation_description": raw["initiation_description"],
        "quote": raw["quote"],
        "semantic_validation": semantic_validation,
        "reason": raw["reason"],
    }
