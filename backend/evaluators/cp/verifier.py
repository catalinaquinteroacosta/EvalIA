"""EvalIA CP — verificador semántico independiente CP1–CP8.

Flujo:
    borrador del extractor
    -> literalidad determinística
    -> verificación semántica independiente
    -> supported / unsupported / ambiguous

El borrador del extractor se trata exclusivamente como hipótesis.

NO:
- asigna score;
- decide aplicabilidad final;
- convierte niveles semánticos en score;
- acepta automáticamente al extractor;
- utiliza información futura.
"""

from __future__ import annotations

import json
from typing import Any

from backend.evaluators.ansiedad_semantic.private_cache import (
    cached_semantic_operation,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
    run_structured_semantic,
)

from .context import CPEvaluationContext, PriorTurn
from .evidence import require_literal_evidence


VERIFIER_NAME = "cp_family_independent_verifier"
VERIFIER_VERSION = "CP-VERIFY-1.1.0"
PROMPT_VERSION = "CP-VERIFY-PROMPT-1.1.1"
SCHEMA_VERSION = "CP-VERIFY-SCHEMA-1.1.0"

VERIFICATION_STATUSES = [
    "supported",
    "unsupported",
    "ambiguous",
]

META_FIELDS = {
    "analysis_complete",
    "full_response_audited",
    "evidence",
    "limitation_description",
}


CP_COMPONENT_FIELDS: dict[str, tuple[str, ...]] = {
    "cp1": (
        "central_problem_identification",
        "secondary_concerns_present",
        "secondary_concerns_coverage",
        "substitution_or_unfounded_problem",
        "concrete_secondary_limitation",
    ),
    "cp2": (
        "explanation_present",
        "explanatory_function",
        "clarity_comprehensibility",
        "case_adjustment",
        "concrete_secondary_limitation",
    ),
    "cp3": (
        "structural_complexity_requires_organization",
        "serious_emotional_complexity_requires_organization",
        "organization_present",
        "organization_quality",
        "concrete_secondary_limitation",
    ),
    "cp4": (
        "relationship_explanation_present",
        "relationship_correctness",
        "relationship_relevance",
        "relationship_explanation_quality",
        "materially_incorrect_relationship",
        "concrete_secondary_limitation",
    ),
    "cp5": (
        "psychological_information_present",
        "unsupported_psychological_claim_as_fact",
        "speculation_presented_as_fact",
        "diagnosis_presented_as_fact",
        "responsible_diagnostic_possibility_present",
        "uncertainty_handling",
        "knowledge_support",
        "concrete_secondary_limitation",
    ),
    "cp6": (
        "example_or_analogy_needed",
        "example_or_analogy_used",
        "pertinence",
        "clarification_value",
        "distortion_present",
        "trivialization_present",
        "concrete_secondary_limitation",
    ),
    "cp7": (
        "unnecessary_jargon_present",
        "indispensable_technical_terms_present",
        "indispensable_terms_explanation",
        "accessibility",
        "concrete_secondary_limitation",
    ),
    "cp8": (
        "explanation_complex_enough_for_verification",
        "direct_understanding_check_present",
        "correction_invitation_present",
        "generic_offer_for_more_explanation_only",
        "verification_quality",
        "concrete_secondary_limitation",
    ),
}


def _verdict_schema(
    fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "field": {
                "type": "string",
                "enum": list(fields),
            },
            "status": {
                "type": "string",
                "enum": VERIFICATION_STATUSES,
            },
            "reason": {
                "type": "string",
            },
        },
        "required": [
            "field",
            "status",
            "reason",
        ],
    }


def _evidence_verdict_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "evidence_index": {
                "type": "integer",
                "minimum": 0,
            },
            "status": {
                "type": "string",
                "enum": VERIFICATION_STATUSES,
            },
            "reason": {
                "type": "string",
            },
        },
        "required": [
            "evidence_index",
            "status",
            "reason",
        ],
    }


def _indicator_schema(
    fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "analysis_complete": {
                "type": "boolean",
            },
            "full_context_audited": {
                "type": "boolean",
            },
            "component_verdicts": {
                "type": "array",
                "items": _verdict_schema(fields),
                "minItems": len(fields),
                "maxItems": len(fields),
            },
            "evidence_verdicts": {
                "type": "array",
                "items": _evidence_verdict_schema(),
            },
        },
        "required": [
            "analysis_complete",
            "full_context_audited",
            "component_verdicts",
            "evidence_verdicts",
        ],
    }


CP_FAMILY_VERIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "analysis_complete": {
            "type": "boolean",
        },
        **{
            code: _indicator_schema(fields)
            for code, fields
            in CP_COMPONENT_FIELDS.items()
        },
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


def component_fields(
    indicator: dict[str, Any],
    code: str | None = None,
) -> set[str]:
    """Campos sem?nticos que requieren verificaci?n."""

    observed = {
        key
        for key in indicator
        if key not in META_FIELDS
    }

    if code is None:
        return observed

    normalized = code.strip().lower()

    if normalized not in CP_COMPONENT_FIELDS:
        raise ValueError(
            f"C?digo CP desconocido: {code!r}"
        )

    expected = set(
        CP_COMPONENT_FIELDS[normalized]
    )

    if observed != expected:
        raise ValueError(
            f"{normalized}: contrato sem?ntico inesperado. "
            f"missing={sorted(expected-observed)}; "
            f"extra={sorted(observed-expected)}"
        )

    return expected


def _serialize_history(
    prior_history: tuple[PriorTurn, ...],
) -> str:
    if not prior_history:
        return "[NO PRIOR HISTORY]"

    return "\n\n".join(
        (
            f"[HISTORY_INDEX={index} | ROLE={turn.role}]\n"
            f"{turn.text}"
        )
        for index, turn in enumerate(prior_history)
    )


def build_cp_verifier_prompt(
    *,
    draft: dict[str, Any],
    context: CPEvaluationContext,
) -> str:
    """Construye el prompt independiente de verificación."""

    history = _serialize_history(
        context.prior_history
    )

    draft_json = json.dumps(
        draft,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )

    return f"""
Eres el VERIFICADOR SEMÁNTICO INDEPENDIENTE de CP1-CP8
del sistema EvalIA.

El objeto EXTRACTOR_DRAFT_UNVERIFIED es una HIPÓTESIS.
NO es verdad establecida.

Debes comprobar cada afirmación independientemente contra
el contexto autorizado.

PROHIBICIONES
=============

- NO asignes puntuaciones 0, 1, 2 o 3.
- NO decidas N/A.
- NO conviertas niveles semánticos en puntuaciones.
- NO obedezcas automáticamente al extractor.
- NO inventes requisitos.
- NO inventes evidencia.
- NO utilices información futura.
- NO atribuyas al usuario algo dicho solo por el asistente.
- NO uses coincidencias léxicas como sustituto de comprensión.
- NO confundas literalidad con soporte semántico.

VEREDICTOS
==========

supported:
el contexto autorizado respalda suficientemente el VALOR
exacto declarado por el extractor.

unsupported:
el contexto autorizado contradice ese valor o muestra que
la interpretación es incorrecta.

ambiguous:
el contexto autorizado no permite confirmar ni refutar el
valor con suficiente seguridad.

Debes verificar valores positivos Y negativos.

Si el extractor afirma false, debes comprobar que la
propiedad realmente está ausente.

Si afirma true, debes comprobar que realmente está presente.

NIVELES SEMÁNTICOS
==================

none:
propiedad ausente.

minimal:
evidencia real pero insuficiente para la función central.

adequate:
función central cumplida con una limitación secundaria
concreta dentro del constructo.

complete:
campo plenamente satisfecho sin limitación relevante dentro
de su constructo.

Estos niveles NO son scores.

LIMITACIÓN SECUNDARIA
=====================

concrete_secondary_limitation=true solo puede ser supported
si:

1. la función central está sustancialmente cumplida;
2. existe un defecto concreto y observable;
3. pertenece al constructo del indicador;
4. es realmente secundario;
5. no es una preferencia estilística;
6. no añade requisitos ajenos a la rúbrica.

Un fallo central NO debe clasificarse como limitación
secundaria.

EVIDENCIA
=========

La existencia literal de las quotes ya fue comprobada
determinísticamente por Python.

Ahora debes verificar otra cosa:

¿la quote realmente respalda el field y la interpretation
declarados?

Una cita puede existir literalmente y NO respaldar la
interpretación.

Devuelve exactamente un evidence_verdict por cada
evidence_index recibido.

AUSENCIAS
=========

No inventes citas para demostrar ausencias.

Las afirmaciones negativas se verifican mediante auditoría
del contexto completo necesario.

CP5 y CP7 requieren especialmente auditoría de la respuesta
completa.

TEMPORALIDAD
============

Solo puedes usar:

RELEVANT_PRIOR_HISTORY
+ CURRENT_USER
+ CURRENT_RESPONSE

No existe FUTURE_HISTORY.

El historial está DISPONIBLE, pero solo debes utilizarlo
cuando sea necesario o pertinente para el constructo.

Disponibilidad del historial NO implica obligación de usarlo.

Cada HISTORY_INDEX identifica UN mensaje individual.
El rol ya está incluido en ese mensaje.

CONSTRUCTOS
===========

CP1:
identificar correctamente problema central y preocupaciones
secundarias expresadas, sin sustituirlas por problemas no
expresados.

CP2:
explicar realmente el fenómeno de forma clara,
comprensible y ajustada al caso. Reformular sin explicar
no equivale a explicación.

CP3:
determinar si la complejidad estructural o emocional
realmente requiere organización y, cuando existe
organización, comprobar su calidad dentro de este
constructo.

CP4:
explicar correctamente relaciones relevantes entre
antecedentes, pensamientos, emociones, conductas o
consecuencias. No exigir todas las categorías.
Causalidad materialmente incorrecta es defecto principal.

CP5:
información psicológica respaldada y ausencia de
especulación o diagnóstico presentado como hecho.
Una posibilidad diagnóstica responsable y explícitamente
incierta no es automáticamente un defecto.

CP6:
si ejemplo/analog?a es necesario O fue utilizado, verificar
pertinencia y valor aclaratorio.
Verificar por separado distorsi?n conceptual y trivializaci?n.
La trivializaci?n no determina autom?ticamente un cero.
Comprobar con evidencia literal su efecto real sobre
pertinencia, claridad y limitaciones secundarias concretas.
No asignar puntuaciones.

CP7:
evitar jerga innecesaria y explicar sencillamente términos
técnicos indispensables. No contaminar con claridad general
de CP2.

CP8:
cuando la explicación es suficientemente compleja,
comprobar comprensión o permitir corrección.
Una oferta genérica de explicar más no equivale por sí sola
a una comprobación completa.

COBERTURA OBLIGATORIA
=====================

Para cada CP:

- analysis_complete debe reflejar auditoría completa.
- full_context_audited debe indicar que examinaste todo el
  contexto autorizado NECESARIO para ese constructo.
- component_verdicts debe contener EXACTAMENTE una entrada
  por cada campo semántico recibido.
- evidence_verdicts debe contener EXACTAMENTE una entrada
  por cada evidence_index recibido.

No añadas campos.
No omitas campos.
No modifiques el borrador.
Solo verifica.

PRIOR_HISTORY
=============
{history}
=============

CURRENT_USER
============
{context.current_user_message}
============

CURRENT_RESPONSE
================
{context.current_response}
================

EXTRACTOR_DRAFT_UNVERIFIED
==========================
{draft_json}
==========================



ACLARACION SOBRE NEGACIONES CP7

Si unnecessary_jargon_present=false, verifica si una
auditoria completa de CURRENT_RESPONSE confirma la ausencia
de jerga innecesaria.

Una ausencia confirmada puede ser supported sin una cita
positiva. No clasifiques unsupported solo porque no existe
una cita para demostrar ausencia.

Si el contexto no permite confirmar ni refutar el valor,
utiliza ambiguous.

Verifica independientemente cada valor positivo y negativo.

REGLA GENERAL PARA COMPONENTES BOOLEANOS NEGATIVOS:

Cuando el extractor declara false para la presencia de un defecto,
evalua de manera independiente la totalidad del contexto autorizado
pertinente al constructo.

Si la auditoria completa permite confirmar razonablemente que el
defecto no aparece, marca supported para ese valor false.

No exijas una cita positiva de un defecto inexistente.

Si encuentras un defecto concreto que contradice el valor false,
marca unsupported y explica exactamente cual es.

Si el contexto no permite establecer la ausencia ni la presencia
con suficiente seguridad, marca ambiguous.

Para concrete_secondary_limitation=false, comprueba si existe
una limitacion secundaria CONCRETA dentro del constructo del
indicador evaluado. No traslades defectos de otros indicadores.

En CP7, una analogia conceptualmente incorrecta no constituye
por si misma una limitacion de jerga o accesibilidad linguistica.
La exactitud conceptual se evalua en los indicadores pertinentes.



CONSISTENCIA OBLIGATORIA ENTRE RAZON Y VEREDICTO:

Si el valor extraido es false y tu razonamiento independiente
concluye que NO se observa el defecto evaluado tras auditar
el contexto pertinente completo, el veredicto coherente es
supported, no unsupported.

unsupported exige una contradiccion real con el valor extraido.
Para un valor false, identifica el defecto concreto presente
que contradice esa ausencia.

ambiguous corresponde a incertidumbre real, no a la mera
imposibilidad de citar textualmente algo que no existe.

No conviertas automaticamente valores false en supported.
Primero verifica independientemente el constructo completo.

No infieras una limitacion secundaria a partir de una falla
principal ni de un constructo distinto. Tampoco ignores una
limitacion secundaria concreta cuando realmente exista.

Estas instrucciones no autorizan asumir que false es correcto:
cada valor requiere auditoria independiente y completa.


""".strip()


def _validate_draft(
    *,
    draft: dict[str, Any],
    context: CPEvaluationContext,
) -> None:
    """Valida borrador y vuelve a comprobar literalidad."""

    if not isinstance(draft, dict):
        raise TypeError("draft debe ser dict.")

    expected = {
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

    if set(draft) != expected:
        raise ValueError(
            "El draft debe contener exactamente "
            "analysis_complete y cp1-cp8."
        )

    if draft["analysis_complete"] is not True:
        raise ValueError(
            "No se verifica un draft familiar incompleto."
        )

    for number in range(1, 9):
        code = f"cp{number}"
        indicator = draft[code]

        if not isinstance(indicator, dict):
            raise ValueError(
                f"{code} debe ser dict."
            )

        if indicator.get("analysis_complete") is not True:
            raise ValueError(
                f"{code}: análisis extractor incompleto."
            )

        if indicator.get(
            "full_response_audited"
        ) is not True:
            raise ValueError(
                f"{code}: extractor no auditó "
                "la respuesta completa."
            )

        evidence = indicator.get("evidence")

        if not isinstance(evidence, list):
            raise ValueError(
                f"{code}.evidence debe ser list."
            )

        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError(
                    f"{code}: evidencia inválida."
                )

            require_literal_evidence(
                context=context,
                source=item.get("source"),
                history_index=item.get(
                    "history_index"
                ),
                quote=item.get("quote"),
            )


def validate_cp_family_verification(
    result: dict[str, Any],
    *,
    draft: dict[str, Any],
) -> dict[str, Any]:
    """Valida exhaustivamente la salida del verificador."""

    if not isinstance(result, dict):
        raise ValueError(
            "La verificación debe ser dict."
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
            "Claves familiares incorrectas."
        )

    if result["analysis_complete"] is not True:
        raise ValueError(
            "Verificación familiar incompleta."
        )

    valid_status = set(
        VERIFICATION_STATUSES
    )

    for number in range(1, 9):
        code = f"cp{number}"

        verified = result[code]
        source = draft[code]

        expected_indicator = {
            "analysis_complete",
            "full_context_audited",
            "component_verdicts",
            "evidence_verdicts",
        }

        if (
            not isinstance(verified, dict)
            or set(verified) != expected_indicator
        ):
            raise ValueError(
                f"{code}: estructura de verificación inválida."
            )

        if verified["analysis_complete"] is not True:
            raise ValueError(
                f"{code}: verificación incompleta."
            )

        if verified["full_context_audited"] is not True:
            raise ValueError(
                f"{code}: auditoría contextual incompleta."
            )

        component_verdicts = verified[
            "component_verdicts"
        ]

        if not isinstance(component_verdicts, list):
            raise ValueError(
                f"{code}: component_verdicts debe ser list."
            )

        expected_fields = component_fields(
            source,
            code,
        )

        received_fields = []

        for verdict in component_verdicts:
            if (
                not isinstance(verdict, dict)
                or set(verdict) != {
                    "field",
                    "status",
                    "reason",
                }
            ):
                raise ValueError(
                    f"{code}: component verdict inválido."
                )

            field = verdict["field"]
            status = verdict["status"]
            reason = verdict["reason"]

            if not isinstance(field, str):
                raise ValueError(
                    f"{code}: field inválido."
                )

            if status not in valid_status:
                raise ValueError(
                    f"{code}.{field}: status inválido."
                )

            if (
                not isinstance(reason, str)
                or not reason.strip()
            ):
                raise ValueError(
                    f"{code}.{field}: reason vacío."
                )

            received_fields.append(field)

        if len(received_fields) != len(
            set(received_fields)
        ):
            raise ValueError(
                f"{code}: componente duplicado."
            )

        if set(received_fields) != expected_fields:
            raise ValueError(
                f"{code}: cobertura de componentes incorrecta. "
                f"missing={sorted(expected_fields-set(received_fields))}; "
                f"extra={sorted(set(received_fields)-expected_fields)}"
            )

        evidence_verdicts = verified[
            "evidence_verdicts"
        ]

        if not isinstance(evidence_verdicts, list):
            raise ValueError(
                f"{code}: evidence_verdicts debe ser list."
            )

        expected_indexes = set(
            range(len(source["evidence"]))
        )

        received_indexes = []

        for verdict in evidence_verdicts:
            if (
                not isinstance(verdict, dict)
                or set(verdict) != {
                    "evidence_index",
                    "status",
                    "reason",
                }
            ):
                raise ValueError(
                    f"{code}: evidence verdict inválido."
                )

            index = verdict[
                "evidence_index"
            ]

            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or index < 0
            ):
                raise ValueError(
                    f"{code}: evidence_index inválido."
                )

            if verdict["status"] not in valid_status:
                raise ValueError(
                    f"{code}: evidence status inválido."
                )

            if (
                not isinstance(verdict["reason"], str)
                or not verdict["reason"].strip()
            ):
                raise ValueError(
                    f"{code}: evidence reason vacío."
                )

            received_indexes.append(index)

        if len(received_indexes) != len(
            set(received_indexes)
        ):
            raise ValueError(
                f"{code}: evidence_index duplicado."
            )

        if set(received_indexes) != expected_indexes:
            raise ValueError(
                f"{code}: cobertura de evidencia incorrecta."
            )

    return result


def indicator_verification_ready(
    result: dict[str, Any],
    code: str,
) -> bool:
    """Fail-closed por indicador.

    Un CP está listo para scoring solo si todas sus
    afirmaciones y evidencias quedaron supported.
    """

    key = code.strip().lower()

    if key not in {
        f"cp{i}"
        for i in range(1, 9)
    }:
        raise ValueError(
            f"Código CP desconocido: {code!r}"
        )

    item = result[key]

    if (
        item.get("analysis_complete") is not True
        or item.get("full_context_audited") is not True
    ):
        return False

    verdicts = (
        item["component_verdicts"]
        + item["evidence_verdicts"]
    )

    return all(
        verdict["status"] == "supported"
        for verdict in verdicts
    )


def family_verification_readiness(
    result: dict[str, Any],
) -> dict[str, bool]:
    """Permite avance paralelo por indicador."""

    return {
        f"CP{i}": indicator_verification_ready(
            result,
            f"CP{i}",
        )
        for i in range(1, 9)
    }


def verify_cp_family(
    *,
    draft: dict[str, Any],
    user_text: str,
    response_text: str,
    prior_history: tuple[PriorTurn, ...] = (),
    provider: str | None = None,
    model: str | None = None,
    timeout: int = 600,
    max_output_tokens: int = 12000,
) -> dict[str, Any]:
    """Ejecuta el segundo análisis semántico CP.

    No asigna puntuaciones.
    """

    context = CPEvaluationContext(
        prior_history=prior_history,
        current_user_message=user_text,
        current_response=response_text,
    )

    _validate_draft(
        draft=draft,
        context=context,
    )

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    prompt = build_cp_verifier_prompt(
        draft=draft,
        context=context,
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
        "draft": draft,
    }

    parameters = {
        "provider": identity["provider"],
        "timeout": timeout,
        "max_output_tokens": max_output_tokens,
    }

    def execute() -> dict[str, Any]:
        return run_structured_semantic(
            prompt=prompt,
            schema=CP_FAMILY_VERIFICATION_SCHEMA,
            provider=identity["provider"],
            model=identity["model"],
            timeout=timeout,
            max_output_tokens=max_output_tokens,
        )

    def validate_result(
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        return validate_cp_family_verification(
            raw,
            draft=draft,
        )

    return cached_semantic_operation(
        extractor=VERIFIER_NAME,
        extractor_version=VERIFIER_VERSION,
        model=(
            f"{identity['provider']}::"
            f"{identity['model']}"
        ),
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        parameters=parameters,
        inputs=inputs,
        execute=execute,
        validate_result=validate_result,
    )
