from decimal import Decimal
from pathlib import Path
import os
import subprocess
import sys
import pytest
from backend.luna_budget import BudgetJournal,BudgetBlocked

def auth(manifest='a'*64,cap='2',n=10):
    return dict(explicit_user_approval=True,sealed_manifest_sha256=manifest,scope='sealed pilot only',allow_definitive_950=False,max_usd=cap,max_requests=n)

def reserve(journal,run='pilot',manifest='a'*64,amount='2',n=10):
    return journal.reserve(run,manifest,reservation_usd=amount,requests=n,authorization=auth(manifest,amount,n),scope='sealed pilot only')

def journal(tmp_path,prior='0'):
    j=BudgetJournal(tmp_path/'budget.json');j.initialize(prior_spent_usd=prior,prior_evidence='known usage receipt sha256');return j

def test_restarts_preserve_uncertain_money_and_do_not_reset(tmp_path):
    j=journal(tmp_path,'97');reserve(j);j.mark_uncertain('pilot',reason='POST response lost')
    again=BudgetJournal(j.path)
    assert again.snapshot()['available_usd']=='1'
    assert again.snapshot()['pending_requests']==10
    with pytest.raises(BudgetBlocked):again.initialize(prior_spent_usd='0',prior_evidence='reset')
    with pytest.raises(BudgetBlocked):again.settle('pilot',actual_usd='.1',actual_requests=1,usage_evidence='partial output')
    assert again.snapshot()['reserved_usd']=='2'

def test_reservation_and_settlement_are_idempotent_but_mismatch_blocks(tmp_path):
    j=journal(tmp_path);first=reserve(j);assert reserve(j)==first
    with pytest.raises(BudgetBlocked):reserve(j,amount='3')
    with pytest.raises(BudgetBlocked):reserve(j,run='duplicate')
    result=j.settle('pilot',actual_usd='0.123456789',actual_requests=10,usage_evidence='complete batch usage',fully_reconciled=True)
    assert result['spent_usd']=='0.123456789' and result['reserved_usd']=='0'
    assert j.settle('pilot',actual_usd='0.123456789',actual_requests=10,usage_evidence='complete batch usage',fully_reconciled=True)==result
    with pytest.raises(BudgetBlocked):j.settle('pilot',actual_usd='.12',actual_requests=10,usage_evidence='different',fully_reconciled=True)

def test_overrun_records_true_cost_and_blocks_future_spending(tmp_path):
    j=journal(tmp_path,'98');reserve(j,amount='1')
    with pytest.raises(BudgetBlocked):j.settle('pilot',actual_usd='2.5',actual_requests=11,usage_evidence='all original outputs',fully_reconciled=True)
    snapshot=BudgetJournal(j.path).snapshot()
    assert snapshot['spent_usd']=='100.5' and snapshot['available_usd']=='-0.5' and snapshot['blocked']
    with pytest.raises(BudgetBlocked):reserve(j,run='next',manifest='b'*64,amount='.01')

@pytest.mark.parametrize('value',['NaN','Infinity','-1',True])
def test_invalid_money_rejected_without_spend(tmp_path,value):
    j=journal(tmp_path)
    with pytest.raises(ValueError):reserve(j,amount=value)
    assert j.snapshot()['reserved_usd']=='0'

def test_balance_is_not_authorization_and_definitive950_disabled(tmp_path):
    j=journal(tmp_path);a=auth();a['explicit_user_approval']=False
    with pytest.raises(BudgetBlocked):j.reserve('x','a'*64,reservation_usd=1,requests=1,authorization=a,scope=a['scope'])
    with pytest.raises(BudgetBlocked):j.reserve('x','a'*64,reservation_usd=1,requests=1,authorization=auth(),scope='different')
    with pytest.raises(BudgetBlocked):j.reserve('x','a'*64,reservation_usd=1,requests=1,authorization=auth(),scope=auth()['scope'],definitive_950=True)
    with pytest.raises(ValueError):reserve(j,n=True)
    assert j.snapshot()['reserved_usd']=='0'

def test_two_processes_cannot_overreserve_absolute_cap(tmp_path):
    j=journal(tmp_path,'99');ready=tmp_path/'start'
    code='''import sys,time
from pathlib import Path
from backend.luna_budget import BudgetJournal,BudgetBlocked
path,gate,label=sys.argv[1:]
while not Path(gate).exists():time.sleep(.01)
j=BudgetJournal(path);manifest=label*64
auth=dict(explicit_user_approval=True,sealed_manifest_sha256=manifest,scope='race pilot',allow_definitive_950=False,max_usd='0.75',max_requests=1)
try:j.reserve(label,manifest,reservation_usd='.75',requests=1,authorization=auth,scope='race pilot');print('reserved')
except BudgetBlocked:print('blocked')
'''
    processes=[subprocess.Popen([sys.executable,'-B','-c',code,str(j.path),str(ready),label],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=os.environ.copy()) for label in ('a','b')]
    ready.write_text('go')
    results=[p.communicate(timeout=20) for p in processes]
    assert all(p.returncode==0 for p in processes),results
    assert sorted(out.strip() for out,err in results)==['blocked','reserved'],results
    assert Decimal(j.snapshot()['reserved_usd'])==Decimal('.75')
    assert Decimal(j.snapshot()['available_usd'])==Decimal('.25')
