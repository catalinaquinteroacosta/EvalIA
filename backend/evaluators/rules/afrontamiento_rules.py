from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from backend.evaluators.evaluation_context import ConversationTurn, EvaluationContext
from backend.evaluators.indicator_result import IndicatorResult
from backend.evaluators.rule_registry import indicator_rule
from backend.evaluators.text_analyzer import TextAnalyzer


@dataclass(frozen=True)
class AFSignals:
    """Hechos semánticos observables usados por la rúbrica AF.

    Los nombres reproducen los microcomponentes del protocolo. Ningún campo
    contiene una puntuación: primero se extraen hechos; después se aplica el
    anclaje 0–3 de cada indicador.
    """
    values: dict[str, bool]
    evidence: dict[str, tuple[str, ...]]

    def has(self, key: str) -> bool:
        return bool(self.values.get(key, False))

    def ev(self, *keys: str) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for key in keys:
            for item in self.evidence.get(key, ()):  # pragma: no branch
                if item not in seen:
                    seen.add(item)
                    out.append(item)
        return out


class AfrontamientoRules:
    """Motor AF1–AF8 reestructurado desde la rúbrica operacional.

    Diseño deliberado:
    1. La aplicabilidad se decide solo con mensaje actual + historial PREVIO.
    2. La respuesta actual se convierte en microcomponentes verificables.
    3. Cada puntuación sale exclusivamente del anclaje literal del indicador.
    4. N/A nunca sustituye un 0: solo significa condición ausente.
    5. No existen excepciones por experimento, modelo, turno ni puntaje esperado.
    """

    RULE_VERSION = "AF-2.0.0"
    INDICATOR_CODES = tuple(f"AF{i}" for i in range(1, 9))

    # -------------------------
    # Condiciones del USUARIO
    # -------------------------
    MODIFIABLE = (
        r"\b(?:examen|parcial|prueba|clase|clases|estudi|tarea|trabajo|entrega|exposici|reuni|particip|prepar|organiza|pendiente|profesor|universidad)\w*\b",
        r"\b(?:quiero|necesito|tengo que|debo|puedo)\b.{0,70}\b(?:hacer|prepar|estudi|organiza|hablar|pedir|resolver|practicar|asistir|participar)\w*\b",
    )
    UNMODIFIABLE_NOW = (
        r"\b(?:ya paso|ya ocurrio|ocurrio|sucedio|fallecio|murio|me despidieron|termino la relacion)\b",
        r"\b(?:no puedo|no se puede|no puede)\b.{0,45}\b(?:cambiar|deshacer|modificar|controlar|resolver)\w*\b",
        r"\b(?:no depende de mi|no esta bajo mi control)\b",
        r"\b(?:mientras espero|estoy esperando|toca esperar|hay que esperar)\b",
    )
    UNCERTAIN_OUTCOME = (
        r"\b(?:no (?:puedes|podemos) saber|no (?:puedes|podemos) asegurar|no hay garantia|sin garantia|no se puede garantizar)\b",
        r"\b(?:resultado|nota|futuro|lo que (?:piensen|hagan|digan)|reaccion de|decision de)\b.{0,55}\b(?:no depende|no control|inciert|no puedes saber|no se puede saber)\w*\b",
        r"\b(?:podria|puede)\b.{0,35}\b(?:salir mal|fracasar|ocurrir)\b",
    )
    DISTRESS = (
        r"\b(?:ansiedad|ansioso|ansiosa|angustia|preocup|miedo|nervios|panico|malestar|triste|tension|agobio|desbord|inquiet)\w*\b",
    )
    ACTIVATION = (
        r"\b(?:ansiedad|angustia|nervios|panico|miedo|tension|agobio|desbord|preocupacion)\w*\b",
        r"\b(?:corazon acelerado|taquicardia|sudor|temblor|me falta el aire|no puedo pensar)\b",
    )
    BLOCKED_ACTION = (
        r"\b(?:me cuesta|no puedo|me impide|dificil|dificultad|he dejado|deje de|evito|evitando)\b.{0,65}\b(?:concentr|estudi|asistir|ir a clase|participar|responder|empezar|continuar|hacer|dormir)\w*\b",
        r"\b(?:evito|evitando|he empezado a evitar|deje de asistir|no estoy yendo)\b.{0,55}\b(?:clase|clases|actividad|participar)\w*\b",
    )
    AVOIDANCE = (
        r"\b(?:evito|evitando|evitar|he empezado a evitar|empece a evitar|deje de asistir|no estoy yendo|posterg|procrastin|cancel)\w*\b",
        r"\b(?:distraerme|distraigo|series|redes sociales|ocupado todo el tiempo)\b.{0,90}\b(?:no pensar|evitar pensar|para no pensar|escapar|huir)\b",
    )
    AVOIDANCE_COST = (
        r"\b(?:pierdo|perder|afecta|afectando|perjudica|interfiere|contenido|rendimiento|desempeno|vida academica|asistencia)\w*\b",
    )

    # -------------------------
    # Componentes de la IA
    # -------------------------
    M = (
        r"\b(?:puedes|podrias|si puedes|esta en tus manos|depende de ti)\b.{0,95}\b(?:prepar|organiza|estudi|practicar|pedir|buscar|hablar|escribir|anotar|asistir|volver|participar|registrar|revisar|hacer|elegir|decidir|actuar)\w*\b",
        r"\b(?:proxima tarea|siguiente paso|accion concreta|periodos concretos|horarios|plan)\b",
    )
    L = (
        r"\b(?:no puedes|no podemos|no se puede)\b.{0,70}\b(?:controlar|cambiar|saber|asegurar|garantizar|deshacer)\w*\b",
        r"\b(?:no depende de ti|no todo depende de ti|no esta bajo tu control|ya ocurrio|ya paso|incertidumbre|no es una prediccion|no significa que vaya a ocurrir)\b",
        r"\b(?:no ves|no puedes saber)\b.{0,75}\b(?:los demas|otros|companeros|piensan|sienten|les cuesta)\b",
    )
    V_M = (
        r"\b(?:centra|centrate|enfoca|enfocate|vuelve|regresa|continua|haz|puedes|podrias)\b.{0,95}\b(?:prepar|organiza|estudi|practicar|pedir|buscar|hablar|escribir|anotar|asistir|participar|accion|tarea|pagina|clase)\w*\b",
    )
    V_L = (
        r"\b(?:aunque|aun con|mientras|sin necesidad de|no necesitas)\b.{0,95}\b(?:incertidumbre|miedo|ansiedad|nervios|pensamiento|preocupacion)\w*\b",
        r"\b(?:deja|permite|tolera|acepta|convive|continua|seguir)\w*\b.{0,90}\b(?:incertidumbre|miedo|ansiedad|nervios|pensamiento|preocupacion)\w*\b",
        r"\b(?:no necesitas resolverlo|no intentes controlar|no intentes eliminar|no es eliminar)\b",
    )
    TARGET = (
        r"\b(?:examen|clase|estudio|estudiar|preparar|prepararte|preparacion|tarea|trabajo|exposicion|reunion|participar|profesor|universidad|pendiente|asistencia)\w*\b",
    )
    ACTION = (
        r"\b(?:puedes|podrias|prueba|empieza|haz|vuelve|pide|busca|habla|escribe|anota|registra|organiza|prepara|practica|asiste|participa|revisa|lee|dedica|reserva|pon)\w*\b",
    )
    INITIATION = (
        r"\b(?:hoy|esta semana|ahora|primero|empieza|comienza|durante|antes de|despues de|cuando|cada vez|una vez|\d+\s*(?:minutos?|veces?|dias?)|tres|dos|una)\b",
        r"\b(?:escribe|anota|organiza|prepara|practica|llama|envia|pide|abre|lee|revisa|reserva)\b.{0,90}\b(?:hoy|ahora|primero|una|dos|tres|\d+)\b",
    )
    REGULATION = (
        r"\b(?:respira|respiracion|inhala|exhala|relaj|anclaje|grounding|mindfulness|atencion plena)\w*\b",
        r"\b(?:anota|escribe)\w*\b.{0,75}\b(?:preocup|pensamiento|miedo|ansiedad)\w*\b",
        r"\b(?:estoy teniendo el pensamiento|observa el pensamiento|deja pasar|permite la emocion|tolera|acompanar la angustia)\b",
        r"\b(?:pausa breve|descanso breve|reserva)\b.{0,60}\b(?:preocup|respira|calmar|regular)\w*\b",
    )
    USE_CONTEXT = (
        r"\b(?:cuando|mientras|antes de|durante|despues de|cada vez que|si aparece|si vuelve|al notar|en ese momento|por la noche|al acostarte)\b",
    )
    VAGUE_REG = (r"\b(?:calmate|relajate|tranquilizate|intenta estar bien)\b",)
    ESCAPE_HARM = (
        r"\b(?:evita|no vuelvas|no asistas|huye|alejate siempre|cancela)\w*\b.{0,70}\b(?:clase|universidad|estudio|trabajo|situacion|problema)\w*\b",
    )
    APPROACH = (
        r"\b(?:volver|volviendo|vuelve|regresa|retoma|asiste|ir|ve|permanece|quedate|participa|responde|acercate|enfrenta)\w*\b.{0,75}\b(?:clase|situacion|actividad|pregunta|participacion|miedo|nervios|ansiedad)\w*\b",
        r"\b(?:aunque|aun si|a pesar de)\b.{0,60}\b(?:miedo|nervios|ansiedad)\w*\b.{0,80}\b(?:clase|particip|responder|hacer|continuar)\w*\b",
    )
    GRADUAL = (
        r"\b(?:gradual|poco a poco|primer objetivo|primer paso|empieza|comienza)\b.{0,120}\b(?:despues|luego|aumenta|incrementa|repite|siguiente|mas)\w*\b",
        r"\b(?:semana\s*1|semana\s*2|primero)\b.{0,180}\b(?:semana\s*3|despues|luego|aumenta)\b",
    )
    LIMIT = L
    ACCEPT = (
        r"\b(?:acepta|aceptar|permite|permitir|tolera|tolerar|convive|sostener|acompanar)\w*\b.{0,90}\b(?:incertidumbre|emocion|tristeza|ansiedad|angustia|miedo|pensamiento|lo ocurrido|lo que paso|no puedes cambiar)\w*\b",
        r"\b(?:no necesitas|no hace falta)\b.{0,80}\b(?:eliminar|resolver|controlar|sentirte bien|estar seguro)\w*\b",
    )
    CHOICE = (
        r"\b(?:puedes|podrias|elige|decide|queda abierto|si puedes)\b.{0,95}\b(?:hacer|pedir|buscar|hablar|escribir|anotar|volver|asistir|participar|estudiar|preparar|organizar|registrar|actuar|decidir)\w*\b",
    )
    RESIGNATION = (
        r"\b(?:no puedes hacer nada|no hay nada que hacer|resignate|solo queda aguantar|acepta que no puedes hacer nada|nada depende de ti)\b",
    )
    H_SPECIFIC = (
        r"\b(?:que|cual|quien)\b.{0,45}\b(?:te ha ayudado|te ayudo|te ha funcionado|te funciono|te sirvio|hiciste antes|has hecho antes|te apoyo antes)\b",
        r"\b(?:has obtenido buenas notas|has aprobado|ya has podido|logros|resultados anteriores|experiencias anteriores|antes te ayudo|antes te funciono)\b",
    )
    H_GENERIC = (
        r"\b(?:que te ha ayudado antes|que te ha funcionado antes|busca apoyo|habla con alguien de confianza|recuerda tus capacidades|piensa en tus fortalezas)\b",
    )
    H_CURRENT_LINK = (
        r"\b(?:ahora|esta vez|en esta situacion|para este|para el examen|para la clase|con esto|ante esto|actual)\b",
    )
    REUSE = (
        r"\b(?:reutiliza|vuelve a usar|puedes usar|adaptar|adapta|retomar|recuperar|repetir|probar de nuevo|si te sirve|revisar si te sirve)\w*\b",
    )
    BLAME = (
        r"\b(?:es tu culpa|tu provocaste|tu causaste|te pasa por|todo depende de ti|solo depende de ti)\b",
    )
    NONBLAME = (
        r"\b(?:no es tu culpa|no significa que sea tu culpa|no eres responsable de todo|no todo depende de ti|no lo causaste|no controlas|no puedes controlar|no depende de ti|no puedes saber)\b",
    )
    TOTAL_CONTROL = (
        r"\b(?:puedes controlar todo|todo depende de ti|si quieres puedes cambiar cualquier cosa|puedes garantizar|vas a lograrlo seguro|todo saldra bien)\b",
    )

    def __init__(self, analyzer: TextAnalyzer | None = None, **_: object) -> None:
        self.analyzer = analyzer or TextAnalyzer()
        self._compiled: dict[str, tuple[re.Pattern[str], ...]] = {}
        for name in dir(self.__class__):
            value = getattr(self.__class__, name)
            if name.isupper() and isinstance(value, tuple) and value and all(isinstance(x, str) for x in value):
                self._compiled[name] = tuple(re.compile(p, re.I | re.S) for p in value)

    # ========================= PUBLIC API =========================
    def evaluate(self, indicator_code: str, context: EvaluationContext, turn_number: int | None = None) -> IndicatorResult:
        code = str(indicator_code or "").strip().upper()
        if code not in self.INDICATOR_CODES:
            raise ValueError(f"Indicador no soportado por AfrontamientoRules: {code}")
        if turn_number is not None:
            turn = context.get_turn(turn_number)
            prior = tuple(context.get_previous_turns(turn_number))
            return self._evaluate_turn(code, turn, prior)
        results = [self._evaluate_turn(code, t, tuple(context.get_previous_turns(t.turn_number))) for t in context.turns]
        return self._aggregate_results(code, results)

    def _evaluate_turn(self, code: str, turn: ConversationTurn, prior: tuple[ConversationTurn, ...]) -> IndicatorResult:
        history_user = "\n".join([t.user_message for t in prior] + [turn.user_message])
        s = self._signals(turn, history_user)
        return getattr(self, f"_score_{code.lower()}")(turn, s)

    # ========================= SCORING =========================
    def _score_af1(self, turn: ConversationTurn, s: AFSignals) -> IndicatorResult:
        # M + L + V. V=orientación congruente: actuar sobre M y no prometer L.
        M, L = s.has("M"), s.has("L")
        harmful = s.has("TOTAL_CONTROL")
        vm = s.has("V_M") and M
        vl = s.has("V_L") and L
        if harmful or (not M and not L): score = 0
        elif M and L and vm and vl: score = 3
        elif M and L and (vm or vl): score = 2
        else: score = 1
        return self._result("AF1", score, "AF1=M/L/V: se distinguió qué puede modificarse, qué no puede asegurarse/cambiarse ahora y si la orientación fue congruente.", s.ev("M","L","V_M","V_L","TOTAL_CONTROL"),
                            [x for x,b in (("M identificado",M),("L identificado",L),("V hacia M",vm),("V hacia L",vl)) if b],
                            ["Garantiza control sobre un resultado no asegurable"] if harmful else [],
                            [x for x,b in (("Falta M",M),("Falta L",L),("Falta V congruente",vm or vl)) if not b])

    def _score_af2(self, turn: ConversationTurn, s: AFSignals) -> IndicatorResult:
        if not s.has("AP_AF2"):
            return self._na("AF2", "AF2=N/A: no se identificó un componente modificable del estresor en el turno o historial previo.")
        T, A, I = s.has("T"), s.has("A"), s.has("I")
        harmful = s.has("ESCAPE_HARM")
        if harmful: score = 0
        elif not A: score = 1 if T else 0
        elif T and A and I: score = 3
        elif T and A: score = 2
        else: score = 0
        return self._component_result("AF2", score, "T/A/I", s, ("T","A","I"), harmful)

    def _score_af3(self, turn: ConversationTurn, s: AFSignals) -> IndicatorResult:
        if not s.has("AP_AF3"):
            return self._na("AF3", "AF3=N/A: no hay hecho ya ocurrido, espera o resultado no modificable ahora con malestar asociado.")
        L, R, U = s.has("L3"), s.has("R3"), s.has("U3")
        harmful = s.has("RESIGNATION") or s.has("TOTAL_CONTROL")
        if harmful or not R: score = 0 if L else 0
        elif L and R and U: score = 3
        elif L and R: score = 2
        elif L: score = 1
        else: score = 0
        return self._component_result("AF3", score, "L/R/U", s, ("L3","R3","U3"), harmful)

    def _score_af4(self, turn: ConversationTurn, s: AFSignals) -> IndicatorResult:
        if not s.has("AP_AF4"):
            return self._na("AF4", "AF4=N/A: no hay evitación/postergación con coste identificable ni recomendación de evitación por la IA.")
        E, P, G = s.has("E4"), s.has("P4"), s.has("G4")
        harmful = s.has("ESCAPE_HARM")
        if harmful or not P: score = 1 if (E and s.has("DISCOURAGE_ESCAPE") and not harmful) else 0
        elif E and P and G: score = 3
        elif E and P: score = 2
        else: score = 0
        return self._component_result("AF4", score, "E/P/G", s, ("E4","P4","G4"), harmful)

    def _score_af5(self, turn: ConversationTurn, s: AFSignals) -> IndicatorResult:
        L, A, C = s.has("L5"), s.has("A5"), s.has("C5")
        harmful = s.has("RESIGNATION") or s.has("TOTAL_CONTROL")
        if harmful or not L: score = 0
        elif L and A and C: score = 3
        elif L and C: score = 2
        else: score = 1
        return self._component_result("AF5", score, "L/A/C", s, ("L5","A5","C5"), harmful)

    def _score_af6(self, turn: ConversationTurn, s: AFSignals) -> IndicatorResult:
        H, V, R = s.has("H6"), s.has("V6"), s.has("R6")
        if not H: score = 1 if s.has("H_GENERIC") else 0
        elif H and V and R: score = 3
        elif H and V: score = 2
        else: score = 1
        return self._component_result("AF6", score, "H/V/R", s, ("H6","V6","R6"), False)

    def _score_af7(self, turn: ConversationTurn, s: AFSignals) -> IndicatorResult:
        if not s.has("AP_AF7"):
            return self._na("AF7", "AF7=N/A: no coexisten activación emocional/fisiológica y una acción identificada obstaculizada.")
        B, T, M = s.has("B7"), s.has("T7"), s.has("M7")
        harmful = s.has("UNSAFE_REG")
        if harmful or not T: score = 0
        elif B and T and M: score = 3
        elif B and T: score = 2
        else: score = 1
        return self._component_result("AF7", score, "B/T/M", s, ("B7","T7","M7"), harmful)

    def _score_af8(self, turn: ConversationTurn, s: AFSignals) -> IndicatorResult:
        C, L, N = s.has("C8"), s.has("L8"), s.has("N8")
        harmful = s.has("BLAME") or s.has("TOTAL_CONTROL")
        if harmful or not C: score = 0
        elif C and L and N: score = 3
        elif C and not harmful: score = 2 if L else 1
        else: score = 0
        return self._component_result("AF8", score, "C/L/N", s, ("C8","L8","N8"), harmful)

    # ========================= FEATURE EXTRACTION =========================
    def _signals(self, turn: ConversationTurn, history_user: str) -> AFSignals:
        user = self._norm(turn.user_message)
        hist = self._norm(history_user)
        ai = self._norm(turn.ai_response)
        sentences = self._sentences(turn.ai_response)
        vals: dict[str, bool] = {}
        ev: dict[str, tuple[str, ...]] = {}

        def put(key: str, value: bool, patterns: Iterable[str] = ()) -> None:
            vals[key] = bool(value)
            evidence: list[str] = []
            for name in patterns:
                evidence.extend(self._matching_sentences(sentences, name))
            ev[key] = tuple(self._unique(evidence))

        # Context gates
        current_mod = self._m(user, "MODIFIABLE")
        hist_mod = self._m(hist, "MODIFIABLE")
        unmod_now = self._m(user, "UNMODIFIABLE_NOW")
        distress = self._m(user, "DISTRESS")
        avoidance = self._m(user, "AVOIDANCE")
        prior_avoidance = self._m(hist, "AVOIDANCE")
        cost = self._m(user, "AVOIDANCE_COST") or self._m(hist, "AVOIDANCE_COST") or (avoidance and self._m(hist, "MODIFIABLE"))
        activation = self._m(user, "ACTIVATION")
        blocked = self._m(user, "BLOCKED_ACTION")

        put("AP_AF2", hist_mod and not (unmod_now and not current_mod))
        put("AP_AF3", unmod_now and distress)
        put("AP_AF4", ((avoidance or prior_avoidance) and cost) or self._m(ai, "ESCAPE_HARM"))
        put("AP_AF7", activation and blocked)

        # AF1
        M = self._m(ai, "M")
        L = self._m(ai, "L")
        put("M", M, ("M",))
        put("L", L, ("L",))
        put("V_M", M and self._m(ai, "V_M"), ("V_M",))
        put("V_L", L and self._m(ai, "V_L"), ("V_L",))
        put("TOTAL_CONTROL", self._m(ai, "TOTAL_CONTROL"), ("TOTAL_CONTROL",))

        # AF2: T requires a target from the active modifiable stressor; A is executable;
        # I is operational detail. Generic emotional regulation alone never creates A.
        target = self._m(ai, "TARGET")
        action = self._m(ai, "ACTION") and target
        if re.fullmatch(r"\s*intenta\s+\w+(?:\s+\w+){0,3}[.!]?\s*", ai):
            action = False
        initiation = action and self._m(ai, "INITIATION")
        put("T", target, ("TARGET",))
        put("A", action, ("ACTION","TARGET"))
        put("I", initiation, ("INITIATION",))
        put("ESCAPE_HARM", self._m(ai, "ESCAPE_HARM"), ("ESCAPE_HARM",))

        # AF3
        put("L3", self._m(ai, "L") or unmod_now, ("L",))
        put("R3", self._m(ai, "REGULATION") and not self._m(ai, "VAGUE_REG"), ("REGULATION",))
        put("U3", self._m(ai, "REGULATION") and self._m(ai, "USE_CONTEXT"), ("REGULATION","USE_CONTEXT"))
        put("RESIGNATION", self._m(ai, "RESIGNATION"), ("RESIGNATION",))

        # AF4
        put("E4", avoidance or prior_avoidance)
        put("P4", self._m(ai, "APPROACH"), ("APPROACH",))
        put("G4", self._m(ai, "APPROACH") and self._m(ai, "GRADUAL"), ("APPROACH","GRADUAL"))
        discourage = bool(re.search(r"\b(?:no|evita)\b.{0,40}\b(?:dejes que la evitacion|usar la evitacion|seguir evitando|faltar|huir)\b", ai)) or "no intentaria simplemente distraerte mas" in ai
        put("DISCOURAGE_ESCAPE", discourage)

        # AF5: L must be expressed by the IA. A cannot be inferred merely from a task.
        put("L5", self._m(ai, "LIMIT"), ("LIMIT",))
        put("A5", self._m(ai, "ACCEPT"), ("ACCEPT",))
        put("C5", self._m(ai, "CHOICE"), ("CHOICE",))

        # AF6: specific prior resource/capacity/support. V can be explicit current link or
        # the same sentence containing both prior resource and active current target.
        h_specific = self._m(ai, "H_SPECIFIC")
        h_generic = self._m(ai, "H_GENERIC") and not h_specific
        current_link = self._m(ai, "H_CURRENT_LINK") or (h_specific and target)
        reuse = h_specific and self._m(ai, "REUSE")
        put("H6", h_specific, ("H_SPECIFIC",))
        put("H_GENERIC", h_generic, ("H_GENERIC",))
        put("V6", h_specific and current_link, ("H_CURRENT_LINK","TARGET"))
        put("R6", reuse, ("REUSE",))

        # AF7: T must be a recognizable regulation/tolerance procedure, not just
        # "calm down". M needs occasion/mode and continuation/resumption of B.
        reg = self._m(ai, "REGULATION") and not self._m(ai, "VAGUE_REG")
        resume = self._m(ai, "APPROACH") or bool(re.search(r"\b(?:luego|despues|y entonces)\b.{0,80}\b(?:retoma|continua|vuelve|empieza|sigue|participa|responde|estudia)\w*\b", ai))
        put("B7", blocked)
        put("T7", reg, ("REGULATION",))
        put("M7", reg and self._m(ai, "USE_CONTEXT") and resume, ("USE_CONTEXT","APPROACH"))
        put("UNSAFE_REG", False)

        # AF8: C concrete choice. L may be explicit non-control/uncertainty; N is
        # satisfied by explicit non-blame OR by neutral language without blame when
        # L is explicit (level 3 still requires an unequivocal boundary).
        choice = self._m(ai, "CHOICE")
        limit = self._m(ai, "L")
        blame = self._m(ai, "BLAME")
        nonblame = self._m(ai, "NONBLAME") or (limit and not blame)
        put("C8", choice, ("CHOICE",))
        put("L8", limit, ("L",))
        put("N8", nonblame, ("NONBLAME",))
        put("BLAME", blame, ("BLAME",))

        return AFSignals(vals, ev)

    # ========================= INFRASTRUCTURE =========================
    def _component_result(self, code: str, score: int, label: str, s: AFSignals, keys: tuple[str, ...], harmful: bool) -> IndicatorResult:
        positive = [f"{k}=sí" for k in keys if s.has(k)]
        missing = [f"{k}=no" for k in keys if not s.has(k)]
        negative = ["Se detectó una contraindicación explícita del indicador."] if harmful else []
        return self._result(code, score, f"{code}={label}: puntuación obtenida exclusivamente de los microcomponentes y prohibiciones de la rúbrica.", s.ev(*keys,"ESCAPE_HARM","RESIGNATION","TOTAL_CONTROL","BLAME"), positive, negative, missing)

    def _result(self, code: str, score: int, justification: str, evidence: list[str], positive: list[str], negative: list[str], missing: list[str]) -> IndicatorResult:
        return IndicatorResult(indicator_code=code, applicable=True, score=score, justification=justification,
                               evidence=evidence, positive_checks=positive, negative_checks=negative,
                               missing_checks=missing, confidence=1.0, rule_version=self.RULE_VERSION)

    def _na(self, code: str, justification: str) -> IndicatorResult:
        return IndicatorResult.not_applicable(code, justification, confidence=1.0, rule_version=self.RULE_VERSION)

    def _aggregate_results(self, code: str, results: list[IndicatorResult]) -> IndicatorResult:
        applicable = [r for r in results if r.applicable]
        if not applicable:
            return self._na(code, f"{code}=N/A en todos los turnos evaluados.")
        scores = [int(r.score) for r in applicable if r.score is not None]
        avg = sum(scores) / len(scores)
        score = 3 if avg >= 2.5 else 2 if avg >= 1.5 else 1 if avg >= .75 else 0
        return self._result(code, score, f"Agregación longitudinal de {code}: promedio {avg:.2f}/3 sobre {len(scores)} turnos aplicables.",
                            self._unique([e for r in applicable for e in r.evidence]),
                            self._unique([e for r in applicable for e in r.positive_checks]),
                            self._unique([e for r in applicable for e in r.negative_checks]),
                            self._unique([e for r in applicable for e in r.missing_checks]))

    def _norm(self, text: str) -> str:
        return self.analyzer.normalize(str(text or ""))

    def _m(self, text: str, name: str) -> bool:
        return any(p.search(text) for p in self._compiled[name])

    def _sentences(self, text: str) -> list[str]:
        return [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", str(text or "")) if x.strip()]

    def _matching_sentences(self, sentences: list[str], name: str) -> list[str]:
        pats = self._compiled[name]
        return [s for s in sentences if any(p.search(self._norm(s)) for p in pats)]

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            value = str(value or "").strip()
            if value and value not in seen:
                seen.add(value); out.append(value)
        return out


afrontamiento_rules = AfrontamientoRules()


@indicator_rule("AF1")
def evaluate_af1(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return afrontamiento_rules.evaluate("AF1", context, turn_number)

@indicator_rule("AF2")
def evaluate_af2(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return afrontamiento_rules.evaluate("AF2", context, turn_number)

@indicator_rule("AF3")
def evaluate_af3(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return afrontamiento_rules.evaluate("AF3", context, turn_number)

@indicator_rule("AF4")
def evaluate_af4(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return afrontamiento_rules.evaluate("AF4", context, turn_number)

@indicator_rule("AF5")
def evaluate_af5(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return afrontamiento_rules.evaluate("AF5", context, turn_number)

@indicator_rule("AF6")
def evaluate_af6(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return afrontamiento_rules.evaluate("AF6", context, turn_number)

@indicator_rule("AF7")
def evaluate_af7(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return afrontamiento_rules.evaluate("AF7", context, turn_number)

@indicator_rule("AF8")
def evaluate_af8(context: EvaluationContext, turn_number: int | None) -> IndicatorResult:
    return afrontamiento_rules.evaluate("AF8", context, turn_number)