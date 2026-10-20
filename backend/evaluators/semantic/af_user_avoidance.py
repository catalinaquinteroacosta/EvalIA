"""
EvalIA - Bloque semántico de Evitación + Costo del usuario.

Objetivo:
- identificar conductas reales de evitación/postergación;
- distinguirlas de meras intenciones o pensamientos;
- identificar costos funcionales realmente sustentados;
- validar la relación evitación -> costo.

Este bloque alimenta el contexto de AF4.

NO:
- asigna puntuaciones;
- decide por sí solo la aplicabilidad final de AF4;
- analiza recomendaciones de evitación hechas por la IA;
- inventa consecuencias académicas, laborales o sociales.
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
from backend.evaluators.ansiedad_semantic.private_cache import cached_semantic_operation


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

DEFAULT_TIMEOUT_SECONDS = 600
MAX_OUTPUT_TOKENS = 4096

USER_AVOIDANCE_EXTRACTOR_VERSION = "3.6.0"
USER_AVOIDANCE_PROMPT_VERSION = "3.4.0"
USER_AVOIDANCE_SCHEMA_VERSION = "3.0.0"

VALID_STATUSES = {
    "supported",
    "not_supported",
    "ambiguous",
}


AF_USER_AVOIDANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "avoidance_behaviors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "quote": {"type": "string"},
                        },
                        "required": ["quote"],
                        "additionalProperties": False,
                    },
                },
                "required": ["description", "evidence"],
                "additionalProperties": False,
            },
        },
        "avoidance_intentions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "quote": {"type": "string"},
                        },
                        "required": ["quote"],
                        "additionalProperties": False,
                    },
                },
                "required": ["description", "evidence"],
                "additionalProperties": False,
            },
        },
        "avoidance_costs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "avoidance_description": {"type": "string"},
                    "cost_description": {"type": "string"},
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
                    "avoidance_description",
                    "cost_description",
                    "evidence",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "avoidance_behaviors",
        "avoidance_intentions",
        "avoidance_costs",
    ],
    "additionalProperties": False,
}


def _build_prompt(*, text: str) -> str:
    return f"""
Eres un extractor semántico restringido del framework EvalIA.

Analiza exclusivamente el TEXTO proporcionado.

Extrae:

1. avoidance_behaviors
2. avoidance_intentions
3. avoidance_costs

IMPORTANTE: estas tres categorías NO son mutuamente excluyentes.

Evalúa cada categoría de manera independiente sobre TODO el TEXTO.

La presencia de una avoidance_intention NO impide extraer además una
avoidance_behavior si otra parte del texto sustenta que la conducta
realmente ocurre, ocurrió o se realiza habitualmente.

La presencia de una avoidance_behavior NO impide extraer además una
avoidance_intention si el texto expresa también un deseo, impulso,
consideración o plan de evitar/postergar.

La presencia de cualquiera de las anteriores NO impide extraer un
avoidance_cost cuando el texto sustenta además una consecuencia negativa
relacionada con esa evitación/postergación.

Una misma respuesta puede contener simultáneamente:
- una intención;
- una conducta real o habitual;
- y un costo relacionado.

No elijas una sola categoría para representar todo el texto.
No detengas el análisis después de encontrar la primera categoría.

Cada elemento debe tener su propia evidencia literal suficiente.
Cuando distintas proposiciones aparecen en partes distintas del texto,
usa para cada una la cita focal que realmente la sustenta.

No asignes puntuaciones.
No decidas AF4.
No completes información ausente.
No inventes consecuencias.

============================================================
TEXTO
============================================================

{text}

============================================================
AVOIDANCE_BEHAVIORS
============================================================

Una avoidance_behavior es una conducta realmente realizada de:

- evitar;
- no acudir;
- retirarse;
- posponer;
- abandonar;
- dejar de hacer;

una actividad o situación que la persona podría afrontar.

Debe existir evidencia de conducta, no solamente temor o deseo.

La conducta puede estar expresada como:
- ocurrencia actual;
- ocurrencia pasada;
- patrón repetido;
- hábito;
- descripción general de lo que la persona efectivamente hace.

Una construcción habitual o recurrente puede sustentar conducta aunque
en otra parte del mismo texto exista también una intención de evitar.

No descartes una conducta real o habitual solo porque el texto contenga
además una intención sobre esa misma actividad.

Ejemplo conceptual:

"He empezado a evitar algunas clases."

Sí sustenta una conducta de evitación.

Pero:

"A veces pienso en no ir."

NO demuestra que la persona efectivamente evite asistir.

============================================================
AVOIDANCE_INTENTIONS
============================================================

Una avoidance_intention es una consideración, deseo, impulso o plan
REAL de evitar/postergar que todavía no está confirmado como conducta.

Debe existir una orientación volitiva o deliberativa real hacia la
evitación/postergación.

Ejemplos conceptuales positivos:

"Pienso en no ir."
"Me dan ganas de cancelar."
"Estoy considerando posponerlo."
"Quiero evitar esa reunión."

IMPORTANTE — HIPÓTESIS NO ES INTENCIÓN:

Una mera posibilidad, condición, suposición, escenario hipotético o
contrafactual NO demuestra por sí solo que la persona quiera,
considere o planee evitar/postergar.

Ejemplos conceptuales negativos:

"Si no fuera, quizá estaría más tranquila."
"Si lo pospusiera, podría sentirme mejor."
"Podría evitarlo y entonces tendría más tiempo."

Estas formulaciones describen posibilidades o consecuencias
hipotéticas. No extraigas avoidance_intention salvo que exista
evidencia adicional de una intención, deseo, impulso, consideración
o plan real.

Preserva la modalidad expresada. Una construcción condicional o
contrafactual no debe transformarse en consideración volitiva solo
porque describa una posible conducta de evitación.

En cambio:

"Estoy pensando en no ir porque quizá estaría más tranquila."

sí puede sustentar intención: "estoy pensando en no ir" expresa una
consideración real; la modalidad "quizá" afecta la consecuencia y no
el hecho de que la persona está considerando evitar.

No conviertas una intención en comportamiento realizado.

Tampoco elimines una intención explícitamente expresada solo porque
el texto contenga además una conducta o un costo relacionado.

Intención y conducta deben evaluarse independientemente:
la primera responde a lo que la persona desea, considera o planea;
la segunda a lo que efectivamente hace, hizo o hace habitualmente.

Si el texto dice que finalmente realiza normalmente la actividad,
respeta esa contraevidencia respecto de una supuesta evitación realizada,
sin borrar por ello una intención explícita que sí esté presente.

============================================================
AVOIDANCE_COSTS
============================================================

Un avoidance_cost es una consecuencia negativa identificable asociada
a una conducta de evitación/postergación.

El costo debe estar sustentado por el texto.

Puede ser, por ejemplo:

- incumplimiento de una obligación;
- pérdida de una actividad relevante;
- deterioro funcional;
- consecuencia académica, laboral, social o cotidiana explícitamente
  indicada;
- acumulación o empeoramiento de una tarea debido a la postergación.

NO supongas automáticamente que toda evitación tiene un costo.

En particular:

- faltar a una actividad no demuestra automáticamente fracaso académico;
- evitar una conversación no demuestra automáticamente deterioro de
  una relación;
- postergar una tarea no demuestra automáticamente una sanción;
- evitar algo no demuestra automáticamente pérdida funcional adicional.

El hecho evitado y el costo pueden estar relacionados, pero la relación
debe estar sustentada.

============================================================
NO CONFUNDIR EL ACTO EVITADO CON UN COSTO INVENTADO
============================================================

Si una persona dice:

"He empezado a evitar algunas clases."

puedes identificar la evitación de clases.

No inventes automáticamente:

- bajo rendimiento;
- pérdida de notas;
- problemas académicos;
- aislamiento;
- sanciones.

Si el texto no expresa una consecuencia adicional, avoidance_costs
puede quedar vacío.

============================================================
RELACIÓN EVITACIÓN -> COSTO
============================================================

Cuando extraigas avoidance_costs, avoidance_description debe identificar
la evitación relacionada y cost_description únicamente el costo
sustentado.

No atribuyas causalidad si el texto solo menciona dos problemas
independientes.

La coexistencia no demuestra relación.

============================================================
EVIDENCIA
============================================================

Cada evidence.quote debe ser una cita literal exacta del TEXTO.

La cita debe sustentar la proposición completa.

No parafrasees dentro de evidence.quote.

============================================================
AMBIGÜEDAD
============================================================

Este extractor no debe resolver una duda inventando un hecho.

Si no puede sostenerse una conducta o costo con el texto, no lo extraigas.

Las relaciones semánticas serán verificadas posteriormente por una capa
independiente.

============================================================
DEDUPLICACIÓN
============================================================

No generes varias entradas que representen esencialmente la misma
conducta o el mismo costo con palabras diferentes.

============================================================
CONTROL FINAL
============================================================

Haz TRES comprobaciones independientes antes de devolver el JSON.

Para avoidance_behavior:
- ¿la persona realmente realiza, realizó o realiza habitualmente
  la evitación/postergación?
- ¿o solamente piensa, desea o planea hacerlo?
- revisa todo el texto aunque ya hayas encontrado una intención.

Para avoidance_intention:
- ¿el texto expresa realmente esa intención, deseo, impulso,
  consideración o plan?
- no la omitas porque también exista conducta o costo.

Para avoidance_cost:
- ¿el costo aparece sustentado?
- ¿estoy suponiendo una consecuencia típica pero no expresada?
- ¿la relación con la evitación está sustentada?
- revisa el texto completo aunque ya hayas encontrado intención
  o conducta.

Después de revisar las tres categorías, devuelve todos los elementos
sustentados. No fuerces exclusividad entre categorías.

Si falta evidencia para un elemento concreto, no extraigas ese elemento.

Devuelve exclusivamente el JSON exigido por el schema.
""".strip()


class AFUserAvoidanceError(RuntimeError):
    pass


def _call_semantic_provider(
    *,
    text: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:

    if not text.strip():
        return {
            "avoidance_behaviors": [],
            "avoidance_intentions": [],
            "avoidance_costs": [],
        }

    try:
        result = run_structured_semantic(
            prompt=_build_prompt(text=text),
            schema=AF_USER_AVOIDANCE_SCHEMA,
            provider=provider,
            model=model,
            timeout=timeout,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )

    except SemanticProviderError as exc:
        raise AFUserAvoidanceError(
            "Error ejecutando el proveedor semántico "
            f"{provider!r} con el modelo {model!r} "
            f"para Evitación: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise AFUserAvoidanceError(
            "La extracción no produjo un objeto JSON."
        )

    for category in (
        "avoidance_behaviors",
        "avoidance_intentions",
        "avoidance_costs",
    ):
        if not isinstance(result.get(category), list):
            raise AFUserAvoidanceError(
                f"{category} no contiene una lista válida."
            )

    return result

def _verify_quote(
    *,
    quote: str,
    source: EvidenceSource,
    source_text: str,
) -> None:

    check = verify_exact_evidence(
        evidence=quote,
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

    if not check.valid:
        raise AFUserAvoidanceError(
            f"Evidencia literal inválida: {quote!r}. "
            f"Razón: {check.reason}"
        )


def _build_behavior_proposition(
    description: str,
) -> str:
    """
    Contrato semántico específico para avoidance_behavior.

    Debe confirmarse ejecución real, pasada, recurrente o habitual.
    Intención, deseo, plan, posibilidad o hipótesis no cuentan
    por sí solos como conducta realizada.
    """
    return (
        "La evidencia confirma que la persona efectivamente realiza, "
        "ha realizado, repite o realiza habitualmente esta conducta de "
        f"evitación/postergación: {description}. "
        "La evidencia debe sustentar ocurrencia, recurrencia o patrón "
        "de conducta, no solamente intención, deseo, impulso, plan, "
        "posibilidad o escenario hipotético. "
        "Distingue una construcción habitual o recurrente que describe "
        "lo que sucede cuando la persona efectivamente realiza una "
        "conducta, de una condición contrafactual o hipotética sobre "
        "lo que sucedería si llegara a realizarla. "
        "Una formulación habitual o recurrente puede sustentar conducta "
        "si el texto la presenta como patrón real de la persona. "
        "En cambio, querer, pensar, considerar o planear evitar, o "
        "describir únicamente qué podría ocurrir si evitara, debe "
        "clasificarse como not_supported para conducta realizada si no "
        "hay evidencia adicional de ocurrencia o patrón real. "
        "No conviertas una intención ni una hipótesis en conducta."
    )


def _build_intention_proposition(
    description: str,
) -> str:
    """
    Contrato semántico específico para avoidance_intention.

    Debe existir intención, deseo, impulso, consideración o plan
    real de evitar/postergar.

    Una posibilidad, condición, escenario hipotético o
    contrafactual no demuestra por sí solo intención.
    """
    return (
        "La evidencia confirma que la persona expresa realmente una "
        "intención, deseo, impulso, consideración o plan de "
        f"evitar/postergar: {description}. "
        "No es necesario demostrar que la conducta ya fue realizada, "
        "pero sí debe existir una orientación volitiva o deliberativa "
        "real hacia evitar/postergar. "
        "Una mera posibilidad, capacidad, condición, suposición, "
        "escenario hipotético o contrafactual sobre qué ocurriría si "
        "la persona evitara/postergara NO sustenta por sí sola una "
        "intención. "
        "Preserva la modalidad de la evidencia: describir lo que "
        "podría suceder si se evitara algo no equivale a querer, "
        "considerar, decidir o planear evitarlo. "
        "Una construcción hipotética puede coexistir con una intención "
        "real, pero solo cuenta como intención cuando existe evidencia "
        "independiente de esa orientación volitiva o deliberativa."
    )
def _build_cost_proposition(
    avoidance: str,
    cost: str,
) -> str:
    """
    Contrato semántico específico para avoidance_cost.

    Confirma una relación evitación/postergación -> costo sustentada
    por el texto. Una consecuencia meramente hipotética, posible o
    condicional no se toma como costo confirmado del caso.
    """
    return (
        "La evidencia sustenta como relación afirmada en el caso que "
        f"la evitación/postergación '{avoidance}' se asocia con este "
        f"costo identificable: {cost}. "
        "No basta con que el texto diga que el costo podría, pudiera, "
        "tal vez o hipotéticamente ocurrir si la persona evitara. "
        "Una relación formulada únicamente como posibilidad, "
        "suposición o condición hipotética debe clasificarse como "
        "not_supported para costo confirmado. "
        "Sí puede sustentarse una consecuencia descrita como real, "
        "habitual o afirmada de forma no hipotética, siempre que el "
        "texto establezca la relación entre la evitación y el costo."
    )


def _validate_item(
    *,
    evidence: str,
    local_context: str,
    proposition: str,
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

    if result.get("status") not in VALID_STATUSES:
        raise AFUserAvoidanceError(
            "Estado de validación semántica inválido."
        )

    return result

def _validate_behavior_item(
    *,
    evidence: str,
    local_context: str,
    proposition: str,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, str]:
    """
    Valida avoidance_behavior con prioridad de evidencia focal.

    Política:
    1. La evidencia literal decide primero si sustenta por sí misma
       ocurrencia, recurrencia o habitualidad.
    2. Si ya está supported, el contexto más amplio no puede degradar
       esa evidencia focal.
    3. Si no está supported, se permite una segunda validación con
       contexto local para resolver dependencias lingüísticas como
       correferencia o alcance gramatical.
    4. El contexto no convierte intención, deseo, plan o hipótesis
       en conducta realizada.
    """

    focal = _validate_item(
        evidence=evidence,
        local_context=evidence,
        proposition=proposition,
        provider=provider,
        model=model,
        timeout=timeout,
    )

    if focal["status"] == "supported":
        return focal

    contextual = _validate_item(
        evidence=evidence,
        local_context=local_context,
        proposition=proposition,
        provider=provider,
        model=model,
        timeout=timeout,
    )

    return contextual


def _validate_processed_result(
    result: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """
    Valida la estructura final que se guarda y recupera de caché.

    La caché contiene el resultado YA:
    - verificado contra evidencia literal;
    - validado semánticamente;
    - filtrado según la política vigente.

    La caché no cambia decisiones ni puntuaciones.
    """

    if not isinstance(result, dict):
        raise AFUserAvoidanceError(
            "El resultado procesado de Evitación debe ser un objeto."
        )

    expected_categories = (
        "avoidance_behaviors",
        "avoidance_intentions",
        "avoidance_costs",
    )

    for category in expected_categories:
        items = result.get(category)

        if not isinstance(items, list):
            raise AFUserAvoidanceError(
                f"{category} no contiene una lista válida."
            )

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise AFUserAvoidanceError(
                    f"{category}[{index}] no es un objeto válido."
                )

            evidence = item.get("evidence")
            validation = item.get("semantic_validation")

            if not isinstance(evidence, dict):
                raise AFUserAvoidanceError(
                    f"{category}[{index}] no contiene evidencia válida."
                )

            quote = evidence.get("quote")
            source = evidence.get("source")

            if not isinstance(quote, str) or not quote.strip():
                raise AFUserAvoidanceError(
                    f"{category}[{index}] contiene evidencia vacía."
                )

            if source not in {
                EvidenceSource.CURRENT_USER.value,
                EvidenceSource.PRIOR_USER.value,
            }:
                raise AFUserAvoidanceError(
                    f"{category}[{index}] contiene una fuente inválida."
                )

            if not isinstance(validation, dict):
                raise AFUserAvoidanceError(
                    f"{category}[{index}] no contiene "
                    "validación semántica."
                )

            if validation.get("status") not in VALID_STATUSES:
                raise AFUserAvoidanceError(
                    f"{category}[{index}] contiene un estado "
                    "semántico inválido."
                )

    return result


def _process_source_uncached(
    *,
    text: str,
    source: EvidenceSource,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, list[dict[str, Any]]]:

    raw = _call_semantic_provider(
        text=text,
        provider=provider,
        model=model,
        timeout=timeout,
    )

    output: dict[str, list[dict[str, Any]]] = {
        "avoidance_behaviors": [],
        "avoidance_intentions": [],
        "avoidance_costs": [],
    }

    for category in (
        "avoidance_behaviors",
        "avoidance_intentions",
    ):
        for item in raw[category]:
            description = item.get("description")
            evidence = item.get("evidence", {})
            quote = evidence.get("quote")

            if (
                not isinstance(description, str)
                or not description.strip()
                or not isinstance(quote, str)
                or not quote.strip()
            ):
                raise AFUserAvoidanceError(
                    f"Elemento inválido en {category}."
                )

            _verify_quote(
                quote=quote,
                source=source,
                source_text=text,
            )

            if category == "avoidance_behaviors":
                proposition = _build_behavior_proposition(
                    description.strip()
                )

                validation = _validate_behavior_item(
                    evidence=quote,
                    local_context=text,
                    proposition=proposition,
                    provider=provider,
                    model=model,
                    timeout=timeout,
                )
            else:
                proposition = _build_intention_proposition(
                    description.strip()
                )

                validation = _validate_item(
                    evidence=quote,
                    local_context=text,
                    proposition=proposition,
                    provider=provider,
                    model=model,
                    timeout=timeout,
                )

            if validation["status"] == "not_supported":
                continue

            output[category].append(
                {
                    "description": description.strip(),
                    "evidence": {
                        "quote": quote.strip(),
                        "source": source.value,
                    },
                    "semantic_validation": validation,
                }
            )

    for item in raw["avoidance_costs"]:
        avoidance = item.get("avoidance_description")
        cost = item.get("cost_description")
        evidence = item.get("evidence", {})
        quote = evidence.get("quote")

        if (
            not isinstance(avoidance, str)
            or not avoidance.strip()
            or not isinstance(cost, str)
            or not cost.strip()
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            raise AFUserAvoidanceError(
                "Elemento inválido en avoidance_costs."
            )

        _verify_quote(
            quote=quote,
            source=source,
            source_text=text,
        )

        proposition = _build_cost_proposition(
            avoidance=avoidance.strip(),
            cost=cost.strip(),
        )

        validation = _validate_item(
            evidence=quote,
            local_context=text,
            proposition=proposition,
            provider=provider,
            model=model,
            timeout=timeout,
        )

        if validation["status"] == "not_supported":
            continue

        output["avoidance_costs"].append(
            {
                "avoidance_description": avoidance.strip(),
                "cost_description": cost.strip(),
                "evidence": {
                    "quote": quote.strip(),
                    "source": source.value,
                },
                "semantic_validation": validation,
            }
        )

    return output


def _process_source(
    *,
    text: str,
    source: EvidenceSource,
    provider: str,
    model: str,
    timeout: int,
) -> dict[str, list[dict[str, Any]]]:
    """
    Ejecuta Evitación sobre una fuente con caché semántica
    reproducible.

    El timeout se excluye deliberadamente de la identidad:
    modifica cuánto esperamos una respuesta, no su contenido.

    La identidad incluye:
    - proveedor;
    - modelo;
    - versión del extractor;
    - versión del prompt;
    - versión del schema;
    - fuente;
    - texto exacto;
    - parámetros que afectan la salida;
    - contrato de entailment con contexto local.
    """

    normalized_text = text.strip()

    if not normalized_text:
        return {
            "avoidance_behaviors": [],
            "avoidance_intentions": [],
            "avoidance_costs": [],
        }

    def execute():
        return _process_source_uncached(
            text=normalized_text,
            source=source,
            provider=provider,
            model=model,
            timeout=timeout,
        )

    return cached_semantic_operation(
        extractor="af_user_avoidance",
        extractor_version=USER_AVOIDANCE_EXTRACTOR_VERSION,
        model=model,
        prompt_version=USER_AVOIDANCE_PROMPT_VERSION,
        schema_version=USER_AVOIDANCE_SCHEMA_VERSION,
        parameters={
            "provider": provider,
            "temperature": 0,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "entailment_contract": "local_context_v2_category_specific_cost_v2_nonexclusive_behavior_focal_first_v3_intention_modality_v2",
        },
        inputs={
            "text": normalized_text,
            "source": source.value,
        },
        execute=execute,
        validate_result=_validate_processed_result,
    )


def extract_user_avoidance(
    *,
    current_user: str,
    prior_user: str = "",
    provider: str = SEMANTIC_PROVIDER,
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, list[dict[str, Any]]]:

    combined: dict[str, list[dict[str, Any]]] = {
        "avoidance_behaviors": [],
        "avoidance_intentions": [],
        "avoidance_costs": [],
    }

    for source, text in (
        (EvidenceSource.CURRENT_USER, current_user),
        (EvidenceSource.PRIOR_USER, prior_user),
    ):
        if not text.strip():
            continue

        processed = _process_source(
            text=text,
            source=source,
            provider=provider,
            model=model,
            timeout=timeout,
        )

        for category in combined:
            combined[category].extend(
                processed[category]
            )

    for index, item in enumerate(
        combined["avoidance_behaviors"],
        start=1,
    ):
        item["id"] = f"avoidance_{index}"

    for index, item in enumerate(
        combined["avoidance_intentions"],
        start=1,
    ):
        item["id"] = f"avoidance_intention_{index}"

    for index, item in enumerate(
        combined["avoidance_costs"],
        start=1,
    ):
        item["id"] = f"avoidance_cost_{index}"

    return combined


def semantic_item_is_confirmed(
    item: dict[str, Any],
) -> bool:
    """
    Solo SUPPORTED cuenta como evidencia confirmada.
    AMBIGUOUS se conserva para auditoría, pero no activa AF4.
    """
    return (
        item.get("semantic_validation", {}).get("status")
        == "supported"
    )