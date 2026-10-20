"""Real retained evidence, offline: a legacy flag cannot bypass qualification."""
import json
from pathlib import Path
from copy import deepcopy
import pytest
from crisis_semantic.domain import Input,Turn
from crisis_semantic.openai_private import OpenAIPrivate
from .pending10_provider import Pending10Provider
from .pending10_ratified import CrisisEvaluator

@pytest.mark.parametrize('code,batch,case_id,score',[
 ('CR-CE10','batch_04','qualified_final_ce10_complete_continuity',3),
 ('CR-RI2','batch_03','release_ri2_vague_qualification',1)])
@pytest.mark.parametrize('certificate',['legacy_flag_only','wrong_identity','current_record'])
def test_current_record_required_without_mutating_provider(monkeypatch,code,batch,case_id,score,certificate):
    root=Path('docs/pending10_20261014')
    case=next(r['case'] for r in json.loads((root/batch/'results.json').read_text(encoding='utf-8')) if r['case']['id']==case_id)
    model=case['history'][0].get('model','pending10') if case['history'] else 'pending10'
    ctx=Input(Turn(case['current_turn'],case['current_user'],case['current_ai'],model),tuple(Turn(t['number'],t['user'],t['ai'],t.get('model',model)) for t in case['history']))
    p=Pending10Provider();p.qualified_components={code};p.qualification_records={}
    if certificate!='legacy_flag_only':
        proof=deepcopy(json.loads((root/'qualification_FINAL.json').read_text(encoding='utf-8'))[code])
        if certificate=='wrong_identity':proof['identity']['model']='gpt-4.1-mini-2025-04-14'
        p.qualification_records[code]=proof
    before=deepcopy(p.qualification_records);before_flags=set(p.qualified_components)
    calls=[]
    def replay(self,stage,system,content,schema,ids,identity,**kwargs):
        calls.append(stage)
        return json.loads((root/batch/(case_id+'_'+stage)/'claims.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(OpenAIPrivate,'run',replay)
    result=CrisisEvaluator(p).evaluate(ctx,[code])['results'][0]
    assert calls==['extract','verify']
    if certificate=='current_record':assert result['status']=='SCORED' and result['score']==score
    else:assert result['status']=='BLOCKED' and result['score'] is None
    assert p.qualification_records==before and p.qualified_components==before_flags
