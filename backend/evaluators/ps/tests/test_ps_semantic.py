from backend.evaluators.ps.contracts import Turn
from backend.evaluators.ps.semantic import evaluate_one, evaluate_family
from backend.evaluators.ps.rubric import rubric_for

def test_all_indicators_have_reference():
    for n in range(1,11):
        r=rubric_for(f'PS{n}')
        assert r['question'] and r['requirement']

def test_na_only_when_verified():
    def extractor(s,p): return {'indicator':'PS2','evidence':[],'components':[]}
    def verifier(s,p): return {'indicator':'PS2','applicability':{'predicate':'not_applicable','verification':'supported','evidence':[]},'levels':{}}
    result=evaluate_one(Turn('Hola','Hola'), 'PS2',extractor,verifier)
    assert result.decision.status=='NA'

def test_unverified_not_scored():
    def extractor(s,p): return {'indicator':'PS2','evidence':[]}
    def verifier(s,p): return {'indicator':'PS2','applicability':{'predicate':'applies','verification':'ambiguous'},'levels':{}}
    assert evaluate_one(Turn('No estoy bien','¿Quieres hablar?'),'PS2',extractor,verifier).decision.status=='BLOCKED'

def test_extractor_cannot_score():
    def extractor(s,p): return {'indicator':'PS1','score':3}
    def verifier(s,p): raise AssertionError('Must never verify malformed extraction')
    import pytest
    with pytest.raises(ValueError): evaluate_one(Turn('Hola','Hola'),'PS1',extractor,verifier)

def test_fabricated_quote_fails():
    def extractor(s,p): return {'indicator':'PS1','evidence':[{'source':'response','quote':'NOT IN RESPONSE'}]}
    def verifier(s,p): raise AssertionError('Must never verify fabricated evidence')
    import pytest
    with pytest.raises(ValueError): evaluate_one(Turn('Hola','Hola'),'PS1',extractor,verifier)

def test_full_family_isolates_failures():
    def bad(s,p): raise ValueError('unavailable')
    r=evaluate_family(Turn('Hola','Hola'),bad,bad)
    assert len(r)==10 and all(x.decision.status=='BLOCKED' for x in r.values())
