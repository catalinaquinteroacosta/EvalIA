import json
import pytest
from backend.evaluators.ansiedad_semantic import budgeted_reader as module

REQUEST={'stage':'extract','indicators':{'IR1':{'components':{'thought_identified':'Pensamiento identificado'}}},
         'original':{'input_sha256':'fixture','user':'texto','response':'texto','prior_history':[]}}

def authorization(**changes):
    result={'explicit_user_approval':True,'authorization_id':'TEST-ONLY-NO-REAL-AUTHORIZATION',
        'additional_cap_usd':'1','extraction_model':'gpt-4.1-mini-2025-04-14',
        'verification_model':'gpt-4.1-2025-04-14'}
    result.update(changes);return result

def completed(body):
    reading={'indicators':{'IR1':{'components':{'thought_identified':{
        'value':False,'evidence':[],'counterevidence':[],
        'complete_response_reviewed':True,'reason':'offline fixture'}}}}}
    return {'model':body['model'],'usage':{'prompt_tokens':100,'completion_tokens':100},
            'choices':[{'finish_reason':'stop','message':{'content':json.dumps(reading)}}]}

def test_not_authorized_never_opens_transport():
    with pytest.raises(PermissionError):module.Reader({'explicit_user_approval':False})

def test_unknown_billing_retains_reservation_and_no_automatic_retry(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    calls=[]
    def fail(body):calls.append(body);raise OSError('uncertain billing')
    reserve=module.estimate(REQUEST,'gpt-4.1-mini-2025-04-14')['reserved_upper_bound_usd']
    reader=module.Reader(authorization(additional_cap_usd=reserve),transport=fail)
    with pytest.raises(OSError):reader(REQUEST)
    with pytest.raises(PermissionError):reader(REQUEST)
    assert len(calls)==1
    events=reader._events()
    assert [e['kind'] for e in events]==['reserved','failure']

def test_completed_private_identity_reuses_without_call(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    calls=[]
    def fake(body):calls.append(body);return completed(body)
    reader=module.Reader(authorization(),transport=fake)
    assert reader(REQUEST)==reader(REQUEST)
    assert len(calls)==1
    changed={**REQUEST,'stage':'independent_verify'}
    reader(changed)
    assert len(calls)==2 and calls[-1]['model']=='gpt-4.1-2025-04-14'

def test_incomplete_output_is_not_reused_as_verified(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    def fake(body):
        row=completed(body);row['choices'][0]['finish_reason']='length';return row
    reader=module.Reader(authorization(),transport=fake)
    with pytest.raises(ValueError):reader(REQUEST)
    assert not [e for e in reader._events() if e['kind']=='settled'][0]['valid_output']

def test_existing_outstanding_reserve_counts_before_send(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path)
    def forbidden(_):raise AssertionError('must not send')
    reader=module.Reader(authorization(outstanding_reservations_usd='1'),transport=forbidden)
    with pytest.raises(PermissionError):reader(REQUEST)
    assert not (tmp_path/'ledger.jsonl').exists()
