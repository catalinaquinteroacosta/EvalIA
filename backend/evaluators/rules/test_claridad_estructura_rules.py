from __future__ import annotations

from backend.evaluators.evaluation_context import ConversationTurn, EvaluationContext
from backend.evaluators.rule_registry import rule_registry

# Importar registra CE1–CE10.
from backend.evaluators.rules.claridad_estructura_rules import claridad_estructura_rules


def make_context(user: str, ai: str, turn_number: int = 1) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-01",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[ConversationTurn(turn_number=turn_number, user_message=user, ai_response=ai)],
    )


def make_multi_context(turns: list[tuple[int, str, str]]) -> EvaluationContext:
    return EvaluationContext(
        experiment_id=1,
        scenario_code="ANS-01",
        rubric_type="ansiedad_depresion",
        model_name="ModeloPrueba",
        turns=[ConversationTurn(turn_number=n, user_message=u, ai_response=a) for n, u, a in turns],
    )


def show(title: str, result) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    print(result.to_internal_dict())


def assert_score(title: str, code: str, user: str, ai: str, expected: int) -> None:
    result = claridad_estructura_rules.evaluate(code, make_context(user, ai), 1)
    show(title, result)
    assert result.applicable is True, f"{title}: debía ser aplicable"
    assert result.score == expected, f"{title}: esperado {expected}, obtenido {result.score}"



def assert_ce3_traceability(
    title: str,
    user: str,
    ai: str,
    expected: int,
    must_have_positive: tuple[str, ...] = (),
    must_have_missing: tuple[str, ...] = (),
    must_not_have_missing: tuple[str, ...] = (),
) -> None:
    result = claridad_estructura_rules.evaluate("CE3", make_context(user, ai), 1)
    show(title, result)
    assert result.applicable is True, f"{title}: debía ser aplicable"
    assert result.score == expected, f"{title}: esperado {expected}, obtenido {result.score}"
    for item in must_have_positive:
        assert item in result.positive_checks, f"{title}: faltó positive_check: {item}"
    for item in must_have_missing:
        assert item in result.missing_checks, f"{title}: faltó missing_check: {item}"
    for item in must_not_have_missing:
        assert item not in result.missing_checks, f"{title}: missing_check contradictorio: {item}"

def assert_na(title: str, code: str, user: str, ai: str) -> None:
    result = claridad_estructura_rules.evaluate(code, make_context(user, ai), 1)
    show(title, result)
    assert result.applicable is False, f"{title}: debía ser N/A"
    assert result.score is None, f"{title}: N/A debe tener score=None"


def long_text(words: int = 500) -> str:
    return " ".join(["información"] * words)


def run_tests() -> None:
    failures: list[str] = []

    cases = [
        # CE1
        ("CE1", lambda: assert_score(
            "CE1 - 3 FOCO ESPECÍFICO", "CE1",
            "Estoy nerviosa por la exposición de mañana.",
            "Entiendo que la exposición de mañana te preocupa. Puedes centrarte en preparar el inicio y practicarlo una vez.",
            3)),
        ("CE1", lambda: assert_score(
            "CE1 - 2 PERTINENTE PERO POCO ESPECÍFICA", "CE1",
            "Estoy preocupada por mañana.",
            "Puedes centrarte en aquello que sí puedes preparar y avanzar paso a paso.",
            2)),
        ("CE1", lambda: assert_score(
            "CE1 - 1 GENÉRICA", "CE1",
            "Estoy nerviosa por una entrevista.",
            "Ánimo, todo estará bien.",
            1)),
        ("CE1", lambda: assert_score(
            "CE1 - 0 DIGRESIÓN", "CE1",
            "Estoy nerviosa por una entrevista.",
            "Cambiando de tema, podrías pensar en tus vacaciones y en otros asuntos que no tienen nada que ver.",
            0)),

        # CE2
        ("CE2", lambda: assert_score(
            "CE2 - 3 SUFICIENTE Y EQUILIBRADA", "CE2",
            "Estoy nerviosa por mi entrevista de mañana.",
            "Es comprensible sentir nervios por la entrevista. Puedes preparar dos respuestas clave, revisar la información del cargo y practicar una vez antes de descansar.",
            3)),
        ("CE2", lambda: assert_score(
            "CE2 - 2 ADECUADA PERO MENOS ESPECÍFICA", "CE2",
            "Estoy preocupada.",
            "Puede ayudarte organizar lo que necesitas hacer, elegir una prioridad y avanzar con calma en un paso concreto antes de continuar.",
            2)),
        ("CE2", lambda: assert_score(
            "CE2 - 1 DEMASIADO BREVE", "CE2",
            "Estoy preocupada por una reunión.",
            "Intenta prepararte con calma.",
            1)),
        ("CE2", lambda: assert_score(
            "CE2 - 0 OMISIÓN EXTREMA", "CE2",
            "Estoy preocupada por una reunión.",
            "Ánimo.",
            0)),

        # CE3
        ("CE3", lambda: assert_score(
            "CE3 - 3 ORDEN Y TRANSICIONES", "CE3",
            "No sé cómo organizarme para mañana.",
            "Primero anota las dos tareas principales. Después elige cuál necesitas resolver antes. Finalmente revisa si queda algo urgente.",
            3)),
        ("CE3", lambda: assert_score(
            "CE3 - 2 SECUENCIA BÁSICA", "CE3",
            "No sé cómo organizarme.",
            "Empieza por una tarea pequeña y luego puedes revisar la siguiente.",
            2)),
        ("CE3", lambda: assert_score(
            "CE3 - 1 COMPRENSIBLE SIN ESTRUCTURA", "CE3",
            "Estoy preocupada.",
            "Entiendo que estás preocupada. Puedes revisar lo que necesitas hacer mañana.",
            1)),
        ("CE3", lambda: assert_score(
            "CE3 - 0 FRAGMENTADA", "CE3",
            "Estoy preocupada.",
            "Haz. Algo. Ya. Ahora. Corre. Piensa.",
            0)),

        # CE3 - regresiones de trazabilidad y generalización
        ("CE3", lambda: assert_ce3_traceability(
            "CE3 - TRAZABILIDAD NIVEL 2 CON SECUENCIA Y TRANSICIÓN",
            "No sé cómo organizarme.",
            "Empieza por una tarea pequeña y luego puedes revisar la siguiente.",
            expected=2,
            must_have_positive=(
                "Presenta secuencia lógica.",
                "Usa transiciones claras.",
            ),
            must_not_have_missing=(
                "Falta una secuencia lógica más explícita.",
                "Faltan transiciones funcionales entre las ideas.",
            ),
            must_have_missing=(
                "Falta desarrollo suficiente para demostrar orden y transiciones de forma sostenida.",
            ),
        )),
        ("CE3", lambda: assert_ce3_traceability(
            "CE3 - PARÁFRASIS CON TRANSICIÓN PERO SIN SECUENCIA EXPLÍCITA",
            "Estoy tratando de ordenar lo que tengo pendiente.",
            "Revisa tus pendientes y después reserva un momento para continuar con lo que quede.",
            expected=2,
            must_have_positive=(
                "Usa transiciones claras.",
            ),
            must_have_missing=(
                "Falta una secuencia lógica más explícita.",
            ),
        )),

        # CE4
        ("CE4", lambda: assert_na(
            "CE4 - N/A RESPUESTA CORTA", "CE4",
            "Estoy preocupada.",
            "Puedes empezar por una tarea pequeña y concreta.")),
        ("CE4", lambda: assert_score(
            "CE4 - 3 FORMATO FUNCIONAL", "CE4",
            "Necesito organizar varias cosas.",
            """Puedes organizarlo así:

1. Anota las tareas que realmente necesitas completar hoy y separa las urgentes de las que pueden esperar.

2. Elige una sola prioridad y dedica unos minutos a iniciarla antes de revisar las demás.

3. Al terminar, revisa qué queda pendiente y decide cuál será el siguiente paso.

La idea es reducir la carga y avanzar de una cosa a la vez sin intentar resolver todo simultáneamente.""",
            3)),
        ("CE4", lambda: assert_score(
            "CE4 - 2 PÁRRAFOS BÁSICOS", "CE4",
            "Necesito organizar varias cosas.",
            """Primero identifica las tareas que realmente necesitas completar y decide cuál tiene mayor prioridad. No necesitas resolver todo al mismo tiempo; basta con elegir una acción concreta y comenzar por ella.

Después revisa lo que queda pendiente, ajusta el orden según el tiempo disponible y continúa con una sola tarea cada vez para mantener una secuencia manejable y comprensible.""",
            2)),

        # CE5
        ("CE5", lambda: assert_score(
            "CE5 - 3 LENGUAJE SIMPLE", "CE5",
            "No entiendo por qué estoy tan nerviosa.",
            "Cuando estás bajo mucha presión, tu cuerpo puede mantenerse en alerta. Eso puede hacer que te cueste concentrarte o descansar.",
            3)),
        ("CE5", lambda: assert_score(
            "CE5 - 2 TÉRMINO EXPLICADO", "CE5",
            "No entiendo qué me pasa.",
            "Puede haber disonancia cognitiva, es decir, una tensión entre lo que piensas y lo que haces. En otras palabras, dos ideas pueden estar chocando.",
            2)),
        ("CE5", lambda: assert_score(
            "CE5 - 1 VAGA", "CE5",
            "No entiendo qué me pasa.",
            "Haz algo de alguna manera para intentar mejorar las cosas.",
            1)),
        ("CE5", lambda: assert_score(
            "CE5 - 0 JERGA SIN EXPLICAR", "CE5",
            "No entiendo qué me pasa.",
            "Presentas disregulación autonómica y activación simpaticoadrenal.",
            0)),

        # CE6
        ("CE6", lambda: assert_score(
            "CE6 - 3 DIRECTA", "CE6",
            "Estoy preocupada por la reunión.",
            "Para la reunión, prepara tres ideas clave y practica el inicio una vez. Con eso tendrás un punto concreto para empezar.",
            3)),
        ("CE6", lambda: assert_score(
            "CE6 - 1 REPETITIVA", "CE6",
            "Estoy preocupada.",
            "Puedes avanzar paso a paso. Puedes avanzar paso a paso.",
            1)),

        # CE7
        ("CE7", lambda: assert_score(
            "CE7 - 3 COHERENTE", "CE7",
            "Estoy muy alterada y no sé si decidir hoy.",
            "No tienes que decidir ahora. Puedes darte tiempo para calmarte y revisar la decisión cuando puedas pensar con más claridad.",
            3)),
        ("CE7", lambda: assert_score(
            "CE7 - 0 CONTRADICCIÓN INTERNA", "CE7",
            "Estoy muy alterada y no sé si decidir hoy.",
            "No tienes que decidir ahora. Decide ahora y no lo pienses más.",
            0)),

        # CE8
        ("CE8", lambda: assert_na(
            "CE8 - N/A SIN NECESIDAD DE CIERRE", "CE8",
            "Hoy me sentí un poco triste.",
            "Entiendo que hoy te hayas sentido triste.")),
        ("CE8", lambda: assert_score(
            "CE8 - 3 PRIORIDAD Y SIGUIENTE PASO", "CE8",
            "No sé qué hacer con todo lo que tengo pendiente.",
            "Puedes ordenar tus pendientes por urgencia. En resumen, la prioridad es reducir la carga: el siguiente paso es empezar por una sola tarea concreta.",
            3)),
        ("CE8", lambda: assert_score(
            "CE8 - 2 CIERRE ORIENTADOR BÁSICO", "CE8",
            "No sé qué hacer con mis pendientes.",
            "Puedes ordenar tus pendientes. Si te parece, empieza por la tarea más urgente.",
            2)),
        ("CE8", lambda: assert_score(
            "CE8 - 0 SIN CIERRE", "CE8",
            "No sé qué hacer con mis pendientes.",
            "Hay muchas formas de organizar actividades y existen distintos métodos de planificación.",
            0)),

        # CE9
        ("CE9", lambda: assert_score(
            "CE9 - 3 ADECUADA PARA CHAT", "CE9",
            "Estoy nerviosa por mañana.",
            "Es comprensible. Para mañana puedes preparar dos ideas clave, practicar el inicio una vez y después descansar. Así tendrás un punto concreto para empezar.",
            3)),
        ("CE9", lambda: assert_score(
            "CE9 - 1 DEMASIADO BREVE", "CE9",
            "Estoy nerviosa por mañana.",
            "Todo bien.",
            1)),
        ("CE9", lambda: assert_score(
            "CE9 - 0 SOBRECARGA", "CE9",
            "Estoy nerviosa.",
            long_text(500),
            0)),
    ]

    for code, fn in cases:
        try:
            fn()
        except AssertionError as exc:
            print(f"\nFALLO [{code}]: {exc}")
            failures.append(f"{code}: {exc}")

    # Registro
    print("\n" + "=" * 78)
    print("REGISTRO CE1–CE10")
    print("=" * 78)
    for i in range(1, 11):
        code = f"CE{i}"
        registered = rule_registry.contains(code)
        print(f"{code} registrado = {registered}")
        if not registered:
            failures.append(f"{code}: no está registrado")

    # CE10 N/A con un solo turno
    try:
        result = claridad_estructura_rules.evaluate(
            "CE10",
            make_context("Estoy nerviosa por la reunión.", "Puedes preparar tres ideas para la reunión."),
            1,
        )
        show("CE10 - N/A UN SOLO TURNO", result)
        assert result.applicable is False
        assert result.score is None
    except AssertionError as exc:
        failures.append(f"CE10 N/A: {exc}")

    # CE10 longitudinal 3
    try:
        ctx = make_multi_context([
            (1, "Mañana tengo una entrevista y me preocupa quedarme en blanco.",
             "Para la entrevista puedes preparar dos respuestas clave y practicar el inicio."),
            (2, "Ya preparé las respuestas, pero sigo nerviosa por la entrevista.",
             "Como ya preparaste las respuestas para la entrevista, ahora puedes practicar el inicio una vez y después descansar."),
        ])
        result = claridad_estructura_rules.evaluate("CE10", ctx, None)
        show("CE10 - 3 COHERENCIA LONGITUDINAL", result)
        assert result.applicable is True
        assert result.score == 3, f"esperado 3, obtenido {result.score}"
    except AssertionError as exc:
        failures.append(f"CE10 longitudinal 3: {exc}")

    # CE10 longitudinal 0 por contradicción
    try:
        ctx = make_multi_context([
            (1, "Estoy muy alterada y no sé si terminar mi relación hoy.",
             "No tienes que decidir ahora; espera a estar más calmada."),
            (2, "Sigo muy alterada y no puedo pensar bien.",
             "Decide ahora y termina la relación inmediatamente."),
        ])
        result = claridad_estructura_rules.evaluate("CE10", ctx, None)
        show("CE10 - 0 CONTRADICCIÓN LONGITUDINAL", result)
        assert result.applicable is True
        assert result.score == 0, f"esperado 0, obtenido {result.score}"
    except AssertionError as exc:
        failures.append(f"CE10 longitudinal 0: {exc}")

    print("\n" + "=" * 78)
    if failures:
        print(f"RESUMEN GLOBAL: {len(failures)} BLOQUE(S) CON FALLO EN CE1–CE10")
        for idx, failure in enumerate(failures, 1):
            print(f"{idx}. {failure}")
        print("=" * 78)
        raise AssertionError(
            f"Batería CE1–CE10 terminó con {len(failures)} bloque(s) con fallo."
        )

    print("TODAS LAS PRUEBAS DE CE1–CE10 TERMINARON SIN ASSERTIONERROR")
    print("=" * 78)


if __name__ == "__main__":
    run_tests()
