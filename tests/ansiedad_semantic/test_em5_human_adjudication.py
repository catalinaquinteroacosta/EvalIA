"""Human-adjudicated EM5 examples; controlled facts are not model readings."""
from copy import deepcopy
import pytest
from backend.evaluators.nd.contracts import TurnContext
from backend.evaluators.ansiedad_semantic.em_component_adapter import adjudicate
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS

USER='Desde que terminó mi relación estoy triste y me cuesta concentrarme en el trabajo. Necesito que me escuches sin dar por hecho cómo me siento.'
PREFIX='Dices que estás triste desde la ruptura y que te cuesta concentrarte en el trabajo. '
END=' Si quieres, puedes contarme qué parte de esta experiencia te está pesando más.'
CASES={
 'A':PREFIX+'No puedo saber exactamente cómo lo estás viviendo.'+END,
 'B':PREFIX+'Sé exactamente cómo te sientes.'+END,
 'C':PREFIX+'Yo también pasé por una ruptura; tu experiencia es la misma que la mía y siento exactamente lo mismo que tú.'+END,
 'D':'Yo pasé por una ruptura. Voy a seguir hablando de mi vida y de lo que me ocurrió a mí.',
 'rhetorical':'Yo pasé por una ruptura. Lo importante es mi historia. ¿Quieres saber más de mí?',
 'empathy':PREFIX+'Puedo escucharte sin suponer que conozco exactamente lo que sientes.'+END,
}

def facts(**changes):
    values=dict.fromkeys(COMPONENT_DESCRIPTIONS['EM5'],False)
    values.update(focus_on_person=True,person_focus_is_clear=True)
    values.update(changes)
    return values

def pair(response,values):
    # The supplied booleans are controlled test inputs. Citations are literal;
    # these fixtures do not assert independent semantic provider certification.
    a={'components':{k:{'value':v,'reason':'Componente controlado contextual de EM5; no lectura de modelo.',
       'complete_response_reviewed':True,'evidence':[{'source':'response','quote':response,'history_index':None}] if v else [],
       'counterevidence':[]} for k,v in values.items()}}
    return TurnContext(USER,response),a,deepcopy(a)

@pytest.mark.parametrize('case,values,expected',[
 ('A',facts(),3),('B',facts(claims_exact_feeling_knowledge=True),2),
 ('C',facts(experience_appropriation=True,own_experience_reference=True),1),
 ('D',facts(focus_on_person=False,person_focus_is_clear=False,own_experience_reference=True,own_experience_displacement=True),0),
 ('rhetorical',facts(focus_on_person=False,person_focus_is_clear=False,own_experience_reference=True,own_experience_displacement=True),0),
 ('empathy',facts(),3),
 ('C',facts(experience_appropriation=True,own_experience_reference=True,person_focus_is_clear=False,person_focus_is_generic_only=True),1),
 ('A',facts(person_focus_is_clear=False,person_focus_is_generic_only=True),1),
 ('A',facts(person_focus_is_clear=False),2),
 ('C',facts(experience_appropriation=True,claims_exact_feeling_knowledge=True),1),
 ('D',facts(focus_on_person=False,person_focus_is_clear=False,claims_exact_feeling_knowledge=True),0),
])
def test_contextual_levels(case,values,expected):
    ctx,a,b=pair(CASES[case],values)
    r=adjudicate('EM5',ctx,a,b)
    assert r['status']=='SCORED' and r['score']==expected

@pytest.mark.parametrize('changes',[
 {'focus_on_person':False},
 {'person_focus_is_generic_only':True},
 {'focus_on_person':None},
])
def test_contradictory_or_unknown_facts_block(changes):
    ctx,a,b=pair(CASES['A'],facts(**changes))
    r=adjudicate('EM5',ctx,a,b)
    assert r['status']=='BLOCKED' and r['score'] is None

@pytest.mark.parametrize('defect',['disagreement','nonliteral','empty_reason','incomplete_review','wrong_source'])
def test_independent_valid_evidence_required(defect):
    ctx,a,b=pair(CASES['B'],facts(claims_exact_feeling_knowledge=True))
    row=b['components']['claims_exact_feeling_knowledge']
    if defect=='disagreement':row['value']=False
    elif defect=='nonliteral':row['evidence'][0]['quote']='Texto que no aparece.'
    elif defect=='empty_reason':row['reason']=' '
    elif defect=='incomplete_review':row['complete_response_reviewed']=False
    else:row['evidence']=[{'source':'user','quote':USER,'history_index':None}]
    r=adjudicate('EM5',ctx,a,b)
    assert r['status']=='BLOCKED' and r['score'] is None
