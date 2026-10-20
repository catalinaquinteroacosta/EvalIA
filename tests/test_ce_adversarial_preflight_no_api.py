from pathlib import Path
from ce_adversarial_preflight import prepare


def test_preflight_all_cases():
    cases = prepare('casos_adversariales_ce2_ce10.json')
    assert len(cases) == 29
    assert {r['indicator'] for r in cases} == {f'CE{i}' for i in range(2,11)}
    assert all(r['actual_score'] is None for r in cases)


def test_ce10_history_only_same_model():
    cases = prepare('casos_adversariales_ce2_ce10.json')
    ce10 = [r for r in cases if r['indicator']=='CE10']
    assert ce10
    assert all(isinstance(r['history'],list) for r in ce10)
    assert next(r for r in ce10 if r['id']=='ce10_other_model')['history']==[]


def test_other_indicators_do_not_inherit_history():
    assert all(r['history'] is None for r in prepare('casos_adversariales_ce2_ce10.json') if r['indicator']!='CE10')
