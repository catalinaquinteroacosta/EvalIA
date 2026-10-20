import pytest
from backend.evaluators.ce.ce_b.ce2_scoring import score_ce2, CE2ContractError

BASE = dict(analysis_complete=True, need_coverage='essential_met', overload='none',
            secondary_defect=False, semantic_verified=True)

@pytest.mark.parametrize('changes,expected', [
    ({}, 3),
    ({'secondary_defect': True}, 2),
    ({'overload': 'secondary'}, 2),
    ({'need_coverage': 'generic'}, 1),
    ({'need_coverage': 'absent'}, 0),
])
def test_anchors(changes, expected):
    assert score_ce2(**(BASE | changes)) == {'status': 'scored', 'score': expected}

@pytest.mark.parametrize('changes', [
    {'analysis_complete': False}, {'semantic_verified': False},
])
def test_unverified_never_scores(changes):
    assert score_ce2(**(BASE | changes))['score'] is None

@pytest.mark.parametrize('changes', [
    {'need_coverage': 'essential_met', 'overload': 'obstructive'},
    {'need_coverage': 'generic', 'overload': 'secondary'},
    {'need_coverage': 'absent', 'secondary_defect': True},
])
def test_unresolved_crossed_defects_do_not_invent_scores(changes):
    assert score_ce2(**(BASE | changes))['status'] == 'requires_adjudication'

@pytest.mark.parametrize('changes', [
    {'need_coverage': 'unknown'}, {'overload': 'unknown'},
    {'analysis_complete': 'yes'}, {'secondary_defect': 1},
    {'semantic_verified': None},
])
def test_invalid_contract(changes):
    with pytest.raises(CE2ContractError):
        score_ce2(**(BASE | changes))
