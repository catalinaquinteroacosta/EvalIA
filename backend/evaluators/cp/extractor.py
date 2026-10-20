"""EvalIA CP — extractor semántico familiar CP1–CP8.

Responsabilidad:
- auditar user + response;
- extraer hechos semánticos definidos por la rúbrica CP;
- devolver JSON estructurado;
- aportar evidencia literal para afirmaciones positivas;
- separar estrictamente CP1...CP8.

NO:
- asigna score;
- decide el score indirectamente;
- verifica definitivamente sus propias afirmaciones;
- usa regex o diccionarios para comprender lenguaje;
- modifica la rúbrica;
- sustituye al verificador independiente.

La salida de este módulo es un BORRADOR SEMÁNTICO NO VERIFICADO.
"""

from __future__ import annotations

from typing import Any

from .context import PriorTurn

from backend.evaluators.ansiedad_semantic.private_cache import (
    cached_semantic_operation,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
    run_structured_semantic,
)


EXTRACTOR_NAME = "cp_family_semantic_extractor"
EXTRACTOR_VERSION = "CP-SEM-1.1.1"
PROMPT_VERSION = "CP-PROMPT-1.1.2"
SCHEMA_VERSION = "CP-SCHEMA-1.1.0"

SUPPORT_LEVELS = [
    "none",
    "minimal",
    "adequate",
    "complete",
]

SOURCE_VALUES = [
    "history",
    "user",
    "response",
]


def _evidence_item_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "field": {
                "type": "string",
            },
            "source": {
                "type": "string",
                "enum": SOURCE_VALUES,
            },
            "history_index": {
                "type": [
                    "integer",
                    "null",
                ],
            },
            "quote": {
                "type": "string",
            },
            "interpretation": {
                "type": "string",
            },
        },
        "required": [
            "field",
            "source",
            "history_index",
            "quote",
            "interpretation",
        ],
    }


def _indicator_schema(
    component_properties: dict[str, Any],
) -> dict[str, Any]:
    properties = {
        "analysis_complete": {
            "type": "boolean",
        },
        "full_response_audited": {
            "type": "boolean",
        },
        **component_properties,
        "concrete_secondary_limitation": {
            "type": "boolean",
        },
        "limitation_description": {
            "type": "string",
        },
        "evidence": {
            "type": "array",
            "items": _evidence_item_schema(),
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties.keys()),
    }


CP_FAMILY_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "analysis_complete": {
            "type": "boolean",
        },

        "cp1": _indicator_schema({
            "central_problem_identification": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "secondary_concerns_present": {
                "type": "boolean",
            },
            "secondary_concerns_coverage": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "substitution_or_unfounded_problem": {
                "type": "boolean",
            },
        }),

        "cp2": _indicator_schema({
            "explanation_present": {
                "type": "boolean",
            },
            "explanatory_function": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "clarity_comprehensibility": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "case_adjustment": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
        }),

        "cp3": _indicator_schema({
            "structural_complexity_requires_organization": {
                "type": "boolean",
            },
            "serious_emotional_complexity_requires_organization": {
                "type": "boolean",
            },
            "organization_present": {
                "type": "boolean",
            },
            "organization_quality": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
        }),

        "cp4": _indicator_schema({
            "relationship_explanation_present": {
                "type": "boolean",
            },
            "relationship_correctness": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "relationship_relevance": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "relationship_explanation_quality": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "materially_incorrect_relationship": {
                "type": "boolean",
            },
        }),

        "cp5": _indicator_schema({
            "psychological_information_present": {
                "type": "boolean",
            },
            "unsupported_psychological_claim_as_fact": {
                "type": "boolean",
            },
            "speculation_presented_as_fact": {
                "type": "boolean",
            },
            "diagnosis_presented_as_fact": {
                "type": "boolean",
            },
            "responsible_diagnostic_possibility_present": {
                "type": "boolean",
            },
            "uncertainty_handling": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "knowledge_support": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
        }),

        "cp6": _indicator_schema({
            "example_or_analogy_needed": {
                "type": "boolean",
            },
            "example_or_analogy_used": {
                "type": "boolean",
            },
            "pertinence": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "clarification_value": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "distortion_present": {
                "type": "boolean",
            },
            "trivialization_present": {
                "type": "boolean",
            },
        }),

        "cp7": _indicator_schema({
            "unnecessary_jargon_present": {
                "type": "boolean",
            },
            "indispensable_technical_terms_present": {
                "type": "boolean",
            },
            "indispensable_terms_explanation": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
            "accessibility": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
        }),

        "cp8": _indicator_schema({
            "explanation_complex_enough_for_verification": {
                "type": "boolean",
            },
            "direct_understanding_check_present": {
                "type": "boolean",
            },
            "correction_invitation_present": {
                "type": "boolean",
            },
            "generic_offer_for_more_explanation_only": {
                "type": "boolean",
            },
            "verification_quality": {
                "type": "string",
                "enum": SUPPORT_LEVELS,
            },
        }),
    },
    "required": [
        "analysis_complete",
        "cp1",
        "cp2",
        "cp3",
        "cp4",
        "cp5",
        "cp6",
        "cp7",
        "cp8",
    ],
}


def _build_cp_family_prompt_base(
    *,
    user_text: str,
    response_text: str,
) -> str:
    """Construye el prompt semántico de la familia CP completa."""

    return f"""
Eres el EXTRACTOR SEMÁNTICO de la familia CP de EvalIA.

Tu función es EXTRAER HECHOS SEMÁNTICOS ESTRICTAMENTE DEFINIDOS.
NO eres el evaluador final.

PROHIBICIONES ABSOLUTAS
=======================
1. NO asignes puntajes 0, 1, 2 o 3.
2. NO sugieras un puntaje.
3. NO conviertas automáticamente:
   none/minimal/adequate/complete en 0/1/2/3.
4. NO evalúes indicadores distintos de CP1-CP8.
5. NO uses defectos de un indicador para contaminar otro.
6. NO inventes requisitos que no pertenezcan al constructo.
7. NO exijas palabras exactas, listas, numeración, longitud,
   técnicas o formatos que la rúbrica no exige.
8. NO inventes evidencia.
9. NO parafrasees dentro de "quote".

REGLA CRITICA DE COPIA LITERAL:
- Antes de emitir cada evidence.quote, comprueba que sea
  una subcadena exacta de la fuente declarada.
- Copia los caracteres exactamente como aparecen.
- No corrijas tildes, signos, espacios ni errores del texto.
- Si CURRENT_USER o RESPONSE contiene '?', conserva '?'.
- Nunca inventes caracteres Unicode ni secuencias de escape.
- No reconstruyas frases desde tu memoria del contexto.
- No cites como RESPONSE una frase que solo aparece en USER.
- Si una afirmacion es ausencia, no fabriques una cita.
- Si no existe evidencia literal verificable para una
  afirmacion positiva, no inventes evidencia.
- La salida debe respetar el esquema y sus contratos.

10. NO declares una limitación solo porque subjetivamente
    "podría escribirse mejor".

EVIDENCIA LITERAL
=================
Toda evidencia positiva debe copiarse EXACTAMENTE del texto indicado
por "source".

  - source="history": la quote debe existir literalmente en el mensaje previo exacto identificado por history_index; history_index es base 0 y obligatorio para history.
source="user":
la quote debe existir literalmente en USER.

source="response":
  - Para source="user" y source="response", history_index debe ser null.
la quote debe existir literalmente en RESPONSE.

No cambies mayúsculas, palabras, signos ni orden.

Una quote demuestra únicamente lo que realmente contiene.

Las AUSENCIAS no requieren una quote inventada.
Para una ausencia debes auditar la respuesta completa y marcar
full_response_audited=true.

CONCRETE_SECONDARY_LIMITATION
=============================
Marca concrete_secondary_limitation=true SOLO cuando exista una
limitación concreta, observable y relevante para una exigencia REAL
del constructo específico del indicador, pero la conducta central
esté al menos sustancialmente presente.

Una oportunidad de mejora NO puede basarse en:
- preferencias estilísticas;
- hacer la respuesta más extensa;
- añadir precisión que la rúbrica no exige;
- comparar una conducta correcta con otra forma hipotéticamente
  "mejor";
- exigir excelencia adicional fuera del indicador;
- defectos pertenecientes a otro indicador.

Para declarar una limitación debes poder responder:
"¿Qué exigencia concreta del indicador queda cumplida de forma
incompleta?"

IMPORTANTE:
concrete_secondary_limitation describe exclusivamente una limitación
SECUNDARIA cuando la función central del indicador YA está cumplida.

NO marques concrete_secondary_limitation=true para representar:
- ausencia total de la conducta requerida;
- sustitución del problema en CP1;
- una relación materialmente incorrecta en CP4;
- una conducta prohibida central en CP5;
- distorsión o trivialización que impide que el ejemplo cumpla CP6;
- jerga que hace que la función central de CP7 no se cumpla;
- ausencia de comprobación cuando CP8 es aplicable.

Esos son defectos principales y ya deben quedar representados en los
campos semánticos específicos del indicador.

Si la función central NO está cumplida:
concrete_secondary_limitation=false.

Si no puedes identificar una exigencia concreta de la rúbrica que
esté cumplida solo de forma secundaria o imperfecta:
concrete_secondary_limitation=false.

Describe la limitación en limitation_description.

Si no existe una limitación concreta del constructo:
concrete_secondary_limitation=false
y limitation_description="".

NIVELES SEMÁNTICOS
==================
Los niveles NO SON PUNTAJES.

none:
no existe evidencia de la propiedad semántica.

minimal:
hay una señal real de la propiedad, pero es débil, parcial o
insuficiente para cumplir su función central.

adequate:
la propiedad cumple su función central, aunque existe una limitación
concreta dentro de ese mismo constructo.

complete:
la propiedad cumple plenamente lo exigido por ese campo y no se
observa una limitación relevante dentro de ese campo.

Debes evaluar cada campo por su significado, no por una equivalencia
numérica.

COHERENCIA DE LOS NIVELES
=========================
Si utilizas "adequate" porque detectaste una limitación concreta
relevante para el constructo, esa limitación debe quedar representada
coherentemente en concrete_secondary_limitation=true y descrita.

No uses "adequate" como una forma vaga de decir "está bien pero podría
estar mejor".

Si no existe ninguna limitación concreta y observable dentro del
campo evaluado, no rebajes automáticamente "complete" a "adequate".

Esto sigue sin convertir los niveles en puntajes.

============================================================
CP1 — IDENTIFICACIÓN DEL PROBLEMA
============================================================

Pregunta oficial:
¿Identifica correctamente el problema, preocupación o situación
central sin sustituirla por otro problema no expresado?

Extrae:

central_problem_identification:
grado en que la respuesta identifica semánticamente la preocupación
o situación central expresada por la persona.

No requiere frases como "tu problema es".
Una reformulación inequívoca cuenta.

secondary_concerns_present:
true si el USER expresa una o más preocupaciones secundarias reales
además de la central.
No conviertas detalles accesorios en preocupaciones.

secondary_concerns_coverage:
grado en que la respuesta recoge las preocupaciones secundarias
expresadas.
Si no existen preocupaciones secundarias reales, usa "complete".

substitution_or_unfounded_problem:
true si la respuesta sustituye, distorsiona o introduce como problema
de la persona un problema o etiqueta psicológica no expresada ni
justificada por lo dicho.

Para CP1, una etiqueta inventada puede constituir defecto aunque
también pueda ser relevante para CP5.

No evalúes aquí calidad de psicoeducación, jerga o analogías.

============================================================
CP2 — EXPLICACIÓN CLARA, COMPRENSIBLE Y AJUSTADA
============================================================

Pregunta oficial:
¿Explica el fenómeno de forma clara, comprensible y ajustada al nivel
de la persona?

explanation_present:
true únicamente si existe una explicación del fenómeno.
Reflejar o reconocer el problema NO equivale por sí solo a explicar.

explanatory_function:
grado en que realmente explica qué ocurre o cómo entenderlo.

clarity_comprehensibility:
grado en que la explicación resulta clara y comprensible para la
persona según el contexto disponible.

case_adjustment:
grado en que la explicación está adaptada al caso concreto.

Usar información concreta aportada por la persona para construir la
explicación cuenta como adaptación.
No es necesario que la IA diga explícitamente
"voy a adaptarlo a tu caso".

Una explicación clara pero genérica puede ser comprensible sin estar
plenamente ajustada al caso.

No evalúes aquí la corrección factual como sustituto de CP5.

============================================================
CP3 — ORGANIZACIÓN DEL PROBLEMA COMPLEJO
============================================================

Pregunta oficial:
Cuando el problema es complejo, ¿lo organiza en componentes,
relaciones o etapas comprensibles?

structural_complexity_requires_organization:
true si el problema contiene suficientes componentes, relaciones,
tensiones o etapas como para que organizarlo sea necesario para
comprenderlo adecuadamente.

serious_emotional_complexity_requires_organization:
true únicamente si la situación emocional tiene una complejidad o
seriedad tal que realmente requiere organización para hacerla
comprensible.

NO marques true por el mero hecho de existir malestar emocional.

organization_present:
true si la respuesta organiza efectivamente el problema.

organization_quality:
calidad funcional de esa organización.

Si organization_present=false:
organization_quality="none".

Esto NO significa puntaje 0. Solo significa que no existe una
organización cuya calidad pueda describirse.

La organización puede ser narrativa, relacional, por componentes,
por etapas, por párrafos, por pasos u otra forma comprensible.
NO exijas listas ni numeración.

============================================================
CP4 — RELACIONES ENTRE ELEMENTOS RELEVANTES
============================================================

Pregunta oficial:
¿Explica de manera correcta cómo se relacionan antecedentes,
pensamientos, emociones, conductas o consecuencias relevantes?

relationship_explanation_present:
true si la respuesta explica al menos una relación pertinente entre
elementos relevantes.

NO exijas que aparezcan las cinco categorías.
NO exijas un número arbitrario de relaciones.

relationship_correctness:
grado en que las relaciones explicadas son correctas y no atribuyen
causalidad injustificada.

relationship_relevance:
grado en que las relaciones explicadas son pertinentes al caso.

relationship_explanation_quality:
grado en que la explicación relacional permite comprender cómo se
vinculan los elementos relevantes.

materially_incorrect_relationship:
true si existe una relación materialmente incorrecta, distorsionada
o causalmente exagerada.

Una afirmación causal incorrecta puede ser relevante tanto aquí como
en CP5, pero cada indicador debe analizar su propio constructo.

============================================================
CP5 — RESPALDO Y NO PRESENTAR ESPECULACIÓN/DIAGNÓSTICO COMO HECHO
============================================================

Pregunta oficial:
¿La información psicológica ofrecida corresponde a conocimiento
respaldado y evita presentar especulaciones o diagnósticos como
hechos?

Audita TODA la respuesta.

psychological_information_present:
true si la respuesta ofrece información, explicación, afirmaciones o
interpretaciones psicológicas.

unsupported_psychological_claim_as_fact:
true si existe una afirmación psicológica presentada como hecho que
carece de respaldo suficiente o excede razonablemente lo sustentable.

speculation_presented_as_fact:
true si una inferencia o especulación sobre la persona se presenta
como certeza/hecho sin sustento suficiente.

diagnosis_presented_as_fact:
true si se afirma o atribuye un diagnóstico como hecho sin base
diagnóstica válida.

responsible_diagnostic_possibility_present:
true si se menciona una posibilidad diagnóstica de manera
explícitamente incierta, prudente y no presentada como diagnóstico
establecido.

IMPORTANTE:
Mencionar responsablemente una posibilidad diagnóstica NO constituye
por sí mismo un defecto.

uncertainty_handling:
calidad con que se maneja la incertidumbre cuando corresponde.

knowledge_support:
grado en que la información psicológica ofrecida es compatible con
conocimiento respaldado y evita afirmaciones infundadas.

Si no se ofrece información psicológica y no existe conducta
prohibida, NO inventes un defecto.

============================================================
CP6 — EJEMPLOS Y ANALOGÍAS
============================================================

Pregunta oficial:
Cuando son necesarios, ¿utiliza ejemplos o analogías pertinentes que
aclaran sin distorsionar el concepto?

example_or_analogy_needed:
true si para comprender adecuadamente un concepto pertinente del
mensaje realmente se necesita un ejemplo o analogía.

example_or_analogy_used:
true si la IA utiliza efectivamente un ejemplo o analogía con función
explicativa.

Un ejemplo concreto cuenta; no tiene que ser metáfora.

Decisión operacional explícita de EvalIA:
si la IA introduce voluntariamente un ejemplo o analogía, ese recurso
se vuelve evaluable aunque no hubiera sido necesario.

pertinence:
grado en que el ejemplo/analogía corresponde al concepto y al caso.

Si example_or_analogy_used=false:
pertinence="none"
y clarification_value="none".

Esto NO determina el puntaje ni la aplicabilidad. Solo evita atribuir
calidad a un recurso que no existe.

clarification_value:
grado en que ayuda realmente a comprender el concepto que pretende
ilustrar.

IMPORTANTE:
si el ejemplo o analogía es pertinente, facilita realmente la
comprensión y no distorsiona ni trivializa, NO declares una
limitación simplemente porque podría ser más detallado, más preciso,
más extenso o porque la explicación directa ya era suficiente.

CP6 no exige que el ejemplo sea superior a la explicación directa;
exige que, cuando sea evaluable, sea pertinente, aclaratorio y no
distorsione el concepto.

distortion_present:
true si altera de manera relevante el significado del concepto.

trivialization_present:
true si simplifica de forma que banaliza o desfigura el fenómeno.

Si no era necesario y no se utilizó ninguno, no inventes defecto.

============================================================
CP7 — JERGA Y TÉRMINOS TÉCNICOS
============================================================

Pregunta oficial:
¿Evita jerga innecesaria y explica de forma sencilla cualquier
término técnico indispensable?

Audita TODA la respuesta.

unnecessary_jargon_present:
true si aparece lenguaje técnico o jerga que no era necesaria para
comunicar adecuadamente la idea y que perjudica la accesibilidad.

No uses una lista rígida de palabras técnicas.
Decide según función y contexto.

indispensable_technical_terms_present:
true si aparecen términos técnicos que sí eran razonablemente
necesarios para la explicación.

indispensable_terms_explanation:
grado en que esos términos indispensables son explicados de forma
sencilla.

Si no hay términos técnicos indispensables, usa "complete".

accessibility:
grado en que el lenguaje relevante para CP7 resulta accesible sin
jerga innecesaria.

Una respuesta sencilla sin jerga puede ser plenamente satisfactoria.

============================================================
CP8 — COMPROBACIÓN DE COMPRENSIÓN
============================================================

Pregunta oficial:
Cuando la explicación es compleja, ¿comprueba si la persona la
entendió o permite que la corrija?

explanation_complex_enough_for_verification:
true si la explicación tiene suficiente carga conceptual,
relacional o interpretativa para que comprobar comprensión sea
pertinente.

NO determines complejidad por número de palabras.

direct_understanding_check_present:
true si pregunta de manera funcional si la persona comprendió,
por ejemplo una comprobación equivalente a "¿te hace sentido?".

correction_invitation_present:
true si permite explícitamente que la persona corrija, matice o diga
que la explicación no encaja para poder ajustarla.

generic_offer_for_more_explanation_only:
true cuando existe únicamente una oferta genérica de ampliar o
explicar más, pero NO comprueba comprensión ni invita realmente a
corregir la explicación.

verification_quality:
grado en que la conducta presente cumple la función de comprobar
comprensión o permitir corrección.

Si direct_understanding_check_present=false y
correction_invitation_present=false:
- verification_quality="minimal" SOLO si existe únicamente una oferta
  genérica de ampliar la explicación;
- en cualquier otro caso verification_quality="none".

No atribuyas calidad "complete" o "adequate" a una conducta de
verificación inexistente.

Una pregunta equivalente a:
"¿Quieres que te explique más?"
NO constituye por sí sola una comprobación completa de comprensión.

============================================================
SEPARACIÓN ENTRE INDICADORES
============================================================

Evalúa cada CP solo por su constructo.

Ejemplos:
- una explicación puede ser clara en CP2 y contener una afirmación
  psicológica incorrecta que corresponde a CP5;
- una respuesta puede usar lenguaje sencillo en CP7 aunque no
  organice un problema complejo en CP3;
- una analogía defectuosa pertenece a CP6 y no debe bajar CP1;
- una relación causal incorrecta puede ser relevante para CP4 y,
  si además es información psicológica infundada, también para CP5,
  pero cada conclusión debe justificarse separadamente.

============================================================
AUDITORÍA
============================================================

Para CADA indicador:
- analysis_complete=true solo si analizaste todo lo necesario para
  ese constructo;
- full_response_audited=true solo si revisaste la respuesta completa
  para detectar evidencia, contradicciones, excepciones o ausencias
  relevantes para ese indicador.

El analysis_complete global será true únicamente si CP1-CP8 fueron
analizados completamente.

No ocultes incertidumbre inventando hechos.
No inventes evidencia.

USER
====
{user_text}
====

RESPONSE
========
{response_text}
========
""".strip()
def _serialize_prior_history(
    prior_history: tuple[PriorTurn, ...],
) -> str:
    """Serializa solo turnos anteriores al turno evaluado."""

    if not isinstance(prior_history, tuple):
        raise TypeError("prior_history debe ser tuple.")

    if not prior_history:
        return "[NO PRIOR HISTORY]"

    chunks: list[str] = []

    for index, turn in enumerate(prior_history):
        if not isinstance(turn, PriorTurn):
            raise TypeError(
                "Cada elemento de prior_history debe ser PriorTurn."
            )

        chunks.append(
            f"[HISTORY_INDEX={index} | ROLE={turn.role}]\n"
            f"{turn.text}"
        )

    return "\n\n".join(chunks)


def build_cp_family_prompt(
    *,
    user_text: str,
    response_text: str,
    prior_history: tuple[PriorTurn, ...] = (),
) -> str:
    """Prompt CP con ventana temporal causal estricta."""

    base_prompt = _build_cp_family_prompt_base(
        user_text=user_text,
        response_text=response_text,
    )

    history_text = _serialize_prior_history(
        prior_history
    )

    temporal_rules = """
TEMPORAL_CONTEXT_RULES
======================

The evaluation target is ONLY the current turn.

Authorized information:
- PRIOR_HISTORY: only turns occurring BEFORE CURRENT_USER.
- CURRENT_USER: current user message.
- CURRENT_RESPONSE: current assistant response being evaluated.

Future turns are forbidden.
Never use information from a later turn to reinterpret or evaluate
the current response.

PRIOR_HISTORY may be used only when relevant to the specific CP
construct.

Do not attribute to the user something stated only by a prior
assistant.

Evidence rules:
- source="history" requires history_index identifying the exact
  zero-based PRIOR_HISTORY element containing the literal quote.
- source="user" refers ONLY to CURRENT_USER and requires
  history_index=null.
- source="response" refers ONLY to CURRENT_RESPONSE and requires
  history_index=null.
- Never invent or reconstruct literal quotes.
""".strip()

    temporal_material = f"""
PRIOR_HISTORY
=============
{history_text}
=============

CURRENT_USER
============
{user_text}
============

CURRENT_RESPONSE
================
{response_text}
================
""".strip()

    return (
        temporal_rules
        + "\n\n"
        + base_prompt
        + "\n\n"
        + temporal_material
    )



def _validate_exact_quote(
    *,
    source: str,
    history_index: int | None,
    quote: str,
    user_text: str,
    response_text: str,
    prior_history: tuple[PriorTurn, ...] = (),
) -> None:
    """Valida fuente y literalidad; no soporte semantico."""

    if not isinstance(quote, str) or not quote:
        raise ValueError(
            "Toda evidencia debe contener quote literal."
        )

    if source == "history":
        if (
            isinstance(history_index, bool)
            or not isinstance(history_index, int)
        ):
            raise ValueError(
                "history requiere history_index entero."
            )

        if not 0 <= history_index < len(prior_history):
            raise ValueError(
                "history_index fuera del historial permitido."
            )

        haystack = prior_history[history_index].text

    elif source == "user":
        if history_index is not None:
            raise ValueError(
                "user requiere history_index=null."
            )

        haystack = user_text

    elif source == "response":
        if history_index is not None:
            raise ValueError(
                "response requiere history_index=null."
            )

        haystack = response_text

    else:
        raise ValueError(
            f"Fuente CP invalida: {source!r}"
        )

    if quote not in haystack:
        import difflib

        matcher = difflib.SequenceMatcher(
            None, quote, haystack, autojunk=False
        )
        match = matcher.find_longest_match(
            0, len(quote), 0, len(haystack)
        )

        matched = quote[
            match.a:match.a + match.size
        ]

        raise ValueError(
            "Quote no encontrada literalmente en "
            f"source={source!r}: {quote!r}; "
            f"longest_match={matched!r}; "
            f"quote_codepoints="
            f"{[hex(ord(c)) for c in quote]}; "
            f"matched_codepoints="
            f"{[hex(ord(c)) for c in matched]}"
        )



def validate_cp_family_extraction(
    result: dict[str, Any],
    *,
    user_text: str,
    response_text: str,
    prior_history: tuple[PriorTurn, ...] = (),
) -> dict[str, Any]:
    """Gate estructural/literal previo a cachear.

    IMPORTANTE:
    esto NO confirma que una quote soporte la interpretación.
    Esa responsabilidad pertenece al verificador independiente.
    """

    if not isinstance(result, dict):
        raise ValueError(
            "La extracción CP debe ser un dict."
        )

    expected_top = {
        "analysis_complete",
        "cp1",
        "cp2",
        "cp3",
        "cp4",
        "cp5",
        "cp6",
        "cp7",
        "cp8",
    }

    if set(result) != expected_top:
        raise ValueError(
            "La extracción CP no contiene exactamente "
            "CP1-CP8 y analysis_complete."
        )

    if result["analysis_complete"] is not True:
        raise ValueError(
            "El extractor CP no completó el análisis familiar."
        )

    for index in range(1, 9):
        code = f"cp{index}"
        indicator = result[code]

        if not isinstance(indicator, dict):
            raise ValueError(
                f"{code} debe ser un objeto."
            )

        if indicator.get("analysis_complete") is not True:
            raise ValueError(
                f"{code} no completó su análisis."
            )

        if indicator.get("full_response_audited") is not True:
            raise ValueError(
                f"{code} no auditó la respuesta completa."
            )

        evidence = indicator.get("evidence")

        if not isinstance(evidence, list):
            raise ValueError(
                f"{code}.evidence debe ser una lista."
            )

        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError(
                    f"Evidencia inválida en {code}."
                )

            field = item.get("field")
            source = item.get("source")
            history_index = item.get("history_index")
            quote = item.get("quote")
            interpretation = item.get("interpretation")

            if not isinstance(field, str) or not field.strip():
                raise ValueError(
                    f"Evidencia sin field válido en {code}."
                )

            if (
                not isinstance(interpretation, str)
                or not interpretation.strip()
            ):
                raise ValueError(
                    f"Evidencia sin interpretación en {code}."
                )

            _validate_exact_quote(
                source=source,
                history_index=history_index,
                quote=quote,
                user_text=user_text,
                response_text=response_text,
                prior_history=prior_history,
            )

        limitation = indicator.get(
            "concrete_secondary_limitation"
        )

        description = indicator.get(
            "limitation_description"
        )

        if limitation is True:
            if (
                not isinstance(description, str)
                or not description.strip()
            ):
                raise ValueError(
                    f"{code} declara limitación secundaria "
                    "sin describirla."
                )

        elif limitation is False:
            if description != "":
                raise ValueError(
                    f"{code} no declara limitación, pero "
                    "limitation_description no está vacío."
                )

        else:
            raise ValueError(
                f"{code}.concrete_secondary_limitation "
                "debe ser booleano."
            )

    # --------------------------------------------------------
    # Invariantes semántico-estructurales.
    #
    # NO interpretan lenguaje.
    # Solo impiden combinaciones internas imposibles o
    # contradictorias dentro del JSON ya extraído.
    # --------------------------------------------------------

    cp3 = result["cp3"]

    if cp3["organization_present"] is False:
        if cp3["organization_quality"] != "none":
            raise ValueError(
                "CP3 incoherente: organization_present=false "
                "requiere organization_quality='none'."
            )

    cp6 = result["cp6"]

    if cp6["example_or_analogy_used"] is False:
        if cp6["pertinence"] != "none":
            raise ValueError(
                "CP6 incoherente: sin ejemplo/analogía usado, "
                "pertinence debe ser 'none'."
            )

        if cp6["clarification_value"] != "none":
            raise ValueError(
                "CP6 incoherente: sin ejemplo/analogía usado, "
                "clarification_value debe ser 'none'."
            )

        if cp6["distortion_present"] is True:
            raise ValueError(
                "CP6 incoherente: no puede existir distorsión "
                "de un ejemplo/analogía inexistente."
            )

        if cp6["trivialization_present"] is True:
            raise ValueError(
                "CP6 incoherente: no puede existir trivialización "
                "de un ejemplo/analogía inexistente."
            )

    cp8 = result["cp8"]

    cp8_has_real_verification = (
        cp8["direct_understanding_check_present"]
        or cp8["correction_invitation_present"]
    )

    if not cp8_has_real_verification:
        if cp8["generic_offer_for_more_explanation_only"]:
            if cp8["verification_quality"] != "minimal":
                raise ValueError(
                    "CP8 incoherente: una oferta genérica aislada "
                    "requiere verification_quality='minimal'."
                )
        elif cp8["verification_quality"] != "none":
            raise ValueError(
                "CP8 incoherente: sin comprobación, corrección "
                "ni oferta genérica, verification_quality debe "
                "ser 'none'."
            )

    # Una limitación secundaria requiere que exista realmente
    # una limitación descrita; esta regla ya se comprobó arriba.
    #
    # Además, algunos defectos son explícitamente PRINCIPALES y
    # no deben duplicarse como secondary limitation.

    cp1 = result["cp1"]

    if cp1["substitution_or_unfounded_problem"]:
        if cp1["concrete_secondary_limitation"]:
            raise ValueError(
                "CP1 incoherente: sustitución del problema es "
                "defecto principal, no limitación secundaria."
            )

    cp7 = result["cp7"]

    if (
        cp7["unnecessary_jargon_present"]
        and cp7["accessibility"] == "complete"
    ):
        raise ValueError(
            "CP7 incoherente: unnecessary_jargon_present=true "
            "no puede coexistir con accessibility='complete'."
        )

    if (
        cp7["unnecessary_jargon_present"]
        and cp7["concrete_secondary_limitation"]
    ):
        raise ValueError(
            "CP7 incoherente: la jerga innecesaria ya est? "
            "representada por su campo principal y no debe "
            "duplicarse como concrete_secondary_limitation."
        )

    cp4 = result["cp4"]

    if cp4["materially_incorrect_relationship"]:
        if cp4["concrete_secondary_limitation"]:
            raise ValueError(
                "CP4 incoherente: relación materialmente "
                "incorrecta es defecto principal."
            )

    if cp6["distortion_present"]:
        if cp6["concrete_secondary_limitation"]:
            raise ValueError(
                "CP6 incoherente: distorsión/trivialización "
                "material es defecto principal."
            )

    return result



def extract_cp_family(
    *,
    user_text: str,
    response_text: str,
    prior_history: tuple[PriorTurn, ...] = (),
    provider: str | None = None,
    model: str | None = None,
    timeout: int = 600,
    max_output_tokens: int = 12000,
) -> dict[str, Any]:
    """Ejecuta extracción semántica coordinada CP1-CP8.

    Devuelve borrador semántico NO VERIFICADO.
    """

    if not isinstance(user_text, str):
        raise TypeError("user_text debe ser str.")

    if not isinstance(response_text, str):
        raise TypeError("response_text debe ser str.")

    if not user_text.strip():
        raise ValueError("user_text no puede estar vacío.")

    if not response_text.strip():
        raise ValueError("response_text no puede estar vacío.")

    if not isinstance(prior_history, tuple):
        raise TypeError("prior_history debe ser tuple.")

    for turn in prior_history:
        if not isinstance(turn, PriorTurn):
            raise TypeError(
                "Cada elemento de prior_history debe ser PriorTurn."
            )

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    prompt = build_cp_family_prompt(
        user_text=user_text,
        response_text=response_text,
        prior_history=prior_history,
    )

    inputs = {
        "prior_history": [
            {
                "role": turn.role,
                "text": turn.text,
            }
            for turn in prior_history
        ],
        "user_text": user_text,
        "response_text": response_text,
    }

    parameters = {
        "provider": identity["provider"],
        "timeout": timeout,
        "max_output_tokens": max_output_tokens,
    }

    def execute() -> dict[str, Any]:
        return run_structured_semantic(
            prompt=prompt,
            schema=CP_FAMILY_EXTRACTION_SCHEMA,
            provider=identity["provider"],
            model=identity["model"],
            timeout=timeout,
            max_output_tokens=max_output_tokens,
        )

    def validate_result(
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        return validate_cp_family_extraction(
            raw,
            user_text=user_text,
            response_text=response_text,
            prior_history=prior_history,
        )

    return cached_semantic_operation(
        extractor=EXTRACTOR_NAME,
        extractor_version=EXTRACTOR_VERSION,
        model=(
            f"{identity['provider']}::{identity['model']}"
        ),
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        parameters=parameters,
        inputs=inputs,
        execute=execute,
        validate_result=validate_result,
    )




