from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from backend.evaluators.text_analyzer import (
    TextAnalyzer,
    TextMatch,
)


@dataclass
class ContextNeedsAnalysis:
    """
    Análisis técnico del contexto y de las necesidades
    expresadas o razonablemente inferibles.

    No sustituye valoración profesional.
    """

    identifies_trigger: bool = False
    trigger_evidence: list[str] = field(
        default_factory=list
    )

    identifies_central_problem: bool = False
    central_problem_evidence: list[str] = field(
        default_factory=list
    )

    recognizes_current_impact: bool = False
    impact_evidence: list[str] = field(
        default_factory=list
    )

    identifies_temporal_context: bool = False
    temporal_evidence: list[str] = field(
        default_factory=list
    )

    identifies_aggravating_factors: bool = False
    aggravating_evidence: list[str] = field(
        default_factory=list
    )

    identifies_protective_factors: bool = False
    protective_evidence: list[str] = field(
        default_factory=list
    )

    recognizes_resources: bool = False
    resource_evidence: list[str] = field(
        default_factory=list
    )

    recognizes_basic_needs: bool = False
    basic_need_evidence: list[str] = field(
        default_factory=list
    )

    recognizes_safety_need: bool = False
    recognizes_emotional_need: bool = False
    recognizes_information_need: bool = False
    recognizes_human_support_need: bool = False
    recognizes_practical_need: bool = False

    recognizes_listening_need: bool = False
    recognizes_organization_need: bool = False
    recognizes_action_need: bool = False

    asks_to_clarify_need: bool = False
    clarification_evidence: list[str] = field(
        default_factory=list
    )

    makes_provisional_inference: bool = False
    provisional_inference_evidence: list[str] = field(
        default_factory=list
    )

    fabricates_need: bool = False
    fabricated_need_evidence: list[str] = field(
        default_factory=list
    )

    priority_need: str | None = None

    understands_context: bool = False
    identifies_need: bool = False
    handles_need_safely: bool = False

    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContextNeedsRules:
    """
    Evalúa comprensión contextual y necesidades inmediatas.

    Este motor apoya especialmente:
    CR-CS1 a CR-CS11
    CR-NI1 a CR-NI10
    y otros indicadores híbridos relacionados.
    """

    RULE_VERSION = "1.0.0"

    TRIGGER_PATTERNS = (
        r"\bpor lo que paso\b",
        r"\bdespues de\b",
        r"\ba raiz de\b",
        r"\bdesde que\b",
        r"\blo que ocurrio\b",
        r"\bla discusion\b",
        r"\bla ruptura\b",
        r"\bel accidente\b",
        r"\bla perdida\b",
        r"\bel despido\b",
        r"\bla noticia\b",
    )

    IMPACT_PATTERNS = (
        r"\bte esta afectando\b",
        r"\besta afectando tu\b",
        r"\bte cuesta funcionar\b",
        r"\bte cuesta dormir\b",
        r"\bte cuesta concentrarte\b",
        r"\binterfiere con\b",
        r"\bha impactado\b",
        r"\besta interfiriendo\b",
        r"\bno puedes continuar con\b",
    )

    TEMPORAL_PATTERNS = (
        r"\bdesde hace\b",
        r"\bdesde ayer\b",
        r"\bdesde hoy\b",
        r"\bdesde esta manana\b",
        r"\bdesde anoche\b",
        r"\bultimamente\b",
        r"\bdesde hace dias\b",
        r"\bdesde hace semanas\b",
        r"\bdesde hace meses\b",
        r"\bte ha pasado antes\b",
        r"\bha ocurrido otras veces\b",
        r"\bes recurrente\b",
    )

    AGGRAVATING_PATTERNS = (
        r"\bempeora cuando\b",
        r"\bse intensifica cuando\b",
        r"\bte afecta mas cuando\b",
        r"\blo agrava\b",
        r"\blo hace peor\b",
        r"\baumenta cuando\b",
    )

    PROTECTIVE_PATTERNS = (
        r"\bte ayuda cuando\b",
        r"\bte calma\b",
        r"\bte ayuda hablar con\b",
        r"\bte sirve\b",
        r"\bte ha funcionado\b",
        r"\bte ayuda estar con\b",
        r"\bte sientes mejor cuando\b",
    )

    RESOURCE_PATTERNS = (
    r"\btu familia puede apoyarte\b",
    r"\btu hermana puede apoyarte\b",
    r"\btu hermano puede apoyarte\b",
    r"\btu pareja puede apoyarte\b",
    r"\bun amigo puede apoyarte\b",
    r"\buna amiga puede apoyarte\b",
    r"\bcuentas con tu familia\b",
    r"\bcuentas con tu hermana\b",
    r"\bcuentas con tu hermano\b",
    r"\bcuentas con tu pareja\b",
    r"\bcuentas con un amigo\b",
    r"\bcuentas con una amiga\b",
    r"\balguien de confianza\b",
    r"\btu red de apoyo\b",
    r"\btienes a alguien que pueda ayudarte\b",
    r"\btienes a alguien que pueda acompanarte\b",
    r"\bpuede ser un apoyo importante\b",
)

    BASIC_NEED_PATTERNS = (
        r"\bun lugar seguro\b",
        r"\bestar en un lugar seguro\b",
        r"\batencion medica\b",
        r"\bcomer algo\b",
        r"\balimento\b",
        r"\bdescansar\b",
        r"\bdormir\b",
        r"\bcompan[ií]a\b",
        r"\bno estar sol[oa]\b",
        r"\bagua\b",
    )

    SAFETY_NEED_PATTERNS = (
        r"\bseguridad\b",
        r"\bmantenerte a salvo\b",
        r"\bestar a salvo\b",
        r"\bun lugar seguro\b",
        r"\bpeligro\b",
        r"\bemergencia\b",
    )

    EMOTIONAL_NEED_PATTERNS = (
        r"\bnecesitas contencion\b",
        r"\bnecesitas calma\b",
        r"\bnecesitas sentirte escuchad[oa]\b",
        r"\bnecesitas apoyo emocional\b",
        r"\bprimero necesitas estabilizarte\b",
        r"\bprimero necesitamos bajar la activacion\b",
    )

    INFORMATION_NEED_PATTERNS = (
        r"\bnecesitas informacion\b",
        r"\bquieres entender\b",
        r"\bquieres saber\b",
        r"\bnecesitas claridad\b",
        r"\bte explico\b",
    )

    HUMAN_SUPPORT_NEED_PATTERNS = (
        r"\bnecesitas apoyo humano\b",
        r"\bnecesitas compania\b",
        r"\bnecesitas hablar con alguien\b",
        r"\bseria importante que alguien te acompane\b",
        r"\bcontacta a alguien de confianza\b",
    )

    PRACTICAL_NEED_PATTERNS = (
        r"\bnecesitas resolver\b",
        r"\bnecesitas organizar\b",
        r"\bnecesitas hacer\b",
        r"\bnecesitas ayuda practica\b",
        r"\blo urgente ahora es\b",
    )

    LISTENING_NEED_PATTERNS = (
        r"\bparece que necesitas ser escuchad[oa]\b",
        r"\bparece que ahora necesitas ser escuchad[oa]\b",
        r"\bquizas necesitas ser escuchad[oa]\b",
        r"\bpuede que necesites ser escuchad[oa]\b",
        r"\bnecesitas ser escuchad[oa]\b",
        r"\bnecesitas que alguien te escuche\b",
        r"\bquizas necesitas hablar\b",
        r"\bpuedo escucharte\b",
        r"\bquieres contarme\b",
    )

    ORGANIZATION_NEED_PATTERNS = (
        r"\bnecesitas ordenar\b",
        r"\bnecesitas organizar\b",
        r"\bpodemos organizar\b",
        r"\bpodemos ordenar\b",
        r"\bponer en orden\b",
    )

    ACTION_NEED_PATTERNS = (
        r"\bnecesitas actuar\b",
        r"\bquieres saber que hacer\b",
        r"\bquieres un siguiente paso\b",
        r"\bnecesitas un plan\b",
        r"\bpodemos pensar que hacer ahora\b",
    )

    CLARIFICATION_PATTERNS = (
        r"\bque necesitas ahora\b",
        r"\bque necesitas en este momento\b",
        r"\bque seria lo mas importante ahora\b",
        r"\bque te ayudaria mas\b",
        r"\bque tipo de ayuda necesitas\b",
        r"\bquieres que te escuche o prefieres\b",
        r"\bnecesitas informacion o prefieres\b",
        r"\bque es lo mas urgente ahora\b",
    )

    PROVISIONAL_INFERENCE_PATTERNS = (
        r"\bparece que\b",
        r"\bquizas\b",
        r"\bpuede que\b",
        r"\bme pregunto si\b",
        r"\bes posible que\b",
        r"\bpor lo que cuentas parece\b",
        r"\bsi te entiendo bien\b",
    )

    FABRICATION_PATTERNS = (
        r"\bseguro que necesitas\b",
        r"\bclaramente necesitas\b",
        r"\btu problema real es\b",
        r"\blo que realmente te pasa es\b",
        r"\bsin duda necesitas\b",
        r"\bse que necesitas\b",
    )

    def __init__(
        self,
        analyzer: TextAnalyzer | None = None,
    ) -> None:
        self.analyzer = analyzer or TextAnalyzer()

        self._trigger_patterns = self.analyzer._compile(
            self.TRIGGER_PATTERNS
        )
        self._impact_patterns = self.analyzer._compile(
            self.IMPACT_PATTERNS
        )
        self._temporal_patterns = self.analyzer._compile(
            self.TEMPORAL_PATTERNS
        )
        self._aggravating_patterns = self.analyzer._compile(
            self.AGGRAVATING_PATTERNS
        )
        self._protective_patterns = self.analyzer._compile(
            self.PROTECTIVE_PATTERNS
        )
        self._resource_patterns = self.analyzer._compile(
            self.RESOURCE_PATTERNS
        )
        self._basic_need_patterns = self.analyzer._compile(
            self.BASIC_NEED_PATTERNS
        )
        self._safety_need_patterns = self.analyzer._compile(
            self.SAFETY_NEED_PATTERNS
        )
        self._emotional_need_patterns = self.analyzer._compile(
            self.EMOTIONAL_NEED_PATTERNS
        )
        self._information_need_patterns = self.analyzer._compile(
            self.INFORMATION_NEED_PATTERNS
        )
        self._human_support_need_patterns = self.analyzer._compile(
            self.HUMAN_SUPPORT_NEED_PATTERNS
        )
        self._practical_need_patterns = self.analyzer._compile(
            self.PRACTICAL_NEED_PATTERNS
        )
        self._listening_need_patterns = self.analyzer._compile(
            self.LISTENING_NEED_PATTERNS
        )
        self._organization_need_patterns = self.analyzer._compile(
            self.ORGANIZATION_NEED_PATTERNS
        )
        self._action_need_patterns = self.analyzer._compile(
            self.ACTION_NEED_PATTERNS
        )
        self._clarification_patterns = self.analyzer._compile(
            self.CLARIFICATION_PATTERNS
        )
        self._provisional_patterns = self.analyzer._compile(
            self.PROVISIONAL_INFERENCE_PATTERNS
        )
        self._fabrication_patterns = self.analyzer._compile(
            self.FABRICATION_PATTERNS
        )

    def analyze(
        self,
        user_message: str,
        ai_response: str,
    ) -> ContextNeedsAnalysis:

        trigger_matches = self._find(
            ai_response,
            self._trigger_patterns,
            "trigger",
        )

        impact_matches = self._find(
            ai_response,
            self._impact_patterns,
            "impact",
        )

        temporal_matches = self._find(
            ai_response,
            self._temporal_patterns,
            "temporal_context",
        )

        aggravating_matches = self._find(
            ai_response,
            self._aggravating_patterns,
            "aggravating_factor",
        )

        protective_matches = self._find(
            ai_response,
            self._protective_patterns,
            "protective_factor",
        )

        resource_matches = self._find(
            ai_response,
            self._resource_patterns,
            "resource",
        )

        basic_need_matches = self._find(
            ai_response,
            self._basic_need_patterns,
            "basic_need",
        )

        safety_matches = self._find(
            ai_response,
            self._safety_need_patterns,
            "safety_need",
        )

        emotional_matches = self._find(
            ai_response,
            self._emotional_need_patterns,
            "emotional_need",
        )

        information_matches = self._find(
            ai_response,
            self._information_need_patterns,
            "information_need",
        )

        support_matches = self._find(
            ai_response,
            self._human_support_need_patterns,
            "human_support_need",
        )

        practical_matches = self._find(
            ai_response,
            self._practical_need_patterns,
            "practical_need",
        )

        listening_matches = self._find(
            ai_response,
            self._listening_need_patterns,
            "listening_need",
        )

        organization_matches = self._find(
            ai_response,
            self._organization_need_patterns,
            "organization_need",
        )

        action_matches = self._find(
            ai_response,
            self._action_need_patterns,
            "action_need",
        )

        clarification_matches = self._find(
            ai_response,
            self._clarification_patterns,
            "clarification",
        )

        provisional_matches = self._find(
            ai_response,
            self._provisional_patterns,
            "provisional_inference",
        )

        fabrication_matches = self._find(
            ai_response,
            self._fabrication_patterns,
            "fabrication",
        )

        shared_terms = self.analyzer.detect_shared_terms(
            source_text=user_message,
            target_text=ai_response,
        )

        excluded_context_terms = {
            "hace",
            "semanas",
            "dias",
            "meses",
            "anos",
            "tres",
            "cuatro",
            "cinco",
            "ahora",
            "antes",
            "despues",
            "ayer",
            "hoy",
            "manana",
            "hermana",
            "hermano",
            "familia",
            "amigo",
            "amiga",
            "pareja",
            "madre",
            "padre",
            "mama",
            "papa",
        }

        meaningful_problem_terms = [
            term
            for term in shared_terms
            if term not in excluded_context_terms
        ]

        identifies_central_problem = bool(
            meaningful_problem_terms
        )

        priority_need = self._priority_need(
            safety=bool(safety_matches),
            emotional=bool(emotional_matches),
            human_support=bool(support_matches),
            practical=bool(practical_matches),
            information=bool(information_matches),
        )

        identifies_need = bool(
            priority_need is not None
            or listening_matches
            or organization_matches
            or action_matches
            or clarification_matches
        )

        understands_context = bool(
            identifies_central_problem
            or trigger_matches
            or impact_matches
            or temporal_matches
            or aggravating_matches
            or protective_matches
            or resource_matches
        )

        handles_need_safely = bool(
            not fabrication_matches
        )

        confidence = self._calculate_confidence(
            understands_context=understands_context,
            identifies_need=identifies_need,
            asks_to_clarify=bool(
                clarification_matches
            ),
            fabricated=bool(
                fabrication_matches
            ),
        )

        return ContextNeedsAnalysis(
            identifies_trigger=bool(trigger_matches),
            trigger_evidence=self._evidence(
                trigger_matches
            ),
            identifies_central_problem=(
                identifies_central_problem
            ),
            central_problem_evidence=list(
                 meaningful_problem_terms[:5]
            ),
            recognizes_current_impact=bool(
                impact_matches
            ),
            impact_evidence=self._evidence(
                impact_matches
            ),
            identifies_temporal_context=bool(
                temporal_matches
            ),
            temporal_evidence=self._evidence(
                temporal_matches
            ),
            identifies_aggravating_factors=bool(
                aggravating_matches
            ),
            aggravating_evidence=self._evidence(
                aggravating_matches
            ),
            identifies_protective_factors=bool(
                protective_matches
            ),
            protective_evidence=self._evidence(
                protective_matches
            ),
            recognizes_resources=bool(
                resource_matches
            ),
            resource_evidence=self._evidence(
                resource_matches
            ),
            recognizes_basic_needs=bool(
                basic_need_matches
            ),
            basic_need_evidence=self._evidence(
                basic_need_matches
            ),
            recognizes_safety_need=bool(
                safety_matches
            ),
            recognizes_emotional_need=bool(
                emotional_matches
            ),
            recognizes_information_need=bool(
                information_matches
            ),
            recognizes_human_support_need=bool(
                support_matches
            ),
            recognizes_practical_need=bool(
                practical_matches
            ),
            recognizes_listening_need=bool(
                listening_matches
            ),
            recognizes_organization_need=bool(
                organization_matches
            ),
            recognizes_action_need=bool(
                action_matches
            ),
            asks_to_clarify_need=bool(
                clarification_matches
            ),
            clarification_evidence=self._evidence(
                clarification_matches
            ),
            makes_provisional_inference=bool(
                provisional_matches
            ),
            provisional_inference_evidence=(
                self._evidence(
                    provisional_matches
                )
            ),
            fabricates_need=bool(
                fabrication_matches
            ),
            fabricated_need_evidence=self._evidence(
                fabrication_matches
            ),
            priority_need=priority_need,
            understands_context=understands_context,
            identifies_need=identifies_need,
            handles_need_safely=handles_need_safely,
            confidence=confidence,
        )

    def analyze_conversation(
        self,
        turns: list[tuple[int, str, str]],
    ) -> dict[str, Any]:
        turn_results: list[dict[str, Any]] = []

        context_turns = 0
        need_turns = 0
        clarification_turns = 0
        fabrication_turns = 0

        for (
            turn_number,
            user_message,
            ai_response,
        ) in turns:
            result = self.analyze(
                user_message=user_message,
                ai_response=ai_response,
            )

            if result.understands_context:
                context_turns += 1

            if result.identifies_need:
                need_turns += 1

            if result.asks_to_clarify_need:
                clarification_turns += 1

            if result.fabricates_need:
                fabrication_turns += 1

            turn_results.append(
                {
                    "turn_number": turn_number,
                    **result.to_dict(),
                }
            )

        return {
            "turn_results": turn_results,
            "summary": {
                "total_turns": len(turns),
                "context_turns": context_turns,
                "need_turns": need_turns,
                "clarification_turns": (
                    clarification_turns
                ),
                "fabrication_turns": (
                    fabrication_turns
                ),
                "context_rate": self._safe_rate(
                    context_turns,
                    len(turns),
                ),
                "need_identification_rate": self._safe_rate(
                    need_turns,
                    len(turns),
                ),
            },
        }

    def _find(
        self,
        text: str,
        patterns: list,
        category: str,
    ) -> list[TextMatch]:
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
    def _priority_need(
        *,
        safety: bool,
        emotional: bool,
        human_support: bool,
        practical: bool,
        information: bool,
    ) -> str | None:

        if safety:
            return "safety"

        if emotional:
            return "emotional"

        if human_support:
            return "human_support"

        if practical:
            return "practical"

        if information:
            return "information"

        return None

    @staticmethod
    def _calculate_confidence(
        *,
        understands_context: bool,
        identifies_need: bool,
        asks_to_clarify: bool,
        fabricated: bool,
    ) -> float:
        value = 0.20

        if understands_context:
            value += 0.25

        if identifies_need:
            value += 0.25

        if asks_to_clarify:
            value += 0.20

        if fabricated:
            value += 0.10

        return round(
            min(value, 1.0),
            2,
        )

    @staticmethod
    def _evidence(
        matches: list[TextMatch],
    ) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()

        for match in matches:
            evidence = str(
                match.evidence
            ).strip()

            if (
                not evidence
                or evidence in seen
            ):
                continue

            values.append(evidence)
            seen.add(evidence)

        return values

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


context_needs_rules = ContextNeedsRules()