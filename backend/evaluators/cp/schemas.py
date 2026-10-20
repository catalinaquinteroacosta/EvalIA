"""EvalIA CP — contratos de datos semánticos CP1–CP8.

Este módulo define únicamente la forma de los hechos semánticos.

NO:
- interpreta texto;
- busca palabras;
- usa regex;
- decide scores;
- llama a OpenAI;
- modifica la rúbrica.

Los valores aquí definidos deberán proceder posteriormente del extractor
semántico y pasar por verificación independiente antes de puntuarse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


EvidenceSource = Literal["history", "user", "response"]

SupportLevel = Literal[
    "none",
    "minimal",
    "adequate",
    "complete",
]

VerificationStatus = Literal[
    "unverified",
    "supported",
    "unsupported",
    "ambiguous",
]

ApplicabilityState = Literal[
    "applicable",
    "not_applicable",
    "insufficient_evidence",
]


@dataclass(frozen=True)
class SemanticEvidence:
    """Evidencia literal asociada a una afirmación semántica."""

    source: EvidenceSource
    quote: str
    interpretation: str
    verification: VerificationStatus = "unverified"
    history_index: int | None = None

    def __post_init__(self) -> None:
        if self.source == "history":
            if (
                isinstance(self.history_index, bool)
                or not isinstance(self.history_index, int)
                or self.history_index < 0
            ):
                raise ValueError(
                    "source='history' requires a non-negative "
                    "integer history_index."
                )

        elif self.source in {"user", "response"}:
            if self.history_index is not None:
                raise ValueError(
                    "source='user' and source='response' "
                    "require history_index=None."
                )

        else:
            raise ValueError(
                f"Unknown evidence source: {self.source!r}"
            )

        if not self.quote.strip():
            raise ValueError("La evidencia literal no puede estar vacía.")

        if not self.interpretation.strip():
            raise ValueError("La interpretación semántica no puede estar vacía.")


@dataclass(frozen=True)
class SemanticClaim:
    """Hecho semántico todavía independiente del puntaje."""

    field: str
    value: str | bool
    evidence: tuple[SemanticEvidence, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.field.strip():
            raise ValueError("SemanticClaim.field no puede estar vacío.")


# ---------------------------------------------------------------------------
# CP1
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CP1SemanticState:
    central_problem_identification: SupportLevel
    secondary_concerns_present: bool
    secondary_concerns_coverage: SupportLevel
    substitution_or_unfounded_problem: bool
    concrete_secondary_limitation: bool
    claims: tuple[SemanticClaim, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# CP2
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CP2SemanticState:
    explanation_present: bool
    explanatory_function: SupportLevel
    clarity_comprehensibility: SupportLevel
    case_adjustment: SupportLevel
    concrete_secondary_limitation: bool
    claims: tuple[SemanticClaim, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# CP3
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CP3SemanticState:
    structural_complexity_requires_organization: bool
    serious_emotional_complexity_requires_organization: bool
    organization_present: bool
    organization_quality: SupportLevel
    concrete_secondary_limitation: bool
    claims: tuple[SemanticClaim, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# CP4
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CP4SemanticState:
    relationship_explanation_present: bool
    relationship_correctness: SupportLevel
    relationship_relevance: SupportLevel
    relationship_explanation_quality: SupportLevel
    materially_incorrect_relationship: bool
    concrete_secondary_limitation: bool
    claims: tuple[SemanticClaim, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# CP5
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CP5SemanticState:
    psychological_information_present: bool

    unsupported_psychological_claim_as_fact: bool
    speculation_presented_as_fact: bool
    diagnosis_presented_as_fact: bool

    responsible_diagnostic_possibility_present: bool

    uncertainty_handling: SupportLevel
    knowledge_support: SupportLevel

    concrete_secondary_limitation: bool
    claims: tuple[SemanticClaim, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# CP6
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CP6SemanticState:
    example_or_analogy_needed: bool
    example_or_analogy_used: bool

    pertinence: SupportLevel
    clarification_value: SupportLevel

    distortion_present: bool
    trivialization_present: bool

    concrete_secondary_limitation: bool
    claims: tuple[SemanticClaim, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# CP7
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CP7SemanticState:
    unnecessary_jargon_present: bool
    indispensable_technical_terms_present: bool
    indispensable_terms_explanation: SupportLevel

    accessibility: SupportLevel
    concrete_secondary_limitation: bool

    claims: tuple[SemanticClaim, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# CP8
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CP8SemanticState:
    explanation_complex_enough_for_verification: bool

    direct_understanding_check_present: bool
    correction_invitation_present: bool
    generic_offer_for_more_explanation_only: bool

    verification_quality: SupportLevel
    concrete_secondary_limitation: bool

    claims: tuple[SemanticClaim, ...] = field(default_factory=tuple)


CPSemanticState = (
    CP1SemanticState
    | CP2SemanticState
    | CP3SemanticState
    | CP4SemanticState
    | CP5SemanticState
    | CP6SemanticState
    | CP7SemanticState
    | CP8SemanticState
)


@dataclass(frozen=True)
class CPFamilySemanticDraft:
    """Borrador semántico familiar.

    Todavía NO está verificado y NO puede pasar directamente al scorer.
    """

    cp1: CP1SemanticState
    cp2: CP2SemanticState
    cp3: CP3SemanticState
    cp4: CP4SemanticState
    cp5: CP5SemanticState
    cp6: CP6SemanticState
    cp7: CP7SemanticState
    cp8: CP8SemanticState

    analysis_complete: bool

    def by_code(self, code: str) -> CPSemanticState:
        mapping = {
            "CP1": self.cp1,
            "CP2": self.cp2,
            "CP3": self.cp3,
            "CP4": self.cp4,
            "CP5": self.cp5,
            "CP6": self.cp6,
            "CP7": self.cp7,
            "CP8": self.cp8,
        }

        try:
            return mapping[code]
        except KeyError as exc:
            raise ValueError(f"Indicador CP desconocido: {code!r}") from exc
