"""Integration route assertions and controlled offline boundary regression."""
import json
from pathlib import Path
import pytest
from .frontend_candidate import CrisisEvaluator,evaluate_anxiety_turn
from .anxiety import evaluate_turn
from crisis_semantic.domain import Input,Turn

CASES=json.loads(Path('docs/crisis_adjudication_20261014/step3_02/adversarial_results.json').read_text(encoding='utf-8'))

def test_anxiety_effective_entrypoint():
    assert evaluate_anxiety_turn is evaluate_turn

@pytest.mark.parametrize('row',CASES)
def test_crisis_effective_candidate(row):
    class Reader:
        qualified_components={'CR-RI2'} # Fixture qualification only.
        def run(self,stage,system,content,schema,ids,identity):
            # Canonical full independent-stage fixture; no API inference claimed.
            if 'CR-NI6.c' in content['predicates']:
                assert 'No atribuyas precisión' in content['predicates']['CR-NI6.c']['text']
            return next(x['payload'] for x in row['literal_evidence'] if x['stage']==stage)
    c=row['context']
    ctx=Input(Turn(c['current_turn'],c['current_user'],c['current_ai'],c['model_evaluated']))
    code=row['obtained']['code']
    actual=CrisisEvaluator(Reader()).evaluate(ctx,[code])['results'][0]
    assert (actual['status'],actual['score'])==(row['expected_status'],row['expected_score'])
