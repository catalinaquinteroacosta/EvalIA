import copy
import pytest
from backend.evaluators.ps.runner import _merge_reconciliation


def sample():
    return {'indicator':'PS3', 'applicability': {'predicate':'applies','verification':'unsupported'},
            'levels': {str(i):{'verification':'supported' if i in (2,3) else 'unsupported', 'evidence':[]} for i in range(4)}}


def test_applicability_merge_preserves_all_levels():
    original = sample()
    proposed = copy.deepcopy(original)
    proposed['applicability'] = {'predicate':'not_applicable','verification':'supported','evidence':[]}
    proposed['levels']['2']['verification'] = 'unsupported'
    merged = _merge_reconciliation(original, proposed, 'Applicability unverified')
    assert merged['levels'] == original['levels']
    assert merged['applicability'] == proposed['applicability']


def test_level_merge_preserves_applicability_and_uncontested_levels():
    original = sample()
    proposed = copy.deepcopy(original)
    proposed['applicability'] = {'predicate':'not_applicable','verification':'supported'}
    proposed['levels']['0']['verification'] = 'supported'
    proposed['levels']['2']['verification'] = 'unsupported'
    merged = _merge_reconciliation(original, proposed, 'Rubric level not uniquely supported')
    assert merged['applicability'] == original['applicability']
    assert merged['levels']['0'] == original['levels']['0']
    assert merged['levels']['2'] == proposed['levels']['2']


def test_unknown_reason_cannot_replace_anything():
    original = sample()
    assert _merge_reconciliation(original, {'indicator':'PS3'}, 'Evidence audit failed') == original


def test_cross_indicator_rejected():
    with pytest.raises(ValueError, match='indicator mismatch'):
        _merge_reconciliation(sample(), {'indicator':'PS2'}, 'Applicability unverified')


def test_no_missing_reconciled_claim():
    with pytest.raises(ValueError, match='Missing reconciled disputed levels'):
        _merge_reconciliation(sample(), {'indicator':'PS3','levels':{}}, 'Rubric level not uniquely supported')
