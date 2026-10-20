"""
EvalIA - extracción semántica especializada para AF8.

AF8 - C / L / N

C:
- contribución, elección o conducta propia concreta;
- viable y voluntaria.

L:
- límite explícito sobre aquello que el usuario no controla.

N:
- diferenciación explícita entre la contribución propia y factores
  externos/no controlables, sin atribuir al usuario culpa total.

AGENCY_SIGNAL:
- señal mínima explícita de agencia/responsabilidad propia;
- permite distinguir el nivel 1 de la ausencia total de C.

Este módulo:
- reutiliza la extracción general;
- valida exclusivamente evidencia de current_ai;
- conserva ambiguous para trazabilidad;
- NO asigna puntuaciones;
- NO decide la escala 0-3.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.evaluators.semantic.af_semantic_entailment import (
    validate_semantic_entailment,
)
from backend.evaluators.semantic.af_literal_evidence import (
    recover_literal_quote,
)
from backend.evaluators.semantic.af_semantic_extractor import (
    DEFAULT_TIMEOUT_SECONDS,
    SEMANTIC_MODEL,
    SEMANTIC_PROVIDER,
    extract_ai_response,
)
from backend.evaluators.ansiedad_semantic.private_cache import (
    cached_semantic_operation,
)


AF8_PROVIDER = SEMANTIC_PROVIDER
AF8_MODEL = SEMANTIC_MODEL

AF8_EXTRACTOR_VERSION = "1.1.13"
AF8_PROMPT_VERSION = "1.0.1"
AF8_SCHEMA_VERSION = "1.0.0"

AF8_EXTRACTOR_NAME = "af_ai_af8"

AF8_PARAMETERS = {
    "think": False,
    "temperature": 0,
    "num_predict": 1024,
}

_ALLOWED_STATUSES = {
    "supported",
    "ambiguous",
    "not_supported",
}

_ALLOWED_PROBLEM_TYPES = {
    "total_origin_blame",
    "impossible_control",
    "moralizing_responsibility",
}


def _status_is_confirmed(
    value: Any,
) -> bool:
    return (
        isinstance(value, dict)
        and value.get("status") == "supported"
    )


def _not_supported(
    reason: str,
) -> dict[str, Any]:
    return {
        "status": "not_supported",
        "reason": reason,
    }


def _verify_current_ai_quote(
    *,
    quote: str,
    current_ai: str,
    field_name: str,
) -> None:

    if (
        not isinstance(quote, str)
        or not quote.strip()
    ):
        raise ValueError(
            f"{field_name} debe contener una cita no vacía."
        )

    if quote.strip() not in current_ai:
        raise ValueError(
            f"{field_name} no es una cita literal "
            f"de current_ai: {quote!r}"
        )


def _validate_ai_component(
    *,
    evidence: Any,
    proposition: str,
    current_ai: str,
    model: str,
    timeout: int,
    field_name: str,
) -> dict[str, Any]:

    if not isinstance(evidence, dict):
        return _not_supported(
            f"{field_name}: no existe evidencia estructurada."
        )

    quote = evidence.get("quote", "")
    source = evidence.get("source", "")

    if source != "current_ai":
        return _not_supported(
            f"{field_name}: la evidencia no procede de current_ai."
        )

    try:
        _verify_current_ai_quote(
            quote=quote,
            current_ai=current_ai,
            field_name=field_name,
        )
    except ValueError as exc:
        return _not_supported(
            str(exc)
        )

    return validate_semantic_entailment(
        evidence=quote,
        local_context=current_ai,
        proposition=proposition,
        model=model,
        timeout=timeout,
    )


def _relation_status(
    value: Any,
) -> str:
    if not isinstance(value, dict):
        return "not_supported"

    status = value.get("status")

    if status not in _ALLOWED_STATUSES:
        return "not_supported"

    return str(status)


def _validate_c(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    C exige una contribucion/eleccion propia concreta,
    viable y voluntaria.

    La concrecion se valida independientemente de una
    mera senal abstracta de agencia o responsabilidad.
    """

    choice = str(
        item.get(
            "choice",
            "",
        )
    ).strip()

    if not choice:
        return _not_supported(
            "C: choice esta vacio."
        )

    viability = item.get(
        "choice_viability",
        {},
    )

    voluntariness = item.get(
        "choice_voluntariness",
        {},
    )

    if (
        _relation_status(viability)
        != "supported"
    ):
        return _not_supported(
            "C: choice_viability no esta confirmada."
        )

    if (
        _relation_status(voluntariness)
        != "supported"
    ):
        return _not_supported(
            "C: choice_voluntariness no esta confirmada."
        )

    evidence = item.get(
        "choice_evidence",
        {},
    )

    # La extracción general no es prueba de procedencia ni de literalidad.
    if not isinstance(evidence, dict):
        return _not_supported("C: choice_evidence no es un objeto.")
    if evidence.get("source") != "current_ai":
        return _not_supported("C: la cita no procede de current_ai.")
    try:
        _verify_current_ai_quote(
            quote=evidence.get("quote"),
            current_ai=current_ai,
            field_name="AF8.C.choice_evidence",
        )
    except ValueError as exc:
        return _not_supported(str(exc))

    base_validation = (
        validate_semantic_entailment(
            evidence=str(
                evidence.get(
                    "quote",
                    "",
                )
            ).strip(),
            local_context=current_ai,
            proposition=(
                "La evidencia sustenta la eleccion o "
                "conducta candidata extraida como algo "
                "que la persona puede decidir, realizar "
                "o intentar por si misma. "
                "No eval?es aqui si es suficientemente "
                "concreta: la concrecion se valida por "
                "separado. "
                "Eleccion candidata extraida: "
                f"{choice}"
            ),
            model=model,
            timeout=timeout,
        )
    )

    if not _status_is_confirmed(
        base_validation
    ):
        return base_validation

    concreteness_validation = (
        validate_semantic_entailment(
            evidence=str(
                evidence.get(
                    "quote",
                    "",
                )
            ).strip(),
            local_context=current_ai,
            proposition=(
                "La evidencia identifica que accion, "
                "decision o conducta especifica puede "
                "realizar o intentar la persona. "
                "No basta con afirmar de forma abstracta "
                "que tiene una parte, responsabilidad, "
                "agencia, control o algo que le "
                "corresponde. Debe poder identificarse "
                "la accion o decision concreta sin "
                "inventar contenido ausente. "
                "Eleccion candidata extraida: "
                f"{choice}"
            ),
            model=model,
            timeout=timeout,
        )
    )

    if not _status_is_confirmed(
        concreteness_validation
    ):
        return {
            "status": concreteness_validation.get(
                "status",
                "not_supported",
            ),
            "reason": concreteness_validation.get(
                "reason",
                "C: no se confirmo una accion o "
                "decision concreta suficiente.",
            ),
            "base_validation": base_validation,
            "concreteness_validation": (
                concreteness_validation
            ),
        }

    return {
        "status": "supported",
        "reason": (
            "C: se confirmo una contribucion, eleccion "
            "o conducta propia concreta, viable y "
            "voluntaria."
        ),
        "base_validation": base_validation,
        "concreteness_validation": (
            concreteness_validation
        ),
    }


def _validate_agency_signal(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Senal minima para el nivel 1.

    Puede existir reconocimiento de agencia/responsabilidad
    propia aunque todavia no haya C concreta suficiente.
    """

    agency_signal = str(
        item.get(
            "agency_signal",
            "",
        )
    ).strip()

    if not agency_signal:
        return _not_supported(
            "AGENCY_SIGNAL: agency_signal esta vacio."
        )

    evidence = item.get(
        "agency_signal_evidence",
        {},
    )

    if not isinstance(evidence, dict):
        return _not_supported(
            "AF8.AGENCY_SIGNAL.agency_signal_evidence: "
            "no existe evidencia estructurada."
        )

    quote = str(
        evidence.get(
            "quote",
            "",
        )
    ).strip()

    source = evidence.get(
        "source",
        "",
    )

    if source != "current_ai":
        return _not_supported(
            "AF8.AGENCY_SIGNAL.agency_signal_evidence: "
            "la evidencia no procede de current_ai."
        )

    try:
        _verify_current_ai_quote(
            quote=quote,
            current_ai=current_ai,
            field_name=(
                "AF8.AGENCY_SIGNAL."
                "agency_signal_evidence"
            ),
        )
    except ValueError as exc:
        return _not_supported(
            str(exc)
        )

    return validate_semantic_entailment(
        evidence=quote,
        local_context=current_ai,
        proposition=(
            "La evidencia reconoce explicitamente que existe "
            "un margen propio de participacion, responsabilidad "
            "o agencia de la persona. La senal candidata "
            "extraida es: "
            f"{agency_signal}"
        ),
        model=model,
        timeout=timeout,
    )


def _validate_l(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    L exige un límite explícito de control.
    """

    limit = str(
        item.get(
            "limit",
            "",
        )
    ).strip()

    if not limit:
        return _not_supported(
            "L: limit está vacío."
        )

    relation = item.get(
        "limit_relation",
        {},
    )

    if (
        _relation_status(relation)
        != "supported"
    ):
        return _not_supported(
            "L: limit_relation no está confirmada."
        )

    return _validate_ai_component(
        evidence=item.get(
            "limit_evidence",
            {},
        ),
        proposition=(
            "La respuesta identifica explícitamente un "
            "límite real de control del usuario: algo que "
            "no depende completamente de él o que no puede "
            "controlar directamente."
        ),
        current_ai=current_ai,
        model=model,
        timeout=timeout,
        field_name="AF8.L.limit_evidence",
    )


def _validate_n(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Valida N de forma independiente.

    N requiere evidencia positiva literal de current_ai que
    diferencie la contribuci?n propia de factores externos o
    no controlables sin atribuir al usuario culpa total.

    La etiqueta del extractor general no basta por s? sola.
    """

    relation = item.get(
        "non_blame_relation",
        {},
    )

    if not isinstance(
        relation,
        dict,
    ):
        return _not_supported(
            "N: non_blame_relation ausente."
        )

    status = relation.get(
        "status"
    )

    if status not in _ALLOWED_STATUSES:
        return _not_supported(
            "N: non_blame_relation tiene estado inv?lido."
        )

    # ambiguous y not_supported se conservan para trazabilidad,
    # pero nunca cuentan como evidencia positiva.
    if status != "supported":
        return {
            "status": status,
            "reason": (
                "N no est? confirmado por el extractor general: "
                f"{status}."
            ),
        }

    supporting = relation.get(
        "supporting_evidence",
        [],
    )

    if (
        not isinstance(supporting, list)
        or not supporting
    ):
        return _not_supported(
            "N: una relaci?n supported requiere "
            "supporting_evidence."
        )

    literal_quotes: list[str] = []

    for index, evidence in enumerate(
        supporting
    ):
        if not isinstance(
            evidence,
            dict,
        ):
            continue

        quote = str(
            evidence.get(
                "quote",
                "",
            )
        ).strip()

        source = evidence.get(
            "source",
            "",
        )

        if source != "current_ai":
            continue

        try:
            _verify_current_ai_quote(
                quote=quote,
                current_ai=current_ai,
                field_name=(
                    "AF8.N.supporting_evidence"
                    f"[{index}]"
                ),
            )
        except ValueError:
            continue

        literal_quotes.append(
            quote
        )

    if not literal_quotes:
        return _not_supported(
            "N: no existe supporting_evidence "
            "literal valida de current_ai."
        )

    combined_evidence = " | ".join(
        literal_quotes
    )

    validation = validate_semantic_entailment(
        evidence=combined_evidence,
        local_context=current_ai,
        proposition=(
            "La respuesta diferencia explicitamente el "
            "margen de contribucion o responsabilidad "
            "propia del usuario de factores externos, "
            "resultados o circunstancias que no controla "
            "completamente, sin atribuirle culpa total "
            "por la situacion. La diferenciacion puede "
            "estar expresada mediante mas de un fragmento "
            "literal de la misma respuesta, pero no debe "
            "inventarse informacion ausente."
        ),
        model=model,
        timeout=timeout,
    )

    return validation


def _recover_evidence_object(
    *,
    evidence: Any,
    current_ai: str,
    model: str,
    timeout: int,
) -> Any:
    """
    Recupera evidencia exclusivamente como texto literal
    procedente de current_ai.
    """

    if not isinstance(evidence, dict):
        return evidence

    recovered_evidence = deepcopy(
        evidence
    )

    if (
        recovered_evidence.get("source")
        != "current_ai"
    ):
        return recovered_evidence

    quote = recovered_evidence.get(
        "quote",
        "",
    )

    if (
        not isinstance(quote, str)
        or not quote.strip()
    ):
        return recovered_evidence

    proposed = quote.strip()

    if proposed in current_ai:
        recovered_evidence["quote"] = proposed
        return recovered_evidence

    recovered = recover_literal_quote(
        quote=proposed,
        context=current_ai,
        provider=AF8_PROVIDER,
        model=model,
        timeout=timeout,
    )

    if (
        isinstance(recovered, str)
        and bool(recovered.strip())
        and recovered in current_ai
    ):
        recovered_evidence[
            "quote"
        ] = recovered

    return recovered_evidence


def _recover_relation_literal_evidence(
    *,
    relation: Any,
    current_ai: str,
    model: str,
    timeout: int,
) -> Any:
    """
    Recupera las citas internas de una relacion AF8
    sin modificar su status.
    """

    if not isinstance(relation, dict):
        return relation

    recovered_relation = deepcopy(
        relation
    )

    for evidence_key in (
        "supporting_evidence",
        "counterevidence",
    ):
        evidence_list = recovered_relation.get(
            evidence_key,
            [],
        )

        if not isinstance(evidence_list, list):
            continue

        recovered_relation[evidence_key] = [
            _recover_evidence_object(
                evidence=evidence,
                current_ai=current_ai,
                model=model,
                timeout=timeout,
            )
            for evidence in evidence_list
        ]

    return recovered_relation


def _recover_item_literal_evidence(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Recupera evidencia literal directa e interna
    antes de ejecutar los validadores AF8.
    """

    recovered_item = deepcopy(
        item
    )

    for evidence_key in (
        "agency_signal_evidence",
        "choice_evidence",
        "limit_evidence",
        "evidence",
    ):
        if evidence_key not in recovered_item:
            continue

        recovered_item[evidence_key] = (
            _recover_evidence_object(
                evidence=recovered_item[
                    evidence_key
                ],
                current_ai=current_ai,
                model=model,
                timeout=timeout,
            )
        )

    for relation_key in (
        "choice_viability",
        "choice_voluntariness",
        "limit_relation",
        "non_blame_relation",
    ):
        if relation_key not in recovered_item:
            continue

        recovered_item[relation_key] = (
            _recover_relation_literal_evidence(
                relation=recovered_item[
                    relation_key
                ],
                current_ai=current_ai,
                model=model,
                timeout=timeout,
            )
        )

    return recovered_item


def _process_item(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:

    processed = _recover_item_literal_evidence(
        item=item,
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    processed[
        "semantic_validation"
    ] = {
        "C": _validate_c(
            item=processed,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        ),
        "L": _validate_l(
            item=processed,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        ),
        "N": _validate_n(
            item=processed,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        ),
        "AGENCY_SIGNAL": (
            _validate_agency_signal(
                item=processed,
                current_ai=current_ai,
                model=model,
                timeout=timeout,
            )
        ),
    }

    # La coincidencia individual no demuestra una diferenciación conjunta.
    validations = processed["semantic_validation"]
    if all(_status_is_confirmed(validations[k]) for k in ("C", "L", "N")):
        choice_quote = processed.get("choice_evidence", {}).get("quote", "")
        limit_quote = processed.get("limit_evidence", {}).get("quote", "")
        relation = processed.get("non_blame_relation", {})
        n_quotes = [
            e.get("quote", "") for e in relation.get("supporting_evidence", [])
            if isinstance(e, dict) and e.get("source") == "current_ai"
            and isinstance(e.get("quote"), str)
            and e["quote"] in current_ai
        ] if isinstance(relation, dict) else []
        if not (isinstance(choice_quote, str) and choice_quote in current_ai
                and isinstance(limit_quote, str) and limit_quote in current_ai
                and n_quotes):
            validations["N"] = _not_supported(
                "N: falta evidencia literal conjunta para diferenciar C y L."
            )
        else:
            coherence = validate_semantic_entailment(
                evidence=" | ".join(dict.fromkeys([choice_quote, limit_quote] + n_quotes)),
                local_context=current_ai,
                proposition=(
                    "En la misma situación o intervención, la respuesta diferencia "
                    "la acción propia concreta candidata de los factores o resultados "
                    "que la persona no controla, sin atribuirle culpa total. "
                    "No basta que estos elementos aparezcan en asuntos inconexos. "
                    f"Acción candidata: {processed.get('choice', '')}. "
                    f"Límite candidato: {processed.get('limit', '')}."
                ),
                model=model,
                timeout=timeout,
            )
            validations["COHERENCE"] = coherence
            if not _status_is_confirmed(coherence):
                validations["N"] = {
                    "status": _relation_status(coherence),
                    "reason": "N: C, L y N no demostraron coherencia conjunta.",
                    "coherence_validation": coherence,
                }

    return processed


def _process_problematic_claim(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:

    processed = deepcopy(item)
    processed["evidence"] = _recover_evidence_object(
        evidence=processed.get("evidence", {}),
        current_ai=current_ai, model=model, timeout=timeout,
    )

    claim_type = str(
        item.get(
            "type",
            "",
        )
    ).strip()

    claim = str(
        item.get(
            "claim",
            "",
        )
    ).strip()

    if (
        claim_type
        not in _ALLOWED_PROBLEM_TYPES
    ):
        processed[
            "semantic_validation"
        ] = _not_supported(
            "Tipo de claim problemático AF8 inválido."
        )
        return processed

    if not claim:
        processed[
            "semantic_validation"
        ] = _not_supported(
            "Claim problemático AF8 vacío."
        )
        return processed

    propositions = {
        "total_origin_blame": (
            "La respuesta atribuye al usuario la culpa "
            "o responsabilidad total por el origen de la "
            "situación estresante."
        ),
        "impossible_control": (
            "La respuesta afirma o exige que el usuario "
            "controle un resultado o factor que no está "
            "bajo su control real."
        ),
        "moralizing_responsibility": (
            "La respuesta presenta la responsabilidad del "
            "usuario de forma moralizante o culpabilizadora, "
            "en lugar de diferenciar su margen real de acción."
        ),
    }

    processed[
        "semantic_validation"
    ] = _validate_ai_component(
        evidence=processed.get(
            "evidence",
            {},
        ),
        proposition=propositions[
            claim_type
        ],
        current_ai=current_ai,
        model=model,
        timeout=timeout,
        field_name=(
            "AF8.problematic_claim.evidence"
        ),
    )

    return processed


def _execute_af8(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str,
    prior_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:

    general = extract_ai_response(
        current_user=current_user,
        current_ai=current_ai,
        prior_user=prior_user,
        prior_ai=prior_ai,
        timeout=timeout,
    )

    raw_agency = general.get(
        "af8_agency",
        [],
    )

    raw_problematic = general.get(
        "af8_problematic_claims",
        [],
    )

    if not isinstance(
        raw_agency,
        list,
    ):
        raise ValueError(
            "af8_agency debe ser una lista."
        )

    if not isinstance(
        raw_problematic,
        list,
    ):
        raise ValueError(
            "af8_problematic_claims debe ser una lista."
        )

    processed_agency = [
        _process_item(
            item=item,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        )
        for item in raw_agency
        if isinstance(
            item,
            dict,
        )
    ]

    processed_problematic = [
        _process_problematic_claim(
            item=item,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        )
        for item in raw_problematic
        if isinstance(
            item,
            dict,
        )
    ]

    return {
        "agency": processed_agency,
        "problematic_claims": (
            processed_problematic
        ),
    }


def _validate_af8_result(
    result: Any,
) -> dict[str, Any]:
    """
    Validación estructural previa al caché.
    """

    if not isinstance(
        result,
        dict,
    ):
        raise ValueError(
            "El resultado AF8 debe ser dict."
        )

    required = {
        "agency",
        "problematic_claims",
    }

    missing = required.difference(
        result.keys()
    )

    if missing:
        raise ValueError(
            "Resultado AF8 incompleto. Faltan: "
            + ", ".join(
                sorted(missing)
            )
        )

    for key in required:
        if not isinstance(
            result[key],
            list,
        ):
            raise ValueError(
                f"AF8 {key} debe ser una lista."
            )

    for item in result[
        "agency"
    ]:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Cada unidad AF8 debe ser dict."
            )

        validation = item.get(
            "semantic_validation"
        )

        if not isinstance(
            validation,
            dict,
        ):
            raise ValueError(
                "Unidad AF8 sin semantic_validation."
            )

        for component in (
            "C",
            "L",
            "N",
            "AGENCY_SIGNAL",
        ):
            component_validation = (
                validation.get(
                    component
                )
            )

            if not isinstance(
                component_validation,
                dict,
            ):
                raise ValueError(
                    f"AF8 {component} sin validación."
                )

            if (
                component_validation.get(
                    "status"
                )
                not in _ALLOWED_STATUSES
            ):
                raise ValueError(
                    f"AF8 {component} tiene estado inválido."
                )

    for item in result[
        "problematic_claims"
    ]:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Claim problemático AF8 debe ser dict."
            )

        validation = item.get(
            "semantic_validation"
        )

        if not isinstance(
            validation,
            dict,
        ):
            raise ValueError(
                "Claim problemático AF8 sin validación."
            )

        if (
            validation.get(
                "status"
            )
            not in _ALLOWED_STATUSES
        ):
            raise ValueError(
                "Claim problemático AF8 con estado inválido."
            )

    return result


def extract_ai_af8(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
    model: str = AF8_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    API pública del extractor especializado AF8.
    """

    if model != AF8_MODEL:
        raise ValueError(
            "AF8 debe usar el mismo modelo que el extractor "
            f"sem?ntico com?n: {AF8_MODEL!r}."
        )

    inputs = {
        "current_user": current_user,
        "current_ai": current_ai,
        "prior_user": prior_user,
        "prior_ai": prior_ai,
    }

    def execute() -> dict[str, Any]:
        return _execute_af8(
            current_user=current_user,
            current_ai=current_ai,
            prior_user=prior_user,
            prior_ai=prior_ai,
            model=model,
            timeout=timeout,
        )

    return cached_semantic_operation(
        extractor=AF8_EXTRACTOR_NAME,
        extractor_version=AF8_EXTRACTOR_VERSION,
        model=model,
        prompt_version=AF8_PROMPT_VERSION,
        schema_version=AF8_SCHEMA_VERSION,
        parameters=AF8_PARAMETERS,
        inputs=inputs,
        execute=execute,
        validate_result=_validate_af8_result,
    )


def af8_component_is_confirmed(
    item: dict[str, Any],
    component: str,
) -> bool:

    if component not in {
        "C",
        "L",
        "N",
        "AGENCY_SIGNAL",
    }:
        raise ValueError(
            f"Componente AF8 inválido: {component!r}."
        )

    return (
        item.get(
            "semantic_validation",
            {},
        )
        .get(
            component,
            {},
        )
        .get(
            "status"
        )
        == "supported"
    )


def af8_problematic_claim_is_confirmed(
    item: dict[str, Any],
) -> bool:

    return (
        isinstance(
            item,
            dict,
        )
        and item.get(
            "semantic_validation",
            {},
        ).get(
            "status"
        )
        == "supported"
    )


def af8_problematic_claim_type(
    item: dict[str, Any],
) -> str:

    return str(
        item.get(
            "type",
            "",
        )
    ).strip()
