from backend.evaluators.rules.cognitive_rules import CognitiveRules


def analyze_user(text: str):
    return CognitiveRules().analyze(
        user_message=text,
        ai_response=".",
    )


# ============================================================
# POSITIVOS CLAROS: LA EXPRESION GENERALIZA DE FORMA ABSOLUTA
# ============================================================

def test_todo_as_global_negative_generalization():
    result = analyze_user("Todo me sale mal.")
    assert result.user_has_absolute_thinking is True


def test_nada_as_global_negative_generalization():
    result = analyze_user("Nada de lo que hago sirve.")
    assert result.user_has_absolute_thinking is True


def test_nadie_as_global_negative_generalization():
    result = analyze_user("Nadie me toma en serio.")
    assert result.user_has_absolute_thinking is True


def test_siempre_as_repeated_global_generalization():
    result = analyze_user("Siempre arruino las cosas importantes.")
    assert result.user_has_absolute_thinking is True


def test_nunca_as_global_negative_generalization():
    result = analyze_user("Nunca hago nada bien.")
    assert result.user_has_absolute_thinking is True


# ============================================================
# NEGATIVOS CLAROS: MISMAS PALABRAS, SIN PENSAMIENTO ABSOLUTO
# ============================================================

def test_todo_as_reference_to_previous_information():
    result = analyze_user("De todo esto termino concluyendo que necesito pensarlo mejor.")
    assert result.user_has_absolute_thinking is False


def test_todo_as_completed_object():
    result = analyze_user("Revisé todo el documento antes de enviarlo.")
    assert result.user_has_absolute_thinking is False


def test_nada_as_absence_of_pending_tasks():
    result = analyze_user("No tengo nada pendiente para mañana.")
    assert result.user_has_absolute_thinking is False


def test_nadie_as_factual_attendance_description():
    result = analyze_user("Nadie asistió a la reunión que fue cancelada.")
    assert result.user_has_absolute_thinking is False


def test_siempre_as_schedule_description():
    result = analyze_user("La oficina siempre abre a las ocho según su horario.")
    assert result.user_has_absolute_thinking is False


def test_nunca_as_factual_personal_history():
    result = analyze_user("Nunca he viajado a Japón.")
    assert result.user_has_absolute_thinking is False
