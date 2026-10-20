import json
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/'fixtures'/'pares_ce2_ce5.json'

def test_sixteen_cases_and_levels():
    cases=json.loads(DATA.read_text(encoding='utf-8'))['cases']
    assert len(cases)==16
    for indicator in ('CE2','CE3','CE4','CE5'):
        subset=[c for c in cases if c['indicator']==indicator]
        assert sorted(c['proposed_score'] for c in subset)==[0,1,2,3]

def test_every_case_is_reviewable():
    cases=json.loads(DATA.read_text(encoding='utf-8'))['cases']
    assert len({c['id'] for c in cases})==16
    assert all(c['user_message'] and c['assistant_response'] and c['rationale'] for c in cases)
    assert all(c['expert_approved'] is False for c in cases)

def test_never_treat_provisional_as_ground_truth():
    cases=json.loads(DATA.read_text(encoding='utf-8'))['cases']
    assert any(c['reference_status']=='provisional' for c in cases)
    assert not any(c['expert_approved'] for c in cases)
