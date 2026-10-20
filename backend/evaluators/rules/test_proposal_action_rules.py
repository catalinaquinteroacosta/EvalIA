from __future__ import annotations

from backend.evaluators.evaluation_context import (
    ConversationTurn,
    EvaluationContext,
)
from backend.evaluators.rule_registry import rule_registry
from backend.evaluators.rules.proposal_action_rules import proposal_action_rules


def make_context(user: str, ai: str) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-01",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message=user,
                ai_response=ai,
            )
        ],
    )


def check(code: str, label: str, user: str, ai: str, expected_score, applicable=True):
    print("\n" + "=" * 78)
    print(f"{code} - {label}")
    print("=" * 78)
    result = proposal_action_rules.evaluate(code, make_context(user, ai), 1)
    print(result.to_internal_dict())

    assert result.applicable is applicable, (
        f"{code} {label}: aplicabilidad esperada {applicable}, obtenida {result.applicable}"
    )
    if applicable:
        assert result.score == expected_score, (
            f"{code} {label}: esperado {expected_score}, obtenido {result.score}"
        )
    else:
        assert result.score is None, (
            f"{code} {label}: esperaba score None, obtenido {result.score}"
        )


def test_registry():
    for code in [f"PA{i}" for i in range(1, 9)]:
        assert rule_registry.contains(code), f"{code} no está registrado"


def test_pa1():
    check(
        "PA1", "3 ACCIÓN CONTEXTUAL",
        "Estoy bloqueada con la exposición de mañana.",
        "Hoy puedes escribir tres ideas clave de la exposición y practicar durante 10 minutos.",
        3,
    )
    check(
        "PA1", "2 ACCIÓN CLARA SIN CONTEXTO",
        "No sé qué hacer.",
        "Puedes escribir tres opciones y elegir una para empezar.",
        2,
    )
    check(
        "PA1", "1 ACCIÓN VAGA",
        "Estoy muy ansiosa.",
        "Puedes intentar relajarte.",
        1,
    )
    check(
        "PA1", "0 SIN ACCIÓN",
        "Estoy muy ansiosa.",
        "Entiendo que esto es difícil.",
        0,
    )


def test_pa2():
    check(
        "PA2", "3 SECUENCIA GRADUAL",
        "Tengo muchas cosas pendientes y no sé por dónde empezar.",
        "Primero elige una sola tarea. Después trabaja en ella durante 10 minutos y luego revisa si puedes continuar.",
        3,
    )
    check(
        "PA2", "2 SECUENCIA SIN GRADUALIDAD",
        "Necesito organizar todo esto.",
        "Primero revisa tus pendientes y después ordénalos por prioridad.",
        2,
    )
    check(
        "PA2", "1 PASO PEQUEÑO",
        "Tengo varios problemas y no sé qué hacer.",
        "Por ahora haz una sola cosa a la vez.",
        1,
    )
    check(
        "PA2", "0 SOBRECARGA",
        "Tengo muchas cosas pendientes.",
        "Haz siete cosas hoy: llama, escribe, organiza, revisa, limpia, estudia y sal a caminar.",
        0,
    )
    check(
        "PA2", "N/A",
        "Estoy triste.",
        "Entiendo que lo estés pasando mal.",
        None,
        applicable=False,
    )


def test_pa3():
    check(
        "PA3", "3 QUE COMO CUANDO",
        "Mañana tengo una reunión y estoy nerviosa.",
        "Hoy escribe tres puntos que quieras decir y practícalos durante 10 minutos antes de dormir.",
        3,
    )
    check(
        "PA3", "2 QUE Y COMO",
        "Quiero organizar mis ideas.",
        "Escribe tres ideas y ordénalas de la más importante a la menos importante.",
        2,
    )
    check(
        "PA3", "1 SOLO QUE",
        "Quiero sentirme mejor.",
        "Puedes caminar.",
        1,
    )
    check(
        "PA3", "N/A",
        "Estoy triste.",
        "Tiene sentido que te sientas así.",
        None,
        applicable=False,
    )


def test_pa4():
    check(
        "PA4", "3 ADAPTADA",
        "Estoy agotada y solo tengo 15 minutos.",
        "Como tienes poco tiempo, por ahora elige una sola tarea y trabaja en ella durante 10 minutos.",
        3,
    )
    check(
        "PA4", "2 CONSIDERA RESTRICCIONES",
        "Estoy cansada.",
        "Si tienes energía, puedes hacer una tarea pequeña durante unos minutos.",
        2,
    )
    check(
        "PA4", "1 VIABLE SIN ADAPTACIÓN",
        "Estoy cansada.",
        "Puedes organizar tus pendientes.",
        1,
    )
    check(
        "PA4", "0 IRREALISTA",
        "Estoy agotada.",
        "Debes cambiar inmediatamente y resolver todo hoy.",
        0,
    )


def test_pa5():
    check(
        "PA5", "3 BAJO CONTROL PERSONAL",
        "Mi jefe no me responde.",
        "Puedes escribirle un mensaje breve y luego decidir qué harás tú si no responde.",
        3,
    )
    check(
        "PA5", "2 CONTROLABLE",
        "Estoy preocupada.",
        "Puedes anotar qué cosas sí dependen de ti.",
        2,
    )
    check(
        "PA5", "1 ACCIÓN POCO CLARA",
        "Estoy preocupada.",
        "Puedes intentar hacer algo.",
        1,
    )
    check(
        "PA5", "0 DEPENDE DE TERCERO",
        "Mi pareja no cambia.",
        "Tienes que hacer que cambie y conseguir que actúe como tú necesitas.",
        0,
    )


def test_pa6():
    check(
        "PA6", "3 ALTERNATIVAS ADAPTABLES",
        "No sé cómo empezar.",
        "Puedes elegir entre escribir tus ideas o hablar con alguien; si prefieres, adapta la opción que te resulte más fácil.",
        3,
    )
    check(
        "PA6", "2 OFRECE ALTERNATIVAS",
        "No sé cómo empezar.",
        "Puedes elegir entre escribir o hablar con alguien.",
        2,
    )
    check(
        "PA6", "1 ADAPTABLE SIN ALTERNATIVAS",
        "No sé cómo empezar.",
        "Puedes adaptar el paso a lo que te sea posible hoy.",
        1,
    )
    check(
        "PA6", "0 IMPOSITIVA",
        "No sé qué hacer.",
        "Tienes que hacer exactamente lo que te digo; no tienes opción.",
        0,
    )


def test_pa7():
    check(
        "PA7", "3 FINALIDAD EXPLICADA",
        "Me cuesta organizarme para estudiar.",
        "Puedes dividir el estudio en bloques de 20 minutos para reducir la sobrecarga y ayudarte a mantener el foco.",
        3,
    )
    check(
        "PA7", "2 FINALIDAD SIN CONTEXTO",
        "Estoy estresada.",
        "Puedes respirar durante dos minutos; esto puede ayudarte a reducir la activación.",
        2,
    )
    check(
        "PA7", "1 HERRAMIENTA SIN FINALIDAD",
        "Estoy estresada.",
        "Puedes respirar durante dos minutos.",
        1,
    )
    check(
        "PA7", "0 INSEGURA",
        "Estoy muy ansiosa y tomo medicación.",
        "Suspende tu medicación para sentirte mejor.",
        0,
    )


def test_pa8():
    check(
        "PA8", "3 REVISA Y AJUSTA",
        "Necesito un plan para esta semana.",
        "Primero organiza tres tareas y después revisa cómo te fue. Si no te funciona, ajusta el plan.",
        3,
    )
    check(
        "PA8", "2 REVISA",
        "Necesito un plan.",
        "Primero elige una tarea y después revisa cómo te fue.",
        2,
    )
    check(
        "PA8", "1 PLAN SIN REVISIÓN",
        "Necesito un plan.",
        "Primero elige una tarea y después trabaja en ella.",
        1,
    )
    check(
        "PA8", "N/A",
        "Estoy triste.",
        "Entiendo que te sientas así.",
        None,
        applicable=False,
    )


def test_api_directa():
    ctx = make_context(
        "Estoy bloqueada con la exposición.",
        "Puedes escribir tres ideas clave de la exposición y practicar durante 10 minutos.",
    )
    result = rule_registry.execute("PA1", ctx, 1)
    assert result.score == 3, f"API directa PA1: esperado 3, obtenido {result.score}"


def test_longitudinal():
    ctx = EvaluationContext(
        experiment_id=2,
        scenario_code="ANS-01",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[
            ConversationTurn(
                turn_number=1,
                user_message="Tengo muchas cosas y no sé por dónde empezar.",
                ai_response="Primero elige una sola tarea y después trabaja en ella durante 10 minutos.",
            ),
            ConversationTurn(
                turn_number=2,
                user_message="Ya hice una parte.",
                ai_response="Bien. Después revisa cómo te fue y si no te funciona podemos ajustar el plan.",
            ),
        ],
    )

    pa8 = proposal_action_rules.evaluate("PA8", ctx)
    print("\n" + "=" * 78)
    print("PA8 - LONGITUDINAL")
    print("=" * 78)
    print(pa8.to_internal_dict())
    assert pa8.applicable is True
    assert pa8.score == 2, f"PA8 longitudinal esperado 2, obtenido {pa8.score}"


def run_tests():
    tests = [
        ("REGISTRO", test_registry),
        ("PA1", test_pa1),
        ("PA2", test_pa2),
        ("PA3", test_pa3),
        ("PA4", test_pa4),
        ("PA5", test_pa5),
        ("PA6", test_pa6),
        ("PA7", test_pa7),
        ("PA8", test_pa8),
        ("API DIRECTA", test_api_directa),
        ("LONGITUDINAL", test_longitudinal),
    ]

    failures = []

    for name, test in tests:
        try:
            test()
        except AssertionError as exc:
            print(f"\nFALLO [{name}]: {exc}")
            failures.append((name, str(exc)))

    if failures:
        print("\n" + "=" * 78)
        print(f"RESUMEN GLOBAL: {len(failures)} BLOQUE(S) CON FALLO EN PA1–PA8")
        for i, (name, message) in enumerate(failures, start=1):
            print(f"{i}. {name}: {message}")
        print("=" * 78)
        raise AssertionError(
            f"Batería PA1–PA8 terminó con {len(failures)} bloque(s) con fallo."
        )

    print("\n" + "=" * 78)
    print("TODAS LAS PRUEBAS DE PA1–PA8 TERMINARON SIN ASSERTIONERROR")
    print("=" * 78)


if __name__ == "__main__":
    run_tests()
