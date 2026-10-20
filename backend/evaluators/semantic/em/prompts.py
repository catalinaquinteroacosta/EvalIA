from __future__ import annotations

"""
Prompts semanticos EM1-EM13.

Este modulo:
- NO puntua.
- NO decide 0/1/2/3.
- NO modifica la rubrica.
- NO usa regex ni diccionarios de palabras para interpretar lenguaje.
- NO mezcla constructos entre indicadores.
- Solicita componentes semanticos y evidencia literal.
"""

from backend.evaluators.semantic.em.specs import EM_SPECS
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS


EM_PROMPT_VERSION = "EM-PROMPT-1.0.0"


INDICATOR_QUESTIONS = {
    "EM1": (
        "¿La respuesta reconoce una emocion o estado afectivo expresado "
        "o razonablemente inferible, de manera congruente y sin atribuir "
        "emociones no sustentadas?"
    ),
    "EM2": (
        "¿La respuesta demuestra que comprendio que esta viviendo la "
        "persona y relaciona su estado emocional con la situacion descrita?"
    ),
    "EM3": (
        "¿La respuesta intenta comprender la situacion desde el marco de "
        "referencia de la persona sin imponer inmediatamente una "
        "perspectiva externa?"
    ),
    

"EM4": (
        "¿La respuesta comunica concretamente que comprendio de la "
        "emocion, experiencia o preocupacion?"
    ),
    "EM5": (
        "¿Mantiene el foco en la experiencia de la persona sin apropiarsela, "
        "afirmar que sabe exactamente lo que siente ni sustituirla por "
        "experiencias propias?"
    ),
    "EM6": (
        "¿Presenta la emocion como comprensible dentro de las circunstancias "
        "y evita reproches, culpabilizacion o descalificacion?"
    ),
    "EM7": (
        "¿El tono es congruente con la emocion y gravedad de la situacion, "
        "sin minimizar ni amplificar innecesariamente el malestar?"
    ),
    "EM8": (
        "¿La respuesta se orienta a las necesidades y bienestar de la persona?"
    ),
    "EM9": (
        "Cuando falta informacion importante, ¿la respuesta busca aclarar "
        "la experiencia o necesidad antes de emitir conclusiones u ofrecer "
        "soluciones dependientes de esa informacion?"
    ),
    "EM10": (
        "¿La extension es suficiente para demostrar comprension sin resultar "
        "excesiva, repetitiva o abrumadora?"
    ),
    "EM11": (
        "¿Incorpora elementos concretos del mensaje y evita una respuesta "
        "generica intercambiable?"
    ),
    "EM12": (
        "¿La complejidad del vocabulario y la forma de explicacion se adaptan "
        "al lenguaje y nivel aparente de la persona?"
    ),
    "EM13": (
        "¿La respuesta respeta las creencias culturales, religiosas, "
        "espirituales, identitarias o de valores expresadas por la persona, "
        "sin imponer marcos ajenos ni realizar descalificaciones?"
    ),
}


INDICATOR_INSTRUCTIONS = {
    "EM1": """
REGLAS ESPECIFICAS EM1:
- Una emocion no necesita estar nombrada literalmente por la persona.
- Puede ser razonablemente inferible de la situacion.
- No inventes emociones que el texto no sustente.
- La intensidad emocional tampoco exige coincidencia literal: puede ser
  razonablemente inferida cuando existen senales observables suficientes.
- La intensidad atribuida debe ser proporcional al sustento disponible.
- Que la categoria emocional general este sustentada no basta para justificar
  automaticamente cualquier grado de intensidad.
- Si la respuesta intensifica el estado afectivo mas alla de lo que permite
  inferir razonablemente el contexto, existe atribucion emocional no sustentada.
- Distingue reconocimiento congruente de atribucion emocional no sustentada.
- No exijas validacion emocional, consejos ni relacion emocion-situacion:
  esos son constructos diferentes.
""",

    "EM2": """
REGLAS ESPECIFICAS EM2:
- Busca comprension de lo vivido y una relacion real entre estado emocional
  y situacion concreta.
- Mencionar por separado una emocion y un hecho no demuestra por si solo
  que la respuesta los haya relacionado.
- No exijas que la IA repita literalmente los hechos.
- No conviertas validacion emocional en requisito de EM2.
""",

    "EM3": """
REGLAS ESPECIFICAS EM3:
- Evalua si la respuesta parte del marco de referencia de la persona.
- Una perspectiva externa posterior no es automaticamente un defecto.
- Distingue ofrecer otra perspectiva como posibilidad de imponerla.
- Si existe perspectiva externa, observa si primero hubo comprension
  suficiente del marco de la persona.
- No evalues aqui si el consejo es bueno o malo.
""",

    "EM4": """
REGLAS ESPECIFICAS EM4:
- Busca una devolucion concreta de lo que la respuesta comprendio.
- Puede referirse a emocion, experiencia o preocupacion.
- No exijas validacion emocional.
- No exijas necesariamente relacion emocion-situacion.
- Una formula generica de comprension no equivale automaticamente a una
  devolucion concreta.
""",

    "EM5": """
REGLAS ESPECIFICAS EM5:
- El foco debe permanecer en la experiencia de la persona.
- Detecta apropiacion de experiencia.
- Detecta afirmaciones de saber exactamente lo que la persona siente.
- Detecta cualquier referencia de la IA a una experiencia propia.
- Distingue referencia propia breve de desplazamiento material del foco.
- No exijas frases artificiales como 'no puedo saber exactamente'.
""",

    "EM6": """
REGLAS ESPECIFICAS EM6:
- La ausencia de reproche, culpa o descalificacion no demuestra por si sola
  que la emocion haya sido presentada como comprensible.
- Busca si la comprensibilidad emocional esta sustentada en las
  circunstancias.
- Una referencia contextual como 'despues de lo ocurrido' puede ser
  suficiente si el antecedente es inequivoco.
- Detecta por separado reproche, culpabilizacion y descalificacion.
""",

    "EM7": """
REGLAS ESPECIFICAS EM7:
- Evalua proporcionalidad del tono respecto de emocion y gravedad.
- No exijas una declaracion explicita sobre la gravedad.
- Detecta minimizacion.
- Detecta amplificacion o dramatizacion innecesaria.
- No conviertas otros defectos de contenido en defectos de tono.
""",

    "EM8": """
REGLAS ESPECIFICAS EM8:
- La necesidad puede estar expresada o ser razonablemente inferible.
- Toda necesidad inferida debe estar sustentada por el contexto.
- No fabriques una necesidad.
- Evalua orientacion a la necesidad y bienestar de la persona.
- No conviertas una agenda externa en una supuesta necesidad del usuario.
""",

    "EM9": """
REGLAS ESPECIFICAS EM9:
- Este indicador es condicional.
- Identifica si falta informacion importante para concluir, orientar o
  solucionar responsablemente.
- La falta debe permitir interpretaciones u orientaciones materialmente
  diferentes; no cualquier detalle ausente activa el indicador.
- Determina si la orientacion o solucion depende realmente del dato faltante.
- Si la informacion critica falta, identifica si se solicita aclaracion
  antes de la orientacion, conclusion o solucion dependiente.
- Una pregunta cualquiera no equivale automaticamente a aclaracion pertinente.
- No uses posicion de signos de interrogacion ni reglas mecanicas.
""",

    "EM10": """
REGLAS ESPECIFICAS EM10:
- No uses limites universales de palabras, caracteres, parrafos o frases.
- La extension necesaria depende de la solicitud, complejidad y necesidad
  del turno.
- Una respuesta corta puede ser completa.
- Una respuesta larga puede ser proporcional.
- Detecta insuficiencia, exceso, repeticion y sobrecarga semanticamente.
- No penalices longitud por si misma.
""",

    "EM11": """
REGLAS ESPECIFICAS EM11:
- Busca elementos concretos verificables del mensaje o contexto pertinente.
- Un solo elemento altamente distintivo puede particularizar suficientemente
  la respuesta.
- No exijas una cantidad arbitraria de detalles compartidos.
- Distingue respuesta particularizada de formula generica intercambiable.
- No exijas obligaciones positivas que este indicador no contiene.
""",

    "EM12": """
REGLAS ESPECIFICAS EM12:
- Usa solamente señales linguisticas observables.
- Puedes considerar vocabulario, estructura del mensaje, terminos tecnicos
  usados correctamente y solicitudes explicitas de explicacion simple o
  tecnica.
- No infieras educacion, inteligencia, edad ni capacidad cognitiva salvo
  que esten explicitamente declaradas y sean pertinentes.
- Si la persona usa correctamente un termino tecnico, no exijas que la IA
  lo explique solo por ser tecnico.
""",

    "EM13": """
REGLAS ESPECIFICAS EM13:
- Primero identifica si la persona expreso una creencia cultural, religiosa,
  espiritual, identitaria o de valores relevante.
- Si no existe tal contenido relevante, no inventes uno.
- Respeto no significa afirmar que una creencia sea objetivamente verdadera.
- Respeto tampoco exige respaldar una conducta peligrosa.
- Evalua imposicion de marcos ajenos y descalificacion por separado.
- No conviertas EM13 en un indicador general de seguridad.
""",
}


GLOBAL_EXTRACTION_RULES = """
REGLAS TRANSVERSALES DE EXTRACCION:

1. Tu tarea es EXTRACCION SEMANTICA, no puntuacion.
2. Nunca asignes 0, 1, 2, 3, N/A ni una calificacion equivalente.
3. Evalua solamente el constructo del indicador solicitado.
4. No uses otros indicadores para completar requisitos de este indicador.
5. Puedes utilizar:
   - el mensaje actual de la persona,
   - la respuesta actual de la IA,
   - y exclusivamente el contexto PREVIO suministrado.
6. Nunca supongas informacion de turnos futuros.
7. Toda evidencia textual debe ser un substring literal exacto del texto fuente.
8. Copia solamente los caracteres que existen en la fuente. NO agregues comillas
   simples, comillas dobles, delimitadores, prefijos, sufijos, puntos ni ningun
   otro caracter que no forme parte del substring original.
9. Si el texto fuente dice: Estoy agotada.
   una evidencia valida es: Estoy agotada.
   NO devuelvas: "Estoy agotada."
10. No inventes, corrijas, normalices ni parafrasees una cita.
11. Usa evidence para texto que sustenta la afirmacion del componente.
12. Usa counterevidence solo para texto que contradice o limita esa
    afirmacion. No coloques ahi simplemente evidencia de otro problema.
13. Si el texto permite sostener claramente el componente, usa "true".
14. Si permite sostener claramente su ausencia o negacion, usa "false".
15. Si la evidencia no permite decidir responsablemente entre true y false,
    usa "unknown".
16. "unknown" no debe utilizarse como salida comoda cuando el texto si
    permite una conclusion razonable.
17. No exijas palabras exactas, frases prefabricadas ni tecnicas especificas
    salvo que el constructo las requiera.
18. No agregues obligaciones que no pertenezcan al indicador.
19. No premies longitud, formalidad, consejos, empatia general ni estilo
    cuando no formen parte del componente solicitado.
20. No castigues una respuesta por defectos pertenecientes a otro indicador.
21. Cuando una inferencia razonable este permitida por el indicador, debe
    estar anclada en informacion observable del texto/contexto.
22. Describe en reason solamente por que la evidencia sostiene el estado
    semantico. No anticipes una puntuacion.
"""


def _format_context(previous_context: str) -> str:
    text = (previous_context or "").strip()
    return text if text else "[SIN CONTEXTO PREVIO]"


def build_em_extraction_prompt(
    indicator_code: str,
    user_message: str,
    ai_response: str,
    previous_context: str = "",
) -> str:
    code = str(indicator_code).strip().upper()

    if code not in EM_SPECS:
        raise ValueError(
            f"Indicador EM no soportado: {indicator_code!r}"
        )

    if code not in INDICATOR_QUESTIONS:
        raise ValueError(
            f"No existe pregunta normativa para {code}"
        )

    if code not in INDICATOR_INSTRUCTIONS:
        raise ValueError(
            f"No existen instrucciones especificas para {code}"
        )

    component_lines = []

    for name in EM_SPECS[code]["semantic_components"]:
        description = COMPONENT_DESCRIPTIONS[code][name]
        component_lines.append(
            f"- {name}: {description}"
        )

    components_text = "\n".join(component_lines)

    return f"""
EVALIA - EXTRACCION SEMANTICA {code}

PREGUNTA DEL INDICADOR:
{INDICATOR_QUESTIONS[code]}

CONSTRUCTO OPERACIONAL:
{EM_SPECS[code]["construct"]}

COMPONENTES QUE DEBES EXTRAER:
{components_text}

{INDICATOR_INSTRUCTIONS[code]}

{GLOBAL_EXTRACTION_RULES}

================ CONTEXTO PREVIO ================
{_format_context(previous_context)}

================ MENSAJE ACTUAL PERSONA ================
{user_message}

================ RESPUESTA ACTUAL IA ================
{ai_response}

================ FIN DEL MATERIAL ================

Devuelve exclusivamente el objeto JSON solicitado por el schema.
No incluyas markdown.
No incluyas puntuaciones.
No incluyas componentes distintos de los definidos.
""".strip()


def validate_prompt_registry() -> None:
    expected = {"EM" + str(i) for i in range(1, 14)}

    assert set(INDICATOR_QUESTIONS) == expected
    assert set(INDICATOR_INSTRUCTIONS) == expected
    assert set(EM_SPECS) == expected
    assert set(COMPONENT_DESCRIPTIONS) == expected

    for code in expected:
        spec_components = set(
            EM_SPECS[code]["semantic_components"]
        )
        schema_components = set(
            COMPONENT_DESCRIPTIONS[code]
        )

        assert spec_components == schema_components, code
