"""Canonical export must preserve review evidence, nulls and real zero."""
import json
from copy import deepcopy
from backend import main

def test_json_download_preserves_canonical_review_and_zero(monkeypatch):
    payload={'experiment':{'id':999},'results':[
        {'code':'A','status':'SCORED','score':0},
        {'code':'B','status':'N/A','score':None},
        {'code':'C','status':'BLOCKED','score':None,'review_id':7,
         'evidence':[{'quote':'¿Qué ocurrió?','source':'response'}],
         'counterevidence':[{'quote':'No lo sé','source':'user'}]}]}
    original=deepcopy(payload)
    monkeypatch.setattr(main,'get_experiment_results',lambda experiment_id:payload)
    response=main.export_experiment_json(999)
    assert response.status_code==200
    assert json.loads(response.body)==original and payload==original
    assert response.headers['content-disposition']=='attachment; filename="EvalIA_experimento_0999.json"'
