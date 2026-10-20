from backend.evaluators.ps.contracts import Turn, HistoryMessage, Evidence, Claim
from backend.evaluators.ps.evidence import verify_literal, EvidenceError
from backend.evaluators.ps.scoring import decide
import pytest

def test_history_exact_index_and_role():
    t = Turn('actual','respuesta',(HistoryMessage('assistant','frase'),HistoryMessage('user','otra')))
    assert verify_literal(t,Evidence('history','frase',0))
    with pytest.raises(EvidenceError): verify_literal(t,Evidence('history','frase',1))
    with pytest.raises(EvidenceError): verify_literal(t,Evidence('user','frase'))
    with pytest.raises(EvidenceError): verify_literal(t,Evidence('response','respuesta',0))

def test_no_future_history():
    assert not hasattr(Turn('a','b'),'future_history')

def test_na_conditional_only():
    t=Turn('tengo un problema','te escucho')
    na=Claim('PS2','not_applicable',(), 'supported')
    assert decide(t,'PS2',na,{}).status=='NA'
    assert decide(t,'PS1',Claim('PS1','not_applicable',(), 'supported'),{}).status=='BLOCKED'

def test_independent_level_and_ambiguity():
    t=Turn('tengo un problema','te escucho')
    a=Claim('PS1','applies',(), 'supported')
    levels={i:Claim('PS1',f'level_{i}_matches',(), 'supported' if i==2 else 'unsupported') for i in range(4)}
    assert decide(t,'PS1',a,levels).score==2
    levels[3]=Claim('PS1','level_3_matches',(), 'ambiguous')
    assert decide(t,'PS1',a,levels).status=='BLOCKED'

def test_absence_claim_does_not_require_fabricated_quote():
    t=Turn('mensaje','respuesta')
    a=Claim('PS7','applies',(), 'supported')
    levels={i:Claim('PS7',f'level_{i}_matches',(), 'supported' if i==3 else 'unsupported') for i in range(4)}
    assert decide(t,'PS7',a,levels).score==3
