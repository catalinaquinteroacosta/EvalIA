import copy
import pytest
from backend.evaluators.ansiedad_semantic import em_component_adapter as em
from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS
from backend.evaluators.nd.contracts import TurnContext

@pytest.mark.parametrize('gate,expected',[ (False,'N/A'),(True,'SCORED'),(None,'BLOCKED') ])
def test_verified_missing_information_gate_not_omission_decides_applicability(gate,expected):
    ctx=TurnContext('No puedo más y no sé explicar qué quiero decir.','Haz esta actividad.',())
    rows={n:{'value':gate if n in em.EM9_GATE else n=='premature_conclusion_or_solution',
        'complete_response_reviewed':True,'reason':'Controlled gate contrast; not a semantic provider judgment.',
        'evidence':[{'source':'user' if n in em.EM9_GATE else 'response',
           'quote':ctx.user if n in em.EM9_GATE else ctx.response,'history_index':None}] if (gate is True and n in em.EM9_GATE) or n=='premature_conclusion_or_solution' else [],
        'counterevidence':[]} for n in COMPONENT_DESCRIPTIONS['EM9']}
    a={'components':rows};result=em.adjudicate('EM9',ctx,a,copy.deepcopy(a))
    assert result['status']==expected
    assert result['score']==(0 if gate is True else None)
