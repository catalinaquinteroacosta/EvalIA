"""Request JSON text has stable official focus order before hashing/sealing."""
import json
import pytest
from backend import luna_reader as reader

def test_official_focus_order_is_sorted_before_json_text(monkeypatch):
    monkeypatch.setattr(reader,'spans',lambda context: {})
    monkeypatch.setattr(reader,'schema',lambda definitions,library: {})
    monkeypatch.setattr(reader,'adapt_body',lambda body,*args: body)
    bodies=[]
    def capture(body,endpoint):
        bodies.append(body)
        raise RuntimeError('offline capture only')
    provider=reader.LunaProvider(capture)
    codes=['CR-RI2','CR-CE10']
    for order in (codes,list(reversed(codes))):
        content={'conversation':{'current_turn':1,'current_user':'user','current_ai':'answer','model_evaluated':'test','history':[]},'predicates':{str(i):{'code':code} for i,code in enumerate(order)}}
        with pytest.raises(reader.ProviderBlocked):provider.run('extract','',content,None,[],None)
        payload=json.loads(bodies[-1]['input'][1]['content'])
        assert list(payload['official_focus'])==sorted(codes)
