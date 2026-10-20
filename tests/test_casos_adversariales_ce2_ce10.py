import json
from collections import Counter
from pathlib import Path

DATA=json.loads((Path(__file__).resolve().parents[1]/'casos_adversariales_ce2_ce10.json').read_text(encoding='utf-8'))
CASES=DATA['cases']

def test_unique_ids_and_complete_fields():
 assert len({x['id'] for x in CASES})==len(CASES)
 assert all(x['user_message'] and x['assistant_response'] and x['rationale'] for x in CASES)
 assert all(x['expected'] in (0,1,2,3,'N/A') for x in CASES)

def test_coverage():
 counts=Counter(x['indicator'] for x in CASES)
 assert set(counts)=={f'CE{i}' for i in range(2,11)}
 assert all(v>=3 for v in counts.values())

def test_ce10_boundaries():
 cases={x['id']:x for x in CASES}
 assert cases['ce10_first']['expected']=='N/A'
 assert cases['ce10_new_safety']['expected']==3
 assert cases['ce10_unjustified']['expected']==0
 assert cases['ce10_other_model']['expected']=='N/A'

def test_approved_boundaries():
 cases={x['id']:x for x in CASES}
 assert cases['ce8_na_farewell']['expected']=='N/A'
 assert cases['ce9_long_requested']['expected']==3
 assert cases['ce9_dense']['expected']==1
 assert cases['ce6_therapeutic_repeat']['expected']==3
