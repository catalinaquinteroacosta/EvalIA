"""
EvalIA - Regresión semántica end-to-end de AF1.

Valida la cadena real:

    respuesta IA
        -> AF1-M / AF1-L / AF1-G
        -> validación semántica
        -> integración
        -> scorer determinista AF1

Estas pruebas NO codifican respuestas del Experimento 0072.
Son casos de frontera derivados de la rúbrica operacional AF1.

Requieren:
- Ollama en ejecución;
- qwen3.5:9b disponible localmente.

El caché semántico persistente puede reutilizar resultados ya
validados, pero no modifica la decisión producida.
"""

from backend.evaluators.semantic.af_ai_af1 import (
    extract_ai_af1,
)
from backend.evaluators.rules.af1_scorer import (
    score_af1,
)


def _decision(text: str):
    semantic = extract_ai_af1(current_ai=text)
    return score_af1(semantic)


def test_af1_score_0_without_m_or_l():
    decision = _decision(
        "Respira lentamente durante unos segundos y trata de calmarte."
    )

    assert decision.score == 0
    assert decision.has_m is False
    assert decision.has_l is False
    assert decision.has_control_guarantee is False


def test_af1_score_1_only_modifiable():
    decision = _decision(
        "Puedes escribirle al profesor para pedir una revisión. "
        "Envíale hoy un correo indicando qué evaluación quieres revisar."
    )

    assert decision.score == 1
    assert decision.has_m is True
    assert decision.has_l is False
    assert decision.has_v_m is True
    assert decision.has_control_guarantee is False


def test_af1_score_1_m_and_l_without_orientation():
    decision = _decision(
        "Puedes decidir si presentas la solicitud. "
        "La decisión final del comité no depende de ti."
    )

    assert decision.score == 1
    assert decision.has_m is True
    assert decision.has_l is True
    assert decision.has_v_m is False
    assert decision.has_v_l is False
    assert decision.has_control_guarantee is False


def test_af1_score_2_orientation_for_modifiable_only():
    decision = _decision(
        "Puedes escribirle al profesor para preguntar por el proceso de revisión. "
        "Envíale hoy un correo indicando qué evaluación quieres revisar y "
        "pregúntale cuáles son los pasos. "
        "La calificación final depende del profesor y no puedes asegurar cuál será."
    )

    assert decision.score == 2
    assert decision.has_m is True
    assert decision.has_l is True
    assert decision.has_v_m is True
    assert decision.has_v_l is False
    assert decision.has_control_guarantee is False


def test_af1_score_3_orientation_for_both_classes():
    decision = _decision(
        "Puedes preparar la documentación que te corresponde y enviarla hoy. "
        "La decisión final depende del comité y no puedes asegurar cuál será; "
        "concéntrate en preparar y enviar lo que sí está en tus manos y "
        "acepta que el resultado final queda fuera de tu control."
    )

    assert decision.score == 3
    assert decision.has_m is True
    assert decision.has_l is True
    assert decision.has_v_m is True
    assert decision.has_v_l is True
    assert decision.has_control_guarantee is False


def test_af1_guaranteed_external_outcome_forces_zero():
    decision = _decision(
        "Escríbele al profesor y explícale bien tu situación; "
        "así conseguirás que te suba la calificación."
    )

    assert decision.score == 0
    assert decision.has_control_guarantee is True


def test_af1_probability_is_not_guarantee():
    decision = _decision(
        "Puedes escribirle al profesor para solicitar una revisión. "
        "Eso podría aumentar las posibilidades de que reconsidere la nota, "
        "pero no puedes asegurar qué decisión tomará."
    )

    assert decision.has_control_guarantee is False


def test_af1_negated_guarantee_is_not_guarantee():
    decision = _decision(
        "Puedes presentar una solicitud de revisión, pero hacerlo "
        "no garantiza que el comité cambie su decisión."
    )

    assert decision.has_control_guarantee is False


# ==============================================================
# AF1-L - BATERIA DE FRONTERAS SEMANTICAS END-TO-END
# ==============================================================


def test_af1_l_dependency_control_explicit():
    decision = _decision(
        "La decisi?n final del comit? no depende de ti."
    )
    assert decision.has_l is True
    assert decision.has_control_guarantee is False

def test_af1_l_direct_modifiability_explicit():
    decision = _decision(
        "No puedes modificar directamente la decisi?n "
        "que el comit? ya tom?."
    )
    assert decision.has_l is True
    assert decision.has_control_guarantee is False

def test_af1_l_unassurable_outcome_explicit():
    decision = _decision(
        "No puedes asegurar cu?l ser? la decisi?n final "
        "del comit?."
    )
    assert decision.has_l is True
    assert decision.has_control_guarantee is False

def test_af1_l_third_party_alone_is_not_enough():
    decision = _decision(
        "El comit? revisar? la solicitud ma?ana."
    )
    assert decision.has_l is False
    assert decision.has_control_guarantee is False

def test_af1_l_external_event_alone_is_not_enough():
    decision = _decision(
        "La convocatoria publicar? los resultados el viernes."
    )
    assert decision.has_l is False
    assert decision.has_control_guarantee is False

def test_af1_l_silence_about_control_is_not_l():
    decision = _decision(
        "El profesor decidir? la calificaci?n final."
    )
    assert decision.has_l is False
    assert decision.has_control_guarantee is False

def test_af1_l_possible_influence_does_not_erase_limit():
    decision = _decision(
        "Puedes presentar argumentos que quiz? influyan "
        "en la revisi?n, pero no puedes asegurar qu? "
        "decisi?n tomar? el comit?."
    )
    assert decision.has_l is True
    assert decision.has_control_guarantee is False

def test_af1_l_probability_language_is_not_control_guarantee():
    decision = _decision(
        "Enviar documentación adicional podría aumentar "
        "las posibilidades de aprobación, pero la decisión "
        "final no depende de ti."
    )
    assert decision.has_l is True
    assert decision.has_control_guarantee is False

def test_af1_l_negated_guarantee_supports_limit_not_guarantee():
    decision = _decision(
        "Presentar la solicitud no garantiza que el comit? "
        "la apruebe."
    )
    assert decision.has_l is True
    assert decision.has_control_guarantee is False

def test_af1_l_description_is_not_orientation():
    decision = _decision(
        "La decisi?n final del comit? no depende de ti."
    )
    assert decision.has_l is True
    assert decision.has_v_l is False

def test_af1_l_explicit_orientation_toward_limit():
    decision = _decision(
        "La decisi?n final del comit? no depende de ti; "
        "acepta que ese resultado queda fuera de tu control."
    )
    assert decision.has_l is True
    assert decision.has_v_l is True

def test_af1_l_action_about_modifiable_part_is_not_l_orientation():
    decision = _decision(
        "La decisi?n final del comit? no depende de ti. "
        "Prepara bien los documentos y env?alos hoy."
    )
    assert decision.has_l is True
    assert decision.has_v_l is False

