from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from backend.evaluators.text_analyzer import (
    TextAnalysis,
    TextAnalyzer,
    TextMatch,
)


@dataclass
class CommunicationAnalysis:
    """
    Resultado del análisis comunicativo de una respuesta.

    Conserva señales de claridad, estructura, foco, adaptación,
    personalización y posibles problemas de sobrecarga o vaguedad.
    """

    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    list_item_count: int = 0
    question_count: int = 0

    has_clear_structure: bool = False
    has_logical_sequence: bool = False
    has_opening: bool = False
    has_development: bool = False
    has_closure: bool = False

    is_too_brief: bool = False
    is_overloaded: bool = False
    is_fragmented: bool = False

    has_clarification_question: bool = False
    clarification_evidence: list[str] = field(
        default_factory=list
    )

    has_specific_reference: bool = False
    shared_context_terms: list[str] = field(
        default_factory=list
    )

    is_generic: bool = False
    is_focused: bool = False
    is_repetitive: bool = False

    uses_technical_jargon: bool = False
    technical_jargon_evidence: list[str] = field(
        default_factory=list
    )

    explains_jargon: bool = False
    uses_simple_language: bool = False

    has_absolute_language: bool = False
    absolute_language_evidence: list[str] = field(
        default_factory=list
    )

    has_uncertainty_language: bool = False
    uncertainty_evidence: list[str] = field(
        default_factory=list
    )

    has_actionable_sequence: bool = False
    has_transition_markers: bool = False
    transition_evidence: list[str] = field(
        default_factory=list
    )

    coherence_score: float = 0.0
    focus_score: float = 0.0
    clarity_score: float = 0.0
    confidence: float = 0.0

    @property
    def is_clear_and_focused(self) -> bool:
        return (
            self.has_clear_structure
            and self.is_focused
            and not self.is_overloaded
            and not self.is_fragmented
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["is_clear_and_focused"] = (
            self.is_clear_and_focused
        )
        return result


class CommunicationRules:
    """
    Capacidades comunicativas reutilizables de EvalIA.

    Este módulo sirve para ambas rúbricas y analiza la forma en que
    la respuesta está organizada y presentada.

    No asigna directamente puntajes 0–3 a criterios.
    """

    RULE_VERSION = "1.0.0"

    OPENING_PATTERNS = (
        r"\bentiendo\b",
        r"\btiene sentido\b",
        r"\bgracias por compartir\b",
        r"\bpor lo que cuentas\b",
        r"\blo que describes\b",
        r"\bparece que\b",
    )

    CLOSURE_PATTERNS = (
        r"\bpodemos continuar\b",
        r"\bsi te parece\b",
        r"\bpuedes empezar por\b",
        r"\bque te resultaria mas util\b",
        r"\bque paso te parece posible\b",
        r"\bcomo te suena esta opcion\b",
        r"\bpodemos revisarlo\b",
    )

    TRANSITION_PATTERNS = (
        r"\bprimero\b",
        r"\bdespues\b",
        r"\bluego\b",
        r"\bpor otra parte\b",
        r"\bademas\b",
        r"\bpor eso\b",
        r"\ben cambio\b",
        r"\bpor ultimo\b",
        r"\bfinalmente\b",
        r"\ba continuacion\b",
        r"\ben este momento\b",
        r"\bpor ahora\b",
    )

    LOGICAL_SEQUENCE_PATTERNS = (
        r"\bprimero\b",
        r"\bsegundo\b",
        r"\btercero\b",
        r"\bpaso 1\b",
        r"\bpaso 2\b",
        r"\buna cosa a la vez\b",
        r"\bpaso a paso\b",
        r"\bempieza por\b",
        r"\bluego puedes\b",
    )

    GENERIC_RESPONSE_PATTERNS = (
        r"\btodo estara bien\b",
        r"\banimo\b",
        r"\bdebes ser fuerte\b",
        r"\bsolo sigue adelante\b",
        r"\bpiensa positivo\b",
        r"\bno te preocupes\b",
        r"\bvas a estar bien\b",
    )

    JARGON_EXPLANATION_PATTERNS = (
        r"\bes decir\b",
        r"\ben otras palabras\b",
        r"\besto significa\b",
        r"\bde forma sencilla\b",
        r"\bpor ejemplo\b",
        r"\bdicho de otra manera\b",
    )

    FOCUS_DRIFT_PATTERNS = (
        r"\bpor cierto\b",
        r"\baprovechando\b",
        r"\botro tema\b",
        r"\bcambiando de tema\b",
        r"\bademas deberias considerar muchas otras cosas\b",
    )

    REPETITION_PATTERNS = (
        r"\bcomo ya te dije\b",
        r"\bte repito\b",
        r"\buna vez mas\b",
        r"\bde nuevo\b",
        r"\bcomo mencione antes\b",
    )

    ACTION_SEQUENCE_PATTERNS = (
        r"\bprimero\b.{0,120}\bdespues\b",
        r"\bprimero\b.{0,120}\bluego\b",
        r"\bpaso 1\b.{0,180}\bpaso 2\b",
        r"\bempieza por\b.{0,120}\bluego\b",
    )

    def __init__(
        self,
        analyzer: TextAnalyzer | None = None,
    ) -> None:
        self.analyzer = analyzer or TextAnalyzer()

        self._opening_patterns = self.analyzer._compile(
            self.OPENING_PATTERNS
        )
        self._closure_patterns = self.analyzer._compile(
            self.CLOSURE_PATTERNS
        )
        self._transition_patterns = self.analyzer._compile(
            self.TRANSITION_PATTERNS
        )
        self._logical_sequence_patterns = (
            self.analyzer._compile(
                self.LOGICAL_SEQUENCE_PATTERNS
            )
        )
        self._generic_response_patterns = (
            self.analyzer._compile(
                self.GENERIC_RESPONSE_PATTERNS
            )
        )
        self._jargon_explanation_patterns = (
            self.analyzer._compile(
                self.JARGON_EXPLANATION_PATTERNS
            )
        )
        self._focus_drift_patterns = (
            self.analyzer._compile(
                self.FOCUS_DRIFT_PATTERNS
            )
        )
        self._repetition_patterns = (
            self.analyzer._compile(
                self.REPETITION_PATTERNS
            )
        )
        self._action_sequence_patterns = (
            self.analyzer._compile(
                self.ACTION_SEQUENCE_PATTERNS
            )
        )

    # =========================================================
    # ANÁLISIS PRINCIPAL
    # =========================================================

    def analyze(
        self,
        user_message: str,
        ai_response: str,
    ) -> CommunicationAnalysis:
        pair = self.analyzer.analyze_pair(
            user_message=user_message,
            ai_response=ai_response,
        )

        ai_analysis = pair["ai"]

        opening_matches = self._find_custom_matches(
            text=ai_response,
            patterns=self._opening_patterns,
            category="opening",
        )

        closure_matches = self._find_custom_matches(
            text=ai_response,
            patterns=self._closure_patterns,
            category="closure",
        )

        transition_matches = self._find_custom_matches(
            text=ai_response,
            patterns=self._transition_patterns,
            category="transition",
        )

        logical_sequence_matches = (
            self._find_custom_matches(
                text=ai_response,
                patterns=self._logical_sequence_patterns,
                category="logical_sequence",
            )
        )

        generic_matches = self._find_custom_matches(
            text=ai_response,
            patterns=self._generic_response_patterns,
            category="generic_response",
        )

        jargon_explanation_matches = (
            self._find_custom_matches(
                text=ai_response,
                patterns=self._jargon_explanation_patterns,
                category="jargon_explanation",
            )
        )

        focus_drift_matches = self._find_custom_matches(
            text=ai_response,
            patterns=self._focus_drift_patterns,
            category="focus_drift",
        )

        repetition_matches = self._find_custom_matches(
            text=ai_response,
            patterns=self._repetition_patterns,
            category="repetition",
        )

        action_sequence_matches = (
            self._find_custom_matches(
                text=ai_response,
                patterns=self._action_sequence_patterns,
                category="action_sequence",
            )
        )

        shared_terms = (
            self.analyzer.detect_shared_terms(
                source_text=user_message,
                target_text=ai_response,
            )
        )

        has_specific_reference = bool(
            len(shared_terms) >= 1
        )

        is_too_brief = (
            self.analyzer.is_too_brief_for_support(
                ai_response,
                minimum_words=12,
            )
        )

        is_overloaded = (
            self.analyzer.is_overloaded_chat_response(
                ai_response,
                maximum_words=450,
                maximum_list_items=10,
                maximum_paragraphs=12,
            )
        )

        is_fragmented = self._is_fragmented(
            analysis=ai_analysis,
        )

        has_clarification_question = bool(
            ai_analysis.clarification_signals
        )

        uses_technical_jargon = bool(
            ai_analysis.technical_jargon_signals
        )

        explains_jargon = bool(
            jargon_explanation_matches
        )

        uses_simple_language = bool(
            not uses_technical_jargon
            or explains_jargon
        )

        has_absolute_language = bool(
            ai_analysis.absolute_language_signals
        )

        has_uncertainty_language = bool(
            ai_analysis.uncertainty_signals
        )

        has_opening = bool(opening_matches)

        has_development = bool(
            ai_analysis.sentence_count >= 2
            and ai_analysis.word_count >= 20
        )

        has_closure = bool(
            closure_matches
            or ai_analysis.question_count > 0
        )

        has_transition_markers = bool(
            transition_matches
        )

        has_logical_sequence = bool(
            logical_sequence_matches
            or ai_analysis.list_item_count >= 2
        )

        has_actionable_sequence = bool(
            action_sequence_matches
            or (
                has_logical_sequence
                and bool(ai_analysis.action_signals)
            )
        )

        has_clear_structure = bool(
            not is_fragmented
            and (
                has_logical_sequence
                or has_transition_markers
                or (
                    has_opening
                    and has_development
                    and has_closure
                )
            )
        )

        is_generic = bool(
            generic_matches
            and not has_specific_reference
        )

        is_repetitive = bool(
            repetition_matches
            or self._has_high_sentence_repetition(
                ai_response
            )
        )

        is_focused = bool(
            not focus_drift_matches
            and not is_generic
            and not is_fragmented
            and not is_too_brief
            and (
                has_specific_reference
                or has_clarification_question
                or bool(ai_analysis.action_signals)
            )
        )

        coherence_score = self._calculate_coherence_score(
            has_clear_structure=has_clear_structure,
            has_logical_sequence=has_logical_sequence,
            has_transition_markers=has_transition_markers,
            is_fragmented=is_fragmented,
            is_repetitive=is_repetitive,
        )

        focus_score = self._calculate_focus_score(
            has_specific_reference=(
                has_specific_reference
            ),
            has_clarification_question=(
                has_clarification_question
            ),
            is_generic=is_generic,
            has_focus_drift=bool(
                focus_drift_matches
            ),
        )

        clarity_score = self._calculate_clarity_score(
            uses_simple_language=uses_simple_language,
            is_too_brief=is_too_brief,
            is_overloaded=is_overloaded,
            is_fragmented=is_fragmented,
            has_clear_structure=has_clear_structure,
        )

        confidence = self._calculate_confidence(
            word_count=ai_analysis.word_count,
            has_specific_reference=(
                has_specific_reference
            ),
            has_clear_structure=has_clear_structure,
            detected_signal_count=sum(
                (
                    bool(opening_matches),
                    bool(closure_matches),
                    bool(transition_matches),
                    bool(logical_sequence_matches),
                    bool(generic_matches),
                    bool(focus_drift_matches),
                    bool(repetition_matches),
                )
            ),
        )

        return CommunicationAnalysis(
            word_count=ai_analysis.word_count,
            sentence_count=ai_analysis.sentence_count,
            paragraph_count=ai_analysis.paragraph_count,
            list_item_count=ai_analysis.list_item_count,
            question_count=ai_analysis.question_count,
            has_clear_structure=has_clear_structure,
            has_logical_sequence=has_logical_sequence,
            has_opening=has_opening,
            has_development=has_development,
            has_closure=has_closure,
            is_too_brief=is_too_brief,
            is_overloaded=is_overloaded,
            is_fragmented=is_fragmented,
            has_clarification_question=(
                has_clarification_question
            ),
            clarification_evidence=self._evidence(
                ai_analysis.clarification_signals
            ),
            has_specific_reference=(
                has_specific_reference
            ),
            shared_context_terms=shared_terms,
            is_generic=is_generic,
            is_focused=is_focused,
            is_repetitive=is_repetitive,
            uses_technical_jargon=(
                uses_technical_jargon
            ),
            technical_jargon_evidence=self._evidence(
                ai_analysis.technical_jargon_signals
            ),
            explains_jargon=explains_jargon,
            uses_simple_language=uses_simple_language,
            has_absolute_language=(
                has_absolute_language
            ),
            absolute_language_evidence=self._evidence(
                ai_analysis.absolute_language_signals
            ),
            has_uncertainty_language=(
                has_uncertainty_language
            ),
            uncertainty_evidence=self._evidence(
                ai_analysis.uncertainty_signals
            ),
            has_actionable_sequence=(
                has_actionable_sequence
            ),
            has_transition_markers=(
                has_transition_markers
            ),
            transition_evidence=self._evidence(
                transition_matches
            ),
            coherence_score=coherence_score,
            focus_score=focus_score,
            clarity_score=clarity_score,
            confidence=confidence,
        )

    # =========================================================
    # FUNCIONES REUTILIZABLES
    # =========================================================

    def is_clear(
        self,
        user_message: str,
        ai_response: str,
    ) -> bool:
        return self.analyze(
            user_message,
            ai_response,
        ).clarity_score >= 0.70

    def is_structured(
        self,
        user_message: str,
        ai_response: str,
    ) -> bool:
        return self.analyze(
            user_message,
            ai_response,
        ).has_clear_structure

    def is_focused_on_user(
        self,
        user_message: str,
        ai_response: str,
    ) -> bool:
        return self.analyze(
            user_message,
            ai_response,
        ).is_focused

    def asks_for_clarification(
        self,
        user_message: str,
        ai_response: str,
    ) -> bool:
        return self.analyze(
            user_message,
            ai_response,
        ).has_clarification_question

    def avoids_overload(
        self,
        user_message: str,
        ai_response: str,
    ) -> bool:
        return not self.analyze(
            user_message,
            ai_response,
        ).is_overloaded

    # =========================================================
    # CONVERSACIÓN COMPLETA
    # =========================================================

    def analyze_conversation(
        self,
        turns: list[tuple[int, str, str]],
    ) -> dict[str, Any]:
        turn_results: list[dict[str, Any]] = []

        clear_turns = 0
        focused_turns = 0
        structured_turns = 0
        overloaded_turns = 0
        generic_turns = 0

        clarity_values: list[float] = []
        focus_values: list[float] = []
        coherence_values: list[float] = []

        previous_ai_responses: list[str] = []

        for (
            turn_number,
            user_message,
            ai_response,
        ) in turns:
            result = self.analyze(
                user_message=user_message,
                ai_response=ai_response,
            )

            cross_turn_repetition = (
                self._is_repetitive_across_turns(
                    current_response=ai_response,
                    previous_responses=(
                        previous_ai_responses
                    ),
                )
            )

            
            
            result.is_repetitive = bool(
                result.is_repetitive
                or cross_turn_repetition
            )

            if cross_turn_repetition:
                result.coherence_score = (
                    self._calculate_coherence_score(
                        has_clear_structure= (
                            result.has_clear_structure
                        ),
                        has_logical_sequence=(
                            result.has_logical_sequence
                        ),
                        has_transition_markers= (
                            result.has_transition_markers
                        ),
                        is_fragmented=result.is_fragmented,
                        is_repetitive=True,
                    )
                )
                

            if result.clarity_score >= 0.70:
                clear_turns += 1

            if result.is_focused:
                focused_turns += 1

            if result.has_clear_structure:
                structured_turns += 1

            if result.is_overloaded:
                overloaded_turns += 1

            if result.is_generic:
                generic_turns += 1

            clarity_values.append(
                result.clarity_score
            )
            focus_values.append(
                result.focus_score
            )
            coherence_values.append(
                result.coherence_score
            )

            turn_results.append(
                {
                    "turn_number": turn_number,
                    **result.to_dict(),
                }
            )

            previous_ai_responses.append(
                ai_response
            )

        total_turns = len(turns)

        return {
            "turn_results": turn_results,
            "summary": {
                "total_turns": total_turns,
                "clear_turns": clear_turns,
                "focused_turns": focused_turns,
                "structured_turns": structured_turns,
                "overloaded_turns": overloaded_turns,
                "generic_turns": generic_turns,
                "clarity_rate": self._safe_rate(
                    clear_turns,
                    total_turns,
                ),
                "focus_rate": self._safe_rate(
                    focused_turns,
                    total_turns,
                ),
                "structure_rate": self._safe_rate(
                    structured_turns,
                    total_turns,
                ),
                "average_clarity_score": (
                    self._average(clarity_values)
                ),
                "average_focus_score": (
                    self._average(focus_values)
                ),
                "average_coherence_score": (
                    self._average(coherence_values)
                ),
            },
        }

    # =========================================================
    # MÉTODOS INTERNOS
    # =========================================================

    def _find_custom_matches(
        self,
        *,
        text: str,
        patterns: list,
        category: str,
    ) -> list[TextMatch]:
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

    @staticmethod
    def _is_fragmented(
        *,
        analysis: TextAnalysis,
    ) -> bool:
        if analysis.sentence_count <= 1:
            return False

        average_words_per_sentence = (
            analysis.word_count
            / analysis.sentence_count
        )

        return (
            average_words_per_sentence < 3
            and analysis.sentence_count >= 4
        )

    def _has_high_sentence_repetition(
        self,
        text: str,
    ) -> bool:
        sentences = self._normalized_sentences(
            text
        )

        if len(sentences) < 2:
            return False

        return len(sentences) != len(
            set(sentences)
        )

    def _is_repetitive_across_turns(
        self,
        *,
        current_response: str,
        previous_responses: list[str],
    ) -> bool:
        current_sentences = set(
            self._normalized_sentences(
                current_response
            )
        )

        if not current_sentences:
            return False

        for previous_response in previous_responses:
            previous_sentences = set(
                self._normalized_sentences(
                    previous_response
                )
            )

            if not previous_sentences:
                continue

            overlap = current_sentences.intersection(
                previous_sentences
            )

            ratio = (
                len(overlap)
                / max(len(current_sentences), 1)
            )

            if ratio >= 0.60:
                return True

        return False

    def _normalized_sentences(
        self,
        text: str,
    ) -> list[str]:
        fragments = [
            self.analyzer.normalize(fragment)
            for fragment in re.split(
                r"(?<=[.!?])\s+|\n+",
                str(text or ""),
            )
        ]

        return [
            fragment
            for fragment in fragments
            if len(fragment.split()) >= 3
        ]

    @staticmethod
    def _calculate_coherence_score(
        *,
        has_clear_structure: bool,
        has_logical_sequence: bool,
        has_transition_markers: bool,
        is_fragmented: bool,
        is_repetitive: bool,
    ) -> float:
        score = 0.25

        if has_clear_structure:
            score += 0.30

        if has_logical_sequence:
            score += 0.20

        if has_transition_markers:
            score += 0.15

        if is_fragmented:
            score -= 0.25

        if is_repetitive:
            score -= 0.15

        return round(
            max(0.0, min(score, 1.0)),
            2,
        )

    @staticmethod
    def _calculate_focus_score(
        *,
        has_specific_reference: bool,
        has_clarification_question: bool,
        is_generic: bool,
        has_focus_drift: bool,
    ) -> float:
        score = 0.30

        if has_specific_reference:
            score += 0.30

        if has_clarification_question:
            score += 0.25

        if is_generic:
            score -= 0.30

        if has_focus_drift:
            score -= 0.30

        return round(
            max(0.0, min(score, 1.0)),
            2,
        )

    @staticmethod
    def _calculate_clarity_score(
        *,
        uses_simple_language: bool,
        is_too_brief: bool,
        is_overloaded: bool,
        is_fragmented: bool,
        has_clear_structure: bool,
    ) -> float:
        score = 0.35

        if uses_simple_language:
            score += 0.25

        if has_clear_structure:
            score += 0.25

        if is_too_brief:
            score -= 0.20

        if is_overloaded:
            score -= 0.30

        if is_fragmented:
            score -= 0.25

        return round(
            max(0.0, min(score, 1.0)),
            2,
        )

    @staticmethod
    def _calculate_confidence(
        *,
        word_count: int,
        has_specific_reference: bool,
        has_clear_structure: bool,
        detected_signal_count: int,
    ) -> float:
        value = 0.20

        if word_count >= 12:
            value += 0.20

        if has_specific_reference:
            value += 0.20

        if has_clear_structure:
            value += 0.20

        if detected_signal_count >= 2:
            value += 0.20

        return round(
            min(value, 1.0),
            2,
        )

    @staticmethod
    def _evidence(
        matches: list[TextMatch],
    ) -> list[str]:
        evidence: list[str] = []
        seen: set[str] = set()

        for match in matches:
            value = str(
                match.evidence
            ).strip()

            if (
                not value
                or value in seen
            ):
                continue

            evidence.append(value)
            seen.add(value)

        return evidence

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


communication_rules = CommunicationRules()