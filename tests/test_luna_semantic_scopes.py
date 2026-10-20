import json
from copy import deepcopy
from pathlib import Path
from backend.luna_reader import adapt_body, effective_clarifications, SEMANTIC_CLARIFICATIONS

ROWS=json.loads(Path('docs/economic_readers_step3_20261015/validation_v2/REQUESTS_NOT_SENT.json').read_text(encoding='utf8'))

def base(row):
    b=deepcopy(row['body']);messages=b.get('input',b.get('messages'))
    assert messages[0]['content'].endswith(SEMANTIC_CLARIFICATIONS)
    messages[0]['content']=messages[0]['content'][:-len(SEMANTIC_CLARIFICATIONS)]
    return b

def codes(row):
    b=row['body'];payload=json.loads(b.get('input',b.get('messages'))[1]['content'])
    return set(d['code'] for d in payload['predicates'].values()) if 'predicates' in payload else set(payload['indicators'])

def test_unaffected_sealed_requests_have_identical_effective_body():
    checked=0
    for row in ROWS:
        if effective_clarifications(codes(row)) != SEMANTIC_CLARIFICATIONS:continue
        assert adapt_body(base(row),row['url']) == row['body']
        checked+=1
    assert checked>=12

def test_scoped_changes_preserve_contract_original_schema_and_caps():
    changed=0
    for row in ROWS:
        adapted=adapt_body(base(row),row['url'])
        old=deepcopy(row['body']);new=deepcopy(adapted)
        old.get('input',old.get('messages'))[0]['content']='system'
        new.get('input',new.get('messages'))[0]['content']='system'
        assert old==new
        changed+=adapted!=row['body']
    assert changed>0

def test_independence_and_no_forced_observations():
    text=effective_clarifications(['CR-OP4','CR-RI2','CR-CT3'])
    assert 'cualquiera de ellas ausente' in text
    assert 'juicio al acompañar la pregunta' in text
    assert 'insuficiencia secundaria concreta' in text
    assert effective_clarifications(['CR-CE10']) == SEMANTIC_CLARIFICATIONS
    assert effective_clarifications(['GD2','EM5']) == SEMANTIC_CLARIFICATIONS
    assert 'referencia1' not in text

def test_em9_scope_requires_causal_not_merely_temporal_relation():
    text=effective_clarifications(['EM9'])
    assert 'relación causal' in text
    assert 'ampliación opcional' in text
    assert effective_clarifications(['EM8']) == SEMANTIC_CLARIFICATIONS
