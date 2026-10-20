"""Offline guards and exact archived raw output replay; not new semantic evidence."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from backend.luna_reader import select_final,adapt_body,LunaProvider,reader_identity,estimate_reserve,usage_cost

BASE=Path('docs/economic_readers_step2_20261015')
def archived(cid):
    return next(json.loads(line)['response']['body'] for line in (BASE/'output_file_id_0.jsonl').read_text(encoding='utf-8').splitlines() if json.loads(line)['custom_id']==cid)

def test_archived_multiple_messages_selects_unique_final_without_rewriting():
    raw=archived('pilot_009_gpt-6-luna');before=deepcopy(raw)
    wire,audit=select_final(raw)
    assert raw==before and audit['selected_phase']=='final_answer' and len(audit['ignored_message_ids'])==1
    assert wire['claims']['CR-RI2.judgment']['observation']=='present'

def test_archived_truncation_stays_blocked_and_cannot_salvage_json():
    with pytest.raises(ValueError,match='incomplete'):select_final(archived('pilot_077_gpt-6-luna'))

def test_ambiguous_final_rejected():
    raw=archived('pilot_009_gpt-6-luna');raw['output'].append(deepcopy(raw['output'][-1]))
    with pytest.raises(ValueError,match='ambiguous'):select_final(raw)

def test_luna_qualification_rejects_gpt41_and_asserted_flags():
    p=LunaProvider(lambda *args:None)
    assert not p.qualified('CR-RI2') and not p.qualified('CR-CE10')
    p.certificates['CR-RI2']={'identity':reader_identity('CR-RI2',p.contracts),'controlled_test_fixture':False,'review_passed':True,'cases':[{'expected':n,'actual':n} for n in range(4)]}
    assert not p.qualified('CR-RI2')
    p.certificates['CR-CE10']=json.loads(Path('docs/pending10_20261014/qualification_FINAL.json').read_text(encoding='utf-8'))['CR-CE10']
    assert not p.qualified('CR-CE10')

@pytest.mark.parametrize('size',[8,100,124])
def test_only_large_crisis_package_gets_bounded_output_headroom(size):
    body={'model':'old','temperature':0,'store':False,'max_output_tokens':min(10000,max(1500,size*80)),
      'input':[{'role':'system','content':'Original prompt'},{'role':'user','content':json.dumps({'predicates':{str(i):{} for i in range(size)}})}],
      'text':{'format':{'schema':{'type':'object'}}}}
    result=adapt_body(body,'/v1/responses')
    assert result['text']==body['text'] and result['input'][1]==body['input'][1]
    assert result['max_output_tokens']==(min(18000,max(body['max_output_tokens'],size*112+256)) if size>100 else body['max_output_tokens'])

def test_budget_accounts_cache_writes_and_sync_never_implicitly_batch():
    raw=archived('pilot_009_gpt-6-luna')
    assert usage_cost(raw,'sync')==2*usage_cost(raw,'batch')
    body={'model':'gpt-6-luna','max_output_tokens':100}
    a=estimate_reserve(body);b=estimate_reserve(body,'sync')
    from decimal import Decimal
    assert Decimal(b['reserved_usd'])==2*Decimal(a['reserved_usd'])
