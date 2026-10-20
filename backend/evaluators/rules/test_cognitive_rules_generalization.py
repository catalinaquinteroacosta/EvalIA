from backend.evaluators.rules.cognitive_rules import CognitiveRules


def analyze_user(text: str):
    """Analiza únicamente las señales cognitivas del mensaje del usuario."""
    return CognitiveRules().analyze(
        user_message=text,
        ai_response=".",
    )


# ============================================================
# 1. COGNICIONES EXPRESADAS DE FORMAS NO LITERALES
# ============================================================

def test_indirect_interpretation_is_detected():
    result = analyze_user(
        "Lo que me viene a la cabeza es que quizá ya no confían en mí."
    )
    assert result.user_has_cognitive_statement is True


def test_possible_explanation_is_detected():
    result = analyze_user(
        "Una posibilidad que estoy considerando es que haya entendido mal lo ocurrido."
    )
    assert result.user_has_cognitive_statement is True


def test_attributed_meaning_is_detected():
    result = analyze_user(
        "Para mí, que no me hayan llamado significa que algo salió mal."
    )
    assert result.user_has_cognitive_statement is True


def test_conclusion_is_detected():
    result = analyze_user(
        "De todo esto termino concluyendo que probablemente no cuentan conmigo."
    )
    assert result.user_has_cognitive_statement is True


def test_internal_question_as_cognition_is_detected():
    result = analyze_user(
        "No sé si estoy interpretando esto como una señal de que hice algo mal."
    )
    assert result.user_has_cognitive_statement is True


def test_competing_interpretations_are_detected():
    result = analyze_user(
        "Puede que solo esté ocupado, aunque también se me ocurre que quizá está evitando hablar conmigo."
    )
    assert result.user_has_cognitive_statement is True


# ============================================================
# 2. PREDICCIONES NEGATIVAS GENERALIZABLES
# ============================================================

def test_future_negative_expectation_without_catalog_phrase():
    result = analyze_user(
        "Tengo la sensación de que cuando llegue el momento probablemente no saldrá como espero."
    )
    assert result.user_has_negative_prediction is True


def test_feared_future_possibility_is_detected():
    result = analyze_user(
        "Me preocupa que esto termine teniendo consecuencias que no pueda manejar."
    )
    assert result.user_has_negative_prediction is True


def test_uncertain_negative_prediction_is_detected():
    result = analyze_user(
        "Quizá mañana descubra que las cosas están peor de lo que pensaba."
    )
    assert result.user_has_negative_prediction is True


# ============================================================
# 3. INFERENCIAS Y ATRIBUCIONES SOBRE OTRAS PERSONAS
# ============================================================

def test_indirect_mind_reading_is_detected():
    result = analyze_user(
        "Por la forma en que me miraron, me da la impresión de que no les gustó lo que dije."
    )
    assert result.user_has_mind_reading is True


def test_uncertain_mind_reading_is_detected():
    result = analyze_user(
        "Tal vez estén pensando que no estoy preparado para esto."
    )
    assert result.user_has_mind_reading is True


# ============================================================
# 4. GENERALIZACIONES Y AUTOEVALUACIONES
# ============================================================

def test_overgeneralization_with_new_wording_is_detected():
    result = analyze_user(
        "Cada vez que intento algo importante termino pensando que las cosas me salen mal."
    )
    assert result.user_has_overgeneralization is True


def test_self_labeling_with_new_label_is_detected():
    result = analyze_user(
        "Después de equivocarme empiezo a verme como alguien completamente incompetente."
    )
    assert result.user_has_self_labeling is True


# ============================================================
# 5. GUARDRAILS: NO TODO PENSAMIENTO ES PROBLEMÁTICO
# ============================================================

def test_neutral_opinion_does_not_open_distress_cognition():
    result = analyze_user(
        "Creo que esta película dura unas dos horas, pero eso no me preocupa."
    )
    assert result.user_has_cognitive_statement is False
    assert result.user_has_possible_distortion is False


def test_neutral_future_plan_is_not_negative_prediction():
    result = analyze_user(
        "Probablemente mañana termine el informe después del almuerzo."
    )
    assert result.user_has_negative_prediction is False


def test_objective_event_is_not_cognitive_statement():
    result = analyze_user(
        "La reunión empezó a las nueve y terminó a las diez."
    )
    assert result.user_has_cognitive_statement is False
    assert result.user_has_possible_distortion is False


def test_question_for_information_is_not_cognitive_distortion():
    result = analyze_user(
        "¿Puedes explicarme cuáles son los pasos para completar este formulario?"
    )
    assert result.user_has_possible_distortion is False


def test_uncertainty_alone_is_not_distortion():
    result = analyze_user(
        "No sé a qué hora llegará el paquete."
    )
    assert result.user_has_possible_distortion is False


# ============================================================
# 6. GUARDRAIL DE RIGIDEZ:
#    UNA PETICIÓN CONVERSACIONAL NO ES UNA EXIGENCIA COGNITIVA
# ============================================================

def test_conversational_request_is_not_absolute_thinking():
    result = analyze_user(
        "Necesito que me expliques esto con un ejemplo sencillo."
    )
    assert result.user_has_absolute_thinking is False


# ============================================================
# 7. CASOS DE CONTROL YA CONOCIDOS
# ============================================================

def test_classic_cognitive_statement_still_detected():
    result = analyze_user(
        "Pienso que voy a fracasar."
    )
    assert result.user_has_cognitive_statement is True


def test_classic_catastrophizing_still_detected():
    result = analyze_user(
        "Todo va a salir mal."
    )
    assert result.user_has_catastrophizing is True


def test_classic_mind_reading_still_detected():
    result = analyze_user(
        "Seguro piensa que soy incompetente."
    )
    assert result.user_has_mind_reading is True


def test_classic_self_labeling_still_detected():
    result = analyze_user(
        "Soy un fracaso."
    )
    assert result.user_has_self_labeling is True
