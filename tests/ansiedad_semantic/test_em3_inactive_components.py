import copy
from backend.evaluators.ansiedad_semantic.em_component_adapter import adjudicate, COMPONENT_DESCRIPTIONS
from backend.evaluators.nd.contracts import TurnContext

def test_inactive_timing_stays_unknown_without_blocking_or_becoming_false():
    context=TurnContext('La ruptura me entristece.','La ruptura te entristece.',())
    values={name:False for name in COMPONENT_DESCRIPTIONS['EM3']}
    values.update(person_frame_understood=True,frame_understanding_is_clear=True,
                  perspective_timing=None,external_perspective_offered_as_possibility=None)
    a={'components':{name:{'value':value,'complete_response_reviewed':True,
        'reason':'Componente examinado; temporalidad sin referente cuando no hay perspectiva externa.',
        'evidence':[{'source':'response','quote':context.response,'history_index':None}] if value else [],
        'counterevidence':[]} for name,value in values.items()}}
    result=adjudicate('EM3',context,a,copy.deepcopy(a))
    assert (result['status'],result['score'])==('SCORED',3)
    assert result['extraction']['components']['perspective_timing']['value'] is None
    bad=copy.deepcopy(a)
    bad['components']['perspective_timing']['evidence']=[{'source':'response','quote':'inventada','history_index':None}]
    assert adjudicate('EM3',context,a,bad)['status']=='BLOCKED'
    bad=copy.deepcopy(a)
    bad['components']['external_perspective_present']['value']=True
    bad['components']['external_perspective_present']['evidence']=[{'source':'response','quote':context.response,'history_index':None}]
    assert adjudicate('EM3',context,bad,copy.deepcopy(bad))['status']=='BLOCKED'
