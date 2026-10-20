import pytest
from backend.evaluators.ansiedad_semantic.af_gate_state import exists_state, conjunction, require_gate
from backend.evaluators.rules.af2_scorer import resolve_af2_applicability
from backend.evaluators.rules.af3_scorer import resolve_af3_applicability

def item(status):return {"semantic_validation":{"status":status}}

@pytest.mark.parametrize("rows,expected",[([],False),([item("supported")],True),([item("not_supported")],False),([item("ambiguous")],None),([{}],None),([item("supported"),item("ambiguous")],True)])
def test_exists_three_states(rows,expected):assert exists_state(rows) is expected

def test_af2_unknown_not_na():
    with pytest.raises(ValueError):resolve_af2_applicability({"modifiable_components":[item("ambiguous")]})
    assert resolve_af2_applicability({"modifiable_components":[item("not_supported")]}) is False

def test_af2_incomplete_not_na():
    with pytest.raises((ValueError,TypeError)):resolve_af2_applicability({})

def test_af3_unknown_needed_domain_blocks():
    with pytest.raises(ValueError):resolve_af3_applicability(user_control={"unmodifiable_now":[item("ambiguous")]},user_emotion={"distress":[item("supported")]})

def test_af3_known_false_conjunct_does_not_require_unneeded_domain():
    assert resolve_af3_applicability(user_control={"unmodifiable_now":[]},user_emotion={"distress":[item("ambiguous")]}) is False
