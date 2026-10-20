"""Pipeline coordinado de la familia CP de EvalIA.

Flujo normativo:

contexto causal
-> extracci?n sem?ntica
-> verificaci?n independiente
-> estado validado
-> reconciliaci?n SOLO de BLOCKED
-> scoring determin?stico individual

El pipeline NO contiene interpretaci?n sem?ntica propia.
El pipeline NO modifica la r?brica.
El pipeline NO punt?a mediante IA.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import PriorTurn
from .extractor import extract_cp_family
from .verifier import verify_cp_family
from .validated_state import (
    ValidatedCPFamilyState,
    ValidatedIndicatorState,
    build_validated_cp_family_state,
)
from .reconciliation import (
    ReconciliationResult,
    reconcile_blocked_indicator,
)
from .scoring import (
    CPIndicatorScore,
    score_validated_indicator,
)


CP_CODES = tuple(
    f"CP{i}"
    for i in range(1, 9)
)


@dataclass(frozen=True)
class CPPipelineResult:
    """Resultado trazable de una evaluaci?n completa CP."""

    draft: dict[str, Any]
    verification: dict[str, Any]
    initial_validated_state: ValidatedCPFamilyState
    final_states: dict[str, ValidatedIndicatorState]
    reconciliations: dict[str, ReconciliationResult]
    scores: dict[str, CPIndicatorScore]
    technical_errors: dict[str, str] | None = None

    def __post_init__(self) -> None:
        expected = set(CP_CODES)

        if set(self.final_states) != expected:
            raise ValueError(
                "final_states debe contener exactamente CP1-CP8."
            )

        if set(self.scores) != expected:
            raise ValueError(
                "scores debe contener exactamente CP1-CP8."
            )

        if not set(self.reconciliations).issubset(expected):
            raise ValueError(
                "reconciliations contiene indicador desconocido."
            )

    @property
    def blocked_codes(self) -> tuple[str, ...]:
        """Indicadores todav?a BLOCKED despu?s de reconciliaci?n."""

        return tuple(
            code
            for code in CP_CODES
            if self.final_states[code].status == "blocked"
        )

    @property
    def reconciled_codes(self) -> tuple[str, ...]:
        """Indicadores que necesitaron segunda pasada."""

        return tuple(
            code
            for code in CP_CODES
            if code in self.reconciliations
        )

    @property
    def ready_codes(self) -> tuple[str, ...]:
        """Indicadores validados despu?s del pipeline sem?ntico."""

        return tuple(
            code
            for code in CP_CODES
            if self.final_states[code].status == "validated"
        )


def _initial_state_map(
    family_state: ValidatedCPFamilyState,
) -> dict[str, ValidatedIndicatorState]:
    """Normaliza las claves p?blicas a CP1-CP8."""

    result: dict[str, ValidatedIndicatorState] = {}

    for code in CP_CODES:
        key = code.lower()

        if key in family_state.indicators:
            state = family_state.indicators[key]
        elif code in family_state.indicators:
            state = family_state.indicators[code]
        else:
            raise ValueError(
                f"Falta {code} en ValidatedCPFamilyState."
            )

        if state.code.lower() != key:
            raise ValueError(
                f"Estado inconsistente para {code}: "
                f"{state.code!r}"
            )

        result[code] = state

    return result


def run_cp_pipeline(
    *,
    user_text: str,
    response_text: str,
    prior_history: tuple[PriorTurn, ...] = (),
    provider: str | None = None,
    model: str | None = None,
    timeout: int = 600,
    extraction_max_output_tokens: int = 12000,
    verification_max_output_tokens: int = 12000,
    reconciliation_max_output_tokens: int = 6000,
) -> CPPipelineResult:
    """Ejecuta CP1-CP8 respetando independencia por indicador."""

    if not isinstance(user_text, str):
        raise TypeError("user_text debe ser str.")

    if not isinstance(response_text, str):
        raise TypeError("response_text debe ser str.")

    if not isinstance(prior_history, tuple):
        raise TypeError("prior_history debe ser tuple.")

    # ---------------------------------------------------------
    # A. Extracci?n sem?ntica cacheada.
    # ---------------------------------------------------------

    draft = extract_cp_family(
        user_text=user_text,
        response_text=response_text,
        prior_history=prior_history,
        provider=provider,
        model=model,
        timeout=timeout,
        max_output_tokens=extraction_max_output_tokens,
    )

    # ---------------------------------------------------------
    # B. Verificaci?n sem?ntica independiente cacheada.
    # ---------------------------------------------------------

    verification = verify_cp_family(
        draft=draft,
        user_text=user_text,
        response_text=response_text,
        prior_history=prior_history,
        provider=provider,
        model=model,
        timeout=timeout,
        max_output_tokens=verification_max_output_tokens,
    )

    # ---------------------------------------------------------
    # C. Construcci?n fail-closed del estado validado.
    # ---------------------------------------------------------

    initial_family = build_validated_cp_family_state(
        draft=draft,
        verification=verification,
    )

    initial_states = _initial_state_map(
        initial_family
    )

    final_states = dict(initial_states)

    # ---------------------------------------------------------
    # D. Segunda pasada SOLO para indicadores BLOCKED.
    #
    # Un fallo/no resoluci?n de un CP no bloquea los dem?s.
    # ---------------------------------------------------------

    reconciliations: dict[
        str,
        ReconciliationResult,
    ] = {}

    technical_errors: dict[str, str] = {}

    for code in CP_CODES:
        state = initial_states[code]

        if state.status != "blocked":
            continue

        try:
            reconciliation = reconcile_blocked_indicator(
                state=state,
                draft=draft,
                verification=verification,
                user_text=user_text,
                response_text=response_text,
                prior_history=prior_history,
                provider=provider,
                model=model,
                timeout=timeout,
                max_output_tokens=(
                    reconciliation_max_output_tokens
                ),
            )
        except Exception as exc:
            technical_errors[code] = (
                "reconciliation: "
                f"{type(exc).__name__}: {exc}"
            )
            # Fail-closed: conservar estado BLOCKED original.
            continue

        reconciliations[code] = reconciliation
        final_states[code] = (
            reconciliation.resolved_state
        )

    # ---------------------------------------------------------
    # E. Scoring determin?stico.
    #
    # Incluso si un indicador sigue BLOCKED, se procesa
    # individualmente y scoring.py devuelve status t?cnico
    # sin fabricar una puntuaci?n.
    # ---------------------------------------------------------

    evaluable_response_present = bool(
        response_text.strip()
    )

    scores: dict[str, CPIndicatorScore] = {}

    for code in CP_CODES:
        try:
            scores[code] = score_validated_indicator(
                final_states[code],
                evaluable_response_present=(
                    evaluable_response_present
                ),
            )
        except Exception as exc:
            technical_errors[code] = (
                "scoring: "
                f"{type(exc).__name__}: {exc}"
            )

            scores[code] = CPIndicatorScore(
                code=code,
                status="technical_error",
                score=None,
                reason=(
                    "Fallo t?cnico de scoring; "
                    "no representa ausencia de evidencia."
                ),
            )

    return CPPipelineResult(
        draft=draft,
        verification=verification,
        initial_validated_state=initial_family,
        final_states=final_states,
        reconciliations=reconciliations,
        scores=scores,
        technical_errors=technical_errors,
    )
