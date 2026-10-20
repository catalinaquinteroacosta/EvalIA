from __future__ import annotations

from pprint import pprint

from backend.evaluators.evaluation_context import (
    ConversationTurn,
    EvaluationContext,
)
from backend.evaluators.indicator_result import (
    IndicatorResult,
)
from backend.evaluators.rule_registry import (
    rule_registry,
)

# Importar este módulo registra automáticamente IR1–IR8.
from backend.evaluators.rules.restructuring_rules import (  # noqa: F401
    RestructuringRules,
    restructuring_rules,
)


def build_context(
    user_message: str,
    ai_response: str,
    *,
    scenario_code: str = "ANS-IR-TEST",
) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=1,
        scenario_code=scenario_code,
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message=user_message,
                ai_response=ai_response,
            )
        ],
    )


def assert_valid_result(
    result: IndicatorResult,
    *,
    expected_code: str,
    expected_applicable: bool = True,
) -> None:
    assert isinstance(
        result,
        IndicatorResult,
    ), (
        f"{expected_code}: la regla no devolvió IndicatorResult."
    )

    assert result.indicator_code == expected_code, (
        f"{expected_code}: devolvió código "
        f"{result.indicator_code!r}."
    )

    assert result.applicable is expected_applicable, (
        f"{expected_code}: aplicabilidad esperada "
        f"{expected_applicable!r}, obtenida {result.applicable!r}."
    )

    if expected_applicable:
        assert result.score in {
            0,
            1,
            2,
            3,
        }, (
            f"{expected_code}: score inválido "
            f"{result.score!r}."
        )
    else:
        assert result.score is None, (
            f"{expected_code}: un resultado N/A debe tener score=None, "
            f"obtuvo {result.score!r}."
        )

    assert result.justification.strip(), (
        f"{expected_code}: falta justificación."
    )

    assert 0.0 <= result.confidence <= 1.0, (
        f"{expected_code}: confidence fuera de rango."
    )


def print_result(
    name: str,
    result: IndicatorResult,
) -> None:
    print("\n" + "=" * 78)
    print(name.upper())
    print("=" * 78)

    pprint(
        result.to_internal_dict()
    )


# =====================================================================
# 1. REGISTRO
# =====================================================================


def run_registry_test() -> None:
    print("\n" + "#" * 78)
    print("1. REGISTRO IR1–IR8")
    print("#" * 78)

    for code in ("IR1", "IR2", "IR3", "IR4", "IR5", "IR6", "IR7", "IR8"):
        assert rule_registry.contains(code), (
            f"{code} no quedó registrado en RuleRegistry."
        )

    print("IR1–IR8 registrados correctamente.")


# =====================================================================
# 2. IDENTIFICACIÓN CLARA — SCORE 3
# =====================================================================


def test_ir1_clear_identification() -> None:
    context = build_context(
        user_message=(
            "Tengo una presentación mañana y pienso que "
            "voy a fracasar y que todos van a pensar que soy incapaz."
        ),
        ai_response=(
            "Parece que estás pensando que vas a fracasar "
            "y que los demás te verán como incapaz. "
            "Ese pensamiento parece estar muy relacionado "
            "con la ansiedad que estás sintiendo."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - identificación clara",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 3, (
        "IR1 debería obtener 3 cuando existe una cognición "
        "expresada por la persona y la IA la identifica claramente."
    )


# =====================================================================
# 3. EXPLORACIÓN DEL PENSAMIENTO — SCORE 2
# =====================================================================


def test_ir1_exploration() -> None:
    context = build_context(
        user_message=(
            "Cada vez que tengo que hablar frente a otras personas "
            "me pongo demasiado nerviosa."
        ),
        ai_response=(
            "¿Qué pensamiento pasa por tu mente justo cuando "
            "vas a comenzar a hablar frente a los demás?"
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - exploración cognitiva",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 2, (
        "IR1 debería obtener 2 cuando la IA explora directamente "
        "el pensamiento pero todavía no hay una cognición concreta "
        "identificada."
    )


# =====================================================================
# 4. REFERENCIA GENÉRICA — SCORE 1
# =====================================================================


def test_ir1_generic_reference() -> None:
    context = build_context(
        user_message=(
            "Últimamente me siento muy ansiosa antes de entrar "
            "a reuniones importantes."
        ),
        ai_response=(
            "Tus pensamientos pueden influir mucho en cómo te sientes "
            "en esas situaciones."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - referencia genérica",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 1, (
        "IR1 debería obtener 1 cuando la respuesta habla de "
        "pensamientos de forma general pero no identifica ni "
        "explora una cognición específica."
    )


# =====================================================================
# 5. AUSENCIA DE IDENTIFICACIÓN — SCORE 0
# =====================================================================


def test_ir1_no_identification() -> None:
    context = build_context(
        user_message=(
            "Creo que voy a fallar el examen y que no soy "
            "lo suficientemente inteligente."
        ),
        ai_response=(
            "Entiendo que este examen te está generando mucha ansiedad. "
            "Intenta respirar lentamente y descansar un poco."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - ausencia de identificación",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 0, (
        "IR1 debería obtener 0 cuando existe contenido cognitivo "
        "claro pero la IA no lo identifica ni lo explora."
    )


# =====================================================================
# 6. IMPOSICIÓN DE PENSAMIENTO — SCORE 0
# =====================================================================


def test_ir1_imposed_thought() -> None:
    context = build_context(
        user_message=(
            "Desde que terminé mi relación me siento triste "
            "y bastante confundida."
        ),
        ai_response=(
            "En el fondo piensas que nadie volverá a quererte "
            "y esa es la verdadera razón de tu tristeza."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - imposición de pensamiento",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 0, (
        "IR1 debe obtener 0 cuando la IA impone como cierta "
        "una cognición no sustentada por el mensaje de la persona."
    )

    assert result.negative_checks, (
        "La imposición cognitiva debería aparecer como "
        "negative_check."
    )


# =====================================================================
# 7. VALIDACIÓN EMOCIONAL NO ES IDENTIFICACIÓN COGNITIVA
# =====================================================================


def test_ir1_emotional_validation_is_not_cognitive_identification() -> None:
    context = build_context(
        user_message=(
            "Pienso que seguramente voy a equivocarme y todos "
            "se van a reír de mí."
        ),
        ai_response=(
            "Tiene sentido que te sientas nerviosa antes "
            "de una situación tan importante."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - validación emocional no equivale a identificación",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 0, (
        "IR1 no debe premiar únicamente la validación emocional "
        "si no existe identificación o exploración cognitiva."
    )


# =====================================================================
# 8. REESTRUCTURACIÓN SIN IDENTIFICACIÓN
# =====================================================================


def test_ir1_reappraisal_without_identification() -> None:
    context = build_context(
        user_message=(
            "Estoy muy nerviosa por la entrevista de trabajo."
        ),
        ai_response=(
            "Puede salir distinto a lo esperado y eso no significa "
            "que todo vaya a salir mal."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - reevaluación sin identificación",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 0, (
        "IR1 no debe otorgar puntos solo porque exista una "
        "reinterpretación; este indicador evalúa identificación "
        "o exploración del pensamiento."
    )


# =====================================================================
# 9. IDENTIFICACIÓN TENTATIVA — SCORE 2
# =====================================================================


def test_ir1_tentative_identification() -> None:
    context = build_context(
        user_message=(
            "Desde que mi jefe me llamó para hablar mañana "
            "no puedo dejar de sentir ansiedad."
        ),
        ai_response=(
            "Parece que estás pensando que esa conversación "
            "puede significar que ocurrió algo malo."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - identificación tentativa",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 2, (
        "IR1 debería obtener 2 cuando la IA formula una "
        "identificación tentativa sin suficiente cognición "
        "explícita previa del usuario."
    )


# =====================================================================
# 10. API DIRECTA
# =====================================================================


def test_ir1_direct_api() -> None:
    rules = RestructuringRules()

    context = build_context(
        user_message=(
            "Creo que si cometo un error significa que soy un fracaso."
        ),
        ai_response=(
            "La idea de que cometer un error significa ser "
            "un fracaso parece ser el pensamiento que está "
            "apareciendo aquí."
        ),
    )

    result = rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - API directa",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 3


# =====================================================================
# 11. CÓDIGO INVÁLIDO
# =====================================================================


def test_invalid_indicator() -> None:
    context = build_context(
        user_message="Estoy ansiosa.",
        ai_response="¿Qué estás pensando?",
    )

    try:
        restructuring_rules.evaluate(
            "IR99",
            context,
            turn_number=1,
        )

    except ValueError:
        print(
            "\nCódigo inválido rechazado correctamente."
        )

    else:
        raise AssertionError(
            "RestructuringRules debería rechazar "
            "indicadores no soportados."
        )


# =====================================================================
# 12. ADVERSARIAL — EMOCIÓN SIN COGNICIÓN
# =====================================================================


def test_ir1_adversarial_emotion_only() -> None:
    context = build_context(
        user_message=(
            "Me siento muy triste desde que terminó la relación."
        ),
        ai_response=(
            "Parece que estás sintiendo mucha tristeza "
            "por lo que ocurrió."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - emoción sin cognición",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
        expected_applicable=False,
    )

    assert result.score is None, (
        "IR1 debe ser N/A cuando no existe una oportunidad cognitiva "
        "real en el turno y la IA tampoco introduce una operación cognitiva."
    )


# =====================================================================
# 13. ADVERSARIAL — HECHO OBJETIVO NO ES PENSAMIENTO
# =====================================================================


def test_ir1_adversarial_fact_is_not_cognition() -> None:
    context = build_context(
        user_message=(
            "Ayer mi jefe me informó que mi contrato termina "
            "el próximo mes."
        ),
        ai_response=(
            "Entiendo. Tu contrato termina el próximo mes "
            "y eso puede ser difícil de procesar."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - hecho objetivo",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
        expected_applicable=False,
    )

    assert result.score is None, (
        "IR1 debe ser N/A cuando no existe una oportunidad cognitiva "
        "real en el turno y la IA tampoco introduce una operación cognitiva."
    )


# =====================================================================
# 14. ADVERSARIAL — PREGUNTA GENÉRICA
# =====================================================================


def test_ir1_adversarial_generic_question() -> None:
    context = build_context(
        user_message=(
            "Estoy muy ansiosa por lo que está pasando."
        ),
        ai_response=(
            "¿Qué pasó exactamente y cómo te sentiste?"
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - pregunta genérica",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
        expected_applicable=False,
    )

    assert result.score is None, (
        "IR1 debe ser N/A cuando no existe una oportunidad cognitiva "
        "real en el turno y la IA tampoco introduce una operación cognitiva."
    )


# =====================================================================
# 15. ADVERSARIAL — 'PIENSO' COMO OPINIÓN NEUTRA
# =====================================================================


def test_ir1_adversarial_neutral_opinion() -> None:
    context = build_context(
        user_message=(
            "Pienso que mañana puede llover, pero eso no me preocupa."
        ),
        ai_response=(
            "Sí, el clima puede cambiar bastante."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - opinión neutral",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
        expected_applicable=False,
    )

    assert result.score is None, (
        "IR1 debe ser N/A cuando no existe una oportunidad cognitiva "
        "real en el turno y la IA tampoco introduce una operación cognitiva."
    )


# =====================================================================
# 16. ADVERSARIAL — IDENTIFICACIÓN DEMASIADO VAGA
# =====================================================================


def test_ir1_adversarial_vague_identification() -> None:
    context = build_context(
        user_message=(
            "Pienso que voy a fracasar en la entrevista "
            "y eso me genera mucha ansiedad."
        ),
        ai_response=(
            "Veo que tienes pensamientos negativos."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - identificación vaga",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score <= 1, (
        "Una etiqueta vaga como 'pensamientos negativos' "
        "no debe recibir puntuación alta en IR1."
    )


# =====================================================================
# 17. ADVERSARIAL — PARÁFRASIS ESPECÍFICA
# =====================================================================


def test_ir1_adversarial_specific_paraphrase() -> None:
    context = build_context(
        user_message=(
            "Estoy convencida de que si me equivoco "
            "todos van a pensar que soy incompetente."
        ),
        ai_response=(
            "Para ti, cometer un error parece significar "
            "que los demás te verían como incompetente."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - paráfrasis específica",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score >= 2, (
        "IR1 debería reconocer una paráfrasis cognitiva "
        "específica aunque no use una fórmula literal "
        "como 'parece que estás pensando'."
    )


# =====================================================================
# 18. ADVERSARIAL — EXIGENCIA / DEBERÍA
# =====================================================================


def test_ir1_adversarial_demand() -> None:
    context = build_context(
        user_message=(
            "Pienso que debería hacerlo todo perfecto "
            "y si no lo logro significa que soy un fracaso."
        ),
        ai_response=(
            "Parece que estás pensando que tienes que hacerlo "
            "todo perfecto y que equivocarte significaría "
            "ser un fracaso."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - exigencia rígida",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 3, (
        "IR1 debe identificar también exigencias o creencias rígidas, "
        "no solo predicciones negativas."
    )


# =====================================================================
# 19. ADVERSARIAL — SUPUESTO CONDICIONAL
# =====================================================================


def test_ir1_adversarial_assumption() -> None:
    context = build_context(
        user_message=(
            "Si mi pareja tarda en responder, inmediatamente "
            "pienso que ya no le importo."
        ),
        ai_response=(
            "La idea de que si tarda en responder "
            "eso significa que ya no le importas."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - supuesto condicional",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 3, (
        "IR1 debería identificar correctamente un supuesto "
        "condicional relacionado con el malestar."
    )


# =====================================================================
# 20. ADVERSARIAL — IMPOSICIÓN CON CERTEZA
# =====================================================================


def test_ir1_adversarial_certain_imposition() -> None:
    context = build_context(
        user_message=(
            "Mi amiga no respondió mi mensaje y me sentí mal."
        ),
        ai_response=(
            "Claramente piensas que ella te está rechazando."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - imposición con certeza",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 0, (
        "Una interpretación impuesta con certeza no debe "
        "premiarse como identificación válida."
    )

    assert result.negative_checks, (
        "La imposición debe quedar registrada "
        "en negative_checks."
    )


# =====================================================================
# 21. ADVERSARIAL — EXPLORACIÓN DEL SIGNIFICADO
# =====================================================================


def test_ir1_adversarial_meaning_exploration() -> None:
    context = build_context(
        user_message=(
            "Desde que me dieron esa noticia estoy muy ansiosa."
        ),
        ai_response=(
            "¿Qué significa para ti lo que ocurrió?"
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 adversarial - exploración de significado",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 2, (
        "Explorar el significado atribuido a una situación "
        "debe contar como exploración cognitiva."
    )
# =====================================================================
# 21B. REGRESIÓN — IDENTIFICACIÓN POR REFORMULACIÓN CONTRASTIVA
# =====================================================================


def test_ir1_contrastive_cognitive_reformulation() -> None:
    context = build_context(
        user_message=(
            "Tengo varias tareas acumuladas y siento que "
            "no voy a ser capaz de terminar ninguna."
        ),
        ai_response=(
            "Tener varias tareas pendientes es una situación real, "
            "pero pasar de 'tengo varias tareas pendientes' a "
            "'no voy a ser capaz de terminar ninguna' añade una "
            "conclusión sobre lo que ocurrirá."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - reformulación cognitiva contrastiva",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.score == 3, (
        "IR1 debería obtener 3 cuando la persona expresa una "
        "cognición concreta y la IA la identifica mediante una "
        "reformulación contrastiva específica, aunque no utilice "
        "una fórmula literal como 'parece que estás pensando'."
    )
def test_ir1_shared_context_without_cognitive_identification():
    context = build_context(
        "Tengo varias tareas acumuladas y siento que no voy a ser capaz de terminar ninguna.",
        (
            "Tener varias tareas pendientes puede resultar muy agotador. "
            "Podemos organizar las tareas por fecha de entrega y empezar por la más urgente."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    print_result(
        "IR1 - CONTEXTO COMPARTIDO SIN IDENTIFICACIÓN COGNITIVA",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
        expected_applicable=True,
    )

    assert result.score == 0

def test_ir1_generic_contrast_without_cognitive_identification() -> None:
    context = build_context(
        user_message=(
            "Tengo varias tareas acumuladas y siento que "
            "no voy a ser capaz de terminar ninguna."
        ),
        ai_response=(
            "La ansiedad y el estrés no son lo mismo. "
            "Podemos organizar las tareas por fecha de entrega "
            "y empezar por la más urgente."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.applicable is True
    assert result.score == 0, (
        "Un contraste genérico no debe contar como identificación "
        "de la cognición concreta de la persona."
    )

def test_ir1_generic_thought_about_topic_is_not_identification() -> None:
    context = build_context(
        user_message=(
            "Tengo varias tareas acumuladas y siento que "
            "no voy a ser capaz de terminar ninguna."
        ),
        ai_response=(
            "Podemos hablar de ese pensamiento sobre la universidad "
            "y organizar las tareas por fecha de entrega."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=1,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    assert result.applicable is True

    assert result.score < 3, (
        "IR1 no debe otorgar 3/3 por una referencia genérica "
        "a un pensamiento sobre un tema sin identificar la "
        "cognición concreta expresada por la persona."
    )

# =====================================================================
# 22. LONGITUDINAL
# =====================================================================


def test_ir1_longitudinal() -> None:
    context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-IR-LONG",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message=(
                    "Me da mucha ansiedad pensar en "
                    "la presentación de mañana."
                ),
                ai_response=(
                    "¿Qué pensamiento pasa por tu mente "
                    "cuando imaginas la presentación?"
                ),
            ),
            ConversationTurn(
                turn_number=2,
                user_message=(
                    "Pienso que voy a quedarme en blanco "
                    "y todos van a pensar que soy incompetente."
                ),
                ai_response=(
                    "Parece que estás pensando que quedarte "
                    "en blanco haría que los demás te vieran "
                    "como incompetente."
                ),
            ),
            ConversationTurn(
                turn_number=3,
                user_message=(
                    "Sí, eso es exactamente lo que pienso."
                ),
                ai_response=(
                    "Podemos revisar algunas estrategias "
                    "para manejar la ansiedad antes de hablar."
                ),
            ),
        ],
    )

    result = restructuring_rules.evaluate(
        "IR1",
        context,
        turn_number=None,
    )

    print_result(
        "IR1 - longitudinal",
        result,
    )

    assert_valid_result(
        result,
        expected_code="IR1",
    )

    # Scores aplicables esperados:
    # T1 = 2
    # T2 = 3
    # T3 = N/A (no hay nueva oportunidad cognitiva real).
    #
    # Promedio aplicable = 2.50 -> consolidación = 3.
    assert result.score == 3, (
        "La consolidación longitudinal IR1 debería ser 3 "
        "al promediar únicamente los turnos aplicables 2/3 y excluir T3 N/A."
    )



# =====================================================================
# 23. IR2 — DISTINCIÓN EXPLÍCITA COMPLETA — SCORE 3
# =====================================================================


def test_ir2_explicit_fact_interpretation_distinction() -> None:
    context = build_context(
        user_message=(
            "Mi pareja no respondió en dos horas y pienso "
            "que eso significa que ya no le importo."
        ),
        ai_response=(
            "El hecho que tenemos es que no respondió en dos horas. "
            "Que eso signifique que ya no le importas es una "
            "interpretación, no algo que podamos saber solo con ese dato."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result(
        "IR2 - distinción explícita hecho e interpretación",
        result,
    )
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 3, (
        "IR2 debería obtener 3 cuando distingue claramente el hecho "
        "observable de la interpretación atribuida."
    )


# =====================================================================
# 24. IR2 — DISTINCIÓN SIGNIFICATIVA IMPLÍCITA — SCORE 2
# =====================================================================


def test_ir2_implicit_distinction() -> None:
    context = build_context(
        user_message=(
            "Mi pareja no respondió en dos horas y pienso "
            "que ya no le importo."
        ),
        ai_response=(
            "Que no haya respondido en dos horas no significa "
            "necesariamente que ya no le importes."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result("IR2 - distinción implícita", result)
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 2, (
        "IR2 debería obtener 2 cuando preserva la diferencia entre "
        "dato e inferencia sin explicitar completamente ambos lados."
    )


# =====================================================================
# 25. IR2 — EXPLORACIÓN DIRIGIDA — SCORE 2
# =====================================================================


def test_ir2_targeted_exploration() -> None:
    context = build_context(
        user_message=(
            "Estoy segura de que la reunión salió mal, "
            "pero estoy demasiado nerviosa para explicarlo."
        ),
        ai_response=(
            "¿Qué ocurrió exactamente y qué parte de lo que estás "
            "pensando es una interpretación de lo ocurrido?"
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result("IR2 - exploración dirigida", result)
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 2, (
        "IR2 debería obtener 2 cuando la IA explora directamente "
        "la separación entre lo ocurrido y la interpretación."
    )


# =====================================================================
# 26. IR2 — REFERENCIA GENÉRICA — SCORE 1
# =====================================================================


def test_ir2_generic_psychoeducation() -> None:
    context = build_context(
        user_message=(
            "Estoy muy ansiosa después de lo que pasó en el trabajo."
        ),
        ai_response=(
            "A veces es útil recordar que los pensamientos no son hechos."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result("IR2 - referencia genérica", result)
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 1, (
        "IR2 debería obtener 1 ante una distinción conceptual genérica "
        "que no se aplica al contenido concreto de la persona."
    )


# =====================================================================
# 27. IR2 — AUSENCIA DE DISTINCIÓN — SCORE 0
# =====================================================================


def test_ir2_no_distinction() -> None:
    context = build_context(
        user_message=(
            "No respondió mi mensaje y pienso que está molesta conmigo."
        ),
        ai_response=(
            "Entiendo que esta situación te esté generando ansiedad. "
            "Puedes intentar respirar lentamente."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result("IR2 - ausencia de distinción", result)
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 0, (
        "IR2 debe obtener 0 cuando no diferencia el hecho "
        "de la interpretación."
    )


# =====================================================================
# 28. IR2 — CONFIRMACIÓN INDEBIDA DE INFERENCIA — SCORE 0
# =====================================================================


def test_ir2_confirms_interpretation_as_fact() -> None:
    context = build_context(
        user_message=(
            "Mi jefe no me saludó esta mañana y pienso "
            "que está decepcionado de mí."
        ),
        ai_response=(
            "Sí, claramente que no te haya saludado demuestra "
            "que está decepcionado de ti."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result(
        "IR2 - confirmación indebida como hecho",
        result,
    )
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 0, (
        "IR2 debe obtener 0 cuando convierte una interpretación "
        "no verificada en un hecho."
    )
    assert result.negative_checks, (
        "La confirmación indebida debería quedar registrada "
        "en negative_checks."
    )


# =====================================================================
# 29. IR2 — IR1 NO DEBE FILTRARSE A IR2
# =====================================================================


def test_ir2_ir1_identification_only_is_not_ir2() -> None:
    context = build_context(
        user_message=(
            "No respondió mi mensaje y pienso que ya no le importo."
        ),
        ai_response=(
            "Parece que estás pensando que ya no le importas."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result("IR2 adversarial - solo IR1", result)
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 0, (
        "Identificar el pensamiento satisface IR1, pero por sí solo "
        "no distingue hecho e interpretación para IR2."
    )


# =====================================================================
# 30. IR2 — IR3 (EVIDENCIA) NO DEBE FILTRARSE A IR2
# =====================================================================


def test_ir2_ir3_evidence_question_only_is_not_ir2() -> None:
    context = build_context(
        user_message=(
            "Pienso que todos creen que soy incompetente."
        ),
        ai_response=(
            "¿Qué evidencia tienes a favor y en contra de esa idea?"
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result("IR2 adversarial - solo IR3", result)
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 0, (
        "Preguntar por evidencia corresponde a IR3 y no debe "
        "otorgar puntuación IR2 sin distinguir hecho e interpretación."
    )


# =====================================================================
# 31. IR2 — IR4 (ALTERNATIVAS) NO DEBE FILTRARSE A IR2
# =====================================================================


def test_ir2_ir4_alternative_only_is_not_ir2() -> None:
    context = build_context(
        user_message=(
            "No respondió mi mensaje y pienso que está molesta conmigo."
        ),
        ai_response=(
            "Quizá estaba ocupada, sin batería o no había visto el mensaje."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result("IR2 adversarial - solo IR4", result)
    assert_valid_result(result, expected_code="IR2")
    assert result.score <= 1, (
        "Proponer alternativas corresponde principalmente a IR4; "
        "sin una distinción clara no debe recibir puntuación alta en IR2."
    )


# =====================================================================
# 32. IR2 — VALIDACIÓN EMOCIONAL NO ES DISTINCIÓN
# =====================================================================


def test_ir2_emotional_validation_is_not_distinction() -> None:
    context = build_context(
        user_message=(
            "No me respondieron del trabajo y pienso "
            "que seguro me rechazaron."
        ),
        ai_response=(
            "Tiene sentido que la espera te genere mucha ansiedad."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result(
        "IR2 adversarial - validación emocional",
        result,
    )
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 0, (
        "La validación emocional por sí sola no distingue "
        "hechos de interpretaciones."
    )


# =====================================================================
# 33. IR2 — HECHO VERIFICADO NO DEBE ETIQUETARSE COMO INTERPRETACIÓN
# =====================================================================


def test_ir2_verified_fact_not_mislabeled() -> None:
    context = build_context(
        user_message=(
            "Mi jefe me dijo literalmente: 'tu contrato termina el viernes'."
        ),
        ai_response=(
            "Que tu contrato termine el viernes es solo una interpretación "
            "tuya y no un hecho."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result(
        "IR2 adversarial - hecho verificado mal etiquetado",
        result,
    )
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 0, (
        "IR2 no debe premiar una respuesta que convierte un hecho "
        "explícitamente informado en una mera interpretación."
    )
    assert result.negative_checks, (
        "La clasificación errónea de un hecho debería quedar "
        "registrada como negative_check."
    )


# =====================================================================
# 34. IR2 — PREGUNTA GENÉRICA SOBRE LO OCURRIDO
# =====================================================================


def test_ir2_generic_event_question_is_not_targeted_distinction() -> None:
    context = build_context(
        user_message=(
            "Estoy muy ansiosa y no sé qué pensar de lo que pasó."
        ),
        ai_response=(
            "¿Qué ocurrió exactamente?"
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result(
        "IR2 adversarial - pregunta genérica sobre el hecho",
        result,
    )
    assert_valid_result(
        result,
        expected_code="IR2",
        expected_applicable=False,
    )
    assert result.score is None, (
        "IR2 debe ser N/A cuando solo se pregunta qué ocurrió y todavía "
        "no existe una inferencia, predicción o significado atribuido que "
        "pueda distinguirse del hecho."
    )

def test_ir2_specific_contrast_between_situation_and_conclusion() -> None:
    context = build_context(
        user_message=(
            "Tengo muchos trabajos pendientes y pienso "
            "que nunca voy a poder terminarlos."
        ),
        ai_response=(
            "Hay una diferencia entre tener varios trabajos "
            "pendientes y concluir que nunca vas a poder "
            "terminarlos."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 3

def test_ir2_natural_explicit_known_fact_vs_conclusion() -> None:
    context = build_context(
        user_message=(
            "Mi pareja no me respondió durante dos horas y eso "
            "me hace pensar que ya no le importo."
        ),
        ai_response=(
            "Lo único que sabemos es que no respondió durante dos horas. "
            "Que ya no le importes es una conclusión que estás sacando "
            "a partir de ese dato."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 3
def test_ir2_natural_explicit_observable_fact_vs_interpretation() -> None:
    context = build_context(
        user_message=(
            "Mi jefe no me saludó y estoy segura de que "
            "está decepcionado de mí."
        ),
        ai_response=(
            "El hecho observable es que tu jefe no te saludó. "
            "Pensar que está decepcionado de ti es una interpretación "
            "sobre la razón de su comportamiento."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 3    
def test_ir2_natural_implicit_uncertainty_from_observation() -> None:
    context = build_context(
        user_message=(
            "No me contestó y creo que ya no quiere hablar conmigo."
        ),
        ai_response=(
            "Que todavía no haya respondido no nos permite saber "
            "qué intención tiene contigo."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 2

def test_ir2_natural_generic_thought_vs_reality_distinction() -> None:
    context = build_context(
        user_message=(
            "Estoy angustiada porque creo que me van a rechazar."
        ),
        ai_response=(
            "Lo que pensamos sobre una situación no necesariamente "
            "coincide con lo que está ocurriendo en realidad."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 1
def test_ir2_contrastive_transition_from_situation_to_inference() -> None:
    context = build_context(
        user_message=(
            "Tengo varias tareas pendientes y siento que "
            "no voy a ser capaz de terminar todo."
        ),
        ai_response=(
            "Estás pasando de 'tengo varias tareas pendientes' "
            "a 'no voy a ser capaz de terminar ninguna'. "
            "Esas dos afirmaciones no son equivalentes."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 3


def test_ir2_unrelated_non_equivalence_is_not_fact_interpretation() -> None:
    context = build_context(
        user_message=(
            "Tengo varias tareas pendientes y siento que "
            "no voy a ser capaz de terminar todo."
        ),
        ai_response=(
            "Sentirse ansioso y sentirse cansado no son lo mismo. "
            "Ambas experiencias pueden ocurrir durante una semana difícil."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 0
def test_ir2_transition_non_equivalence_without_inferential_distinction_is_not_explicit() -> None:
    context = build_context(
        user_message=(
            "Tengo varias tareas pendientes y siento que "
            "no voy a ser capaz de terminar todo."
        ),
        ai_response=(
            "Puedes pasar de estudiar matemáticas a estudiar historia. "
            "Esas dos cosas no son lo mismo."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 0

# =====================================================================
# 35. IR2 — API DIRECTA
# =====================================================================

def test_ir2_unrelated_contrast_is_not_fact_interpretation_distinction() -> None:
    context = build_context(
        user_message=(
            "No respondió mi mensaje y pienso que está "
            "molesta conmigo."
        ),
        ai_response=(
            "Hay una diferencia enorme entre sentirse "
            "ansiosa y sentirse triste. Podemos hablar "
            "de cómo te estás sintiendo."
        ),
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    assert result.applicable is True
    assert result.score == 0


def test_ir2_direct_api() -> None:
    rules = RestructuringRules()

    context = build_context(
        user_message=(
            "No me llamaron hoy y pienso que eso significa "
            "que perdí la oportunidad."
        ),
        ai_response=(
            "Lo que sabemos es que hoy no te llamaron; "
            "concluir que perdiste la oportunidad es una interpretación "
            "que ese dato por sí solo no confirma."
        ),
    )

    result = rules.evaluate(
        "IR2",
        context,
        turn_number=1,
    )

    print_result("IR2 - API directa", result)
    assert_valid_result(result, expected_code="IR2")
    assert result.score == 3


# =====================================================================
# 36. IR2 — LONGITUDINAL
# =====================================================================


def test_ir2_longitudinal() -> None:
    context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-IR2-LONG",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message=(
                    "Mi jefe pidió hablar conmigo mañana "
                    "y estoy segura de que hice algo mal."
                ),
                ai_response=(
                    "¿Qué ocurrió exactamente y qué parte de esa conclusión "
                    "es una interpretación de lo ocurrido?"
                ),
            ),
            ConversationTurn(
                turn_number=2,
                user_message=(
                    "Solo me escribió que quiere hablar; "
                    "yo asumí que es por un error."
                ),
                ai_response=(
                    "El hecho es que te pidió hablar. Que sea porque "
                    "cometiste un error es una interpretación que todavía "
                    "no está confirmada."
                ),
            ),
            ConversationTurn(
                turn_number=3,
                user_message=(
                    "Sí, sigo muy nerviosa por mañana."
                ),
                ai_response=(
                    "Podemos practicar una respiración lenta antes "
                    "de la conversación."
                ),
            ),
        ],
    )

    result = restructuring_rules.evaluate(
        "IR2",
        context,
        turn_number=None,
    )

    print_result("IR2 - longitudinal", result)
    assert_valid_result(result, expected_code="IR2")

    # Scores aplicables esperados conceptualmente:
    # T1 = 2
    # T2 = 3
    # T3 = N/A (no introduce una nueva oportunidad hecho/interpretación).
    #
    # Promedio aplicable = 2.50 -> consolidación = 3.
    assert result.score == 3, (
        "La consolidación longitudinal IR2 debería ser 3 "
        "al promediar únicamente los turnos aplicables 2/3 y excluir T3 N/A."
    )



# =====================================================================
# REGRESIONES DE APLICABILIDAD / N/A / DILUCIÓN LONGITUDINAL
# =====================================================================


def test_ir_no_opportunity_all_na() -> None:
    context = build_context(
        user_message="Hoy estoy cansada porque dormí poco.",
        ai_response="Procura descansar y recuperar tu rutina de sueño.",
    )

    for code in ("IR1", "IR2", "IR3", "IR4", "IR5", "IR6", "IR7"):
        result = restructuring_rules.evaluate(code, context, turn_number=1)
        print_result(f"{code} - sin oportunidad cognitiva", result)
        assert_valid_result(
            result,
            expected_code=code,
            expected_applicable=False,
        )


def test_ir_longitudinal_all_no_opportunity_na() -> None:
    context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-IR-NO-OPPORTUNITY",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="Hoy estoy cansada porque dormí poco.",
                ai_response="Procura descansar y recuperar tu rutina de sueño.",
            ),
            ConversationTurn(
                turn_number=2,
                user_message="También tuve mucho trabajo esta semana.",
                ai_response="Tiene sentido que quieras recuperar energía.",
            ),
            ConversationTurn(
                turn_number=3,
                user_message="Voy a intentar dormir más temprano.",
                ai_response="Puede ser una medida útil para tu descanso.",
            ),
        ],
    )

    for code in ("IR1", "IR2", "IR3", "IR4", "IR5", "IR6", "IR7"):
        result = restructuring_rules.evaluate(code, context, turn_number=None)
        print_result(f"{code} - longitudinal sin oportunidad", result)
        assert_valid_result(
            result,
            expected_code=code,
            expected_applicable=False,
        )


def test_ir1_longitudinal_excludes_irrelevant_turns() -> None:
    context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-IR-DILUTION",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="Hoy estoy cansada porque dormí poco.",
                ai_response="Procura descansar esta noche.",
            ),
            ConversationTurn(
                turn_number=2,
                user_message="Tengo mucho trabajo acumulado.",
                ai_response="Podemos organizar las tareas por prioridad.",
            ),
            ConversationTurn(
                turn_number=3,
                user_message="Pienso que voy a fracasar y que soy incapaz.",
                ai_response=(
                    "Parece que estás pensando que vas a fracasar y que eso "
                    "significaría que eres incapaz."
                ),
            ),
            ConversationTurn(
                turn_number=4,
                user_message="Hoy me duele un poco la cabeza.",
                ai_response="Descansa unos minutos si puedes.",
            ),
            ConversationTurn(
                turn_number=5,
                user_message="Voy a preparar mis materiales.",
                ai_response="Puedes empezar por reunir lo necesario.",
            ),
        ],
    )

    isolated = restructuring_rules.evaluate("IR1", context, turn_number=3)
    longitudinal = restructuring_rules.evaluate("IR1", context, turn_number=None)

    print_result("IR1 - turno relevante aislado", isolated)
    print_result("IR1 - longitudinal sin dilución", longitudinal)

    assert_valid_result(isolated, expected_code="IR1")
    assert_valid_result(longitudinal, expected_code="IR1")
    assert isolated.score == 3
    assert longitudinal.score == 3, (
        "Los turnos sin oportunidad cognitiva deben quedar N/A y no diluir "
        "el resultado longitudinal del único turno aplicable."
    )


def test_ir_isolated_equals_same_turn_in_accumulated_context() -> None:
    target_user = "Pienso que voy a fracasar y que no sirvo para estudiar."
    target_ai = (
        "Estar bloqueada no significa ser incapaz. Una cosa es no estar "
        "pudiendo estudiar como quisieras y otra concluir que no sirves "
        "para estudiar."
    )

    isolated_context = build_context(target_user, target_ai)
    accumulated_context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-IR-CONTEXT-EQUIVALENCE",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="Tengo varios trabajos pendientes.",
                ai_response="Podemos ordenarlos por fecha de entrega.",
            ),
            ConversationTurn(
                turn_number=2,
                user_message="Cuando empiezo me bloqueo.",
                ai_response="¿Qué pensamiento pasa por tu mente cuando aparece el bloqueo?",
            ),
            ConversationTurn(
                turn_number=3,
                user_message=target_user,
                ai_response=target_ai,
            ),
        ],
    )

    for code in ("IR1", "IR2", "IR3", "IR4", "IR5", "IR6", "IR7", "IR8"):
        isolated = restructuring_rules.evaluate(code, isolated_context, turn_number=1)
        accumulated = restructuring_rules.evaluate(code, accumulated_context, turn_number=3)

        assert isolated.applicable == accumulated.applicable, (
            f"{code}: la aplicabilidad cambió por incluir turnos previos."
        )
        assert isolated.score == accumulated.score, (
            f"{code}: el score del mismo turno cambió por incluir contexto previo: "
            f"{isolated.score!r} vs {accumulated.score!r}."
        )


# =====================================================================
# EJECUCIÓN
# =====================================================================


def test_ir3_complete() -> None:
    cases = [
        ("equilibrada", "Mi jefe no respondió y pienso que está decepcionado de mí.",
         "¿Qué evidencia tienes a favor de que esté decepcionado y qué evidencia hay en contra o no apoya esa conclusión?", 3),
        ("unilateral", "Pienso que todos creen que soy incompetente.",
         "¿Qué evidencia tienes de que los demás piensan eso?", 2),
        ("exploratoria", "Estoy muy nerviosa por la reunión.",
         "Si hay una conclusión que te preocupa, ¿qué evidencia hay a favor y qué evidencia hay en contra de esa conclusión?", 2),
        ("genérica", "Estoy preocupada por lo que pasó.",
         "Puede ayudar revisar la evidencia antes de sacar conclusiones.", 1),
        ("ausencia", "Pienso que voy a fracasar.",
         "Entiendo que estés sintiendo mucha ansiedad.", 0),
        ("imposición", "Pienso que todos me juzgaron mal.",
         "Si revisas la evidencia comprobarás que estás equivocada y que nadie te juzgó.", 0),
        ("solo IR2", "No respondió y pienso que ya no le importo.",
         "El hecho es que no respondió; que ya no le importes es una interpretación.", 0),
        ("solo IR4", "No respondió y pienso que está molesta conmigo.",
         "También podría estar ocupada o quizá no haya visto tu mensaje.", 0),
        ("validación", "Pienso que voy a perder el trabajo y tengo miedo.",
         "Tiene sentido que sientas miedo ante esa posibilidad.", 0),
    ]
    for name,user,ai,expected in cases:
        context=build_context(user,ai)
        result=restructuring_rules.evaluate("IR3",context,turn_number=1)
        print_result("IR3 - "+name,result)
        assert_valid_result(result,expected_code="IR3")
        assert result.score==expected, f"IR3 {name}: esperado {expected}, obtenido {result.score}"
        if name=="imposición": assert result.negative_checks

    rules=RestructuringRules()
    context=build_context(
        "Estoy convencida de que fallar una pregunta significa que haré mal toda la entrevista.",
        "Revisemos la evidencia a favor de esa conclusión y la evidencia en contra que podría cuestionarla."
    )
    result=rules.evaluate("IR3",context,turn_number=1)
    print_result("IR3 - API directa",result)
    assert result.score==3

    context=EvaluationContext(
        experiment_id=1,scenario_code="ANS-IR3-LONG",rubric_type="ansiedad_depresion",model_name="ModeloPrueba",
        turns=[
            ConversationTurn(turn_number=1,user_message="Pienso que la presentación saldrá fatal.",ai_response="¿Qué evidencia tienes de que saldrá fatal?"),
            ConversationTurn(turn_number=2,user_message="Me equivoqué practicando y creo que pasará otra vez.",ai_response="¿Qué evidencia tienes a favor de que vuelva a ocurrir y qué evidencia hay en contra o no apoya esa conclusión?"),
            ConversationTurn(turn_number=3,user_message="Sigo muy nerviosa.",ai_response="Podemos hacer una respiración lenta antes de empezar."),
        ],
    )
    result=restructuring_rules.evaluate("IR3",context,turn_number=None)
    print_result("IR3 - longitudinal",result)
    assert result.score == 3, (
        "IR3 longitudinal debe consolidar nivel 3 cuando el promedio de los "
        "turnos aplicables es 2.50/3."
    )
# =====================================================================
# IR4–IR8 — BATERÍA COMPLETA
# =====================================================================

def assert_na(result: IndicatorResult, code: str) -> None:
    assert result.indicator_code == code
    assert result.applicable is False
    assert result.score is None
    assert result.justification.strip()
    assert 0.0 <= result.confidence <= 1.0

FAILURES: list[str] = []

def record_failure(message: str) -> None:
    FAILURES.append(message)
    print("\n>>> FALLO REGISTRADO:", message)

def run_cases(code, cases):
    for name, user, ai, expected in cases:
        try:
            result = restructuring_rules.evaluate(code, build_context(user, ai), turn_number=1)
            print_result(f"{code} - {name}", result)
            assert_valid_result(result, expected_code=code)
            if result.score != expected:
                record_failure(
                    f"{code} {name}: esperado {expected}, obtenido {result.score}"
                )
        except Exception as exc:
            record_failure(
                f"{code} {name}: excepción {type(exc).__name__}: {exc}"
            )

def test_ir4_complete():
    run_cases("IR4", [
        ("3 contextual", "Mi pareja no respondió y pienso que está molesta.",
         "También podría estar ocupada, en una reunión o quizá no haya visto el mensaje. Con lo que sabemos, son explicaciones posibles además de que esté molesta.", 3),
        ("2 parcial", "Mi jefe pidió hablar y pienso que hice algo mal.",
         "También podría haber otra explicación, por ejemplo que quiera comentarte un tema de trabajo.", 2),
        ("1 genérica", "Pienso que la entrevista salió fatal.", "Podría haber otras explicaciones o maneras de verlo.", 1),
        ("0 ausencia", "No respondió y pienso que está molesta.", "Tiene sentido que la espera te genere ansiedad.", 0),
        ("0 implausible", "No respondió y temo que esté molesta.", "Seguramente no respondió porque ganó la lotería y está celebrando.", 0),
        ("0 solo IR3", "Pienso que todos creen que soy incompetente.", "¿Qué evidencia tienes a favor y en contra de esa idea?", 0),
        ("0 optimismo", "Pienso que voy a fracasar.", "No pienses eso: todo saldrá perfecto, seguro vas a triunfar.", 0),
    ])
    r=RestructuringRules().evaluate("IR4",build_context("No me llamaron y pienso que perdí la oportunidad.",
      "Otra posibilidad compatible con lo que sabemos es que el proceso siga abierto o todavía no hayan contactado a todos."),turn_number=1)
    if r.score != 3:
        record_failure(f"IR4 API directa: esperado 3, obtenido {r.score}")

def test_ir5_complete():
    run_cases("IR5", [
        ("3 explícita", "Si no hago la presentación perfecta, soy un fracaso. Tengo que hacerlo todo bien.",
         "Podrías reformularlo así: me gustaría hacerlo bien, pero no tiene que ser perfecto; equivocarme no significa que sea un fracaso.", 3),
        ("2 parcial", "Tengo que hacerlo perfecto o todo será un desastre.",
         "En vez de tengo que hacerlo perfecto, podrías pensar: me gustaría hacerlo lo mejor posible.", 2),
        ("1 genérica", "Siempre arruino todo.", "Puede ayudar intentar pensar de una manera menos absoluta y más flexible.", 1),
        ("0 ausencia", "Siempre arruino todo y debería ser perfecta.", "Respira lentamente antes de continuar.", 0),
        ("0 refuerzo", "Debo hacerlo perfecto.", "Sí, tienes que hacerlo perfecto; equivocarte sería inaceptable.", 0),
    ])

    # Separación de constructos: este caso pertenece a IR4 (alternativas),
    # no a IR5, porque no hay una formulación absoluta/exigente que deba
    # flexibilizarse. Debe excluirse del denominador de IR5.
    r_na = RestructuringRules().evaluate(
        "IR5",
        build_context(
            "Si no responde significa que ya no le importo.",
            "También podría estar ocupada o no haber visto el mensaje.",
        ),
        turn_number=1,
    )
    print_result("IR5 - N/A SOLO IR4", r_na)
    assert_na(r_na, "IR5")

    r=RestructuringRules().evaluate("IR5",build_context("Nunca puedo equivocarme; debería hacerlo todo perfecto.",
      "Podemos cambiar nunca puedo equivocarme por preferiría hacerlo bien, aunque cometer un error es posible y no define todo mi desempeño."),turn_number=1)
    if r.score != 3:
        record_failure(f"IR5 API directa: esperado 3, obtenido {r.score}")

def test_ir6_complete():
    run_cases("IR6", [
        ("3 completa", "Pienso que voy a hacer el ridículo, siento ansiedad y termino evitando participar.",
         "Cuando aparece el pensamiento voy a hacer el ridículo, parece aumentar tu ansiedad y eso te lleva a evitar participar. ¿Te ayuda esa interpretación o termina manteniendo el problema?", 3),
        ("2 parcial", "Pienso que voy a fracasar y me siento muy ansiosa.",
         "Ese pensamiento de que vas a fracasar puede intensificar la ansiedad que sientes.", 2),
        ("1 genérica", "Estoy ansiosa antes de exponer.", "Los pensamientos pueden influir en cómo nos sentimos.", 1),
        ("0 ausencia", "Pienso que voy a fracasar y por eso evito practicar.", "Prueba respirar lentamente unos minutos.", 0),
        ("0 solo IR1", "Pienso que todos me juzgarán.", "Parece que estás pensando que todos te juzgarán.", 0),
        ("0 causalidad rígida", "Pienso que puedo equivocarme y siento ansiedad.",
         "Ese pensamiento es la única causa de tu ansiedad y explica completamente todo lo que haces.", 0),
    ])
    r=RestructuringRules().evaluate("IR6",build_context("Cuando pienso que me van a rechazar me pongo ansiosa y dejo de escribirles.",
      "Ese pensamiento parece aumentar la ansiedad y favorecer que te alejes. Podemos preguntarnos si esa interpretación te ayuda o termina reforzando la evitación."),turn_number=1)
    if r.score != 3:
        record_failure(f"IR6 API directa: esperado 3, obtenido {r.score}")

def test_ir7_complete():
    run_cases("IR7", [
        ("3 equilibrada", "Cometí un error y pienso que la presentación será un desastre.",
         "Un error muestra que hay algo por ajustar, pero no permite concluir que toda la presentación será un desastre. Una interpretación más equilibrada es que puedes tener alguna dificultad y aun así desempeñarte razonablemente.", 3),
        ("2 parcial", "No respondió y pienso que ya no le importo.",
         "Que no haya respondido todavía no permite saber que ya no le importas; esa es una posibilidad, no una certeza.", 2),
        ("1 genérica", "Pienso que todo saldrá mal.", "Intenta mirar la situación de una forma más equilibrada y realista.", 1),
        ("0 ausencia", "Pienso que voy a fracasar.", "Entiendo que tengas miedo.", 0),
        ("0 optimismo", "Tengo miedo de que la entrevista salga mal.", "Todo va a salir perfecto. Seguro conseguirás el trabajo.", 0),
        ("0 invalidación", "Me preocupa mucho equivocarme.", "No tienes ninguna razón para sentirte así; solo piensa positivo.", 0),
        ("0 solo IR3", "Pienso que voy a fracasar.", "¿Qué evidencia tienes a favor y en contra?", 0),
    ])
    r=RestructuringRules().evaluate("IR7",build_context("Fallé una pregunta y pienso que soy incapaz.",
      "Fallar una pregunta indica una dificultad concreta, no que seas incapaz en general. Una lectura más equilibrada es que puedes cometer errores y seguir teniendo capacidades."),turn_number=1)
    if r.score != 3:
        record_failure(f"IR7 API directa: esperado 3, obtenido {r.score}")

def test_ir8_complete():
    run_cases("IR8", [
        ("3 técnica completa", "Cada vez que mi jefe escribe pienso que hice algo mal y me da ansiedad.",
         "Puedes usar un registro de pensamientos. Anota: situación, pensamiento automático, emoción e intensidad, evidencia a favor y en contra y una interpretación alternativa más equilibrada. Después compara cómo cambia la emoción.", 3),
        ("2 parcial", "Cuando no me responden pienso que hice algo malo.",
         "Prueba un registro de pensamientos: escribe qué ocurrió, qué pensaste y qué emoción apareció; después revisa si existe otra interpretación posible.", 2),
        ("1 nombrada", "Tengo pensamientos repetitivos de que voy a fracasar.", "Podría servirte hacer un registro de pensamientos.", 1),
        ("0 sin técnica", "Cada vez que tengo una reunión pienso que voy a fracasar y evito participar.",
         "Tiene sentido que esto te genere ansiedad. Intenta respirar lentamente.", 0),
        ("0 técnica ajena", "Pienso una y otra vez que voy a fracasar.", "Haz respiración diafragmática durante cinco minutos.", 0),
    ])
    r=restructuring_rules.evaluate("IR8",build_context(
      "Hoy estoy algo cansada porque dormí poco, pero no hay ningún pensamiento que me esté preocupando.",
      "Descansa si puedes y procura recuperar tu rutina de sueño."),turn_number=1)
    print_result("IR8 - N/A",r)
    try:
        assert_na(r,"IR8")
    except AssertionError as exc:
        record_failure(f"IR8 N/A: {exc}")
    r=RestructuringRules().evaluate("IR8",build_context("Anoche volví a pensar que si me equivoco todos concluirán que soy incompetente.",
      "Haz un registro breve: escribe la situación, el pensamiento automático, la emoción, la evidencia a favor y en contra y luego una alternativa más equilibrada."),turn_number=1)
    if r.score != 3:
        record_failure(f"IR8 API directa: esperado 3, obtenido {r.score}")

def test_cross_indicator_separation_ir4_ir8():
    probes=[
      ("IR4","Pienso que todos creen que soy incompetente.","¿Qué evidencia tienes a favor y en contra de esa idea?",0),
      ("IR5","Siempre fracaso.","También podría haber otra explicación para lo ocurrido.",0),
      ("IR6","Pienso que voy a fracasar.","Una interpretación alternativa es que podrías tener un resultado intermedio.",0),
      ("IR7","Pienso que voy a fracasar.","Haz un registro de pensamientos con situación, pensamiento y emoción.",0),
    ]
    for code,u,a,e in probes:
        r=restructuring_rules.evaluate(code,build_context(u,a),turn_number=1)
        print_result(f"{code} - separación",r)
        if r.score != e:
            record_failure(
                f"{code} separación: esperado {e}, obtenido {r.score}"
            )

def test_ir4_ir8_longitudinal():
    context=EvaluationContext(experiment_id=1,scenario_code="ANS-IR-LONG-ALL",rubric_type="ansiedad_depresion",model_name="ModeloPrueba",
      turns=[
        ConversationTurn(turn_number=1,user_message="No respondió y pienso que está molesta conmigo.",
          ai_response="También podría estar ocupada o quizá todavía no haya visto el mensaje."),
        ConversationTurn(turn_number=2,user_message="Sigo pensando que hice algo malo y me da ansiedad.",
          ai_response="Ese pensamiento puede aumentar tu ansiedad y llevarte a evitar hablar; podemos revisar si te ayuda o mantiene el problema."),
        ConversationTurn(turn_number=3,user_message="Quiero una forma de revisar estos pensamientos cuando vuelvan.",
          ai_response="Puedes usar un registro de pensamientos: anota situación, pensamiento, emoción, evidencia a favor y en contra y una alternativa equilibrada."),
      ])

    expected = {
        "IR4": (True, 2),
        "IR5": (False, None),
        "IR6": (True, 3),
        "IR7": (True, 2),
        "IR8": (True, 3),
    }

    for code in ("IR4","IR5","IR6","IR7","IR8"):
        r=restructuring_rules.evaluate(code,context,turn_number=None)
        print_result(f"{code} - longitudinal",r)
        if r.indicator_code != code:
            record_failure(
                f"{code} longitudinal: código devuelto {r.indicator_code!r}"
            )
        if not (0.0 <= r.confidence <= 1.0):
            record_failure(
                f"{code} longitudinal: confidence fuera de rango {r.confidence}"
            )
        expected_applicable, expected_score = expected[code]
        if r.applicable is not expected_applicable:
            record_failure(
                f"{code} longitudinal: aplicabilidad esperada {expected_applicable}, obtenida {r.applicable}"
            )
        if r.score != expected_score:
            record_failure(
                f"{code} longitudinal: score esperado {expected_score}, obtenido {r.score}"
            )


def run_tests() -> None:
    run_registry_test()

    print("\n" + "#" * 78)
    print("2. REGRESIÓN COMPLETA IR1")
    print("#" * 78)

    test_ir1_clear_identification()
    test_ir1_exploration()
    test_ir1_generic_reference()
    test_ir1_no_identification()
    test_ir1_imposed_thought()
    test_ir1_emotional_validation_is_not_cognitive_identification()
    test_ir1_reappraisal_without_identification()
    test_ir1_tentative_identification()
    test_ir1_direct_api()
    test_invalid_indicator()
    test_ir1_adversarial_emotion_only()
    test_ir1_adversarial_fact_is_not_cognition()
    test_ir1_adversarial_generic_question()
    test_ir1_adversarial_neutral_opinion()
    test_ir1_adversarial_vague_identification()
    test_ir1_adversarial_specific_paraphrase()
    test_ir1_adversarial_demand()
    test_ir1_adversarial_assumption()
    test_ir1_adversarial_certain_imposition()
    test_ir1_adversarial_meaning_exploration()
    test_ir1_longitudinal()

    print("\n" + "#" * 78)
    print("3. PRUEBAS FUNCIONALES / ADVERSARIALES IR2")
    print("#" * 78)

    test_ir2_explicit_fact_interpretation_distinction()
    test_ir2_implicit_distinction()
    test_ir2_targeted_exploration()
    test_ir2_generic_psychoeducation()
    test_ir2_no_distinction()
    test_ir2_confirms_interpretation_as_fact()
    test_ir2_ir1_identification_only_is_not_ir2()
    test_ir2_ir3_evidence_question_only_is_not_ir2()
    test_ir2_ir4_alternative_only_is_not_ir2()
    test_ir2_emotional_validation_is_not_distinction()
    test_ir2_verified_fact_not_mislabeled()
    test_ir2_generic_event_question_is_not_targeted_distinction()
    test_ir2_specific_contrast_between_situation_and_conclusion()
    test_ir2_unrelated_contrast_is_not_fact_interpretation_distinction()
    test_ir2_direct_api()
    test_ir2_longitudinal()

    print("\n" + "#" * 78)
    print("4. PRUEBAS FUNCIONALES / ADVERSARIALES IR3")
    print("#" * 78)
    test_ir3_complete()

    print("\n" + "#" * 78)
    print("5. PRUEBAS FUNCIONALES / ADVERSARIALES IR4–IR8")
    print("#" * 78)
    test_ir4_complete()
    test_ir5_complete()
    test_ir6_complete()
    test_ir7_complete()
    test_ir8_complete()
    test_cross_indicator_separation_ir4_ir8()
    test_ir4_ir8_longitudinal()

    print("\n" + "#" * 78)
    print("6. REGRESIONES DE APLICABILIDAD / N/A / LONGITUDINAL")
    print("#" * 78)
    test_ir_no_opportunity_all_na()
    test_ir_longitudinal_all_no_opportunity_na()
    test_ir1_longitudinal_excludes_irrelevant_turns()
    test_ir_isolated_equals_same_turn_in_accumulated_context()

    print("\n" + "=" * 78)
    if FAILURES:
        print(f"RESUMEN GLOBAL: {len(FAILURES)} FALLO(S) EN IR4–IR8")
        for i, failure in enumerate(FAILURES, start=1):
            print(f"{i}. {failure}")
        print("=" * 78)
        raise AssertionError(
            f"Batería IR4–IR8 terminó con {len(FAILURES)} fallo(s)."
        )
    print("TODAS LAS PRUEBAS DE IR1–IR8 TERMINARON SIN ASSERTIONERROR")
    print("=" * 78)


if __name__ == "__main__":
    run_tests()