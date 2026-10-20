import json
from decimal import Decimal
import pytest
from backend.evaluators.ansiedad_semantic import night_validation as night,budgeted_reader as budget

def test_uncertain_commitment_above_cash_ceiling_has_no_available_balance(tmp_path,monkeypatch):
    events=[{'kind':'reserved','attempt':1,'authorization':'cash','reserved_usd':'0.4'},
            {'kind':'reserved','attempt':2,'authorization':'cash','reserved_usd':'0.5'},
            {'kind':'settled','attempt':1,'actual_usd':'0.3'}]
    (tmp_path/'ledger.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n',encoding='utf-8')
    monkeypatch.setattr(night,'ROOT',tmp_path)
    monkeypatch.setattr(night,'AUTH',{'authorization_id':'cash','additional_cap_usd':'0.6'})
    state=night.accounting()
    assert Decimal(state['committed_usd'])==Decimal('0.8')
    assert Decimal(state['available_usd'])==0
    assert Decimal(state['reserve_shortfall_usd'])==Decimal('0.2')

def test_existing_uncertain_reservation_blocks_transport_after_lower_balance(tmp_path,monkeypatch):
    (tmp_path/'ledger.jsonl').write_text(json.dumps({'kind':'reserved','attempt':1,'authorization':'cash','reserved_usd':'1'})+'\n',encoding='utf-8')
    monkeypatch.setattr(budget,'ROOT',tmp_path)
    calls=[]
    reader=budget.Reader({'explicit_user_approval':True,'authorization_id':'cash','additional_cap_usd':'0.5',
        'extraction_model':'gpt-4.1-mini-2025-04-14','verification_model':'gpt-4.1-2025-04-14'},transport=lambda q:calls.append(q))
    request={'stage':'extract','indicators':{'PA1':{'components':{'action':'Actual action'}}}}
    with pytest.raises(PermissionError,match='reservas inciertas'):reader(request)
    assert calls==[]
