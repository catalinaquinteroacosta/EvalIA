"""Reconciliaci?n sem?ntica independiente para estados BLOCKED de CP.

Arquitectura:
extractor -> verifier -> validated_state -> reconciliation -> scoring

Este m?dulo:
- NO punt?a;
- NO decide aplicabilidad;
- NO reeval?a componentes ya validados;
- NO convierte unsupported autom?ticamente en su contrario;
- NO usa turnos futuros;
- solo adjudica discrepancias BLOCKED;
- mantiene BLOCKED si la evidencia no permite resolverlas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from backend.evaluators.ansiedad_semantic.private_cache import (
    cached_semantic_operation,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
    run_structured_semantic,
)

from .context import CPEvaluationContext, PriorTurn
from .contracts import get_cp_contract
from .evidence import require_literal_evidence
from .validated_state import (
    CP_COMPONENT_FIELDS,
    ValidatedIndicatorState,
)


RECONCILER_NAME = "cp_blocked_semantic_reconciler"
RECONCILER_VERSION = "CP-RECON-1.0.0"
PROMPT_VERSION = "CP-RECON-PROMPT-1.0.2"
SCHEMA_VERSION = "CP-RECON-SCHEMA-1.0.0"

ResolutionStatus = Literal["resolved", "unresolved"]

SUPPORT_LEVELS = {
    "none",
    "minimal",
    "adequate",
    "complete",
}


@dataclass(frozen=True)
class ReconciliationResult:
    """Resultado t?cnico de reconciliar UN indicador."""

    code: str
    status: ResolutionStatus
    resolved_state: ValidatedIndicatorState
    resolved_components: tuple[str, ...]
    unresolved_components: tuple[str, ...]
    resolved_evidence_indices: tuple[int, ...]
    unresolved_evidence_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        normalized = self.code.strip().lower()

        if normalized not in CP_COMPONENT_FIELDS:
            raise ValueError(
                f"Indicador CP desconocido: {self.code!r}"
            )

        object.__setattr__(self, "code", normalized)

        if self.status not in {"resolved", "unresolved"}:
            raise ValueError(
                f"Estado de reconciliaci?n desconocido: "
                f"{self.status!r}"
            )

        if self.resolved_state.code != normalized:
            raise ValueError(
                "resolved_state pertenece a otro indicador."
            )

        if (
            self.status == "resolved"
            and self.resolved_state.status != "validated"
        ):
            raise ValueError(
                "status='resolved' exige estado final validated."
            )

        if (
            self.status == "unresolved"
            and self.resolved_state.status != "blocked"
        ):
            raise ValueError(
                "status='unresolved' exige estado final blocked."
            )


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


def _evidence_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "source": {
                "type": "string",
                "enum": ["history", "user", "response"],
            },
            "history_index": {
                "anyOf": [
                    {"type": "integer", "minimum": 0},
                    {"type": "null"},
                ]
            },
            "quote": {
                "type": "string",
                "minLength": 1,
            },
            "interpretation": {
                "type": "string",
                "minLength": 1,
            },
        },
        "required": [
            "source",
            "history_index",
            "quote",
            "interpretation",
        ],
    }


def _component_resolution_schema(
    blocked_fields: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "field": {
                "type": "string",
                "enum": list(blocked_fields),
            },
            "resolution": {
                "type": "string",
                "enum": ["resolved", "unresolved"],
            },
            "value_json": {
                "type": "string",
            },
            "reason": {
                "type": "string",
                "minLength": 1,
            },
            "evidence": {
                "type": "array",
                "items": _evidence_schema(),
            },
        },
        "required": [
            "field",
            "resolution",
            "value_json",
            "reason",
            "evidence",
        ],
    }


def build_reconciliation_schema(
    blocked_fields: tuple[str, ...],
    blocked_evidence_indices: tuple[int, ...],
) -> dict[str, Any]:
    """Schema estricto y limitado a lo actualmente BLOCKED."""

    if not blocked_fields and not blocked_evidence_indices:
        raise ValueError(
            "La reconciliaci?n exige al menos un elemento BLOCKED."
        )

    properties: dict[str, Any] = {
        "analysis_complete": {
            "type": "boolean",
        },
        "component_resolutions": {
            "type": "array",
            "items": (
                _component_resolution_schema(blocked_fields)
                if blocked_fields
                else {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {},
                }
            ),
        },
        "evidence_resolutions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "evidence_index": {
                        "type": "integer",
                        "enum": list(blocked_evidence_indices),
                    },
                    "resolution": {
                        "type": "string",
                        "enum": ["supported", "unresolved"],
                    },
                    "reason": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
                "required": [
                    "evidence_index",
                    "resolution",
                    "reason",
                ],
            },
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": [
            "analysis_complete",
            "component_resolutions",
            "evidence_resolutions",
        ],
    }


def _contract_payload(code: str) -> dict[str, Any]:
    contract = get_cp_contract(code.upper())

    return {
        "code": contract.code,
        "question": contract.question,
        "applicability": contract.applicability,
        "kind": contract.kind,
        "construct": contract.construct,
        "na_rule": contract.na_rule,
        "score_0": contract.score_0,
        "score_1": contract.score_1,
        "score_2": contract.score_2,
        "score_3": contract.score_3,
    }


def _draft_indicator(
    draft: dict[str, Any],
    code: str,
) -> dict[str, Any]:
    key = code.lower()

    value = draft.get(key)

    if not isinstance(value, dict):
        raise ValueError(
            f"draft no contiene {key} v?lido."
        )

    return value


def _verification_indicator(
    verification: dict[str, Any],
    code: str,
) -> dict[str, Any]:
    key = code.lower()

    value = verification.get(key)

    if not isinstance(value, dict):
        raise ValueError(
            f"verification no contiene {key} v?lido."
        )

    return value


def build_reconciliation_prompt(
    *,
    state: ValidatedIndicatorState,
    draft: dict[str, Any],
    verification: dict[str, Any],
    context: CPEvaluationContext,
) -> str:
    """Construye adjudicaci?n independiente de una discrepancia."""

    code = state.code
    draft_indicator = _draft_indicator(draft, code)
    verification_indicator = _verification_indicator(
        verification,
        code,
    )

    contract_json = json.dumps(
        _contract_payload(code),
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    validated_json = json.dumps(
        state.components,
        ensure_ascii=False,
        indent=2,
    )

    blocked_components_json = json.dumps(
        list(state.blocked_components),
        ensure_ascii=False,
    )

    blocked_evidence_json = json.dumps(
        list(state.blocked_evidence_indices),
        ensure_ascii=False,
    )

    draft_json = json.dumps(
        draft_indicator,
        ensure_ascii=False,
        indent=2,
    )

    verifier_json = json.dumps(
        verification_indicator,
        ensure_ascii=False,
        indent=2,
    )

    # CP-A8.59-CONTRACT-HINTS
    # Instrucciones de formato; no modifica criterios de la rubrica.
    type_hints = {}
    for field in state.blocked_components:
        original = draft_indicator.get(field)
        if isinstance(original, bool):
            type_hints[field] = {
                "type": "boolean",
                "value_json_examples": ["true", "false"],
            }
        elif isinstance(original, str):
            hint = {
                "type": "string",
                "serialization": "JSON string with double quotes",
            }
            if original in SUPPORT_LEVELS:
                hint["allowed_values"] = sorted(SUPPORT_LEVELS)
            type_hints[field] = hint
        else:
            type_hints[field] = {
                "type": "unknown",
                "instruction": "unresolved if type cannot be established",
            }

    type_hints_json = json.dumps(
        type_hints,
        ensure_ascii=False,
        indent=2,
    )

    history = _serialize_history(context.prior_history)

    return f"""
Eres el ADJUDICADOR SEM?NTICO INDEPENDIENTE de EvalIA.

Tu tarea NO es puntuar.
Tu tarea NO es decidir aplicabilidad.
Tu tarea NO es volver a evaluar componentes ya validados.

Debes revisar EXCLUSIVAMENTE los componentes y evidencias
marcados BLOCKED por desacuerdo entre extracci?n y verificaci?n.

REGLAS OBLIGATORIAS

1. La r?brica oficial incluida abajo es la autoridad normativa.
2. Usa ?nicamente:
   - PRIOR_HISTORY anterior al turno;
   - CURRENT_USER;
   - CURRENT_RESPONSE.
3. Nunca uses informaci?n posterior al turno evaluado.
4. No asumas que el extractor tiene raz?n.
5. No asumas que el verificador tiene raz?n.
6. "unsupported" NO significa autom?ticamente que el valor
   contrario sea verdadero.
7. Si el contexto autorizado permite determinar claramente
   el valor sem?ntico correcto, marca resolution="resolved".
8. Si persiste ambig?edad razonable, contradicci?n no resoluble
   o evidencia insuficiente, marca resolution="unresolved".
9. Para un componente resolved, value_json debe contener
   JSON v?lido que represente el valor sem?ntico correcto.
10. Para unresolved, value_json debe ser exactamente "null".
    Ademas, evidence debe ser exactamente [].
    No adjuntes citas a un componente unresolved.
11. Toda evidencia nueva debe ser una CITA LITERAL EXACTA.
    Para resolved, incluye solo citas verificables literalmente
    en la fuente declarada. Si una cita no es exacta, no la
    reconstruyas ni la incluyas.
12. No reconstruyas, resumas ni cambies palabras de una cita.
13. source="history" exige history_index base 0.
14. source="user" y source="response" exigen history_index=null.
15. No inventes requisitos fuera de la r?brica.
16. No emitas puntuaciones 0/1/2/3.
17. No emitas N/A.
18. No modifiques componentes que no est?n BLOCKED.

CONTRATO OFICIAL DEL INDICADOR
==============================
{contract_json}

TIPOS Y SERIALIZACION DE COMPONENTES BLOCKED
============================================
{type_hints_json}

Respeta exactamente el tipo indicado.
Los valores permitidos de tipo string solo se restringen
cuando aparecen explicitamente en allowed_values.
No inventes valores ni transformes niveles semanticos
fuera del contrato.
Si no puedes determinar un valor valido con respaldo
suficiente, usa resolution="unresolved",
value_json="null" y evidence=[].

Para evidence usa exclusivamente fragmentos textuales
copiados exactamente de PRIOR_HISTORY, CURRENT_USER
o CURRENT_RESPONSE.
No parafrasees citas, no agregues puntuacion ni N/A.
Si no puedes verificar literalmente una cita, omitela.
Una cita invalida nunca debe ser corregida por aproximacion.

CONTROL ESTRICTO DE CITAS EN RECONCILIACION:
1. Copia cada evidence.quote como subcadena exacta de
   PRIOR_HISTORY, CURRENT_USER o RESPONSE.
2. Conserva literalmente signos '?', tildes, espacios,
   puntuacion y cualquier caracter inusual de la fuente.
3. Nunca reconstruyas palabras ni corrijas ortografia.
4. No cites como RESPONSE texto que aparece solo en USER.
5. Si un componente puede resolverse mediante una ausencia
   observada en la respuesta completa, no inventes citas.
6. Si no puedes respaldar una resolucion positiva con
   evidencia literal suficiente, declara unresolved.
7. No sustituyas evidencia rechazada por una cita aproximada.
8. No cambies componentes previamente validados.
9. No inventes criterios de puntuacion ni aplicabilidad.
10. Respeta exactamente la rubrica oficial AD-02.


COMPONENTES YA VALIDADOS ? NO MODIFICAR
========================================
{validated_json}

COMPONENTES BLOCKED A ADJUDICAR
===============================
{blocked_components_json}

?NDICES DE EVIDENCIA BLOCKED
============================
{blocked_evidence_json}

HIP?TESIS ORIGINAL DEL EXTRACTOR
================================
{draft_json}

OBJECI?N / VEREDICTO DEL VERIFICADOR
====================================
{verifier_json}

PRIOR_HISTORY
=============
{history}

CURRENT_USER
============
{context.current_user_message}

CURRENT_RESPONSE
================
{context.current_response}

Devuelve ?nicamente la estructura solicitada.



CONTRATO DE SERIALIZACION value_json

value_json es una cadena que contiene JSON valido.

Para booleanos, su contenido debe ser true o false.
Para niveles semanticos str, su contenido debe incluir
comillas dobles JSON: por ejemplo, "complete".

El contenido de value_json debe ser decodificable mediante
json.loads y conservar el tipo contractual del componente.

Si resolution="unresolved", value_json debe ser "null".

Nunca inventes evidencia ni resuelvas un componente
sin respaldo semantico suficiente.

""".strip()


def _decode_component_value(
    *,
    code: str,
    field: str,
    value_json: str,
    draft_indicator: dict[str, Any],
) -> Any:
    """Decodifica valor reconciliado y conserva tipo contractual."""

    try:
        value = json.loads(value_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{code}.{field}: value_json no es JSON v?lido."
        ) from exc

    if field not in draft_indicator:
        raise ValueError(
            f"{code}.{field}: campo ausente del draft."
        )

    original = draft_indicator[field]

    # bool debe comprobarse antes de int porque bool hereda de int.
    if isinstance(original, bool):
        if not isinstance(value, bool):
            raise ValueError(
                f"{code}.{field}: se esperaba bool."
            )
        return value

    if isinstance(original, str):
        if not isinstance(value, str):
            raise ValueError(
                f"{code}.{field}: se esperaba str."
            )

        if original in SUPPORT_LEVELS and value not in SUPPORT_LEVELS:
            raise ValueError(
                f"{code}.{field}: nivel sem?ntico inv?lido {value!r}."
            )

        return value

    raise ValueError(
        f"{code}.{field}: tipo sem?ntico no soportado."
    )


def _original_evidence_by_index(
    *,
    draft_indicator: dict[str, Any],
    evidence_index: int,
) -> dict[str, Any]:
    """Recupera evidencia original preservando ?ndice del draft."""

    evidence = draft_indicator.get("evidence")

    if not isinstance(evidence, list):
        raise ValueError(
            "El draft del indicador no contiene evidence v?lida."
        )

    if (
        not isinstance(evidence_index, int)
        or isinstance(evidence_index, bool)
        or evidence_index < 0
        or evidence_index >= len(evidence)
    ):
        raise ValueError(
            "?ndice de evidencia BLOCKED fuera del draft: "
            f"{evidence_index!r}"
        )

    item = evidence[evidence_index]

    if not isinstance(item, dict):
        raise ValueError(
            f"Evidencia original {evidence_index} inv?lida."
        )

    required = {
        "source",
        "history_index",
        "quote",
    }

    if not required.issubset(item):
        raise ValueError(
            f"Evidencia original {evidence_index} incompleta."
        )

    return item


def _validate_literal_item(
    *,
    item: dict[str, Any],
    context: CPEvaluationContext,
) -> None:
    require_literal_evidence(
        source=item["source"],
        history_index=item["history_index"],
        quote=item["quote"],
        context=context,
    )


def validate_reconciliation_result(
    result: dict[str, Any],
    *,
    state: ValidatedIndicatorState,
    draft: dict[str, Any],
    context: CPEvaluationContext,
) -> dict[str, Any]:
    """Gate fail-closed antes de cachear reconciliaci?n."""

    if not isinstance(result, dict):
        raise ValueError(
            "La reconciliaci?n debe ser dict."
        )

    expected_top = {
        "analysis_complete",
        "component_resolutions",
        "evidence_resolutions",
    }

    if set(result) != expected_top:
        raise ValueError(
            "Salida de reconciliaci?n con campos inesperados."
        )

    if result["analysis_complete"] is not True:
        raise ValueError(
            "La reconciliaci?n debe completar el an?lisis."
        )

    component_resolutions = result["component_resolutions"]
    evidence_resolutions = result["evidence_resolutions"]

    if not isinstance(component_resolutions, list):
        raise ValueError(
            "component_resolutions debe ser list."
        )

    if not isinstance(evidence_resolutions, list):
        raise ValueError(
            "evidence_resolutions debe ser list."
        )

    expected_components = set(state.blocked_components)
    observed_components: set[str] = set()

    draft_indicator = _draft_indicator(
        draft,
        state.code,
    )

    for item in component_resolutions:
        if not isinstance(item, dict):
            raise ValueError(
                "Resoluci?n de componente inv?lida."
            )

        field = item.get("field")

        if field not in expected_components:
            raise ValueError(
                f"Intento de reconciliar campo no BLOCKED: {field!r}"
            )

        if field in observed_components:
            raise ValueError(
                f"Resoluci?n duplicada para {field!r}."
            )

        observed_components.add(field)

        resolution = item.get("resolution")
        value_json = item.get("value_json")
        evidence = item.get("evidence")

        if resolution == "resolved":
            if value_json == "null":
                raise ValueError(
                    f"{field}: resolved no puede usar null."
                )

            _decode_component_value(
                code=state.code,
                field=field,
                value_json=value_json,
                draft_indicator=draft_indicator,
            )

            if not isinstance(evidence, list):
                raise ValueError(
                    f"{field}: evidence debe ser list."
                )

            for evidence_item in evidence:
                _validate_literal_item(
                    item=evidence_item,
                    context=context,
                )

        elif resolution == "unresolved":
            if value_json != "null":
                raise ValueError(
                    f"{field}: unresolved exige value_json='null'."
                )

            if evidence != []:
                raise ValueError(
                    f"{field}: unresolved no transporta evidencia."
                )

        else:
            raise ValueError(
                f"{field}: resolution inv?lida."
            )

    if observed_components != expected_components:
        missing = expected_components - observed_components
        raise ValueError(
            "Faltan componentes BLOCKED por reconciliar: "
            f"{sorted(missing)}"
        )

    expected_evidence = set(
        state.blocked_evidence_indices
    )
    observed_evidence: set[int] = set()

    for item in evidence_resolutions:
        if not isinstance(item, dict):
            raise ValueError(
                "Resoluci?n de evidencia inv?lida."
            )

        index = item.get("evidence_index")

        if index not in expected_evidence:
            raise ValueError(
                "Intento de reconciliar ?ndice de evidencia "
                f"no BLOCKED: {index!r}"
            )

        if index in observed_evidence:
            raise ValueError(
                f"?ndice de evidencia duplicado: {index}"
            )

        observed_evidence.add(index)

        resolution = item.get("resolution")

        if resolution not in {
            "supported",
            "unresolved",
        }:
            raise ValueError(
                f"Resoluci?n inv?lida para evidencia {index}."
            )

        if resolution == "supported":
            original_evidence = _original_evidence_by_index(
                draft_indicator=draft_indicator,
                evidence_index=index,
            )

            _validate_literal_item(
                item=original_evidence,
                context=context,
            )

        reason = item.get("reason")

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(
                f"Evidencia {index}: reason obligatorio."
            )

    if observed_evidence != expected_evidence:
        missing = expected_evidence - observed_evidence
        raise ValueError(
            "Faltan evidencias BLOCKED por reconciliar: "
            f"{sorted(missing)}"
        )

    return result


def apply_reconciliation(
    *,
    state: ValidatedIndicatorState,
    draft: dict[str, Any],
    reconciliation: dict[str, Any],
) -> ReconciliationResult:
    """Aplica solo resoluciones ya validadas estructuralmente."""

    if state.status != "blocked":
        return ReconciliationResult(
            code=state.code,
            status="resolved",
            resolved_state=state,
            resolved_components=(),
            unresolved_components=(),
            resolved_evidence_indices=(),
            unresolved_evidence_indices=(),
        )

    components = dict(state.components)
    blocked = set(state.blocked_components)

    resolved_components: list[str] = []
    unresolved_components: list[str] = []

    draft_indicator = _draft_indicator(
        draft,
        state.code,
    )

    for item in reconciliation["component_resolutions"]:
        field = item["field"]

        if item["resolution"] == "resolved":
            components[field] = _decode_component_value(
                code=state.code,
                field=field,
                value_json=item["value_json"],
                draft_indicator=draft_indicator,
            )
            blocked.remove(field)
            resolved_components.append(field)
        else:
            unresolved_components.append(field)

    supported_evidence = set(
        state.supported_evidence_indices
    )
    blocked_evidence = set(
        state.blocked_evidence_indices
    )

    resolved_evidence: list[int] = []
    unresolved_evidence: list[int] = []

    for item in reconciliation["evidence_resolutions"]:
        index = item["evidence_index"]

        if item["resolution"] == "supported":
            blocked_evidence.remove(index)
            supported_evidence.add(index)
            resolved_evidence.append(index)
        else:
            unresolved_evidence.append(index)

    final_status = (
        "blocked"
        if blocked or blocked_evidence
        else "validated"
    )

    final_state = ValidatedIndicatorState(
        code=state.code,
        status=final_status,
        components=components,
        blocked_components=tuple(sorted(blocked)),
        supported_evidence_indices=tuple(
            sorted(supported_evidence)
        ),
        blocked_evidence_indices=tuple(
            sorted(blocked_evidence)
        ),
    )

    result_status: ResolutionStatus = (
        "resolved"
        if final_status == "validated"
        else "unresolved"
    )

    return ReconciliationResult(
        code=state.code,
        status=result_status,
        resolved_state=final_state,
        resolved_components=tuple(
            sorted(resolved_components)
        ),
        unresolved_components=tuple(
            sorted(unresolved_components)
        ),
        resolved_evidence_indices=tuple(
            sorted(resolved_evidence)
        ),
        unresolved_evidence_indices=tuple(
            sorted(unresolved_evidence)
        ),
    )


def reconcile_blocked_indicator(
    *,
    state: ValidatedIndicatorState,
    draft: dict[str, Any],
    verification: dict[str, Any],
    user_text: str,
    response_text: str,
    prior_history: tuple[PriorTurn, ...] = (),
    provider: str | None = None,
    model: str | None = None,
    timeout: int = 600,
    max_output_tokens: int = 6000,
) -> ReconciliationResult:
    """Ejecuta segunda pasada ?nicamente sobre un CP BLOCKED."""

    if state.status != "blocked":
        return ReconciliationResult(
            code=state.code,
            status="resolved",
            resolved_state=state,
            resolved_components=(),
            unresolved_components=(),
            resolved_evidence_indices=(),
            unresolved_evidence_indices=(),
        )

    context = CPEvaluationContext(
        prior_history=prior_history,
        current_user_message=user_text,
        current_response=response_text,
    )

    # Confirma existencia de entradas antes de llamada sem?ntica.
    _draft_indicator(draft, state.code)
    _verification_indicator(
        verification,
        state.code,
    )

    schema = build_reconciliation_schema(
        state.blocked_components,
        state.blocked_evidence_indices,
    )

    prompt = build_reconciliation_prompt(
        state=state,
        draft=draft,
        verification=verification,
        context=context,
    )

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    parameters = {
        "timeout": timeout,
        "max_output_tokens": max_output_tokens,
    }

    inputs = {
        "code": state.code,
        "validated_components": state.components,
        "blocked_components": list(
            state.blocked_components
        ),
        "supported_evidence_indices": list(
            state.supported_evidence_indices
        ),
        "blocked_evidence_indices": list(
            state.blocked_evidence_indices
        ),
        "draft_indicator": _draft_indicator(
            draft,
            state.code,
        ),
        "verification_indicator": _verification_indicator(
            verification,
            state.code,
        ),
        "prior_history": [
            {
                "role": turn.role,
                "text": turn.text,
            }
            for turn in prior_history
        ],
        "current_user_message": user_text,
        "current_response": response_text,
        "contract": _contract_payload(state.code),
    }

    def execute() -> dict[str, Any]:
        return run_structured_semantic(
            prompt=prompt,
            schema=schema,
            provider=identity["provider"],
            model=identity["model"],
            timeout=timeout,
            max_output_tokens=max_output_tokens,
        )

    def validate_result(
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        return validate_reconciliation_result(
            raw,
            state=state,
            draft=draft,
            context=context,
        )

    raw = cached_semantic_operation(
        extractor=RECONCILER_NAME,
        extractor_version=RECONCILER_VERSION,
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

    return apply_reconciliation(
        state=state,
        draft=draft,
        reconciliation=raw,
    )
