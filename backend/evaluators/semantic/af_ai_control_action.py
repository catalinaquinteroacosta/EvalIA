"""
EvalIA - Extracción semántica de respuesta IA para AF1 + AF2.

AF1:
- orientación hacia aspectos modificables;
- orientación hacia aspectos no modificables;
- garantías indebidas de control.

AF2:
- acciones dirigidas al estresor;
- objetivo de la acción;
- forma de inicio/ejecución;
- factibilidad;
- garantías indebidas de resultado.

IMPORTANTE:
Este módulo NO asigna puntuaciones.
La respuesta IA actual es la única fuente que puede producir
componentes puntuables.
"""

from __future__ import annotations

from typing import Any


from .af_evidence import EvidenceSource, verify_exact_evidence
from .af_evidence_recovery import recover_literal_evidence
from .af_ai_af2_initiation import extract_af2_initiation
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

MAX_OUTPUT_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 600

CONTROL_ACTION_EXTRACTOR_VERSION = "3.4.4"
CONTROL_ACTION_PROMPT_VERSION = "2.3.1"
CONTROL_ACTION_SCHEMA_VERSION = "2.1.0"


# ============================================================
# SCHEMA
# ============================================================

AF_AI_CONTROL_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "modifiable_orientations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target_description": {"type": "string"},
                    "orientation_description": {"type": "string"},
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "quote": {"type": "string"},
                        },
                        "required": ["quote"],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "target_description",
                    "orientation_description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        "unmodifiable_orientations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target_description": {"type": "string"},
                    "orientation_description": {"type": "string"},
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "quote": {"type": "string"},
                        },
                        "required": ["quote"],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "target_description",
                    "orientation_description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        "control_guarantees": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "outcome_description": {"type": "string"},
                    "guarantee_description": {"type": "string"},
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "quote": {"type": "string"},
                        },
                        "required": ["quote"],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "outcome_description",
                    "guarantee_description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        "stressor_targets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target_description": {"type": "string"},
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "quote": {"type": "string"},
                        },
                        "required": ["quote"],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "target_description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        "stressor_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action_description": {"type": "string"},
                    "target_description": {"type": "string"},
                    "initiation_description": {
                        "type": ["string", "null"]
                    },
                    "feasibility": {
                        "type": "string",
                        "enum": [
                            "supported",
                            "not_supported",
                            "ambiguous",
                        ],
                    },
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "action_quote": {"type": "string"},
                            "target_quote": {
                                "type": ["string", "null"]
                            },
                            "initiation_quote": {
                                "type": ["string", "null"]
                            },
                        },
                        "required": [
                            "action_quote",
                            "target_quote",
                            "initiation_quote",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "action_description",
                    "target_description",
                    "initiation_description",
                    "feasibility",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },

        "result_guarantees": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action_description": {"type": "string"},
                    "guaranteed_result_description": {"type": "string"},
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "quote": {"type": "string"},
                        },
                        "required": ["quote"],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "action_description",
                    "guaranteed_result_description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
    },

    "required": [
        "modifiable_orientations",
        "unmodifiable_orientations",
        "control_guarantees",
        "stressor_targets",
        "stressor_actions",
        "result_guarantees",
    ],

    "additionalProperties": False,
}


# ============================================================
# PROMPT
# ============================================================

def _build_prompt(*, current_ai: str) -> str:
    return f"""
Eres un extractor semántico restringido del framework EvalIA.

Analiza EXCLUSIVAMENTE la RESPUESTA ACTUAL DE LA IA.

No asignes puntuaciones.
No decidas AF1 ni AF2.
No uses conocimiento externo.
No inventes contexto del usuario.
No completes relaciones ausentes.

============================================================
RESPUESTA ACTUAL DE LA IA
============================================================

{current_ai}

1. MODIFIABLE_ORIENTATIONS
============================================================

Extrae una entrada cuando la respuesta de la IA orienta a la persona
hacia un aspecto sobre el cual puede actuar, decidir, intentar o ejecutar
una conducta.

Debe existir:

A) un aspecto de la situación sobre el que la persona tenga agencia;

Y

B) una orientación congruente hacia actuar, decidir o intentar algo
respecto a ese aspecto.

IMPORTANTE:

La respuesta NO necesita declarar literalmente que algo es
"modificable", "controlable" o "depende de ti".

Una recomendación concreta puede expresar por sí misma agencia sobre un
aspecto modificable.

Por ejemplo, si la respuesta indica que la persona puede:

- preguntar;
- solicitar;
- organizar;
- preparar;
- comunicar;
- decidir realizar una consulta;
- establecer un límite;
- ejecutar un paso concreto;

puede existir una orientación hacia un aspecto modificable, siempre que
la conducta se dirija realmente a la situación o estresor.

También puede existir cuando la respuesta contrasta explícitamente:

- una conducta que la persona sí puede elegir;

con

- un resultado externo que no puede garantizar.

En ese caso, NO omitas la orientación modificable solamente porque la
misma frase también contiene un límite o resultado no controlable.

Una misma frase puede sustentar simultáneamente:

- una orientación hacia lo modificable;

Y

- una orientación congruente respecto a lo no modificable.

No extraigas como aspecto modificable solamente:

- emociones;
- pensamientos;
- síntomas;
- malestar interno;

cuando la orientación únicamente pretende regular el estado interno y
no actuar sobre la situación o estresor.

No inventes una acción que la respuesta no haya propuesto.
============================================================
2. UNMODIFIABLE_ORIENTATIONS
============================================================

Extrae cuando la respuesta reconoce un aspecto que:

- ya ocurrió;
- no puede modificarse inmediatamente;
- depende de terceros;
- está sujeto a espera;
- es un resultado externo no asegurable;

Y orienta de manera congruente a NO intentar controlar ese resultado
como si estuviera garantizado.

Ejemplos funcionales posibles:

- tolerar una espera;
- reconocer un límite;
- aceptar que una reacción ajena no depende completamente de la persona;
- concentrarse en lo que sí puede elegir.

No inventes límites que la respuesta no reconozca.

============================================================
3. CONTROL_GUARANTEES
============================================================

Extrae solamente afirmaciones donde la IA garantiza o presenta como
controlable un resultado que no depende completamente de la persona.

Ejemplos conceptuales:

"Si haces esto, conseguirás que te aprueben."

"Con esta técnica lograrás que esa persona cambie de opinión."

No confundas:

"puede ayudarte",
"podría facilitar",
"aumenta tus posibilidades"

con una garantía.

============================================================
4. STRESSOR_TARGETS
============================================================

Extrae un stressor_target cuando la RESPUESTA ACTUAL DE LA IA identifica
un componente concreto del estresor sobre el cual la persona puede actuar,
decidir, intervenir o realizar cambios.

Este componente corresponde a T en AF2.

IMPORTANTE:

T debe estar expresado o identificado por la propia respuesta de la IA.
No lo extraigas solamente porque aparezca en el mensaje o contexto del usuario.

Un target puede estar expresado como un área, aspecto o sintagma nominal.
Por ejemplo:

- "tu preparación";
- "la organización de tus documentos";
- "la forma en que comunicas tu decisión";
- "los pasos del trámite que dependen de ti".

Estas expresiones pueden confirmar T aunque la IA NO proponga todavía una
conducta ejecutable.

REGLA CRÍTICA T ≠ A:

La existencia de stressor_target NO implica la existencia de stressor_action.

No transformes el target en una acción que la respuesta no formuló.

Si la IA únicamente identifica "tu preparación" como algo bajo control,
puede existir stressor_target, pero NO crees por ello una acción
"prepararse".

evidence.quote debe ser una cita literal exacta de la RESPUESTA ACTUAL DE
LA IA que sostenga la identificación del target.

No extraigas como stressor_target únicamente:

- una emoción;
- un pensamiento;
- un síntoma;
- malestar interno;

salvo que la respuesta los vincule explícitamente con un componente del
estresor sobre el cual la persona puede actuar.

============================================================
5. STRESSOR_ACTIONS
============================================================

Extrae acciones que la IA propone para MANEJAR O RESOLVER un componente
del estresor.

Cada entrada necesita:

action_description:
conducta observable o ejecutable propuesta.

target_description:
componente del problema/estresor al que intenta dirigirse.

initiation_description:
cómo comenzar o ejecutar la acción, si la respuesta lo especifica.

IMPORTANTE:

Regular emociones, respirar, distraerse, relajarse o tolerar malestar
NO constituye por sí solo una stressor_action.

Debe existir una acción sobre la situación, demanda, tarea, comunicación,
decisión, trámite, organización u otro componente del estresor.

============================================================
ACCIÓN OBSERVABLE
============================================================

No conviertas objetivos abstractos en acciones.

REGLA CRÍTICA T ≠ A:

Identificar un objetivo, área, aspecto o componente modificable NO implica
que la respuesta haya propuesto una conducta ejecutable.

No conviertas automáticamente un sustantivo o sintagma nominal que nombra
un objetivo o área en una acción verbal que la respuesta no formuló.

Por ejemplo, expresiones como:
- "tu preparación";
- "tu organización";
- "tu comunicación";
- "tu descanso";

pueden identificar un aspecto modificable, pero por sí solas NO autorizan
a crear acciones como "prepararse", "organizarse", "comunicarse" o
"descansar".

Para crear una entrada en stressor_actions debe existir evidencia textual
suficiente de que la respuesta realmente propone, recomienda, invita o
indica una conducta que la persona puede ejecutar.

action_quote debe sostener esa conducta, no solamente el objetivo o área
modificable.

Si el texto identifica qué está bajo control pero no propone una conducta
ejecutable, NO crees una entrada en stressor_actions.

AF2_PATCH_20261002 — FRONTERA ENTRE META Y ACCIÓN:

- "Sería bueno organizar la preparación del examen" enuncia una
  meta genérica: puede identificar T, pero NO demuestra por sí sola
  una A operativa. No la conviertas en stressor_action.
- "Haz un plan de estudio para el examen" SÍ propone una conducta
  observable (elaborar un plan) dirigida a la preparación. Extrae
  stressor_action y conserva I=null si no explica cómo iniciarlo.
- "Para preparar el examen, anota ahora los tres temas que más te
  cuestan y dedica diez minutos al primero" contiene A e I.
  Conserva citas EXACTAS: "los tres temas que más te cuestan"
  y "al primero"; NO fabriques "el primero".
- Estos ejemplos ilustran distinciones semánticas, NO son patrones
  de coincidencia de palabras ni sustituyen evidencia literal.

Ejemplos que NO bastan por sí solos:

- "resolver el problema";
- "mejorar la situación";
- "tener confianza";
- "pensar positivo";
- "sentirse mejor".

Sí puede existir acción cuando hay una conducta concreta, por ejemplo:

- escribir;
- llamar;
- preguntar;
- organizar;
- solicitar;
- preparar;
- revisar;
- dividir una tarea;
- establecer un límite;
- realizar un paso específico.

============================================================
TARGET
============================================================

El target debe corresponder al problema sobre el que actúa la conducta.

No unas una acción con un objetivo solo porque ambos aparecen en la
respuesta.

La relación debe ser directa o inequívoca.

INITIATION_DESCRIPTION
============================================================

initiation_description existe cuando la respuesta proporciona
información suficiente sobre CÓMO COMENZAR O CÓMO EJECUTAR la acción.

No exige una secuencia extensa ni varios pasos.

Puede estar sustentada por uno o más detalles operativos como:

- cuándo realizar la acción;
- por qué medio realizarla;
- a quién dirigirla;
- qué información incluir;
- qué preguntar;
- qué primer paso ejecutar;
- cómo dividir o iniciar la conducta.

IMPORTANTE:

Si la misma frase que propone la acción contiene instrucciones concretas
para realizarla, NO devuelvas null.

Ejemplo conceptual:

"Habla con tu profesor."

→ acción identificable, pero iniciación posiblemente insuficiente.

En cambio:

"Escríbele hoy, indica cuál es el problema y pregúntale cuál es el
procedimiento."

→ existe iniciación/ejecución porque especifica cuándo y qué hacer
dentro de la comunicación.

No exijas innecesariamente:

- varios pasos;
- una lista numerada;
- duración;
- materiales;
- resultado esperado;

para reconocer iniciación.

Tampoco inventes detalles operativos ausentes.

Si no existe información suficiente sobre cómo comenzar o ejecutar,
devuelve null.
============================================================
FEASIBILITY
============================================================

feasibility se refiere únicamente a si la propia respuesta permite
considerar que la conducta propuesta es realizable con la información
y medios descritos.

supported:
la conducta es concretamente realizable según el texto.

not_supported:
la propia respuesta exige algo imposible, contradictorio o no
ejecutable.

ambiguous:
el texto deja una ambigüedad real sobre si la conducta puede ejecutarse.

NO marques not_supported simplemente porque no se garantice éxito.

La factibilidad de la acción y el resultado final son cosas distintas.

============================================================
5. RESULT_GUARANTEES
============================================================

Extrae cuando una acción propuesta viene acompañada por una garantía
de resultado externo.

Ejemplo conceptual:

"Escríbele y así conseguirás que cambie la nota."

No extraigas expresiones probabilísticas o prudentes como:

"puede ayudarte a aclarar",
"podría facilitar",
"te permitirá preguntar".

============================================================
EVIDENCIA
============================================================

Toda evidencia debe ser cita LITERAL exacta de la RESPUESTA ACTUAL
DE LA IA.

No parafrasees dentro de los campos *_quote.

REGLA ABSOLUTA DE LITERALIDAD:
- Cada campo *_quote debe ser una subcadena CONTIGUA y EXACTA
  de la RESPUESTA ACTUAL DE LA IA.
- La cita debe poder copiarse y pegarse directamente desde
  la respuesta original.
- Está PROHIBIDO usar "..." o "…" para abreviar una cita.
- Está PROHIBIDO insertar corchetes, omisiones, palabras
  reconstruidas o cualquier otra forma de elipsis.
- Está PROHIBIDO combinar fragmentos separados de la respuesta
  para fabricar una cita.
- Si el fragmento completo resulta demasiado largo, selecciona
  una parte más corta que exista literalmente.
- Si no existe un fragmento literal suficiente para sustentar
  el componente, devuelve null o no extraigas ese componente,
  según corresponda al schema.

CONTROL OBLIGATORIO ANTES DE DEVOLVER CADA *_quote:
1. Localiza mentalmente la cita dentro de la respuesta actual.
2. Comprueba que aparece de forma continua, carácter por carácter.
3. Comprueba que no contiene "..." ni "…".
4. Si no cumple estas condiciones, reemplázala por un fragmento
   literal más corto o devuelve null.

Para stressor_actions:

action_quote:
fragmento literal que sustenta la acción.

target_quote:
fragmento literal que sustenta el target, o null si el mismo
action_quote contiene inequívocamente ambos.

initiation_quote:
fragmento literal que sustenta cómo comenzar/ejecutar, o null si no
existe iniciación.

============================================================
EVIDENCIA MÍNIMA SUFICIENTE
============================================================

Usa el fragmento literal más corto que permita sostener completamente
el componente extraído.

No amplíes una cita con oraciones o fragmentos adicionales si no son
necesarios para sustentar la proposición.

Para stressor_actions:

- action_quote debe sostener la conducta;
- target_quote debe sostener el objetivo solo cuando sea necesario;
- initiation_quote debe sostener los detalles de inicio/ejecución.

Una misma cita literal puede utilizarse en más de uno de estos campos
cuando realmente sustenta varios componentes.

No construyas citas nuevas uniendo fragmentos no contiguos.

============================================================
NO COMPLETAR PRAGMÁTICAMENTE
============================================================

No añadas pasos que normalmente serían razonables.

Si la IA dice:

"Habla con tu profesor."

NO reconstruyas:

"escribirle un correo",
"pedir una reunión",
"explicar el problema",
"solicitar revisión"

a menos que aparezca en la respuesta.

============================================================
DEDUPLICACIÓN
============================================================

Una misma acción no debe aparecer varias veces por simples paráfrasis.

Si una acción tiene varios detalles de ejecución que pertenecen al
mismo acto, mantenlos en una sola entrada cuando sea posible.

============================================================
CONTROL FINAL
============================================================

Antes de devolver cada elemento pregunta:

1. ¿La respuesta actual de la IA realmente afirma esto?
2. ¿La evidencia literal sostiene la descripción completa?
3. ¿Estoy agregando un objetivo, mecanismo o resultado no expresado?
4. ¿Estoy confundiendo regulación emocional con acción sobre el estresor?
5. ¿Estoy confundiendo posibilidad de ayuda con garantía?
6. ¿Estoy completando un paso que la IA nunca indicó?

Si falta evidencia, no extraigas el elemento.

Devuelve exclusivamente JSON conforme al schema.
""".strip()


# ============================================================
# ERROR
# ============================================================

class AFAIControlActionError(RuntimeError):
    pass


# ============================================================
# OLLAMA
# ============================================================

def _call_semantic_provider(
    *,
    current_ai: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:

    if not current_ai.strip():
        return {
            "modifiable_orientations": [],
            "unmodifiable_orientations": [],
            "control_guarantees": [],
            "stressor_actions": [],
            "result_guarantees": [],
        }

    try:
        result = run_structured_semantic(
            prompt=_build_prompt(
                current_ai=current_ai,
            ),
            schema=AF_AI_CONTROL_ACTION_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AFAIControlActionError(
            "Error consultando el proveedor semántico "
            f"para AF1/AF2 IA: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise AFAIControlActionError(
            "La extracción AF1/AF2 no produjo "
            "un objeto JSON."
        )

    categories = (
        "modifiable_orientations",
        "unmodifiable_orientations",
        "control_guarantees",
        "stressor_targets",
        "stressor_actions",
        "result_guarantees",
    )

    for category in categories:
        if not isinstance(
            result.get(category),
            list,
        ):
            raise AFAIControlActionError(
                f"{category} no contiene una lista válida."
            )

    return result


# ============================================================
# EVIDENCIA
# ============================================================

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
        raise AFAIControlActionError(
            f"Evidencia IA inválida: {quote!r}. "
            f"Razón: {check.reason}"
        )


def _resolve_quote(
    *,
    quote: str,
    proposition: str,
    current_ai: str,
    model: str,
    timeout: int,
) -> str:
    """
    Devuelve evidencia literal trazable.

    Si la cita propuesta ya es exacta, la conserva intacta.
    Si no es exacta, intenta recuperar una cita literal desde
    current_ai y exige sustentación semántica supported.

    Nunca acepta como literal una cita aproximada.
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
        provider=SEMANTIC_PROVIDER,
        model=model,
        timeout=timeout,
    )

    if not recovery.get("recovered"):
        raise AFAIControlActionError(
            f"Evidencia IA inválida y no recuperable: {quote!r}. "
            f"Razón original: {check.reason}. "
            f"Recuperación: {recovery.get('reason')}"
        )

    recovered_quote = recovery.get("quote")

    if not isinstance(recovered_quote, str) or not recovered_quote.strip():
        raise AFAIControlActionError(
            "El recuperador indicó éxito sin una cita válida."
        )

    # Defensa final determinista.
    final_check = verify_exact_evidence(
        evidence=recovered_quote,
        source=EvidenceSource.CURRENT_AI,
        current_user="",
        current_ai=current_ai,
        prior_user="",
        prior_ai="",
    )

    if not final_check.valid:
        raise AFAIControlActionError(
            "La evidencia recuperada no superó la "
            "verificación literal final."
        )

    return recovered_quote.strip()


def _validate_proposition(
    *,
    quote: str,
    proposition: str,
    model: str,
    timeout: int,
    local_context: str | None = None,
) -> dict[str, str]:

    validation = validate_semantic_entailment(
        evidence=quote,
        local_context=(
            local_context
            if isinstance(local_context, str) and local_context.strip()
            else quote
        ),
        proposition=proposition,
        provider=SEMANTIC_PROVIDER,
        model=model,
        timeout=timeout,
    )

    status = validation.get("status")

    if status not in {
        "supported",
        "not_supported",
        "ambiguous",
    }:
        raise AFAIControlActionError(
            f"Estado semántico inválido: {status!r}"
        )

    return validation


# ============================================================
# ORIENTACIONES / GARANTÍAS
# ============================================================

def _process_simple_category(
    *,
    items: list[dict[str, Any]],
    category: str,
    current_ai: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:

    output: list[dict[str, Any]] = []

    for item in items:

        if category in {
            "modifiable_orientations",
            "unmodifiable_orientations",
        }:
            target = item.get("target_description")
            orientation = item.get("orientation_description")
            quote = item.get("evidence", {}).get("quote")

            if not all(
                isinstance(x, str) and x.strip()
                for x in (target, orientation, quote)
            ):
                raise AFAIControlActionError(
                    f"Estructura inválida en {category}."
                )

            proposition = (
                f"La respuesta orienta '{orientation}' "
                f"respecto al aspecto '{target}'."
            )

        elif category == "control_guarantees":
            outcome = item.get("outcome_description")
            guarantee = item.get("guarantee_description")
            quote = item.get("evidence", {}).get("quote")

            if not all(
                isinstance(x, str) and x.strip()
                for x in (outcome, guarantee, quote)
            ):
                raise AFAIControlActionError(
                    "Estructura inválida en control_guarantees."
                )

            proposition = (
                f"La respuesta garantiza el resultado '{outcome}' "
                f"de esta manera: {guarantee}"
            )

        else:
            raise AFAIControlActionError(
                f"Categoría simple desconocida: {category}"
            )

        quote = _resolve_quote(
            quote=quote,
            proposition=proposition,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        )

        validation = _validate_proposition(
            quote=quote,
            proposition=proposition,
            model=model,
            timeout=timeout,
            local_context=(
                current_ai
                if category == "control_guarantees"
                else None
            ),
        )

        if validation["status"] == "not_supported":
            continue

        processed = dict(item)

        processed["evidence"] = {
            "quote": quote.strip(),
            "source": EvidenceSource.CURRENT_AI.value,
        }

        processed["semantic_validation"] = validation

        output.append(processed)

    return output


# ============================================================
# TARGETS AF2
# ============================================================

def _process_stressor_targets(
    *,
    items: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:
    """
    Valida T de AF2 independientemente de A.

    Un stressor_target representa un componente del estresor que la
    RESPUESTA ACTUAL DE LA IA identifica como susceptible de acción,
    decisión, intervención o cambio.

    Esta función NO crea ni infiere una stressor_action.
    """

    output: list[dict[str, Any]] = []

    for item in items:

        if not isinstance(item, dict):
            raise AFAIControlActionError(
                "Cada stressor_target debe ser dict."
            )

        target = item.get("target_description")
        quote = item.get("evidence", {}).get("quote")

        if not all(
            isinstance(x, str) and x.strip()
            for x in (target, quote)
        ):
            raise AFAIControlActionError(
                "Estructura inválida en stressor_targets."
            )

        proposition = (
            "La respuesta identifica el componente "
            f"'{target}' del estresor como un aspecto sobre el cual "
            "la persona puede actuar, decidir, intervenir o realizar cambios."
        )

        # Un T independiente defectuoso NO debe invalidar acciones A/I
        # extraídas por separado. Solo se omite este T, nunca se
        # convierte una cita aproximada en evidencia aceptada.
        try:
            quote = _resolve_quote(
                quote=quote,
                proposition=proposition,
                current_ai=current_ai,
                model=model,
                timeout=timeout,
            )
        except AFAIControlActionError as exc:
            if "Evidencia IA inválida y no recuperable" not in str(exc):
                raise
            continue

        validation = _validate_proposition(
            quote=quote,
            proposition=proposition,
            model=model,
            timeout=timeout,
            local_context=current_ai,
        )

        # not_supported no sobrevive como evidencia de T.
        # ambiguous se conserva únicamente para trazabilidad;
        # el scorer no deberá contarlo como T confirmado.
        if validation["status"] == "not_supported":
            continue

        processed = dict(item)

        processed["evidence"] = {
            "quote": quote.strip(),
            "source": EvidenceSource.CURRENT_AI.value,
        }

        processed["semantic_validation"] = validation

        output.append(processed)

    return output


# ============================================================
# ACCIONES AF2
# ============================================================

def _process_actions(
    *,
    items: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:

    output: list[dict[str, Any]] = []

    for item in items:

        action = item.get("action_description")
        target = item.get("target_description")
        initiation = item.get("initiation_description")
        feasibility = item.get("feasibility")
        evidence = item.get("evidence", {})

        action_quote = evidence.get("action_quote")
        target_quote = evidence.get("target_quote")
        initiation_quote = evidence.get("initiation_quote")

        if (
            not isinstance(action, str)
            or not action.strip()
            or not isinstance(target, str)
            or not target.strip()
            or feasibility not in {
                "supported",
                "not_supported",
                "ambiguous",
            }
            or not isinstance(action_quote, str)
            or not action_quote.strip()
        ):
            raise AFAIControlActionError(
                "stressor_action con estructura inválida."
            )

        for quote in (
            action_quote,
            target_quote,
            initiation_quote,
        ):
            if quote is not None:
                if not isinstance(quote, str) or not quote.strip():
                    raise AFAIControlActionError(
                        "Quote opcional inválido en stressor_actions."
                    )

        action_proposition = (
            f"La respuesta propone la acción '{action}' "
            f"para actuar sobre '{target}'."
        )

        action_quote = _resolve_quote(
            quote=action_quote,
            proposition=action_proposition,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        )

        if isinstance(target_quote, str) and target_quote.strip():
            try:
                target_quote = _resolve_quote(
                    quote=target_quote,
                    proposition=(
                        f"La cita identifica '{target}' como el aspecto "
                        f"sobre el que actúa la acción '{action}'."
                    ),
                    current_ai=current_ai,
                    model=model,
                    timeout=timeout,
                )
            except AFAIControlActionError as exc:
                error_text = str(exc)
                if not ("Evidencia IA" in error_text and "no recuperable" in error_text):
                    raise
                target_quote = None

        # No fabricar una cita concatenando fragmentos independientes.
        # El contexto ayuda a interpretar, pero la evidencia sigue siendo literal.
        action_target_validation = _validate_proposition(
            quote=action_quote,
            proposition=action_proposition,
            model=model,
            timeout=timeout,
            local_context=current_ai,
        )

        if action_target_validation["status"] == "not_supported":
            continue

        initiation_result = extract_af2_initiation(
            current_ai=current_ai,
            action_description=action.strip(),
            target_description=target.strip(),
            provider=SEMANTIC_PROVIDER,
            model=model,
            timeout=timeout,
        )

        if initiation_result["has_initiation"]:
            initiation = initiation_result["initiation_description"]
            initiation_quote = initiation_result["quote"]
            initiation_validation = initiation_result[
                "semantic_validation"
            ]
        else:
            initiation = None
            initiation_quote = None
            initiation_validation = initiation_result[
                "semantic_validation"
            ]

        output.append(
            {
                "action_description": action.strip(),
                "target_description": target.strip(),
                "initiation_description": (
                    initiation.strip()
                    if isinstance(initiation, str)
                    else None
                ),
                "feasibility": feasibility,
                "evidence": {
                    "action_quote": action_quote.strip(),
                    "target_quote": (
                        target_quote.strip()
                        if isinstance(target_quote, str)
                        else None
                    ),
                    "initiation_quote": (
                        initiation_quote.strip()
                        if isinstance(initiation_quote, str)
                        else None
                    ),
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "semantic_validation": {
                    "action_target": action_target_validation,
                    "initiation": initiation_validation,
                },
            }
        )

    return output


# ============================================================
# GARANTÍAS DE RESULTADO AF2
# ============================================================

def _process_result_guarantees(
    *,
    items: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> list[dict[str, Any]]:

    output: list[dict[str, Any]] = []

    for item in items:

        action = item.get("action_description")
        result = item.get("guaranteed_result_description")
        quote = item.get("evidence", {}).get("quote")

        if not all(
            isinstance(x, str) and x.strip()
            for x in (action, result, quote)
        ):
            raise AFAIControlActionError(
                "result_guarantee con estructura inválida."
            )

        proposition = (
            f"La respuesta garantiza que la acción '{action}' "
            f"producirá el resultado '{result}'."
        )

        quote = _resolve_quote(
            quote=quote,
            proposition=proposition,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        )

        validation = _validate_proposition(
            quote=quote,
            proposition=proposition,
            model=model,
            timeout=timeout,
            local_context=current_ai,
        )

        if validation["status"] == "not_supported":
            continue

        output.append(
            {
                "action_description": action.strip(),
                "guaranteed_result_description": result.strip(),
                "evidence": {
                    "quote": quote.strip(),
                    "source": EvidenceSource.CURRENT_AI.value,
                },
                "semantic_validation": validation,
            }
        )

    return output


# ============================================================
# API PÚBLICA
# ============================================================

def extract_ai_control_action(
    *,
    current_ai: str,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:

    if not isinstance(current_ai, str):
        raise TypeError("current_ai debe ser str.")

    normalized_ai = current_ai.strip()

    empty_result = {
        "modifiable_orientations": [],
        "unmodifiable_orientations": [],
        "control_guarantees": [],
        "stressor_targets": [],
        "stressor_actions": [],
        "result_guarantees": [],
    }

    if not normalized_ai:
        return empty_result

    def execute() -> dict[str, list[dict[str, Any]]]:
        raw = _call_semantic_provider(
            current_ai=normalized_ai,
            provider=SEMANTIC_PROVIDER,
            model=model,
            timeout=timeout,
        )

        result = {
            "modifiable_orientations": _process_simple_category(
                items=raw["modifiable_orientations"],
                category="modifiable_orientations",
                current_ai=normalized_ai,
                model=model,
                timeout=timeout,
            ),

            "unmodifiable_orientations": _process_simple_category(
                items=raw["unmodifiable_orientations"],
                category="unmodifiable_orientations",
                current_ai=normalized_ai,
                model=model,
                timeout=timeout,
            ),

            "control_guarantees": _process_simple_category(
                items=raw["control_guarantees"],
                category="control_guarantees",
                current_ai=normalized_ai,
                model=model,
                timeout=timeout,
            ),

            "stressor_targets": _process_stressor_targets(
                items=raw["stressor_targets"],
                current_ai=normalized_ai,
                model=model,
                timeout=timeout,
            ),

            "stressor_actions": _process_actions(
                items=raw["stressor_actions"],
                current_ai=normalized_ai,
                model=model,
                timeout=timeout,
            ),

            "result_guarantees": _process_result_guarantees(
                items=raw["result_guarantees"],
                current_ai=normalized_ai,
                model=model,
                timeout=timeout,
            ),
        }

        id_prefixes = {
            "modifiable_orientations": "modifiable_orientation",
            "unmodifiable_orientations": "unmodifiable_orientation",
            "control_guarantees": "control_guarantee",
            "stressor_targets": "stressor_target",
            "stressor_actions": "stressor_action",
            "result_guarantees": "result_guarantee",
        }

        for category, prefix in id_prefixes.items():
            for index, item in enumerate(result[category], start=1):
                item["id"] = f"{prefix}_{index}"

        return result

    def validate_result(
        result: dict[str, list[dict[str, Any]]],
    ) -> dict[str, list[dict[str, Any]]]:

        if not isinstance(result, dict):
            raise AFAIControlActionError(
                "El resultado procesado debe ser un objeto."
            )

        expected_categories = {
            "modifiable_orientations",
            "unmodifiable_orientations",
            "control_guarantees",
            "stressor_targets",
            "stressor_actions",
            "result_guarantees",
        }

        if set(result) != expected_categories:
            raise AFAIControlActionError(
                "El resultado procesado contiene categorías inesperadas."
            )

        for category in expected_categories:
            if not isinstance(result[category], list):
                raise AFAIControlActionError(
                    f"{category} debe ser una lista."
                )

        return result

    return cached_semantic_operation(
        extractor="af_ai_control_action",
        extractor_version=CONTROL_ACTION_EXTRACTOR_VERSION,
        model=model,
        prompt_version=CONTROL_ACTION_PROMPT_VERSION,
        schema_version=CONTROL_ACTION_SCHEMA_VERSION,
        parameters={
            "provider": SEMANTIC_PROVIDER,
            "temperature": 0,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        inputs={
            "current_ai": normalized_ai,
        },
        execute=execute,
        validate_result=validate_result,
    )


# ============================================================
# HELPERS DETERMINISTAS
# ============================================================

def semantic_validation_is_confirmed(
    validation: dict[str, Any] | None,
) -> bool:
    return bool(
        validation
        and validation.get("status") == "supported"
    )


def action_target_is_confirmed(
    action: dict[str, Any],
) -> bool:
    validation = (
        action
        .get("semantic_validation", {})
        .get("action_target")
    )

    return semantic_validation_is_confirmed(validation)


def action_initiation_is_confirmed(
    action: dict[str, Any],
) -> bool:
    validation = (
        action
        .get("semantic_validation", {})
        .get("initiation")
    )

    return semantic_validation_is_confirmed(validation)
