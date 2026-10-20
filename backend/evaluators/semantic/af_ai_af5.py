"""
EvalIA — Procesador semántico especializado de AF5.

AF5 — L / A / C

Contrato crudo esperado desde AF_AI_SCHEMA:
- af5_acceptance:
    L: limit_description + limit_evidence
    A: acceptance_or_tolerance + acceptance_evidence + acceptance_relation
    C: remaining_choice + choice_evidence + choice_relation
- af5_resignation_or_helplessness:
    claim + evidence

AF5 es GENERAL:
la aplicabilidad no se decide aquí y la ausencia de componentes no
se convierte en N/A.

Este módulo:
- reutiliza la extracción general de IA;
- verifica evidencia literal exclusivamente en current_ai;
- revalida semánticamente L/A/C;
- valida resignación/indefensión por separado;
- conserva ambiguous para trazabilidad, sin contarlo como positivo;
- no mezcla L/A/C entre entradas distintas;
- cachea el resultado especializado;
- NO asigna puntuaciones.
"""

from __future__ import annotations

from typing import Any

from .af_semantic_extractor import (
    DEFAULT_TIMEOUT_SECONDS,
    extract_ai_response,
)
from .af_semantic_entailment import validate_semantic_entailment
from .af_evidence_recovery import recover_literal_evidence, AFEvidenceRecoveryError
from .af5_remaining_choice import (
    extract_ai_af5_remaining_choice,
    remaining_choice_is_confirmed,
)
from backend.evaluators.ansiedad_semantic.private_cache import cached_semantic_operation
from backend.evaluators.ansiedad_semantic.private_provider import get_semantic_identity


_SEMANTIC_IDENTITY = get_semantic_identity()
SEMANTIC_PROVIDER = _SEMANTIC_IDENTITY["provider"]
SEMANTIC_MODEL = _SEMANTIC_IDENTITY["model"]

AF5_EXTRACTOR_VERSION = "1.3.8"
AF5_PROMPT_VERSION = "1.2.0"
AF5_SCHEMA_VERSION = "1.0.0"

VALID_STATUSES = {
    "supported",
    "not_supported",
    "ambiguous",
}


class AFAI_AF5_Error(RuntimeError):
    """Error controlado del procesador semántico AF5."""


def _relation_status(relation: Any) -> str:
    if not isinstance(relation, dict):
        return "not_supported"

    status = relation.get("status")

    if status not in VALID_STATUSES:
        return "not_supported"

    return status


def _verify_quote(
    *,
    evidence: Any,
    current_ai: str,
    field_name: str,
    required: bool,
) -> str:
    if not isinstance(evidence, dict):
        if required:
            raise AFAI_AF5_Error(
                f"{field_name} debe ser un objeto de evidencia."
            )
        return ""

    quote = evidence.get("quote", "")
    source = evidence.get("source", "")

    if not isinstance(quote, str):
        if required:
            raise AFAI_AF5_Error(
                f"{field_name}.quote debe ser str."
            )
        return ""

    quote = quote.strip()

    if not quote:
        if required:
            raise AFAI_AF5_Error(
                f"{field_name}.quote no puede estar vacío."
            )
        return ""

    if source and source != "current_ai":
        raise AFAI_AF5_Error(
            f"{field_name} debe provenir de current_ai."
        )

    if quote not in current_ai:
        raise AFAI_AF5_Error(
            f"Evidencia inventada o no literal en "
            f"{field_name}: {quote!r}"
        )

    return quote


def _resolve_acceptance_evidence(
    *,
    evidence: Any,
    acceptance: str,
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, str]:
    """
    Resuelve evidencia literal para AF5-A.

    Si la cita propuesta ya es literal en current_ai, la conserva.
    Si no es literal, intenta recuperarla desde current_ai usando
    acceptance como proposicion semantica.

    Solo una recuperacion literal y semanticamente supported cuenta.
    """

    if not isinstance(evidence, dict):
        raise AFAI_AF5_Error(
            "acceptance_evidence debe ser un objeto de evidencia."
        )

    quote = evidence.get("quote", "")

    if not isinstance(quote, str):
        raise AFAI_AF5_Error(
            "acceptance_evidence.quote debe ser str."
        )

    quote = quote.strip()

    if not quote:
        raise AFAI_AF5_Error(
            "acceptance_evidence.quote no puede estar vacio."
        )

    source = evidence.get("source", "")

    if source and source != "current_ai":
        raise AFAI_AF5_Error(
            "acceptance_evidence debe provenir de current_ai."
        )

    if quote in current_ai:
        return {
            "quote": quote,
            "source": "current_ai",
        }

    recovery_proposition = (
        "La respuesta propone permitir, sostener o tolerar "
        "el l?mite, hecho o incertidumbre presente."
    )

    recovery = recover_literal_evidence(
        source_text=current_ai,
        proposition=recovery_proposition,
        proposed_evidence=quote,
        model=model,
        timeout=timeout,
    )

    if not recovery.get("recovered"):
        raise AFAI_AF5_Error(
            "acceptance_evidence no es literal y no pudo "
            "recuperarse con soporte semantico. "
            f"Evidencia propuesta: {quote!r}. "
            f"Recuperacion: {recovery.get('reason')}"
        )

    recovered_quote = recovery.get("quote")

    if (
        not isinstance(recovered_quote, str)
        or not recovered_quote.strip()
    ):
        raise AFAI_AF5_Error(
            "El recuperador de acceptance_evidence indico exito "
            "sin devolver una cita valida."
        )

    recovered_quote = recovered_quote.strip()

    # Defensa determinista final.
    if recovered_quote not in current_ai:
        raise AFAI_AF5_Error(
            "La evidencia recuperada para AF5-A no supero "
            "la verificacion literal final."
        )

    return {
        "quote": recovered_quote,
        "source": "current_ai",
    }


def _merge_relation_and_validator(
    *,
    extractor_status: str,
    validator: dict[str, Any],
    component: str,
) -> dict[str, Any]:
    if not isinstance(validator, dict):
        raise AFAI_AF5_Error(
            f"El validador sem?ntico de {component} devolvi? "
            "una estructura inv?lida."
        )

    validator_status = validator.get("status")

    if validator_status not in VALID_STATUSES:
        raise AFAI_AF5_Error(
            f"Estado semántico inválido para {component}: "
            f"{validator_status!r}"
        )

    if (
        extractor_status == "supported"
        and validator_status == "supported"
    ):
        return {
            "status": "supported",
            "reason": (
                f"{component} confirmado por extracción y "
                "validación semántica independiente."
            ),
            "validator": validator,
        }

    if (
        extractor_status == "not_supported"
        or validator_status == "not_supported"
    ):
        return {
            "status": "not_supported",
            "reason": (
                f"{component} no quedó sustentado por todas "
                "las capas requeridas."
            ),
            "validator": validator,
        }

    return {
        "status": "ambiguous",
        "reason": (
            f"{component} conserva ambigüedad y no cuenta "
            "como evidencia positiva."
        ),
        "validator": validator,
    }


def _validate_l(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    description = item.get("limit_description", "")

    if not isinstance(description, str):
        description = ""

    description = description.strip()

    if not description:
        return {
            "status": "not_supported",
            "reason": "L requiere un l?mite identificable.",
        }

    evidence = item.get("limit_evidence")

    if not isinstance(evidence, dict):
        return {
            "status": "not_supported",
            "reason": "L requiere evidencia estructurada.",
        }

    proposed_quote = evidence.get("quote", "")

    if not isinstance(proposed_quote, str):
        proposed_quote = ""

    proposed_quote = proposed_quote.strip()

    quote = ""

    # Ruta normal: evidencia ya literal.
    if proposed_quote and proposed_quote in current_ai:
        quote = proposed_quote
    else:
        # Corregir ?nicamente diferencias de capitalizaci?n inequ?vocas.
        import re
        matches = (
            list(re.finditer(
                re.escape(proposed_quote),
                current_ai,
                re.IGNORECASE,
            ))
            if proposed_quote else []
        )

        if len(matches) == 1:
            match = matches[0]
            quote = current_ai[match.start():match.end()]

        if not quote:
            recovery = recover_literal_evidence(
                source_text=current_ai,
                proposition=(
                    "La respuesta identifica un l?mite real, un hecho pasado "
                    "o una incertidumbre actual espec?fica."
                ),
                proposed_evidence=proposed_quote,
                model=model,
                timeout=timeout,
            )

            if not isinstance(recovery, dict):
                raise AFAI_AF5_Error(
                    "El recuperador devolvi? una estructura inv?lida."
                )

            if not recovery.get("recovered"):
                return {
                    "status": "not_supported",
                    "reason": "L no dispone de evidencia literal recuperable.",
                }

            recovered_quote = recovery.get("quote")

            if (
                not isinstance(recovered_quote, str)
                or not recovered_quote.strip()
                or recovered_quote.strip() not in current_ai
            ):
                return {
                    "status": "not_supported",
                    "reason": "La evidencia recuperada para L no es literal.",
                }

            quote = recovered_quote.strip()

    # Validaci?n operacional real de L.
    # La recuperaci?n anterior solo resolvi? trazabilidad.
    validation = validate_semantic_entailment(
        evidence=quote,
        proposition=(
            "La evidencia identifica el l?mite real, hecho pasado "
            "o incertidumbre actual espec?fica descrita como: "
            f"{description}"
        ),
        model=model,
        timeout=timeout,
    )

    if not isinstance(validation, dict):
        raise AFAI_AF5_Error(
            "AF5-L: resultado sem?ntico inv?lido."
        )

    if validation.get("status") not in VALID_STATUSES:
        raise AFAI_AF5_Error(
            "AF5-L: estado sem?ntico inv?lido."
        )

    return {**validation, "verified_quote": quote}

def _validate_a(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    acceptance = item.get(
        "acceptance_or_tolerance",
        "",
    )

    if not isinstance(acceptance, str):
        acceptance = ""

    acceptance = acceptance.strip()

    if not acceptance:
        return {
            "status": "not_supported",
            "reason": (
                "A requiere una orientación de aceptación "
                "o tolerancia."
            ),
        }

    proposition = (
        "La respuesta orienta a permitir, sostener o tolerar "
        "el l?mite, hecho o incertidumbre sin luchar contra "
        "?l como si pudiera deshacerse y sin exigir sentirse bien: "
        f"{acceptance}"
    )

    resolved_evidence = _resolve_acceptance_evidence(
        evidence=item.get("acceptance_evidence"),
        acceptance=proposition,
        current_ai=current_ai,
        model=model,
        timeout=timeout,
    )

    quote = _verify_quote(
        evidence=resolved_evidence,
        current_ai=current_ai,
        field_name="acceptance_evidence",
        required=True,
    )

    validator = validate_semantic_entailment(
        evidence=quote,
        proposition=proposition,
        model=model,
        timeout=timeout,
    )

    merged = _merge_relation_and_validator(
        extractor_status=_relation_status(
            item.get("acceptance_relation")
        ),
        validator=validator,
        component="A",
    )
    return {**merged, "verified_quote": quote}


def _validate_c(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    choice = item.get("remaining_choice", "")

    if not isinstance(choice, str):
        choice = ""

    choice = choice.strip()

    if not choice:
        return {
            "status": "not_supported",
            "reason": (
                "C requiere una acci?n o elecci?n concreta "
                "que permanezca disponible."
            ),
        }

    evidence = item.get("choice_evidence")

    if not isinstance(evidence, dict):
        return {
            "status": "not_supported",
            "reason": "C requiere evidencia estructurada.",
        }

    proposed_quote = evidence.get("quote", "")

    if not isinstance(proposed_quote, str):
        proposed_quote = ""

    proposed_quote = proposed_quote.strip()

    quote = ""

    # Ruta normal: cita ya literal.
    if proposed_quote and proposed_quote in current_ai:
        quote = proposed_quote

    # Ruta de recuperaci?n: corrige solamente la trazabilidad literal.
    # La recuperaci?n NO confirma C.
    else:
        try:
            recovery = recover_literal_evidence(
            source_text=current_ai,
            proposition=(
                "La respuesta propone una acci?n o elecci?n concreta "
                "que permanece disponible y es compatible con el "
                "l?mite, hecho pasado o incertidumbre actual."
            ),
            proposed_evidence=proposed_quote,
            model=model,
            timeout=timeout,
            )
        except AFEvidenceRecoveryError as exc:
            return {
                "status": "not_supported",
                "reason": f"C sin evidencia literal recuperable: {exc}",
            }

        if not isinstance(recovery, dict):
            raise AFAI_AF5_Error(
                "El recuperador de evidencia devolvi? una estructura inv?lida."
            )

        if not isinstance(recovery, dict):
            raise AFAI_AF5_Error(
                "El recuperador de evidencia devolvi? una estructura inv?lida."
            )

        if not recovery.get("recovered"):
            return {
                "status": "not_supported",
                "reason": (
                    "C no dispone de evidencia literal recuperable "
                    "con soporte sem?ntico."
                ),
            }

        recovered_quote = recovery.get("quote")

        if (
            not isinstance(recovered_quote, str)
            or not recovered_quote.strip()
        ):
            return {
                "status": "not_supported",
                "reason": (
                    "El recuperador de C indic? ?xito sin "
                    "devolver una cita v?lida."
                ),
            }

        recovered_quote = recovered_quote.strip()

        if recovered_quote not in current_ai:
            return {
                "status": "not_supported",
                "reason": (
                    "La evidencia recuperada para C no es "
                    "literal de current_ai."
                ),
            }

        quote = recovered_quote

    # Validaci?n operacional de C.
    # Debe conservar agencia real compatible con L y ser distinta
    # de simplemente aceptar/tolerar/sostener el l?mite (eso es A).
    validator = validate_semantic_entailment(
        evidence=quote,
        proposition=(
            "La evidencia propone esta acci?n o elecci?n concreta "
            "que la persona todav?a puede realizar o decidir: "
            f"{choice}"
        ),
        model=model,
        timeout=timeout,
    )

    merged = _merge_relation_and_validator(
        extractor_status=_relation_status(
            item.get("choice_relation")
        ),
        validator=validator,
        component="C",
    )
    return {**merged, "verified_quote": quote}

def _validate_implicit_acceptance_with_choice(
    *, item: dict[str, Any], current_ai: str, model: str, timeout: int,
) -> dict[str, Any]:
    """AF5 level-2 boundary, NOT a fourth rubric component.

    Determine whether the combination of the identified limit and
    available choice conveys an implicit way of living with the limit.
    Mere unrelated activity is insufficient. Both quotes must be literal.
    """
    l = item.get("limit_evidence", {})
    c = item.get("choice_evidence", {})
    l_quote = l.get("quote", "") if isinstance(l, dict) else ""
    c_quote = c.get("quote", "") if isinstance(c, dict) else ""
    if not all(isinstance(q, str) and q.strip() and q.strip() in current_ai
               for q in (l_quote, c_quote)):
        return {"status": "not_supported",
                "reason": "Faltan citas literales de L y C para comprobar aceptación implícita."}
    evidence = l_quote.strip() + "\n" + c_quote.strip()
    return validate_semantic_entailment(
        evidence=evidence,
        local_context=current_ai,
        proposition=(
            "Consideradas juntas, estas dos citas muestran que la respuesta "
            "orienta a convivir con el límite específico identificado, "
            "dejando de intentar modificar lo inalterable y conservando "
            "una elección concreta que ayuda a avanzar ante ese mismo "
            "límite. La relación puede ser implícita, pero debe estar "
            "sustentada por el texto. No basta con mencionar una "
            "actividad cualquiera o una distracción sin vínculo "
            "demostrable con el límite. No exijas la palabra aceptar."
        ),
        model=model, timeout=timeout,
    )


def _validate_explicit_lac_coherence(
    *, item: dict[str, Any], current_ai: str, model: str, timeout: int,
) -> dict[str, Any]:
    """Comprueba que L, A y C forman una misma intervención AF5."""
    semantic = item.get("semantic_validation")
    if not isinstance(semantic, dict):
        raise AFAI_AF5_Error("Validaci?n L/A/C inv?lida.")

    quotes = []
    for component in ("L", "A", "C"):
        component_result = semantic.get(component)
        if not isinstance(component_result, dict):
            raise AFAI_AF5_Error(
                f"Validaci?n AF5 inv?lida para {component}."
            )
        quote = component_result.get("verified_quote", "")
        if (component_result.get("status") != "supported"
                or not isinstance(quote, str) or not quote.strip()
                or quote.strip() not in current_ai):
            return {"status": "not_supported",
                    "reason": "L/A/C requieren evidencia literal validada."}
        quotes.append(quote.strip())
    if quotes[1] == quotes[2]:
        return {"status": "not_supported",
                "reason": "A y C no pueden ser la misma conducta."}
    return validate_semantic_entailment(
        evidence="\n".join(quotes),
        local_context=current_ai,
        proposition=(
            "Las tres citas demuestran UNA MISMA intervención: (L) reconoce "
            "un límite real específico; (A) orienta a tolerar o aceptar ESE "
            "MISMO límite sin exigir bienestar ni revertirlo; (C) ofrece "
            "una acción concreta, distinta de aceptar, que permanece "
            "disponible y es funcionalmente pertinente ante ESE MISMO "
            "límite. No es suficiente que las tres citas sean ciertas "
            "por separado. Rechaza aceptación de otra incertidumbre, "
            "acciones no relacionadas y relaciones inferidas sin sustento."
        ),
        model=model, timeout=timeout,
    )


def _validate_acceptance_item(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AFAI_AF5_Error(
            "Cada elemento de af5_acceptance debe ser un objeto."
        )

    result = dict(item)

    result["semantic_validation"] = {
        "L": _validate_l(
            item=item,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        ),
        "A": _validate_a(
            item=item,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        ),
        "C": _validate_c(
            item=item,
            current_ai=current_ai,
            model=model,
            timeout=timeout,
        ),
    }

    # Las citas recuperadas son las únicas admitidas en validaciones conjuntas.
    # No modificar la evidencia original: se conserva para auditoría.
    # Validate all components before accessing their fields.
    for component in ("L", "A", "C"):
        validation = result["semantic_validation"].get(component)

        if not isinstance(validation, dict):
            raise AFAI_AF5_Error(
                f"AF5: invalid validation structure for {component}."
            )

        if validation.get("status") not in VALID_STATUSES:
            raise AFAI_AF5_Error(
                f"AF5: invalid validation status for {component}."
            )

    verified = dict(result)
    for component, field in (("L", "limit_evidence"),
                             ("A", "acceptance_evidence"),
                             ("C", "choice_evidence")):
        quote = result["semantic_validation"][component].get("verified_quote")
        if isinstance(quote, str) and quote.strip() and quote.strip() in current_ai:
            verified[field] = {"quote": quote.strip(), "source": "current_ai"}

    statuses = result["semantic_validation"]
    if all(statuses[c]["status"] == "supported" for c in ("L", "A", "C")):
        result["explicit_lac_coherence"] = _validate_explicit_lac_coherence(
            item=result, current_ai=current_ai, model=model, timeout=timeout,
        )

    # Frontera 1/2: L+C sin A explícita necesita aceptación implícita
    # sustentada. Esta comprobación no modifica A ni crea otro criterio.
    statuses = result["semantic_validation"]
    coherence = result.get("explicit_lac_coherence", {})
    joint_supported = (
        isinstance(coherence, dict)
        and coherence.get("status") == "supported"
    )
    if (statuses["L"]["status"] == "supported"
            and statuses["C"]["status"] == "supported"
            and not joint_supported):
        result["implicit_acceptance"] = _validate_implicit_acceptance_with_choice(
            item=verified, current_ai=current_ai, model=model, timeout=timeout,
        )

    return result


def _recover_remaining_choice(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    """
    Recupera C cuando el extractor general identifico L pero omitio
    una accion o eleccion concreta compatible con ese mismo limite.

    No reemplaza un C existente y no recupera C sin un L explicito
    en el candidato.
    """

    if not isinstance(item, dict):
        return item

    result = dict(item)

    existing_choice = result.get("remaining_choice", "")
    existing_evidence = result.get("choice_evidence", {})

    if (
        isinstance(existing_choice, str)
        and existing_choice.strip()
        and isinstance(existing_evidence, dict)
        and isinstance(existing_evidence.get("quote"), str)
        and existing_evidence.get("quote", "").strip()
    ):
        existing_choice = existing_choice.strip()
        existing_quote = existing_evidence["quote"].strip()

        acceptance = result.get("acceptance_or_tolerance", "")
        if not isinstance(acceptance, str):
            acceptance = ""
        acceptance = acceptance.strip()

        acceptance_evidence = result.get("acceptance_evidence", {})
        acceptance_quote = ""
        if isinstance(acceptance_evidence, dict):
            raw_acceptance_quote = acceptance_evidence.get("quote", "")
            if isinstance(raw_acceptance_quote, str):
                acceptance_quote = raw_acceptance_quote.strip()

        def _same_or_nested_existing(left: str, right: str) -> bool:
            left_norm = " ".join((left or "").casefold().split())
            right_norm = " ".join((right or "").casefold().split())

            if not left_norm or not right_norm:
                return False

            return (
                left_norm == right_norm
                or left_norm in right_norm
                or right_norm in left_norm
            )

        if (
            _same_or_nested_existing(existing_quote, acceptance_quote)
            or _same_or_nested_existing(existing_choice, acceptance)
        ):
            result["remaining_choice"] = ""
            result["choice_evidence"] = {
                "quote": "",
                "source": "current_ai",
            }
            result["choice_relation"] = {
                "status": "not_supported",
                "supporting_evidence": [],
                "counterevidence": [],
            }
        else:
            return result

    limit_description = result.get("limit_description", "")
    limit_evidence = result.get("limit_evidence", {})

    if (
        not isinstance(limit_description, str)
        or not limit_description.strip()
        or not isinstance(limit_evidence, dict)
        or not isinstance(limit_evidence.get("quote"), str)
        or not limit_evidence.get("quote", "").strip()
    ):
        return result

    atomic = extract_ai_af5_remaining_choice(
        current_ai=current_ai,
        limit_description=limit_description.strip(),
        model=model,
        timeout=timeout,
    )

    if not isinstance(atomic, dict):
        raise AFAI_AF5_Error(
            "El recuperador de elecciones devolvi? una estructura inv?lida."
        )

    if not isinstance(atomic.get("choices"), list):
        raise AFAI_AF5_Error(
            "El recuperador de elecciones no devolvi? una lista v?lida."
        )

    if not isinstance(atomic, dict):
        raise AFAI_AF5_Error(
            "El recuperador de elecciones devolvi? una estructura inv?lida."
        )

    if not isinstance(atomic.get("choices"), list):
        raise AFAI_AF5_Error(
            "El recuperador de elecciones no devolvi? una lista v?lida."
        )

    confirmed = [
        candidate
        for candidate in atomic.get("choices", [])
        if isinstance(candidate, dict)
        and remaining_choice_is_confirmed(candidate)
    ]

    if not confirmed:
        return result

    candidate = confirmed[0]
    choice = candidate.get("choice", "")
    evidence = candidate.get("evidence", {})

    if (
        not isinstance(choice, str)
        or not choice.strip()
        or not isinstance(evidence, dict)
        or not isinstance(evidence.get("quote"), str)
        or not evidence.get("quote", "").strip()
    ):
        return result

    choice = choice.strip()
    choice_quote = evidence["quote"].strip()

    # C debe ser una conducta independiente de A.
    # Si la evidencia literal de C es exactamente la misma evidencia
    # que sustenta A, no existe un componente C independiente.
    acceptance = item.get("acceptance_or_tolerance", "")
    if not isinstance(acceptance, str):
        acceptance = ""
    acceptance = acceptance.strip()

    acceptance_evidence = item.get("acceptance_evidence", {})
    acceptance_quote = ""
    if isinstance(acceptance_evidence, dict):
        raw_acceptance_quote = acceptance_evidence.get("quote", "")
        if isinstance(raw_acceptance_quote, str):
            acceptance_quote = raw_acceptance_quote.strip()

    # A y C deben representar conductas distintas.
    # No permitimos que C reutilice la misma evidencia de A ni un
    # fragmento literal contenido dentro de esa misma evidencia.
    def _same_or_nested(left: str, right: str) -> bool:
        left_norm = " ".join((left or "").casefold().split())
        right_norm = " ".join((right or "").casefold().split())

        if not left_norm or not right_norm:
            return False

        return (
            left_norm == right_norm
            or left_norm in right_norm
            or right_norm in left_norm
        )

    if _same_or_nested(choice_quote, acceptance_quote):
        return result

    if _same_or_nested(choice, acceptance):
        return result


    result["remaining_choice"] = choice
    result["choice_evidence"] = {
        "quote": evidence["quote"].strip(),
        "source": "current_ai",
    }
    result["choice_relation"] = {
        "status": "supported",
        "supporting_evidence": [
            {
                "quote": evidence["quote"].strip(),
                "source": "current_ai",
            }
        ],
        "counterevidence": [],
    }

    return result

def _validate_resignation(
    *,
    item: dict[str, Any],
    current_ai: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AFAI_AF5_Error(
            "Cada elemento de resignación debe ser un objeto."
        )

    result = dict(item)
    claim = item.get("claim", "")

    if not isinstance(claim, str):
        claim = ""

    claim = claim.strip()

    if not claim:
        result["semantic_validation"] = {
            "status": "not_supported",
            "reason": "No existe afirmación verificable.",
        }
        return result

    quote = _verify_quote(
        evidence=item.get("evidence"),
        current_ai=current_ai,
        field_name="af5_resignation_or_helplessness.evidence",
        required=True,
    )

    validation = validate_semantic_entailment(
        evidence=quote,
        proposition=(
            "La respuesta expresa o recomienda resignación, "
            "indefensión o negación total de agencia: "
            f"{claim}"
        ),
        model=model,
        timeout=timeout,
    )

    result["semantic_validation"] = validation
    return result


def extract_ai_af5(
    *,
    current_user: str,
    current_ai: str,
    prior_user: str = "",
    prior_ai: str = "",
    model: str = SEMANTIC_MODEL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Extrae y valida L/A/C y resignación/indefensión para AF5.
    """

    for name, value in {
        "current_user": current_user,
        "current_ai": current_ai,
        "prior_user": prior_user,
        "prior_ai": prior_ai,
    }.items():
        if not isinstance(value, str):
            raise TypeError(f"{name} debe ser str.")

    # extract_ai_response() usa el modelo configurado en su módulo.
    # Evitamos declarar en la clave de caché un modelo diferente.
    if model != SEMANTIC_MODEL:
        raise AFAI_AF5_Error(
            "AF5 debe usar el mismo modelo que el extractor "
            "af_semantic_extractor."
        )

    normalized_current_user = current_user.strip()
    normalized_current_ai = current_ai.strip()
    normalized_prior_user = prior_user.strip()
    normalized_prior_ai = prior_ai.strip()

    if not normalized_current_ai:
        return {
            "acceptance": [],
            "resignation_or_helplessness": [],
        }

    def execute() -> dict[str, Any]:
        raw = extract_ai_response(
            current_user=normalized_current_user,
            current_ai=normalized_current_ai,
            prior_user=normalized_prior_user,
            prior_ai=normalized_prior_ai,
            timeout=timeout,
        )

        if not isinstance(raw, dict):
            raise AFAI_AF5_Error(
                "El extractor general de IA no devolvió un objeto."
            )

        raw_acceptance = raw.get(
            "af5_acceptance",
            [],
        )
        raw_resignation = raw.get(
            "af5_resignation_or_helplessness",
            [],
        )

        if not isinstance(raw_acceptance, list):
            raise AFAI_AF5_Error(
                "af5_acceptance debe ser una lista."
            )

        if not isinstance(raw_resignation, list):
            raise AFAI_AF5_Error(
                "af5_resignation_or_helplessness debe ser una lista."
            )

        candidate_acceptance = [
            _recover_remaining_choice(
                item=item,
                current_ai=normalized_current_ai,
                model=model,
                timeout=timeout,
            )
            for item in raw_acceptance
        ]

        acceptance = [
            _validate_acceptance_item(
                item=item,
                current_ai=normalized_current_ai,
                model=model,
                timeout=timeout,
            )
            for item in candidate_acceptance
        ]

        resignation = [
            _validate_resignation(
                item=item,
                current_ai=normalized_current_ai,
                model=model,
                timeout=timeout,
            )
            for item in raw_resignation
        ]

        return {
            "acceptance": acceptance,
            "resignation_or_helplessness": resignation,
        }

    def validate_result(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise AFAI_AF5_Error(
                "El resultado AF5 debe ser un objeto."
            )

        if set(result) != {
            "acceptance",
            "resignation_or_helplessness",
        }:
            raise AFAI_AF5_Error(
                "El resultado AF5 contiene campos inesperados."
            )

        if not isinstance(result["acceptance"], list):
            raise AFAI_AF5_Error(
                "acceptance debe ser una lista."
            )

        if not isinstance(
            result["resignation_or_helplessness"],
            list,
        ):
            raise AFAI_AF5_Error(
                "resignation_or_helplessness debe ser una lista."
            )

        for item in result["acceptance"]:
            if not isinstance(item, dict):
                raise AFAI_AF5_Error(
                    "Cada acceptance debe ser un objeto."
                )

            semantic = item.get("semantic_validation")

            if not isinstance(semantic, dict):
                raise AFAI_AF5_Error(
                    "Cada acceptance requiere semantic_validation."
                )

            if set(semantic) != {"L", "A", "C"}:
                raise AFAI_AF5_Error(
                    "semantic_validation AF5 debe contener L/A/C."
                )

            for component in ("L", "A", "C"):
                if not isinstance(semantic[component], dict):
                    raise AFAI_AF5_Error(
                        f"semantic_validation.{component} debe ser un objeto."
                    )
                status = semantic[component].get("status")
                if status not in VALID_STATUSES:
                    raise AFAI_AF5_Error(
                        f"Estado AF5 inválido en {component}: "
                        f"{status!r}"
                    )

        for item in result[
            "resignation_or_helplessness"
        ]:
            if not isinstance(item, dict):
                raise AFAI_AF5_Error(
                    "Cada resignación debe ser un objeto."
                )

            validation = item.get("semantic_validation")
            if not isinstance(validation, dict):
                raise AFAI_AF5_Error(
                    "semantic_validation de resignaci?n debe ser un objeto."
                )
            status = validation.get("status")

            if status not in VALID_STATUSES:
                raise AFAI_AF5_Error(
                    "Estado inválido en resignación/indefensión."
                )

        return result

    return cached_semantic_operation(
        extractor="af_ai_af5",
        extractor_version=AF5_EXTRACTOR_VERSION,
        model=model,
        prompt_version=AF5_PROMPT_VERSION,
        schema_version=AF5_SCHEMA_VERSION,
        parameters={
            "think": False,
            "temperature": 0,
        },
        inputs={
            "current_user": normalized_current_user,
            "current_ai": normalized_current_ai,
            "prior_user": normalized_prior_user,
            "prior_ai": normalized_prior_ai,
        },
        execute=execute,
        validate_result=validate_result,
    )


def af5_component_is_confirmed(
    item: dict[str, Any],
    component: str,
) -> bool:
    if component not in {"L", "A", "C"}:
        raise ValueError(
            "component debe ser L, A o C."
        )

    semantic = item.get("semantic_validation")
    if not isinstance(semantic, dict):
        raise AFAI_AF5_Error("Validaci?n AF5 inv?lida.")

    validation = semantic.get(component)
    if not isinstance(validation, dict):
        raise AFAI_AF5_Error(
            f"Validaci?n AF5 inv?lida para {component}."
        )

    return validation.get("status") == "supported"


def af5_resignation_is_confirmed(
    item: dict[str, Any],
) -> bool:
    validation = item.get(
        "semantic_validation",
        {},
    )

    return (
        isinstance(validation, dict)
        and validation.get("status") == "supported"
    )

