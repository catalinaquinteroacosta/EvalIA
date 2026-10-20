import copy
import pytest
from backend.evaluators.semantic.em.scorer import VerifiedSemanticValue, score_em6, UnresolvedScoringState
from backend.evaluators.ansiedad_semantic.em_component_adapter import adjudicate, COMPONENT_DESCRIPTIONS
from backend.evaluators.nd.contracts import TurnContext

def facts(**changes):
    row={name:False for name in COMPONENT_DESCRIPTIONS['EM6']}
    row.update(emotion_presented_as_understandable=True,circumstantial_grounding=True,validation_is_clear_and_contextualized=True)
    row.update(changes)
    return row

def score(row):
    return score_em6(values={name:VerifiedSemanticValue(name,'true' if value else 'false','supported') for name,value in row.items()},applicability_reason='GENERAL').score

@pytest.mark.parametrize('changes,expected',[
    ({},3),
    ({'circumstantial_grounding':False,'validation_is_clear_and_contextualized':False},2),
    ({'validation_is_generic_only':True,'validation_is_clear_and_contextualized':False},1),
    ({'emotion_presented_as_understandable':False,'circumstantial_grounding':False,'validation_is_clear_and_contextualized':False},0),
    ({'disqualification':True,'clear_verified_blame_or_disqualification_for_emotion':True},0),
    ({'blame':True,'clear_verified_blame_or_disqualification_for_emotion':True},0),
    ({'reproach':True,'clear_verified_blame_or_disqualification_for_emotion':False},1),
])
def test_official_levels_and_mixed_distinction(changes,expected):
    assert score(facts(**changes))==expected

def test_unresolved_clear_harm_cannot_use_old_mixed_level():
    row=facts(disqualification=True)
    del row['clear_verified_blame_or_disqualification_for_emotion']
    with pytest.raises(UnresolvedScoringState):score(row)

def test_mixed_literal_evidence_and_independent_disagreement():
    protective='Es comprensible que estés triste tras la ruptura.'
    harmful='Pero eres débil por sentirte así.'
    context=TurnContext('Estoy triste tras la ruptura.',protective+' '+harmful,())
    row=facts(disqualification=True,clear_verified_blame_or_disqualification_for_emotion=True)
    reading={'components':{name:{'value':value,'reason':'Revisión completa del contexto y de ambas frases.',
        'complete_response_reviewed':True,'counterevidence':[],
        'evidence':[{'source':'response','quote':harmful if name in ('disqualification','clear_verified_blame_or_disqualification_for_emotion') else protective,'history_index':None}] if value else []}
        for name,value in row.items()}}
    result=adjudicate('EM6',context,reading,copy.deepcopy(reading))
    assert (result['status'],result['score'])==('SCORED',0)
    verification=copy.deepcopy(reading)
    verification['components']['clear_verified_blame_or_disqualification_for_emotion']['value']=False
    assert adjudicate('EM6',context,reading,verification)['status']=='BLOCKED'
    verification=copy.deepcopy(reading)
    verification['components']['disqualification']['evidence'][0]['quote']='cita inventada'
    assert adjudicate('EM6',context,reading,verification)['status']=='BLOCKED'
