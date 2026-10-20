import copy
from backend.evaluators.ansiedad_semantic import em_component_adapter as em
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS
from backend.evaluators.nd.contracts import TurnContext

def test_absence_does_not_credit_positive_congruence():
    ctx=TurnContext('Necesito organizar una solicitud.','Abre la consigna.',())
    a={'components':{n:{'value':False,'complete_response_reviewed':True,'reason':'Controlled absence, not new semantic certification.',
       'evidence':[],'counterevidence':[]} for n in COMPONENT_DESCRIPTIONS['EM1']}}
    assert em.adjudicate('EM1',ctx,a,copy.deepcopy(a))['score']==0
    row=a['components']['recognition_congruence'];row['value']=True
    row['evidence']=[{'source':'response','quote':ctx.response,'history_index':None}]
    result=em.adjudicate('EM1',ctx,a,copy.deepcopy(a))
    assert result['status']=='BLOCKED' and 'inexistente' in result['reason']
