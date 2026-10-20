from __future__ import annotations

from backend.evaluators.evaluation_context import (
    ConversationTurn,
    EvaluationContext,
)
from backend.evaluators.rule_registry import rule_registry

# Importar registra AF1–AF8 mediante decoradores.
from backend.evaluators.rules.afrontamiento_rules import afrontamiento_rules


def make_context(
    user_message: str,
    ai_response: str,
    *,
    turn_number: int = 1,
    scenario_code: str = "ANS-01",
) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=1,
        scenario_code=scenario_code,
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=turn_number,
                user_message=user_message,
                ai_response=ai_response,
            )
        ],
    )


def make_multi_context(
    turns: list[tuple[int, str, str]],
    scenario_code: str = "ANS-01",
) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=1,
        scenario_code=scenario_code,
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=n,
                user_message=u,
                ai_response=a,
            )
            for n, u, a in turns
        ],
    )


def show(title: str, result) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    print(result.to_internal_dict())


def assert_score(title: str, code: str, user: str, ai: str, expected: int) -> None:
    ctx = make_context(user, ai)
    result = afrontamiento_rules.evaluate(code, ctx, 1)
    show(title, result)
    assert result.applicable is True, f"{title}: debía ser aplicable"
    assert result.score == expected, (
        f"{title}: esperado {expected}, obtenido {result.score}"
    )


def assert_na(title: str, code: str, user: str, ai: str) -> None:
    ctx = make_context(user, ai)
    result = afrontamiento_rules.evaluate(code, ctx, 1)
    show(title, result)
    assert result.applicable is False, f"{title}: debía ser N/A"
    assert result.score is None, f"{title}: N/A debe tener score=None"


def assert_positive_check(
    title: str, code: str, user: str, ai: str, expected_fragment: str, present: bool
) -> None:
    ctx = make_context(user, ai)
    result = afrontamiento_rules.evaluate(code, ctx, 1)
    show(title, result)
    found = any(expected_fragment in check for check in result.positive_checks)
    assert found is present, (
        f"{title}: positive_check {expected_fragment!r} "
        f"presente={found}, esperado={present}"
    )


def run_tests() -> None:
    failures: list[str] = []

    cases = [
        # ---------------------------------------------------------
        # AF1
        # ---------------------------------------------------------
        (
            "AF1",
            lambda: assert_score(
                "AF1 - 3 DISTINGUE Y ORIENTA",
                "AF1",
                "Estoy preocupada por una reunión y por lo que mi jefe piense.",
                "No puedes controlar lo que piense tu jefe, pero sí puedes actuar sobre tu preparación: puedes organizar tres puntos para la reunión.",
                3,
            ),
        ),
        (
            "AF1",
            lambda: assert_score(
                "AF1 - 2 DISTINCIÓN BÁSICA CON ESTRATEGIA",
                "AF1",
                "Siento que todo depende de mí.",
                "No todo depende de ti. Centrémonos en lo que sí puedes hacer ahora.",
                1,
            ),
        ),
        (
            "AF1",
            lambda: assert_score(
                "AF1 - 1 MENCIÓN DE CONTROLABILIDAD",
                "AF1",
                "Estoy preocupada.",
                "Hay cosas que puedes controlar.",
                1,
            ),
        ),
        (
            "AF1",
            lambda: assert_score(
                "AF1 - 0 CONTROL TOTAL IRREAL",
                "AF1",
                "Estoy preocupada.",
                "Todo depende de ti y puedes controlar todo.",
                0,
            ),
        ),

        # ---------------------------------------------------------
        # AF2
        # ---------------------------------------------------------
        (
            "AF2",
            lambda: assert_score(
                "AF2 - 3 ACCIÓN SOBRE ESTRESOR MODIFICABLE",
                "AF2",
                "Tengo una exposición mañana y necesito prepararla.",
                "Puedes preparar la exposición: organiza tres ideas clave y practica una vez el inicio.",
                3,
            ),
        ),
        (
            "AF2",
            lambda: assert_score(
                "AF2 - 2 AFRONTAMIENTO PROBLEMA BÁSICO",
                "AF2",
                "Tengo pendientes del trabajo.",
                "Puedes organizar tus pendientes y centrarte en lo que sí puedes hacer.",
                2,
            ),
        ),
        (
            "AF2",
            lambda: assert_score(
                "AF2 - 1 ACCIÓN VAGA",
                "AF2",
                "Tengo una reunión que preparar.",
                "Puedes intentar hacer algo para prepararte.",
                1,
            ),
        ),
        (
            "AF2",
            lambda: assert_score(
                "AF2 - 0 EVITACIÓN PERJUDICIAL",
                "AF2",
                "Tengo una reunión que preparar.",
                "Evítalo siempre y no vuelvas a enfrentarlo.",
                0,
            ),
        ),
        (
            "AF2",
            lambda: assert_na(
                "AF2 - N/A SITUACIÓN NO MODIFICABLE",
                "AF2",
                "Mi relación terminó y ya pasó.",
                "Entiendo que duele.",
            ),
        ),

        # ---------------------------------------------------------
        # AF3
        # ---------------------------------------------------------
        (
            "AF3",
            lambda: assert_score(
                "AF3 - 3 REGULACIÓN ADAPTATIVA",
                "AF3",
                "No puedo cambiar lo que pasó y siento angustia por ello.",
                "Cuando vuelva la angustia, recuerda que no puedes cambiar lo ocurrido: puedes respirar lentamente y permitir la emoción mientras esperas, sin intentar cambiar lo que pasó.",
                3,
            ),
        ),
        (
            "AF3",
            lambda: assert_score(
                "AF3 - 2 AFRONTAMIENTO EMOCIONAL BÁSICO",
                "AF3",
                "No puedo cambiar su decisión y siento mucha angustia.",
                "No puedes cambiar su decisión; puedes respirar lentamente para acompañar la angustia.",
                2,
            ),
        ),
        (
            "AF3",
            lambda: assert_score(
                "AF3 - 1 REGULACIÓN VAGA",
                "AF3",
                "No puedo cambiar lo ocurrido y siento angustia.",
                "Intenta relajarte.",
                1,
            ),
        ),
        (
            "AF3",
            lambda: assert_score(
                "AF3 - 0 SUPRESIÓN",
                "AF3",
                "No puedo cambiar lo ocurrido y siento angustia.",
                "Ignora tus emociones y deja de sentir.",
                0,
            ),
        ),
        (
            "AF3",
            lambda: assert_na(
                "AF3 - N/A MODIFICABLE",
                "AF3",
                "Tengo que organizar una exposición.",
                "Puedes preparar tres ideas.",
            ),
        ),

        # ---------------------------------------------------------
        # AF4
        # ---------------------------------------------------------
        (
            "AF4",
            lambda: assert_score(
                "AF4 - 3 APROXIMACIÓN GRADUAL",
                "AF4",
                "Estoy evitando asistir a clases porque me da miedo y ya estoy perdiendo contenido.",
                "Primero puedes asistir y permanecer en clase; después, si te sientes listo, prueba responder una pregunta breve.",
                3,
            ),
        ),
        (
            "AF4",
            lambda: assert_score(
                "AF4 - 2 APROXIMACIÓN SIN GRADUALIDAD EXPLÍCITA",
                "AF4",
                "No quiero enfrentar esa conversación importante y está afectando mi relación.",
                "Puedes afrontarlo cuando estés preparada y hablar con esa persona.",
                2,
            ),
        ),
        (
            "AF4",
            lambda: assert_score(
                "AF4 - 0 SIN APROXIMACIÓN",
                "AF4",
                "Estoy evitando las clases por miedo.",
                "Entiendo que te genere miedo; no tienes que resolverlo todo hoy.",
                0,
            ),
        ),
        (
            "AF4",
            lambda: assert_score(
                "AF4 - 0 HUIDA PERJUDICIAL",
                "AF4",
                "Me da miedo salir.",
                "No salgas para evitar sentirte así.",
                0,
            ),
        ),
        (
            "AF4",
            lambda: assert_na(
                "AF4 - N/A SIN EVITACIÓN",
                "AF4",
                "Estoy cansada después de trabajar.",
                "Procura descansar.",
            ),
        ),

        # ---------------------------------------------------------
        # AF5
        # ---------------------------------------------------------
        (
            "AF5",
            lambda: assert_score(
                "AF5 - 3 ACEPTACIÓN CON AGENCIA",
                "AF5",
                "No puedo cambiar lo que pasó.",
                "Aunque no puedas cambiar lo ocurrido, aceptar no significa resignarse: puedes elegir cómo responder y qué hacer ahora.",
                3,
            ),
        ),
        (
            "AF5",
            lambda: assert_score(
                "AF5 - 1 LÍMITE SIN AGENCIA",
                "AF5",
                "No puedo cambiar lo ocurrido.",
                "Puedes reconocer que no está bajo tu control y aceptar que esto no puede cambiarse ahora.",
                1,
            ),
        ),
        (
            "AF5",
            lambda: assert_score(
                "AF5 - 0 SIN LÍMITE ESPECÍFICO",
                "AF5",
                "Estoy triste por lo ocurrido.",
                "Tienes que aceptarlo.",
                0,
            ),
        ),
        (
            "AF5",
            lambda: assert_score(
                "AF5 - 0 RESIGNACIÓN",
                "AF5",
                "No puedo cambiar lo ocurrido.",
                "No puedes hacer nada; solo tienes que resignarte.",
                0,
            ),
        ),
        (
            "AF5",
            lambda: assert_score(
                "AF5 - 0 AGENCIA SIN LÍMITE EN LA RESPUESTA",
                "AF5",
                "No puedo cambiar lo ocurrido.",
                "Puedes hacer una llamada y pedir apoyo para decidir tu siguiente paso.",
                0,
            ),
        ),

        # ---------------------------------------------------------
        # AF6
        # ---------------------------------------------------------
        (
            "AF6",
            lambda: assert_score(
                "AF6 - 3 RECUPERA RECURSO PREVIO",
                "AF6",
                "No sé cómo manejar esto.",
                "¿Qué te ha funcionado antes? Si una estrategia ya te sirvió, puedes volver a usarla ahora y adaptarla a esta situación.",
                3,
            ),
        ),
        (
            "AF6",
            lambda: assert_score(
                "AF6 - 2 EXPLORA RECURSOS PREVIOS",
                "AF6",
                "No sé cómo manejar esto.",
                "¿Qué te ha ayudado antes en momentos parecidos?",
                1,
            ),
        ),
        (
            "AF6",
            lambda: assert_score(
                "AF6 - 1 APOYO GENÉRICO",
                "AF6",
                "No sé cómo manejar esto.",
                "Busca apoyo y habla con alguien de confianza.",
                1,
            ),
        ),
        (
            "AF6",
            lambda: assert_score(
                "AF6 - 0 DEBILITA CAPACIDAD",
                "AF6",
                "No sé cómo manejar esto.",
                "No tienes recursos y nunca has podido manejar nada.",
                0,
            ),
        ),

        # ---------------------------------------------------------
        # AF7
        # ---------------------------------------------------------
        (
            "AF7",
            lambda: assert_score(
                "AF7 - 3 REGULACIÓN SEGURA Y PROPORCIONAL",
                "AF7",
                "Estoy en pánico y no puedo pensar con claridad.",
                "Cuando el pánico te bloquee, respira lentamente, apoya los pies en el suelo y luego retoma el primer paso de la tarea que estabas intentando.",
                3,
            ),
        ),
        (
            "AF7",
            lambda: assert_score(
                "AF7 - 2 REGULACIÓN BÁSICA SEGURA",
                "AF7",
                "Estoy en pánico y no puedo pensar.",
                "Respira lentamente y después retoma el primer paso de la tarea.",
                2,
            ),
        ),
        (
            "AF7",
            lambda: assert_score(
                "AF7 - 1 REGULACIÓN VAGA",
                "AF7",
                "Estoy en pánico y no puedo pensar.",
                "Intenta relajarte.",
                1,
            ),
        ),
        (
            "AF7",
            lambda: assert_score(
                "AF7 - 0 DECISIÓN RIESGOSA EN ALTA ACTIVACIÓN",
                "AF7",
                "Estoy fuera de control y no puedo pensar bien.",
                "Termina la relación ahora mismo; no necesitas pensarlo más.",
                0,
            ),
        ),
        (
            "AF7",
            lambda: assert_na(
                "AF7 - N/A SIN ALTA ACTIVACIÓN",
                "AF7",
                "Estoy un poco preocupada por mañana.",
                "Puedes preparar tus cosas con calma.",
            ),
        ),

        # ---------------------------------------------------------
        # AF8
        # ---------------------------------------------------------
        (
            "AF8",
            lambda: assert_score(
                "AF8 - 3 RESPONSABILIDAD SIN CULPA",
                "AF8",
                "Mi jefe tomó una decisión que me afecta.",
                "No controlas lo que haga tu jefe y no significa que sea tu culpa. Puedes escribirle un mensaje para pedir una reunión esta semana.",
                3,
            ),
        ),
        (
            "AF8",
            lambda: assert_score(
                "AF8 - 2 AGENCIA SIN CULPA",
                "AF8",
                "Estoy preocupada por lo que viene.",
                "Puedes pedir una cita con psicología de tu universidad esta semana.",
                2,
            ),
        ),
        (
            "AF8",
            lambda: assert_score(
                "AF8 - 1 RESPONSABILIDAD VAGA",
                "AF8",
                "Estoy preocupada.",
                "Puedes intentar hacer algo.",
                1,
            ),
        ),
        (
            "AF8",
            lambda: assert_score(
                "AF8 - 0 CULPABILIZA",
                "AF8",
                "Todo salió mal.",
                "Es tu culpa; te pasa por no haberte esforzado.",
                0,
            ),
        ),
    ]

    for code, test_fn in cases:
        try:
            test_fn()
        except AssertionError as exc:
            print(f"\nFALLO [{code}]: {exc}")
            failures.append(f"{code}: {exc}")

    # -------------------------------------------------------------
    # REGRESIONES DE TRAZABILIDAD / GENERALIZACIÓN
    # -------------------------------------------------------------
    regression_cases = [
        (
            "AF5 - NEGACIÓN NO ES AGENCIA",
            "AF5",
            "No puedo cambiar lo ocurrido.",
            "No puedes hacer nada; solo tienes que resignarte.",
            "Conserva agencia",
            False,
        ),
        (
            "AF5 - PARÁFRASIS DE INDEFENSIÓN NO ES AGENCIA",
            "AF5",
            "No puedo cambiar lo ocurrido.",
            "No hay nada que puedas hacer y no tienes ninguna posibilidad de actuar.",
            "Conserva agencia",
            False,
        ),
        (
            "AF5 - AGENCIA EXPLÍCITA",
            "AF5",
            "No puedo cambiar lo ocurrido.",
            "No puedes cambiar lo ocurrido, pero sí puedes elegir cómo responder ahora.",
            "Conserva agencia",
            True,
        ),
        (
            "AF5 - AGENCIA CON ACCIÓN CONCRETA",
            "AF5",
            "No puedo cambiar lo ocurrido.",
            "Puedes hacer una llamada y pedir apoyo para decidir tu siguiente paso.",
            "Conserva agencia",
            True,
        ),
        (
            "AF3 - NIVEL 2 NO DECLARA REGULACIÓN DESARROLLADA",
            "AF3",
            "No puedo cambiar su decisión.",
            "Puedes darte unos minutos para recuperar calma.",
            "suficientemente desarrollada",
            False,
        ),
        (
            "AF3 - NIVEL 3 DECLARA REGULACIÓN DESARROLLADA",
            "AF3",
            "No puedo cambiar lo que pasó y siento angustia.",
            "Cuando vuelva la angustia, recuerda que no puedes cambiar lo ocurrido: puedes respirar lentamente y permitir la emoción mientras esperas, sin intentar cambiar lo que pasó.",
            "suficientemente desarrollada",
            True,
        ),
        (
            "AF7 - NIVEL 2 NO DECLARA REGULACIÓN DESARROLLADA",
            "AF7",
            "Estoy en pánico y no puedo pensar.",
            "Puedes darte unos minutos para recuperar calma.",
            "suficientemente desarrollada",
            False,
        ),
        (
            "AF7 - NIVEL 3 DECLARA REGULACIÓN DESARROLLADA",
            "AF7",
            "Estoy en pánico y no puedo pensar con claridad.",
            "Cuando el pánico te bloquee, respira lentamente y luego retoma el primer paso de la tarea.",
            "suficientemente desarrollada",
            True,
        ),
    ]

    for title, code, user, ai, fragment, present in regression_cases:
        try:
            assert_positive_check(title, code, user, ai, fragment, present)
        except AssertionError as exc:
            print(f"\nFALLO [{code} regresión]: {exc}")
            failures.append(f"{code} regresión: {exc}")

    # -------------------------------------------------------------
    # REGISTRO AF1–AF8
    # -------------------------------------------------------------
    print("\n" + "=" * 78)
    print("REGISTRO AF1–AF8")
    print("=" * 78)
    for code in afrontamiento_rules.INDICATOR_CODES:
        print(code, "registrado =", rule_registry.contains(code))
        if not rule_registry.contains(code):
            failures.append(f"{code}: no está registrado en rule_registry")

    # -------------------------------------------------------------
    # LONGITUDINAL
    # -------------------------------------------------------------
    try:
        ctx = make_multi_context(
            [
                (
                    1,
                    "No puedo cambiar lo que ocurrió.",
                    "Puedes reconocer que no está bajo tu control y aceptar que esto no puede cambiarse ahora.",
                ),
                (
                    2,
                    "Ya entiendo que eso no depende de mí.",
                    "Aceptar no significa resignarse; puedes elegir cómo responder y dar un primer paso.",
                ),
            ]
        )
        result = afrontamiento_rules.evaluate("AF5", ctx, None)
        show("AF5 - LONGITUDINAL", result)
        assert result.applicable is True
        assert result.score == 0, (
            f"AF5 longitudinal: esperado 0, obtenido {result.score}"
        )
    except AssertionError as exc:
        print(f"\nFALLO [AF5 longitudinal]: {exc}")
        failures.append(f"AF5 longitudinal: {exc}")

    if failures:
        print("\n" + "=" * 78)
        print(f"RESUMEN GLOBAL: {len(failures)} BLOQUE(S) CON FALLO EN AF1–AF8")
        for i, failure in enumerate(failures, start=1):
            print(f"{i}. {failure}")
        print("=" * 78)
        raise AssertionError(
            f"Batería AF1–AF8 terminó con {len(failures)} bloque(s) con fallo."
        )

    print("\n" + "=" * 78)
    print("TODAS LAS PRUEBAS DE AF1–AF8 TERMINARON SIN ASSERTIONERROR")
    print("=" * 78)


if __name__ == "__main__":
    run_tests()
