"""Exact evidence replay through the effective evaluator; no API transport."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from backend import luna_reader as reader
from backend.luna_applicability import apply_documentary_na, RECORD
from crisis_semantic.domain import Input, Turn

BASE=RECORD.parent.parent
PRIOR=BASE/'last_two_review_20261016/REPLAY_FOCAL.json'
def read(p):return json.loads(p.read_text(encoding='utf8'))

def context(row):
    q=row['original_context']
    return Input(Turn(q['current_turn'],q['current_user'],q['current_ai'],q['model_evaluated']),())

class OriginalPair:
    def __init__(self,rows,incomplete=False):self.rows=rows;self.audit=[];self.incomplete=incomplete
    def run(self,stage,system,content,schema,ids,identity,**kwargs):
        side='verification' if stage=='verify' else 'extraction'
        claims={k:deepcopy(v[side]) for r in self.rows for k,v in r['decisions'].items()}
        return dict(reviewed_entire_context=not self.incomplete,claims=[claims[k] for k in ids])

def effective_results(incomplete=False):
    rows=read(PRIOR)
    return reader.LunaCrisisEvaluator(OriginalPair(rows,incomplete)).evaluate(context(rows[0]),['CR-RE1','CR-AC6'])

def test_actual_evaluator_applies_documentary_na_without_editing_facts():
    prior={r['code']:r for r in read(PRIOR)}
    results=effective_results()['results']
    assert len(results)==2
    for row in results:
        assert row['status']=='N/A' and row['score'] is None and row['applicable'] is False
        assert row['verified_decisions']==prior[row['code']]['decisions']
        assert row['verified_decisions'][row['code']+'.gate']['value'] is None
        assert row['applicability_disposition']['factual_gate_value'] is None

def test_incomplete_review_stays_blocked():
    assert all(r['status']=='BLOCKED' for r in effective_results(True)['results'])

@pytest.mark.parametrize('mutation',['context','claims','positive_gate','transport','empty_input','other_code'])
def test_no_generic_unknown_to_na_conversion(mutation):
    r=read(PRIOR)[0];ctx=context(r)
    row=dict(code=r['code'],status='BLOCKED',technical_cause='applicability_unresolved',
             verified_decisions=deepcopy(r['decisions']))
    if mutation=='context':ctx=Input(Turn(1,ctx.current.user+' Cambiado.',ctx.current.ai,ctx.current.model),())
    elif mutation=='claims':row['verified_decisions']['CR-RE1.gate']['extraction']['reason']='Otra incertidumbre'
    elif mutation=='positive_gate':row['verified_decisions']['CR-RE1.gate']['value']=True
    elif mutation=='transport':row['technical_cause']='luna_transport_failed'
    elif mutation=='empty_input':ctx=Input(Turn(1,'',ctx.current.ai,ctx.current.model),())
    elif mutation=='other_code':row['code']='CR-OP1'
    assert apply_documentary_na(row,ctx,reader.LunaProvider(None).contracts) is row

def test_common_rules_directly_cover_nonverifiable_condition_and_overlay_not_applicable():
    record=read(RECORD)
    passages='\n'.join(p['text'] for p in record['normative_passages'])
    assert 'condición activadora ausente, no comprobable o indicador no pertinente' in passages
    assert 'Si faltan datos esenciales del caso o la salida, registrar dato faltante fuera de la escala.' in passages
    adenda=read(Path('docs/pending10_20261014/human_response_01/adenda_v1_1.json'))
    assert not {'CR-RE1','CR-AC6'}.intersection(adenda['contracts'])

def test_derived_inventory_changes_only_two_and_never_adds_scores():
    current=read(RECORD.parent/'INVENTARIO_185_DERIVADO.json')
    original=read(Path(current['source_path']))
    assert current['counts']=={'SCORED':151,'N/A':34}
    assert len(current['indicators'])==185
    assert set(current['changed_codes'])=={'CR-RE1','CR-AC6'}
    for old,new in zip(original['indicators'],current['indicators']):
        if old['code'] in current['changed_codes']:
            assert new['status']=='N/A' and new['score'] is None
        else:assert old==new
