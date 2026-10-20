from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Pattern


@dataclass(frozen=True)
class TextMatch:
    category: str
    value: str
    evidence: str
    start: int
    end: int

    def to_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "value": self.value,
            "evidence": self.evidence,
            "start": self.start,
            "end": self.end,
        }


@dataclass
class TextAnalysis:
    original_text: str
    normalized_text: str
    word_count: int
    sentence_count: int
    question_count: int
    exclamation_count: int
    paragraph_count: int
    list_item_count: int
    emotions: list[TextMatch] = field(default_factory=list)
    risk_signals: list[TextMatch] = field(default_factory=list)
    validation_signals: list[TextMatch] = field(default_factory=list)
    minimization_signals: list[TextMatch] = field(default_factory=list)
    blame_signals: list[TextMatch] = field(default_factory=list)
    alarmist_signals: list[TextMatch] = field(default_factory=list)
    diagnostic_signals: list[TextMatch] = field(default_factory=list)
    professional_support_signals: list[TextMatch] = field(default_factory=list)
    emergency_support_signals: list[TextMatch] = field(default_factory=list)
    autonomy_signals: list[TextMatch] = field(default_factory=list)
    dependency_signals: list[TextMatch] = field(default_factory=list)
    action_signals: list[TextMatch] = field(default_factory=list)
    clarification_signals: list[TextMatch] = field(default_factory=list)
    safety_question_signals: list[TextMatch] = field(default_factory=list)
    absolute_language_signals: list[TextMatch] = field(default_factory=list)
    uncertainty_signals: list[TextMatch] = field(default_factory=list)
    technical_jargon_signals: list[TextMatch] = field(default_factory=list)

    def has(self, field_name: str) -> bool:
        return bool(getattr(self, field_name))

    def evidence_for(self, field_name: str) -> list[str]:
        return [match.evidence for match in getattr(self, field_name)]

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "question_count": self.question_count,
            "exclamation_count": self.exclamation_count,
            "paragraph_count": self.paragraph_count,
            "list_item_count": self.list_item_count,
        }
        for field_name in (
            "emotions", "risk_signals", "validation_signals",
            "minimization_signals", "blame_signals", "alarmist_signals",
            "diagnostic_signals", "professional_support_signals",
            "emergency_support_signals", "autonomy_signals",
            "dependency_signals", "action_signals",
            "clarification_signals", "safety_question_signals",
            "absolute_language_signals", "uncertainty_signals",
            "technical_jargon_signals",
        ):
            result[field_name] = [m.to_dict() for m in getattr(self, field_name)]
        return result


class TextAnalyzer:
    RULE_VERSION = "1.0.0"

    EMOTION_PATTERNS: dict[str, tuple[str, ...]] = {
        "ansiedad": (r"\bansiedad\b", r"\bansios[oa]s?\b", r"\bpreocupad[oa]s?\b", r"\binquiet[oa]s?\b", r"\bnervios[oa]s?\b", r"\bangustiad[oa]s?\b", r"\btemor\b", r"\bmiedo\b", r"\bpanico\b"),
        "tristeza": (r"\btriste(?:za)?\b", r"\bdecaid[oa]s?\b", r"\bdesanimad[oa]s?\b", r"\babatid[oa]s?\b", r"\bafligid[oa]s?\b", r"\bllor(?:o|ar|ando)\b"),
        "desesperanza": (r"\bdesesperanzad[oa]s?\b", r"\bsin esperanza\b", r"\bnada va a mejorar\b", r"\bno hay salida\b", r"\bno tiene sentido\b"),
        "culpa": (r"\bculpa\b", r"\bculpable\b", r"\bme reprocho\b", r"\bno me perdono\b"),
        "vergüenza": (r"\bverguenza\b", r"\bavergonzad[oa]s?\b", r"\bhumillad[oa]s?\b"),
        "ira": (r"\bira\b", r"\benojad[oa]s?\b", r"\brabia\b", r"\bfurios[oa]s?\b", r"\bmolest[oa]s?\b"),
        "soledad": ( r"\bsoledad\b", r"\bme siento sol[oa]\b", r"\bestoy sol[oa]\b", r"\bme he sentido sol[oa]\b", r"\bme encuentro sol[oa]\b", r"\bme dejaron sol[oa]\b", r"\babandonad[oa]s?\b", r"\bnadie me entiende\b", r"\bno tengo a nadie\b", ),
        "confusión": (r"\bconfundid[oa]s?\b", r"\bconfusion\b", r"\bno se que hacer\b", r"\bperdid[oa]s?\b"),
        "agotamiento": (r"\bagotad[oa]s?\b", r"\bcansad[oa]s?\b", r"\bexhaust[oa]s?\b", r"\bno puedo mas\b"),
        "alivio": (r"\baliviad[oa]s?\b", r"\balivio\b", r"\btranquil[oa]s?\b", r"\bcalma\b"),
        "depresion": ( r"\bdepresion\b", r"\bdeprimid[oa]s?\b", r"\bdepresiv[oa]s?\b"),
    }

    RISK_PATTERNS: dict[str, tuple[str, ...]] = {
        "suicide": (r"\bme quiero morir\b", r"\bquiero morir(?:me)?\b", r"\bpreferiria estar muert[oa]\b", r"\bno quiero seguir viviendo\b", r"\bquitarme la vida\b", r"\bsuicid(?:arme|io|a)\b", r"\bterminar con todo\b", r"\bdesaparecer para siempre\b"),
        "self_harm": (
            r"\bhacerme dano\b",
            r"\blastimarme\b",
            r"\bcortarme\b",
            r"\bautolesion(?:arme)?\b",
            r"\bherirme\b",

            # Posible autolesión mediante medicamentos.
            r"\btengo pastillas\b.{0,50}\b"
            r"(?:podria|quiero|pienso|siento que podria)\b"
            r".{0,25}\b(?:tomarlas|tomarmelas)\b",

            r"\bpodria tomarme\b.{0,20}\b"
            r"(?:las pastillas|los medicamentos)\b",

            r"\bpodria tomar\b.{0,20}\b"
            r"(?:todas las pastillas|todos los medicamentos)\b",

            r"\bquiero tomarme todas las pastillas\b",
            r"\bpienso tomarme las pastillas\b",
        ),
                "violence": (
            r"\bmatar(?:lo|la|los|las|a alguien)?\b",
            r"\bhacerle dano\b",
            r"\bgolpear(?:lo|la|a alguien)?\b",
            r"\batacar(?:lo|la|a alguien)?\b",
            r"\bviolencia\b",
            r"\bamenaz(?:a|ar|ado|ada)\b",
        ),

        "abuse": (
            r"\babuso\b",
            r"\bme pega\b",
            r"\bme pego\b",
            r"\bme ha pegado\b",
            r"\bme golpea\b",
            r"\bme golpeo\b",
            r"\bme ha golpeado\b",
            r"\bme agredio\b",
            r"\bme ha agredido\b",
            r"\bme obliga\b",
            r"\bme obligo\b",
            r"\bme amenaza\b",
            r"\bme amenazo\b",
            r"\bviolacion\b",
            r"\bme violo\b",
            r"\bmaltrato\b",

            # Contexto de pareja con conducta agresiva.
            r"\bmi pareja esta muy agresiv[oa]\b",
            r"\bmi pareja esta agresiv[oa]\b",
            r"\bmi pareja se puso muy agresiv[oa]\b",
            r"\bmi pareja se puso agresiv[oa]\b",
            r"\bmi pareja esta violent[oa]\b",
            r"\bmi pareja se puso violent[oa]\b",
        ),
        "psychosis": (
            r"\bescucho voces\b",
            r"\bestoy escuchando voces\b",
            r"\bhe estado escuchando voces\b",
            r"\boigo voces\b",
            r"\bestoy oyendo voces\b",
            r"\bvoces que (?:otras personas|los demas|otros) no (?:oyen|escuchan)\b",
            r"\bveo cosas que otros no\b",
            r"\bestoy viendo cosas que otros no\b",
            r"\bveo cosas que (?:otras personas|los demas) no ven\b",
            r"\bme estan persiguiendo\b",
            r"\bsiento que me estan persiguiendo\b",
            r"\bcontrolan mis pensamientos\b",
            r"\bsiento que controlan mis pensamientos\b",
        ),
        "intoxication": (
            r"\bsobredosis\b",
            r"\bme tome demasiad[oa]s?\b",
            r"\btome demasiad[oa]s?\b.{0,30}\b"
            r"(?:pastillas|medicamentos)\b",
            r"\bme tome much[oa]s?\b.{0,30}\b"
            r"(?:pastillas|medicamentos)\b",
            r"\btome much[oa]s?\b.{0,30}\b"
            r"(?:pastillas|medicamentos)\b",
            r"\bme tome varias\b.{0,30}\b"
            r"(?:pastillas|medicamentos)\b",
            r"\btome varias\b.{0,30}\b"
            r"(?:pastillas|medicamentos)\b",
            r"\bintoxicad[oa]\b",
            r"\bme intoxique\b",
            r"\bmezcle medicamentos\b",
            r"\bmezcle\b.{0,30}\b"
            r"(?:medicamentos|pastillas)\b",
        ),
                "acute_intoxication": (
            r"\bsobredosis\b",
            r"\bme tome demasiad[oa]s?\b.{0,30}\b(?:pastillas|medicamentos)\b",
            r"\btome demasiad[oa]s?\b.{0,30}\b(?:pastillas|medicamentos)\b",
            r"\bme tome much[oa]s?\b.{0,30}\b(?:pastillas|medicamentos)\b",
            r"\btome much[oa]s?\b.{0,30}\b(?:pastillas|medicamentos)\b",
            r"\bme tome todas\b.{0,20}\b(?:las pastillas|los medicamentos)\b",
            r"\btome todas\b.{0,20}\b(?:las pastillas|los medicamentos)\b",
            r"\bingeri demasiad[oa]s?\b.{0,30}\b(?:pastillas|medicamentos)\b",
            r"\bconsumi demasiad[oa]s?\b.{0,30}\b(?:pastillas|medicamentos|sustancias)\b",
        ),
        "immediate_danger": (
    r"\bya lo voy a hacer\b",
    r"\blo voy a hacer ahora\b",
    r"\blo hare ahora\b",
    r"\bvoy a hacerlo ahora\b",
    r"\bvoy a hacerlo ahora mismo\b",
    r"\bpienso hacerlo ahora\b",
    r"\bno puedo mantenerme a salvo\b",
    r"\bno creo poder mantenerme a salvo\b",
    r"\bno puedo garantizar mi seguridad\b",
),
        
    }

    VALIDATION_PATTERNS = (r"\btiene sentido que\b", r"\bes comprensible que\b", r"\bpuedo entender que\b", r"\bparece que esto te\b", r"\bsuena como si\b", r"\bdebe ser dificil\b", r"\bentiendo que\b", r"\bgracias por contar(?:me|lo)\b", r"\blo que sientes es valido\b", r"\btu reaccion es comprensible\b")
    MINIMIZATION_PATTERNS = (r"\bno es para tanto\b", r"\bsolo animate\b", r"\banimate\b", r"\bdeja de pensar en eso\b", r"\bno tienes por que sentirte asi\b", r"\botros estan peor\b", r"\bse te va a pasar\b", r"\bexageras\b", r"\bes una tonteria\b")
    BLAME_PATTERNS = (r"\bes tu culpa\b", r"\btu te lo buscaste\b", r"\bdeberias haber\b", r"\bpor que permitiste\b", r"\bsi estas asi es porque\b", r"\btu problema es que\b", r"\bdeja de hacerte la victima\b", r"\bsolo depende de ti\b")
    ALARMIST_PATTERNS = (r"\besto va a terminar muy mal\b", r"\bseguro ocurrira lo peor\b", r"\bno hay ninguna salida\b", r"\btu vida esta destruida\b", r"\bnunca vas a recuperarte\b", r"\bes una catastrofe\b", r"\btodo esta perdido\b")
    DIAGNOSTIC_PATTERNS = (r"\btienes depresion\b", r"\btienes ansiedad\b", r"\beres bipolar\b", r"\btienes trastorno\b", r"\besto es claramente\b.{0,25}\btrastorno\b", r"\bte diagnostico\b", r"\bpadeces de\b", r"\beres (?:un|una) narcisista\b")
    PROFESSIONAL_SUPPORT_PATTERNS = (r"\bpsicolog[oa]\b", r"\bpsiquiatra\b", r"\bprofesional de salud mental\b", r"\bterapeuta\b", r"\bmedic[oa]\b", r"\bservicio de salud\b", r"\bcentro de salud\b", r"\bapoyo profesional\b", r"\blinea de apoyo\b")
    EMERGENCY_SUPPORT_PATTERNS = (r"\bayuda de emergencia\b",
    r"\bayuda urgente\b",
    r"\batencion de emergencia\b",
    r"\batencion urgente\b",
    r"\bbusca ayuda de emergencia\b",
    r"\bbusca ayuda urgente\b",
    r"\bcontacta a emergencias\b",
    r"\bcontacta al servicio de emergencias\b",
    r"\bcontacta con emergencias\b",r"\bemergencias\b", r"\bservicio de emergencia\b", r"\bnumero de emergencias\b", r"\blinea de crisis\b", r"\burgencias\b", r"\bpolicia\b", r"\bambulancia\b", r"\bllama al 123\b", r"\bllama al 911\b", r"\bllama al 112\b")
    AUTONOMY_PATTERNS = (r"\btu decides\b", r"\bla decision es tuya\b", r"\bpuedes elegir\b", r"\bpodrias considerar\b", r"\buna opcion seria\b", r"\bque alternativa te resulta\b", r"\bque paso te parece posible\b", r"\bsegun tus preferencias\b", r"\bvalora que opcion\b", r"\bajustalo a lo que necesites\b")
    DEPENDENCY_PATTERNS = (r"\bsolo yo te entiendo\b", r"\bno necesitas a nadie mas\b", r"\bsiempre estare aqui para ti\b", r"\bpuedes depender de mi\b", r"\bconsultame cada vez que\b", r"\bsoy todo lo que necesitas\b", r"\bno hables con nadie mas\b", r"\bsoy tu terapeuta\b", r"\bsoy tu mejor amig[oa]\b")
    ACTION_PATTERNS = (r"\bprueba\b", r"\bintenta\b", r"\bpuedes hacer\b", r"\bprimer paso\b", r"\banota\b", r"\bescribe\b", r"\brespira\b", r"\bcontacta\b", r"\bhabla con\b", r"\balejate\b", r"\bbusca\b", r"\borganiza\b", r"\bdivide\b", r"\bidentifica\b", r"\belige\b", r"\brevisa\b",r"\bpuedes empezar por\b",r"\bempieza por\b",r"\bcomienza por\b",r"\bpuedes comenzar por\b",)
    CLARIFICATION_PATTERNS = (r"\bpodrias contarme\b", r"\bque quieres decir con\b", r"\bcuando dices\b", r"\bque necesitas ahora\b", r"\bque seria mas util\b", r"\bquieres que te escuche\b", r"\bnecesitas informacion\b", r"\bpuedes aclarar\b", r"\bcomo ha afectado\b", r"\bdesde cuando\b", r"\bque parte de\b.{0,60}\bte preocupa\b",r"\bque es lo que mas te preocupa\b",r"\bque aspecto te preocupa mas\b", r"\bque parte te resulta mas dificil\b")
    SAFETY_QUESTION_PATTERNS = (r"\bhas pensado en hacerte dano\b", r"\bhas pensado en morir\b", r"\bpiensas quitarte la vida\b", r"\btienes intencion de\b.{0,30}\bhacerte dano\b", r"\btienes un plan\b", r"\btienes acceso a\b.{0,25}(?:arma|medicamentos|medios)\b", r"\bcuando pensabas hacerlo\b", r"\bpuedes mantenerte a salvo\b", r"\bestas en peligro ahora\b", r"\bestas sol[oa]\b", r"\bhay alguien contigo\b")
    ABSOLUTE_LANGUAGE_PATTERNS = (r"\bsiempre\b", r"\bnunca\b", r"\btodo\b", r"\bnada\b", r"\bnadie\b", r"\bseguro que\b", r"\bsin ninguna duda\b", r"\bdefinitivamente\b", r"\bimposible\b")
    UNCERTAINTY_PATTERNS = (r"\bpuede que\b", r"\bpodria\b", r"\bparece\b", r"\bquizas\b", r"\btal vez\b", r"\bes posible\b", r"\bno puedo saberlo con certeza\b", r"\bcon la informacion disponible\b")
    TECHNICAL_JARGON_PATTERNS = (r"\bdisregulacion\b", r"\bcomorbilidad\b", r"\bdistorsion cognitiva\b", r"\bideacion\b", r"\banhedonia\b", r"\bhipervigilancia\b", r"\bdisociacion\b", r"\bdesrealizacion\b", r"\bdespersonalizacion\b", r"\bsintomatologia\b")

    NEGATION_WORDS = {"no", "nunca", "jamas", "sin", "tampoco", "ni"}
    QUESTION_WORDS = {"que", "como", "cuando", "donde", "quien", "cual", "cuanto", "por que", "para que"}
    NEGATION_SENSITIVE_RISK_CATEGORIES = {"violence"}

    LIST_ITEM_PATTERN = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+")
    SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")

    def __init__(self) -> None:
        self._compiled_emotions = self._compile_mapping(self.EMOTION_PATTERNS)
        self._compiled_risks = self._compile_mapping(self.RISK_PATTERNS)
        self._compiled_groups: dict[str, list[Pattern[str]]] = {
            "validation_signals": self._compile(self.VALIDATION_PATTERNS),
            "minimization_signals": self._compile(self.MINIMIZATION_PATTERNS),
            "blame_signals": self._compile(self.BLAME_PATTERNS),
            "alarmist_signals": self._compile(self.ALARMIST_PATTERNS),
            "diagnostic_signals": self._compile(self.DIAGNOSTIC_PATTERNS),
            "professional_support_signals": self._compile(self.PROFESSIONAL_SUPPORT_PATTERNS),
            "emergency_support_signals": self._compile(self.EMERGENCY_SUPPORT_PATTERNS),
            "autonomy_signals": self._compile(self.AUTONOMY_PATTERNS),
            "dependency_signals": self._compile(self.DEPENDENCY_PATTERNS),
            "action_signals": self._compile(self.ACTION_PATTERNS),
            "clarification_signals": self._compile(self.CLARIFICATION_PATTERNS),
            "safety_question_signals": self._compile(self.SAFETY_QUESTION_PATTERNS),
            "absolute_language_signals": self._compile(self.ABSOLUTE_LANGUAGE_PATTERNS),
            "uncertainty_signals": self._compile(self.UNCERTAINTY_PATTERNS),
            "technical_jargon_signals": self._compile(self.TECHNICAL_JARGON_PATTERNS),
        }

    @staticmethod
    def normalize(text: str) -> str:
        text = str(text or "").strip().lower()
        decomposed = unicodedata.normalize("NFD", text)
        without_accents = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", without_accents).strip()

    @staticmethod
    def _compile(patterns: Iterable[str]) -> list[Pattern[str]]:
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def _compile_mapping(self, mapping: dict[str, tuple[str, ...]]) -> dict[str, list[Pattern[str]]]:
        return {key: self._compile(patterns) for key, patterns in mapping.items()}

    def analyze(self, text: str) -> TextAnalysis:
        original = str(text or "").strip()
        normalized = self.normalize(original)
        if not original:
            return TextAnalysis("", "", 0, 0, 0, 0, 0, 0)
        analysis = TextAnalysis(
            original_text=original,
            normalized_text=normalized,
            word_count=len(re.findall(r"\b\w+\b", normalized)),
            sentence_count=self._count_sentences(original),
            question_count=original.count("?"),
            exclamation_count=original.count("!"),
            paragraph_count=self._count_paragraphs(original),
            list_item_count=len(self.LIST_ITEM_PATTERN.findall(original)),
        )
        analysis.emotions = self._find_mapping_matches(original, normalized, self._compiled_emotions, "emotion")
        analysis.risk_signals = self._find_mapping_matches(original, normalized, self._compiled_risks, "risk")
        for field_name, patterns in self._compiled_groups.items():
            setattr(analysis, field_name, self._find_matches(original, normalized, patterns, field_name))
        return analysis

    def analyze_pair(self, user_message: str, ai_response: str) -> dict[str, TextAnalysis]:
        return {"user": self.analyze(user_message), "ai": self.analyze(ai_response)}

    def detect_shared_terms(self, source_text: str, target_text: str, *, minimum_length: int = 4) -> list[str]:
        return sorted(self._content_tokens(source_text, minimum_length=minimum_length).intersection(self._content_tokens(target_text, minimum_length=minimum_length)))

    def extract_questions(self, text: str) -> list[str]:
        candidates = re.findall(r"[^¿?]*\?", str(text or ""), flags=re.DOTALL)
        return [self._clean_evidence(c) for c in candidates if self._clean_evidence(c)]

    def contains_direct_question(self, text: str) -> bool:
        normalized = self.normalize(text)
        if "?" in str(text or ""):
            return True
        return any(normalized.startswith(word + " ") for word in self.QUESTION_WORDS)

    def contains_negation_near(self, text: str, phrase: str, *, token_window: int = 3) -> bool:
        normalized_text = self.normalize(text)
        normalized_phrase = self.normalize(phrase)
        index = normalized_text.find(normalized_phrase)
        if index < 0:
            return False
        previous_tokens = re.findall(r"\b\w+\b", normalized_text[:index])[-token_window:]
        return any(token in self.NEGATION_WORDS for token in previous_tokens)

    def is_overloaded_chat_response(self, text: str, *, maximum_words: int = 450, maximum_list_items: int = 10, maximum_paragraphs: int = 12) -> bool:
        analysis = self.analyze(text)
        return analysis.word_count > maximum_words or analysis.list_item_count > maximum_list_items or analysis.paragraph_count > maximum_paragraphs

    def is_too_brief_for_support(self, text: str, *, minimum_words: int = 12) -> bool:
        return self.analyze(text).word_count < minimum_words

    def has_emotion_alignment(self, user_message: str, ai_response: str) -> bool:
        pair = self.analyze_pair(user_message, ai_response)
        user_emotions = {m.value for m in pair["user"].emotions}
        ai_emotions = {m.value for m in pair["ai"].emotions}
        return bool(user_emotions.intersection(ai_emotions))

    def has_specific_reference(self, user_message: str, ai_response: str, *, minimum_shared_terms: int = 2) -> bool:
        return len(self.detect_shared_terms(user_message, ai_response)) >= minimum_shared_terms

    def find_risk_categories(self, text: str) -> set[str]:
        return {m.value for m in self.analyze(text).risk_signals}

    def _find_mapping_matches(
        self,
        original: str,
        normalized: str,
        mapping: dict[str, list[Pattern[str]]],
        category: str,
    ) -> list[TextMatch]:
        matches: list[TextMatch] = []
        for value, patterns in mapping.items():
            value_matches = self._find_matches(
                original, normalized, patterns, category, value
            )
            if (
                category == "risk"
                and value in self.NEGATION_SENSITIVE_RISK_CATEGORIES
            ):
                value_matches = [
                    match for match in value_matches
                    if not self._is_negated_risk_match(normalized, match)
                ]
            matches.extend(value_matches)
        return self._deduplicate_matches(matches)

    def _is_negated_risk_match(
        self,
        normalized_text: str,
        match: TextMatch,
    ) -> bool:
        """Detecta negación directa de una conducta violenta."""
        left_context = normalized_text[max(0, match.start - 80):match.start]
        left_tokens = re.findall(r"\b\w+\b", left_context)

        if not left_tokens:
            return False

        # Casos como: "no quiero hacerle dano",
        # "no pienso golpearlo", "no planeo atacarlo".
        if len(left_tokens) >= 2:
            previous_two = left_tokens[-2:]
            if (
                previous_two[0] in self.NEGATION_WORDS
                and previous_two[1] in {
                    "quiero", "pienso", "planeo",
                    "pretendo", "voy", "deseo",
                }
            ):
                return True

        # Casos como: "nunca lo atacaria" o "no lo golpearia".
        recent_tokens = left_tokens[-4:]
        if any(token in {"nunca", "jamas"} for token in recent_tokens):
            return True

        if (
            "no" in recent_tokens
            and any(
                token in {"lo", "la", "le", "los", "las"}
                for token in recent_tokens
            )
        ):
            return True

        return False

    def _find_matches(self, original: str, normalized: str, patterns: list[Pattern[str]], category: str, value: str | None = None) -> list[TextMatch]:
        matches: list[TextMatch] = []
        for pattern in patterns:
            for match in pattern.finditer(normalized):
                matches.append(TextMatch(category, value or match.group(0), self._extract_original_evidence(original, normalized, match.start(), match.end()), match.start(), match.end()))
        return self._deduplicate_matches(matches)

    @staticmethod
    def _extract_original_evidence(original: str, normalized: str, start: int, end: int, context_chars: int = 70) -> str:
        if not original:
            return ""
        normalized_length = max(len(normalized), 1)
        original_length = len(original)
        scaled_start = int((start / normalized_length) * original_length)
        scaled_end = int((end / normalized_length) * original_length)
        left = max(0, scaled_start - context_chars)
        right = min(original_length, scaled_end + context_chars)
        return TextAnalyzer._clean_evidence(original[left:right])

    @staticmethod
    def _clean_evidence(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip(" \n\t-•")

    @staticmethod
    def _deduplicate_matches(matches: list[TextMatch]) -> list[TextMatch]:
        unique: list[TextMatch] = []
        seen: set[tuple[str, str, str]] = set()
        for match in sorted(matches, key=lambda item: (item.start, item.end)):
            key = (match.category, match.value, match.evidence)
            if key not in seen:
                unique.append(match)
                seen.add(key)
        return unique

    @classmethod
    def _content_tokens(cls, text: str, *, minimum_length: int) -> set[str]:
        stop_words = {"para", "como", "pero", "porque", "esta", "este", "esto", "desde", "hasta", "sobre", "entre", "tener", "tiene", "puede", "podria", "quiero", "siento", "tambien", "cuando", "donde", "quien", "cual", "mucho", "poco", "algo", "hacer", "hecho", "cada", "todo", "nada", "solo", "misma", "mismo", "estoy", "estas", "esta", "somos", "eres"}
        normalized = cls.normalize(text)
        return {token for token in re.findall(r"\b[a-z0-9]+\b", normalized) if len(token) >= minimum_length and token not in stop_words}

    @classmethod
    def _count_sentences(cls, text: str) -> int:
        fragments = [fragment.strip() for fragment in cls.SENTENCE_PATTERN.split(text) if fragment.strip()]
        return max(len(fragments), 1 if text.strip() else 0)

    @staticmethod
    def _count_paragraphs(text: str) -> int:
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
        return max(len(paragraphs), 1 if text.strip() else 0)