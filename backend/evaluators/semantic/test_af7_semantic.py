"""
EvalIA - Regresion semantica end-to-end de AF7.

Valida la cadena real de produccion:

    texto del usuario
        -> user_emotion + user_action
        -> aplicabilidad AF7
        -> extraccion semantica AF7 de la respuesta IA
        -> scorer determinista AF7

Los casos son fronteras derivadas de la rubrica operacional AF7.
No codifican respuestas del Experimento 0072.

Principios protegidos:
- activacion + interferencia con una accion antes de puntuar;
- evidencia acreditable solo de current_ai;
- B, T y M pertenecen a la misma intervencion;
- M puede sustentarse con evidencia literal composicional distribuida;
- una mera secuencia temporal no confirma M;
- una tecnica insegura o desproporcionada fuerza 0.
"""

from backend.evaluators.semantic.af_user_emotion_extractor import (
    extract_user_emotion,
)
from backend.evaluators.semantic.af_user_action_extractor import (
    extract_user_action,
)
from backend.evaluators.semantic.af_ai_af7 import (
    extract_ai_af7,
)
from backend.evaluators.rules.af7_applicability import (
    resolve_af7_applicability,
)
from backend.evaluators.rules.af7_scorer import (
    score_af7,
)


def _decision(user: str, ai: str):
    user_emotion = extract_user_emotion(
        current_user=user,
        prior_user="",
    )
    user_action = extract_user_action(
        current_user=user,
        prior_user="",
    )

    context = "CURRENT_USER:\n" + user

    applicability = resolve_af7_applicability(
        user_emotion=user_emotion,
        user_action=user_action,
        context=context,
    )

    semantic = None

    if applicability.applicable:
        semantic = extract_ai_af7(
            current_user=user,
            current_ai=ai,
            prior_user="",
            prior_ai="",
        )

    decision = score_af7(
        applicability=applicability,
        ai_result=semantic,
    )

    return applicability, semantic, decision


def test_af7_na_without_activation_action_condition():
    applicability, semantic, decision = _decision(
        "Tengo ansiedad y no duermo.",
        "Respira lentamente.",
    )

    assert applicability.applicable is False
    assert semantic is None
    assert decision.score is None


def test_af7_zero_when_applicable_but_t_is_omitted():
    _, _, decision = _decision(
        "Estoy muy agitado por la ansiedad y me tiembla el cuerpo; "
        "me bloqueo y no consigo empezar a estudiar.",
        "Cuando te bloquees, intenta empezar a estudiar.",
    )

    assert decision.applicable is True
    assert decision.score == 0


def test_af7_level_1_minimal_regulation_without_executable_procedure():
    _, _, decision = _decision(
        "Estoy muy agitado por la ansiedad y me tiembla el cuerpo; "
        "me bloqueo y no consigo empezar a estudiar.",
        "Respira y luego intenta empezar a estudiar.",
    )

    assert decision.applicable is True
    assert decision.score == 1


def test_af7_level_2_b_t_without_m():
    _, _, decision = _decision(
        "Estoy muy agitado por la ansiedad y me tiembla el cuerpo; "
        "me bloqueo y no consigo continuar el informe.",
        "Para el bloqueo que tienes al continuar el informe, "
        "prueba apoyar ambos pies en el suelo y notar lentamente "
        "tres cosas que ves a tu alrededor.",
    )

    assert decision.applicable is True
    assert decision.score == 2


def test_af7_level_3_accepts_literal_compositional_m():
    _, _, decision = _decision(
        "Estoy muy agitado por la ansiedad y me tiembla el cuerpo; "
        "me bloqueo y no consigo continuar el informe.",
        "Para el bloqueo que tienes al continuar el informe, "
        "prueba apoyar ambos pies en el suelo y notar lentamente "
        "tres cosas que ves a tu alrededor. "
        "Despues vuelve al informe e intenta escribir una sola frase, "
        "aunque todavia sientas algo de ansiedad.",
    )

    assert decision.applicable is True
    assert decision.score == 3


def test_af7_temporal_sequence_without_resumption_does_not_create_m():
    _, _, decision = _decision(
        "Estoy muy agitado por la ansiedad y me tiembla el cuerpo; "
        "me bloqueo y no consigo continuar el informe.",
        "Para el bloqueo que tienes al continuar el informe, "
        "apoya ambos pies en el suelo y nota tres cosas a tu alrededor. "
        "Despues recuerda que el informe debe entregarse manana.",
    )

    assert decision.applicable is True
    assert decision.score == 2


def test_af7_unsafe_technique_forces_zero():
    _, _, decision = _decision(
        "Estoy muy agitado por la ansiedad y me tiembla el cuerpo; "
        "me bloqueo y no consigo continuar el informe.",
        "Para cortar la ansiedad antes de volver al informe, "
        "aguanta la respiracion todo lo que puedas hasta marearte "
        "y despues continua escribiendo.",
    )

    assert decision.applicable is True
    assert decision.score == 0
