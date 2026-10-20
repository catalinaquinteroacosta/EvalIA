import pytest
from backend.evaluators.ps.contracts import Turn
from backend.evaluators.ps.semantic import _evidence, SemanticProtocolError, _claim

def test_current_index_repaired_only_when_quote_verified():
    turn=Turn('Estoy aquí','¿Te sientes seguro?')
    ev=_evidence([{'source':'response','quote':'¿Te sientes seguro?','history_index':0}],turn)
    assert ev[0].history_index is None

def test_current_index_not_repaired_without_literal():
    with pytest.raises(SemanticProtocolError):
        _evidence([{'source':'response','quote':'texto inventado','history_index':0}],Turn('a','b'))

def test_history_index_preserved():
    ev=_evidence([{'source':'history','quote':'Hola','history_index':0}],Turn('a','b'))
    assert ev[0].history_index == 0

def test_malformed_level_is_explicit_protocol_error():
    with pytest.raises(SemanticProtocolError, match='Malformed claim'):
        _claim('PS2','supported','level_2_matches',Turn('a','b'))

def test_missing_turn_never_repairs():
    with pytest.raises(SemanticProtocolError):
        _evidence([{'source':'response','quote':'b','history_index':0}])
