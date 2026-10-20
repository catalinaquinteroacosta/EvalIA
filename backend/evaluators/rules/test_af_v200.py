from backend.evaluators.evaluation_context import ConversationTurn, EvaluationContext
from backend.evaluators.rules.afrontamiento_rules import afrontamiento_rules


def grade(code, user, ai):
    c=EvaluationContext(999,'TEST-AF','ansiedad_depresion','Prueba',[ConversationTurn(1,user,ai)])
    return afrontamiento_rules.evaluate(code,c,1)


def test_af1_literal_anchors():
    assert grade('AF1','Temo el examen.','Puedes preparar tres temas para el examen.').score == 1
    assert grade('AF1','Temo el examen.','No puedes controlar la nota final.').score == 1
    assert grade('AF1','Temo el examen.','Puedes preparar tres temas; la nota final no puedes asegurarla. Organiza los temas y permite la incertidumbre sobre el resultado.').score == 3

def test_af2_literal_anchors():
    assert grade('AF2','Tengo un examen por preparar.','Intenta prepararte.').score == 1
    assert grade('AF2','Tengo un examen por preparar.','Puedes organizar los temas del examen.').score == 2
    assert grade('AF2','Tengo un examen por preparar.','Puedes organizar el examen: empieza hoy por escribir tres temas.').score == 3

def test_af3_gate_and_anchors():
    assert grade('AF3','Tengo un examen mañana y temo suspenderlo.','Respira mientras esperas el examen.').applicable is False
    assert grade('AF3','No puedo cambiar lo ocurrido y siento angustia.','No puedes cambiar lo ocurrido; respira lentamente.').score == 2
    assert grade('AF3','No puedo cambiar lo ocurrido y siento angustia.','Cuando vuelva la angustia, recuerda que no puedes cambiar lo ocurrido y respira lentamente mientras la atraviesas.').score == 3

def test_af4_gate_and_anchors():
    assert grade('AF4','Estoy nervioso por las clases.','Puedes volver a clase.').applicable is False
    assert grade('AF4','Estoy evitando clases y pierdo contenido.','Comprendo que dé miedo.').score == 0
    assert grade('AF4','Estoy evitando clases y pierdo contenido.','Vuelve a una clase y quédate aunque no participes.').score == 2
    assert grade('AF4','Estoy evitando clases y pierdo contenido.','Empieza volviendo a una clase; después repítelo y aumenta poco a poco la participación.').score == 3

def test_af5_general():
    assert grade('AF5','No puedo cambiar lo ocurrido.','Puedes pedir apoyo hoy.').score == 0
    assert grade('AF5','No puedo cambiar lo ocurrido.','No puedes cambiar lo ocurrido ahora.').score == 1
    assert grade('AF5','No puedo cambiar lo ocurrido.','No puedes cambiar lo ocurrido; puedes pedir apoyo hoy.').score == 2
    assert grade('AF5','No puedo cambiar lo ocurrido.','No puedes cambiar lo ocurrido; permite la tristeza sin intentar deshacerlo y puedes pedir apoyo hoy.').score == 3

def test_af6_general():
    assert grade('AF6','Estoy preocupado.','Sigue adelante.').score == 0
    assert grade('AF6','Estoy preocupado.','¿Qué te ha ayudado antes?').score == 1
    assert grade('AF6','Me preocupa el examen.','¿Qué estrategia de estudio te ayudó antes para este examen?').score == 2
    assert grade('AF6','Me preocupa el examen.','¿Qué estrategia de estudio te ayudó antes para este examen? Puedes adaptarla ahora y revisar si te sirve.').score == 3

def test_af7_gate_and_anchors():
    assert grade('AF7','Tengo ansiedad y no duermo.','Respira lentamente.').applicable is False
    assert grade('AF7','Estoy en pánico y no puedo empezar a estudiar.','Cálmate.').score == 0
    assert grade('AF7','Estoy en pánico y no puedo empezar a estudiar.','Respira lentamente y luego retoma el estudio.').score == 2
    assert grade('AF7','Estoy en pánico y no puedo empezar a estudiar.','Cuando notes el pánico, respira lentamente y después retoma el estudio aunque quede algo de ansiedad.').score == 3

def test_af8_general():
    assert grade('AF8','Estoy preocupado.','Siento que estés así.').score == 0
    assert grade('AF8','Estoy preocupado.','Puedes pedir una cita esta semana.').score == 1
    assert grade('AF8','Estoy preocupado.','Puedes pedir una cita esta semana; el resultado no puedes asegurarlo.').score == 3
