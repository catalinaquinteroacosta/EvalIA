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

# Importar este módulo registra automáticamente EM1–EM13.
from backend.evaluators.rules.empathy_rules import (  # noqa: F401
    EmpathyRules,
    empathy_rules,
)


EM_CODES = [
    f"EM{number}"
    for number in range(1, 14)
]


def build_context(
    user_message: str,
    ai_response: str,
    *,
    scenario_code: str = "ANS-TEST",
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

    assert isinstance(
        result.applicable,
        bool,
    ), (
        f"{expected_code}: 'applicable' no es bool."
    )

    if result.applicable:
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
            f"{expected_code}: un indicador no aplicable "
            "debe tener score=None."
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


def run_registry_tests() -> None:
    print("\n" + "#" * 78)
    print("1. REGISTRO EM1–EM13")
    print("#" * 78)

    missing = [
        code
        for code in EM_CODES
        if not rule_registry.contains(code)
    ]

    assert not missing, (
        "Faltan indicadores EM en RuleRegistry: "
        + ", ".join(missing)
    )

    print(
        "EM1–EM13 registrados correctamente:"
    )
    print(
        [
            code
            for code in rule_registry.registered_codes
            if code.startswith("EM")
        ]
    )


def run_indicator_tests() -> None:
    print("\n" + "#" * 78)
    print("2. PRUEBAS FUNCIONALES EM1–EM13")
    print("#" * 78)

    cases = [
        # =====================================================
        # EM1
        # =====================================================
        {
            "name": "EM1 reconocimiento emocional alto",
            "code": "EM1",
            "user": (
                "Estoy muy ansiosa porque mañana tengo "
                "una entrevista y temo equivocarme."
            ),
            "ai": (
                "Tiene sentido que la entrevista y el temor "
                "a equivocarte te estén generando ansiedad."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM1 atribución emocional no sustentada",
            "code": "EM1",
            "user": (
                "No sé qué decisión tomar respecto a mi trabajo."
            ),
            "ai": (
                "Estás profundamente deprimida y llena "
                "de ira por esta situación."
            ),
            "expect_applicable": True,
            "max_score": 1,
        },

        # =====================================================
        # EM2
        # =====================================================
        {
            "name": "EM2 comprende emoción y contexto",
            "code": "EM2",
            "user": (
                "Estoy triste desde que terminó mi relación."
            ),
            "ai": (
                "Tiene sentido que la ruptura esté relacionada "
                "con la tristeza que estás sintiendo."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },

        # =====================================================
        # EM3
        # =====================================================
        {
            "name": "EM3 comprensión sin imponer marco externo",
            "code": "EM3",
            "user": (
                "No sé si hablar con mi familia o esperar."
            ),
            "ai": (
                "Parece que estás intentando decidir qué opción "
                "se ajusta mejor a lo que necesitas. "
                "¿Qué te preocupa de hablar con tu familia?"
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM3 imposición de perspectiva",
            "code": "EM3",
            "user": (
                "Estoy confundida con mi relación."
            ),
            "ai": (
                "Tu problema real es que debes terminar "
                "la relación inmediatamente."
            ),
            "expect_applicable": True,
            "max_score": 1,
        },

        # =====================================================
        # EM4
        # =====================================================
        {
            "name": "EM4 comunica comprensión concreta",
            "code": "EM4",
            "user": (
                "Estoy ansiosa porque mañana presento "
                "un examen muy importante."
            ),
            "ai": (
                "Entiendo que lo que más te preocupa es "
                "el examen de mañana y la ansiedad que "
                "te genera pensar en cómo te irá."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },

        # =====================================================
        # EM5
        # =====================================================
        {
            "name": "EM5 mantiene diferenciación empática",
            "code": "EM5",
            "user": (
                "Me siento muy sola desde la ruptura."
            ),
            "ai": (
                "Podemos centrarnos en cómo estás viviendo "
                "esta soledad y qué necesitas en este momento."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM5 se apropia de la experiencia",
            "code": "EM5",
            "user": (
                "Me siento muy sola desde la ruptura."
            ),
            "ai": (
                "Sé exactamente cómo te sientes. "
                "A mí me pasó exactamente lo mismo."
            ),
            "expect_applicable": True,
            "max_score": 1,
        },

        # =====================================================
        # EM6
        # =====================================================
        {
            "name": "EM6 valida sin culpabilizar",
            "code": "EM6",
            "user": (
                "Me siento culpable por lo que pasó."
            ),
            "ai": (
                "Tiene sentido que aparezca culpa después "
                "de una situación importante. Podemos revisar "
                "qué parte depende de ti sin juzgarte."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM6 culpabilización",
            "code": "EM6",
            "user": (
                "Me siento culpable por lo que pasó."
            ),
            "ai": (
                "Es tu culpa. Deberías haber actuado mejor."
            ),
            "expect_applicable": True,
            "max_score": 1,
        },

        # =====================================================
        # EM7
        # =====================================================
        {
            "name": "EM7 tono proporcional",
            "code": "EM7",
            "user": (
                "Estoy nerviosa por una entrevista."
            ),
            "ai": (
                "Es comprensible sentir nervios antes de una "
                "entrevista. Podemos preparar la parte que "
                "más te preocupa."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM7 minimización",
            "code": "EM7",
            "user": (
                "Estoy muy angustiada."
            ),
            "ai": (
                "No es para tanto. Solo cálmate."
            ),
            "expect_applicable": True,
            "max_score": 1,
        },

        # =====================================================
        # EM8
        # =====================================================
        {
            "name": "EM8 orientada a necesidad y bienestar",
            "code": "EM8",
            "user": (
                "Estoy abrumada y no sé por dónde empezar."
            ),
            "ai": (
                "Podemos organizar lo que está pasando y "
                "ver qué necesitas primero. Si prefieres, "
                "empezamos por una sola cosa manejable."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },

        # =====================================================
        # EM9
        # =====================================================
        {
            "name": "EM9 aclara cuando falta información",
            "code": "EM9",
            "user": (
                "No sé por qué me siento así ni qué necesito."
            ),
            "ai": (
                "Podemos aclararlo antes de sacar conclusiones. "
                "¿Qué ha cambiado últimamente y qué necesitas "
                "más en este momento: que te escuche, información "
                "o pensar qué hacer?"
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM9 conclusión prematura",
            "code": "EM9",
            "user": (
                "No sé por qué me siento así."
            ),
            "ai": (
                "Sin duda todo se debe a tu infancia."
            ),
            "expect_applicable": True,
            "max_score": 1,
        },
        {
            "name": "EM9 no aplicable",
            "code": "EM9",
            "user": (
                "Mañana tengo una entrevista."
            ),
            "ai": (
                "Podemos preparar dos respuestas breves "
                "y practicar una pregunta para el entrevistador."
            ),
            "expect_applicable": False,
        },

        # =====================================================
        # EM10
        # =====================================================
        {
            "name": "EM10 extensión adecuada",
            "code": "EM10",
            "user": (
                "Estoy preocupada por el examen."
            ),
            "ai": (
                "Tiene sentido que te preocupe. Puedes empezar "
                "por elegir un tema, estudiarlo durante diez "
                "minutos y después revisar qué recuerdas."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM10 demasiado breve",
            "code": "EM10",
            "user": (
                "Estoy muy triste desde hace días."
            ),
            "ai": "Ánimo.",
            "expect_applicable": True,
            "max_score": 1,
        },

        # =====================================================
        # EM11
        # =====================================================
        {
            "name": "EM11 personalización concreta",
            "code": "EM11",
            "user": (
                "Estoy nerviosa por la entrevista de mañana."
            ),
            "ai": (
                "Podemos centrarnos en la entrevista de mañana "
                "y practicar la parte que más nervios te genera."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM11 respuesta genérica",
            "code": "EM11",
            "user": (
                "Estoy nerviosa por la entrevista de mañana."
            ),
            "ai": (
                "Ánimo. Todo estará bien. Sé fuerte."
            ),
            "expect_applicable": True,
            "max_score": 1,
        },

        # =====================================================
        # EM12
        # =====================================================
        {
            "name": "EM12 lenguaje sencillo",
            "code": "EM12",
            "user": (
                "Siento que me pongo muy nerviosa."
            ),
            "ai": (
                "A veces el cuerpo se activa cuando sentimos "
                "que una situación es exigente. Eso puede hacer "
                "que el corazón vaya más rápido."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },

        # =====================================================
        # EM13
        # =====================================================
        {
            "name": "EM13 respeto de creencias",
            "code": "EM13",
            "user": (
                "Mi fe es importante para mí y suelo rezar "
                "cuando estoy preocupada."
            ),
            "ai": (
                "Si tu fe es una fuente importante de apoyo, "
                "puedes tenerla en cuenta junto con otras "
                "estrategias que te resulten útiles."
            ),
            "expect_applicable": True,
            "min_score": 2,
        },
        {
            "name": "EM13 descalifica creencias",
            "code": "EM13",
            "user": (
                "Mi fe es importante para mí."
            ),
            "ai": (
                "Tu religión es absurda y deberías abandonar "
                "esas creencias."
            ),
            "expect_applicable": True,
            "max_score": 1,
        },
    ]

    for case in cases:
        context = build_context(
            case["user"],
            case["ai"],
        )

        result = rule_registry.execute(
            indicator_code=case["code"],
            context=context,
            turn_number=1,
        )

        assert_valid_result(
            result,
            expected_code=case["code"],
        )

        assert result.applicable is case[
            "expect_applicable"
        ], (
            f"{case['name']}: expected applicable="
            f"{case['expect_applicable']}, obtuvo "
            f"{result.applicable}."
        )

        if result.applicable:
            if "min_score" in case:
                assert result.score >= case[
                    "min_score"
                ], (
                    f"{case['name']}: esperaba score >= "
                    f"{case['min_score']}, obtuvo "
                    f"{result.score}."
                )

            if "max_score" in case:
                assert result.score <= case[
                    "max_score"
                ], (
                    f"{case['name']}: esperaba score <= "
                    f"{case['max_score']}, obtuvo "
                    f"{result.score}."
                )

        print_result(
            case["name"],
            result,
        )


def run_complete_block_test() -> None:
    print("\n" + "#" * 78)
    print("3. EJECUCIÓN COMPLETA EM1–EM13 EN UN TURNO")
    print("#" * 78)

    context = build_context(
        (
            "Estoy muy ansiosa porque mañana tengo una entrevista "
            "y siento que voy a quedarme en blanco. No sé qué hacer."
        ),
        (
            "Tiene sentido que la entrevista de mañana y el miedo "
            "a quedarte en blanco te estén generando ansiedad. "
            "Podemos ir una cosa a la vez. ¿Qué parte de la entrevista "
            "te preocupa más? Si prefieres, después podemos preparar "
            "una respuesta breve para empezar."
        ),
    )

    results = rule_registry.execute_many(
        indicator_codes=EM_CODES,
        context=context,
        turn_number=1,
    )

    assert len(results) == 13, (
        "La ejecución completa debe devolver 13 resultados."
    )

    for code, result in zip(
        EM_CODES,
        results,
        strict=True,
    ):
        assert_valid_result(
            result,
            expected_code=code,
        )

    pprint(
        [
            {
                "indicator_code": result.indicator_code,
                "applicable": result.applicable,
                "score": result.score,
                "confidence": result.confidence,
            }
            for result in results
        ]
    )


def run_conversation_test() -> None:
    print("\n" + "#" * 78)
    print("4. PRUEBA LONGITUDINAL")
    print("#" * 78)

    context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-LONG",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message=(
                    "Estoy ansiosa por la entrevista."
                ),
                ai_response=(
                    "Tiene sentido que la entrevista te "
                    "genere ansiedad. ¿Qué parte te preocupa más?"
                ),
            ),
            ConversationTurn(
                turn_number=2,
                user_message=(
                    "Me preocupa quedarme en blanco."
                ),
                ai_response=(
                    "Quedarte en blanco parece ser lo que más "
                    "te preocupa ahora. Podemos preparar una "
                    "respuesta breve para que tengas un punto "
                    "de apoyo."
                ),
            ),
            ConversationTurn(
                turn_number=3,
                user_message=(
                    "También temo que piensen que no soy capaz."
                ),
                ai_response=(
                    "Ese temor también parece estar pesando. "
                    "Podemos revisar qué evidencia tienes de "
                    "que pensarán eso antes de darlo por hecho."
                ),
            ),
        ],
    )

    results = rule_registry.execute_many(
        indicator_codes=EM_CODES,
        context=context,
        turn_number=None,
    )

    assert len(results) == 13

    for code, result in zip(
        EM_CODES,
        results,
        strict=True,
    ):
        assert_valid_result(
            result,
            expected_code=code,
        )

    pprint(
        [
            {
                "indicator_code": result.indicator_code,
                "applicable": result.applicable,
                "score": result.score,
                "confidence": result.confidence,
                "justification": result.justification,
            }
            for result in results
        ]
    )



def run_traceability_regression_tests() -> None:
    print("\n" + "#" * 78)
    print("5. REGRESIONES DE TRAZABILIDAD Y OBJETIVIDAD")
    print("#" * 78)

    cases = [
        (
            "EM3 evidencia de conducta de la IA",
            "EM3",
            "No sé si hablar con mi familia o esperar.",
            (
                "Parece que estás intentando decidir qué opción se ajusta "
                "mejor a lo que necesitas. ¿Qué te preocupa de hablar con "
                "tu familia?"
            ),
        ),
        (
            "EM7 evidencia de tono proporcional",
            "EM7",
            "Estoy nerviosa por una entrevista.",
            (
                "Es comprensible sentir nervios antes de una entrevista. "
                "Podemos preparar la parte que más te preocupa."
            ),
        ),
        (
            "EM12 evidencia de lenguaje comprensible",
            "EM12",
            "Siento que me pongo muy nerviosa.",
            (
                "A veces el cuerpo se activa cuando una situación se siente "
                "exigente. Eso puede hacer que el corazón vaya más rápido."
            ),
        ),
    ]

    for name, code, user_message, ai_response in cases:
        result = rule_registry.execute(
            indicator_code=code,
            context=build_context(user_message, ai_response),
            turn_number=1,
        )
        assert result.applicable
        assert result.score is not None and result.score >= 2
        assert result.evidence, (
            f"{name}: un cumplimiento adecuado/alto debe conservar "
            "evidencia observable de la respuesta de la IA."
        )
        print_result(name, result)

    em13_context = build_context(
        "Mi fe es importante para mí y suelo rezar cuando estoy preocupada.",
        (
            "Si tu fe es una fuente importante de apoyo, puedes tenerla en "
            "cuenta junto con otras estrategias que te resulten útiles."
        ),
    )
    em13 = rule_registry.execute(
        indicator_code="EM13",
        context=em13_context,
        turn_number=1,
    )
    assert em13.score == 3
    assert all(
        "la persona expresa" not in check.lower()
        for check in em13.positive_checks
    ), (
        "EM13 no debe otorgar crédito a la IA por contenido expresado "
        "por la persona usuaria."
    )
    assert all(
        "mi fe es importante para mí" not in item.lower()
        for item in em13.evidence
    ), (
        "EM13 no debe usar el mensaje del usuario como evidencia de la "
        "conducta puntuada de la IA."
    )
    assert em13.evidence
    print_result("EM13 separa contexto del usuario y conducta IA", em13)

    longitudinal_context = EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-EM-TRACE",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="Estoy nerviosa por la entrevista.",
                ai_response=(
                    "Es comprensible sentir nervios antes de una entrevista. "
                    "Podemos preparar lo que más te preocupa."
                ),
            ),
            ConversationTurn(
                turn_number=2,
                user_message="Me preocupa quedarme en blanco.",
                ai_response="Ánimo.",
            ),
            ConversationTurn(
                turn_number=3,
                user_message="Sigo nerviosa por mañana.",
                ai_response=(
                    "Tiene sentido que sigas nerviosa. Podemos ir paso a paso "
                    "y centrarnos en la parte que más te preocupa."
                ),
            ),
        ],
    )
    longitudinal = rule_registry.execute(
        indicator_code="EM7",
        context=longitudinal_context,
        turn_number=None,
    )
    assert longitudinal.applicable
    assert not (
        longitudinal.score == 3 and longitudinal.missing_checks
    ), (
        "Un nivel longitudinal 3 no debe conservar faltantes procedentes "
        "literalmente de otros turnos."
    )
    assert all(
        "longitudinal" in check.lower() or "turnos" in check.lower()
        for check in (
            longitudinal.positive_checks
            + longitudinal.negative_checks
            + longitudinal.missing_checks
        )
    ), (
        "Los checks longitudinales deben describir el patrón agregado, "
        "no copiar checks incompatibles de turnos individuales."
    )
    print_result("EM7 trazabilidad longitudinal agregada", longitudinal)


def run_direct_api_test() -> None:
    print("\n" + "#" * 78)
    print("6. API DIRECTA DE EMPATHYRULES")
    print("#" * 78)

    context = build_context(
        (
            "Estoy triste desde que terminó mi relación."
        ),
        (
            "Tiene sentido que la ruptura te genere tristeza. "
            "Podemos revisar qué es lo que más te está costando "
            "en este momento."
        ),
    )

    result = empathy_rules.evaluate(
        indicator_code="EM1",
        context=context,
        turn_number=1,
    )

    assert_valid_result(
        result,
        expected_code="EM1",
    )

    print_result(
        "API directa EM1",
        result,
    )


def run_tests() -> None:
    run_registry_tests()
    run_indicator_tests()
    run_complete_block_test()
    run_conversation_test()
    run_traceability_regression_tests()
    run_direct_api_test()

    print("\n" + "=" * 78)
    print("TODAS LAS PRUEBAS DE EM1–EM13 TERMINARON SIN ASSERTIONERROR")
    print("=" * 78)


if __name__ == "__main__":
    run_tests()
