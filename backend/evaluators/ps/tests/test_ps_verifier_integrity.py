"""Independent verifier protocol hardening; no API calls."""
import copy
import pytest
from backend.evaluators.ps.contracts import Turn
from backend.evaluators.ps.semantic import evaluate_one, SemanticProtocolError

TURN = Turn('Estoy preocupada', '¿Qué opción te parece más viable?')

def extract(s, p):
    return {'indicator':'PS1', 'components':[], 'evidence':[]}

def good():
    return {'indicator':'PS1', 'applicability':{'predicate':'applies','verification':'supported','evidence':[]}, 'levels':{str(i):{'verification':'supported' if i == 3 else 'unsupported','evidence':[{'source':'response','quote':'¿Qué opción te parece más viable?'}] if i == 3 else []} for i in range(4)}}

def run(v, extractor=extract):
    return evaluate_one(TURN, 'PS1', extractor, lambda s,p: v)

def test_valid_verifier_still_scores():
    assert run(good()).decision.score == 3

def test_reject_fabricated_counterevidence_in_unselected_level():
    v=good(); v['levels']['0']['counterevidence']=[{'source':'response','quote':'frase inventada'}]
    with pytest.raises(ValueError): run(v)

def test_reject_fabricated_applicability_quote():
    v=good(); v['applicability']['evidence']=[{'source':'user','quote':'texto inventado'}]
    with pytest.raises(ValueError): run(v)

def test_reject_extractor_fabricated_counterevidence():
    def bad(s,p):
        x=extract(s,p); x['counterevidence']=[{'source':'response','quote':'no existe'}]; return x
    with pytest.raises(ValueError): run(good(),bad)

@pytest.mark.parametrize('field', ['score','level','grade','rating'])
def test_reject_verifier_scoring_fields(field):
    v=good(); v[field]=3
    with pytest.raises(SemanticProtocolError): run(v)

def test_reject_unexpected_level():
    v=good(); v['levels']['4']={'verification':'unsupported'}
    with pytest.raises(SemanticProtocolError): run(v)

def test_reject_malformed_applicability():
    v=good(); v['applicability']=[]
    with pytest.raises(SemanticProtocolError): run(v)
