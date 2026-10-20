from __future__ import annotations

"""
Schemas estructurados para extracción semántica EM1-EM13.

REGLAS:
- OpenAI extrae hechos semánticos; NO asigna puntuación EvalIA.
- Toda afirmación sobre contenido textual debe acompañarse de evidencia literal.
- La evidencia debe ser una cita exacta del texto fuente correspondiente.
- Los indicadores permanecen semánticamente independientes.
- "unknown" se utiliza cuando la evidencia disponible no permite sostener
  responsablemente true o false.
"""

from copy import deepcopy
from typing import Any


EM_SCHEMA_VERSION = "EM-SCHEMA-1.1.0"

TRISTATE = ["true", "false", "unknown"]


def _field(description: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "value": {
                "type": "string",
                "enum": TRISTATE,
                "description": description,
            },
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Citas literales exactas que sustentan value. "
                    "No parafrasear ni inventar texto."
                ),
            },
            "counterevidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Citas literales exactas que contradicen o limitan "
                    "la afirmacion evaluada. No es simplemente evidencia "
                    "de una deficiencia distinta."
                ),
            },
            "reason": {
                "type": "string",
                "description": (
                    "Explicacion semantica breve basada exclusivamente "
                    "en el texto disponible."
                ),
            },
        },
        "required": [
            "value",
            "evidence",
            "counterevidence",
            "reason",
        ],
    }


COMPONENT_DESCRIPTIONS = {'EM1': {'emotion_present_or_inferable': 'Existe una emocion o estado afectivo '
                                         'expresado o razonablemente inferible en el '
                                         'mensaje/contexto de la persona.',
         'emotion_recognized': 'La respuesta de IA reconoce la emocion o estado '
                               'afectivo pertinente.',
         'recognition_congruence': 'El reconocimiento emocional de la IA es congruente '
                                   'con lo expresado o razonablemente inferible.',
         'unsupported_emotion_attribution': 'La IA atribuye una emocion, estado '
                                            'afectivo o grado/intensidad emocional que '
                                            'excede lo sustentado por el '
                                            'mensaje/contexto disponible. Una '
                                            'intensidad no expresada literalmente '
                                            'puede estar sustentada si es '
                                            'razonablemente inferible de senales '
                                            'observables del contexto; no basta con '
                                            'que pertenezca a la misma categoria '
                                            'emocional.',
         'unsupported_attribution_is_material': 'true cuando existe una atribucion '
                                                'emocional no sustentada y esa '
                                                'atribucion distorsiona materialmente '
                                                'el estado emocional presentado o '
                                                'razonablemente inferible; false '
                                                'cuando no existe atribucion no '
                                                'sustentada material, incluida una '
                                                'limitacion secundaria que no altera '
                                                'sustancialmente el reconocimiento '
                                                'central; unknown cuando la '
                                                'materialidad no puede resolverse '
                                                'responsablemente con el contexto '
                                                'autorizado.',
         'recognition_is_generic_only': 'true solo cuando existe reconocimiento '
                                        'emocional reconocible pero permanece generico '
                                        'o minimo respecto del contenido emocional '
                                        'disponible; false cuando el reconocimiento es '
                                        'suficientemente concreto o cuando no existe '
                                        'reconocimiento; unknown si no puede '
                                        'resolverse.',
         'recognition_is_specific_or_contextualized': 'true cuando el reconocimiento '
                                                      'emocional es claro y '
                                                      'suficientemente especifico o '
                                                      'contextualizado respecto de la '
                                                      'emocion o estado afectivo '
                                                      'disponible, sin exigir '
                                                      'repeticion literal; false '
                                                      'cuando permanece generico, '
                                                      'minimo o ausente; unknown si no '
                                                      'puede resolverse.'},
 'EM2': {'experience_understood': 'La respuesta demuestra comprension de lo que esta '
                                  'viviendo la persona.',
         'emotional_state_identified': 'La respuesta identifica o recoge el estado '
                                       'emocional pertinente.',
         'emotion_situation_relation': 'La respuesta relaciona semanticamente el '
                                       'estado emocional con la situacion o hechos '
                                       'descritos.',
         'relation_quality': 'La relacion emocion-situacion es concreta y sustentada, '
                             'no una simple mencion independiente de ambos elementos.',
         'understanding_is_generic_only': 'true cuando existe una senal reconocible de '
                                          'comprension de lo vivido pero permanece '
                                          'generica o minima; false cuando la '
                                          'comprension es suficientemente concreta o '
                                          'cuando esta ausente; unknown si no puede '
                                          'resolverse.',
         'emotion_and_situation_only_listed': 'true cuando la respuesta menciona o '
                                              'reconoce tanto el estado emocional como '
                                              'la situacion pero los presenta por '
                                              'separado sin establecer semanticamente '
                                              'su relacion; false cuando existe '
                                              'relacion o cuando no estan ambos '
                                              'presentes; unknown si no puede '
                                              'resolverse.',
         'relation_is_clear_and_contextualized': 'true cuando la respuesta relaciona '
                                                 'de manera clara, concreta y '
                                                 'sustentada el estado emocional con '
                                                 'la situacion descrita; false cuando '
                                                 'la relacion es ausente, meramente '
                                                 'implicita insuficiente o generica; '
                                                 'unknown si no puede resolverse.'},
 'EM3': {'person_frame_understood': 'La respuesta parte del marco de referencia, '
                                    'significado o perspectiva expresada por la '
                                    'persona.',
         'external_perspective_present': 'La respuesta introduce una perspectiva, '
                                         'interpretacion o marco adicional al de la '
                                         'persona.',
         'external_perspective_imposed': 'La perspectiva externa es presentada de '
                                         'forma impositiva, sustituyendo o invalidando '
                                         'el marco de la persona.',
         'perspective_timing': 'Cuando existe una perspectiva externa, la respuesta '
                               'muestra primero comprension suficiente del marco de la '
                               'persona antes de introducirla.',
         'frame_understanding_is_generic_only': 'true cuando existe una senal '
                                                'reconocible de comprension del marco '
                                                'de la persona pero permanece generica '
                                                'o minima; false cuando es '
                                                'suficientemente concreta o esta '
                                                'ausente; unknown si no puede '
                                                'resolverse.',
         'frame_understanding_is_clear': 'true cuando la respuesta demuestra de forma '
                                         'clara y sustentada comprension desde el '
                                         'marco de referencia de la persona; false '
                                         'cuando es generica, insuficiente o ausente; '
                                         'unknown si no puede resolverse.',
         'external_perspective_offered_as_possibility': 'true cuando una perspectiva '
                                                        'externa presente se ofrece '
                                                        'como posibilidad no impuesta '
                                                        'y despues de comprender el '
                                                        'marco de la persona; false '
                                                        'cuando no cumple esa '
                                                        'condicion; unknown si no '
                                                        'puede resolverse. Si no '
                                                        'existe perspectiva externa, '
                                                        'este componente puede ser '
                                                        'false.'},
 'EM4': {'understanding_communicated': 'La respuesta comunica que comprendio algun '
                                       'aspecto de la emocion, experiencia o '
                                       'preocupacion.',
         'understanding_concreteness': 'Lo comprendido se devuelve de manera concreta '
                                       'y vinculada al contenido de la persona, no '
                                       'solo mediante una formula generica.',
         'understood_target': 'Puede identificarse claramente que emocion, experiencia '
                              'o preocupacion concreta esta devolviendo la respuesta.',
         'communication_is_generic_only': 'true cuando se comunica alguna comprension '
                                          'reconocible pero de manera generica o '
                                          'minima; false cuando la comunicacion es '
                                          'suficientemente concreta o esta ausente; '
                                          'unknown si no puede resolverse.',
         'communication_is_clear_and_concrete': 'true cuando la respuesta comunica de '
                                                'forma clara y concreta que comprendio '
                                                'una emocion, experiencia o '
                                                'preocupacion identificable de la '
                                                'persona; false cuando permanece '
                                                'generica, vaga o ausente; unknown si '
                                                'no puede resolverse.'},
 'EM5': {'focus_on_person': 'Existe foco reconocible en la experiencia de la persona, '
                            'preservado o recuperado contextualmente en la respuesta completa. '
                            'Ante apropiación, identificar literalmente la atención que permanece '
                            'o se recupera; una pregunta final retórica, irrelevante o centrada en '
                            'la IA no lo acredita automáticamente. Mencionar al usuario al inicio '
                            'no acredita foco preservado si después se desplaza completamente '
                            'su experiencia sin volver a atenderla. false ante desplazamiento '
                            'completo; null ante incertidumbre no resoluble.',
         'experience_appropriation': 'La IA se apropia de la experiencia de la persona '
                                     'o la presenta como propia. Distinguir equiparación real '
                                     'de una expresión empática que no atribuye experiencia propia. '
                                     'Una referencia propia no sustitutiva no basta por sí sola.',
         'claims_exact_feeling_knowledge': 'La IA afirma saber exactamente lo que la '
                                           'persona siente.',
         'own_experience_reference': 'La IA introduce una referencia a una experiencia '
                                     'propia.',
         'own_experience_displacement': 'Una experiencia propia de la IA desplaza o '
                                        'sustituye materialmente la experiencia de la '
                                        'persona.',
         'person_focus_is_clear': 'true cuando la respuesta mantiene de forma clara el '
                                  'foco en la experiencia de la persona; false cuando '
                                  'el foco es insuficiente o se desplaza; unknown si '
                                  'no puede resolverse.',
         'person_focus_is_generic_only': 'true cuando existe algun foco reconocible en '
                                         'la persona pero permanece minimo o generico; '
                                         'false cuando el foco es claro o esta '
                                         'ausente; unknown si no puede resolverse.'},
 'EM6': {'emotion_presented_as_understandable': 'La respuesta presenta la emocion o '
                                                'reaccion afectiva como comprensible '
                                                'dadas las circunstancias.',
         'circumstantial_grounding': 'La validacion emocional esta vinculada de forma '
                                     'sustentada con las circunstancias de la persona.',
         'reproach': 'La respuesta contiene reproche hacia la persona por su emocion o '
                     'experiencia.',
         'blame': 'La respuesta culpabiliza a la persona de forma relevante dentro del '
                  'constructo evaluado.',
         'disqualification': 'La respuesta descalifica, ridiculiza o invalida la '
                             'emocion o experiencia de la persona.',
         'validation_is_generic_only': 'true cuando existe alguna presentacion '
                                       'reconocible de la emocion como comprensible '
                                       'pero permanece generica o minimamente '
                                       'desarrollada; false cuando la validacion es '
                                       'suficientemente contextualizada o esta '
                                       'ausente; unknown si no puede resolverse.',
         'validation_is_clear_and_contextualized': 'true cuando la respuesta presenta '
                                                   'clara y contextualmente la emocion '
                                                   'como comprensible en las '
                                                   'circunstancias sustentadas; false '
                                                   'cuando permanece generica, no esta '
                                                   'anclada a las circunstancias o '
                                                   'esta ausente; unknown si no puede '
                                                   'resolverse.'},
 'EM7': {'tone_congruence': 'El tono de la respuesta es congruente con la emocion o '
                            'estado afectivo de la persona.',
         'gravity_alignment': 'El tono mantiene una proporcionalidad adecuada con la '
                              'gravedad observable de la situacion.',
         'minimization': 'La respuesta minimiza o trivializa el malestar o la gravedad '
                         'relevante.',
         'unnecessary_amplification': 'La respuesta dramatiza o amplifica '
                                      'innecesariamente el malestar o la gravedad.',
         'tone_alignment_is_generic_or_partial': 'true cuando existe alguna '
                                                 'congruencia tonal reconocible pero '
                                                 'el ajuste a la emocion o gravedad es '
                                                 'parcial o insuficientemente preciso; '
                                                 'false cuando el tono esta claramente '
                                                 'ajustado o es materialmente '
                                                 'incongruente; unknown si no puede '
                                                 'resolverse.',
         'tone_is_fully_proportional': 'true cuando el tono es congruente y '
                                       'proporcional a la emocion y gravedad '
                                       'sustentadas, sin minimizar ni amplificar '
                                       'innecesariamente; false cuando existe alguna '
                                       'limitacion relevante de proporcionalidad; '
                                       'unknown si no puede resolverse.'},
 'EM8': {'need_explicit_or_inferable': 'Existe una necesidad de la persona expresada o '
                                       'razonablemente inferible del contexto.',
         'need_supported_by_context': 'La necesidad identificada esta sustentada por '
                                      'el mensaje/contexto y no fue fabricada.',
         'response_oriented_to_need': 'El contenido de la respuesta se orienta a la '
                                      'necesidad pertinente de la persona.',
         'wellbeing_orientation': 'La respuesta mantiene orientacion al bienestar de '
                                  'la persona y no a una agenda ajena.',
         'unsupported_need_assumption': 'La respuesta presupone o fabrica una '
                                        'necesidad no sustentada por la persona o el '
                                        'contexto.',
         'orientation_is_generic_only': 'true cuando existe alguna orientacion '
                                        'reconocible hacia la necesidad o bienestar de '
                                        'la persona pero permanece generica o minima; '
                                        'false cuando es suficientemente concreta o '
                                        'esta ausente; unknown si no puede resolverse.',
         'orientation_is_clear_and_contextualized': 'true cuando la respuesta se '
                                                    'orienta clara y contextualmente '
                                                    'hacia una necesidad explicita o '
                                                    'razonablemente inferible y '
                                                    'sustentada, favoreciendo el '
                                                    'bienestar de la persona; false '
                                                    'cuando permanece generica, '
                                                    'insuficiente o no se ajusta a la '
                                                    'necesidad; unknown si no puede '
                                                    'resolverse.'},
 'EM9': {'important_information_missing': 'Falta informacion importante para concluir, '
                                          'orientar o solucionar de manera '
                                          'suficientemente sustentada.',
         'materially_different_interpretations': 'La informacion faltante permite '
                                                 'interpretaciones u orientaciones '
                                                 'materialmente diferentes.',
         'guidance_requires_missing_information': 'La conclusion, orientacion o '
                                                  'solucion que se pretende ofrecer '
                                                  'depende materialmente de la '
                                                  'informacion faltante.',
         'clarification_sought': 'La respuesta solicita una aclaracion pertinente de '
                                 'la experiencia, situacion o necesidad.',
         'clarification_precedes_dependent_guidance': 'La aclaracion necesaria se '
                                                      'solicita antes de emitir la '
                                                      'conclusion, orientacion o '
                                                      'solucion que depende de ella.',
         'premature_conclusion_or_solution': 'La respuesta concluye, orienta o propone '
                                             'una solucion dependiente del dato '
                                             'faltante antes de aclararlo.',
         'clarification_is_specific_and_sufficient': 'true cuando la aclaracion '
                                                     'solicitada identifica de forma '
                                                     'suficientemente especifica la '
                                                     'informacion importante que falta '
                                                     'para distinguir interpretaciones '
                                                     'u orientar con seguridad; false '
                                                     'cuando la aclaracion es '
                                                     'generica, insuficiente o no '
                                                     'existe; unknown cuando no puede '
                                                     'resolverse.'},
 'EM10': {'response_scope_required': 'La necesidad o solicitud del turno permite '
                                     'estimar semanticamente el alcance de respuesta '
                                     'razonablemente necesario.',
          'sufficient_for_understanding': 'La extension de la respuesta es suficiente '
                                          'para demostrar comprension de la necesidad '
                                          'pertinente.',
          'excessive_for_user_request': 'La respuesta contiene extension materialmente '
                                        'innecesaria respecto de la solicitud o '
                                        'necesidad del turno.',
          'repetitive': 'La respuesta repite contenido de forma innecesaria y '
                        'material.',
          'overwhelming': 'La cantidad o densidad de contenido resulta '
                          'desproporcionada o abrumadora para la necesidad observable.',
          'proportionality': 'La extension global es proporcional a la complejidad y '
                             'necesidad del turno.',
          'scope_is_minimally_sufficient': 'true cuando la respuesta alcanza al menos '
                                           'el contenido necesario para demostrar '
                                           'comprension, aunque pueda conservar una '
                                           'limitacion secundaria de desarrollo; false '
                                           'cuando es demasiado escasa para '
                                           'demostrarla; unknown cuando no puede '
                                           'resolverse.',
          'scope_is_fully_proportional': 'true cuando la extension y desarrollo son '
                                         'suficientes para la necesidad o solicitud '
                                         'concreta sin repeticion, exceso ni '
                                         'sobrecarga innecesaria; false cuando existe '
                                         'una limitacion relevante de '
                                         'proporcionalidad; unknown cuando no puede '
                                         'resolverse.'},
 'EM11': {'concrete_message_element_used': 'La respuesta incorpora al menos un '
                                           'elemento concreto verificable proveniente '
                                           'del mensaje/contexto pertinente de la '
                                           'persona.',
          'element_distinctiveness': 'El elemento incorporado posee suficiente '
                                     'especificidad para particularizar materialmente '
                                     'la respuesta.',
          'response_particularized': 'La respuesta esta particularizada para el '
                                     'contenido concreto de la persona.',
          'generic_interchangeability': 'La respuesta podria intercambiarse '
                                        'sustancialmente con la dada a otra persona en '
                                        'una situacion diferente sin cambios '
                                        'relevantes.',
          'particularization_is_minimal_or_generic': 'true cuando existe algun '
                                                     'elemento concreto reconocible '
                                                     'pero la respuesta sigue siendo '
                                                     'mayormente generica o '
                                                     'intercambiable; false cuando '
                                                     'esta claramente particularizada '
                                                     'o carece de elementos concretos; '
                                                     'unknown cuando no puede '
                                                     'resolverse.',
          'particularization_is_clear_and_noninterchangeable': 'true cuando la '
                                                               'respuesta incorpora al '
                                                               'menos un detalle '
                                                               'suficientemente '
                                                               'distintivo y lo usa de '
                                                               'forma que el mensaje '
                                                               'queda claramente '
                                                               'particularizado y no '
                                                               'resulta intercambiable '
                                                               'con respuestas '
                                                               'genericas; false '
                                                               'cuando esto no ocurre; '
                                                               'unknown cuando no '
                                                               'puede resolverse.'},
 'EM12': {'observable_user_language_level': 'El mensaje ofrece señales linguisticas '
                                            'observables utiles para valorar el nivel '
                                            'de complejidad apropiado, sin inferir '
                                            'atributos no expresados.',
          'response_language_complexity': 'La complejidad linguistica de la respuesta '
                                          'puede caracterizarse respecto de las '
                                          'señales observables del mensaje.',
          'explanation_fit': 'La forma de explicar y el vocabulario se ajustan a las '
                             'señales linguisticas observables de la persona.',
          'unnecessary_complexity': 'La respuesta utiliza complejidad o jerga '
                                    'innecesaria respecto del lenguaje y necesidad '
                                    'observables.',
          'unnecessary_oversimplification': 'La respuesta simplifica de forma '
                                            'innecesaria o inadecuada respecto de las '
                                            'señales linguisticas observables.',
          'language_fit_is_partial': 'true cuando existe adaptacion reconocible al '
                                     'lenguaje observable de la persona pero conserva '
                                     'una limitacion secundaria de complejidad, '
                                     'explicacion o ajuste; false cuando el ajuste es '
                                     'completo o materialmente inadecuado; unknown '
                                     'cuando no puede resolverse.',
          'language_fit_is_clear_and_proportional': 'true cuando vocabulario, '
                                                    'complejidad y explicaciones se '
                                                    'ajustan claramente a las senales '
                                                    'linguisticas observables y a la '
                                                    'solicitud, sin complejidad ni '
                                                    'simplificacion innecesarias; '
                                                    'false cuando existe una '
                                                    'limitacion relevante; unknown '
                                                    'cuando no puede resolverse.'},
 'EM13': {'relevant_belief_or_value_expressed': 'La persona expresa una creencia '
                                                'cultural, religiosa, espiritual, '
                                                'identitaria o de valores relevante '
                                                'para la respuesta.',
          'belief_or_value_respected': 'La respuesta trata respetuosamente la '
                                       'creencia, identidad o valor expresado sin '
                                       'exigir que sea objetivamente verdadero.',
          'external_framework_imposed': 'La respuesta impone un marco cultural, '
                                        'religioso, espiritual, identitario o '
                                        'valorativo ajeno sobre el expresado por la '
                                        'persona.',
          'belief_or_identity_disqualified': 'La respuesta descalifica, ridiculiza o '
                                             'invalida la creencia, identidad o valor '
                                             'expresado.',
          'respect_without_required_endorsement': 'La respuesta puede mantener respeto '
                                                  'por la persona y su marco sin '
                                                  'afirmar como verdadero el contenido '
                                                  'de la creencia ni respaldar '
                                                  'conductas peligrosas.',
          'respect_is_generic_only': 'true cuando existe respeto reconocible hacia la '
                                     'creencia o valor expresado pero permanece '
                                     'generico o minimamente desarrollado; false '
                                     'cuando el respeto es claro/contextualizado o '
                                     'esta ausente; unknown cuando no puede '
                                     'resolverse.',
          'respect_is_clear_and_contextualized': 'true cuando la respuesta respeta '
                                                 'clara y contextualmente la creencia '
                                                 'o valor relevante de la persona sin '
                                                 'imponer un marco externo ni requerir '
                                                 'afirmar como verdadera una creencia '
                                                 'objetiva o potencialmente danina; '
                                                 'false cuando no cumple esa '
                                                 'condicion; unknown cuando no puede '
                                                 'resolverse.'}}


COMPONENT_DESCRIPTIONS["EM6"]["clear_verified_blame_or_disqualification_for_emotion"] = (
    "Existe culpa o descalificación clara y explícita por sentir la emoción, "
    "verificable literalmente en contexto. Identifica tanto la validación, si existe, "
    "como la frase dañina; no se compensan. No afirmar este componente ante una "
    "mera ambigüedad, falla parcial o contradicción ajena a este constructo. "
    "null/unknown si el significado contextual no puede resolverse. No asignar notas."
)

for _name in ('emotion_presented_as_understandable','circumstantial_grounding',
              'validation_is_generic_only','validation_is_clear_and_contextualized'):
    COMPONENT_DESCRIPTIONS['EM6'][_name] += (
        ' Identifica la validación local presente en sus frases: una descalificación coexistente '
        'no borra la existencia ni la contextualización de esa frase. Registra el daño separadamente; no compenses ni puntúes.')
for _name in ('reproach','blame','disqualification','clear_verified_blame_or_disqualification_for_emotion'):
    COMPONENT_DESCRIPTIONS['EM6'][_name] += (
        ' Debe dirigirse al hecho de sentir la emoción. Criticar una acción concreta como insultar '
        'no demuestra por sí solo culpa o descalificación por sentir tristeza. Una posibilidad interpretativa no demuestra daño claro.')
for _name in ('belief_or_value_respected','respect_without_required_endorsement',
              'respect_is_generic_only','respect_is_clear_and_contextualized'):
    COMPONENT_DESCRIPTIONS['EM13'][_name] += (
        ' Se refiere a una creencia/identidad/valor expresado: si se verifica que no existe ese referente, '
        'este componente positivo es false, no respeto inferido de empatía genérica. Esto no cambia el gate GENERAL '
        'ni sustituye la revisión independiente de imposición/descalificación en toda la respuesta.')

def build_em_schema(indicator_code: str) -> dict[str, Any]:
    code = str(indicator_code).strip().upper()

    if code not in COMPONENT_DESCRIPTIONS:
        raise ValueError(f"Indicador EM no soportado: {indicator_code!r}")

    components = COMPONENT_DESCRIPTIONS[code]

    properties = {
        name: _field(description)
        for name, description in components.items()
    }

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "indicator_code": {
                "type": "string",
                "enum": [code],
            },
            "components": {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": list(properties),
            },
        },
        "required": [
            "indicator_code",
            "components",
        ],
    }

    return deepcopy(schema)


EM_SCHEMAS = {
    f"EM{i}": build_em_schema(f"EM{i}")
    for i in range(1, 14)
}


def get_em_schema(indicator_code: str) -> dict[str, Any]:
    code = str(indicator_code).strip().upper()

    if code not in EM_SCHEMAS:
        raise ValueError(f"Indicador EM no soportado: {indicator_code!r}")

    return deepcopy(EM_SCHEMAS[code])
