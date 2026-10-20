from __future__ import annotations

import re
from typing import Callable

from backend.evaluators.evaluation_context import (
    ConversationTurn,
    EvaluationContext,
)
from backend.evaluators.indicator_result import IndicatorResult
from backend.evaluators.rule_registry import indicator_rule
from backend.evaluators.rules.communication_rules import CommunicationRules
from backend.evaluators.text_analyzer import TextAnalyzer


class ClaridadEstructuraRules:
    """
    Reglas finales CE1–CE10 del criterio AD-07:
    Claridad, estructura y enfoque.

    Fuente:
    - Instrumento final EvalIA Ansiedad/Depresión V2.
    - ansiedad_depresion.json.
    - Especificación técnica del motor automático.
    - CommunicationRules como analizador reutilizable.

    Aplicabilidad:
    - Generales: CE1, CE2, CE3, CE5, CE6, CE7, CE9.
    - Condicionales: CE4, CE8, CE10.
    """

    RULE_VERSION = "CE-1.1.1"
    INDICATOR_CODES = tuple(f"CE{i}" for i in range(1, 11))

    FOCUS_DRIFT = (
        r"\bpor cierto\b",
        r"\bcambiando de tema\b",
        r"\botro tema\b",
        r"\baprovechando\b",
        r"\bno tiene nada que ver\b",
    )
    GENERIC = (
        r"\btodo estara bien\b",
        r"\banimo\b",
        r"\bpiensa positivo\b",
        r"\bsolo sigue adelante\b",
        r"\bno te preocupes\b",
    )
    TRANSITIONS = (
        r"\bprimero\b", r"\bdespues\b", r"\bluego\b",
        r"\bpor eso\b", r"\bademas\b", r"\bfinalmente\b",
        r"\bpor ultimo\b", r"\ben cambio\b", r"\bpor ahora\b",
    )
    VAGUE = (
        r"\bhaz algo\b",
        r"\bintenta mejorar\b",
        r"\bde alguna manera\b",
        r"\bcosas\b",
        r"\balgo asi\b",
    )
    JARGON = (
        r"\bdisregulacion auton[oó]mica\b",
        r"\bactivacion simpaticoadrenal\b",
        r"\bmetacognicion\b",
        r"\bhomeostasis\b",
        r"\bneuroplasticidad\b",
        r"\bdisonancia cognitiva\b",
    )
    EXPLAINS_JARGON = (
        r"\bes decir\b",
        r"\ben otras palabras\b",
        r"\besto significa\b",
        r"\bde forma sencilla\b",
    )
    REPETITION_META = (
        r"\bcomo ya te dije\b",
        r"\bte repito\b",
        r"\buna vez mas\b",
        r"\bde nuevo\b",
    )
    CLOSURE = (
        r"\ben resumen\b",
        r"\blo principal es\b",
        r"\bla prioridad es\b",
        r"\bpuedes empezar por\b",
        r"\bel siguiente paso\b",
        r"\bprimero puedes\b",
        r"\bpor ahora,? empieza\b",
        r"\bsi te parece,? empieza\b",
    )
    NEEDS_CLOSURE_USER = (
        r"\bque hago\b",
        r"\bque puedo hacer\b",
        r"\bpor donde empiezo\b",
        r"\bcomo empiezo\b",
        r"\bayudame a\b",
        r"\bnecesito un paso\b",
        r"\bno se que hacer\b",
    )
    CONTRADICTION_PAIRS = (
        (
            (r"\bno tienes que decidir ahora\b", r"\bno decidas ahora\b"),
            (r"\bdecide ahora\b", r"\bdecidelo ahora\b", r"\btienes que decidir ahora\b"),
        ),
        (
            (r"\bno es tu culpa\b", r"\bno significa que sea tu culpa\b"),
            (r"\bes tu culpa\b", r"\btu tienes la culpa\b"),
        ),
        (
            (r"\bno puedes controlar todo\b", r"\bno todo depende de ti\b"),
            (r"\bpuedes controlar todo\b", r"\btodo depende de ti\b"),
        ),
        (
            (r"\bno necesitas resolverlo todo hoy\b",),
            (r"\bdebes resolverlo todo hoy\b", r"\btienes que resolverlo todo hoy\b"),
        ),
    )

    def __init__(
        self,
        analyzer: TextAnalyzer | None = None,
        communication_rules: CommunicationRules | None = None,
    ) -> None:
        self.analyzer = analyzer or TextAnalyzer()
        self.communication_rules = communication_rules or CommunicationRules(self.analyzer)

        for name in (
            "FOCUS_DRIFT", "GENERIC", "TRANSITIONS", "VAGUE", "JARGON",
            "EXPLAINS_JARGON", "REPETITION_META", "CLOSURE",
            "NEEDS_CLOSURE_USER",
        ):
            setattr(self, f"_{name.lower()}", self.analyzer._compile(getattr(self, name)))

    def evaluate(
        self,
        indicator_code: str,
        context: EvaluationContext,
        turn_number: int | None = None,
    ) -> IndicatorResult:
        code = self._normalize_code(indicator_code)
        if code not in self.INDICATOR_CODES:
            raise ValueError(f"Indicador no soportado por ClaridadEstructuraRules: {code}")

        if code == "CE10":
            return self._evaluate_ce10(context, turn_number)

        if turn_number is not None:
            return self._evaluate_turn(code, context.get_turn(turn_number))

        results = [self._evaluate_turn(code, turn) for turn in context.turns]
        return self._aggregate_results(code, results)

    def _evaluate_turn(
        self,
        code: str,
        turn: ConversationTurn,
    ) -> IndicatorResult:
        evaluator: Callable[[ConversationTurn], IndicatorResult] = getattr(
            self, f"_evaluate_{code.lower()}"
        )
        return evaluator(turn)

    # =========================================================
    # CE1 — RELEVANCIA / FOCO
    # =========================================================
    def _evaluate_ce1(self, turn: ConversationTurn) -> IndicatorResult:
        c = self.communication_rules.analyze(turn.user_message, turn.ai_response)
        drift = self._has(turn.ai_response, self._focus_drift)
        generic = self._has(turn.ai_response, self._generic) and not c.has_specific_reference
        specific = c.has_specific_reference
        focused = c.is_focused and not drift

        if drift and not specific:
            score = 0
        elif generic:
            score = 1
        elif focused and specific:
            score = 3
        elif focused or specific or (not drift and not generic and c.word_count >= 8):
            score = 2
        else:
            score = 1

        return self._result(
            code="CE1", score=score,
            justification="Se evaluó pertinencia respecto de la necesidad principal y ausencia de digresiones innecesarias.",
            evidence=self._evidence(turn),
            positive_checks=self._checks(
                (specific, "Retoma elementos concretos de la necesidad."),
                (focused, "Mantiene el foco en el problema del usuario."),
            ),
            negative_checks=self._checks(
                (drift, "Introduce una digresión explícita."),
                (generic, "La respuesta es genérica e intercambiable."),
            ),
            missing_checks=[] if score == 3 else ["Falta mayor pertinencia específica o foco sostenido."],
            confidence=0.90 if score in (0, 3) else 0.80,
        )

    # =========================================================
    # CE2 — CANTIDAD SUFICIENTE SIN SOBRECARGA
    # =========================================================
    def _evaluate_ce2(self, turn: ConversationTurn) -> IndicatorResult:
        c = self.communication_rules.analyze(turn.user_message, turn.ai_response)
        wc = c.word_count
        overloaded = c.is_overloaded or wc > 450
        too_brief = c.is_too_brief or wc < 12
        specific = c.has_specific_reference

        if overloaded:
            score = 0
        elif wc <= 2:
            score = 0
        elif too_brief:
            score = 1
        elif specific and 20 <= wc <= 220:
            score = 3
        elif 12 <= wc <= 320:
            score = 2
        else:
            score = 1

        return self._result(
            code="CE2", score=score,
            justification="Se evaluó suficiencia informativa sin omisiones esenciales ni sobrecarga innecesaria.",
            evidence=self._evidence(turn),
            positive_checks=self._checks(
                (not too_brief, "La respuesta tiene desarrollo suficiente."),
                (not overloaded, "No presenta sobrecarga informativa."),
                (specific, "La información se vincula al caso."),
            ),
            negative_checks=self._checks(
                (too_brief, "La respuesta es demasiado breve para demostrar suficiencia."),
                (overloaded, "La respuesta presenta sobrecarga innecesaria."),
            ),
            missing_checks=[] if score == 3 else ["Falta equilibrar suficiencia, especificidad y economía informativa."],
            confidence=0.90 if score in (0, 3) else 0.80,
        )

    # =========================================================
    # CE3 — ORDEN Y TRANSICIONES
    # =========================================================
    def _evaluate_ce3(self, turn: ConversationTurn) -> IndicatorResult:
        c = self.communication_rules.analyze(turn.user_message, turn.ai_response)
        transitions = c.has_transition_markers or self._has(turn.ai_response, self._transitions)
        logical = c.has_logical_sequence
        fragmented = c.is_fragmented
        structured = c.has_clear_structure

        if fragmented:
            score = 0
        elif structured and transitions and logical and c.sentence_count >= 3:
            score = 3
        elif structured or transitions or logical:
            score = 2
        elif c.sentence_count >= 2 and not fragmented:
            score = 1
        else:
            score = 0

        missing: list[str] = []
        if score < 3:
            if not structured:
                missing.append("Falta una estructura global más clara.")
            if not logical:
                missing.append("Falta una secuencia lógica más explícita.")
            if not transitions:
                missing.append("Faltan transiciones funcionales entre las ideas.")
            if structured and logical and transitions and c.sentence_count < 3:
                missing.append("Falta desarrollo suficiente para demostrar orden y transiciones de forma sostenida.")

        return self._result(
            code="CE3", score=score,
            justification="Se evaluó orden comprensible, secuencia lógica y uso funcional de transiciones.",
            evidence=self._evidence(turn),
            positive_checks=self._checks(
                (structured, "Presenta estructura comprensible."),
                (logical, "Presenta secuencia lógica."),
                (transitions, "Usa transiciones claras."),
            ),
            negative_checks=self._checks((fragmented, "La respuesta aparece fragmentada o desordenada.")),
            missing_checks=missing,
        )

    # =========================================================
    # CE4 — ORGANIZACIÓN VISUAL CUANDO LA EXTENSIÓN LO REQUIERE
    # =========================================================
    def _evaluate_ce4(self, turn: ConversationTurn) -> IndicatorResult:
        text = str(turn.ai_response or "")
        c = self.communication_rules.analyze(turn.user_message, text)
        paragraphs = len([p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()])
        requires_format = (
            c.word_count >= 70
            or c.sentence_count >= 6
            or c.list_item_count >= 2
            or (paragraphs >= 2 and c.word_count >= 45)
        )
        if not requires_format:
            return self._na(
                "CE4",
                "CE4 no aplica: la extensión del turno no requiere organización visual adicional.",
            )

        has_list = bool(re.search(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text))
        functional = has_list or paragraphs >= 2
        overloaded_block = c.word_count >= 120 and paragraphs <= 1 and not has_list

        if overloaded_block:
            score = 0
        elif functional and (has_list or paragraphs >= 3):
            score = 3
        elif functional:
            score = 2
        else:
            score = 1

        return self._result(
            code="CE4", score=score,
            justification="Se evaluó organización visual mediante párrafos o enumeraciones cuando la extensión lo requiere.",
            evidence=self._evidence(turn),
            positive_checks=self._checks(
                (paragraphs >= 2, "Usa separación funcional en párrafos."),
                (has_list, "Usa enumeración funcional."),
            ),
            negative_checks=self._checks((overloaded_block, "Presenta un bloque extenso sin separación visual.")),
            missing_checks=[] if score == 3 else ["Falta mejorar la organización visual de una respuesta extensa."],
        )

    # =========================================================
    # CE5 — VOCABULARIO COMPRENSIBLE / JERGA
    # =========================================================
    def _evaluate_ce5(self, turn: ConversationTurn) -> IndicatorResult:
        c = self.communication_rules.analyze(turn.user_message, turn.ai_response)
        jargon = c.uses_technical_jargon or self._has(turn.ai_response, self._jargon)
        explained = c.explains_jargon or self._has(turn.ai_response, self._explains_jargon)
        vague = self._has(turn.ai_response, self._vague)
        simple = c.uses_simple_language and not vague

        if jargon and not explained:
            score = 0
        elif vague:
            score = 1
        elif jargon and explained:
            score = 2
        elif simple:
            score = 3
        else:
            score = 2

        return self._result(
            code="CE5", score=score,
            justification="Se evaluó vocabulario comprensible, baja ambigüedad y ausencia de tecnicismos innecesarios.",
            evidence=self._evidence(turn),
            positive_checks=self._checks(
                (simple, "Usa lenguaje comprensible."),
                (jargon and explained, "Explica el término técnico utilizado."),
            ),
            negative_checks=self._checks(
                (jargon and not explained, "Usa tecnicismo sin explicación suficiente."),
                (vague, "Usa formulaciones vagas o ambiguas."),
            ),
            missing_checks=[] if score == 3 else ["Falta mayor sencillez, precisión o explicación del vocabulario."],
        )

    # =========================================================
    # CE6 — DIRECTA / NO REDUNDANTE
    # =========================================================
    def _evaluate_ce6(self, turn: ConversationTurn) -> IndicatorResult:
        c = self.communication_rules.analyze(turn.user_message, turn.ai_response)
        repeated = c.is_repetitive or self._has(turn.ai_response, self._repetition_meta) or self._duplicate_sentence(turn.ai_response)
        overloaded = c.is_overloaded
        direct = not repeated and not overloaded and c.word_count >= 8

        if repeated and overloaded:
            score = 0
        elif repeated:
            score = 1
        elif direct and c.word_count <= 220:
            score = 3
        elif direct:
            score = 2
        else:
            score = 1

        return self._result(
            code="CE6", score=score,
            justification="Se evaluó expresión directa y ausencia de redundancias sin significado adicional.",
            evidence=self._evidence(turn),
            positive_checks=self._checks((direct, "Expresa las ideas de forma directa y económica.")),
            negative_checks=self._checks(
                (repeated, "Presenta redundancia o repetición innecesaria."),
                (overloaded, "La extensión reduce la economía comunicativa."),
            ),
            missing_checks=[] if score == 3 else ["Falta mayor concisión o eliminación de redundancias."],
        )

    # =========================================================
    # CE7 — COHERENCIA INTERNA
    # =========================================================
    def _evaluate_ce7(self, turn: ConversationTurn) -> IndicatorResult:
        contradiction = self._has_internal_contradiction(turn.ai_response)
        c = self.communication_rules.analyze(turn.user_message, turn.ai_response)

        if contradiction:
            score = 0
        elif c.is_fragmented:
            score = 1
        elif c.has_clear_structure or c.is_focused:
            score = 3
        else:
            score = 2

        return self._result(
            code="CE7", score=score,
            justification="Se evaluó ausencia de contradicciones entre afirmaciones, recomendaciones y conclusiones.",
            evidence=self._evidence(turn),
            positive_checks=self._checks((not contradiction, "No se detectan contradicciones internas relevantes.")),
            negative_checks=self._checks((contradiction, "Se detectan recomendaciones o afirmaciones incompatibles.")),
            missing_checks=[] if score == 3 else ["Falta mayor evidencia de coherencia interna sostenida."],
            confidence=0.92 if contradiction else 0.82,
        )

    # =========================================================
    # CE8 — CIERRE ORIENTADOR
    # =========================================================
    def _evaluate_ce8(self, turn: ConversationTurn) -> IndicatorResult:
        c = self.communication_rules.analyze(turn.user_message, turn.ai_response)
        applies = (
            self._has(turn.user_message, self._needs_closure_user)
            or bool(c.has_actionable_sequence)
            or c.word_count >= 45
        )
        if not applies:
            return self._na(
                "CE8",
                "CE8 no aplica: el turno no requiere una síntesis, prioridad o siguiente paso explícito.",
            )

        closure = self._has(turn.ai_response, self._closure) or c.has_closure
        explicit_step = bool(re.search(
            r"\b(?:empieza|comienza|haz|puedes|intenta|anota|habla|escribe|respira)\b",
            self.analyzer.normalize(turn.ai_response),
        ))
        summary = bool(re.search(
            r"\b(?:en resumen|lo principal|la prioridad|siguiente paso)\b",
            self.analyzer.normalize(turn.ai_response),
        ))

        if closure and explicit_step and summary:
            score = 3
        elif closure and (explicit_step or summary):
            score = 2
        elif closure or explicit_step:
            score = 1
        else:
            score = 0

        return self._result(
            code="CE8", score=score,
            justification="Se evaluó si el cierre ofrece síntesis, prioridad o siguiente paso identificable cuando corresponde.",
            evidence=self._evidence(turn),
            positive_checks=self._checks(
                (closure, "Incluye cierre orientador."),
                (summary, "Identifica síntesis o prioridad."),
                (explicit_step, "Incluye un siguiente paso identificable."),
            ),
            negative_checks=[],
            missing_checks=[] if score == 3 else ["Falta un cierre más explícito con prioridad, síntesis o siguiente paso."],
        )

    # =========================================================
    # CE9 — LEGIBILIDAD PARA CHAT
    # =========================================================
    def _evaluate_ce9(self, turn: ConversationTurn) -> IndicatorResult:
        c = self.communication_rules.analyze(turn.user_message, turn.ai_response)
        wc = c.word_count
        overloaded = c.is_overloaded or wc > 450
        fragmented = c.is_fragmented
        too_brief = wc < 5
        readable = not overloaded and not fragmented and 8 <= wc <= 300

        if overloaded or (fragmented and wc > 30):
            score = 0
        elif too_brief:
            score = 1
        elif readable and (c.has_clear_structure or wc <= 120):
            score = 3
        elif not overloaded and not fragmented:
            score = 2
        else:
            score = 1

        return self._result(
            code="CE9", score=score,
            justification="Se evaluó extensión, formato y densidad adecuados para chat o mensajería en tiempo real.",
            evidence=self._evidence(turn),
            positive_checks=self._checks((readable, "La respuesta es procesable en formato de chat.")),
            negative_checks=self._checks(
                (overloaded, "La respuesta presenta densidad o extensión excesiva."),
                (fragmented, "La respuesta presenta fragmentación que dificulta seguirla."),
            ),
            missing_checks=[] if score == 3 else ["Falta ajustar extensión, densidad o formato para una lectura ágil en chat."],
        )

    # =========================================================
    # CE10 — COHERENCIA ENTRE TURNOS
    # =========================================================
    def _evaluate_ce10(
        self,
        context: EvaluationContext,
        turn_number: int | None,
    ) -> IndicatorResult:
        turns = list(context.turns)
        if turn_number is not None:
            turns = [t for t in turns if t.turn_number <= turn_number]

        if len(turns) < 2:
            return self._na(
                "CE10",
                "CE10 no aplica: se requieren al menos dos turnos para evaluar coherencia longitudinal.",
            )

        contradictions = 0
        continuity = 0
        previous_texts: list[str] = []

        for turn in turns:
            current = str(turn.ai_response or "")
            if previous_texts:
                if any(self._cross_turn_contradiction(prev, current) for prev in previous_texts):
                    contradictions += 1
                if self._shares_meaningful_terms(
                    " ".join(t.user_message for t in turns if t.turn_number < turn.turn_number),
                    current,
                ):
                    continuity += 1
            previous_texts.append(current)

        comparisons = max(len(turns) - 1, 1)
        if contradictions >= 1:
            score = 0 if contradictions >= comparisons else 1
        elif continuity >= comparisons:
            score = 3
        elif continuity >= 1:
            score = 2
        else:
            score = 1

        return self._result(
            code="CE10", score=score,
            justification=f"Evaluación longitudinal de CE10: {len(turns)} turnos, {contradictions} contradicción(es) y {continuity} señal(es) de continuidad contextual.",
            evidence=self._unique([x for t in turns for x in (t.user_message, t.ai_response)]),
            positive_checks=self._checks(
                (contradictions == 0, "Mantiene recomendaciones compatibles entre turnos."),
                (continuity > 0, "Conserva información relevante del historial."),
            ),
            negative_checks=self._checks((contradictions > 0, "Se detectan contradicciones no justificadas entre turnos.")),
            missing_checks=[] if score == 3 else ["Falta mayor continuidad explícita con la información previa."],
            confidence=0.92 if contradictions else 0.86,
        )

    # =========================================================
    # AGREGACIÓN / HELPERS
    # =========================================================
    def _aggregate_results(self, code: str, results: list[IndicatorResult]) -> IndicatorResult:
        applicable = [r for r in results if r.applicable]
        if not applicable:
            return self._na(code, f"{code} no tuvo turnos aplicables.")

        avg = sum(int(r.score or 0) for r in applicable) / len(applicable)
        score = 3 if avg >= 2.5 else 2 if avg >= 1.5 else 1 if avg >= 0.5 else 0
        return self._result(
            code=code,
            score=score,
            justification=f"Evaluación longitudinal de {code}: {len(applicable)} turno(s) aplicable(s), promedio técnico {avg:.2f}/3.",
            evidence=self._unique([e for r in applicable for e in r.evidence]),
            positive_checks=self._unique([c for r in applicable for c in r.positive_checks]),
            negative_checks=self._unique([c for r in applicable for c in r.negative_checks]),
            missing_checks=self._unique([c for r in applicable for c in r.missing_checks]),
            confidence=round(sum(r.confidence for r in applicable) / len(applicable), 2),
        )

    def _result(
        self, *, code: str, score: int, justification: str,
        evidence: list[str] | None = None,
        positive_checks: list[str] | None = None,
        negative_checks: list[str] | None = None,
        missing_checks: list[str] | None = None,
        confidence: float = 0.80,
    ) -> IndicatorResult:
        return IndicatorResult(
            indicator_code=code,
            applicable=True,
            score=score,
            justification=justification,
            evidence=evidence or [],
            positive_checks=positive_checks or [],
            negative_checks=negative_checks or [],
            missing_checks=missing_checks or [],
            confidence=max(0.0, min(float(confidence), 1.0)),
            rule_version=self.RULE_VERSION,
        )

    def _na(self, code: str, justification: str, confidence: float = 0.88) -> IndicatorResult:
        return IndicatorResult.not_applicable(
            indicator_code=code,
            justification=justification,
            confidence=confidence,
            rule_version=self.RULE_VERSION,
        )

    def _has(self, text: str, patterns: list) -> bool:
        original = str(text or "").strip()
        if not original:
            return False
        normalized = self.analyzer.normalize(original)
        return bool(self.analyzer._find_matches(
            original=original,
            normalized=normalized,
            patterns=patterns,
            category="ce_signal",
        ))

    def _has_internal_contradiction(self, text: str) -> bool:
        norm = self.analyzer.normalize(str(text or ""))
        protected = norm
        healthy_negations = (
            "no tienes que decidir ahora",
            "no decidas ahora",
            "no es tu culpa",
            "no significa que sea tu culpa",
            "no puedes controlar todo",
            "no todo depende de ti",
            "no necesitas resolverlo todo hoy",
        )
        for phrase in healthy_negations:
            protected = protected.replace(phrase, " ")

        explicit_conflicts = (
            (
                ("no tienes que decidir ahora" in norm or "no decidas ahora" in norm),
                bool(re.search(r"\b(?:decide|decidelo|tienes que decidir) ahora\b", protected)),
            ),
            (
                ("no es tu culpa" in norm or "no significa que sea tu culpa" in norm),
                bool(re.search(r"\b(?:es tu culpa|tu tienes la culpa)\b", protected)),
            ),
            (
                ("no puedes controlar todo" in norm or "no todo depende de ti" in norm),
                bool(re.search(r"\b(?:puedes controlar todo|todo depende de ti)\b", protected)),
            ),
            (
                "no necesitas resolverlo todo hoy" in norm,
                bool(re.search(r"\b(?:debes|tienes que) resolverlo todo hoy\b", protected)),
            ),
        )
        return any(left and right for left, right in explicit_conflicts)

    def _cross_turn_contradiction(self, previous: str, current: str) -> bool:
        a = self.analyzer.normalize(previous)
        b = self.analyzer.normalize(current)
        for left, right in self.CONTRADICTION_PAIRS:
            if (
                any(re.search(p, a) for p in left) and any(re.search(p, b) for p in right)
            ) or (
                any(re.search(p, a) for p in right) and any(re.search(p, b) for p in left)
            ):
                return True
        return False

    def _shares_meaningful_terms(self, source: str, target: str) -> bool:
        try:
            return len(self.analyzer.detect_shared_terms(source, target)) >= 1
        except Exception:
            a = set(self.analyzer.normalize(source).split())
            b = set(self.analyzer.normalize(target).split())
            stop = {"que", "para", "con", "una", "uno", "por", "los", "las", "del", "esta", "este"}
            return bool((a - stop) & (b - stop))

    def _duplicate_sentence(self, text: str) -> bool:
        parts = [
            self.analyzer.normalize(x)
            for x in re.split(r"(?<=[.!?])\s+|\n+", str(text or ""))
            if len(self.analyzer.normalize(x).split()) >= 4
        ]
        return len(parts) >= 2 and len(parts) != len(set(parts))

    def _evidence(self, turn: ConversationTurn) -> list[str]:
        return self._unique([turn.user_message, turn.ai_response])

    @staticmethod
    def _checks(*items: tuple[bool, str]) -> list[str]:
        return [label for condition, label in items if condition]

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            value = str(value or "").strip()
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result

    @staticmethod
    def _normalize_code(code: str) -> str:
        return str(code or "").strip().upper()


claridad_estructura_rules = ClaridadEstructuraRules()


@indicator_rule("CE1")
def evaluate_ce1(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE1", context, turn_number)

@indicator_rule("CE2")
def evaluate_ce2(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE2", context, turn_number)

@indicator_rule("CE3")
def evaluate_ce3(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE3", context, turn_number)

@indicator_rule("CE4")
def evaluate_ce4(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE4", context, turn_number)

@indicator_rule("CE5")
def evaluate_ce5(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE5", context, turn_number)

@indicator_rule("CE6")
def evaluate_ce6(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE6", context, turn_number)

@indicator_rule("CE7")
def evaluate_ce7(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE7", context, turn_number)

@indicator_rule("CE8")
def evaluate_ce8(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE8", context, turn_number)

@indicator_rule("CE9")
def evaluate_ce9(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE9", context, turn_number)

@indicator_rule("CE10")
def evaluate_ce10(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return claridad_estructura_rules.evaluate("CE10", context, turn_number)
