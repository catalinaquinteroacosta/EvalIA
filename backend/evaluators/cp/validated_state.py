from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .verifier import CP_COMPONENT_FIELDS


ValidationStatus = Literal[
    "validated",
    "blocked",
]


@dataclass(frozen=True)
class ValidatedIndicatorState:
    """
    Estado semántico posterior a verificación independiente.

    Este objeto NO puntúa y NO decide aplicabilidad.

    Solo permite distinguir entre:

    - componentes respaldados por el verificador;
    - componentes bloqueados por unsupported/ambiguous;
    - evidencia semánticamente verificada;
    - evidencia bloqueada.

    Un indicador con cualquier componente requerido bloqueado
    NO está listo para scoring.
    """

    code: str
    status: ValidationStatus

    components: dict[str, Any]

    blocked_components: tuple[str, ...]

    supported_evidence_indices: tuple[int, ...]
    blocked_evidence_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        normalized = self.code.strip().lower()

        if normalized not in CP_COMPONENT_FIELDS:
            raise ValueError(
                f"Código CP desconocido: {self.code!r}"
            )

        object.__setattr__(
            self,
            "code",
            normalized,
        )

        expected = set(
            CP_COMPONENT_FIELDS[normalized]
        )

        component_keys = set(self.components)

        blocked = set(self.blocked_components)

        if not component_keys.issubset(expected):
            raise ValueError(
                f"{normalized}: components contiene "
                "campos fuera del contrato."
            )

        if not blocked.issubset(expected):
            raise ValueError(
                f"{normalized}: blocked_components contiene "
                "campos fuera del contrato."
            )

        if component_keys & blocked:
            raise ValueError(
                f"{normalized}: un componente no puede estar "
                "simultáneamente validado y bloqueado."
            )

        covered = component_keys | blocked

        if covered != expected:
            raise ValueError(
                f"{normalized}: cobertura incompleta del estado "
                f"validado. missing={sorted(expected-covered)}"
            )

        if self.status == "validated":
            if blocked:
                raise ValueError(
                    f"{normalized}: status='validated' "
                    "no admite componentes bloqueados."
                )

            if component_keys != expected:
                raise ValueError(
                    f"{normalized}: status='validated' exige "
                    "todos los componentes."
                )

            if self.blocked_evidence_indices:
                raise ValueError(
                    f"{normalized}: status='validated' no puede "
                    "contener evidencia bloqueada."
                )

        elif self.status == "blocked":
            if not blocked and not self.blocked_evidence_indices:
                raise ValueError(
                    f"{normalized}: status='blocked' exige "
                    "al menos un componente o evidencia bloqueada."
                )

        else:
            raise ValueError(
                f"ValidationStatus desconocido: "
                f"{self.status!r}"
            )

        if (
            set(self.supported_evidence_indices)
            & set(self.blocked_evidence_indices)
        ):
            raise ValueError(
                f"{normalized}: un índice de evidencia no puede "
                "estar supported y blocked simultáneamente."
            )

    @property
    def ready_for_scoring(self) -> bool:
        return self.status == "validated"


@dataclass(frozen=True)
class ValidatedCPFamilyState:
    """
    Estado validado de CP1–CP8.

    La preparación es INDIVIDUAL por indicador.
    Un CP bloqueado no bloquea automáticamente los demás.
    """

    indicators: dict[str, ValidatedIndicatorState]

    def __post_init__(self) -> None:
        expected = set(CP_COMPONENT_FIELDS)
        observed = set(self.indicators)

        if observed != expected:
            raise ValueError(
                "Cobertura familiar CP incorrecta. "
                f"missing={sorted(expected-observed)}; "
                f"extra={sorted(observed-expected)}"
            )

        for code, state in self.indicators.items():
            if state.code != code:
                raise ValueError(
                    f"{code}: state.code={state.code!r} "
                    "no coincide con la clave."
                )

    def by_code(
        self,
        code: str,
    ) -> ValidatedIndicatorState:
        normalized = code.strip().lower()

        if normalized not in self.indicators:
            raise ValueError(
                f"Código CP desconocido: {code!r}"
            )

        return self.indicators[normalized]

    @property
    def readiness(self) -> dict[str, bool]:
        return {
            code.upper(): state.ready_for_scoring
            for code, state in self.indicators.items()
        }


def _verification_map(
    indicator_verification: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Convierte component_verdicts a mapa por field.

    Fail closed ante duplicados.
    """

    verdicts = indicator_verification.get(
        "component_verdicts"
    )

    if not isinstance(verdicts, list):
        raise ValueError(
            "component_verdicts debe ser una lista."
        )

    result: dict[str, dict[str, Any]] = {}

    for verdict in verdicts:
        if not isinstance(verdict, dict):
            raise ValueError(
                "Cada component_verdict debe ser objeto."
            )

        field = verdict.get("field")

        if not isinstance(field, str):
            raise ValueError(
                "component_verdict.field inválido."
            )

        if field in result:
            raise ValueError(
                f"Veredicto duplicado para {field!r}."
            )

        result[field] = verdict

    return result


def _evidence_partition(
    indicator_verification: dict[str, Any],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """
    Separa evidencia supported de evidencia bloqueada.

    unsupported y ambiguous son ambos fail-closed.
    """

    verdicts = indicator_verification.get(
        "evidence_verdicts"
    )

    if not isinstance(verdicts, list):
        raise ValueError(
            "evidence_verdicts debe ser una lista."
        )

    supported: list[int] = []
    blocked: list[int] = []
    seen: set[int] = set()

    for verdict in verdicts:
        if not isinstance(verdict, dict):
            raise ValueError(
                "Cada evidence_verdict debe ser objeto."
            )

        index = verdict.get("evidence_index")
        status = verdict.get("status")

        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or index < 0
        ):
            raise ValueError(
                "evidence_index inválido."
            )

        if index in seen:
            raise ValueError(
                f"evidence_index duplicado: {index}"
            )

        seen.add(index)

        if status == "supported":
            supported.append(index)

        elif status in {
            "unsupported",
            "ambiguous",
        }:
            blocked.append(index)

        else:
            raise ValueError(
                f"Status de evidencia inválido: {status!r}"
            )

    return (
        tuple(sorted(supported)),
        tuple(sorted(blocked)),
    )


def build_validated_indicator_state(
    *,
    code: str,
    draft_indicator: dict[str, Any],
    verification_indicator: dict[str, Any],
) -> ValidatedIndicatorState:
    """
    Construye el estado validado de UN indicador.

    Regla central:
    solamente status='supported' permite transportar
    el valor extraído al estado validado.

    unsupported/ambiguous NO se convierten en False,
    'none', 0, N/A ni ningún otro valor.

    Se BLOQUEAN.
    """

    normalized = code.strip().lower()

    if normalized not in CP_COMPONENT_FIELDS:
        raise ValueError(
            f"Código CP desconocido: {code!r}"
        )

    if not isinstance(draft_indicator, dict):
        raise ValueError(
            f"{normalized}: draft inválido."
        )

    if not isinstance(
        verification_indicator,
        dict,
    ):
        raise ValueError(
            f"{normalized}: verification inválida."
        )

    if (
        verification_indicator.get(
            "analysis_complete"
        )
        is not True
    ):
        raise ValueError(
            f"{normalized}: verificación incompleta."
        )

    if (
        verification_indicator.get(
            "full_context_audited"
        )
        is not True
    ):
        raise ValueError(
            f"{normalized}: contexto no auditado."
        )

    expected = set(
        CP_COMPONENT_FIELDS[normalized]
    )

    observed_draft = {
        key
        for key in draft_indicator
        if key
        not in {
            "analysis_complete",
            "full_response_audited",
            "evidence",
            "limitation_description",
        }
    }

    if observed_draft != expected:
        raise ValueError(
            f"{normalized}: contrato del draft incorrecto. "
            f"missing={sorted(expected-observed_draft)}; "
            f"extra={sorted(observed_draft-expected)}"
        )

    verdict_map = _verification_map(
        verification_indicator
    )

    if set(verdict_map) != expected:
        raise ValueError(
            f"{normalized}: cobertura del verificador "
            "incorrecta. "
            f"missing={sorted(expected-set(verdict_map))}; "
            f"extra={sorted(set(verdict_map)-expected)}"
        )

    validated: dict[str, Any] = {}
    blocked: list[str] = []

    for field in CP_COMPONENT_FIELDS[normalized]:
        verdict = verdict_map[field]
        status = verdict.get("status")

        if status == "supported":
            validated[field] = draft_indicator[field]

        elif status in {
            "unsupported",
            "ambiguous",
        }:
            blocked.append(field)

        else:
            raise ValueError(
                f"{normalized}.{field}: "
                f"status inválido {status!r}"
            )

    (
        supported_evidence,
        blocked_evidence,
    ) = _evidence_partition(
        verification_indicator
    )

    status: ValidationStatus

    if blocked or blocked_evidence:
        status = "blocked"
    else:
        status = "validated"

    return ValidatedIndicatorState(
        code=normalized,
        status=status,
        components=validated,
        blocked_components=tuple(blocked),
        supported_evidence_indices=supported_evidence,
        blocked_evidence_indices=blocked_evidence,
    )


def build_validated_cp_family_state(
    *,
    draft: dict[str, Any],
    verification: dict[str, Any],
) -> ValidatedCPFamilyState:
    """
    Construye CP1–CP8 de forma independiente.

    No existe bloqueo familiar automático.
    """

    if not isinstance(draft, dict):
        raise ValueError(
            "draft familiar inválido."
        )

    if not isinstance(verification, dict):
        raise ValueError(
            "verification familiar inválida."
        )

    if verification.get("analysis_complete") is not True:
        raise ValueError(
            "Verificación familiar incompleta."
        )

    indicators: dict[
        str,
        ValidatedIndicatorState,
    ] = {}

    for code in CP_COMPONENT_FIELDS:
        if code not in draft:
            raise ValueError(
                f"Falta {code} en draft."
            )

        if code not in verification:
            raise ValueError(
                f"Falta {code} en verification."
            )

        indicators[code] = (
            build_validated_indicator_state(
                code=code,
                draft_indicator=draft[code],
                verification_indicator=verification[
                    code
                ],
            )
        )

    return ValidatedCPFamilyState(
        indicators=indicators
    )
