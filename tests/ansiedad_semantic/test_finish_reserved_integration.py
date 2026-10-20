import copy
from backend.evaluators.ansiedad_semantic.finish_holdout_corpus import build
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn,authorized_context
from backend.evaluators.ansiedad_semantic.engine import evaluate_turn

def test_reserved_history_excludes_future_and_other_model():
    case=next(c for c in build() if c['id']=='reserved-CE');o=case['original']
    earlier=o['prior_history']
    rows=[OriginalTurn(o['conversation'],o['model'],1,earlier[0]['text'],earlier[1]['text']),
          OriginalTurn(o['conversation'],o['model'],2,o['user'],o['response']),
          OriginalTurn(o['conversation'],o['model'],3,'FUTURE POISON','FUTURE POISON'),
          OriginalTurn(o['conversation'],'other model',1,'OTHER POISON','OTHER POISON')]
    assert authorized_context(rows,o['conversation'],o['model'],2)==o

def test_actual_entry_point_does_not_score_provider_failure():
    case=next(c for c in build() if c['id']=='reserved-AF');o=case['original'];calls=[]
    def unavailable(q):
        calls.append(copy.deepcopy(q))
        raise RuntimeError('Controlled provider failure, no API transport')
    result=evaluate_turn([OriginalTurn(o['conversation'],o['model'],1,o['user'],o['response'])],
        o['conversation'],o['model'],1,reader=unavailable)
    assert len(result['rows'])==81
    assert all(r['score'] is None for r in result['rows'])
    assert all(r['status']=='BLOCKED' for r in result['rows'] if r['code']!='CE10')
    assert next(r for r in result['rows'] if r['code']=='CE10')['status']=='N/A'
    assert result['summary']['percentage'] is None and not result['summary']['complete']
    assert len(calls)==9
