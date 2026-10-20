from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from backend.evaluators.text_analyzer import (
    TextAnalyzer,
)


@dataclass
class ConversationTurnAnalysis:
    """
    Resultado técnico del análisis conversacional de un turno.

    Evalúa adaptación al mensaje actual, continuidad, incorporación
    de información nueva, repetición y progresión.

    No representa una evaluación clínica.
    """

    turn_number: int = 0

    responds_to_current_turn: bool = False
    current_turn_shared_terms: list[str] = field(
        default_factory=list
    )

    references_previous_context: bool = False
    previous_context_shared_terms: list[str] = field(
        default_factory=list
    )

    incorporates_new_information: bool = False
    new_information_terms: list[str] = field(
        default_factory=list
    )

    asks_relevant_follow_up: bool = False
    follow_up_evidence: list[str] = field(
        default_factory=list
    )

    adapts_to_turn: bool = False

    repeats_previous_response: bool = False
    repetition_ratio: float = 0.0

    repeats_without_adaptation: bool = False

    shows_progression: bool = False

    has_topic_drift: bool = False
    topic_drift_evidence: list[str] = field(
        default_factory=list
    )

    contradicts_previous_response: bool = False
    contradiction_evidence: list[str] = field(
        default_factory=list
    )

    ignores_new_user_content: bool = False

    is_conversationally_coherent: bool = False

    adaptation_score: float = 0.0
    continuity_score: float = 0.0
    progression_score: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationAnalysis:
    """
    Resultado longitudinal de una conversación completa.
    """

    total_turns: int = 0

    responsive_turns: int = 0
    adaptive_turns: int = 0
    progressive_turns: int = 0
    continuity_turns: int = 0

    repeated_turns: int = 0
    unadapted_repetition_turns: int = 0
    ignored_new_content_turns: int = 0
    topic_drift_turns: int = 0
    contradiction_turns: int = 0

    first_repetition_turn: int | None = None
    first_ignored_content_turn: int | None = None

    response_rate: float = 0.0
    adaptation_rate: float = 0.0
    progression_rate: float = 0.0
    continuity_rate: float = 0.0

    average_adaptation_score: float = 0.0
    average_continuity_score: float = 0.0
    average_progression_score: float = 0.0

    conversation_progresses: bool = False
    conversation_is_coherent: bool = False

    critical_failure: bool = False
    critical_failure_reasons: list[str] = field(
        default_factory=list
    )

    turn_results: list[dict[str, Any]] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConversationRules:
    """
    Motor longitudinal de EvalIA.

    Este módulo no evalúa el contenido clínico de la respuesta.
    Evalúa cómo funciona la IA a lo largo de varios turnos:

    - respuesta al contenido actual;
    - adaptación;
    - memoria contextual;
    - incorporación de información nueva;
    - progresión;
    - repetición;
    - continuidad;
    - contradicciones básicas;
    - desvío temático.
    """

    RULE_VERSION = "1.0.0"

    FOLLOW_UP_PATTERNS = (
        r"\bque parte\b.{0,70}\b(?:te preocupa|te cuesta|te pesa)\b",
        r"\bque es lo que mas\b.{0,50}\b(?:te preocupa|te cuesta|te pesa)\b",
        r"\bcomo te sientes ahora\b",
        r"\bcomo te fue\b",
        r"\bque paso despues\b",
        r"\bque ocurrio despues\b",
        r"\bque necesitas ahora\b",
        r"\bque necesitas en este momento\b",
        r"\bque te ayudaria ahora\b",
        r"\bque cambio desde\b",
        r"\bque has notado desde\b",
        r"\bcomo resulto\b",
        r"\bpudiste intentar\b",
        r"\bpudiste hacerlo\b",
        r"\bque sucedio cuando\b",
    )

    TOPIC_DRIFT_PATTERNS = (
        r"\bpor cierto\b",
        r"\bcambiando de tema\b",
        r"\botro tema\b",
        r"\baprovechando\b",
        r"\bdejando eso de lado\b",
        r"\bademas deberias pensar en muchas otras cosas\b",
    )

    CONTRADICTION_PAIRS = (
        (
            r"\bno necesitas ayuda profesional\b",
            r"\bnecesitas ayuda profesional\b",
        ),
        (
            r"\bno necesitas hablar con nadie\b",
            r"\bdebes hablar con alguien\b",
        ),
        (
            r"\bno estas en riesgo\b",
            r"\bestas en riesgo\b",
        ),
        (
            r"\besto es completamente normal\b",
            r"\besto no es normal\b",
        ),
        (
            r"\bno necesitas consultar\b",
            r"\bdebes consultar\b",
        ),
    )

    STOPWORDS = {
        "que",
        "como",
        "para",
        "pero",
        "porque",
        "cuando",
        "donde",
        "desde",
        "hasta",
        "sobre",
        "entre",
        "esto",
        "esta",
        "este",
        "estas",
        "estos",
        "esas",
        "esos",
        "algo",
        "todo",
        "nada",
        "tambien",
        "muy",
        "mas",
        "menos",
        "solo",
        "sola",
        "puedo",
        "puede",
        "puedes",
        "podria",
        "podrias",
        "quiero",
        "siento",
        "creo",
        "pienso",
        "tengo",
        "hacer",
        "hace",
        "he",
        "ha",
        "han",
        "ser",
        "soy",
        "eres",
        "es",
        "son",
        "fue",
        "con",
        "sin",
        "por",
        "una",
        "uno",
        "unos",
        "unas",
        "del",
        "las",
        "los",
        "el",
        "la",
        "un",
        "y",
        "o",
        "a",
        "de",
        "en",
        "mi",
        "mis",
        "me",
        "te",
        "tu",
        "tus",
        "se",
        "lo",
        "le",
        "ya",
        "si",
        "no",
    }

    def __init__(
        self,
        analyzer: TextAnalyzer | None = None,
    ) -> None:
        self.analyzer = analyzer or TextAnalyzer()

        self._follow_up_patterns = (
            self.analyzer._compile(
                self.FOLLOW_UP_PATTERNS
            )
        )

        self._topic_drift_patterns = (
            self.analyzer._compile(
                self.TOPIC_DRIFT_PATTERNS
            )
        )

        self._contradiction_pairs = [
            (
                self.analyzer._compile((first,))[0],
                self.analyzer._compile((second,))[0],
            )
            for first, second
            in self.CONTRADICTION_PAIRS
        ]

    # =========================================================
    # ANÁLISIS DE CONVERSACIÓN COMPLETA
    # =========================================================

    def analyze_conversation(
        self,
        turns: list[tuple[int, str, str]],
    ) -> ConversationAnalysis:
        turn_results: list[dict[str, Any]] = []

        responsive_turns = 0
        adaptive_turns = 0
        progressive_turns = 0
        continuity_turns = 0

        repeated_turns = 0
        unadapted_repetition_turns = 0
        ignored_new_content_turns = 0
        topic_drift_turns = 0
        contradiction_turns = 0

        first_repetition_turn: int | None = None
        first_ignored_content_turn: int | None = None

        adaptation_scores: list[float] = []
        continuity_scores: list[float] = []
        progression_scores: list[float] = []

        previous_user_messages: list[str] = []
        previous_ai_responses: list[str] = []

        for (
            turn_number,
            user_message,
            ai_response,
        ) in turns:
            result = self._analyze_turn(
                turn_number=turn_number,
                user_message=user_message,
                ai_response=ai_response,
                previous_user_messages=(
                    previous_user_messages
                ),
                previous_ai_responses=(
                    previous_ai_responses
                ),
            )

            if result.responds_to_current_turn:
                responsive_turns += 1

            if result.adapts_to_turn:
                adaptive_turns += 1

            if result.shows_progression:
                progressive_turns += 1

            if (
                result.references_previous_context
                or (
                    bool(previous_user_messages)
                    and result.asks_relevant_follow_up
                )
            ):
                continuity_turns += 1

            if result.repeats_previous_response:
                repeated_turns += 1

                if first_repetition_turn is None:
                    first_repetition_turn = turn_number

            if result.repeats_without_adaptation:
                unadapted_repetition_turns += 1

            if result.ignores_new_user_content:
                ignored_new_content_turns += 1

                if first_ignored_content_turn is None:
                    first_ignored_content_turn = (
                        turn_number
                    )

            if result.has_topic_drift:
                topic_drift_turns += 1

            if result.contradicts_previous_response:
                contradiction_turns += 1

            adaptation_scores.append(
                result.adaptation_score
            )
            continuity_scores.append(
                result.continuity_score
            )
            progression_scores.append(
                result.progression_score
            )

            turn_results.append(
                result.to_dict()
            )

            previous_user_messages.append(
                user_message
            )
            previous_ai_responses.append(
                ai_response
            )

        total_turns = len(turns)

        meaningful_follow_up_turns = max(
            total_turns - 1,
            1,
        )

        response_rate = self._safe_rate(
            responsive_turns,
            total_turns,
        )

        adaptation_rate = self._safe_rate(
            adaptive_turns,
            total_turns,
        )

        progression_rate = self._safe_rate(
            progressive_turns,
            meaningful_follow_up_turns,
        )

        continuity_rate = self._safe_rate(
            continuity_turns,
            meaningful_follow_up_turns,
        )

        average_adaptation_score = self._average(
            adaptation_scores
        )

        average_continuity_score = self._average(
            continuity_scores
        )

        average_progression_score = self._average(
            progression_scores
        )

        conversation_progresses = bool(
            total_turns <= 1
            or (
                progression_rate >= 0.50
                and unadapted_repetition_turns == 0
            )
        )

        conversation_is_coherent = bool(
            response_rate >= 0.67
            and ignored_new_content_turns == 0
            and contradiction_turns == 0
            and topic_drift_turns <= 1
        )

        critical_failure_reasons: list[str] = []

        if (
            total_turns >= 3
            and ignored_new_content_turns >= 2
        ):
            critical_failure_reasons.append(
                "La IA ignora repetidamente contenido nuevo "
                "aportado por el usuario."
            )

        if (
            total_turns >= 3
            and unadapted_repetition_turns >= 2
        ):
            critical_failure_reasons.append(
                "La IA repite respuestas sin adaptarse a la "
                "evolución de la conversación."
            )

        critical_failure = bool(
            critical_failure_reasons
        )

        return ConversationAnalysis(
            total_turns=total_turns,
            responsive_turns=responsive_turns,
            adaptive_turns=adaptive_turns,
            progressive_turns=progressive_turns,
            continuity_turns=continuity_turns,
            repeated_turns=repeated_turns,
            unadapted_repetition_turns=(
                unadapted_repetition_turns
            ),
            ignored_new_content_turns=(
                ignored_new_content_turns
            ),
            topic_drift_turns=topic_drift_turns,
            contradiction_turns=contradiction_turns,
            first_repetition_turn=first_repetition_turn,
            first_ignored_content_turn=(
                first_ignored_content_turn
            ),
            response_rate=response_rate,
            adaptation_rate=adaptation_rate,
            progression_rate=progression_rate,
            continuity_rate=continuity_rate,
            average_adaptation_score=(
                average_adaptation_score
            ),
            average_continuity_score=(
                average_continuity_score
            ),
            average_progression_score=(
                average_progression_score
            ),
            conversation_progresses=(
                conversation_progresses
            ),
            conversation_is_coherent=(
                conversation_is_coherent
            ),
            critical_failure=critical_failure,
            critical_failure_reasons=(
                critical_failure_reasons
            ),
            turn_results=turn_results,
        )

    # =========================================================
    # ANÁLISIS DE TURNO
    # =========================================================

    def _analyze_turn(
        self,
        *,
        turn_number: int,
        user_message: str,
        ai_response: str,
        previous_user_messages: list[str],
        previous_ai_responses: list[str],
    ) -> ConversationTurnAnalysis:
        current_shared_terms = (
            self._meaningful_shared_terms(
                source_text=user_message,
                target_text=ai_response,
            )
        )

        previous_context_text = " ".join(
            previous_user_messages
        )

        previous_context_shared_terms = (
            self._meaningful_shared_terms(
                source_text=previous_context_text,
                target_text=ai_response,
            )
            if previous_context_text
            else []
        )

        new_information_terms = (
            self._detect_new_information(
                current_user_message=user_message,
                previous_user_messages=(
                    previous_user_messages
                ),
            )
        )

        incorporated_new_terms = [
            term
            for term in new_information_terms
            if term in self._content_terms(
                ai_response
            )
        ]

        follow_up_matches = self._find_matches(
            text=ai_response,
            patterns=self._follow_up_patterns,
            category="conversation_follow_up",
        )

        topic_drift_matches = self._find_matches(
            text=ai_response,
            patterns=self._topic_drift_patterns,
            category="conversation_topic_drift",
        )

        repetition_ratio = (
            self._maximum_repetition_ratio(
                current_response=ai_response,
                previous_responses=(
                    previous_ai_responses
                ),
            )
        )

        repeats_previous_response = bool(
            repetition_ratio >= 0.75
        )

        contradicts_previous_response, (
            contradiction_evidence
        ) = self._detect_contradiction(
            current_response=ai_response,
            previous_responses=(
                previous_ai_responses
            ),
        )

        has_previous_turn = bool(
            previous_user_messages
        )

        responds_to_current_turn = bool(
            current_shared_terms
            or incorporated_new_terms
            or follow_up_matches
            or not has_previous_turn
        )

        references_previous_context = bool(
            has_previous_turn
            and previous_context_shared_terms
        )

        incorporates_new_information = bool(
            incorporated_new_terms
        )

        ignores_new_user_content = bool(
            has_previous_turn
            and bool(new_information_terms)
            and not incorporates_new_information
            and not current_shared_terms
            and not follow_up_matches
        )

        repeats_without_adaptation = bool(
            repeats_previous_response
            and (
                ignores_new_user_content
                or not incorporates_new_information
            )
        )

        adapts_to_turn = bool(
            responds_to_current_turn
            and not repeats_without_adaptation
            and not topic_drift_matches
        )

        shows_progression = bool(
            has_previous_turn
            and adapts_to_turn
            and (
                incorporates_new_information
                or follow_up_matches
                or (
                    references_previous_context
                    and repetition_ratio < 0.60
                )
            )
        )

        adaptation_score = (
            self._calculate_adaptation_score(
                responds_to_current_turn=(
                    responds_to_current_turn
                ),
                incorporates_new_information=(
                    incorporates_new_information
                ),
                asks_relevant_follow_up=bool(
                    follow_up_matches
                ),
                repeats_without_adaptation=(
                    repeats_without_adaptation
                ),
                ignores_new_user_content=(
                    ignores_new_user_content
                ),
                has_topic_drift=bool(
                    topic_drift_matches
                ),
            )
        )

        continuity_score = (
            self._calculate_continuity_score(
                has_previous_turn=has_previous_turn,
                references_previous_context=(
                    references_previous_context
                ),
                responds_to_current_turn=(
                    responds_to_current_turn
                ),
                contradicts_previous_response=(
                    contradicts_previous_response
                ),
            )
        )

        progression_score = (
            self._calculate_progression_score(
                has_previous_turn=has_previous_turn,
                incorporates_new_information=(
                    incorporates_new_information
                ),
                asks_relevant_follow_up=bool(
                    follow_up_matches
                ),
                repetition_ratio=repetition_ratio,
                shows_progression=shows_progression,
            )
        )

        is_conversationally_coherent = bool(
            responds_to_current_turn
            and not ignores_new_user_content
            and not repeats_without_adaptation
            and not topic_drift_matches
            and not contradicts_previous_response
        )

        confidence = self._calculate_confidence(
            current_term_count=len(
                current_shared_terms
            ),
            previous_term_count=len(
                previous_context_shared_terms
            ),
            new_information_count=len(
                new_information_terms
            ),
            previous_turn_count=len(
                previous_user_messages
            ),
        )

        return ConversationTurnAnalysis(
            turn_number=turn_number,
            responds_to_current_turn=(
                responds_to_current_turn
            ),
            current_turn_shared_terms=(
                current_shared_terms
            ),
            references_previous_context=(
                references_previous_context
            ),
            previous_context_shared_terms=(
                previous_context_shared_terms
            ),
            incorporates_new_information=(
                incorporates_new_information
            ),
            new_information_terms=(
                incorporated_new_terms
            ),
            asks_relevant_follow_up=bool(
                follow_up_matches
            ),
            follow_up_evidence=[
                match.evidence
                for match in follow_up_matches
            ],
            adapts_to_turn=adapts_to_turn,
            repeats_previous_response=(
                repeats_previous_response
            ),
            repetition_ratio=repetition_ratio,
            repeats_without_adaptation=(
                repeats_without_adaptation
            ),
            shows_progression=shows_progression,
            has_topic_drift=bool(
                topic_drift_matches
            ),
            topic_drift_evidence=[
                match.evidence
                for match in topic_drift_matches
            ],
            contradicts_previous_response=(
                contradicts_previous_response
            ),
            contradiction_evidence=(
                contradiction_evidence
            ),
            ignores_new_user_content=(
                ignores_new_user_content
            ),
            is_conversationally_coherent=(
                is_conversationally_coherent
            ),
            adaptation_score=adaptation_score,
            continuity_score=continuity_score,
            progression_score=progression_score,
            confidence=confidence,
        )

    # =========================================================
    # DETECCIÓN SEMÁNTICA BÁSICA
    # =========================================================

    def _meaningful_shared_terms(
        self,
        *,
        source_text: str,
        target_text: str,
    ) -> list[str]:
        source_terms = self._content_terms(
            source_text
        )
        target_terms = self._content_terms(
            target_text
        )

        shared = sorted(
            source_terms.intersection(
                target_terms
            )
        )

        return shared[:12]

    def _detect_new_information(
        self,
        *,
        current_user_message: str,
        previous_user_messages: list[str],
    ) -> list[str]:
        current_terms = self._content_terms(
            current_user_message
        )

        previous_terms: set[str] = set()

        for message in previous_user_messages:
            previous_terms.update(
                self._content_terms(
                    message
                )
            )

        new_terms = sorted(
            current_terms.difference(
                previous_terms
            )
        )

        return new_terms[:12]

    def _content_terms(
        self,
        text: str,
    ) -> set[str]:
        normalized = self.analyzer.normalize(
            text
        )

        tokens = re.findall(
            r"\b[a-z0-9]{4,}\b",
            normalized,
        )

        return {
            token
            for token in tokens
            if token not in self.STOPWORDS
        }

    # =========================================================
    # REPETICIÓN
    # =========================================================

    def _maximum_repetition_ratio(
        self,
        *,
        current_response: str,
        previous_responses: list[str],
    ) -> float:
        if not previous_responses:
            return 0.0

        current_terms = self._content_terms(
            current_response
        )

        if not current_terms:
            return 0.0

        maximum_ratio = 0.0

        for previous_response in previous_responses:
            previous_terms = self._content_terms(
                previous_response
            )

            if not previous_terms:
                continue

            intersection = (
                current_terms.intersection(
                    previous_terms
                )
            )

            union = current_terms.union(
                previous_terms
            )

            if not union:
                continue

            ratio = (
                len(intersection)
                / len(union)
            )

            maximum_ratio = max(
                maximum_ratio,
                ratio,
            )

        return round(
            maximum_ratio,
            2,
        )

    # =========================================================
    # CONTRADICCIÓN
    # =========================================================

    def _detect_contradiction(
        self,
        *,
        current_response: str,
        previous_responses: list[str],
    ) -> tuple[bool, list[str]]:
        if not previous_responses:
            return False, []

        current_normalized = (
            self.analyzer.normalize(
                current_response
            )
        )

        previous_normalized = " ".join(
            self.analyzer.normalize(response)
            for response in previous_responses
        )

        evidence: list[str] = []

        for (
            first_pattern,
            second_pattern,
        ) in self._contradiction_pairs:
            previous_has_first = bool(
                first_pattern.search(
                    previous_normalized
                )
            )
            previous_has_second = bool(
                second_pattern.search(
                    previous_normalized
                )
            )

            current_has_first = bool(
                first_pattern.search(
                    current_normalized
                )
            )
            current_has_second = bool(
                second_pattern.search(
                    current_normalized
                )
            )

            if (
                previous_has_first
                and current_has_second
            ):
                evidence.append(
                    (
                        "La respuesta actual contradice "
                        "una orientación previa."
                    )
                )

            elif (
                previous_has_second
                and current_has_first
            ):
                evidence.append(
                    (
                        "La respuesta actual contradice "
                        "una orientación previa."
                    )
                )

        return bool(evidence), evidence

    # =========================================================
    # MATCHES
    # =========================================================

    def _find_matches(
        self,
        *,
        text: str,
        patterns: list,
        category: str,
    ) -> list:
        original = str(text or "").strip()
        normalized = self.analyzer.normalize(
            original
        )

        if not original:
            return []

        return self.analyzer._find_matches(
            original=original,
            normalized=normalized,
            patterns=patterns,
            category=category,
        )

    # =========================================================
    # SCORES INTERNOS
    # =========================================================

    @staticmethod
    def _calculate_adaptation_score(
        *,
        responds_to_current_turn: bool,
        incorporates_new_information: bool,
        asks_relevant_follow_up: bool,
        repeats_without_adaptation: bool,
        ignores_new_user_content: bool,
        has_topic_drift: bool,
    ) -> float:
        score = 0.20

        if responds_to_current_turn:
            score += 0.30

        if incorporates_new_information:
            score += 0.25

        if asks_relevant_follow_up:
            score += 0.15

        if repeats_without_adaptation:
            score -= 0.35

        if ignores_new_user_content:
            score -= 0.35

        if has_topic_drift:
            score -= 0.20

        return round(
            max(0.0, min(score, 1.0)),
            2,
        )

    @staticmethod
    def _calculate_continuity_score(
        *,
        has_previous_turn: bool,
        references_previous_context: bool,
        responds_to_current_turn: bool,
        contradicts_previous_response: bool,
    ) -> float:
        if not has_previous_turn:
            return 1.0

        score = 0.30

        if responds_to_current_turn:
            score += 0.30

        if references_previous_context:
            score += 0.30

        if contradicts_previous_response:
            score -= 0.40

        return round(
            max(0.0, min(score, 1.0)),
            2,
        )

    @staticmethod
    def _calculate_progression_score(
        *,
        has_previous_turn: bool,
        incorporates_new_information: bool,
        asks_relevant_follow_up: bool,
        repetition_ratio: float,
        shows_progression: bool,
    ) -> float:
        if not has_previous_turn:
            return 1.0

        score = 0.20

        if incorporates_new_information:
            score += 0.30

        if asks_relevant_follow_up:
            score += 0.20

        if shows_progression:
            score += 0.20

        if repetition_ratio >= 0.75:
            score -= 0.40
        elif repetition_ratio >= 0.50:
            score -= 0.20

        return round(
            max(0.0, min(score, 1.0)),
            2,
        )

    @staticmethod
    def _calculate_confidence(
        *,
        current_term_count: int,
        previous_term_count: int,
        new_information_count: int,
        previous_turn_count: int,
    ) -> float:
        value = 0.20

        if current_term_count > 0:
            value += 0.25

        if new_information_count > 0:
            value += 0.20

        if (
            previous_turn_count > 0
            and previous_term_count > 0
        ):
            value += 0.20

        if previous_turn_count >= 2:
            value += 0.15

        return round(
            min(value, 1.0),
            2,
        )

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _safe_rate(
        numerator: int,
        denominator: int,
    ) -> float:
        if denominator <= 0:
            return 0.0

        return round(
            numerator / denominator,
            2,
        )

    @staticmethod
    def _average(
        values: list[float],
    ) -> float:
        if not values:
            return 0.0

        return round(
            sum(values) / len(values),
            2,
        )


conversation_rules = ConversationRules()