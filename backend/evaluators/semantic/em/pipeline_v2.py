"""Pipeline canónico EM V2.

Flujo:
contexto autorizado
-> aplicabilidad
-> extracción semántica cacheada
-> verificación independiente cacheada
-> reconciliación SOLO de componentes BLOCKED
-> scoring determinístico
-> 0/1/2/3/N/A/BLOCKED

Reglas:
- N/A != BLOCKED.
- unsupported NO se invierte.
- ambiguous NO se fuerza.
- solo status=supported resuelve proposed_value.
- una discrepancia recibe una segunda pasada independiente.
- un indicador BLOCKED no bloquea otros indicadores.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from .em_private_cache import (
    cached_semantic_operation,
)
from backend.evaluators.semantic.semantic_provider import (
    get_semantic_identity,
)

from .applicability import (
    determine_em_applicability,
)
from .extractor_v2 import (
    EM_EXTRACTOR_V2_VERSION,
    extract_em_components_v2,
)
from .schemas_v2 import (
    get_em_schema_v2,
)
from .scorer import (
    EM_SCORER_VERSION,
    UnresolvedScoringState,
    VerifiedSemanticValue,
    score_em_indicator,
)
from .verifier_v2 import (
    EM_VERIFIER_V2_VERSION,
    verify_component_semantics_v2,
)


EM_PIPELINE_V2_VERSION = "EM-PIPELINE-2.0.0"

VALID_CODES = tuple(
    f"EM{i}" for i in range(1, 14)
)

GENERAL_CODES = frozenset({
    "EM1", "EM2", "EM3", "EM4",
    "EM5", "EM6", "EM7", "EM8",
    "EM10", "EM11", "EM12", "EM13",
})

APPLICABILITY_COMPONENTS = {
    "EM9": (
        "important_information_missing",
        "materially_different_interpretations",
        "guidance_requires_missing_information",
    ),
}


class _DoNotCacheSemanticResult(RuntimeError):
    """Transporta un resultado válido que no debe persistirse."""

    def __init__(
        self,
        result: dict[str, Any],
    ) -> None:
        super().__init__(
            "Resultado semántico válido pero no cacheable."
        )
        self.result = result


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(
            asdict(value)
        )

    if isinstance(value, Mapping):
        return {
            str(k): _json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _json_safe(v)
            for v in value
        ]

    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if hasattr(value, "__dict__"):
        return _json_safe(
            vars(value)
        )

    return str(value)


def _normalized_history(
    prior_history: Sequence[
        Mapping[str, object]
    ] | None,
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for item in prior_history or []:
        role = str(
            item["role"]
        )
        text = str(
            item["text"]
        )

        if role not in {
            "user",
            "assistant",
        }:
            raise ValueError(
                f"Rol histórico inválido: {role!r}"
            )

        result.append({
            "role": role,
            "text": text,
        })

    return result


def _schema_identity(
    indicator_code: str,
) -> str:
    schema = get_em_schema_v2(
        indicator_code
    )

    raw = json.dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]

    return (
        f"EM-SCHEMA-V2-{digest}"
    )


def _blocked_result(
    *,
    indicator_code: str,
    reason: str,
    extraction: dict[str, Any] | None = None,
    verifications: dict[str, Any] | None = None,
    reconciliation: dict[str, Any] | None = None,
    applicability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "indicator_code": indicator_code,
        "status": "blocked",
        "applicable": None,
        "score": None,
        "reason": reason,
        "applicability": applicability,
        "extraction": extraction,
        "verifications": verifications or {},
        "reconciliation": reconciliation or {},
        "pipeline_version": EM_PIPELINE_V2_VERSION,
        "extractor_version": EM_EXTRACTOR_V2_VERSION,
        "verifier_version": EM_VERIFIER_V2_VERSION,
        "scorer_version": EM_SCORER_VERSION,
    }


def _na_result(
    *,
    indicator_code: str,
    reason: str,
    extraction: dict[str, Any] | None = None,
    verifications: dict[str, Any] | None = None,
    reconciliation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "indicator_code": indicator_code,
        "status": "ok",
        "applicable": False,
        "score": None,
        "reason": reason,
        "applicability": {
            "applicable": False,
            "reason": reason,
        },
        "extraction": extraction,
        "verifications": verifications or {},
        "reconciliation": reconciliation or {},
        "pipeline_version": EM_PIPELINE_V2_VERSION,
        "extractor_version": EM_EXTRACTOR_V2_VERSION,
        "verifier_version": EM_VERIFIER_V2_VERSION,
        "scorer_version": EM_SCORER_VERSION,
    }


def _extract_cached(
    *,
    indicator_code: str,
    user_message: str,
    ai_response: str,
    prior_history: list[dict[str, str]],
    provider: str,
    model: str,
) -> dict[str, Any]:

    def execute():
        return extract_em_components_v2(
            indicator_code=indicator_code,
            user_message=user_message,
            ai_response=ai_response,
            prior_history=prior_history,
            provider=provider,
            model=model,
        )

    def validate(result):
        safe = _json_safe(result)

        if (
            safe.get("indicator_code")
            != indicator_code
        ):
            raise ValueError(
                "Extractor devolvió indicador incorrecto."
            )

        if not safe.get(
            "literal_evidence_valid",
            False,
        ):
            raise ValueError(
                "Extractor con evidencia literal inválida."
            )

        components = safe.get(
            "components"
        )

        if not isinstance(
            components,
            dict,
        ) or not components:
            raise ValueError(
                "Extractor sin componentes válidos."
            )

        return safe

    return cached_semantic_operation(
        extractor=(
            "evalia.em.extractor_v2"
        ),
        extractor_version=(
            EM_EXTRACTOR_V2_VERSION
        ),
        model=f"{provider}:{model}",
        prompt_version=(
            EM_EXTRACTOR_V2_VERSION
        ),
        schema_version=_schema_identity(
            indicator_code
        ),
        parameters={
            "indicator_code":
                indicator_code,
            "operation":
                "component_extraction",
        },
        inputs={
            "prior_history":
                prior_history,
            "user_message":
                user_message,
            "ai_response":
                ai_response,
        },
        execute=execute,
        validate_result=validate,
    )


def _verify_cached(
    *,
    indicator_code: str,
    component_name: str,
    component: dict[str, Any],
    siblings: dict[str, str],
    prior_history: list[dict[str, str]],
    user_message: str,
    ai_response: str,
    provider: str,
    model: str,
    pass_name: str,
) -> dict[str, Any]:

    def execute():
        return verify_component_semantics_v2(
            indicator_code=indicator_code,
            component_name=component_name,
            proposed_value=component["value"],
            evidence=component.get(
                "evidence",
                [],
            ),
            counterevidence=component.get(
                "counterevidence",
                [],
            ),
            prior_history=prior_history,
            user_message=user_message,
            ai_response=ai_response,
            sibling_components=siblings,
            provider=provider,
            model=model,
        )

    def validate(result):
        safe = _json_safe(result)

        status = safe.get(
            "status"
        )

        if status not in {
            "supported",
            "unsupported",
            "ambiguous",
        }:
            raise ValueError(
                f"Status verifier inválido: {status!r}"
            )

        if safe.get(
            "verification_error"
        ):
            raise _DoNotCacheSemanticResult(
                safe
            )

        # Solo supported se reutiliza.
        # Un desacuerdo/ambigüedad puede convertirse
        # en BLOCKED y debe poder reconciliarse
        # mediante una llamada independiente.
        if status != "supported":
            raise _DoNotCacheSemanticResult(
                safe
            )

        return safe

    try:
        return cached_semantic_operation(
            extractor=(
                "evalia.em.verifier_v2"
            ),
            extractor_version=(
                EM_VERIFIER_V2_VERSION
            ),
            model=f"{provider}:{model}",
            prompt_version=(
                EM_VERIFIER_V2_VERSION
            ),
            schema_version=(
                "EM-VERIFIER-OUTPUT-V2"
            ),
            parameters={
                "indicator_code":
                    indicator_code,
                "component_name":
                    component_name,
                "proposed_value":
                    component["value"],
                "pass":
                    pass_name,
            },
            inputs={
                "prior_history":
                    prior_history,
                "user_message":
                    user_message,
                "ai_response":
                    ai_response,
                "evidence":
                    component.get(
                        "evidence",
                        [],
                    ),
                "counterevidence":
                    component.get(
                        "counterevidence",
                        [],
                    ),
                "sibling_components":
                    siblings,
            },
            execute=execute,
            validate_result=validate,
        )

    except _DoNotCacheSemanticResult as exc:
        return exc.result


def _verify_component_with_reconciliation(
    *,
    indicator_code: str,
    component_name: str,
    components: dict[str, Any],
    prior_history: list[dict[str, str]],
    user_message: str,
    ai_response: str,
    provider: str,
    model: str,
) -> tuple[
    VerifiedSemanticValue | None,
    dict[str, Any],
    dict[str, Any] | None,
]:

    component = components[
        component_name
    ]

    siblings = {
        name: data["value"]
        for name, data
        in components.items()
        if name != component_name
    }

    primary = _verify_cached(
        indicator_code=indicator_code,
        component_name=component_name,
        component=component,
        siblings=siblings,
        prior_history=prior_history,
        user_message=user_message,
        ai_response=ai_response,
        provider=provider,
        model=model,
        pass_name="primary",
    )

    if (
        primary.get("status")
        == "supported"
        and not primary.get(
            "verification_error"
        )
    ):
        return (
            VerifiedSemanticValue(
                name=component_name,
                proposed_value=component[
                    "value"
                ],
                verification_status=(
                    "supported"
                ),
            ),
            primary,
            None,
        )

    # Segunda pasada SOLO porque el componente
    # quedó técnicamente bloqueado.
    reconciliation = _verify_cached(
        indicator_code=indicator_code,
        component_name=component_name,
        component=component,
        siblings=siblings,
        prior_history=prior_history,
        user_message=user_message,
        ai_response=ai_response,
        provider=provider,
        model=model,
        pass_name="reconciliation",
    )

    if (
        reconciliation.get("status")
        == "supported"
        and not reconciliation.get(
            "verification_error"
        )
    ):
        return (
            VerifiedSemanticValue(
                name=component_name,
                proposed_value=component[
                    "value"
                ],
                verification_status=(
                    "supported"
                ),
            ),
            primary,
            reconciliation,
        )

    return (
        None,
        primary,
        reconciliation,
    )


def evaluate_em_indicator_v2(
    indicator_code: str,
    *,
    user_message: str,
    ai_response: str,
    prior_history: Sequence[
        Mapping[str, object]
    ] | None = None,
    evaluable_emotional_or_experiential_content: str = "true",
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:

    code = str(
        indicator_code
    ).strip().upper()

    if code not in VALID_CODES:
        raise ValueError(
            f"Indicador EM desconocido: {indicator_code!r}"
        )

    history = _normalized_history(
        prior_history
    )

    identity = get_semantic_identity(
        provider=provider,
        model=model,
    )

    provider_name = identity[
        "provider"
    ]
    model_name = identity[
        "model"
    ]

    # --------------------------------------------------
    # Aplicabilidad GENERAL.
    # unknown NO es N/A.
    # --------------------------------------------------

    if code in GENERAL_CODES:

        if (
            evaluable_emotional_or_experiential_content
            == "unknown"
        ):
            return _blocked_result(
                indicator_code=code,
                reason=(
                    "La existencia de contenido emocional "
                    "o experiencial evaluable permanece "
                    "semanticamente no resuelta."
                ),
            )

        applicability = (
            determine_em_applicability(
                code,
                {},
                evaluable_emotional_or_experiential_content=(
                    evaluable_emotional_or_experiential_content
                ),
            )
        )

        if not applicability.applicable:
            return _na_result(
                indicator_code=code,
                reason=applicability.reason,
            )

    extraction = _extract_cached(
        indicator_code=code,
        user_message=user_message,
        ai_response=ai_response,
        prior_history=history,
        provider=provider_name,
        model=model_name,
    )

    components = extraction[
        "components"
    ]

    verifications: dict[
        str,
        Any,
    ] = {}

    reconciliation: dict[
        str,
        Any,
    ] = {}

    verified: dict[
        str,
        VerifiedSemanticValue,
    ] = {}

    # --------------------------------------------------
    # EM9 / EM13:
    # verificar primero SOLO componentes que gobiernan
    # aplicabilidad.
    # --------------------------------------------------

    governing = APPLICABILITY_COMPONENTS.get(
        code,
        (),
    )

    for name in governing:

        if name not in components:
            return _blocked_result(
                indicator_code=code,
                reason=(
                    "Falta componente requerido para "
                    f"aplicabilidad: {name}"
                ),
                extraction=extraction,
                verifications=verifications,
                reconciliation=reconciliation,
            )

        value, primary, second = (
            _verify_component_with_reconciliation(
                indicator_code=code,
                component_name=name,
                components=components,
                prior_history=history,
                user_message=user_message,
                ai_response=ai_response,
                provider=provider_name,
                model=model_name,
            )
        )

        verifications[name] = primary

        if second is not None:
            reconciliation[name] = second

        if value is None:
            return _blocked_result(
                indicator_code=code,
                reason=(
                    "La aplicabilidad no puede resolverse "
                    "porque el componente "
                    f"{name!r} permanece BLOCKED "
                    "después de reconciliación."
                ),
                extraction=extraction,
                verifications=verifications,
                reconciliation=reconciliation,
            )

        verified[name] = value

    if code == "EM9":

        applicability_values = {
            name:
                components[name]["value"]
            for name in governing
        }

        # determine_em_applicability ya no puede
        # recibir unknown en una condición gobernante
        # confirmada como resoluble. Aun así se blinda.
        if any(
            value == "unknown"
            for value
            in applicability_values.values()
        ):
            return _blocked_result(
                indicator_code=code,
                reason=(
                    "La condición de aplicabilidad "
                    "permanece unknown después de "
                    "verificación."
                ),
                extraction=extraction,
                verifications=verifications,
                reconciliation=reconciliation,
            )

        applicability = determine_em_applicability(code, applicability_values)
        if not applicability.applicable:
            return _na_result(
                indicator_code=code,
                reason=applicability.reason,
                extraction=extraction,
                verifications=verifications,
                reconciliation=reconciliation,
            )

    # --------------------------------------------------
    # Indicador aplicable:
    # verificar componentes restantes.
    # --------------------------------------------------

    for name in components:

        if name in verified:
            continue

        value, primary, second = (
            _verify_component_with_reconciliation(
                indicator_code=code,
                component_name=name,
                components=components,
                prior_history=history,
                user_message=user_message,
                ai_response=ai_response,
                provider=provider_name,
                model=model_name,
            )
        )

        verifications[name] = primary

        if second is not None:
            reconciliation[name] = second

        if value is None:
            return _blocked_result(
                indicator_code=code,
                reason=(
                    f"{name} permanece BLOCKED "
                    "después de la reconciliación "
                    "independiente."
                ),
                extraction=extraction,
                verifications=verifications,
                reconciliation=reconciliation,
                applicability={
                    "applicable": True,
                    "reason": (
                        applicability.reason
                    ),
                },
            )

        verified[name] = value

    try:
        score = score_em_indicator(
            code,
            applicable=True,
            applicability_reason=(
                applicability.reason
            ),
            values=verified,
        )

    except UnresolvedScoringState as exc:
        return _blocked_result(
            indicator_code=code,
            reason=(
                "Scoring no resoluble: "
                f"{exc}"
            ),
            extraction=extraction,
            verifications=verifications,
            reconciliation=reconciliation,
            applicability={
                "applicable": True,
                "reason": (
                    applicability.reason
                ),
            },
        )

    return {
        "indicator_code": code,
        "status": "ok",
        "applicable": True,
        "score": score.score,
        "reason": score.reason,
        "applicability": {
            "applicable": True,
            "reason": applicability.reason,
        },
        "extraction": extraction,
        "verifications": verifications,
        "reconciliation": reconciliation,
        "pipeline_version": EM_PIPELINE_V2_VERSION,
        "extractor_version": EM_EXTRACTOR_V2_VERSION,
        "verifier_version": EM_VERIFIER_V2_VERSION,
        "scorer_version": EM_SCORER_VERSION,
    }


def evaluate_em_family_v2(
    *,
    user_message: str,
    ai_response: str,
    prior_history: Sequence[
        Mapping[str, object]
    ] | None = None,
    evaluable_emotional_or_experiential_content: str = "true",
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:

    indicators: dict[
        str,
        dict[str, Any],
    ] = {}

    for code in VALID_CODES:

        try:
            indicators[code] = (
                evaluate_em_indicator_v2(
                    code,
                    user_message=user_message,
                    ai_response=ai_response,
                    prior_history=prior_history,
                    evaluable_emotional_or_experiential_content=(
                        evaluable_emotional_or_experiential_content
                    ),
                    provider=provider,
                    model=model,
                )
            )

        except Exception as exc:
            # Aislamiento familiar:
            # un problema técnico no detiene
            # los otros indicadores.
            indicators[code] = {
                "indicator_code": code,
                "status": "error",
                "applicable": None,
                "score": None,
                "reason": (
                    f"{type(exc).__name__}: {exc}"
                ),
                "pipeline_version":
                    EM_PIPELINE_V2_VERSION,
            }

    return {
        "family": "EM",
        "pipeline_version":
            EM_PIPELINE_V2_VERSION,
        "indicators": indicators,
    }
