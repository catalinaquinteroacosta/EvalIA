import pytest
from backend.evaluators.ce.ce_b.ce2_provider_bridge import extract_ce2_draft, SCHEMA

def test_bridge_mock_never_scores():
    calls=[]
    def fake(**kwargs):
        calls.append(kwargs)
        return dict(analysis_complete=False,full_response_audited=False,need_coverage='generic',
                    overload='none',secondary_defect=False,claims=[])
    out=extract_ce2_draft(user_text='Escúchame',response_text='Te escucho',semantic_runner=fake,
                          provider='openai',model='test-model')
    assert out['status']=='unverified_draft' and 'score' not in out
    assert calls[0]['schema']==SCHEMA
    assert 'Escúchame' in calls[0]['prompt']

def test_bridge_rejects_malformed_provider_output():
    with pytest.raises(ValueError):
        extract_ce2_draft(user_text='Hola',response_text='Hola',provider='openai',model='test-model',
                          semantic_runner=lambda **kw: {'score':3})

@pytest.mark.parametrize('user,response',[('', 'respuesta'),('usuario','')])
def test_bridge_rejects_missing_inputs(user,response):
    with pytest.raises(ValueError):
        extract_ce2_draft(user_text=user,response_text=response,
                          semantic_runner=lambda **kw: {})
