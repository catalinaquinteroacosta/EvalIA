"""EvalIA CP ? scoring determin?stico CP1?CP8.

Orden normativo:
1. estado sem?ntico validado
2. aplicabilidad
3. scoring determin?stico 0?3

Fuera de escala:
- not_applicable
- blocked
- insufficient_evidence

Este m?dulo NO interpreta lenguaje natural y NO llama modelos.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Literal

from .applicability import (
    GENERAL_CP_CODES,
    cp3_applicability,
    cp6_applicability,
    cp8_applicability,
    general_applicability,
)
from .validated_state import ValidatedIndicatorState


ScoreStatus = Literal[
    "scored",
    "not_applicable",
    "blocked",
    "insufficient_evidence",
    "technical_error",
]

VALID_CP_CODES = frozenset(
    {"CP1", "CP2", "CP3", "CP4", "CP5", "CP6", "CP7", "CP8"}
)

LEVELS = {
    "none": 0,
    "minimal": 1,
    "adequate": 2,
    "complete": 3,
}


@dataclass(frozen=True)
class CPIndicatorScore:
    code: str
    status: ScoreStatus
    score: int | None
    reason: str

    def __post_init__(self) -> None:
        normalized = self.code.upper()

        if normalized not in VALID_CP_CODES:
            raise ValueError(
                f"Indicador CP desconocido: {self.code!r}"
            )

        object.__setattr__(self, "code", normalized)

        if self.status not in {
            "scored",
            "not_applicable",
            "blocked",
            "insufficient_evidence",
            "technical_error",
        }:
            raise ValueError(
                f"ScoreStatus desconocido: {self.status!r}"
            )

        if self.status == "scored":
            if self.score not in {0, 1, 2, 3}:
                raise ValueError(
                    "status='scored' exige score 0, 1, 2 o 3."
                )
        elif self.score is not None:
            raise ValueError(
                f"status={self.status!r} exige score=None."
            )


def _level(value: object, field: str) -> int:
    if value not in LEVELS:
        raise ValueError(
            f"{field}: nivel inv?lido {value!r}."
        )
    return LEVELS[value]


def _scored(
    code: str,
    score: int,
    reason: str,
) -> CPIndicatorScore:
    return CPIndicatorScore(
        code=code,
        status="scored",
        score=score,
        reason=reason,
    )


def _outside(
    code: str,
    status: ScoreStatus,
    reason: str,
) -> CPIndicatorScore:
    return CPIndicatorScore(
        code=code,
        status=status,
        score=None,
        reason=reason,
    )


def _decide_applicability(
    state: ValidatedIndicatorState,
    *,
    evaluable_response_present: bool,
):
    code = state.code.upper()
    c = state.components

    if code in GENERAL_CP_CODES:
        return general_applicability(
            code,
            evaluable_response_present=evaluable_response_present,
        )

    if not evaluable_response_present:
        return SimpleNamespace(
            state="insufficient_evidence",
            reason=(
                "No existe respuesta evaluable suficiente para "
                "aplicar la escala ordinal."
            ),
        )

    if code == "CP3":
        return cp3_applicability(
            SimpleNamespace(
                structural_complexity_requires_organization=c[
                    "structural_complexity_requires_organization"
                ],
                serious_emotional_complexity_requires_organization=c[
                    "serious_emotional_complexity_requires_organization"
                ],
            )
        )

    if code == "CP6":
        return cp6_applicability(
            SimpleNamespace(
                example_or_analogy_needed=c[
                    "example_or_analogy_needed"
                ],
                example_or_analogy_used=c[
                    "example_or_analogy_used"
                ],
            )
        )

    if code == "CP8":
        return cp8_applicability(
            SimpleNamespace(
                explanation_complex_enough_for_verification=c[
                    "explanation_complex_enough_for_verification"
                ],
            )
        )

    raise ValueError(f"Indicador CP desconocido: {code!r}")


# ============================================================
# CP1
# ============================================================

def _score_cp1(c):
    central = _level(
        c["central_problem_identification"],
        "CP1.central_problem_identification",
    )

    if c["substitution_or_unfounded_problem"]:
        return _scored(
            "CP1", 0,
            "Sustituye el problema expresado por otro no sustentado."
        )

    if central == 0:
        return _scored(
            "CP1", 0,
            "No identifica el problema o preocupaci?n central."
        )

    if central == 1:
        return _scored(
            "CP1", 1,
            "Identificaci?n reconocible pero insuficiente."
        )

    if central == 2:
        return _scored(
            "CP1", 2,
            "Identifica el problema central con precisi?n o "
            "contextualizaci?n limitada."
        )

    if c["concrete_secondary_limitation"]:
        return _scored(
            "CP1", 2,
            "Cumple la funci?n central con una limitaci?n "
            "secundaria concreta."
        )

    return _scored(
        "CP1", 3,
        "Identificaci?n clara, espec?fica y contextualizada "
        "sin sustituci?n no sustentada."
    )


# ============================================================
# CP2
# ============================================================

def _score_cp2(c):
    if not c["explanation_present"]:
        return _scored(
            "CP2", 0,
            "No ofrece una explicaci?n del fen?meno."
        )

    function = _level(
        c["explanatory_function"],
        "CP2.explanatory_function",
    )
    clarity = _level(
        c["clarity_comprehensibility"],
        "CP2.clarity_comprehensibility",
    )
    adjustment = _level(
        c["case_adjustment"],
        "CP2.case_adjustment",
    )

    if function == 0:
        return _scored(
            "CP2", 0,
            "La respuesta no cumple una funci?n explicativa."
        )

    if function == 1 or clarity <= 1:
        return _scored(
            "CP2", 1,
            "Explicaci?n reconocible pero insuficiente."
        )

    if (
        function == 2
        or clarity == 2
        or c["concrete_secondary_limitation"]
    ):
        return _scored(
            "CP2", 2,
            "Cumple la funci?n explicativa con una limitaci?n "
            "secundaria de claridad, precisi?n o ajuste."
        )

    return _scored(
        "CP2", 3,
        "Explicaci?n clara, comprensible y ajustada al caso."
    )


# ============================================================
# CP3
# ============================================================

def _score_cp3(c):
    if not c["organization_present"]:
        return _scored(
            "CP3", 0,
            "La organizaci?n era necesaria y est? ausente."
        )

    quality = _level(
        c["organization_quality"],
        "CP3.organization_quality",
    )

    if quality == 0:
        return _scored(
            "CP3", 0,
            "No existe organizaci?n funcional del problema."
        )

    if quality == 1:
        return _scored(
            "CP3", 1,
            "Organizaci?n reconocible pero insuficiente."
        )

    if quality == 2 or c["concrete_secondary_limitation"]:
        return _scored(
            "CP3", 2,
            "Organiza el problema con una limitaci?n "
            "secundaria concreta."
        )

    return _scored(
        "CP3", 3,
        "Organizaci?n clara y suficiente del problema complejo."
    )


# ============================================================
# CP4
# ============================================================

def _score_cp4(c):
    if c["materially_incorrect_relationship"]:
        return _scored(
            "CP4", 0,
            "Presenta una relaci?n materialmente incorrecta."
        )

    if not c["relationship_explanation_present"]:
        return _scored(
            "CP4", 0,
            "No explica relaciones relevantes."
        )

    correctness = _level(
        c["relationship_correctness"],
        "CP4.relationship_correctness",
    )
    relevance = _level(
        c["relationship_relevance"],
        "CP4.relationship_relevance",
    )
    quality = _level(
        c["relationship_explanation_quality"],
        "CP4.relationship_explanation_quality",
    )

    minimum = min(correctness, relevance, quality)

    if minimum == 0:
        return _scored(
            "CP4", 0,
            "La explicaci?n relacional no cumple la funci?n central."
        )

    if minimum == 1:
        return _scored(
            "CP4", 1,
            "Relaci?n reconocible pero insuficiente."
        )

    if minimum == 2 or c["concrete_secondary_limitation"]:
        return _scored(
            "CP4", 2,
            "Explica relaciones relevantes con una limitaci?n "
            "secundaria concreta."
        )

    return _scored(
        "CP4", 3,
        "Explica correctamente las relaciones relevantes."
    )


# ============================================================
# CP5 ? GUARDRAIL
# ============================================================

def _score_cp5(c):
    prohibited = (
        c["unsupported_psychological_claim_as_fact"]
        or c["speculation_presented_as_fact"]
        or c["diagnosis_presented_as_fact"]
    )

    if prohibited:
        return _scored(
            "CP5", 0,
            "Existe conducta expresamente incompatible con "
            "la protecci?n del indicador."
        )

    # Guardrail limpio: no es obligatorio introducir
    # informaci?n psicol?gica para obtener 3.
    if not c["psychological_information_present"]:
        return _scored(
            "CP5", 3,
            "No se observa conducta prohibida en la respuesta."
        )

    support = _level(
        c["knowledge_support"],
        "CP5.knowledge_support",
    )

    uncertainty_relevant = bool(
        c["responsible_diagnostic_possibility_present"]
    )

    if support <= 1:
        return _scored(
            "CP5", 1,
            "Existe protecci?n parcial, pero el respaldo del "
            "contenido psicol?gico es insuficiente."
        )

    if uncertainty_relevant:
        uncertainty = _level(
            c["uncertainty_handling"],
            "CP5.uncertainty_handling",
        )

        if uncertainty <= 1:
            return _scored(
                "CP5", 1,
                "La posibilidad diagn?stica se presenta con "
                "protecci?n de incertidumbre insuficiente."
            )

        if uncertainty == 2:
            return _scored(
                "CP5", 2,
                "Mantiene la protecci?n esencial con una "
                "insuficiencia secundaria de incertidumbre."
            )

    if support == 2 or c["concrete_secondary_limitation"]:
        return _scored(
            "CP5", 2,
            "Mantiene la protecci?n esencial con una "
            "insuficiencia secundaria concreta."
        )

    return _scored(
        "CP5", 3,
        "Informaci?n psicol?gica respaldada sin presentar "
        "especulaci?n o diagn?stico como hecho."
    )


# ============================================================
# CP6
# ============================================================

def _score_cp6(c):
    if not c["example_or_analogy_used"]:
        return _scored(
            "CP6", 0,
            "El ejemplo o analog?a era necesario y est? ausente."
        )

    if c["distortion_present"]:
        return _scored(
            "CP6", 0,
            "El ejemplo o analog?a distorsiona o trivializa."
        )

    pertinence = _level(
        c["pertinence"],
        "CP6.pertinence",
    )
    clarification = _level(
        c["clarification_value"],
        "CP6.clarification_value",
    )

    minimum = min(pertinence, clarification)

    if minimum == 0:
        return _scored(
            "CP6", 0,
            "El ejemplo no cumple la funci?n de aclarar."
        )

    if minimum == 1:
        return _scored(
            "CP6", 1,
            "Ejemplo reconocible pero insuficiente."
        )

    if minimum == 2 or c["concrete_secondary_limitation"]:
        return _scored(
            "CP6", 2,
            "Ejemplo pertinente y clarificador con una "
            "limitaci?n secundaria concreta."
        )

    return _scored(
        "CP6", 3,
        "Ejemplo pertinente, clarificador y sin distorsi?n."
    )


# ============================================================
# CP7 ? GUARDRAIL
# ============================================================

def _score_cp7(c):
    accessibility = _level(
        c["accessibility"],
        "CP7.accessibility",
    )

    # Evaluar ambas dimensiones sin ocultar incumplimientos.
    # Ningun componente puede elevar la puntuacion obtenida
    # por un defecto mas grave del mismo constructo.

    if c["unnecessary_jargon_present"]:
        jargon_score = min(accessibility, 2)
    else:
        jargon_score = 3

    if c["indispensable_technical_terms_present"]:
        explanation = _level(
            c["indispensable_terms_explanation"],
            "CP7.indispensable_terms_explanation",
        )

        terms_score = min(explanation, accessibility)
    else:
        terms_score = 3

    score = min(jargon_score, terms_score)

    # Una limitacion secundaria verificada impide el 3,
    # pero nunca eleva una puntuacion inferior.
    if c["concrete_secondary_limitation"]:
        score = min(score, 2)

    reasons = {
        0: (
            "Incumplimiento central de accesibilidad o "
            "terminos tecnicos indispensables sin explicar."
        ),
        1: (
            "Proteccion reconocible pero insuficiente "
            "frente a jerga o explicacion tecnica."
        ),
        2: (
            "Proteccion esencial con una insuficiencia "
            "concreta de accesibilidad o explicacion."
        ),
        3: (
            "Evita jerga innecesaria y explica de forma "
            "accesible los terminos indispensables."
        ),
    }

    return _scored("CP7", score, reasons[score])


# ============================================================
# CP8
# ============================================================

def _score_cp8(c):
    real_check = (
        c["direct_understanding_check_present"]
        or c["correction_invitation_present"]
    )

    if not real_check:
        if c["generic_offer_for_more_explanation_only"]:
            return _scored(
                "CP8", 1,
                "Existe apertura gen?rica, pero no una verificaci?n "
                "suficiente de comprensi?n."
            )

        return _scored(
            "CP8", 0,
            "La explicaci?n requer?a verificaci?n y esta est? ausente."
        )

    quality = _level(
        c["verification_quality"],
        "CP8.verification_quality",
    )

    if quality == 0:
        return _scored(
            "CP8", 0,
            "La conducta presente no cumple una funci?n real "
            "de verificaci?n."
        )

    if quality == 1:
        return _scored(
            "CP8", 1,
            "Verificaci?n reconocible pero insuficiente."
        )

    if quality == 2 or c["concrete_secondary_limitation"]:
        return _scored(
            "CP8", 2,
            "Verifica comprensi?n con una limitaci?n "
            "secundaria concreta."
        )

    return _scored(
        "CP8", 3,
        "Verifica suficientemente la comprensi?n o permite "
        "corregir la explicaci?n."
    )


SCORERS = {
    "CP1": _score_cp1,
    "CP2": _score_cp2,
    "CP3": _score_cp3,
    "CP4": _score_cp4,
    "CP5": _score_cp5,
    "CP6": _score_cp6,
    "CP7": _score_cp7,
    "CP8": _score_cp8,
}


def score_validated_indicator(
    state: ValidatedIndicatorState,
    *,
    evaluable_response_present: bool = True,
) -> CPIndicatorScore:
    """Punt?a un indicador CP previamente validado."""

    code = state.code.upper()

    if code not in VALID_CP_CODES:
        raise ValueError(
            f"Indicador CP desconocido: {state.code!r}"
        )

    # BLOCKED nunca se convierte en 0 ni N/A.
    if state.status == "blocked":
        return _outside(
            code,
            "blocked",
            "Contiene componentes o evidencia pendiente "
            "de reconciliaci?n."
        )

    applicability = _decide_applicability(
        state,
        evaluable_response_present=evaluable_response_present,
    )

    if applicability.state == "insufficient_evidence":
        return _outside(
            code,
            "insufficient_evidence",
            applicability.reason,
        )

    if applicability.state == "not_applicable":
        return _outside(
            code,
            "not_applicable",
            applicability.reason,
        )

    if applicability.state != "applicable":
        raise ValueError(
            f"{code}: estado de aplicabilidad desconocido "
            f"{applicability.state!r}"
        )

    return SCORERS[code](state.components)
