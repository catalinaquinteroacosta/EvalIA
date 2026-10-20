"""
EvalIA â€” extracciÃ³n semÃ¡ntica especializada para AF6.

AF6 â€” H / V / R

Objetivo:
- reutilizar la extracciÃ³n general de la respuesta de IA;
- verificar semÃ¡nticamente los componentes especÃ­ficos de AF6;
- relacionar recursos documentados con antecedentes reales del usuario;
- distinguir preguntas especÃ­ficas, preguntas genÃ©ricas y supuestos
  no sustentados;
- NO asignar puntuaciones.

Componentes:

H:
- recurso previo documentado y sustentado por el usuario; o
- pregunta especÃ­fica de la IA orientada a identificar quÃ© recurso
  concreto ayudÃ³ previamente.

V:
- vÃ­nculo del recurso o pregunta especÃ­fica con la dificultad actual.

R:
- propuesta concreta de reutilizaciÃ³n o adaptaciÃ³n del recurso
  para la situaciÃ³n actual.

PolÃ­tica:
- solo "supported" cuenta como evidencia positiva;
- "ambiguous" se conserva para trazabilidad;
- nunca se inventan recursos previos del usuario;
- no se mezclan componentes entre entradas diferentes;
- el scorer determinista se encuentra fuera de este mÃ³dulo.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from backend.evaluators.semantic.af_semantic_entailment import (
    validate_semantic_entailment,
)
from backend.evaluators.semantic.af_semantic_extractor import (
    DEFAULT_TIMEOUT_SECONDS,
    extract_ai_response,
)
from backend.evaluators.semantic.af_user_resources import (
    extract_user_resources,
    resource_is_confirmed,
)
from backend.evaluators.ansiedad_semantic.private_cache import (
    cached_semantic_operation,
)
from backend.evaluators.ansiedad_semantic.private_provider import (
    get_semantic_identity,
)


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

AF6_EXTRACTOR_VERSION = "2.6.0"
AF6_PROMPT_VERSION = "1.0.0"
AF6_SCHEMA_VERSION = "1.0.0"

_ALLOWED_STATUSES = {
    "supported",
    "ambiguous",
    "not_supported",
}

AF6_EXTRACTOR_NAME = "af_ai_af6"

AF6_PARAMETERS = {
    "think": False,
    "temperature": 0,
    "num_predict": 1024,
}


def _status_is_confirmed(
    value: Any,
) -> bool:
    return (
        isinstance(value, dict)
        and value.get("status") == "supported"
    )


def _verify_current_ai_quote(
    *,
    quote: str,
    current_ai: str,
    field_name: str,
) -> None:
    """
    Toda evidencia atribuida a la respuesta evaluada debe ser
    un fragmento literal de current_ai.
    """

    if not isinstance(quote, str) or not quote.strip():
        raise ValueError(
            f"{field_name} debe contener una cita no vacÃ­a."
        )

    if quote.strip() not in current_ai:
        raise ValueError(
            f"{field_name} no es una cita literal de current_ai: "
            f"{quote!r}"
        )


def _validate_ai_component(
    *,
    evidence: dict[str, Any],
    proposition: str,
    current_ai: str,
    model: str,
    timeout: int,
    field_name: str,
) -> dict[str, Any]:
    """
    Valida que una proposiciÃ³n AF6 estÃ© realmente sustentada
    por evidencia literal de la respuesta actual de la IA.
    """

    if not isinstance(evidence, dict):
        return {
            "status": "not_supported",
            "reason": (
                f"{field_name}: no existe evidencia estructurada."
            ),
        }

    quote = evidence.get("quote", "")
    source = evidence.get("source", "")

    if source != "current_ai":
        return {
            "status": "not_supported",
            "reason": (
                f"{field_name}: la evidencia no procede de current_ai."
            ),
        }

    try:
        _verify_current_ai_quote(
            quote=quote,
            current_ai=current_ai,
            field_name=field_name,
        )
    except ValueError as exc:
        return {
            "status": "not_supported",
            "reason": str(exc),
        }

    return validate_semantic_entailment(
        evidence=quote.strip(),
        local_context=current_ai,
        proposition=proposition.strip(),
        provider=SEMANTIC_PROVIDER,
        model=model,
        timeout=timeout,
    )


def _confirmed_user_resources(
    user_resources: dict[str, Any],
) -> list[dict[str, Any]]:
    items = user_resources.get(
        "prior_helpful_resources",
        [],
    )

    if not isinstance(items, list):
        raise ValueError(
            "prior_helpful_resources debe ser una lista."
        )

    return [
        item
        for item in items
        if isinstance(item, dict)
        and resource_is_confirmed(item)
    ]


def _resource_match_validation(
    *,
    ai_resource: str,
    ai_evidence: dict[str, Any],
    user_resources: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Comprueba que un recurso presentado por la IA como antecedente
    documentado corresponda realmente a un recurso previo confirmado
    del usuario.

    No basta con que el recurso aparezca en current_ai.
    """

    if not user_resources:
        return {
            "status": "not_supported",
            "reason": (
                "La IA presenta un recurso previo, pero no existe "
                "un antecedente Ãºtil confirmado del usuario."
            ),
        }

    ai_validation = _validate_ai_component(
        evidence=ai_evidence,
        proposition=(
            "La respuesta de la IA identifica como antecedente "
            f"del usuario este recurso: {ai_resource}"
        ),
        current_ai=current_ai,
        model=model,
        timeout=timeout,
        field_name="resource_evidence",
    )

    if not _status_is_confirmed(ai_validation):
        return ai_validation

    ambiguous_result: dict[str, Any] | None = None

    for user_resource in user_resources:
        description = str(
            user_resource.get("description", "")
        ).strip()

        helpfulness = str(
            user_resource.get(
                "helpfulness_description",
                "",
            )
        ).strip()

        if not description:
            continue

        proposition = (
            f"El recurso mencionado por la IA, '{ai_resource}', "
            f"corresponde al recurso previo confirmado del usuario "
            f"'{description}'"
        )

        if helpfulness:
            proposition += (
                f", que previamente le resultÃ³ Ãºtil de esta manera: "
                f"{helpfulness}"
            )

        evidence = (
            f"Recurso IA: {ai_resource}\n"
            f"Recurso usuario: {description}"
        )

        if helpfulness:
            evidence += (
                f"\nUtilidad previa: {helpfulness}"
            )

        validation = validate_semantic_entailment(
            evidence=evidence,
            proposition=proposition,
            provider=SEMANTIC_PROVIDER,
            model=model,
            timeout=timeout,
        )

        if validation.get("status") == "supported":
            return {
                **validation,
                "matched_user_resource_id": (
                    user_resource.get("id")
                ),
            }

        if (
            validation.get("status") == "ambiguous"
            and ambiguous_result is None
        ):
            ambiguous_result = {
                **validation,
                "matched_user_resource_id": (
                    user_resource.get("id")
                ),
            }

    if ambiguous_result is not None:
        return ambiguous_result

    return {
        "status": "not_supported",
        "reason": (
            "No se confirmÃ³ correspondencia entre el recurso "
            "mencionado por la IA y los recursos previos "
            "documentados del usuario."
        ),
    }


def _validate_h(
    *,
    item: dict[str, Any],
    user_resources: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    H puede confirmarse de dos maneras:

    1. documented_resource:
       la IA recupera un recurso previo realmente documentado.

    2. specific_question:
       la IA pregunta especÃ­ficamente por un recurso que ayudÃ³
       previamente, sin inventarlo.

    generic_question no alcanza H confirmada.
    unsupported_assumption tampoco.
    """

    mode = item.get("mode")
    resource = str(
        item.get("resource", "")
    ).strip()

    evidence = item.get(
        "resource_evidence",
        {},
    )

    if mode == "documented_resource":
        if not resource:
            return {
                "status": "not_supported",
                "reason": (
                    "documented_resource sin recurso identificable."
                ),
            }

        return _resource_match_validation(
            ai_resource=resource,
            ai_evidence=evidence,
            user_resources=user_resources,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        )

    if mode == "specific_question":
        if not resource:
            return {
                "status": "not_supported",
                "reason": (
                    "specific_question sin contenido especÃ­fico."
                ),
            }

        return _validate_ai_component(
            evidence=evidence,
            proposition=(
                "La IA formula una pregunta especÃ­fica orientada "
                "a identificar quÃ© recurso, estrategia o conducta "
                "concreta ayudÃ³ previamente al usuario"
            ),
            current_ai=current_ai,
            model=model,
            timeout=timeout,
            field_name="resource_evidence",
        )

    if mode == "generic_question":
        return {
            "status": "not_supported",
            "reason": (
                "Una pregunta genÃ©rica no confirma H; se conserva "
                "como seÃ±al mÃ­nima para el scorer."
            ),
        }

    if mode == "unsupported_assumption":
        return {
            "status": "not_supported",
            "reason": (
                "La IA presupone un recurso previo no sustentado."
            ),
        }

    return {
        "status": "not_supported",
        "reason": (
            f"Modo AF6 desconocido o invÃ¡lido: {mode!r}."
        ),
    }


def _validate_v(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Valida V usando exclusivamente evidencia literal de current_ai.

    La relación recurso -> dificultad actual puede estar expresada
    en más de una cita de supporting_evidence. Por ello, las citas
    autorizadas se validan conjuntamente, sin permitir que
    local_context sustituya evidencia semántica ausente.
    """

    relation = item.get(
        "current_difficulty_relation",
        {},
    )

    if not _status_is_confirmed(relation):
        return {
            "status": (
                relation.get("status", "not_supported")
                if isinstance(relation, dict)
                else "not_supported"
            ),
            "reason": (
                "La extracción general no confirmó el vínculo "
                "con la dificultad actual."
            ),
        }

    supporting_evidence = relation.get(
        "supporting_evidence",
        [],
    )

    if not isinstance(supporting_evidence, list):
        return {
            "status": "not_supported",
            "reason": (
                "current_difficulty_relation no contiene una lista "
                "válida de supporting_evidence."
            ),
        }

    resource = str(
        item.get("resource", "")
    ).strip()

    quotes: list[str] = []

    for evidence in supporting_evidence:
        if not isinstance(evidence, dict):
            continue

        if evidence.get("source") != "current_ai":
            continue

        quote = str(
            evidence.get("quote", "")
        ).strip()

        if not quote:
            continue

        try:
            _verify_current_ai_quote(
                quote=quote,
                current_ai=current_ai,
                field_name=(
                    "current_difficulty_relation."
                    "supporting_evidence"
                ),
            )
        except ValueError:
            continue

        if quote not in quotes:
            quotes.append(quote)

    if not quotes:
        return {
            "status": "not_supported",
            "reason": (
                "No existe evidencia literal válida de current_ai "
                "para comprobar V."
            ),
        }

    # V puede estar expresada mediante una referencia anaforica:
    # "ese recurso". Se incorpora la evidencia literal de H
    # para identificar el antecedente, sin sustituir las citas
    # que deben demostrar el vinculo con la dificultad actual.
    resource_evidence = item.get("resource_evidence", {})
    resource_quote = ""

    if isinstance(resource_evidence, dict):
        candidate = str(
            resource_evidence.get("quote", "")
        ).strip()

        if (
            resource_evidence.get("source") == "current_ai"
            and candidate
        ):
            try:
                _verify_current_ai_quote(
                    quote=candidate,
                    current_ai=current_ai,
                    field_name="resource_evidence",
                )
                resource_quote = candidate
            except ValueError:
                pass

    # Incorporar evidencia literal de reutilizacion del mismo item
    # cuando amplie el contexto de la relacion recurso-dificultad.
    reuse_evidence = item.get("reuse_evidence", {})
    reuse_quote = ""

    if isinstance(reuse_evidence, dict):
        candidate = str(
            reuse_evidence.get("quote", "")
        ).strip()

        if (
            reuse_evidence.get("source") == "current_ai"
            and candidate
        ):
            try:
                _verify_current_ai_quote(
                    quote=candidate,
                    current_ai=current_ai,
                    field_name="reuse_evidence",
                )
                reuse_quote = candidate
            except ValueError:
                pass

    evidence_quotes = (
        ([resource_quote] if resource_quote else [])
        + quotes
    )

    if reuse_quote and reuse_quote not in evidence_quotes:
        evidence_quotes.append(reuse_quote)

    joint_evidence = "\n".join(evidence_quotes)

    validation = validate_semantic_entailment(
        evidence=current_ai,
        local_context=current_ai,
        proposition=(
            (((
    f"La respuesta propone utilizar nuevamente o adaptar "
    f"el MISMO recurso anterior identificado como '{resource}' "
    f"para afrontar la dificultad actual. Debe existir una "
    f"propuesta de uso de ese recurso concreto, directamente "
    f"o mediante una referencia inequ?voca como 'ese recurso'. "
    f"No basta con mencionar el recurso anterior y recomendar "
    f"una actividad diferente para afrontar la dificultad."
)))
        ),
        provider=SEMANTIC_PROVIDER,
        model=model,
        timeout=timeout,
    )

    return {
        **validation,
        "validation_mode": (
            "joint_current_difficulty_evidence_v1"
        ),
        "validated_quotes": quotes,
    }


def _validate_r(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    reuse = str(
        item.get(
            "reuse_or_adaptation",
            "",
        )
    ).strip()

    if not reuse:
        return {
            "status": "not_supported",
            "reason": (
                "No existe propuesta concreta de reutilizaciÃ³n "
                "o adaptaciÃ³n."
            ),
        }

    relation = item.get(
        "reuse_relation",
        {},
    )

    if not _status_is_confirmed(relation):
        return {
            "status": (
                relation.get("status", "not_supported")
                if isinstance(relation, dict)
                else "not_supported"
            ),
            "reason": (
                "La extracciÃ³n general no confirmÃ³ que la conducta "
                "sea reutilizaciÃ³n o adaptaciÃ³n del recurso."
            ),
        }

    return _validate_ai_component(
        evidence=item.get(
            "reuse_evidence",
            {},
        ),
        proposition=(
            "La respuesta propone reutilizar o adaptar de manera "
            f"concreta el recurso previo de esta forma: {reuse}"
        ),
        current_ai=current_ai,
        model=model,
        timeout=timeout,
        field_name="reuse_evidence",
    )


def _process_item(
    *,
    item: dict[str, Any],
    user_resources: list[dict[str, Any]],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    output = deepcopy(item)

    h_validation = _validate_h(
        item=item,
        user_resources=user_resources,
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    v_validation = _validate_v(
        item=item,
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    r_validation = _validate_r(
        item=item,
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    output["semantic_validation"] = {
        "H": h_validation,
        "V": v_validation,
        "R": r_validation,
    }

    # Normalización especializada AF6:
    # el extractor general puede proponer specific_question,
    # pero si la validación especializada de H determina que
    # la pregunta no alcanza especificidad suficiente, debe
    # conservarse como generic_question y no perderse como
    # señal mínima.
    if (
        output.get("mode") == "specific_question"
        and h_validation.get("status") == "not_supported"
    ):
        output["mode"] = "generic_question"
        output["generic_question_reason"] = (
            "La extracción general propuso specific_question, "
            "pero la validación especializada de H no confirmó "
            "una pregunta suficientemente específica sobre un "
            "recurso, estrategia o conducta previa concreta."
        )

    # Guardrail AF6:
    # si la IA presenta como hecho un recurso previo documentado,
    # pero el usuario no tiene ningún antecedente útil confirmado
    # y H no está sustentada, la atribución constituye una
    # presuposición histórica no sustentada.
    #
    # No se aplica a preguntas específicas/genéricas ni a casos
    # ambiguos: solo a documented_resource inequívocamente
    # incompatible con la ausencia total de antecedentes
    # confirmados del usuario.
    h_reason = str(
        h_validation.get("reason", "")
    )

    unsupported_history = (
        output.get("mode") == "documented_resource"
        and h_validation.get("status") == "not_supported"
        and (
            not user_resources
            or (
                "No se confirmó correspondencia"
                in h_reason
            )
            or (
                "No se confirmÃ³ correspondencia"
                in h_reason
            )
        )
    )

    if unsupported_history:
        output["mode"] = "unsupported_assumption"
        output["unsupported_assumption_reason"] = (
            "La IA presenta como hecho un recurso, apoyo o éxito "
            "previo que no está sustentado por los antecedentes "
            "útiles confirmados del usuario."
        )

    return output


def _execute_af6(
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

    user_resource_result = extract_user_resources(
        current_user=current_user,
        prior_user=prior_user,
        model=model,
        timeout=timeout,
    )

    confirmed_resources = _confirmed_user_resources(
        user_resource_result
    )

    raw_items = general.get(
        "af6_prior_resources",
        [],
    )

    if not isinstance(raw_items, list):
        raise ValueError(
            "af6_prior_resources debe ser una lista."
        )

    processed: list[dict[str, Any]] = []

    for item in raw_items:
        if not isinstance(item, dict):
            continue

        processed.append(
            _process_item(
                item=item,
                user_resources=confirmed_resources,
                current_ai=current_ai,
                model=model,
                timeout=timeout,
            )
        )

    return {
        "prior_resources": processed,
        "confirmed_user_resources": confirmed_resources,
    }



def _validate_af6_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Valida la estructura completa del resultado especializado AF6
    antes de almacenarlo en cache o devolverlo desde cache.

    No asigna puntuaciones ni reinterpreta contenido sem?ntico.
    """

    if not isinstance(result, dict):
        raise ValueError(
            "AF6: el resultado debe ser dict."
        )

    prior_resources = result.get(
        "prior_resources"
    )

    confirmed_user_resources = result.get(
        "confirmed_user_resources"
    )

    if not isinstance(
        prior_resources,
        list,
    ):
        raise ValueError(
            "AF6: prior_resources debe ser una lista."
        )

    if not isinstance(
        confirmed_user_resources,
        list,
    ):
        raise ValueError(
            "AF6: confirmed_user_resources debe ser una lista."
        )

    for index, item in enumerate(
        prior_resources
    ):
        if not isinstance(item, dict):
            raise ValueError(
                "AF6: cada elemento de prior_resources "
                f"debe ser dict; ?ndice={index}."
            )

        semantic = item.get(
            "semantic_validation"
        )

        if not isinstance(
            semantic,
            dict,
        ):
            raise ValueError(
                "AF6: semantic_validation ausente o inv?lido "
                f"en prior_resources[{index}]."
            )

        for component in (
            "H",
            "V",
            "R",
        ):
            validation = semantic.get(
                component
            )

            if not isinstance(
                validation,
                dict,
            ):
                raise ValueError(
                    "AF6: componente "
                    f"{component} inv?lido en "
                    f"prior_resources[{index}]."
                )

            status = validation.get(
                "status"
            )

            if status not in _ALLOWED_STATUSES:
                raise ValueError(
                    "AF6: estado inv?lido para "
                    f"{component} en "
                    f"prior_resources[{index}]: "
                    f"{status!r}."
                )

    for index, item in enumerate(
        confirmed_user_resources
    ):
        if not isinstance(item, dict):
            raise ValueError(
                "AF6: cada elemento de "
                "confirmed_user_resources debe ser dict; "
                f"?ndice={index}."
            )

    return result


def extract_ai_af6(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    API pÃºblica del extractor especializado AF6.

    El resultado se cachea con todos los textos que pueden modificar
    la decisiÃ³n semÃ¡ntica. El timeout no forma parte de la identidad
    porque no modifica el significado del resultado.
    """

    if model != SEMANTIC_MODEL:
        raise ValueError(
            "AF6 debe usar el mismo modelo que el extractor "
            f"general: {SEMANTIC_MODEL!r}."
        )

    inputs = {
        "current_user": current_user,
        "current_ai": current_ai,
        "prior_user": prior_user,
        "prior_ai": prior_ai,
    }

    def execute() -> dict[str, Any]:
        return _execute_af6(
            current_user=current_user,
            current_ai=current_ai,
            prior_user=prior_user,
            prior_ai=prior_ai,
            model=model,
            timeout=timeout,
        )

    return cached_semantic_operation(
        extractor=AF6_EXTRACTOR_NAME,
        extractor_version=AF6_EXTRACTOR_VERSION,
        model=model,
        prompt_version=AF6_PROMPT_VERSION,
        schema_version=AF6_SCHEMA_VERSION,
        parameters=AF6_PARAMETERS,
        inputs=inputs,
        execute=execute,
        validate_result=_validate_af6_result,
    )


def af6_component_is_confirmed(
    item: dict[str, Any],
    component: str,
) -> bool:
    """
    Solo SUPPORTED equivale a componente AF6 confirmado.
    """

    if component not in {"H", "V", "R"}:
        raise ValueError(
            f"Componente AF6 invÃ¡lido: {component!r}."
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
        .get("status")
        == "supported"
    )


def af6_mode(
    item: dict[str, Any],
) -> str:
    return str(
        item.get(
            "mode",
            "",
        )
    ).strip()


def af6_is_generic_question(
    item: dict[str, Any],
) -> bool:
    return (
        af6_mode(item)
        == "generic_question"
    )


def af6_is_unsupported_assumption(
    item: dict[str, Any],
) -> bool:
    return (
        af6_mode(item)
        == "unsupported_assumption"
    )

