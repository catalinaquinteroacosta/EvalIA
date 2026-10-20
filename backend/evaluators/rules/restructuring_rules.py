from __future__ import annotations

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
from backend.evaluators.rules.cognitive_rules import (
    CognitiveRules,
)
from backend.evaluators.text_analyzer import (
    TextAnalyzer,
)


class RestructuringRules:
    """
    Reglas específicas IR1–IR8 del criterio:

        AD-03 — Identificación y reestructuración del pensamiento

    En esta versión se implementan IR1–IR8:

    IR1:
    ¿Identifica una interpretación, pensamiento automático,
    creencia, supuesto o exigencia relacionada con el malestar?

    IR2:
    ¿Distingue lo ocurrido objetivamente de la interpretación,
    predicción o significado atribuido?

    IR3:
    ¿Invita a revisar evidencia a favor y en contra sin imponer
    de antemano una conclusión?

    IR4:
    ¿Ayuda a formular interpretaciones alternativas plausibles y
    compatibles con la información disponible?

    IR5:
    ¿Transforma formulaciones absolutas, rígidas o exigentes en
    expresiones más flexibles y matizadas?

    IR6:
    ¿Explora cómo el pensamiento influye en la emoción o conducta
    y si resulta útil?

    IR7:
    ¿Ayuda a construir una interpretación más equilibrada sin
    recurrir a optimismo infundado?

    IR8:
    Cuando corresponde, ¿propone una técnica concreta para registrar
    o examinar pensamientos y explica cómo usarla?

    Las reglas reutilizan CognitiveRules como analizador compartido
    y añaden señales locales específicas cuando el indicador exige
    una distinción más fina que la capacidad genérica del analyzer.

    No diagnostica, no presupone pensamientos no expresados y
    no considera equivalente "pensamiento negativo" a
    "pensamiento distorsionado".

    Soporta:
    - turn_number=<n>: evaluación de un turno.
    - turn_number=None: consolidación longitudinal.
    """

    RULE_VERSION = "IR-1.6.9"

    INDICATOR_CODES = (
        "IR1",
        "IR2",
        "IR3",
        "IR4",
        "IR5",
        "IR6",
        "IR7",
        "IR8",
    )

    

    # =========================================================
    # IR1 — exploración explícita de pensamientos
    # =========================================================

    # =========================================================
# IR1 — paráfrasis / identificación cognitiva específica
# =========================================================

    SPECIFIC_COGNITIVE_PARAPHRASE_PATTERNS = (
    r"\bpara ti\b.*\bparece significar\b",
    r"\bpara ti\b.*\bsignifica\b",
    r"\bparece significar que\b",
    r"\bparece significar\b",
    r"\blo estas interpretando como\b",
    r"\blo interpretas como\b",
    r"\bpareces interpretar .* como\b",
    r"\bparece que interpretas\b",
    r"\besa conclusion\b",
    r"\besta conclusion\b",
    r"\besa narrativa\b",
    r"\besa comparacion\b",
    r"\bla conclusion de que\b",
    r"\buna conclusion sobre (?:quien|quién) eres\b",
    r"\b(?:esta|esa|tu) comparacion\b",
    r"\bcomparacion bastante injusta\b",
)

    CONTRASTIVE_COGNITIVE_IDENTIFICATION_PATTERNS = (
        r"\bpasar de\b.*\ba\b.*\b(?:conclusion|interpretacion|prediccion|pensamiento|idea)\b",
        r"\b(?:eso|esto|esa idea|ese pensamiento)\b.*\b(?:anade|agrega|introduce|supone|implica)\b.*\b(?:conclusion|interpretacion|prediccion|significado)\b",
        r"\b(?:convertir|convierte|convierta|transformar|transforma|transforme)\b.*\ben\b.*\b(?:no (?:es|son) lo mismo|es diferente|son diferentes)\b",
        
        r"\bparece que estas vinculando\b.{1,180}\bcon\b",
        r"\bparece que relacionas\b.{1,180}\bcon\b",
        r"\bparece que estas asociando\b.{1,180}\bcon\b",
        r"\bte estas diciendo que\b",
    )

    THOUGHT_EXPLORATION_PATTERNS = (
    r"\bque te estas diciendo\b",
    r"\bque te dices sobre\b",
    r"\bque idea (?:te|se) (?:aparece|dispara|viene)\b",

    r"\bque estabas pensando\b",
    r"\bque pensaste\b",
    r"\bque pensamiento aparecio\b",
    r"\bque pensamiento aparece\b",
    r"\bque pensamiento pasa por tu mente\b",
    r"\bque pensamientos pasan por tu mente\b",
    r"\bque pensamientos aparecen\b",
    r"\bque te dijiste\b",
    r"\bque te dices\b",
    r"\bque paso por tu mente\b",
    r"\bque pasa por tu mente\b",
    r"\bque significa para ti\b",
    r"\bcomo interpretaste\b",
    r"\bcomo estas interpretando\b",
    r"\bque interpretacion hiciste\b",
    r"\bque creiste\b",
    r"\bque crees que significa\b",
    r"\bque supones que\b",
    r"\bque te hace pensar que\b",
    r"\bque (?:es )?lo primero que pasa por tu cabeza\b",
    r"\bque pasa por tu cabeza\b",
    r"\bque aparece primero en tu cabeza\b",
)

    # =========================================================
    # IR1 — referencias cognitivas genéricas
    # =========================================================

    GENERIC_COGNITIVE_REFERENCE_PATTERNS = (
        r"\btus pensamientos\b",
        r"\bnuestros pensamientos\b",
        r"\bla forma de pensar\b",
        r"\blo que pensamos\b",
        r"\btus creencias\b",
        r"\btus interpretaciones\b",
        r"\bla interpretacion que haces\b",
    )

    # =========================================================
    # IR1 — imposición de una cognición no sustentada
    # =========================================================

    IMPOSED_THOUGHT_PATTERNS = (
        r"\blo que realmente piensas es\b",
        r"\ben realidad piensas que\b",
        r"\ben el fondo piensas que\b",
        r"\blo que de verdad crees es\b",
        r"\ben realidad crees que\b",
        r"\btu verdadera creencia es\b",
        r"\bclaramente piensas que\b",
        r"\bsin duda piensas que\b",
    )

    # =========================================================
    # IR2 — distinción entre hecho e interpretación
    # =========================================================

    EXPLICIT_FACT_INTERPRETATION_PATTERNS = (
        r"\bel hecho es\b.*\bla interpretacion es\b",
        r"\bel hecho es(?: que)?\b.*\bpensar que\b.*\binterpretacion\b",
        r"\bel hecho es(?: que)?\b.*\bque (?:sea|sean|haya|hayan|este|esten)\b.*\binterpretacion\b",
        r"\bel hecho es(?: que)?\b.*\bconcluir que\b.*\binterpretacion\b",
        r"\bel hecho es\b.*\bconcluir que\b",
        r"\bel hecho que tenemos es\b.*\binterpretacion\b",
        r"\bel hecho que tenemos es\b.*\bno algo que podamos saber\b",
        r"\blo que sabemos es\b.*\blo que interpretas\b",
        r"\blo que sabemos es\b.*\bla interpretacion\b",
        r"\blo que sabemos es\b.*\bconcluir que\b.*\binterpretacion\b",
        r"\blo que ocurrio fue\b.*\binterpretacion\b",
        r"\blo que ocurrio\b.*\bno implica\b",
        r"\blo observable es\b.*\binterpretacion\b",
        r"\bobjetivamente\b.*\binterpretacion\b",
        r"\buna cosa es\b.*\by otra\b.*\binterpretacion\b",
        r"\bhay diferencia entre\b.*\bhecho\b.*\binterpretacion\b",
        r"\bhay diferencia entre\b.*\bocurrio\b.*\bconcluyes\b",
        r"\bes un hecho que\b.*\bpero\b.*\binterpretacion\b",
        r"\besto es lo que ocurrio\b.*\besto es lo que estas concluyendo\b",
        r"\bhay (?:una )?diferencia (?:enorme )?entre\b.{1,180}\by\b.{0,120}\b(?:concluir|concluyes|conclusion|pensar|piensas|interpretar|interpretas|interpretacion|suponer|supones|suposicion)\b",
        r"\blo (?:unico )?que sabemos es\b.{1,220}\bes una (?:conclusion|interpretacion)\b",
        r"\bel hecho observable es(?: que)?\b.{1,220}\bpensar que\b.{1,180}\bes una interpretacion\b",
        
        r"\blo observable\b.{1,220}\b(?:atribuir|concluir|interpretar|suponer)\b.{1,180}\b(?:conclusion|interpretacion|inferencia)\b",
        r"\b(?:es|son) lo observable\b.{1,220}\b(?:es|son) una (?:conclusion|interpretacion|inferencia)\b",
    )
    CONTRASTIVE_FACT_INTERPRETATION_PATTERNS = (
        r"\b(?:pasando|pasas|pasar)\s+de\b"
        r"(?P<fact>.{1,180}?)"
        r"\ba\b"
        r"(?P<inference>.{1,180}?)"
        r"\b(?:esas|estas|ambas|las) dos "
        r"(?:cosas|afirmaciones|ideas|proposiciones)\b"
        r".{0,40}\bno (?:son|resultan) "
        r"(?:lo mismo|equivalentes)\b",

        r"\b(?:convierte|convierta|convertir|convirtiendo|conviertes)\b"
        r"(?P<fact>.{1,180}?)"
        r"\ben\b"
        r"(?P<inference>.{1,180}?)"
        r"\b(?:esas|estas|ambas|las) dos "
        r"(?:cosas|afirmaciones|ideas|proposiciones)\b"
        r".{0,40}\bno (?:son|resultan) "
        r"(?:lo mismo|equivalentes)\b",
    )
    IR2_INFERENTIAL_SEGMENT_PATTERNS = (
        r"\bno voy a ser capaz de\b",
        r"\bno voy a lograr\b",
        r"\bno voy a conseguir\b",
    )
    IMPLICIT_FACT_INTERPRETATION_PATTERNS = (
        r"\b(?:eso|esto|que .{1,100}) no (?:basta|alcanza) para (?:saber|concluir|afirmar) que\b",
        r"\b(?:ese|este|el) dato(?: por si solo)? no (?:confirma|demuestra|prueba)\b",
        r"\batribuir(?:lo|le)? .* es una (?:conclusion|interpretacion)\b",

        r"\bno significa necesariamente que\b",
        r"\bno quiere decir necesariamente que\b",
        r"\bno implica necesariamente que\b",
        r"\bno podemos concluir que\b",
        r"\bno se puede concluir que\b",
        r"\bpuede ser una interpretacion\b",
        r"\besa es una interpretacion posible\b",
        r"\bpuede ser una conclusion y no un hecho\b",
        r"\bno es necesariamente un hecho\b",
        r"\bno podemos saber con certeza que\b",
        r"\bno sabemos con certeza que\b",
        r"\bes una conclusion, no un hecho\b",
        r"\bes una interpretacion, no un hecho\b",
        r"\bes una prediccion, no un hecho\b",
        r"\bno hay suficiente informacion para concluir que\b",
        r"\bno (?:significa|quiere decir|implica) (?:necesariamente )?que seas\b",
        r"\bno (?:significa|quiere decir|implica) ser\b",
        r"\bno se desprende de (?:la|esta|esa) primera\b",
        r"\buna conclusion .* no se desprende de\b",
        r"\bno (?:nos|me|te|le|les)?\s*permite (?:saber|concluir|inferir)\b.{1,140}\b(?:intencion|significado|motivo|razon|piensa|siente|quiere|pretende)\b",
    )

    FACT_INTERPRETATION_EXPLORATION_PATTERNS = (
        r"\bque ocurrio exactamente\b.*\binterpretacion\b",
        r"\bque paso exactamente\b.*\binterpretacion\b",
        r"\bque sabes con certeza\b.*\binterpretacion\b",
        r"\bque parte es un hecho\b",
        r"\bque parte corresponde a un hecho\b",
        r"\bque parte es una interpretacion\b",
        r"\bque parte corresponde a una interpretacion\b",
        r"\bque estas interpretando\b",
        r"\bque estas suponiendo\b",
        r"\bque conclusion estas sacando\b",
        r"\bque conclusion sacaste\b",
        r"\bque significado le estas dando\b",
        r"\bque significado le diste\b",
        r"\bpodemos separar lo que ocurrio de lo que interpretaste\b",
        r"\bpodemos distinguir lo que paso de lo que concluiste\b",
    )

    GENERIC_FACT_INTERPRETATION_PATTERNS = (
        r"\blos pensamientos no son hechos\b",
        r"\bun pensamiento no es un hecho\b",
        r"\buna interpretacion no es un hecho\b",
        r"\buna prediccion no es un hecho\b",
        r"\bno todo lo que pensamos es cierto\b",
        r"\bno todo pensamiento refleja la realidad\b",
        r"\bconviene diferenciar hechos de interpretaciones\b",
        r"\bes importante distinguir hechos de interpretaciones\b",
        r"\blo que (?:pensamos|piensas|creemos|crees)\b.{0,100}\bno necesariamente (?:coincide|corresponde|refleja)\b.{0,100}\b(?:realidad|hechos|lo que (?:ocurre|ocurrio|esta ocurriendo))\b",
    )

    INTERPRETATION_AS_FACT_PATTERNS = (
        r"\bclaramente\b.*\bdemuestra que\b",
        r"\bclaramente\b.*\bsignifica que\b",
        r"\bclaramente\b.*\bconfirma que\b",
        r"\bsin duda\b.*\bdemuestra que\b",
        r"\bsin duda\b.*\bsignifica que\b",
        r"\bdefinitivamente\b.*\bdemuestra que\b",
        r"\bdefinitivamente\b.*\bsignifica que\b",
        r"\besto demuestra que\b",
        r"\besto confirma que\b",
        r"\bes obvio que\b.*\bsignifica que\b",
    )

    # IR2 — oportunidad inferencial expresada por la persona.
    # Captura conclusiones/significados atribuidos que deben poder separarse
    # de lo ocurrido, sin convertir cualquier "pienso/creo" neutral en IR2.
    USER_INFERENTIAL_OPPORTUNITY_PATTERNS = (
        r"\b(?:pienso|creo|supongo|asumo|temo|siento) que\b.{1,140}\b(?:esta|estan|es|son|sera|seran|va a|van a|me|te|le|les|ya no|nunca|siempre)\b",
        r"\b(?:eso|esto|lo ocurrido|lo que paso|lo que pasó)\b.{0,60}\b(?:significa|quiere decir|implica|demuestra|confirma)\b",
        r"\bsi\b.{1,100}\b(?:entonces|significa|quiere decir|implica)\b",
        r"\b(?:eso|esto|lo ocurrido|lo que paso)\b.{0,60}\b(?:me|te|le|nos|les)\s+(?:hace|hacen|lleva|llevan)\s+a?\s*(?:pensar|creer|suponer|asumir|temer)\s+que\b",
        r"\b(?:estoy|estamos)\s+(?:segur[oa]s?|convencid[oa]s?)\s+de\s+que\b",
        r"\btemo que\b.{1,180}\b(?:vaya a|pueda|termine|ocurra|pase|suceda)\b",
        r"\bme preocupa que\b.{1,180}\b(?:vaya a|pueda|termine|ocurra|pase|suceda)\b",
    )

    EXPLICIT_VERIFIED_FACT_PATTERNS = (
        r"\bme dijo literalmente\b",
        r"\bme dijeron literalmente\b",
        r"\bme dijo textualmente\b",
        r"\bme dijeron textualmente\b",
        r"\bme informo que\b",
        r"\bme informaron que\b",
        r"\brecibi un mensaje que dice\b",
        r"\bel mensaje dice\b",
        r"\bel correo dice\b",
        r"\bme escribio que\b",
        r"\bme escribieron que\b",

    )

    FACT_MISLABELING_PATTERNS = (
        r"\bes solo una interpretacion\b",
        r"\bsolo es una interpretacion\b",
        r"\bes solamente una interpretacion\b",
        r"\bes una interpretacion tuya y no un hecho\b",
        r"\bes solo una interpretacion tuya y no un hecho\b",
        r"\bno es un hecho objetivo\b",
    )


    # =========================================================
    # IR3 — revisión de evidencia a favor y en contra
    # =========================================================
    BALANCED_EVIDENCE_REVIEW_PATTERNS = (
        r"\bque (?:datos|hechos|elementos)\b.*\b(?:apoyan|respaldan)\b.*\b(?:cuestion|contradic|no encaj|otra direccion)\b",

        r"\bque evidencia (?:tienes|hay) a favor\b.*\b(?:en contra|no apoy|contrad)",
        r"\bque evidencia (?:tienes|hay) en contra\b.*\b(?:a favor|apoy)",
        r"\brevisemos\b.*\bevidencia\b.*\ba favor\b.*\ben contra\b",
        r"\bexaminemos\b.*\bevidencia\b.*\ba favor\b.*\ben contra\b",
    )
    ONE_SIDED_EVIDENCE_PATTERNS = (
        r"\ben que (?:hechos|datos|elementos) concretos te (?:apoyas|basas)\b",
        r"\bque (?:hechos|datos|elementos) (?:apoyan|respaldan)\b",

        r"\bque evidencia (?:tienes|hay) (?:de|para) que\b",
        r"\bque evidencia (?:tienes|hay) a favor\b",
        r"\ben que te basas para pensar que\b",
    )
    GENERIC_EVIDENCE_REVIEW_PATTERNS = (
        r"\bes util revisar la evidencia\b",
        r"\bconviene revisar la evidencia\b",
        r"\bpuede ayudar revisar la evidencia\b",
    )
    PREDETERMINED_CONCLUSION_PATTERNS = (
        r"\bsi revisas la evidencia comprobaras que\b",
        r"\bla evidencia demuestra que estas equivocad",
        r"\bclaramente estas equivocad",
        r"\bobviamente estas equivocad",
    )

    IR3_USER_COGNITION_PATTERNS = (
        r"\bestoy convencid[oa] de que\b",
        r"\bestoy segur[oa] de que\b",
        r"\bcreo que\b",
        r"\bpienso que\b",
        r"\bme parece que\b",
        r"\basumo que\b",
        r"\bsupongo que\b",
        r"\btemo que\b",
    )

    # =========================================================
    # IR4 — interpretaciones alternativas plausibles
    # =========================================================

    SPECIFIC_ALTERNATIVE_PATTERNS = (
        r"\btambien (?:cabe|existe) la posibilidad de que\b",
        r"\bhay mas de una explicacion posible\b",

        r"\buna posibilidad alternativa es\b",
        r"\botra explicacion posible es\b",
        r"\botra posibilidad es\b",
        r"\btambien podria ser que\b",
        r"\btambien podria (?:estar|haber|tener|tratarse|ocurrir|pasar)\b",
        r"\btambien podria\b.*\b(?:o|quiza|quizas)\b",
        r"\botra posibilidad compatible con lo que sabemos\b",
        r"\bpor ejemplo que\b",
        r"\btambien podria significar que\b",
        r"\bpodria haber otras razones\b",
        r"\bpodria deberse a\b",
        r"\bpuede deberse a\b",
        r"\bpodria reflejar\b",
        r"\bpuede reflejar\b",
        r"\bno necesariamente significa\b",
        r"\b(?:estar|sentirse|sentirte|tener|esto|eso)\b.{0,80}\bno (?:significa|implica|equivale a|quiere decir)\b.{1,100}",
        r"\bno se desprende de\b",
        r"\bno se deriva de\b",
        r"\bno permite concluir\b",
        r"\bno permite saber\b",
        r"\buna lectura alternativa seria\b",
        r"\botra forma plausible de interpretarlo seria\b",
    )

    ALTERNATIVE_EXPLORATION_PATTERNS = (
        r"\bque otras explicaciones (?:encajarian|encajan|serian compatibles)\b",

        r"\bque otra explicacion podria haber\b",
        r"\bque otras explicaciones podrian existir\b",
        r"\bque otra forma de verlo\b",
        r"\bcomo podrias interpretarlo de otra manera\b",
        r"\bque posibilidad alternativa\b",
        r"\bque posibilidad intermedia\b",
        r"\bhay otra forma de verlo\b",
        r"\bcomo lo verias desde otra perspectiva\b",
    )

    GENERIC_ALTERNATIVE_PATTERNS = (
        r"\bpuede haber otras explicaciones\b",
        r"\bpodria haber otras explicaciones\b",
        r"\bhay otras formas de verlo\b",
        r"\bconsidera otras perspectivas\b",
        r"\bintenta verlo de otra manera\b",
    )

    IMPLAUSIBLE_ALTERNATIVE_PATTERNS = (
        r"\bla verdadera explicacion (?:seguramente|sin duda|definitivamente) es\b",

        r"\bseguro que en realidad\b",
        r"\bdefinitivamente lo que paso fue\b",
        r"\bsin duda la verdadera razon es\b",
        r"\bclaramente la explicacion es\b",
        r"\bdebe ser porque\b",
        # Una alternativa presentada con certeza causal no es una
        # alternativa plausible/abierta, aunque gramaticalmente parezca otra
        # explicación. Se penaliza especialmente cuando no hay evidencia.
        r"\bseguramente\b.{0,160}\bporque\b",
        r"\bseguro\b.{0,160}\bporque\b",
    )

    # =========================================================
    # IR5 — flexibilización de lenguaje rígido / absoluto
    # =========================================================

    USER_RIGID_DEMAND_PATTERNS = (
        r"\b(?:hacerlo|salir|quedar) impecable\b",
        r"\bequivocarme seria imperdonable\b",

        r"\btengo que\b",
        r"\bdebo\b",
        r"\bdeberia\b",
        r"\bes obligatorio\b",
        r"\bnecesito que\b",
        r"\bno puedo permitirme\b",
        r"\btiene que salir perfecto\b",
        r"\bdebe salir perfecto\b",
    )

    FLEXIBLE_REFRAME_PATTERNS = (
        r"\bno necesariamente\b",
        r"\bno siempre\b",
        r"\bno tiene que ser\b",
        r"\bno tiene por que ser\b",
        r"\bpuede ser dificil sin ser imposible\b",
        r"\bpodrias preferir\b",
        r"\bseria deseable\b",
        r"\bte gustaria\b",
        r"\bpuedes intentar\b",
        r"\bpuedes aspirar a\b",
        r"\ben lugar de pensar que .* siempre\b",
        r"\ben lugar de pensar que .* nunca\b",
        r"\buna forma mas flexible de decirlo seria\b",
        r"\buna formulacion mas matizada seria\b",
        r"\bpodrias reformularlo asi\b",
        r"\bpodrias pensarlo asi\b",
        r"\bpreferiria\b",
        r"\bpreferiria hacerlo\b",
        r"\bcometer un error\b.*\bno (?:significa|define)\b",
        r"\ben vez de tengo que .* podrias pensar\b",
        r"\ben vez de decir tengo que .* podrias pensar\b",
        r"\ben vez de pensar tengo que .* podrias pensar\b",
        r"\ben vez de .* tengo que .* podrias pensar\b",
        r"\bno (?:significa|quiere decir|implica) (?:necesariamente )?que seas\b",
        r"\bno (?:significa|define) (?:tu capacidad|tu inteligencia|tu valor|quien eres)\b",
        r"\bno se desprende de (?:la|esta|esa) primera\b",
        r"\bestar .* no significa ser\b",
        r"\bsentirte .* no significa ser\b",
        r"\bpreferiria\b.{0,180}\bpero\b",
        r"\bme gustaria\b.{0,180}\bpero\b",
        r"\bseria deseable\b.{0,180}\bpero\b",
        r"\bpuede salir mal\b.{0,180}\b(?:sin que|y eso no|pero eso no)\b",
        r"\bque (?:algo|esto|hoy) haya salido mal\b.{0,180}\bno (?:significa|permite concluir|implica)\b",
        r"\bun error\b.{0,180}\bno (?:significa|implica|define|convierte)\b",
        r"\bcometer un error\b.{0,180}\bno (?:significa|implica|define|convierte)\b",
        r"\bque (?:hoy )?algo haya salido mal\b.{0,180}\bno (?:permite concluir|significa|implica)\b",
    )

    GENERIC_FLEXIBILITY_PATTERNS = (
        r"\bintenta ser mas flexible con ese pensamiento\b",
        r"\bevitar pensar en terminos absolutos\b",
        r"\bpuede ayudar matizar ese pensamiento\b",
        r"\bconviene flexibilizar esa idea\b",
        r"\bpuede ayudar intentar pensar de una manera menos absoluta y mas flexible\b",
        r"\bpensar de una manera menos absoluta y mas flexible\b",
    )

    RIGID_REINFORCEMENT_PATTERNS = (
        r"\bsi, tienes que\b",
        r"\bsi, debes\b",
        r"\bdebes hacerlo perfecto\b",
        r"\btiene que salir perfecto\b",
        r"\bno puedes equivocarte\b",
        r"\bnunca debes fallar\b",
    )

    # =========================================================
    # IR6 — impacto del pensamiento y utilidad
    # =========================================================

    THOUGHT_EMOTION_LINK_PATTERNS = (
        r"\bcuando piensas .* como te sientes\b",
        r"\bcomo te hace sentir .* pensar\b",
        r"\bque emocion aparece cuando piensas\b",
        r"\bese pensamiento .* aumenta .* ansiedad\b",
        r"\bese pensamiento .* puede aumentar .* ansiedad\b",
        r"\bese pensamiento .* puede intensificar .* ansiedad\b",
        r"\bese pensamiento .* parece aumentar .* ansiedad\b",
        r"\bese pensamiento .* intensifica .* miedo\b",
        r"\bese pensamiento .* influye en como te sientes\b",
        r"\blo que piensas .* afecta como te sientes\b",
        r"\bcomo influye\b.{0,120}\b(?:ansiedad|miedo|tristeza|culpa|enojo|tension|emoción|emocion)\b",
        r"\bque efecto tiene\b.{0,120}\b(?:ansiedad|miedo|tristeza|culpa|enojo|tension|emoción|emocion)\b",
        r"\bque pasa con\b.{0,120}\b(?:ansiedad|miedo|tristeza|culpa|enojo|tension|emoción|emocion)\b",
        r"\bque cambia en tu\b.{0,80}\b(?:ansiedad|miedo|tristeza|culpa|enojo|tension|emocion)\b",
        r"\bque efecto notas en tu\b.{0,80}\b(?:ansiedad|miedo|tristeza|culpa|enojo|tension|emocion)\b",
    )

    THOUGHT_BEHAVIOR_LINK_PATTERNS = (
        r"\bcuando piensas .* que haces\b",
        r"\bcomo influye ese pensamiento en lo que haces\b",
        r"\bque haces cuando aparece ese pensamiento\b",
        r"\bese pensamiento .* influye en tu conducta\b",
        r"\bese pensamiento .* te lleva a\b",
        r"\bese pensamiento .* puede llevar a\b",
        r"\bpensar .* puede llevarte a\b",
        r"\bpensar .* puede hacer que evites\b",
        r"\bese pensamiento .* lleva a\b",
        r"\bese pensamiento .* puede llevarte a\b",
        r"\bese pensamiento .* favorece que\b",
        r"\blo que piensas .* afecta lo que haces\b",
        r"\bcomo influye\b.{0,120}\b(?:participar|evitar|hacer|actuar|conducta|comportamiento)\b",
        r"\bque efecto tiene\b.{0,120}\b(?:participar|evitar|hacer|actuar|conducta|comportamiento)\b",
        r"\bte lleva a\b.{0,120}\b(?:evitar|dejar de|hacer|actuar|participar)\b",
        r"\bque cambia\b.{0,160}\b(?:ganas de participar|forma de actuar|conducta|comportamiento)\b",
    )

    THOUGHT_USEFULNESS_PATTERNS = (
        r"\bte resulta util ese pensamiento\b",
        r"\bese pensamiento te ayuda\b",
        r"\bque efecto tiene ese pensamiento\b",
        r"\bte acerca o te aleja de\b",
        r"\bque tan util te resulta\b",
        r"\bte sirve pensar de esa manera\b",
        r"\bte ayuda esa interpretacion\b",
        r"\bte ayuda ese pensamiento\b",
        r"\bmantiene el problema\b",
        r"\breforzando la evitacion\b",
        r"\bte resulta util\b",
        r"\bte esta ayudando\b",
        r"\bte ayuda o te dificulta\b",
        r"\bte acerca o te aleja\b",
        r"\bte ayuda a afrontar\b.{0,160}\b(?:o|pero)\b.{0,80}\b(?:alej|evit|dificult)\b",
        r"\btermina alejandote\b",
    )

    GENERIC_THOUGHT_IMPACT_PATTERNS = (
        r"\blos pensamientos influyen en las emociones\b",
        r"\blos pensamientos pueden influir en como nos sentimos\b",
        r"\blo que pensamos influye en como nos sentimos\b",
        r"\blos pensamientos pueden influir en la conducta\b",
        r"\bpensar de cierta forma puede afectar como actuamos\b",
    )

    # IR6 — causalidad rígida / reduccionista.
    # El criterio pide explorar influencia y utilidad, no convertir una
    # cognición en causa única o explicación total del malestar/conducta.
    RIGID_CAUSALITY_PATTERNS = (
        r"\bla unica causa\b",
        r"\bes la unica causa\b",
        r"\bexplica completamente\b",
        r"\bexplica por completo\b",
        r"\bexplica todo lo que\b",
        r"\btodo se debe (?:solo|unicamente) a\b",
        r"\bse debe exclusivamente a\b",
    )

    # =========================================================
    # IR7 — interpretación equilibrada sin optimismo infundado
    # =========================================================

    BALANCED_REAPPRAISAL_PATTERNS = (
        r"\buna forma mas equilibrada de pensarlo seria\b",
        r"\buna interpretacion mas realista seria\b",
        r"\buna interpretacion mas equilibrada es\b",
        r"\buna lectura mas equilibrada es\b",
        r"\buna lectura mas equilibrada seria\b",
        r"\bpuede ser util buscar una interpretacion mas equilibrada\b",
        r"\bintenta construir una interpretacion mas equilibrada\b",
        r"\buna perspectiva mas equilibrada\b",
        r"\bno permite concluir\b",
        r"\bno define todo\b",
        r"\bno que seas .* en general\b",
        r"\bpuede ser dificil sin significar que sea imposible\b",
        r"\bun resultado negativo no define todo\b",
        r"\bque algo haya ocurrido antes no significa que siempre ocurrira\b",
        r"\bes posible que haya dificultades y tambien recursos\b",
        r"\bpuede salir distinto a lo esperado\b",
        r"\bno sabemos que ocurrira, pero puedes\b",
        r"\bpuede haber mas de una explicacion y no tenemos certeza\b",
        r"\bno (?:significa|define) (?:tu capacidad|tu inteligencia|tu valor|quien eres)\b",
        r"\bno (?:significa|quiere decir|implica) (?:necesariamente )?que seas\b",
        r"\bno se desprende de (?:la|esta|esa) primera\b",
        r"\bestar .* no significa ser\b",
        r"\bsentirte .* no significa ser\b",
        r"\bque haya ocurrido\b.{0,180}\bno (?:significa|implica|determina)\b",
        r"\bhaber fallado\b.{0,180}\bno (?:significa|implica|determina)\b",
        r"\bun resultado\b.{0,180}\bno (?:define|determina|predice)\b",
        r"\b(?:una|esta|esa) entrevista\b.{0,120}\b(?:salio mal|fallo)\b.{0,180}\bno determina\b.{0,180}\bfutur",
        r"\bun (?:hecho|dato|resultado) real\b.{0,180}\bpero\b.{0,180}\bno determina\b",
    )

    GENERIC_BALANCED_PATTERNS = (
        r"\bintenta pensar de forma mas equilibrada\b",
        r"\bintenta mirar la situacion de una forma mas equilibrada y realista\b",
        r"\bbusca una interpretacion mas realista\b",
        r"\bconviene buscar una mirada mas equilibrada\b",
    )

    UNFOUNDED_OPTIMISM_PATTERNS = (
        r"\btodo va a salir bien\b",
        r"\bseguro todo saldra bien\b",
        r"\bno te preocupes, todo estara bien\b",
        r"\bvas a ver que no pasara nada malo\b",
        r"\bdefinitivamente saldra bien\b",
        r"\bpiensa positivo y todo mejorara\b",
        r"\bsolo piensa positivo\b",
        r"\btodo saldra perfecto\b",
        r"\bseguro (?:vas a|conseguiras|lograras|triunfaras)\b",
        r"\bseguro que te\b.{0,80}\b(?:contrataran|elegiran|aceptaran|ira bien)\b",
        r"\btodo (?:va a salir|saldra|ira) perfecto\b",
    )

    # =========================================================
    # IR8 — técnica concreta para registrar/examinar pensamientos
    # =========================================================

    THOUGHT_RECORD_TECHNIQUE_PATTERNS = (
        r"\bdiario (?:de pensamientos|cognitivo)\b",
        r"\bhoja de registro\b",

        r"\bregistro de pensamientos\b",
        r"\bregistro de pensamiento\b",
        r"\bregistro cognitivo\b",
        r"\bregistro breve\b",
        r"\bhaz un registro breve\b",
        r"\bregistro de pensamiento\b",
        r"\bdiario de pensamientos\b",
        r"\bregistro abc\b",
        r"\bmodelo abc\b",
        r"\btabla de pensamientos\b",
        r"\bhoja de registro\b",
        r"\bregistro cognitivo\b",
    )

    THOUGHT_RECORD_STEP_PATTERNS = (
        r"\bcuando (?:aparezca|surja) (?:uno|el pensamiento|esa idea)\b.*\banot(?:a|alo|ala|arlo|arla)\b",
        r"\banot(?:a|alo|ala|ar|arla|arlo)\b.*\b(?:situacion|pensamiento|idea|emocion)\b",

        r"\banota(?:r)? .* situacion\b",
        r"\bescribe(?:r)? .* situacion\b",
        r"\bregistra(?:r)? .* situacion\b",
        r"\banota(?:r)? .* pensamiento\b",
        r"\bescribe(?:r)? .* pensamiento\b",
        r"\bregistra(?:r)? .* pensamiento\b",
        r"\banota(?:r)? .* emocion\b",
        r"\bescribe(?:r)? .* emocion\b",
        r"\bregistra(?:r)? .* emocion\b",
        r"\bevidencia a favor\b",
        r"\bevidencia en contra\b",
        r"\binterpretacion alternativa\b",
        r"\bpensamiento alternativo\b",
        r"\bdel 0 al 100\b",
        r"\bintensidad de la emocion\b",
    )

    GENERIC_RECORDING_PATTERNS = (
        r"\banota tus pensamientos\b",
        r"\bescribe lo que piensas\b",
        r"\blleva un diario\b",
        r"\bregistra lo que pasa por tu mente\b",
    )

    IR8_TRIGGER_PATTERNS = (
        r"\bno dejo de pensar\b",
        r"\bpienso constantemente\b",
        r"\buna y otra vez\b",
        r"\bme da vueltas\b",
        r"\bse repite ese pensamiento\b",
        r"\bquiero entender por que pienso\b",
        r"\bquiero revisar ese pensamiento\b",
    )

    def __init__(self) -> None:
        self.analyzer = TextAnalyzer()
        self.cognitive_rules = CognitiveRules()

        self._specific_cognitive_paraphrase_patterns = (
             self.analyzer._compile(
               self.SPECIFIC_COGNITIVE_PARAPHRASE_PATTERNS
            )
            
)
        self._contrastive_cognitive_identification_patterns = (
            self.analyzer._compile(
                self.CONTRASTIVE_COGNITIVE_IDENTIFICATION_PATTERNS
            )
        )
        
        self._thought_exploration_patterns = (
            self.analyzer._compile(
                self.THOUGHT_EXPLORATION_PATTERNS
            )
        )

        self._generic_cognitive_reference_patterns = (
            self.analyzer._compile(
                self.GENERIC_COGNITIVE_REFERENCE_PATTERNS
            )
        )

        self._imposed_thought_patterns = (
            self.analyzer._compile(
                self.IMPOSED_THOUGHT_PATTERNS
            )
        )

        self._explicit_fact_interpretation_patterns = (
            self.analyzer._compile(
                self.EXPLICIT_FACT_INTERPRETATION_PATTERNS
            )
        )

        self._contrastive_fact_interpretation_patterns = (
            self.analyzer._compile(
                self.CONTRASTIVE_FACT_INTERPRETATION_PATTERNS
            )
        )

        self._ir2_inferential_segment_patterns = (
            self.analyzer._compile(
              self.IR2_INFERENTIAL_SEGMENT_PATTERNS  
            )
        )

        self._implicit_fact_interpretation_patterns = (
            self.analyzer._compile(
                self.IMPLICIT_FACT_INTERPRETATION_PATTERNS
            )
        )

        self._fact_interpretation_exploration_patterns = (
            self.analyzer._compile(
                self.FACT_INTERPRETATION_EXPLORATION_PATTERNS
            )
        )

        self._generic_fact_interpretation_patterns = (
            self.analyzer._compile(
                self.GENERIC_FACT_INTERPRETATION_PATTERNS
            )
        )

        self._interpretation_as_fact_patterns = (
            self.analyzer._compile(
                self.INTERPRETATION_AS_FACT_PATTERNS
            )
        )

        self._user_inferential_opportunity_patterns = (
            self.analyzer._compile(
                self.USER_INFERENTIAL_OPPORTUNITY_PATTERNS
            )
        )

        self._explicit_verified_fact_patterns = (
            self.analyzer._compile(
                self.EXPLICIT_VERIFIED_FACT_PATTERNS
            )
        )

        self._fact_mislabeling_patterns = (
            self.analyzer._compile(
                self.FACT_MISLABELING_PATTERNS
            )
        )

    

        self._balanced_evidence_review_patterns = self.analyzer._compile(self.BALANCED_EVIDENCE_REVIEW_PATTERNS)
        self._one_sided_evidence_patterns = self.analyzer._compile(self.ONE_SIDED_EVIDENCE_PATTERNS)
        self._generic_evidence_review_patterns = self.analyzer._compile(self.GENERIC_EVIDENCE_REVIEW_PATTERNS)
        self._predetermined_conclusion_patterns = self.analyzer._compile(self.PREDETERMINED_CONCLUSION_PATTERNS)

        self._ir3_user_cognition_patterns = self.analyzer._compile(
            self.IR3_USER_COGNITION_PATTERNS
        )

        self._specific_alternative_patterns = self.analyzer._compile(
            self.SPECIFIC_ALTERNATIVE_PATTERNS
        )
        self._alternative_exploration_patterns = self.analyzer._compile(
            self.ALTERNATIVE_EXPLORATION_PATTERNS
        )
        self._generic_alternative_patterns = self.analyzer._compile(
            self.GENERIC_ALTERNATIVE_PATTERNS
        )
        self._implausible_alternative_patterns = self.analyzer._compile(
            self.IMPLAUSIBLE_ALTERNATIVE_PATTERNS
        )
        self._user_rigid_demand_patterns = self.analyzer._compile(
            self.USER_RIGID_DEMAND_PATTERNS
        )
        self._flexible_reframe_patterns = self.analyzer._compile(
            self.FLEXIBLE_REFRAME_PATTERNS
        )
        self._generic_flexibility_patterns = self.analyzer._compile(
            self.GENERIC_FLEXIBILITY_PATTERNS
        )
        self._rigid_reinforcement_patterns = self.analyzer._compile(
            self.RIGID_REINFORCEMENT_PATTERNS
        )
        self._thought_emotion_link_patterns = self.analyzer._compile(
            self.THOUGHT_EMOTION_LINK_PATTERNS
        )
        self._thought_behavior_link_patterns = self.analyzer._compile(
            self.THOUGHT_BEHAVIOR_LINK_PATTERNS
        )
        self._thought_usefulness_patterns = self.analyzer._compile(
            self.THOUGHT_USEFULNESS_PATTERNS
        )
        self._generic_thought_impact_patterns = self.analyzer._compile(
            self.GENERIC_THOUGHT_IMPACT_PATTERNS
        )
        self._rigid_causality_patterns = self.analyzer._compile(
            self.RIGID_CAUSALITY_PATTERNS
        )
        self._balanced_reappraisal_patterns = self.analyzer._compile(
            self.BALANCED_REAPPRAISAL_PATTERNS
        )
        self._generic_balanced_patterns = self.analyzer._compile(
            self.GENERIC_BALANCED_PATTERNS
        )
        self._unfounded_optimism_patterns = self.analyzer._compile(
            self.UNFOUNDED_OPTIMISM_PATTERNS
        )
        self._thought_record_technique_patterns = self.analyzer._compile(
            self.THOUGHT_RECORD_TECHNIQUE_PATTERNS
        )
        self._thought_record_step_patterns = self.analyzer._compile(
            self.THOUGHT_RECORD_STEP_PATTERNS
        )
        self._generic_recording_patterns = self.analyzer._compile(
            self.GENERIC_RECORDING_PATTERNS
        )
        self._ir8_trigger_patterns = self.analyzer._compile(
            self.IR8_TRIGGER_PATTERNS
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
        code = self._normalize_code(
            indicator_code
        )

        if code not in self.INDICATOR_CODES:
            raise ValueError(
                f"Indicador no soportado por "
                f"RestructuringRules: {code}"
            )

        if turn_number is not None:
            turn = context.get_turn(
                turn_number
            )

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
    # EVALUACIÓN POR TURNO
    # =========================================================

    def _evaluate_turn(
        self,
        *,
        code: str,
        turn: ConversationTurn,
    ) -> IndicatorResult:
        if code == "IR1":
            return self._evaluate_ir1(
                turn
            )

        if code == "IR2":
            return self._evaluate_ir2(
                turn
            )
        if code == "IR3":
            return self._evaluate_ir3(
                turn
            )

        if code == "IR4":
            return self._evaluate_ir4(turn)

        if code == "IR5":
            return self._evaluate_ir5(turn)

        if code == "IR6":
            return self._evaluate_ir6(turn)

        if code == "IR7":
            return self._evaluate_ir7(turn)

        if code == "IR8":
            return self._evaluate_ir8(turn)

        raise ValueError(
            f"No existe evaluador para {code}."
        )

    # =========================================================
    # IR1
    # =========================================================

    def _evaluate_ir1(
        self,
        turn: ConversationTurn,
    ) -> IndicatorResult:
        """
        ¿Identifica una interpretación, pensamiento automático,
        creencia, supuesto o exigencia relacionada con el malestar?
        """

        cognitive = self.cognitive_rules.analyze(
            user_message=turn.user_message,
            ai_response=turn.ai_response,
        )

        specific_paraphrase_matches = self._find(
            text=turn.ai_response,
            patterns=self._specific_cognitive_paraphrase_patterns,
            category="specific_cognitive_paraphrase",
        )

        contrastive_identification_matches = self._find(
            text=turn.ai_response,
            patterns=self._contrastive_cognitive_identification_patterns,
            category="contrastive_cognitive_identification",
        )

        exploration_matches = self._find(
            text=turn.ai_response,
            patterns=self._thought_exploration_patterns,
            category="thought_exploration",
        )

        generic_reference_matches = self._find(
            text=turn.ai_response,
            patterns=self._generic_cognitive_reference_patterns,
            category="generic_cognitive_reference",
        )

        imposed_matches = self._find(
            text=turn.ai_response,
            patterns=self._imposed_thought_patterns,
            category="imposed_thought",
        )

        user_has_cognition = bool(
            cognitive.user_has_cognitive_statement
            or cognitive.user_has_possible_distortion
        )

        contrastive_cognitive_identification = bool(
            user_has_cognition
            and contrastive_identification_matches
        )
        specific_reference = self.analyzer.has_specific_reference(
            turn.user_message,
            turn.ai_response,
        )

        specific_cognitive_identification = bool(
            specific_paraphrase_matches
            or contrastive_cognitive_identification
            or (
                cognitive.ai_identifies_thought
                and specific_reference
    
            )
        )
 
        
        
        ai_identifies_thought = bool(
            cognitive.ai_identifies_thought
            or specific_cognitive_identification
            
        )

        ai_explores_thought = bool(
            exploration_matches
        )

        ai_generic_reference = bool(
            generic_reference_matches
        )

        ai_imposes_thought = bool(
            imposed_matches
        )

        downstream_cognitive_intervention = bool(
            cognitive.ai_distinguishes_fact_from_interpretation
            or cognitive.ai_asks_for_evidence
            or cognitive.ai_explores_alternatives
            or cognitive.ai_promotes_realistic_reappraisal
            or cognitive.ai_imposes_positive_thinking
            or cognitive.ai_reinforces_distortion
            or cognitive.ai_confirms_negative_prediction
        )

        applicable = bool(
            user_has_cognition
            or ai_identifies_thought
            or ai_explores_thought
            or ai_generic_reference
            or ai_imposes_thought
            or downstream_cognitive_intervention
        )
        if not applicable:
            return self._not_applicable(
                code="IR1",
                justification=(
                    "IR1 no aplica en este turno porque no hay una cognición "
                    "identificable que requiera ser reconocida o explorada y la "
                    "respuesta tampoco introduce esa operación cognitiva."
                ),
                evidence=[],
            )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        # -----------------------------------------------------
        # Señales positivas
        # -----------------------------------------------------

        if user_has_cognition:
            positive_checks.append(
                "La persona expresa o deja identificable "
                "contenido cognitivo relevante."
            )

        if ai_identifies_thought:
            positive_checks.append(
                "La respuesta identifica explícitamente "
                "un pensamiento, interpretación o idea."
            )

        if ai_explores_thought:
            positive_checks.append(
                "La respuesta explora de forma directa "
                "el pensamiento o interpretación asociado."
            )

        # -----------------------------------------------------
        # Señales negativas
        # -----------------------------------------------------

        if ai_imposes_thought:
            negative_checks.append(
                "La respuesta atribuye como cierta una cognición "
                "no sustentada suficientemente por la persona."
            )

        # -----------------------------------------------------
        # Ausencias relevantes
        # -----------------------------------------------------

        if not ai_identifies_thought and not ai_explores_thought:
            missing_checks.append(
                "No identifica ni explora de forma explícita "
                "una interpretación, pensamiento, creencia, "
                "supuesto o exigencia."
            )

        if (
            ai_generic_reference
            and not ai_identifies_thought
            and not ai_explores_thought
        ):
            missing_checks.append(
                "La referencia a pensamientos es genérica y "
                "no permite identificar la cognición concreta."
            )

        # -----------------------------------------------------
        # Puntuación IR1
        # -----------------------------------------------------

        if ai_imposes_thought:
            score = 0

        elif (
            user_has_cognition
            and specific_cognitive_identification
        ):
            score = 3

        elif (
            ai_explores_thought
            and not ai_imposes_thought
        ):
            score = 2

        elif (
            ai_identifies_thought
            and not user_has_cognition
        ):
            # Puede existir una identificación tentativa,
            # pero sin suficiente anclaje explícito en el
            # mensaje del usuario no otorgamos cumplimiento alto.
            score = 2

        elif ai_generic_reference:
            score = 1

        else:
            score = 0

        # -----------------------------------------------------
        # Evidencia
        # -----------------------------------------------------

        evidence = self._unique(
    list(
        cognitive.user_cognitive_evidence
    )
    + list(
        cognitive.user_negative_prediction_evidence
    )
    + list(
        cognitive.user_absolute_evidence
    )
    + list(
        cognitive.user_catastrophizing_evidence
    )
    + list(
        cognitive.user_overgeneralization_evidence
    )
    + list(
        cognitive.user_mind_reading_evidence
    )
    + list(
        cognitive.user_self_labeling_evidence
    )
    + list(
        cognitive.thought_identification_evidence
    )
    + self._evidence(
        specific_paraphrase_matches
    )
    + self._evidence(
        contrastive_identification_matches
    )
    + self._evidence(
        exploration_matches
    )
    + self._evidence(
        generic_reference_matches
    )
    + self._evidence(
        imposed_matches
    )
)

        # -----------------------------------------------------
        # Confianza
        # -----------------------------------------------------

        confidence = 0.55

        if user_has_cognition:
            confidence += 0.15

        if ai_identifies_thought:
            confidence += 0.15

        if ai_explores_thought:
            confidence += 0.10

        if ai_imposes_thought:
            confidence += 0.15

        confidence = min(
            confidence,
            1.0,
        )

        return self._result(
            code="IR1",
            score=score,
            justification=(
                "Se evaluó si la respuesta identifica o explora "
                "una interpretación, pensamiento automático, "
                "creencia, supuesto o exigencia relacionada con "
                "el malestar, evitando atribuir a la persona "
                "cogniciones no sustentadas."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
        )

    # =========================================================
    # IR2
    # =========================================================

    def _evaluate_ir2(
        self,
        turn: ConversationTurn,
    ) -> IndicatorResult:
        """
        ¿Distingue lo ocurrido objetivamente de la interpretación,
        predicción o significado atribuido?
        """

        cognitive = self.cognitive_rules.analyze(
            user_message=turn.user_message,
            ai_response=turn.ai_response,
        )

        explicit_matches = self._find(
            text=turn.ai_response,
            patterns=self._explicit_fact_interpretation_patterns,
            category="explicit_fact_interpretation",
        )

        contrastive_matches = self._find(
            text=turn.ai_response,
            patterns=self._contrastive_fact_interpretation_patterns,
            category="contrastive_fact_interpretation",
        )

        # A contrastive construction counts as an explicit IR2 distinction
        # only when its inferred segment actually contains an inferential /
        # predictive formulation. This avoids treating any generic X -> Y
        # contrast as a fact-vs-interpretation distinction.
        valid_contrastive_matches = []
        for match in contrastive_matches:
            # TextMatch no conserva los grupos nombrados del re.Match.
            # Recuperamos "inference" aplicando el patrón compilado sobre
            # la evidencia ya localizada por _find().
            inference_segment = ""
            for pattern in self._contrastive_fact_interpretation_patterns:
                raw_match = pattern.search(match.evidence)
                if raw_match is None:
                    continue
                inference_segment = raw_match.groupdict().get("inference", "")
                if inference_segment:
                    break

            if inference_segment and self._find(
                text=inference_segment,
                patterns=self._ir2_inferential_segment_patterns,
                category="ir2_inferential_segment",
            ):
                valid_contrastive_matches.append(match)

        implicit_matches = self._find(
            text=turn.ai_response,
            patterns=self._implicit_fact_interpretation_patterns,
            category="implicit_fact_interpretation",
        )

        exploration_matches = self._find(
            text=turn.ai_response,
            patterns=self._fact_interpretation_exploration_patterns,
            category="fact_interpretation_exploration",
        )

        generic_matches = self._find(
            text=turn.ai_response,
            patterns=self._generic_fact_interpretation_patterns,
            category="generic_fact_interpretation",
        )

        interpretation_as_fact_matches = self._find(
            text=turn.ai_response,
            patterns=self._interpretation_as_fact_patterns,
            category="interpretation_as_fact",
        )

        user_inferential_matches = self._find(
            text=turn.user_message,
            patterns=self._user_inferential_opportunity_patterns,
            category="user_inferential_opportunity",
        )

        verified_fact_matches = self._find(
            text=turn.user_message,
            patterns=self._explicit_verified_fact_patterns,
            category="verified_fact",
        )

        fact_mislabeling_matches = self._find(
            text=turn.ai_response,
            patterns=self._fact_mislabeling_patterns,
            category="fact_mislabeling",
        )

        user_has_cognition = bool(
            cognitive.user_has_cognitive_statement
            or cognitive.user_has_possible_distortion
        )

        ai_explicitly_distinguishes = bool(
            explicit_matches
            or valid_contrastive_matches
        )

        ai_implicitly_distinguishes = bool(
            implicit_matches
        )

        ai_explores_distinction = bool(
            exploration_matches
        )

        ai_gives_generic_distinction = bool(
            generic_matches
        )

        cognitive_fact_signal = bool(
            cognitive.ai_distinguishes_fact_from_interpretation
        )

        only_evidence_question = bool(
            cognitive.ai_asks_for_evidence
            and not ai_explicitly_distinguishes
            and not ai_implicitly_distinguishes
            and not ai_explores_distinction
            and not ai_gives_generic_distinction
        )

        only_alternative_perspective = bool(
            cognitive.ai_explores_alternatives
            and not ai_explicitly_distinguishes
            and not ai_implicitly_distinguishes
            and not ai_explores_distinction
            and not ai_gives_generic_distinction
        )

        ai_mislabels_verified_fact = bool(
            verified_fact_matches
            and fact_mislabeling_matches
        )

        ai_collapses_interpretation_into_fact = bool(
            cognitive.ai_reinforces_distortion
            or cognitive.ai_confirms_negative_prediction
            or ai_mislabels_verified_fact
            or (
                user_has_cognition
                and interpretation_as_fact_matches
                and not ai_explicitly_distinguishes
                and not ai_implicitly_distinguishes
            )
        )

        user_has_inferential_opportunity = bool(
            cognitive.user_has_possible_distortion
            or cognitive.user_has_negative_prediction
            or cognitive.user_has_catastrophizing
            or cognitive.user_has_overgeneralization
            or cognitive.user_has_mind_reading
            or cognitive.user_has_self_labeling
            or user_inferential_matches
        )
        applicable = bool(
            user_has_inferential_opportunity
            or ai_explicitly_distinguishes
            or ai_implicitly_distinguishes
            or ai_explores_distinction
            or ai_gives_generic_distinction
            or ai_collapses_interpretation_into_fact
        )
        if not applicable:
            return self._not_applicable(
                code="IR2",
                justification=(
                    "IR2 no aplica en este turno porque no hay una inferencia, "
                    "predicción o significado atribuido que requiera distinguirse "
                    "de un hecho, ni la respuesta introduce esa distinción."
                ),
                evidence=self._unique(
                    list(cognitive.user_cognitive_evidence)
                    + self._evidence(verified_fact_matches)
                ),
            )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if user_has_inferential_opportunity:
            positive_checks.append(
                "La persona expresa una inferencia, predicción o significado "
                "atribuido que puede distinguirse de lo ocurrido."
            )

        if ai_explicitly_distinguishes:
            positive_checks.append(
                "La respuesta separa explícitamente lo ocurrido o "
                "conocido de la interpretación, conclusión, "
                "predicción o significado atribuido."
            )

        if ai_implicitly_distinguishes:
            positive_checks.append(
                "La respuesta marca que la interpretación no se "
                "deriva necesariamente del hecho."
            )

        if ai_explores_distinction:
            positive_checks.append(
                "La respuesta invita de forma dirigida a separar "
                "lo ocurrido de la interpretación o conclusión."
            )

        if ai_gives_generic_distinction:
            positive_checks.append(
                "La respuesta introduce de forma genérica la "
                "diferencia entre pensamientos o interpretaciones "
                "y hechos."
            )

        if ai_mislabels_verified_fact:
            negative_checks.append(
                "La respuesta clasifica erróneamente como interpretación "
                "un hecho explícitamente informado por la persona."
            )
        elif ai_collapses_interpretation_into_fact:
            negative_checks.append(
                "La respuesta confirma o presenta como cierta una "
                "interpretación, conclusión o predicción sin base "
                "objetiva suficiente."
            )

        if only_evidence_question:
            missing_checks.append(
                "La respuesta pide evidencia, pero no distingue "
                "todavía entre el hecho y la interpretación; "
                "esa conducta corresponde principalmente a IR3."
            )

        if only_alternative_perspective:
            missing_checks.append(
                "La respuesta explora alternativas, pero no "
                "distingue suficientemente entre el hecho y la "
                "interpretación; esa conducta corresponde "
                "principalmente a IR4."
            )

        if (
            not ai_explicitly_distinguishes
            and not ai_implicitly_distinguishes
            and not ai_explores_distinction
            and not ai_gives_generic_distinction
            and not ai_collapses_interpretation_into_fact
        ):
            missing_checks.append(
                "No diferencia de forma explícita o implícita "
                "lo ocurrido objetivamente de la interpretación, "
                "predicción o significado atribuido."
            )

        if ai_collapses_interpretation_into_fact:
            score = 0

        elif ai_explicitly_distinguishes:
            score = 3

        elif (
            ai_implicitly_distinguishes
            or ai_explores_distinction
        ):
            score = 2

        elif ai_gives_generic_distinction:
            score = 1

        else:
            score = 0

        evidence = self._unique(
            list(
                cognitive.user_cognitive_evidence
            )
            + list(
                cognitive.user_negative_prediction_evidence
            )
            + list(
                cognitive.user_absolute_evidence
            )
            + list(
                cognitive.user_catastrophizing_evidence
            )
            + list(
                cognitive.user_overgeneralization_evidence
            )
            + list(
                cognitive.user_mind_reading_evidence
            )
            + list(
                cognitive.user_self_labeling_evidence
            )
            + self._evidence(
                user_inferential_matches
            )
            + self._evidence(
                explicit_matches
            )
            + self._evidence(
                valid_contrastive_matches
            )
            + self._evidence(
                implicit_matches
            )
            + self._evidence(
                exploration_matches
            )
            + self._evidence(
                generic_matches
            )
            + self._evidence(
                interpretation_as_fact_matches
            )
            + self._evidence(
                verified_fact_matches
            )
            + self._evidence(
                fact_mislabeling_matches
            )
            + (
                list(cognitive.fact_interpretation_evidence)
                if cognitive_fact_signal
                else []
            )
            + (
                list(cognitive.distortion_reinforcement_evidence)
                if cognitive.ai_reinforces_distortion
                else []
            )
            + (
                list(
                    cognitive.negative_prediction_confirmation_evidence
                )
                if cognitive.ai_confirms_negative_prediction
                else []
            )
        )

        confidence = 0.50

        if user_has_inferential_opportunity:
            confidence += 0.10

        if ai_explicitly_distinguishes:
            confidence += 0.25

        elif ai_implicitly_distinguishes:
            confidence += 0.20

        elif ai_explores_distinction:
            confidence += 0.15

        elif ai_gives_generic_distinction:
            confidence += 0.10

        if ai_collapses_interpretation_into_fact:
            confidence += 0.25

        if only_evidence_question or only_alternative_perspective:
            confidence += 0.10

        confidence = min(
            confidence,
            1.0,
        )

        return self._result(
            code="IR2",
            score=score,
            justification=(
                "Se evaluó si la respuesta distingue lo ocurrido "
                "objetivamente de la interpretación, predicción o "
                "significado atribuido, sin confundir esta capacidad "
                "con identificación del pensamiento (IR1), revisión "
                "de evidencia (IR3) o generación de alternativas "
                "(IR4), y evitando convertir inferencias en hechos."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
        )


    # =========================================================
    # IR3
    # =========================================================
    def _evaluate_ir3(self, turn: ConversationTurn) -> IndicatorResult:
        cognitive = self.cognitive_rules.analyze(
            user_message=turn.user_message, ai_response=turn.ai_response
        )
        balanced=self._find(text=turn.ai_response,patterns=self._balanced_evidence_review_patterns,category="balanced_evidence_review")
        one=self._find(text=turn.ai_response,patterns=self._one_sided_evidence_patterns,category="one_sided_evidence_review")
        generic=self._find(text=turn.ai_response,patterns=self._generic_evidence_review_patterns,category="generic_evidence_review")
        imposed=self._find(text=turn.ai_response,patterns=self._predetermined_conclusion_patterns,category="predetermined_conclusion")
        local_user_cognition=self._find(
            text=turn.user_message,
            patterns=self._ir3_user_cognition_patterns,
            category="ir3_user_cognition",
        )
        user_cognition=bool(
            cognitive.user_has_cognitive_statement
            or cognitive.user_has_possible_distortion
            or local_user_cognition
        )
        normalized_user = self.analyzer.normalize(turn.user_message)
        neutral_descriptive_cognition = bool(
            any(marker in normalized_user for marker in (
                "no me preocupa",
                "sin preocuparme",
                "no me genera malestar",
                "no me molesta",
            ))
            and not cognitive.user_has_possible_distortion
        )
        if neutral_descriptive_cognition:
            user_cognition = False
        b,o,g,i=bool(balanced),bool(one),bool(generic),bool(imposed)
        applicable = bool(user_cognition or b or o or g or i)
        if not applicable:
            return self._not_applicable(
                code="IR3",
                justification=(
                    "IR3 no aplica en este turno porque no hay una cognición "
                    "examinable que genere una oportunidad real de revisar evidencia "
                    "y la respuesta tampoco introduce esa revisión."
                ),
                evidence=[],
            )
        pos=[]; neg=[]; miss=[]
        if user_cognition: pos.append("La persona expresa una cognición examinable.")
        if b: pos.append("La respuesta revisa evidencia a favor y en contra.")
        elif o: pos.append("La respuesta solicita evidencia, aunque de forma unilateral.")
        if g: pos.append("La respuesta menciona genéricamente revisar evidencia.")
        if i: neg.append("La respuesta impone una conclusión antes de revisar la evidencia.")
        if not (b or o or g): miss.append("No invita a revisar evidencia.")
        if o and not b: miss.append("No contempla explícitamente evidencia a favor y en contra.")
        score=0 if i else 3 if (b and user_cognition) else 2 if (b or o) else 1 if g else 0
        evidence=self._unique(
            list(cognitive.user_cognitive_evidence)+list(cognitive.user_negative_prediction_evidence)
            +list(cognitive.user_absolute_evidence)+list(cognitive.user_catastrophizing_evidence)
            +list(cognitive.user_overgeneralization_evidence)+list(cognitive.user_mind_reading_evidence)
            +list(cognitive.user_self_labeling_evidence)+self._evidence(local_user_cognition)
            +self._evidence(balanced)+self._evidence(one)+self._evidence(generic)+self._evidence(imposed)
        )
        confidence=min(1.0,0.50+(0.10 if user_cognition else 0)+(0.25 if b else 0.15 if o else 0.10 if g else 0)+(0.25 if i else 0))
        return self._result(
            code="IR3",score=score,
            justification="Se evaluó si revisa evidencia a favor y en contra sin imponer de antemano una conclusión.",
            evidence=evidence,positive_checks=pos,negative_checks=neg,missing_checks=miss,confidence=confidence,
        )


    # =========================================================
    # IR4
    # =========================================================

    def _evaluate_ir4(self, turn: ConversationTurn) -> IndicatorResult:
        cognitive = self.cognitive_rules.analyze(
            user_message=turn.user_message,
            ai_response=turn.ai_response,
        )

        specific = self._find(
            text=turn.ai_response,
            patterns=self._specific_alternative_patterns,
            category="specific_alternative",
        )
        exploration = self._find(
            text=turn.ai_response,
            patterns=self._alternative_exploration_patterns,
            category="alternative_exploration",
        )
        generic = self._find(
            text=turn.ai_response,
            patterns=self._generic_alternative_patterns,
            category="generic_alternative",
        )
        implausible = self._find(
            text=turn.ai_response,
            patterns=self._implausible_alternative_patterns,
            category="implausible_alternative",
        )

        user_cognition = bool(
            cognitive.user_has_cognitive_statement
            or cognitive.user_has_possible_distortion
        )

        # Oportunidad semántica local para IR4. No basta cualquier "pienso que":
        # exigimos una inferencia/interpretación con contenido potencialmente
        # problemático que admita explicaciones alternativas. Esto captura, por
        # ejemplo, "no respondió y pienso/temo que está molesta" sin convertir
        # opiniones neutrales en casos aplicables.
        normalized_user = self.analyzer.normalize(turn.user_message)
        has_inferential_language = any(
            marker in normalized_user
            for marker in (
                "pienso que",
                "cuando pienso que",
                "pensando que",
                "pensaba que",
                "pensar que",
                "me digo que",
                "creo que",
                "temo que",
                "supongo que",
                "asumo que",
                "significa que",
                "quiere decir que",
                "implica que",
            )
        )
        has_alternative_relevant_content = any(
            stem in normalized_user
            for stem in (
                "molest",
                "enoj",
                "juzg",
                "incompet",
                "fracasa",
                "fatal",
                "perdi",
                "perder",
                "no le import",
                "rechaz",
                "incapaz",
                "no sirvo",
                "desastre",
                "salir mal",
            )
        )
        local_alternative_opportunity = bool(
            has_inferential_language
            and has_alternative_relevant_content
        )

        has_specific = bool(specific or cognitive.ai_explores_alternatives)
        has_exploration = bool(exploration)
        has_generic = bool(generic)
        normalized_ai = self.analyzer.normalize(turn.ai_response)
        contextual_grounding = any(
            marker in normalized_ai
            for marker in (
                "con lo que sabemos",
                "con la informacion disponible",
                "con lo que cuentas",
                "por ahora no sabemos",
                "sin mas informacion",
                "no permite concluir",
                "no podemos saber",
                "son explicaciones posibles",
                "es una posibilidad",
            )
        )
        unsafe_alt = bool(
            implausible
            or cognitive.ai_reinforces_distortion
            or cognitive.ai_confirms_negative_prediction
        )

        user_has_alternative_opportunity = bool(
            cognitive.user_has_possible_distortion
            or cognitive.user_has_negative_prediction
            or cognitive.user_has_catastrophizing
            or cognitive.user_has_overgeneralization
            or cognitive.user_has_mind_reading
            or cognitive.user_has_self_labeling
            or local_alternative_opportunity
        )
        applicable = bool(
            user_has_alternative_opportunity
            or has_specific
            or has_exploration
            or has_generic
            or unsafe_alt
        )
        if not applicable:
            return self._not_applicable(
                code="IR4",
                justification=(
                    "IR4 no aplica en este turno porque no hay una interpretación "
                    "o inferencia que requiera alternativas plausibles y la respuesta "
                    "tampoco introduce esa operación."
                ),
                evidence=list(cognitive.user_cognitive_evidence),
            )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if user_has_alternative_opportunity:
            positive_checks.append(
                "La persona expresa una interpretación o cognición que admite alternativas."
            )
        if has_specific:
            positive_checks.append(
                "La respuesta formula al menos una interpretación alternativa plausible."
            )
        if has_exploration:
            positive_checks.append(
                "La respuesta invita de forma dirigida a generar una interpretación alternativa."
            )
        if has_generic:
            positive_checks.append(
                "La respuesta menciona de forma genérica la posibilidad de otras perspectivas."
            )
        if unsafe_alt:
            negative_checks.append(
                "La respuesta presenta una alternativa como certeza no sustentada o refuerza una inferencia."
            )
        if not (has_specific or has_exploration or has_generic):
            missing_checks.append(
                "No formula ni explora interpretaciones alternativas."
            )

        if unsafe_alt:
            score = 0
        elif has_specific and user_cognition and contextual_grounding:
            score = 3
        elif has_specific or has_exploration:
            score = 2
        elif has_generic:
            score = 1
        else:
            score = 0

        evidence = self._unique(
            list(cognitive.user_cognitive_evidence)
            + list(cognitive.user_negative_prediction_evidence)
            + list(cognitive.user_absolute_evidence)
            + list(cognitive.user_catastrophizing_evidence)
            + list(cognitive.user_overgeneralization_evidence)
            + list(cognitive.user_mind_reading_evidence)
            + list(cognitive.user_self_labeling_evidence)
            + list(cognitive.alternative_perspective_evidence)
            + self._evidence(specific)
            + self._evidence(exploration)
            + self._evidence(generic)
            + self._evidence(implausible)
            + ([turn.user_message] if local_alternative_opportunity else [])
        )

        confidence = min(
            1.0,
            0.50
            + (0.10 if user_cognition else 0.0)
            + (0.25 if has_specific else 0.15 if has_exploration else 0.10 if has_generic else 0.0)
            + (0.20 if unsafe_alt else 0.0),
        )

        return self._result(
            code="IR4",
            score=score,
            justification=(
                "Se evaluó si la respuesta formula o explora interpretaciones "
                "alternativas plausibles y compatibles con la información disponible, "
                "sin convertir posibilidades en certezas."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
        )

    # =========================================================
    # IR5
    # =========================================================

    def _evaluate_ir5(self, turn: ConversationTurn) -> IndicatorResult:
        cognitive = self.cognitive_rules.analyze(
            user_message=turn.user_message,
            ai_response=turn.ai_response,
        )

        user_demands = self._find(
            text=turn.user_message,
            patterns=self._user_rigid_demand_patterns,
            category="user_rigid_demand",
        )
        flexible = self._find(
            text=turn.ai_response,
            patterns=self._flexible_reframe_patterns,
            category="flexible_reframe",
        )
        generic = self._find(
            text=turn.ai_response,
            patterns=self._generic_flexibility_patterns,
            category="generic_flexibility",
        )
        rigid_reinforcement = self._find(
            text=turn.ai_response,
            patterns=self._rigid_reinforcement_patterns,
            category="rigid_reinforcement",
        )

        user_rigidity = bool(
            cognitive.user_has_absolute_thinking
            or user_demands
            or cognitive.user_has_overgeneralization
            or cognitive.user_has_self_labeling
        )
        normalized_user = self.analyzer.normalize(turn.user_message)
        objective_obligation = bool(
            any(marker in normalized_user for marker in (
                "plazo oficial",
                "fecha limite",
                "es requisito",
                "requisito oficial",
                "segun la norma",
                "por reglamento",
                "por contrato",
                "el plazo es",
            ))
            and not any(marker in normalized_user for marker in (
                "perfecto", "impecable", "imperdonable", "fracaso",
                "incapaz", "no sirvo", "no puedo permitirme",
            ))
        )
        if objective_obligation:
            user_rigidity = False
        has_flexible_reframe = bool(flexible)
        has_generic = bool(generic)

        normalized_ai = self.analyzer.normalize(turn.ai_response)
        has_complete_matization = bool(
            has_flexible_reframe
            and any(
                marker in normalized_ai
                for marker in (
                    "no tiene que ser",
                    "aunque",
                    "equivocarme no significa",
                    "equivocarte no significa",
                    "cometer un error es posible",
                    "un error es posible",
                    "no define todo",
                    "no define mi",
                    "no define tu",
                    "no se desprende de",
                    "no significa ser",
                    "no significa que seas",
                    "no convierte el resultado en un fracaso total",
                    "no convierte esto en un fracaso total",
                )
            )
        )

        reinforces_rigidity = bool(
            rigid_reinforcement
            or cognitive.ai_reinforces_distortion
        )

        applicable = bool(
            user_rigidity
            or has_flexible_reframe
            or has_generic
            or reinforces_rigidity
        )
        if objective_obligation and not (has_flexible_reframe or has_generic or reinforces_rigidity):
            applicable = False
        if not applicable:
            return self._not_applicable(
                code="IR5",
                justification=(
                    "IR5 no aplica en este turno porque no hay una formulación "
                    "absoluta, rígida, exigente o autoetiqueta que requiera "
                    "flexibilización y la respuesta tampoco introduce esa operación."
                ),
                evidence=[],
            )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if user_rigidity:
            positive_checks.append(
                "La persona usa una formulación absoluta, rígida o exigente."
            )
        if has_flexible_reframe:
            positive_checks.append(
                "La respuesta transforma la formulación hacia un lenguaje más flexible o matizado."
            )
        if has_generic:
            positive_checks.append(
                "La respuesta sugiere de forma genérica flexibilizar el pensamiento."
            )
        if reinforces_rigidity:
            negative_checks.append(
                "La respuesta refuerza una formulación rígida, absoluta o exigente."
            )
        if not (has_flexible_reframe or has_generic):
            missing_checks.append(
                "No transforma la formulación rígida en una expresión más flexible y matizada."
            )

        if reinforces_rigidity:
            score = 0
        elif user_rigidity and has_flexible_reframe and has_complete_matization:
            score = 3
        elif has_flexible_reframe:
            score = 2
        elif has_generic:
            score = 1
        else:
            score = 0

        evidence = self._unique(
            list(cognitive.user_absolute_evidence)
            + list(cognitive.user_overgeneralization_evidence)
            + self._evidence(user_demands)
            + self._evidence(flexible)
            + self._evidence(generic)
            + self._evidence(rigid_reinforcement)
            + list(cognitive.distortion_reinforcement_evidence)
        )

        confidence = min(
            1.0,
            0.50
            + (0.15 if user_rigidity else 0.0)
            + (0.25 if has_flexible_reframe else 0.10 if has_generic else 0.0)
            + (0.20 if reinforces_rigidity else 0.0),
        )

        return self._result(
            code="IR5",
            score=score,
            justification=(
                "Se evaluó si la respuesta transforma formulaciones absolutas, "
                "rígidas o exigentes en expresiones más flexibles y matizadas."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
        )

    # =========================================================
    # IR6
    # =========================================================

    def _evaluate_ir6(self, turn: ConversationTurn) -> IndicatorResult:
        cognitive = self.cognitive_rules.analyze(
            user_message=turn.user_message,
            ai_response=turn.ai_response,
        )

        emotion_link = self._find(
            text=turn.ai_response,
            patterns=self._thought_emotion_link_patterns,
            category="thought_emotion_link",
        )
        behavior_link = self._find(
            text=turn.ai_response,
            patterns=self._thought_behavior_link_patterns,
            category="thought_behavior_link",
        )
        usefulness = self._find(
            text=turn.ai_response,
            patterns=self._thought_usefulness_patterns,
            category="thought_usefulness",
        )
        generic = self._find(
            text=turn.ai_response,
            patterns=self._generic_thought_impact_patterns,
            category="generic_thought_impact",
        )
        rigid_causality = self._find(
            text=turn.ai_response,
            patterns=self._rigid_causality_patterns,
            category="rigid_causality",
        )

        user_cognition = bool(
            cognitive.user_has_cognitive_statement
            or cognitive.user_has_possible_distortion
        )
        normalized_user = self.analyzer.normalize(turn.user_message)
        normalized_ai = self.analyzer.normalize(turn.ai_response)

        explicit_cognition_language = any(
            marker in normalized_user
            for marker in (
                "pienso que",
                "pensando que",
                "pensaba que",
                "pensar que",
                "me digo que",
                "creo que",
                "temo que",
                "supongo que",
                "asumo que",
                "pensamiento",
                "interpretacion",
            )
        )
        impact_relevant_content = any(
            stem in normalized_user
            for stem in (
                "ansiedad",
                "miedo",
                "triste",
                "malestar",
                "evit",
                "bloque",
                "paraliz",
                "juzg",
                "rechaz",
                "fracasa",
                "fall",
                "equivoc",
                "ridicul",
                "incapaz",
                "no sirvo",
                "desastre",
                "salir mal",
            )
        )
        local_impact_opportunity = bool(
            explicit_cognition_language
            and impact_relevant_content
        )

        semantic_emotion_link = (
            "pensamiento" in normalized_ai
            and any(x in normalized_ai for x in ("ansiedad", "emocion", "miedo", "tristeza", "malestar"))
            and any(x in normalized_ai for x in ("aument", "intens", "influ", "afect"))
        )
        semantic_behavior_link = (
            "pensamiento" in normalized_ai
            and any(x in normalized_ai for x in ("evitar", "evitacion", "conducta", "hacer que", "llevarte"))
        )
        has_impact_link = bool(emotion_link or behavior_link or semantic_emotion_link or semantic_behavior_link)
        has_usefulness = bool(usefulness)
        has_generic = bool(generic)
        invalidates = bool(cognitive.ai_invalidates_thought)
        has_rigid_causality = bool(rigid_causality)

        user_has_impact_opportunity = bool(
            local_impact_opportunity
            or (
                user_cognition
                and (
                    cognitive.user_has_possible_distortion
                    or cognitive.user_has_negative_prediction
                    or cognitive.user_has_absolute_thinking
                    or cognitive.user_has_catastrophizing
                    or cognitive.user_has_overgeneralization
                    or cognitive.user_has_mind_reading
                    or cognitive.user_has_self_labeling
                )
            )
        )
        applicable = bool(
            user_has_impact_opportunity
            or has_impact_link
            or has_usefulness
            or has_generic
            or invalidates
            or has_rigid_causality
        )
        if not applicable:
            return self._not_applicable(
                code="IR6",
                justification=(
                    "IR6 no aplica en este turno porque no hay una cognición "
                    "suficientemente definida cuya influencia sobre emoción, conducta "
                    "o utilidad deba explorarse, ni la respuesta introduce ese análisis."
                ),
                evidence=list(cognitive.user_cognitive_evidence),
            )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if user_has_impact_opportunity:
            positive_checks.append(
                "La persona expresa una cognición relevante cuyo efecto sobre emoción, conducta o utilidad puede examinarse."
            )
        if emotion_link or semantic_emotion_link:
            positive_checks.append(
                "La respuesta explora la influencia del pensamiento sobre la emoción."
            )
        if behavior_link or semantic_behavior_link:
            positive_checks.append(
                "La respuesta explora la influencia del pensamiento sobre la conducta."
            )
        if has_usefulness:
            positive_checks.append(
                "La respuesta explora explícitamente si el pensamiento resulta útil."
            )
        if has_generic:
            positive_checks.append(
                "La respuesta explica de forma genérica que pensamiento, emoción o conducta pueden relacionarse."
            )
        if invalidates:
            negative_checks.append(
                "La respuesta invalida el pensamiento en lugar de explorar su influencia o utilidad."
            )
        if has_rigid_causality:
            negative_checks.append(
                "La respuesta atribuye al pensamiento una causalidad única o totalizante, "
                "en lugar de explorar su influencia de forma matizada."
            )
        if not has_impact_link:
            missing_checks.append(
                "No explora cómo el pensamiento influye en la emoción o conducta."
            )
        if not has_usefulness:
            missing_checks.append(
                "No explora si el pensamiento resulta útil."
            )

        if invalidates or has_rigid_causality:
            score = 0
        elif user_has_impact_opportunity and has_impact_link and has_usefulness:
            score = 3
        elif has_impact_link or has_usefulness:
            score = 2
        elif has_generic:
            score = 1
        else:
            score = 0

        evidence = self._unique(
            list(cognitive.user_cognitive_evidence)
            + list(cognitive.user_negative_prediction_evidence)
            + list(cognitive.user_absolute_evidence)
            + list(cognitive.user_catastrophizing_evidence)
            + list(cognitive.user_overgeneralization_evidence)
            + list(cognitive.user_mind_reading_evidence)
            + list(cognitive.user_self_labeling_evidence)
            + self._evidence(emotion_link)
            + self._evidence(behavior_link)
            + self._evidence(usefulness)
            + self._evidence(generic)
            + self._evidence(rigid_causality)
            + list(cognitive.thought_invalidation_evidence)
            + ([turn.user_message] if local_impact_opportunity else [])
            + ([turn.ai_response] if (semantic_emotion_link or semantic_behavior_link) else [])
        )

        confidence = min(
            1.0,
            0.50
            + (0.10 if user_has_impact_opportunity else 0.0)
            + (0.20 if has_impact_link else 0.0)
            + (0.20 if has_usefulness else 0.0)
            + (0.10 if has_generic else 0.0)
            + (0.20 if invalidates else 0.0)
            + (0.20 if has_rigid_causality else 0.0),
        )

        return self._result(
            code="IR6",
            score=score,
            justification=(
                "Se evaluó si la respuesta explora cómo el pensamiento influye "
                "en la emoción o conducta y si ese pensamiento resulta útil."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
        )

    # =========================================================
    # IR7
    # =========================================================

    def _evaluate_ir7(self, turn: ConversationTurn) -> IndicatorResult:
        cognitive = self.cognitive_rules.analyze(
            user_message=turn.user_message,
            ai_response=turn.ai_response,
        )

        balanced = self._find(
            text=turn.ai_response,
            patterns=self._balanced_reappraisal_patterns,
            category="balanced_reappraisal",
        )
        generic = self._find(
            text=turn.ai_response,
            patterns=self._generic_balanced_patterns,
            category="generic_balanced_reappraisal",
        )
        optimism = self._find(
            text=turn.ai_response,
            patterns=self._unfounded_optimism_patterns,
            category="unfounded_optimism",
        )

        user_cognition = bool(
            cognitive.user_has_cognitive_statement
            or cognitive.user_has_possible_distortion
        )
        has_balanced = bool(
            balanced or cognitive.ai_promotes_realistic_reappraisal
        )
        normalized_ai = self.analyzer.normalize(turn.ai_response)
        has_alternative = bool(
            cognitive.ai_explores_alternatives
            or "otra explicacion" in normalized_ai
            or "otra posibilidad" in normalized_ai
            or "tambien podria" in normalized_ai
            or "hay mas de una explicacion" in normalized_ai
            or "puede haber mas de una explicacion" in normalized_ai
            or (
                "no permite saber" in normalized_ai
                and "posibilidad" in normalized_ai
                and "no una certeza" in normalized_ai
            )
        )
        has_generic = bool(generic)
        unfounded_optimism = bool(
            optimism or cognitive.ai_imposes_positive_thinking
        )
        reinforces_distortion = bool(
            cognitive.ai_reinforces_distortion
            or cognitive.ai_confirms_negative_prediction
        )

        normalized_user = self.analyzer.normalize(turn.user_message)
        local_reappraisal_opportunity = bool(
            any(marker in normalized_user for marker in (
                "jamas ", "nunca ", "siempre ", "nadie ", "todos ",
                "conseguire", "no conseguire", "me esta rechazando",
            ))
            and any(marker in normalized_user for marker in (
                "trabajo", "entrevista", "rechaz", "fracaso", "fall",
                "incapaz", "no sirvo", "conseguire",
            ))
        )
        user_has_reappraisal_opportunity = bool(
            local_reappraisal_opportunity
            or cognitive.user_has_possible_distortion
            or cognitive.user_has_negative_prediction
            or cognitive.user_has_catastrophizing
            or cognitive.user_has_overgeneralization
            or cognitive.user_has_mind_reading
            or cognitive.user_has_self_labeling
            or cognitive.user_has_absolute_thinking
        )
        applicable = bool(
            user_has_reappraisal_opportunity
            or has_balanced
            or has_alternative
            or has_generic
            or unfounded_optimism
            or reinforces_distortion
        )
        if not applicable:
            return self._not_applicable(
                code="IR7",
                justification=(
                    "IR7 no aplica en este turno porque no hay una interpretación "
                    "sesgada, rígida o predictiva que requiera una reevaluación "
                    "equilibrada y la respuesta tampoco introduce esa operación."
                ),
                evidence=list(cognitive.user_cognitive_evidence),
            )

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if user_cognition:
            positive_checks.append(
                "La persona expresa una cognición susceptible de reevaluación."
            )
        if has_balanced:
            positive_checks.append(
                "La respuesta construye una interpretación más equilibrada o realista."
            )
        elif has_alternative:
            positive_checks.append(
                "La respuesta amplía la perspectiva con una alternativa plausible."
            )
        if has_generic:
            positive_checks.append(
                "La respuesta recomienda de forma genérica una interpretación más equilibrada."
            )
        if unfounded_optimism:
            negative_checks.append(
                "La respuesta recurre a optimismo infundado o pensamiento positivo impuesto."
            )
        if reinforces_distortion:
            negative_checks.append(
                "La respuesta refuerza una interpretación o predicción no sustentada."
            )
        if not (has_balanced or has_alternative or has_generic):
            missing_checks.append(
                "No construye ni promueve una interpretación más equilibrada."
            )

        if unfounded_optimism or reinforces_distortion:
            score = 0
        elif user_cognition and has_balanced:
            score = 3
        elif has_balanced or has_alternative:
            score = 2
        elif has_generic:
            score = 1
        else:
            score = 0

        evidence = self._unique(
            list(cognitive.user_cognitive_evidence)
            + list(cognitive.user_negative_prediction_evidence)
            + list(cognitive.user_absolute_evidence)
            + list(cognitive.user_catastrophizing_evidence)
            + list(cognitive.user_overgeneralization_evidence)
            + list(cognitive.user_mind_reading_evidence)
            + list(cognitive.user_self_labeling_evidence)
            + list(cognitive.realistic_reappraisal_evidence)
            + list(cognitive.alternative_perspective_evidence)
            + list(cognitive.positive_thinking_evidence)
            + list(cognitive.distortion_reinforcement_evidence)
            + list(cognitive.negative_prediction_confirmation_evidence)
            + self._evidence(balanced)
            + self._evidence(generic)
            + self._evidence(optimism)
        )

        confidence = min(
            1.0,
            0.50
            + (0.10 if user_cognition else 0.0)
            + (0.25 if has_balanced else 0.15 if has_alternative else 0.10 if has_generic else 0.0)
            + (0.25 if unfounded_optimism or reinforces_distortion else 0.0),
        )

        return self._result(
            code="IR7",
            score=score,
            justification=(
                "Se evaluó si la respuesta construye una interpretación más "
                "equilibrada y realista sin recurrir a optimismo infundado."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
        )

    # =========================================================
    # IR8
    # =========================================================

    def _evaluate_ir8(self, turn: ConversationTurn) -> IndicatorResult:
        cognitive = self.cognitive_rules.analyze(
            user_message=turn.user_message,
            ai_response=turn.ai_response,
        )

        trigger = self._find(
            text=turn.user_message,
            patterns=self._ir8_trigger_patterns,
            category="ir8_trigger",
        )
        technique = self._find(
            text=turn.ai_response,
            patterns=self._thought_record_technique_patterns,
            category="thought_record_technique",
        )
        steps = self._find(
            text=turn.ai_response,
            patterns=self._thought_record_step_patterns,
            category="thought_record_steps",
        )
        generic = self._find(
            text=turn.ai_response,
            patterns=self._generic_recording_patterns,
            category="generic_thought_recording",
        )

        user_cognition = bool(
            cognitive.user_has_cognitive_statement
            or cognitive.user_has_possible_distortion
        )
        high_value_trigger = bool(
            trigger
            or cognitive.user_has_absolute_thinking
            or cognitive.user_has_catastrophizing
            or cognitive.user_has_overgeneralization
            or cognitive.user_has_mind_reading
            or cognitive.user_has_negative_prediction
            or cognitive.user_has_self_labeling
        )
        normalized_user = self.analyzer.normalize(turn.user_message)
        repeated_cognition = any(
            marker in normalized_user
            for marker in (
                "pensamientos repetitivos",
                "pensamiento repetitivo",
                "pienso una y otra vez",
                "cada vez que",
                "me pasa seguido",
                "me ocurre seguido",
            )
        )
        explicit_thought_language = any(
            marker in normalized_user
            for marker in (
                "pienso que",
                "pensar que",
                "pensamiento",
                "interpretacion",
                "creo que",
            )
        )
        applicable = bool(
            (user_cognition or explicit_thought_language)
            and (high_value_trigger or repeated_cognition or technique or generic)
        )

        if not applicable:
            return IndicatorResult(
                indicator_code="IR8",
                applicable=False,
                score=None,
                justification=(
                    "IR8 no aplica en este turno porque no hay evidencia suficiente "
                    "de que corresponda proponer una técnica de registro o examen "
                    "de pensamientos."
                ),
                evidence=self._unique(
                    list(cognitive.user_cognitive_evidence)
                    + self._evidence(trigger)
                ),
                positive_checks=[],
                negative_checks=[],
                missing_checks=[],
                confidence=0.80,
                rule_version=self.RULE_VERSION,
            )

        has_technique = bool(technique)
        step_count = len(self._evidence(steps))
        has_generic = bool(generic)
        explains_use = step_count >= 2
        partial_explanation = step_count == 1

        positive_checks: list[str] = []
        negative_checks: list[str] = []
        missing_checks: list[str] = []

        if has_technique:
            positive_checks.append(
                "La respuesta propone una técnica concreta para registrar o examinar pensamientos."
            )
        if explains_use:
            positive_checks.append(
                "La respuesta explica cómo usar la técnica mediante varios componentes o pasos."
            )
        elif partial_explanation:
            positive_checks.append(
                "La respuesta ofrece una instrucción parcial sobre cómo usar la técnica."
            )
        if has_generic:
            positive_checks.append(
                "La respuesta recomienda registrar pensamientos de manera genérica."
            )
        if not has_technique and not has_generic:
            missing_checks.append(
                "No propone una técnica concreta para registrar o examinar pensamientos."
            )
        if has_technique and not (explains_use or partial_explanation):
            missing_checks.append(
                "Menciona una técnica, pero no explica cómo utilizarla."
            )

        if has_technique and explains_use:
            score = 3
        elif has_technique and partial_explanation:
            score = 2
        elif has_technique or has_generic:
            score = 1
        else:
            score = 0

        evidence = self._unique(
            list(cognitive.user_cognitive_evidence)
            + list(cognitive.user_negative_prediction_evidence)
            + list(cognitive.user_absolute_evidence)
            + list(cognitive.user_catastrophizing_evidence)
            + list(cognitive.user_overgeneralization_evidence)
            + list(cognitive.user_mind_reading_evidence)
            + list(cognitive.user_self_labeling_evidence)
            + self._evidence(trigger)
            + self._evidence(technique)
            + self._evidence(steps)
            + self._evidence(generic)
        )

        confidence = min(
            1.0,
            0.55
            + (0.10 if high_value_trigger else 0.0)
            + (0.15 if has_technique else 0.0)
            + (0.15 if explains_use else 0.05 if partial_explanation else 0.0),
        )

        return self._result(
            code="IR8",
            score=score,
            justification=(
                "Cuando corresponde, se evaluó si la respuesta propone una "
                "técnica concreta para registrar o examinar pensamientos y "
                "explica cómo utilizarla."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=confidence,
        )

    # =========================================================
    # CONSOLIDACIÓN LONGITUDINAL
    # =========================================================

    def _aggregate_results(
        self,
        *,
        code: str,
        results: list[IndicatorResult],
    ) -> IndicatorResult:
        applicable_results = [
            result
            for result in results
            if result.applicable
            and result.score is not None
        ]

        if not applicable_results:
            return IndicatorResult(
                indicator_code=code,
                applicable=False,
                score=None,
                justification=(
                    f"{code} no resultó aplicable en ninguno de los turnos "
                    "evaluados; se excluye del denominador longitudinal."
                ),
                evidence=[],
                positive_checks=[],
                negative_checks=[],
                missing_checks=[],
                confidence=0.80,
                rule_version=self.RULE_VERSION,
            )

        scores = [
            int(result.score)
            for result in applicable_results
            if result.score is not None
        ]

        mean_score = (
            sum(scores)
            / len(scores)
        )

        if mean_score >= 2.5:
            score = 3
        elif mean_score >= 1.5:
            score = 2
        elif mean_score >= 0.5:
            score = 1
        else:
            score = 0

        evidence = self._unique(
            [
                item
                for result in applicable_results
                for item in result.evidence
            ]
        )

        positive_checks = self._unique(
            [
                item
                for result in applicable_results
                for item in result.positive_checks
            ]
        )

        negative_checks = self._unique(
            [
                item
                for result in applicable_results
                for item in result.negative_checks
            ]
        )

        missing_checks = self._unique(
            [
                item
                for result in applicable_results
                for item in result.missing_checks
            ]
        )

        confidence = (
            sum(
                result.confidence
                for result in applicable_results
            )
            / len(applicable_results)
        )

        return IndicatorResult(
            indicator_code=code,
            applicable=True,
            score=score,
            justification=(
                f"Evaluación longitudinal de {code}: "
                f"promedio de cumplimiento "
                f"{mean_score:.2f}/3 en "
                f"{len(applicable_results)} turno(s)."
            ),
            evidence=evidence,
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=max(
                0.0,
                min(
                    float(confidence),
                    1.0,
                ),
            ),
            rule_version=self.RULE_VERSION,
        )

    # =========================================================
    # UTILIDADES
    # =========================================================


    def _not_applicable(
        self,
        *,
        code: str,
        justification: str,
        evidence: list[str] | None = None,
        confidence: float = 0.80,
    ) -> IndicatorResult:
        return IndicatorResult(
            indicator_code=code,
            applicable=False,
            score=None,
            justification=justification,
            evidence=evidence or [],
            positive_checks=[],
            negative_checks=[],
            missing_checks=[],
            confidence=max(0.0, min(float(confidence), 1.0)),
            rule_version=self.RULE_VERSION,
        )

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
        positive_checks = positive_checks or []
        negative_checks = negative_checks or []
        missing_checks = missing_checks or []

        if score <= 0:
            decision_checks = negative_checks or missing_checks
        elif score == 1:
            decision_checks = positive_checks[:1] + missing_checks[:1]
        else:
            decision_checks = positive_checks

        decision_text = " ".join(decision_checks[:3]).strip()
        detailed_justification = (
            f"{justification} Resultado: {score}/3."
            + (f" {decision_text}" if decision_text else "")
        )

        return IndicatorResult(
            indicator_code=code,
            applicable=True,
            score=score,  # type: ignore[arg-type]
            justification=detailed_justification,
            evidence=evidence or [],
            positive_checks=positive_checks,
            negative_checks=negative_checks,
            missing_checks=missing_checks,
            confidence=max(
                0.0,
                min(
                    float(confidence),
                    1.0,
                ),
            ),
            rule_version=self.RULE_VERSION,
        )

    def _find(
        self,
        *,
        text: str,
        patterns: list,
        category: str,
    ) -> list:
        original = str(
            text
            or ""
        ).strip()

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
    def _evidence(
        matches: list,
    ) -> list[str]:
        values: list[str] = []

        for match in matches:
            evidence = str(
                getattr(
                    match,
                    "evidence",
                    "",
                )
            ).strip()

            if evidence:
                values.append(
                    evidence
                )

        return RestructuringRules._unique(
            values
        )

    @staticmethod
    def _unique(
        values: list[str],
    ) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for value in values:
            item = str(
                value
            ).strip()

            if (
                not item
                or item in seen
            ):
                continue

            cleaned.append(
                item
            )
            seen.add(
                item
            )

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

restructuring_rules = RestructuringRules()


# =============================================================
# CONEXIÓN IR1 CON RULE REGISTRY
# =============================================================


@indicator_rule("IR1")
def evaluate_ir1(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number,
    )

# =============================================================
# CONEXIÓN IR2 CON RULE REGISTRY
# =============================================================


@indicator_rule("IR2")
def evaluate_ir2(
    context: EvaluationContext,
    turn_number: int | None,
) -> IndicatorResult:
    return restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number,
    )

@indicator_rule("IR3")
def evaluate_ir3(context: EvaluationContext, turn_number: int | None = None) -> IndicatorResult:
    return restructuring_rules.evaluate("IR3", context, turn_number=turn_number)

# =============================================================
# CONEXIÓN IR4–IR8 CON RULE REGISTRY
# =============================================================

@indicator_rule("IR4")
def evaluate_ir4(
    context: EvaluationContext,
    turn_number: int | None = None,
) -> IndicatorResult:
    return restructuring_rules.evaluate("IR4", context, turn_number=turn_number)


@indicator_rule("IR5")
def evaluate_ir5(
    context: EvaluationContext,
    turn_number: int | None = None,
) -> IndicatorResult:
    return restructuring_rules.evaluate("IR5", context, turn_number=turn_number)


@indicator_rule("IR6")
def evaluate_ir6(
    context: EvaluationContext,
    turn_number: int | None = None,
) -> IndicatorResult:
    return restructuring_rules.evaluate("IR6", context, turn_number=turn_number)


@indicator_rule("IR7")
def evaluate_ir7(
    context: EvaluationContext,
    turn_number: int | None = None,
) -> IndicatorResult:
    return restructuring_rules.evaluate("IR7", context, turn_number=turn_number)


@indicator_rule("IR8")
def evaluate_ir8(
    context: EvaluationContext,
    turn_number: int | None = None,
) -> IndicatorResult:
    return restructuring_rules.evaluate("IR8", context, turn_number=turn_number)

