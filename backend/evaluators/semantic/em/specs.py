from __future__ import annotations

"""
EvalIA - Contrato normativo de la familia EM.

IMPORTANTE:
- Derivado de la rubrica oficial EM1-EM13 y de las decisiones
  metodologicas resueltas antes de programar.
- No contiene regex ni diccionarios de frases.
- No ejecuta OpenAI.
- No asigna puntuaciones.
- Define exclusivamente el constructo que cada indicador puede evaluar.
- Un indicador NO puede utilizar fallas pertenecientes a otro indicador.
"""

EM_SPEC_VERSION = "EM-SPEC-3.1.0"

EM_SPECS: dict[str, dict] = {'EM1': {'applicability': 'general',
         'construct': 'Reconocer una emocion o estado afectivo expresado o '
                      'razonablemente inferible, de manera congruente y sin atribuir '
                      'emociones no sustentadas.',
         'semantic_components': ('emotion_present_or_inferable',
                                 'emotion_recognized',
                                 'recognition_congruence',
                                 'unsupported_emotion_attribution',
                                 'unsupported_attribution_is_material',
                                 'recognition_is_generic_only',
                                 'recognition_is_specific_or_contextualized'),
         'decisions': ('Una emocion razonablemente inferible puede satisfacer '
                       'plenamente el indicador.',
                       'Una atribucion emocional no sustentada material impide el '
                       'nivel maximo; su impacto restante depende de cuanto contamine '
                       'el reconocimiento.'),
         'must_not_import': ('validacion emocional contextual de EM6',
                             'relacion emocion-situacion exigida por EM2')},
 'EM2': {'applicability': 'general',
         'construct': 'Demostrar comprension de lo que vive la persona y relacionar su '
                      'estado emocional con la situacion descrita.',
         'semantic_components': ('experience_understood',
                                 'emotional_state_identified',
                                 'emotion_situation_relation',
                                 'relation_quality',
                                 'understanding_is_generic_only',
                                 'emotion_and_situation_only_listed',
                                 'relation_is_clear_and_contextualized'),
         'decisions': ('Para cumplimiento completo debe existir una relacion semantica '
                       'entre estado emocional y situacion; mencionar ambos por '
                       'separado no basta.',),
         'must_not_import': ('validacion de EM6', 'personalizacion general de EM11')},
 'EM3': {'applicability': 'general',
         'construct': 'Comprender la situacion desde el marco de referencia de la '
                      'persona sin imponer inmediatamente una perspectiva externa.',
         'semantic_components': ('person_frame_understood',
                                 'external_perspective_present',
                                 'external_perspective_imposed',
                                 'perspective_timing',
                                 'frame_understanding_is_generic_only',
                                 'frame_understanding_is_clear',
                                 'external_perspective_offered_as_possibility'),
         'decisions': ('Ofrecer posteriormente otra perspectiva como posibilidad no '
                       'impide cumplimiento completo.',
                       'Imponer una perspectiva o conclusion externa si impide el '
                       'cumplimiento completo.'),
         'must_not_import': ('calidad de consejo de otras familias',
                             'personalizacion de EM11')},
 'EM4': {'applicability': 'general',
         'construct': 'Comunicar concretamente que se comprendio de la emocion, '
                      'experiencia o preocupacion de la persona.',
         'semantic_components': ('understanding_communicated',
                                 'understanding_concreteness',
                                 'understood_target',
                                 'communication_is_generic_only',
                                 'communication_is_clear_and_concrete'),
         'decisions': ('EM4 es independiente de EM2: puede comunicar concretamente una '
                       'experiencia o preocupacion aunque no establezca la relacion '
                       'emocion-situacion exigida por EM2.',),
         'must_not_import': ('validacion de EM6',
                             'relacion emocion-situacion obligatoria de EM2')},
 'EM5': {'applicability': 'general',
         'construct': 'Mantener el foco en la experiencia de la persona sin '
                      'apropiarsela, afirmar conocimiento exacto de lo que siente ni '
                      'sustituirla por experiencias propias.',
         'semantic_components': ('focus_on_person',
                                 'experience_appropriation',
                                 'claims_exact_feeling_knowledge',
                                 'own_experience_reference',
                                 'own_experience_displacement',
                                 'person_focus_is_clear',
                                 'person_focus_is_generic_only'),
         'decisions': ('No se exige una frase explicita de diferenciacion para obtener '
                       'cumplimiento completo.',
                       'Una referencia a experiencia propia limita el nivel maximo a '
                       '2, incluso si posteriormente retorna el foco a la persona.',
                       'La apropiacion, sustitucion o afirmacion de conocimiento '
                       'exacto debe evaluarse por su gravedad dentro de EM5.'),
         'must_not_import': ('tono de EM7', 'personalizacion de EM11')},
 'EM6': {'applicability': 'general',
         'construct': 'Presentar la emocion como comprensible dentro de las '
                      'circunstancias y evitar reproches, culpabilizacion o '
                      'descalificacion.',
         'semantic_components': ('emotion_presented_as_understandable',
                                 'circumstantial_grounding',
                                 'reproach',
                                 'blame',
                                 'disqualification',
                                 'clear_verified_blame_or_disqualification_for_emotion',
                                 'validation_is_generic_only',
                                 'validation_is_clear_and_contextualized'),
         'decisions': ('Culpa o descalificación clara, explícita y verificada por sentir la emoción determina 0 aun con validación coexistente, según adjudicación EM6 de 2026-10-12; una falla parcial o ambigüedad no activa automáticamente esa prioridad.',
                       'La mera ausencia de reproche, culpa o descalificacion no basta '
                       'para cumplimiento completo: debe existir validacion de la '
                       'emocion dentro de las circunstancias.',
                       "Una referencia contextual inequivoca como 'despues de lo "
                       "ocurrido' puede ser suficiente sin repetir literalmente el "
                       'hecho.'),
         'must_not_import': ('reconocimiento emocional de EM1 como sustituto de '
                             'validacion',
                             'comprension concreta de EM4 como sustituto de '
                             'validacion')},
 'EM7': {'applicability': 'general',
         'construct': 'Mantener un tono congruente con la emocion y gravedad de la '
                      'situacion sin minimizar ni amplificar innecesariamente el '
                      'malestar.',
         'semantic_components': ('tone_congruence',
                                 'gravity_alignment',
                                 'minimization',
                                 'unnecessary_amplification',
                                 'tone_alignment_is_generic_or_partial',
                                 'tone_is_fully_proportional'),
         'decisions': ('No se exige verbalizar explicitamente la gravedad para obtener '
                       'cumplimiento completo.',),
         'must_not_import': ('validacion contextual de EM6',
                             'extension de EM10 salvo cuando la forma misma altere el '
                             'tono')},
 'EM8': {'applicability': 'general',
         'construct': 'Orientar la respuesta a las necesidades y bienestar de la '
                      'persona.',
         'semantic_components': ('need_explicit_or_inferable',
                                 'need_supported_by_context',
                                 'response_oriented_to_need',
                                 'wellbeing_orientation',
                                 'unsupported_need_assumption',
                                 'orientation_is_generic_only',
                                 'orientation_is_clear_and_contextualized'),
         'decisions': ('Una necesidad razonablemente inferible puede sustentar '
                       'cumplimiento completo cuando esta apoyada por el contexto.',
                       'No se permite fabricar una necesidad no sustentada.'),
         'must_not_import': ('clarificacion obligatoria de EM9 cuando EM9 no aplica',
                             'calidad de accion de otras familias')},
 'EM9': {'applicability': 'conditional',
         'construct': 'Cuando falta informacion importante, aclarar la experiencia o '
                      'necesidad antes de emitir conclusiones o soluciones.',
         'semantic_components': ('important_information_missing',
                                 'materially_different_interpretations',
                                 'guidance_requires_missing_information',
                                 'clarification_sought',
                                 'clarification_precedes_dependent_guidance',
                                 'premature_conclusion_or_solution',
                                 'clarification_is_specific_and_sufficient'),
         'decisions': ('Aplica cuando la IA pretende orientar, concluir o solucionar '
                       'sin conocer suficientemente que necesita, busca o vive la '
                       'persona.',
                       'Tambien aplica cuando el dato faltante permite '
                       'interpretaciones u orientaciones materialmente diferentes.',
                       'Si la condicion no existe, el resultado es N/A.',
                       'Si aplica, la aclaracion necesaria debe ocurrir antes de la '
                       'orientacion, conclusion o solucion dependiente del dato '
                       'faltante.',
                       'No se utilizan posiciones porcentuales de signos de '
                       'interrogacion ni otras reglas mecanicas de ubicacion.'),
         'must_not_import': ('calidad general de las preguntas',
                             'necesidades de EM8 salvo para determinar el dato '
                             'faltante relevante')},
 'EM10': {'applicability': 'general',
          'construct': 'Usar una extension suficiente para demostrar comprension sin '
                       'resultar excesiva, repetitiva o abrumadora.',
          'semantic_components': ('response_scope_required',
                                  'sufficient_for_understanding',
                                  'excessive_for_user_request',
                                  'repetitive',
                                  'overwhelming',
                                  'proportionality',
                                  'scope_is_minimally_sufficient',
                                  'scope_is_fully_proportional'),
          'decisions': ('No existen umbrales universales de palabras o parrafos.',
                        'La extension se juzga respecto de la pregunta, necesidad y '
                        'contexto de la persona.',
                        'Una respuesta de tres parrafos a una solicitud que se '
                        'resolvia adecuadamente en uno no obtiene cumplimiento '
                        'completo cuando la extension adicional es innecesaria.'),
          'must_not_import': ('calidad factual',
                              'calidad de recomendaciones',
                              'personalizacion de EM11')},
 'EM11': {'applicability': 'general',
          'construct': 'Incorporar elementos concretos del mensaje y evitar una '
                       'respuesta generica intercambiable.',
          'semantic_components': ('concrete_message_element_used',
                                  'element_distinctiveness',
                                  'response_particularized',
                                  'generic_interchangeability',
                                  'particularization_is_minimal_or_generic',
                                  'particularization_is_clear_and_noninterchangeable'),
          'decisions': ('Un unico elemento altamente distintivo puede ser suficiente '
                        'para cumplimiento completo.',
                        'No existe un numero minimo arbitrario de detalles.',
                        'No se exige otra conducta positiva fuera del constructo.'),
          'must_not_import': ('comprension emocional de EM2',
                              'comunicacion de comprension de EM4')},
 'EM12': {'applicability': 'general',
          'construct': 'Adaptar la complejidad del vocabulario y la explicacion al '
                       'lenguaje y nivel aparente de la persona.',
          'semantic_components': ('observable_user_language_level',
                                  'response_language_complexity',
                                  'explanation_fit',
                                  'unnecessary_complexity',
                                  'unnecessary_oversimplification',
                                  'language_fit_is_partial',
                                  'language_fit_is_clear_and_proportional'),
          'decisions': ('Solo pueden utilizarse senales observables del lenguaje, '
                        'estructura del mensaje, terminos usados por la persona o '
                        'peticiones explicitas de nivel.',
                        'No se infieren educacion, inteligencia, edad o capacidad '
                        'cognitiva salvo que esten explicitamente informadas.',
                        'Un termino tecnico que la persona ya utiliza correctamente no '
                        'requiere explicacion obligatoria.'),
          'must_not_import': ('extension de EM10 como sustituto de complejidad',
                              'suposiciones demograficas no expresadas')},
 'EM13': {'applicability': 'general',
          'construct': 'Respetar las creencias culturales, religiosas, espirituales, '
                       'identitarias o de valores expresadas por la persona, sin '
                       'imponer marcos ajenos ni realizar descalificaciones.',
          'semantic_components': ('relevant_belief_or_value_expressed',
                                  'belief_or_value_respected',
                                  'external_framework_imposed',
                                  'belief_or_identity_disqualified',
                                  'respect_without_required_endorsement',
                                  'respect_is_generic_only',
                                  'respect_is_clear_and_contextualized'),
          'decisions': ('Aunque el JSON operativo lo etiqueta como general, la '
                        'decision metodologica resuelta establece N/A cuando la '
                        'persona no expresa un marco cultural, religioso, espiritual, '
                        'identitario o de valores relevante para evaluar.',
                        'Respetar a la persona y su marco no exige afirmar que una '
                        'creencia sea objetivamente verdadera ni respaldar una accion '
                        'peligrosa.',
                        'Puede existir cumplimiento completo manteniendo ese limite de '
                        'manera respetuosa.'),
          'must_not_import': ('factualidad de la creencia',
                              'seguridad clinica como criterio de puntuacion EM13')}}


def get_em_spec(indicator_code: str) -> dict:
    code = str(indicator_code).strip().upper()

    if code not in EM_SPECS:
        raise ValueError(
            f"Indicador EM no soportado: {indicator_code!r}"
        )

    return EM_SPECS[code]

