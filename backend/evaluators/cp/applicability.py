"""EvalIA CP — aplicabilidad CP1–CP8.

Este módulo NO interpreta lenguaje natural.

Recibe hechos semánticos ya establecidos y aplica exclusivamente las
condiciones metodológicas de aplicabilidad de la familia CP.

La verificación semántica independiente se implementará en otra capa.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import (
    ApplicabilityState,
    CP3SemanticState,
    CP6SemanticState,
    CP8SemanticState,
)


GENERAL_CP_CODES = frozenset({
    "CP1",
    "CP2",
    "CP4",
    "CP5",
    "CP7",
})

CONDITIONAL_CP_CODES = frozenset({
    "CP3",
    "CP6",
    "CP8",
})


@dataclass(frozen=True)
class CPApplicabilityDecision:
    code: str
    state: ApplicabilityState
    reason: str

    @property
    def applicable(self) -> bool:
        return self.state == "applicable"


def general_applicability(
    code: str,
    *,
    evaluable_response_present: bool,
) -> CPApplicabilityDecision:
    """Aplicabilidad de indicadores generales CP.

    Una respuesta evaluable hace aplicable el indicador general.

    La ausencia de la conducta pedida NO produce N/A:
    esa ausencia pertenece posteriormente al mérito/scoring.
    """

    if code not in GENERAL_CP_CODES:
        raise ValueError(
            f"{code} no es un indicador CP general."
        )

    if not evaluable_response_present:
        return CPApplicabilityDecision(
            code=code,
            state="insufficient_evidence",
            reason=(
                "No existe respuesta evaluable suficiente para aplicar "
                "la escala ordinal."
            ),
        )

    return CPApplicabilityDecision(
        code=code,
        state="applicable",
        reason=(
            "Indicador general con respuesta evaluable; "
            "la calidad de la conducta no altera su aplicabilidad."
        ),
    )


def cp3_applicability(
    state: CP3SemanticState,
) -> CPApplicabilityDecision:
    """CP3: problema con complejidad que exige organización.

    Decisión metodológica aprobada:
    puede activarse por complejidad estructural o por una situación
    emocional suficientemente seria que realmente requiera organización.

    La mera presencia de malestar emocional no activa CP3.
    """

    required = (
        state.structural_complexity_requires_organization
        or state.serious_emotional_complexity_requires_organization
    )

    if not required:
        return CPApplicabilityDecision(
            code="CP3",
            state="not_applicable",
            reason=(
                "No se verificó complejidad que exija organizar el "
                "problema en componentes, relaciones o etapas."
            ),
        )

    return CPApplicabilityDecision(
        code="CP3",
        state="applicable",
        reason=(
            "Se verificó complejidad que exige organización."
        ),
    )


def cp6_applicability(
    state: CP6SemanticState,
) -> CPApplicabilityDecision:
    """Aplicabilidad CP6 conforme al contrato oficial."""

    # DOCX CP6: necessity activates the gate; use alone does not.
    applicable = state.example_or_analogy_needed

    if not applicable:
        return CPApplicabilityDecision(
            code="CP6",
            state="not_applicable",
            reason=(
                "No se necesitaba ejemplo o analogia, "
                "independientemente de que la IA utilizara uno."
            ),
        )

    return CPApplicabilityDecision(
        code="CP6",
        state="applicable",
        reason=(
            "El ejemplo o analogia era necesario para comprender "
            "un concepto pertinente."
        ),
    )



def cp8_applicability(
    state: CP8SemanticState,
) -> CPApplicabilityDecision:
    """CP8: explicación suficientemente compleja para verificar comprensión.

    La longitud por sí sola NO determina complejidad.
    Esta función no calcula complejidad desde texto: recibe el hecho
    semántico previamente establecido.
    """

    if not state.explanation_complex_enough_for_verification:
        return CPApplicabilityDecision(
            code="CP8",
            state="not_applicable",
            reason=(
                "No se verificó una explicación con carga conceptual "
                "o relacional suficiente para ameritar comprobación."
            ),
        )

    return CPApplicabilityDecision(
        code="CP8",
        state="applicable",
        reason=(
            "La explicación es suficientemente compleja para "
            "ameritar verificación de comprensión."
        ),
    )
