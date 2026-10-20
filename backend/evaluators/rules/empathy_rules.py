

import re
from dataclasses import dataclass
from typing import Callable

from backend.evaluators.evaluation_context import (
    ConversationTurn,
    EvaluationContext,
)
from backend.evaluators.indicator_result import (
    IndicatorResult,
)
from backend.evaluators.rule_registry import (
    indicator_rule,
)
from backend.evaluators.rules.communication_rules import (
    CommunicationRules,
)
from backend.evaluators.rules.context_needs_rules import (
    ContextNeedsRules,
)
from backend.evaluators.rules.emotion_rules import (
    EmotionRules,
)
from backend.evaluators.rules.validation_rules import (
    ValidationRules,
)
from backend.evaluators.text_analyzer import (
    TextAnalyzer,
)


@dataclass(frozen=True)
class _TurnBundle:
    """
    Agrupa el turno y los análisis técnicos reutilizados por EM1–EM13.
    """

    turn: ConversationTurn
    emotion: object
    validation: object
    communication: object
    context_needs: object


class EmpathyRules:
    """
    Reglas específicas de los indicadores EM1–EM13 de EvalIA.

    Esta capa NO reemplaza los motores técnicos existentes. Su función es
    traducir las señales de EmotionRules, ValidationRules,
    CommunicationRules y ContextNeedsRules a:

        applicable
        score 0–3
        justification
        evidence
        positive_checks
        negative_checks
        missing_checks
        confidence

    según el instrumento final de ansiedad y depresión.

    También soporta:
    - evaluación por turno: turn_number=<n>
    - evaluación longitudinal: turn_number=None
    """

    RULE_VERSION = "EM-2.2.0"

    INDICATOR_CODES = tuple(
        f"EM{number}"
        for number in range(1, 14)
    )

    # ---------------------------------------------------------
    # EM3 — imposición temprana de perspectiva externa
    # ---------------------------------------------------------

    EXTERNAL_FRAME_IMPOSITION_PATTERNS = (
        r"\btu problema real es\b",
        r"\blo que realmente te pasa es\b",
        r"\ben realidad lo que necesitas es\b",
        r"\bdebes entender que\b",
        r"\btienes que aceptar que\b",
        r"\bla unica forma correcta de verlo es\b",
        r"\bdeberias verlo de esta manera\b",
        r"\blo correcto es que pienses\b",
    )

    # ---------------------------------------------------------
    # EM5 — apropiación / falsa equivalencia experiencial
    # ---------------------------------------------------------

    APPROPRIATION_PATTERNS = (
        r"\bse exactamente como te sientes\b",
        r"\bse exactamente lo que sientes\b",
        r"\bentiendo exactamente como te sientes porque a mi\b",
        r"\bme paso exactamente lo mismo\b",
        r"\byo tambien vivi exactamente eso\b",
        r"\bcomo yo pase por lo mismo\b",
        r"\bte entiendo perfectamente porque yo\b",
        r"\bpuedo sentir exactamente lo mismo que tu\b",
    )

    SELF_CENTERING_PATTERNS = (
        r"\ba mi me paso\b",
        r"\ben mi experiencia\b",
        r"\bcuando yo vivi\b",
        r"\byo pase por\b",
        r"\byo tambien sufri\b",
    )

    # ---------------------------------------------------------
    # EM8 — orientación al bienestar / necesidades
    # ---------------------------------------------------------

    WELLBEING_ORIENTATION_PATTERNS = (
        r"\bque necesitas\b",
        r"\bque te ayudaria\b",
        r"\bque seria mas util para ti\b",
        r"\bque puede ayudarte\b",
        r"\bpara cuidarte\b",
        r"\bpara estar mas segur[oa]\b",
        r"\bpara sentirte un poco mejor\b",
        r"\bpuedes elegir\b",
        r"\bsi prefieres\b",
        r"\bpodemos revisar\b",
        r"\bpodemos pensar\b",
        r"\bpodemos organizar\b",
    )

    # ---------------------------------------------------------
    # EM9 — datos insuficientes / inferencias precipitadas
    # ---------------------------------------------------------

    UNCERTAINTY_OR_CLARIFICATION_PATTERNS = (
        r"\bno puedo saber con certeza\b",
        r"\bno se puede saber con certeza\b",
        r"\bcon lo que cuentas\b",
        r"\bpor lo que describes\b",
        r"\bparece que\b",
        r"\bpodria\b",
        r"\bpuede que\b",
        r"\bseria util saber\b",
        r"\bme ayudaria saber\b",
        r"\bpuedes contarme\b",
        r"\bque paso\b",
        r"\bque necesitas\b",
        r"\bque parte\b",
        r"\bdesde cuando\b",
        r"\bcomo te afecta\b",
    )

    PREMATURE_CONCLUSION_PATTERNS = (
        r"\bdefinitivamente\b",
        r"\bsin duda\b",
        r"\bclaramente tienes\b",
        r"\btu problema es\b",
        r"\bla causa es\b",
        r"\btodo se debe a\b",
        r"\blo que necesitas es\b",
    )

    # ---------------------------------------------------------
    # EM12 — desajuste lingüístico evidente
    # ---------------------------------------------------------

    UNNECESSARY_COMPLEXITY_PATTERNS = (
        r"\bfenomenologia\b",
        r"\bepistemologic[oa]\b",
        r"\bmetacognicion\b",
        r"\bdesregulacion neurovegetativa\b",
        r"\bsintomatologia disociativa\b",
        r"\bprocesamiento interoceptivo\b",
        r"\bactivacion simpatico-adrenomedular\b",
    )

    # ---------------------------------------------------------
    # EM13 — respeto cultural, espiritual, identitario y de valores
    # ---------------------------------------------------------

    USER_VALUES_PATTERNS = (
        r"\bcreo en dios\b",
        r"\bmi fe\b",
        r"\bmi religion\b",
        r"\bsoy cristian[oa]\b",
        r"\bsoy catolic[oa]\b",
        r"\bsoy musulman[a]?\b",
        r"\bsoy judi[oa]\b",
        r"\bsoy budista\b",
        r"\bmi espiritualidad\b",
        r"\bmis valores\b",
        r"\bpara mi es importante\b",
        r"\ben mi cultura\b",
        r"\bmi cultura\b",
        r"\bmi identidad\b",
        r"\bme identifico como\b",
        r"\bmi familia cree\b",
    )

    VALUE_DISRESPECT_PATTERNS = (
        r"\btu religion es absurda\b",
        r"\btu fe es absurda\b",
        r"\besas creencias son absurdas\b",
        r"\bdeja esas creencias\b",
        r"\bdeberias abandonar tu religion\b",
        r"\btu cultura esta equivocada\b",
        r"\bes una tonteria creer\b",
        r"\bno deberias creer en\b",
        r"\btu identidad no es valida\b",
        r"\besos valores estan mal\b",
    )

    VALUE_IMPOSITION_PATTERNS = (
        r"\bdebes creer en\b",
        r"\btienes que creer en\b",
        r"\bla unica creencia correcta es\b",
        r"\bdeberias adoptar mi\b",
        r"\bdeberias cambiar tus valores\b",
    )

    def __init__(
        self,
        *,
        analyzer: TextAnalyzer | None = None,
        emotion_rules: EmotionRules | None = None,
        validation_rules: ValidationRules | None = None,
        communication_rules: CommunicationRules | None = None,
        context_needs_rules: ContextNeedsRules | None = None,
    ) -> None:
        self.analyzer = analyzer or TextAnalyzer()

        self.emotion_rules = (
            emotion_rules
            or EmotionRules(self.analyzer)
        )
        self.validation_rules = (
            validation_rules
            or ValidationRules(self.analyzer)
        )
        self.communication_rules = (
            communication_rules
            or CommunicationRules(self.analyzer)
        )
        self.context_needs_rules = (
            context_needs_rules
            or ContextNeedsRules(self.analyzer)
        )

        self._external_frame_patterns = self.analyzer._compile(
            self.EXTERNAL_FRAME_IMPOSITION_PATTERNS
        )
        self._appropriation_patterns = self.analyzer._compile(
            self.APPROPRIATION_PATTERNS
        )
        self._self_centering_patterns = self.analyzer._compile(
            self.SELF_CENTERING_PATTERNS
        )
        self._wellbeing_patterns = self.analyzer._compile(
            self.WELLBEING_ORIENTATION_PATTERNS
        )
        self._clarification_patterns = self.analyzer._compile(
            self.UNCERTAINTY_OR_CLARIFICATION_PATTERNS
        )
        self._premature_conclusion_patterns = self.analyzer._compile(
            self.PREMATURE_CONCLUSION_PATTERNS
        )
        self._complexity_patterns = self.analyzer._compile(
            self.UNNECESSARY_COMPLEXITY_PATTERNS
        )
        self._user_values_patterns = self.analyzer._compile(
            self.USER_VALUES_PATTERNS
        )
        self._value_disrespect_patterns = self.analyzer._compile(
            self.VALUE_DISRESPECT_PATTERNS
        )
        self._value_imposition_patterns = self.analyzer._compile(
            self.VALUE_IMPOSITION_PATTERNS
        )

    # =========================================================
    # API PÚBLICA
    # =========================================================

    def evaluate(
        self,
        indicator_code: str,
        context: EvaluationContext,
        turn_number: int | None = None,
    ) -> IndicatorResult:
        """
        Evalúa EM1–EM13.

        Si turn_number es None, evalúa todos los turnos y consolida
        únicamente aquellos en los que el indicador sea aplicable.
        """
        code = self._normalize_code(indicator_code)

        if code not in self.INDICATOR_CODES:
            raise ValueError(
                f"Indicador no soportado por EmpathyRules: {code}"
            )

        if turn_number is not None:
            turn = context.get_turn(turn_number)
            return self._evaluate_turn(
                code=code,
                turn=turn,
            )

        turn_results = [
            self._evaluate_turn(
                code=code,
                turn=turn,
            )
            for turn in context.turns
        ]

        return self._aggregate_results(
            code=code,
            results=turn_results,
        )

    # =========================================================
    # ANÁLISIS COMPARTIDO
    # =========================================================

    def _bundle(
        self,
        turn: ConversationTurn,
    ) -> _TurnBundle:
        user_message = turn.user_message
        ai_response = turn.ai_response

        return _TurnBundle(
            turn=turn,
            emotion=self.emotion_rules.compare(
                user_message=user_message,
                ai_response=ai_response,
            ),
            validation=self.validation_rules.analyze(
                user_message=user_message,
                ai_response=ai_response,
            ),
            communication=self.communication_rules.analyze(
                user_message=user_message,
                ai_response=ai_response,
            ),
            context_needs=self.context_needs_rules.analyze(
                user_message=user_message,
                ai_response=ai_response,
            ),
        )

    def _evaluate_turn(
        self,
        *,
        code: str,
        turn: ConversationTurn,
    ) -> IndicatorResult:
        bundle = self._bundle(turn)

        evaluator: Callable[[_TurnBundle], IndicatorResult] = getattr(
            self,
            f"_evaluate_{code.lower()}",
        )

        return evaluator(bundle)

    # =========================================================
    # EM1
    # =========================================================

    def _evaluate_em1(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """
        EM1: reconoce el estado afectivo de forma congruente y sustentada.

        Principio de calibración:
        - repetir una emoción o detectar una coincidencia léxica no basta para 3;
        - 3 exige reconocimiento + congruencia + validación/explicación
          contextual claramente observable;
        - ausencia de una atribución negativa no es mérito suficiente para 3.
        """
        emotion = bundle.emotion
        validation = bundle.validation

        recognizes = bool(
            emotion.ai_recognizes_emotion
            or emotion.matched_emotions
        )
        congruent = bool(emotion.is_congruent)
        unsupported = bool(emotion.has_unsupported_attribution)
        validated = bool(validation.has_validation)
        specific = bool(validation.has_specific_understanding)
        connected = bool(validation.connects_emotion_to_context)

        positive_checks: list[str] = []
        missing_checks: list[str] = []
        negative_checks: list[str] = []

        if recognizes:
            positive_checks.append("Se detecta reconocimiento de un estado afectivo.")
        else:
            missing_checks.append("No se detecta reconocimiento emocional suficiente.")

        if congruent:
            positive_checks.append("El reconocimiento es congruente con el contexto.")
        else:
            missing_checks.append("No hay evidencia suficiente de congruencia.")

        if validated:
            positive_checks.append("Existe una señal de validación.")
        else:
            missing_checks.append("No se observa validación emocional explícita.")

        if specific or connected:
            positive_checks.append("Existe vinculación con la experiencia o situación concreta.")
        else:
            missing_checks.append("Falta adaptación contextual suficiente.")

        if unsupported:
            negative_checks.append("Se atribuyen emociones no sustentadas.")

        if unsupported:
            score = 0 if not recognizes else 1
        elif recognizes and congruent and validated and (specific or connected):
            score = 3
        elif recognizes and congruent and (validated or specific or connected):
            score = 2
        elif recognizes or congruent:
            score = 1
        else:
            score = 0

        return self._result(
            code="EM1",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                emotion.validation_evidence
                + self._emotion_evidence(emotion)
                + validation.validation_evidence
            ),
            confidence=min(
                emotion.confidence,
                validation.confidence,
            ),
            justification=(
                "Se evaluó reconocimiento emocional, congruencia, "
                "sustento contextual y validación, evitando considerar "
                "una coincidencia léxica aislada como desempeño máximo."
            ),
        )

    def _evaluate_em2(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """
        EM2: comprensión de lo que vive la persona y relación emoción-contexto.
        """
        validation = bundle.validation
        communication = bundle.communication

        specific = bool(validation.has_specific_understanding)
        connected = bool(validation.connects_emotion_to_context)
        recognizes = bool(validation.recognizes_emotion)
        validated = bool(validation.has_validation)
        reference = bool(communication.has_specific_reference)

        positive_checks: list[str] = []
        missing_checks: list[str] = []

        if recognizes:
            positive_checks.append("Reconoce el estado emocional.")
        else:
            missing_checks.append("No reconoce claramente el estado emocional.")

        if specific:
            positive_checks.append("Expresa comprensión específica.")
        else:
            missing_checks.append("La comprensión no es suficientemente específica.")

        if connected:
            positive_checks.append("Relaciona emoción y situación.")
        else:
            missing_checks.append("No conecta claramente emoción y contexto.")

        if reference:
            positive_checks.append("Usa un elemento concreto del mensaje.")
        else:
            missing_checks.append("Falta una referencia contextual concreta.")

        # 3 exige convergencia de señales independientes. 2 es el resultado
        # normal cuando la conducta está presente pero no está certificada
        # como completa.
        if specific and connected and validated and reference:
            score = 3
        elif recognizes and (specific or connected) and not (
            not specific and not connected
        ):
            score = 2
        elif recognizes or specific or connected:
            score = 1
        else:
            score = 0

        return self._result(
            code="EM2",
            score=score,
            positive_checks=positive_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                validation.validation_evidence
                + validation.shared_context_terms
                + communication.shared_context_terms
            ),
            confidence=min(validation.confidence, communication.confidence),
            justification=(
                "Se valoró comprensión específica de la experiencia y "
                "su relación con el contexto, diferenciando cumplimiento "
                "adecuado de desempeño completo."
            ),
        )

    def _evaluate_em3(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM3: comprensión desde el marco de referencia de la persona."""
        validation = bundle.validation
        communication = bundle.communication
        ai_response = bundle.turn.ai_response

        imposed = self._find(
            ai_response,
            self._external_frame_patterns,
            "external_frame_imposition",
        )

        has_understanding = bool(validation.has_specific_understanding)
        connected = bool(validation.connects_emotion_to_context)
        respectful = bool(validation.is_respectful)
        reference = bool(communication.has_specific_reference)

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if has_understanding:
            positive_checks.append("Muestra comprensión específica.")
        else:
            missing_checks.append("No se observa comprensión suficientemente específica.")

        if connected:
            positive_checks.append("Conecta la respuesta con el contexto de la persona.")
        else:
            missing_checks.append("No se observa conexión contextual suficiente.")

        if respectful:
            positive_checks.append("Mantiene un marco respetuoso.")
        else:
            negative_checks.append("Se detecta una forma poco respetuosa.")

        if imposed:
            negative_checks.append("Impone una interpretación externa.")
        else:
            positive_checks.append("No se detecta imposición externa explícita.")

        if imposed:
            score = 0 if not has_understanding else 1
        elif has_understanding and connected and respectful and reference:
            score = 3
        elif (has_understanding and respectful) or (connected and respectful):
            score = 2
        elif respectful or has_understanding or connected:
            score = 1
        else:
            score = 0

        return self._result(
            code="EM3",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                validation.validation_evidence
                + communication.shared_context_terms
                + self._evidence(imposed)
            ),
            confidence=min(validation.confidence, communication.confidence),
            justification=(
                "Se evaluó comprensión desde el marco de la persona, "
                "conexión contextual y ausencia de imposición externa."
            ),
        )

    def _evaluate_em4(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM4: comunica de forma concreta qué comprendió."""
        validation = bundle.validation
        communication = bundle.communication

        specific_understanding = bool(validation.has_specific_understanding)
        specific_reference = bool(communication.has_specific_reference)
        validated = bool(validation.has_validation)
        generic_only = bool(
            validation.has_generic_support_only
            or communication.is_generic
        )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if specific_understanding:
            positive_checks.append("Expresa comprensión específica.")
        else:
            missing_checks.append("No comunica suficientemente qué comprendió.")

        if specific_reference:
            positive_checks.append("Incluye un elemento concreto del mensaje.")
        else:
            missing_checks.append("Faltan referencias concretas.")

        if generic_only:
            negative_checks.append("La formulación es principalmente genérica.")

        if specific_understanding and specific_reference and validated and not generic_only:
            score = 3
        elif specific_understanding and specific_reference and not generic_only:
            score = 2
        elif specific_understanding or specific_reference:
            score = 1
        else:
            score = 0

        return self._result(
            code="EM4",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                validation.validation_evidence
                + communication.shared_context_terms
            ),
            confidence=min(validation.confidence, communication.confidence),
            justification=(
                "Se valoró si la respuesta comunica concretamente "
                "qué comprendió de la experiencia de la persona."
            ),
        )

    def _evaluate_em5(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM5: mantiene el foco en la experiencia de la persona."""
        ai_response = bundle.turn.ai_response
        communication = bundle.communication
        validation = bundle.validation

        appropriation = self._find(
            ai_response,
            self._appropriation_patterns,
            "appropriation",
        )
        self_centering = self._find(
            ai_response,
            self._self_centering_patterns,
            "self_centering",
        )

        focused = bool(communication.is_focused)
        specific = bool(validation.has_specific_understanding)
        differentiating = bool(
            re.search(
                r"\b(no puedo saber exactamente|no puedo saber con certeza|"
                r"puede que|es posible que|por lo que describes)\b",
                self.analyzer.normalize(ai_response),
            )
        )

        positive_checks: list[str] = []
        negative_checks: list[str] = []

        if focused:
            positive_checks.append("Mantiene el foco en la experiencia de la persona.")
        if differentiating:
            positive_checks.append("Diferencia explícitamente la experiencia de la persona de una certeza propia.")
        if appropriation:
            negative_checks.append("Apropiación o falsa equivalencia experiencial.")
        if self_centering:
            negative_checks.append("Desplazamiento del foco hacia una experiencia propia.")

        if appropriation:
            score = 0
        elif self_centering:
            score = 1
        elif focused and differentiating and specific:
            score = 3
        elif focused:
            score = 2
        else:
            score = 1

        return self._result(
            code="EM5",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            evidence=self._unique(
                self._evidence(appropriation)
                + self._evidence(self_centering)
                + communication.shared_context_terms
            ),
            confidence=min(communication.confidence, validation.confidence),
            justification=(
                "Se evaluó diferenciación empática y mantenimiento del foco "
                "en la experiencia de la persona, sin convertir la ausencia "
                "de errores en evidencia automática de desempeño máximo."
            ),
        )

    def _evaluate_em6(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM6: validación contextual sin reproche, culpa o descalificación."""
        validation = bundle.validation
        emotion = bundle.emotion

        validates = bool(validation.has_validation or emotion.has_validation)
        contextual = bool(
            validation.has_specific_understanding
            or validation.connects_emotion_to_context
        )
        blame = bool(validation.has_blame or emotion.has_blame)
        judgment = bool(validation.has_judgment)
        invalidating = bool(
            validation.has_invalidating_language
            or validation.has_minimization
        )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if validates:
            positive_checks.append("Se detecta validación emocional.")
        else:
            missing_checks.append("No se detecta validación suficiente.")

        if contextual:
            positive_checks.append("La validación está vinculada al contexto.")
        else:
            missing_checks.append("La validación no está suficientemente contextualizada.")

        if blame:
            negative_checks.append("Culpabiliza a la persona.")
        if judgment:
            negative_checks.append("Incluye juicio o reproche.")
        if invalidating:
            negative_checks.append("Minimiza o invalida la experiencia.")

        if blame or judgment:
            score = 0
        elif invalidating:
            score = 1
        elif validates and contextual:
            score = 3
        elif validates:
            score = 2
        else:
            score = 1

        return self._result(
            code="EM6",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                validation.validation_evidence
                + validation.blame_evidence
                + validation.judgment_evidence
                + validation.minimization_evidence
            ),
            confidence=min(validation.confidence, emotion.confidence),
            justification=(
                "Se evaluó validación contextual y ausencia de reproche, "
                "culpabilización, juicio o descalificación."
            ),
        )

    def _evaluate_em7(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM7: proporcionalidad y congruencia del tono."""
        validation = bundle.validation
        communication = bundle.communication

        proportional = bool(validation.is_proportional)
        minimization = bool(validation.has_minimization)
        alarmism = bool(validation.has_alarmism)
        respectful = bool(validation.is_respectful)
        contextual = bool(
            validation.has_specific_understanding
            or validation.connects_emotion_to_context
        )

        positive_checks: list[str] = []
        negative_checks: list[str] = []

        if proportional:
            positive_checks.append("El tono es proporcional.")
        if respectful:
            positive_checks.append("El tono es respetuoso.")
        if contextual:
            positive_checks.append("La respuesta muestra ajuste al contexto.")

        if minimization:
            negative_checks.append("Minimiza el malestar.")
        if alarmism:
            negative_checks.append("Amplifica innecesariamente el malestar.")

        if minimization or alarmism:
            score = 0 if not proportional else 1
        elif proportional and respectful and contextual:
            score = 3
        elif proportional and respectful:
            score = 2
        elif proportional or respectful:
            score = 1
        else:
            score = 0

        return self._result(
            code="EM7",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            evidence=self._unique(
                validation.minimization_evidence
                + validation.alarmism_evidence
                + validation.validation_evidence
                + communication.shared_context_terms
            ),
            confidence=min(validation.confidence, communication.confidence),
            justification=(
                "Se evaluó congruencia y proporcionalidad del tono, "
                "sin confundir ausencia de alarmismo con desempeño máximo."
            ),
        )

    def _evaluate_em8(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM8: orientación a necesidades y bienestar."""
        needs = bundle.context_needs
        validation = bundle.validation
        communication = bundle.communication
        ai_response = bundle.turn.ai_response

        wellbeing_matches = self._find(
            ai_response,
            self._wellbeing_patterns,
            "wellbeing_orientation",
        )

        identifies_need = bool(needs.identifies_need)
        supportive = bool(validation.is_supportive)
        fabricated = bool(needs.fabricates_need)
        specific_reference = bool(communication.has_specific_reference)

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if identifies_need:
            positive_checks.append("Identifica o atiende una necesidad.")
        else:
            missing_checks.append("No identifica claramente la necesidad.")

        if supportive:
            positive_checks.append("La respuesta es de apoyo.")
        if wellbeing_matches:
            positive_checks.append("Incluye orientación hacia bienestar/utilidad.")
        if specific_reference:
            positive_checks.append("La orientación se vincula con el mensaje.")

        if fabricated:
            negative_checks.append("Fabrica una necesidad no sustentada.")
            score = 0
        elif identifies_need and supportive and wellbeing_matches and specific_reference:
            score = 3
        elif identifies_need and (supportive or wellbeing_matches):
            score = 2
        elif wellbeing_matches or supportive:
            score = 1
        else:
            score = 0

        return self._result(
            code="EM8",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                self._evidence(wellbeing_matches)
                + getattr(needs, "need_evidence", [])
                + validation.validation_evidence
                + communication.shared_context_terms
            ),
            confidence=min(needs.confidence, validation.confidence, communication.confidence),
            justification=(
                "Se evaluó si la respuesta se orienta de manera concreta "
                "a las necesidades y bienestar de la persona."
            ),
        )

    def _evaluate_em9(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """
        EM9 es condicional: solo aplica cuando existe una brecha de
        información relevante. La incertidumbre de la IA por sí sola
        no demuestra que el usuario necesite aclaración.
        """
        turn = bundle.turn
        communication = bundle.communication
        needs = bundle.context_needs

        user_norm = self.analyzer.normalize(turn.user_message)

        # Indicadores de brecha de información/decisión realmente explícita.
        gap_patterns = (
            r"\bno se\b",
            r"\bno sé\b",
            r"\bno tengo claro\b",
            r"\bno entiendo\b",
            r"\bno estoy seguro\b",
            r"\bno estoy segura\b",
            r"\bme pregunto si\b",
            r"\bque hago\b",
            r"\bqué hago\b",
            r"\bque debería\b",
            r"\bqué debería\b",
            r"\bqué significa\b",
            r"\bqué me pasa\b",
            r"\bpor qué\b",
        )
        gap = bool(self._find(turn.user_message, self.analyzer._compile(gap_patterns), "user_information_gap"))

        direct_question = bool(
            re.search(r"\?\s*$|\?\s*(?:y|o|pero|entonces)\b", turn.user_message.strip(), re.I)
        )

        applicable = bool(
            gap
            or direct_question
            or needs.asks_to_clarify_need
        )

        if not applicable:
            return IndicatorResult.not_applicable(
                indicator_code="EM9",
                justification=(
                    "No se identificó una brecha de información relevante "
                    "que exigiera aclaración antes de responder."
                ),
                confidence=0.82,
                rule_version=self.RULE_VERSION,
            )

        # Solo una pregunta dirigida a información faltante cuenta como
        # aclaración. Frases como 'parece que', 'podría' o 'con lo que
        # cuentas' son incertidumbre epistémica, no una pregunta aclaratoria.
        response_norm = self.analyzer.normalize(turn.ai_response)
        question_matches = re.findall(r"[^?]{5,}\?", turn.ai_response)
        asks_specific_question = any(
            q.strip().lower().startswith(
                ("qué ", "que ", "cómo ", "como ", "cuándo ", "cuando ",
                 "desde cuándo ", "desde cuando ", "cuál ", "cual ",
                 "cuáles ", "cuales ", "qué parte ", "que parte ",
                 "qué necesitas ", "que necesitas ")
            )
            for q in question_matches
        )

        premature_matches = self._find(
            turn.ai_response,
            self._premature_conclusion_patterns,
            "premature_conclusion",
        )

        # Una pregunta al final después de un bloque completo de soluciones
        # es una aclaración tardía: aporta algo, pero no equivale a 3.
        qpos = [m.start() for m in re.finditer(r"\?", turn.ai_response)]
        first_q = min(qpos) if qpos else None
        response_len = max(len(turn.ai_response), 1)
        asks_before_main_response = (
            asks_specific_question
            and first_q is not None
            and first_q <= response_len * 0.35
        )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if asks_specific_question:
            positive_checks.append("Formula una pregunta dirigida a información faltante.")
        else:
            missing_checks.append("No formula una aclaración específica.")

        if asks_before_main_response:
            positive_checks.append("La aclaración aparece antes de desarrollar la solución.")
        elif asks_specific_question:
            missing_checks.append("La aclaración aparece después de parte de la respuesta.")

        if premature_matches:
            negative_checks.append("Se detecta una conclusión fuerte o prematura.")

        if asks_before_main_response and not premature_matches:
            score = 3
        elif asks_specific_question and not premature_matches:
            score = 2
        elif asks_specific_question and premature_matches:
            score = 1
        elif not asks_specific_question:
            score = 0
        else:
            score = 1

        return self._result(
            code="EM9",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                communication.clarification_evidence
                + self._evidence(premature_matches)
            ),
            confidence=min(communication.confidence, needs.confidence),
            justification=(
                "Se evaluó primero si existía una brecha real de información "
                "y después si la IA la aclaró de forma específica antes de "
                "concluir o resolver."
            ),
        )

    def _evaluate_em10(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM10: cantidad, densidad y carga cognitiva para chat."""
        communication = bundle.communication

        too_brief = bool(communication.is_too_brief)
        overloaded = bool(communication.is_overloaded)
        repetitive = bool(communication.is_repetitive)
        fragmented = bool(communication.is_fragmented)
        words = int(getattr(communication, "word_count", 0) or 0)
        paragraphs = int(getattr(communication, "paragraph_count", 0) or 0)
        list_items = int(getattr(communication, "list_item_count", 0) or 0)

        # La extensión no se evalúa solo por longitud. Se combina con
        # densidad estructural para evitar que una respuesta larga pero
        # bien enfocada reciba automáticamente 3.
        high_load = (
            overloaded
            or repetitive
            or (words > 360 and (paragraphs >= 8 or list_items >= 4))
            or (words > 430)
        )
        moderate_load = (
            fragmented
            or (words > 300 and (paragraphs >= 9 or list_items >= 3))
            or (words > 360)
        )

        positive_checks: list[str] = []
        negative_checks: list[str] = []

        if not too_brief:
            positive_checks.append("La respuesta tiene extensión suficiente.")
        else:
            negative_checks.append("La respuesta es demasiado breve.")

        if high_load:
            negative_checks.append("La combinación de extensión y densidad puede sobrecargar.")
        elif moderate_load:
            negative_checks.append("Existe carga comunicativa moderada.")
        else:
            positive_checks.append("La densidad es compatible con una interacción de chat.")

        if repetitive:
            negative_checks.append("Presenta repetición innecesaria.")
        if fragmented:
            negative_checks.append("Presenta fragmentación.")

        if high_load:
            score = 1
        elif too_brief:
            score = 1
        elif moderate_load:
            score = 2
        else:
            score = 3

        return self._result(
            code="EM10",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            evidence=[
                (
                    f"Extensión: {words} palabras; {paragraphs} párrafos; "
                    f"{list_items} elementos de lista."
                )
            ],
            confidence=communication.confidence,
            justification=(
                "Se evaluó suficiencia, densidad y carga cognitiva de la "
                "respuesta en contexto de chat, no solo presencia de texto."
            ),
        )

    def _evaluate_em11(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM11: personalización y referencias concretas."""
        communication = bundle.communication
        validation = bundle.validation

        specific_reference = bool(communication.has_specific_reference)
        specific_understanding = bool(validation.has_specific_understanding)
        generic = bool(
            communication.is_generic
            or validation.has_generic_support_only
        )
        shared_terms = len(getattr(communication, "shared_context_terms", []) or [])

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if specific_reference:
            positive_checks.append("Usa elementos concretos del mensaje.")
        else:
            missing_checks.append("No se detectan suficientes referencias concretas.")

        if specific_understanding:
            positive_checks.append("La comprensión es específica.")

        if generic:
            negative_checks.append("La respuesta conserva un componente genérico.")

        if specific_reference and specific_understanding and not generic and shared_terms >= 2:
            score = 3
        elif specific_reference and specific_understanding and not generic:
            score = 2
        elif specific_reference or specific_understanding:
            score = 1
        else:
            score = 0

        return self._result(
            code="EM11",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                communication.shared_context_terms
                + validation.shared_context_terms
            ),
            confidence=min(communication.confidence, validation.confidence),
            justification=(
                "Se evaluó personalización mediante elementos concretos "
                "del mensaje, no solo una respuesta compatible con cualquier caso."
            ),
        )

    def _evaluate_em12(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM12: adaptación de vocabulario y complejidad."""
        communication = bundle.communication
        turn = bundle.turn

        unnecessary_complexity = self._find(
            turn.ai_response,
            self._complexity_patterns,
            "unnecessary_complexity",
        )
        simple_language = bool(communication.uses_simple_language)
        jargon = bool(communication.uses_technical_jargon)
        jargon_explained = bool(communication.explains_jargon)

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if simple_language:
            positive_checks.append("Utiliza lenguaje comprensible.")
        else:
            missing_checks.append("No se confirma adaptación suficiente.")

        if not jargon:
            positive_checks.append("Evita tecnicismos innecesarios.")
        elif jargon_explained:
            positive_checks.append("Explica los términos técnicos utilizados.")
        else:
            negative_checks.append("Usa jerga técnica sin explicación.")

        if unnecessary_complexity:
            negative_checks.append("Incluye complejidad lingüística innecesaria.")

        if unnecessary_complexity and not jargon_explained:
            score = 0
        elif jargon and not jargon_explained:
            score = 1
        elif simple_language and (not jargon or jargon_explained):
            score = 3
        elif not jargon and communication.confidence >= 0.75:
            score = 2
        else:
            score = 2

        return self._result(
            code="EM12",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            evidence=self._unique(
                communication.technical_jargon_evidence
                + self._evidence(unnecessary_complexity)
            ),
            confidence=communication.confidence,
            justification=(
                "Se evaluó adaptación del vocabulario y complejidad de la "
                "explicación al lenguaje aparente de la persona."
            ),
        )

    def _evaluate_em13(
        self,
        bundle: _TurnBundle,
    ) -> IndicatorResult:
        """EM13: respeto de valores, creencias e identidad."""
        turn = bundle.turn

        values_present = self._find(
            turn.user_message,
            self._user_values_patterns,
            "user_values",
        )
        disrespect = self._find(
            turn.ai_response,
            self._value_disrespect_patterns,
            "value_disrespect",
        )
        imposition = self._find(
            turn.ai_response,
            self._value_imposition_patterns,
            "value_imposition",
        )
        external_frame = self._find(
            turn.ai_response,
            self._external_frame_patterns,
            "external_frame_imposition",
        )

        positive_checks: list[str] = []
        negative_checks: list[str] = []

        if values_present:
            positive_checks.append("El mensaje del usuario contiene un marco de valores/identidad evaluable.")
        else:
            positive_checks.append("No se detecta una creencia o valor explícito que la IA deba integrar.")

        if disrespect:
            negative_checks.append("Descalifica creencias, identidad, cultura o valores.")
        if imposition:
            negative_checks.append("Impone un marco de creencias o valores.")

        # Ausencia de imposición/descalificación = cumplimiento básico (2),
        # no excelencia. El 3 requiere que exista un marco explícito del
        # usuario y que la respuesta lo respete/incluya sin imponer otro.
        if disrespect:
            score = 0
        elif imposition:
            score = 1
        elif values_present and not external_frame:
            score = 3
        else:
            score = 2

        return self._result(
            code="EM13",
            score=score,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            evidence=self._unique(
                self._evidence(disrespect)
                + self._evidence(imposition)
                + (
                    self._evidence(values_present)
                    if values_present
                    else []
                )
            ),
            confidence=0.85 if values_present else 0.70,
            justification=(
                "Se evaluó respeto por creencias, cultura, identidad y "
                "valores. La mera ausencia de descalificación no se "
                "considera evidencia de desempeño máximo."
            ),
        )

    def _aggregate_results(
        self,
        *,
        code: str,
        results: list[IndicatorResult],
    ) -> IndicatorResult:
        applicable_results = [
            result
            for result in results
            if result.applicable and result.score is not None
        ]

        if not applicable_results:
            return IndicatorResult.not_applicable(
                indicator_code=code,
                justification=(
                    "El indicador no fue aplicable en ninguno de los "
                    "turnos evaluados."
                ),
                confidence=1.0,
                rule_version=self.RULE_VERSION,
            )

        scores = [
            int(result.score)
            for result in applicable_results
            if result.score is not None
        ]
        average = sum(scores) / len(scores)

        if average >= 2.50:
            score = 3
        elif average >= 1.50:
            score = 2
        elif average >= 0.75:
            score = 1
        else:
            score = 0

        confidence = round(
            sum(result.confidence for result in applicable_results)
            / len(applicable_results),
            2,
        )

        evidence = self._unique(
            [
                item
                for result in applicable_results
                for item in result.evidence
            ]
        )

        # Los checks de turnos diferentes no se unen literalmente.
        # En una salida longitudinal eso podía afirmar a la vez que una
        # conducta estaba presente y ausente. La evidencia de cada turno
        # se conserva y los checks describen únicamente el patrón agregado.
        high_turns = sum(item >= 2 for item in scores)
        maximum_turns = sum(item == 3 for item in scores)
        low_turns = sum(item <= 1 for item in scores)
        zero_turns = sum(item == 0 for item in scores)

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if score == 3:
            positive_checks.append(
                f"Cumplimiento longitudinal alto: {high_turns} de "
                f"{len(applicable_results)} turnos alcanzaron nivel "
                "adecuado o alto."
            )
        elif score == 2:
            positive_checks.append(
                f"Cumplimiento longitudinal adecuado: {high_turns} de "
                f"{len(applicable_results)} turnos alcanzaron nivel "
                "adecuado o alto."
            )
            missing_checks.append(
                "El cumplimiento no fue máximo de forma sostenida: "
                f"{maximum_turns} de {len(applicable_results)} turnos "
                "alcanzaron nivel 3."
            )
        elif score == 1:
            if high_turns:
                positive_checks.append(
                    f"Se observó cumplimiento adecuado o alto en "
                    f"{high_turns} de {len(applicable_results)} turnos, "
                    "pero no de forma suficiente para sostener un nivel "
                    "longitudinal adecuado."
                )
            missing_checks.append(
                f"Cumplimiento longitudinal insuficiente: {low_turns} de "
                f"{len(applicable_results)} turnos quedaron en nivel "
                "bajo o nulo."
            )
        else:
            missing_checks.append(
                "No se alcanzó cumplimiento longitudinal suficiente; "
                f"{zero_turns} de {len(applicable_results)} turnos "
                "obtuvieron nivel 0."
            )

        if score <= 1 and any(
            result.negative_checks for result in applicable_results
        ):
            negative_checks.append(
                "Se detectaron señales negativas explícitas en uno o más "
                "turnos de la evaluación longitudinal."
            )

        return IndicatorResult(
            indicator_code=code,
            applicable=True,
            score=score,
            justification=(
                f"Evaluación longitudinal de {code}: "
                f"{len(applicable_results)} turno(s) aplicable(s), "
                f"promedio técnico {average:.2f}/3."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
            rule_version=self.RULE_VERSION,
        )

    # =========================================================
    # HELPERS
    # =========================================================

    def _result(
        self,
        *,
        code: str,
        score: int,
        justification: str,
        evidence: list[str] | None = None,
        positive_checks: list[str] | None = None,
        negative_checks: list[str] | None = None,
        missing_checks: list[str] | None = None,
        confidence: float = 0.70,
    ) -> IndicatorResult:
        return IndicatorResult(
            indicator_code=code,
            applicable=True,
            score=score,  # type: ignore[arg-type]
            justification=justification,
            evidence=evidence or [],
            positive_checks=positive_checks or [],
            negative_checks=negative_checks or [],
            missing_checks=missing_checks or [],
            confidence=max(
                0.0,
                min(float(confidence), 1.0),
            ),
            rule_version=self.RULE_VERSION,
        )

    def _find(
        self,
        text: str,
        patterns: list,
        category: str,
    ) -> list:
        original = str(text or "").strip()

        if not original:
            return []

        normalized = self.analyzer.normalize(
            original
        )

        return self.analyzer._find_matches(
            original=original,
            normalized=normalized,
            patterns=patterns,
            category=category,
        )

    @staticmethod
    def _response_evidence(
        ai_response: str,
        *,
        limit: int = 220,
    ) -> list[str]:
        """Conserva un fragmento de la respuesta de la IA como evidencia."""
        cleaned = " ".join(str(ai_response or "").split())
        if not cleaned:
            return []
        return [cleaned[:limit]]

    @staticmethod
    def _evidence(
        matches: list,
    ) -> list[str]:
        values: list[str] = []

        for match in matches:
            evidence = str(
                getattr(match, "evidence", "")
            ).strip()

            if evidence:
                values.append(evidence)

        return EmpathyRules._unique(values)

    @staticmethod
    def _emotion_evidence(
        emotion_analysis: object,
    ) -> list[str]:
        values: list[str] = []

        ai_profile = getattr(
            emotion_analysis,
            "ai_profile",
            None,
        )

        if ai_profile is None:
            return values

        evidence_by_emotion = getattr(
            ai_profile,
            "evidence_by_emotion",
            {},
        )

        for items in evidence_by_emotion.values():
            values.extend(items)

        return EmpathyRules._unique(values)

    @staticmethod
    def _unique(
        values: list[str],
    ) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for value in values:
            item = str(value).strip()

            if not item or item in seen:
                continue

            cleaned.append(item)
            seen.add(item)

        return cleaned

    @staticmethod
    def _normalize_code(
        indicator_code: str,
    ) -> str:
        return str(
            indicator_code
        ).strip().upper()


# =============================================================
# INSTANCIA REUTILIZABLE
# =============================================================

empathy_rules = EmpathyRules()


# =============================================================
# CONEXIÓN EM1–EM13 CON EL RULE REGISTRY
# =============================================================
#
# Estas funciones son deliberadamente delgadas:
# el razonamiento vive dentro de EmpathyRules y el decorador las
# registra como las reglas oficiales de cada indicador.
# =============================================================


@indicator_rule("EM1")
def evaluate_em1(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM1",
        context,
        turn_number,
    )


@indicator_rule("EM2")
def evaluate_em2(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM2",
        context,
        turn_number,
    )


@indicator_rule("EM3")
def evaluate_em3(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM3",
        context,
        turn_number,
    )


@indicator_rule("EM4")
def evaluate_em4(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM4",
        context,
        turn_number,
    )


@indicator_rule("EM5")
def evaluate_em5(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM5",
        context,
        turn_number,
    )


@indicator_rule("EM6")
def evaluate_em6(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM6",
        context,
        turn_number,
    )


@indicator_rule("EM7")
def evaluate_em7(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM7",
        context,
        turn_number,
    )


@indicator_rule("EM8")
def evaluate_em8(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM8",
        context,
        turn_number,
    )


@indicator_rule("EM9")
def evaluate_em9(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM9",
        context,
        turn_number,
    )


@indicator_rule("EM10")
def evaluate_em10(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM10",
        context,
        turn_number,
    )


@indicator_rule("EM11")
def evaluate_em11(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM11",
        context,
        turn_number,
    )


@indicator_rule("EM12")
def evaluate_em12(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM12",
        context,
        turn_number,
    )


@indicator_rule("EM13")
def evaluate_em13(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return empathy_rules.evaluate(
        "EM13",
        context,
        turn_number,
    )
