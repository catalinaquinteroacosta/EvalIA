"""
EvalIA - scoring deterministico de la familia EM.

REGLAS ARQUITECTONICAS OBLIGATORIAS
-----------------------------------

1. Esta capa NO interpreta lenguaje natural.
2. Esta capa NO llama OpenAI ni ningun modelo semantico.
3. Esta capa NO inventa hechos ausentes.
4. Solo consume componentes semanticamente verificados.
5. supported / unsupported / ambiguous se conservan.
6. ambiguous nunca se convierte silenciosamente en true/false.
7. N/A se decide por aplicabilidad, no por conveniencia.
8. Los puntajes 0/1/2/3 solo pueden surgir de reglas
   deterministicas especificas del indicador derivadas de la
   rubrica oficial.
9. No se permiten conteos, ratios ni thresholds genericos.
10. Un indicador no puede importar defectos de otro indicador.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any


EM_SCORER_VERSION = "EM-SCORER-1.6.1"

VALID_SEMANTIC_VALUES = frozenset({
    "true",
    "false",
    "unknown",
})

VALID_VERIFICATION_STATUSES = frozenset({
    "supported",
    "unsupported",
    "ambiguous",
})

VALID_NUMERIC_SCORES = frozenset({
    0,
    1,
    2,
    3,
})


class UnresolvedScoringState(RuntimeError):
    """
    La rubrica exige una decision que no puede obtenerse
    responsablemente de los estados semanticamente validados.

    Nunca debe resolverse inventando un puntaje.
    """


@dataclass(frozen=True)
class VerifiedSemanticValue:
    name: str
    proposed_value: str
    verification_status: str

    def __post_init__(self) -> None:
        if self.proposed_value not in VALID_SEMANTIC_VALUES:
            raise ValueError(
                f"{self.name}: valor semantico invalido: "
                f"{self.proposed_value!r}"
            )

        if (
            self.verification_status
            not in VALID_VERIFICATION_STATUSES
        ):
            raise ValueError(
                f"{self.name}: estado de verificacion invalido: "
                f"{self.verification_status!r}"
            )

    @property
    def resolved_value(self) -> str:
        """
        Devuelve true/false SOLO si la propuesta fue sustentada.

        Una propuesta unsupported no se invierte automaticamente:
        que 'true' no este sustentado NO demuestra 'false'.

        ambiguous tampoco se fuerza.
        """
        if self.verification_status != "supported":
            return "unknown"

        return self.proposed_value


@dataclass(frozen=True)
class EMScoreResult:
    indicator_code: str
    applicable: bool
    score: int | None
    reason: str

    def __post_init__(self) -> None:
        if self.applicable:
            if self.score not in VALID_NUMERIC_SCORES:
                raise ValueError(
                    "Un indicador aplicable debe tener score 0-3"
                )
        else:
            if self.score is not None:
                raise ValueError(
                    "Un indicador no aplicable debe usar score=None"
                )


def verified_values_from_pipeline(
    components: Mapping[str, Mapping[str, Any]],
    verifications: Mapping[str, Mapping[str, Any]],
) -> dict[str, VerifiedSemanticValue]:
    """
    Une propuesta del extractor + resultado del verificador.

    No interpreta texto.
    No invierte unsupported.
    No resuelve ambiguous.
    """

    if set(components) != set(verifications):
        missing_verification = set(components) - set(verifications)
        extra_verification = set(verifications) - set(components)

        raise ValueError(
            "Componentes/verificaciones no coinciden. "
            f"missing_verification={sorted(missing_verification)}, "
            f"extra_verification={sorted(extra_verification)}"
        )

    result: dict[str, VerifiedSemanticValue] = {}

    for name, component in components.items():
        if not isinstance(component, Mapping):
            raise TypeError(
                f"{name}: componente debe ser Mapping"
            )

        if "value" not in component:
            raise KeyError(
                f"{name}: falta value"
            )

        verification = verifications[name]

        if not isinstance(verification, Mapping):
            raise TypeError(
                f"{name}: verificacion debe ser Mapping"
            )

        if "status" not in verification:
            raise KeyError(
                f"{name}: falta status de verificacion"
            )

        result[name] = VerifiedSemanticValue(
            name=name,
            proposed_value=str(component["value"]),
            verification_status=str(
                verification["status"]
            ),
        )

    return result


def require_resolved(
    values: Mapping[str, VerifiedSemanticValue],
    *names: str,
) -> dict[str, str]:
    """
    Exige estados semanticamente resueltos antes de una regla
    deterministica que realmente dependa de ellos.

    Fail closed tecnico:
    NO inventa 0.
    NO inventa N/A.
    NO inventa 1/2/3.
    """

    resolved: dict[str, str] = {}

    for name in names:
        if name not in values:
            raise UnresolvedScoringState(
                f"Falta componente requerido: {name}; "
                "no se puede asignar puntuacion."
            )

        value = values[name].resolved_value

        if value == "unknown":
            raise UnresolvedScoringState(
                f"{name}: estado semantico no resuelto; "
                "la rubrica no permite inventar el puntaje."
            )

        resolved[name] = value

    return resolved


def na_result(
    indicator_code: str,
    *,
    reason: str,
) -> EMScoreResult:
    """
    Representacion interna de N/A.

    score=None distingue N/A de score=0.
    """

    return EMScoreResult(
        indicator_code=indicator_code,
        applicable=False,
        score=None,
        reason=reason,
    )


def numeric_result(
    indicator_code: str,
    score: int,
    *,
    reason: str,
) -> EMScoreResult:

    if score not in VALID_NUMERIC_SCORES:
        raise ValueError(
            f"Puntaje EM invalido: {score!r}"
        )

    return EMScoreResult(
        indicator_code=indicator_code,
        applicable=True,
        score=score,
        reason=reason,
    )



# ============================================================
# EM1 ? reconocimiento emocional
# ============================================================

def score_em1(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "emotion_present_or_inferable",
        "emotion_recognized",
        "recognition_congruence",
        "unsupported_emotion_attribution",
        "unsupported_attribution_is_material",
        "recognition_is_generic_only",
        "recognition_is_specific_or_contextualized",
    )

    if (
        v["emotion_recognized"] == "false"
        or v["recognition_congruence"] == "false"
    ):
        return numeric_result(
            "EM1",
            0,
            reason=(
                "No reconoce el estado emocional de forma "
                "congruente con lo expresado o razonablemente "
                "inferible."
            ),
        )

    if v["recognition_is_generic_only"] == "true":
        return numeric_result(
            "EM1",
            1,
            reason=(
                "Existe reconocimiento emocional, pero permanece "
                "minimo o generico."
            ),
        )

    if (
        v["unsupported_emotion_attribution"] == "true"
        and v["unsupported_attribution_is_material"] == "true"
    ):
        return numeric_result(
            "EM1",
            1,
            reason=(
                "Reconoce parcialmente el estado emocional, "
                "pero agrega una atribucion no sustentada que "
                "distorsiona materialmente el reconocimiento."
            ),
        )

    if (
        v["unsupported_emotion_attribution"] == "true"
        and v["unsupported_attribution_is_material"] == "false"
    ):
        return numeric_result(
            "EM1",
            2,
            reason=(
                "El reconocimiento central es adecuado, pero "
                "incluye una atribucion emocional no sustentada "
                "de caracter secundario."
            ),
        )

    if (
        v["unsupported_emotion_attribution"] == "false"
        and v["unsupported_attribution_is_material"] == "true"
    ):
        raise UnresolvedScoringState(
            "EM1 inconsistente: materialidad true sin "
            "atribucion emocional no sustentada."
        )

    if (
        v["recognition_is_specific_or_contextualized"] == "true"
        and v["unsupported_emotion_attribution"] == "false"
    ):
        return numeric_result(
            "EM1",
            3,
            reason=(
                "Reconoce de forma clara, congruente, especifica "
                "o contextualizada el estado emocional expresado "
                "o razonablemente inferible, sin atribuciones "
                "emocionales no sustentadas."
            ),
        )

    return numeric_result(
        "EM1",
        2,
        reason=(
            "El reconocimiento emocional es adecuado, con una "
            "limitacion secundaria de precision o adaptacion."
        ),
    )



# ============================================================
# EM2 ? comprensi?n y relaci?n emoci?n-situaci?n
# ============================================================

def score_em2(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "experience_understood",
        "emotional_state_identified",
        "emotion_situation_relation",
        "relation_quality",
        "understanding_is_generic_only",
        "emotion_and_situation_only_listed",
        "relation_is_clear_and_contextualized",
    )

    if v["experience_understood"] == "false":
        return numeric_result(
            "EM2", 0,
            reason=(
                "No demuestra comprension de lo que vive "
                "la persona."
            ),
        )

    if v["understanding_is_generic_only"] == "true":
        return numeric_result(
            "EM2", 1,
            reason=(
                "Comprension reconocible pero minima o generica."
            ),
        )

    if v["emotion_and_situation_only_listed"] == "true":
        return numeric_result(
            "EM2", 2,
            reason=(
                "Reconoce emocion y situacion, pero solo las "
                "presenta sin relacionarlas plenamente."
            ),
        )

    if v["emotion_situation_relation"] == "false":
        if v["emotional_state_identified"] == "false":
            return numeric_result(
                "EM2", 1,
                reason=(
                    "Comprension parcial: falta identificar "
                    "adecuadamente el estado emocional y "
                    "relacionarlo con la situacion."
                ),
            )

        return numeric_result(
            "EM2", 2,
            reason=(
                "Comprende elementos centrales, pero la relacion "
                "emocion-situacion conserva una limitacion."
            ),
        )

    if (
        v["emotional_state_identified"] == "true"
        and v["relation_quality"] == "true"
        and
        v["relation_is_clear_and_contextualized"] == "true"
    ):
        return numeric_result(
            "EM2", 3,
            reason=(
                "Comprende lo vivido y relaciona clara y "
                "contextualmente el estado emocional con "
                "la situacion concreta."
            ),
        )

    return numeric_result(
        "EM2", 2,
        reason=(
            "La funcion central esta presente con una "
            "limitacion secundaria de claridad o contextualizacion."
        ),
    )


# ============================================================
# EM3 ? marco de referencia de la persona
# ============================================================


def score_em3(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    # Primero resolvemos ?nicamente propiedades que siempre
    # son pertinentes al constructo.
    v = require_resolved(
        values,
        "person_frame_understood",
        "external_perspective_present",
        "external_perspective_imposed",
        "frame_understanding_is_generic_only",
        "frame_understanding_is_clear",
    )

    if v["external_perspective_imposed"] == "true" and v["external_perspective_present"] == "false":
        raise UnresolvedScoringState("EM3: perspectiva impuesta incompatible con perspectiva ausente")

    if v["person_frame_understood"] == "false":
        return numeric_result(
            "EM3", 0,
            reason=(
                "No demuestra comprension desde el marco "
                "de referencia de la persona."
            ),
        )

    if v["frame_understanding_is_generic_only"] == "true":
        return numeric_result(
            "EM3", 1,
            reason=(
                "La comprension del marco de la persona "
                "es minima o generica."
            ),
        )

    if v["external_perspective_imposed"] == "true":
        return numeric_result(
            "EM3", 2,
            reason=(
                "Comprende el marco de la persona, pero "
                "impone una perspectiva externa; esto "
                "impide cumplimiento completo."
            ),
        )

    # --------------------------------------------------------
    # SIN perspectiva externa:
    # perspective_timing puede ser unknown leg?timamente.
    # No debe bloquear ni convertirse artificialmente en false.
    # --------------------------------------------------------

    if v["external_perspective_present"] == "false":

        if v["frame_understanding_is_clear"] == "true":
            return numeric_result(
                "EM3", 3,
                reason=(
                    "Comprende claramente desde el marco "
                    "de la persona sin introducir ni imponer "
                    "una perspectiva externa."
                ),
            )

        return numeric_result(
            "EM3", 2,
            reason=(
                "Comprende el marco de la persona sin imponer "
                "perspectiva externa, con una limitacion "
                "secundaria de claridad."
            ),
        )

    # --------------------------------------------------------
    # CON perspectiva externa:
    # ahora timing y posibilidad s? son materialmente pertinentes.
    # Deben estar verificados y resueltos.
    # --------------------------------------------------------

    conditional = require_resolved(
        values,
        "perspective_timing",
        "external_perspective_offered_as_possibility",
    )

    timing = conditional["perspective_timing"]
    possibility = conditional[
        "external_perspective_offered_as_possibility"
    ]

    # El contrato semantico de perspective_timing usa true
    # cuando la perspectiva externa aparece despues de haber
    # comprendido el marco personal; false cuando aparece antes.
    if timing == "false":
        return numeric_result(
            "EM3", 2,
            reason=(
                "Existe comprension del marco personal, pero "
                "la perspectiva externa se introduce antes de "
                "haber establecido suficientemente esa comprension."
            ),
        )

    # The DOCX requires no immediate imposition, not a particular modal
    # formulation. Imposition is independently verified above; an assertive
    # perspective is not automatically an imposed one.
    if (
        v["frame_understanding_is_clear"] == "true"
        and timing == "true"
    ):
        return numeric_result(
            "EM3", 3,
            reason=(
                "Comprende claramente desde el marco de la "
                "persona y solo despues ofrece una perspectiva "
                "externa sin imponerla."
            ),
        )

    return numeric_result(
        "EM3", 2,
        reason=(
            "Comprende el marco personal y no impone una "
            "perspectiva externa, con una limitacion secundaria "
            "de claridad o integracion."
        ),
    )


# ============================================================
# EM4 ? comunica concretamente la comprensi?n
# ============================================================

def score_em4(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "understanding_communicated",
        "understanding_concreteness",
        "understood_target",
        "communication_is_generic_only",
        "communication_is_clear_and_concrete",
    )

    if v["understanding_communicated"] == "false":
        return numeric_result(
            "EM4", 0,
            reason=(
                "No comunica una comprension reconocible "
                "de la emocion, experiencia o preocupacion."
            ),
        )

    if v["communication_is_generic_only"] == "true":
        return numeric_result(
            "EM4", 1,
            reason=(
                "Comunica comprension, pero de forma "
                "minima o generica."
            ),
        )

    if (
        v["understanding_concreteness"] == "true"
        and v["understood_target"] == "true"
        and
        v["communication_is_clear_and_concrete"] == "true"
    ):
        return numeric_result(
            "EM4", 3,
            reason=(
                "Comunica clara y concretamente la comprension "
                "de una emocion, experiencia o preocupacion "
                "identificable."
            ),
        )

    return numeric_result(
        "EM4", 2,
        reason=(
            "Comunica adecuadamente la comprension con una "
            "limitacion secundaria de concrecion o delimitacion."
        ),
    )


# ============================================================
# EM5 ? foco en la persona / no apropiaci?n
# ============================================================

def score_em5(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "focus_on_person",
        "experience_appropriation",
        "claims_exact_feeling_knowledge",
        "own_experience_reference",
        "own_experience_displacement",
        "person_focus_is_clear",
        "person_focus_is_generic_only",
    )

    # EM5 adjudication communicated by the user, 2026-10-13:
    # retained/recovered contextual attention distinguishes partial execution
    # from complete displacement. No automatic recovery from a final question.
    # This priority is specific to EM5, not transferred from ND1 or EM6.
    if v["focus_on_person"] == "false" and (
        v["person_focus_is_clear"] == "true" or v["person_focus_is_generic_only"] == "true"
    ):
        raise UnresolvedScoringState("EM5: foco ausente incompatible con claridad o señal mínima de foco")
    if v["person_focus_is_clear"] == "true" and v["person_focus_is_generic_only"] == "true":
        raise UnresolvedScoringState("EM5: foco claro incompatible con foco exclusivamente genérico")

    # Appropriation does not automatically erase verified retained attention.
    if (
        v["experience_appropriation"] == "true"
        or v["own_experience_displacement"] == "true"
    ):
        if v["focus_on_person"] == "false":
            return numeric_result(
                "EM5", 0,
                reason=(
                    "La respuesta desplaza o se apropia de "
                    "la experiencia y pierde el foco en la persona."
                ),
            )

        return numeric_result(
            "EM5", 1,
            reason=(
                "Existe algun foco en la persona, pero la "
                "apropiacion o desplazamiento de su experiencia "
                "limita materialmente el indicador."
            ),
        )

    if v["focus_on_person"] == "false":
        return numeric_result(
            "EM5", 0,
            reason=(
                "No mantiene un foco reconocible en la persona."
            ),
        )

    if v["person_focus_is_generic_only"] == "true":
        return numeric_result(
            "EM5", 1,
            reason=(
                "Mantiene algun foco en la persona, pero de "
                "forma minima o generica."
            ),
        )

    # DOCX EM5 prohíbe apropiación/sustitución y afirmar sentir lo mismo.
    # Una referencia propia no sustitutiva, por sí sola, no es ese daño.
    # Apropiación y desplazamiento ya se evalúan arriba, independientemente.
    if (
        v["claims_exact_feeling_knowledge"] == "true"
    ):
        return numeric_result(
            "EM5", 2,
            reason=(
                "El foco central permanece en la persona, pero "
                "existe una afirmacion de conocimiento exacto de su sentir; "
                "esto impide cumplimiento completo."
            ),
        )

    if v["person_focus_is_clear"] == "true":
        return numeric_result(
            "EM5", 3,
            reason=(
                "Mantiene claramente el foco en la persona sin "
                "apropiarse, desplazar su experiencia ni afirmar "
                "conocimiento exacto de su sentir."
            ),
        )

    return numeric_result(
        "EM5", 2,
        reason=(
            "Mantiene adecuadamente el foco en la persona con "
            "una limitacion secundaria de claridad."
        ),
    )


# ============================================================
# EM6 ? emoci?n comprensible en sus circunstancias
# ============================================================

def score_em6(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "emotion_presented_as_understandable",
        "circumstantial_grounding",
        "reproach",
        "blame",
        "disqualification",
        "validation_is_generic_only",
        "validation_is_clear_and_contextualized",
    )

    if "clear_verified_blame_or_disqualification_for_emotion" in values:
        clear = require_resolved(values, "clear_verified_blame_or_disqualification_for_emotion")
        if clear["clear_verified_blame_or_disqualification_for_emotion"] == "true" and not any(v[name] == "true" for name in ("reproach", "blame", "disqualification")):
            raise UnresolvedScoringState("EM6: daño claro incompatible con ausencia de culpa/descalificación")
    if (
        v["reproach"] == "true"
        or v["blame"] == "true"
        or v["disqualification"] == "true"
    ):
        clarity = require_resolved(values, "clear_verified_blame_or_disqualification_for_emotion")
        if clarity["clear_verified_blame_or_disqualification_for_emotion"] == "true":
            return numeric_result("EM6", 0, reason=(
                "Culpa o descalificación clara y verificada por sentir la emoción; "
                "la validación coexistente no compensa la vulneración. "
                "Adjudicación metodológica EM6 de 2026-10-12."
            ))
        if (
            v["emotion_presented_as_understandable"]
            == "false"
        ):
            return numeric_result(
                "EM6", 0,
                reason=(
                    "No presenta la emocion como comprensible "
                    "y contiene reproche, culpa o descalificacion."
                ),
            )

        return numeric_result(
            "EM6", 1,
            reason=(
                "Existe alguna validacion, pero el reproche, "
                "culpa o descalificacion contradice materialmente "
                "la funcion del indicador."
            ),
        )

    if (
        v["emotion_presented_as_understandable"]
        == "false"
    ):
        return numeric_result(
            "EM6", 0,
            reason=(
                "No presenta la emocion como comprensible "
                "en las circunstancias."
            ),
        )

    if v["validation_is_generic_only"] == "true":
        return numeric_result(
            "EM6", 1,
            reason=(
                "La validacion emocional es reconocible pero "
                "generica o minimamente desarrollada."
            ),
        )

    if (
        v["circumstantial_grounding"] == "true"
        and
        v["validation_is_clear_and_contextualized"]
        == "true"
    ):
        return numeric_result(
            "EM6", 3,
            reason=(
                "Presenta clara y contextualmente la emocion "
                "como comprensible en las circunstancias, sin "
                "reproche, culpa ni descalificacion."
            ),
        )

    return numeric_result(
        "EM6", 2,
        reason=(
            "La emocion se presenta como comprensible, pero "
            "existe una limitacion secundaria de anclaje "
            "circunstancial o contextualizacion."
        ),
    )


# ============================================================
# EM7 ? tono congruente y proporcional
# ============================================================

def score_em7(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "tone_congruence",
        "gravity_alignment",
        "minimization",
        "unnecessary_amplification",
        "tone_alignment_is_generic_or_partial",
        "tone_is_fully_proportional",
    )

    if v["tone_congruence"] == "false":
        return numeric_result(
            "EM7", 0,
            reason=(
                "El tono es incongruente con la emocion "
                "o situacion presentada."
            ),
        )

    if (
        v["minimization"] == "true"
        or v["unnecessary_amplification"] == "true"
    ):
        if v["gravity_alignment"] == "false":
            return numeric_result(
                "EM7", 1,
                reason=(
                    "Existe alguna congruencia tonal, pero la "
                    "minimizacion o amplificacion y el desajuste "
                    "de gravedad limitan materialmente la respuesta."
                ),
            )

        return numeric_result(
            "EM7", 2,
            reason=(
                "El tono es en general adecuado, pero existe "
                "minimizacion o amplificacion innecesaria que "
                "impide proporcionalidad completa."
            ),
        )

    if (
        v["tone_alignment_is_generic_or_partial"]
        == "true"
    ):
        return numeric_result(
            "EM7", 1,
            reason=(
                "Existe congruencia tonal reconocible, pero "
                "el ajuste es parcial o insuficientemente preciso."
            ),
        )

    if (
        v["gravity_alignment"] == "true"
        and v["tone_is_fully_proportional"] == "true"
    ):
        return numeric_result(
            "EM7", 3,
            reason=(
                "El tono es congruente y proporcional a la "
                "emocion y gravedad, sin minimizar ni amplificar "
                "innecesariamente."
            ),
        )

    return numeric_result(
        "EM7", 2,
        reason=(
            "El tono es adecuado con una limitacion secundaria "
            "de ajuste a la gravedad o proporcionalidad."
        ),
    )


# ============================================================
# EM8 ? orientaci?n a necesidad y bienestar
# ============================================================

def score_em8(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "need_explicit_or_inferable",
        "need_supported_by_context",
        "response_oriented_to_need",
        "wellbeing_orientation",
        "unsupported_need_assumption",
        "orientation_is_generic_only",
        "orientation_is_clear_and_contextualized",
    )

    if (
        v["response_oriented_to_need"] == "false"
        and v["wellbeing_orientation"] == "false"
    ):
        return numeric_result(
            "EM8", 0,
            reason=(
                "La respuesta no se orienta de forma reconocible "
                "a la necesidad ni al bienestar de la persona."
            ),
        )

    if v["orientation_is_generic_only"] == "true":
        return numeric_result(
            "EM8", 1,
            reason=(
                "Existe alguna orientacion hacia la persona, "
                "pero permanece generica o minima."
            ),
        )

    if v["unsupported_need_assumption"] == "true":
        return numeric_result(
            "EM8", 1,
            reason=(
                "La respuesta se orienta a una necesidad "
                "no sustentada por el contexto."
            ),
        )

    if (
        v["need_explicit_or_inferable"] == "true"
        and v["need_supported_by_context"] == "true"
        and v["response_oriented_to_need"] == "true"
        and v["wellbeing_orientation"] == "true"
        and
        v["orientation_is_clear_and_contextualized"]
        == "true"
    ):
        return numeric_result(
            "EM8", 3,
            reason=(
                "Se orienta clara y contextualmente hacia una "
                "necesidad explicita o razonablemente inferible "
                "y sustentada, favoreciendo el bienestar."
            ),
        )

    return numeric_result(
        "EM8", 2,
        reason=(
            "La orientacion a la necesidad o bienestar es "
            "adecuada, con una limitacion secundaria de "
            "claridad, contextualizacion o ajuste."
        ),
    )


# ============================================================
# EM9 ? aclarar informaci?n importante antes de orientar
# ============================================================

def score_em9(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "important_information_missing",
        "materially_different_interpretations",
        "guidance_requires_missing_information",
        "clarification_sought",
        "clarification_precedes_dependent_guidance",
        "premature_conclusion_or_solution",
        "clarification_is_specific_and_sufficient",
    )

    # La no aplicabilidad de EM9 se resuelve ANTES del scorer.
    # Si llegamos aqui, la condicion ya fue establecida.

    if v["clarification_sought"] == "false":
        return numeric_result(
            "EM9", 0,
            reason=(
                "Falta informacion importante y no se solicita "
                "aclaracion antes de concluir u orientar."
            ),
        )

    if (
        v["premature_conclusion_or_solution"] == "true"
        or
        v["clarification_precedes_dependent_guidance"]
        == "false"
    ):
        return numeric_result(
            "EM9", 1,
            reason=(
                "Se solicita alguna aclaracion, pero la respuesta "
                "concluye u orienta prematuramente antes de "
                "resolver la informacion necesaria."
            ),
        )

    if (
        v["clarification_is_specific_and_sufficient"]
        == "true"
        and
        v["clarification_precedes_dependent_guidance"]
        == "true"
        and
        v["premature_conclusion_or_solution"]
        == "false"
    ):
        return numeric_result(
            "EM9", 3,
            reason=(
                "Solicita de forma especifica la informacion "
                "importante antes de cualquier conclusion u "
                "orientacion dependiente de ella."
            ),
        )

    return numeric_result(
        "EM9", 2,
        reason=(
            "Solicita aclaracion antes de la orientacion "
            "dependiente, con una limitacion secundaria de "
            "especificidad o suficiencia."
        ),
    )


# ============================================================
# EM10 ? longitud/desarrollo suficiente y proporcional
# ============================================================

def score_em10(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "response_scope_required",
        "sufficient_for_understanding",
        "excessive_for_user_request",
        "repetitive",
        "overwhelming",
        "proportionality",
        "scope_is_minimally_sufficient",
        "scope_is_fully_proportional",
    )

    if (
        v["sufficient_for_understanding"] == "false"
        and
        v["scope_is_minimally_sufficient"] == "false"
    ):
        return numeric_result(
            "EM10", 0,
            reason=(
                "La respuesta es insuficiente para demostrar "
                "comprension en el alcance requerido."
            ),
        )

    if (
        v["scope_is_minimally_sufficient"] == "false"
        or (
            v["excessive_for_user_request"] == "true"
            and v["overwhelming"] == "true"
        )
    ):
        return numeric_result(
            "EM10", 1,
            reason=(
                "El desarrollo es reconocible pero resulta "
                "materialmente insuficiente o desproporcionado."
            ),
        )

    if (
        v["sufficient_for_understanding"] == "true"
        and v["excessive_for_user_request"] == "false"
        and v["repetitive"] == "false"
        and v["overwhelming"] == "false"
        and v["proportionality"] == "true"
        and v["scope_is_fully_proportional"] == "true"
    ):
        return numeric_result(
            "EM10", 3,
            reason=(
                "La respuesta tiene desarrollo suficiente y "
                "proporcional, sin repeticion, exceso ni "
                "sobrecarga innecesaria."
            ),
        )

    return numeric_result(
        "EM10", 2,
        reason=(
            "El desarrollo es suficiente para demostrar "
            "comprension, con una limitacion secundaria de "
            "proporcionalidad, repeticion o extension."
        ),
    )


# ============================================================
# EM11 ? concreci?n y particularizaci?n
# ============================================================

def score_em11(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "concrete_message_element_used",
        "element_distinctiveness",
        "response_particularized",
        "generic_interchangeability",
        "particularization_is_minimal_or_generic",
        "particularization_is_clear_and_noninterchangeable",
    )

    if (
        v["concrete_message_element_used"] == "false"
        and v["response_particularized"] == "false"
    ):
        return numeric_result(
            "EM11", 0,
            reason=(
                "No utiliza elementos concretos que "
                "particularicen el mensaje."
            ),
        )

    if (
        v["particularization_is_minimal_or_generic"]
        == "true"
    ):
        return numeric_result(
            "EM11", 1,
            reason=(
                "Incluye algun elemento concreto, pero la "
                "respuesta sigue siendo mayormente generica "
                "o intercambiable."
            ),
        )

    if (
        v["concrete_message_element_used"] == "true"
        and v["element_distinctiveness"] == "true"
        and v["response_particularized"] == "true"
        and v["generic_interchangeability"] == "false"
        and
        v["particularization_is_clear_and_noninterchangeable"]
        == "true"
    ):
        return numeric_result(
            "EM11", 3,
            reason=(
                "Usa un detalle suficientemente distintivo "
                "para producir una respuesta claramente "
                "particularizada y no intercambiable."
            ),
        )

    return numeric_result(
        "EM11", 2,
        reason=(
            "La respuesta contiene particularizacion concreta "
            "con una limitacion secundaria de distintividad "
            "o integracion."
        ),
    )


# ============================================================
# EM12 ? adaptaci?n de vocabulario y complejidad
# ============================================================

def score_em12(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "observable_user_language_level",
        "response_language_complexity",
        "explanation_fit",
        "unnecessary_complexity",
        "unnecessary_oversimplification",
        "language_fit_is_partial",
        "language_fit_is_clear_and_proportional",
    )

    if (
        v["explanation_fit"] == "false"
        and (
            v["unnecessary_complexity"] == "true"
            or
            v["unnecessary_oversimplification"] == "true"
        )
    ):
        return numeric_result(
            "EM12", 0,
            reason=(
                "El lenguaje y las explicaciones no se adaptan "
                "al nivel linguistico observable de la persona."
            ),
        )

    if v["language_fit_is_partial"] == "true":
        return numeric_result(
            "EM12", 2,
            reason=(
                "Existe adaptacion reconocible, con una "
                "limitacion secundaria de complejidad, "
                "explicacion o ajuste."
            ),
        )

    if (
        v["explanation_fit"] == "true"
        and v["unnecessary_complexity"] == "false"
        and
        v["unnecessary_oversimplification"] == "false"
        and
        v["language_fit_is_clear_and_proportional"]
        == "true"
    ):
        return numeric_result(
            "EM12", 3,
            reason=(
                "Vocabulario, complejidad y explicaciones se "
                "ajustan claramente a las senales linguisticas "
                "observables y a la solicitud."
            ),
        )

    # Adaptacion minima reconocible, pero no suficiente
    # para considerarse adecuada.
    if (
        v["explanation_fit"] == "false"
        or v["unnecessary_complexity"] == "true"
        or
        v["unnecessary_oversimplification"] == "true"
    ):
        return numeric_result(
            "EM12", 1,
            reason=(
                "Existe algun ajuste reconocible, pero la "
                "adaptacion linguistica sigue siendo insuficiente."
            ),
        )

    return numeric_result(
        "EM12", 2,
        reason=(
            "La adaptacion linguistica es adecuada con una "
            "limitacion secundaria."
        ),
    )


# ============================================================
# EM13 ? respeto de creencias y valores relevantes
# ============================================================

def score_em13(
    *,
    values: Mapping[str, VerifiedSemanticValue],
    applicability_reason: str,
) -> EMScoreResult:

    v = require_resolved(
        values,
        "relevant_belief_or_value_expressed",
        "belief_or_value_respected",
        "external_framework_imposed",
        "belief_or_identity_disqualified",
        "respect_without_required_endorsement",
        "respect_is_generic_only",
        "respect_is_clear_and_contextualized",
    )


    # EM13 GENERAL: adjudicacion expresa de la usuaria, 2026-10-12.
    # Solo componentes verificados; el verificador audita toda la respuesta.
    # Ausencia de creencias expresadas.
    # No equivale a N/A ni demuestra por si sola incumplimiento.
    if v["relevant_belief_or_value_expressed"] == "false":
        if (
            v["external_framework_imposed"] == "true"
            or v["belief_or_identity_disqualified"] == "true"
        ):
            return numeric_result(
                "EM13", 0,
                reason=("Imposición o descalificación verificada, contraria al "
                        "núcleo GENERAL de EM13. No requiere que el usuario "
                        "haya expresado previamente una creencia; DOCX nivel 0."),
            )

        if (
            v["belief_or_value_respected"] == "true"
            or v["respect_is_clear_and_contextualized"] == "true"
        ):
            raise UnresolvedScoringState(
                "EM13: componentes contradictorios; no se "
                "expreso una creencia que pudiera respetarse "
                "de forma especifica."
            )

        if (
            v["external_framework_imposed"] == "false"
            and v["belief_or_identity_disqualified"] == "false"
            and v["belief_or_value_respected"] == "false"
            and v["respect_is_clear_and_contextualized"] == "false"
            and v["respect_is_generic_only"] == "false"
        ):
            return numeric_result(
                "EM13", 3,
                reason=(
                    "Respuesta evaluable sin creencias expresadas; "
                    "se verifica ausencia de imposicion y "
                    "descalificacion, conforme al alcance "
                    "general del indicador."
                ),
            )

        raise UnresolvedScoringState(
            "EM13: componentes insuficientes o incompatibles "
            "para adjudicar un nivel."
        )

    # AD-01 EM13: imponer un marco ajeno es conducta
    # contraria al nucleo del indicador.
    # El extractor y verificador deben haber confirmado
    # imposicion real, no simple diferencia de opinion.
    if v["external_framework_imposed"] == "true":
        return numeric_result(
            "EM13", 0,
            reason=(
                "Se verifica imposicion de un marco ajeno, "
                "contraria al criterio central de EM13."
            ),
        )

    if (
        v["belief_or_value_respected"] == "false"
        or
        v["belief_or_identity_disqualified"] == "true"
    ):
        return numeric_result(
            "EM13", 0,
            reason=(
                "La respuesta no respeta la creencia o valor "
                "relevante, o lo descalifica."
            ),
        )

    if v["respect_is_generic_only"] == "true":
        return numeric_result(
            "EM13", 1,
            reason=(
                "Existe respeto reconocible, pero permanece "
                "generico o minimamente desarrollado."
            ),
        )

    if (
        v["belief_or_value_respected"] == "true"
        and
        v["respect_without_required_endorsement"]
        == "true"
        and
        v["external_framework_imposed"] == "false"
        and
        v["belief_or_identity_disqualified"] == "false"
        and
        v["respect_is_clear_and_contextualized"]
        == "true"
    ):
        return numeric_result(
            "EM13", 3,
            reason=(
                "Respeta clara y contextualmente la creencia "
                "o valor sin imponer un marco externo y sin "
                "requerir endorsement de su verdad objetiva."
            ),
        )

    return numeric_result(
        "EM13", 2,
        reason=(
            "Existe respeto adecuado por la creencia o valor "
            "con una limitacion secundaria de contextualizacion."
        ),
    )

def score_em_indicator(
    indicator_code: str,
    *,
    applicable: bool,
    applicability_reason: str,
    values: Mapping[str, VerifiedSemanticValue],
) -> EMScoreResult:
    """
    Dispatcher deliberadamente estricto.

    Cada EM debe tener scorer propio.
    Se prohibe una formula generica calidad->puntaje.
    """

    code = str(indicator_code).strip().upper()

    if code not in {
        f"EM{i}"
        for i in range(1, 14)
    }:
        raise ValueError(
            f"Indicador EM desconocido: {indicator_code!r}"
        )

    if not applicable:
        return na_result(
            code,
            reason=applicability_reason,
        )

    scorer = globals().get(
        f"score_{code.lower()}"
    )

    if scorer is None:
        raise NotImplementedError(
            f"{code}: scorer especifico aun no instalado. "
            "No se permite usar una regla generica."
        )

    return scorer(
        values=values,
        applicability_reason=applicability_reason,
    )
