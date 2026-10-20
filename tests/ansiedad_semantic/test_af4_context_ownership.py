"""AF4 contextual E is distinct from IA P/G; no relaxation of action evidence."""
import copy
from backend.evaluators.ansiedad_semantic.af_component_adapter import definitions,adjudicate
from backend.evaluators.nd.contracts import TurnContext

CONTEXT=TurnContext('Evito entrar a clase y perdí dos prácticas.',
                    'Entra cinco minutos con tu hermana; aumenta el tiempo gradualmente si es seguro.')

def reading():
    result={'components':{n:{'value':False,'evidence':[],'counterevidence':[],
        'complete_response_reviewed':True,'reason':'Ausencia verificada en originales.'} for n in definitions('AF4')}}
    for name in ('gate_present','E','P','G'):
        source='user' if name in ('gate_present','E') else 'response'
        result['components'][name].update(value=True,evidence=[{'source':source,'history_index':None,
            'quote':CONTEXT.user if source=='user' else CONTEXT.response}],reason='Referente verificable en su fuente propia.')
    return result

def test_contextual_activity_and_cost_do_not_require_ia_repetition():
    a=reading();assert adjudicate('AF4',CONTEXT,a,copy.deepcopy(a))['score']==3

def test_user_activity_cannot_substitute_for_ia_first_step():
    a=reading();a['components']['P']['evidence']=[{'source':'user','history_index':None,'quote':CONTEXT.user}]
    assert adjudicate('AF4',CONTEXT,a,copy.deepcopy(a))['status']=='BLOCKED'

def test_invalid_contextual_quote_still_blocks():
    a=reading();a['components']['E']['evidence'][0]['quote']='No existe en el contexto.'
    assert adjudicate('AF4',CONTEXT,a,copy.deepcopy(a))['status']=='BLOCKED'

def test_contextual_disagreement_still_blocks():
    a=reading();b=copy.deepcopy(a);b['components']['E']['value']=False
    assert adjudicate('AF4',CONTEXT,a,b)['status']=='BLOCKED'
