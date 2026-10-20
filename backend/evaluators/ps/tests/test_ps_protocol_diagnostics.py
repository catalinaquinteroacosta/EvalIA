import pytest
from backend.evaluators.ps.semantic import _evidence, SemanticProtocolError

def test_current_evidence_requires_null():
    with pytest.raises(SemanticProtocolError, match='history_index=null'):
        _evidence([{'source':'response','quote':'hola','history_index':0}])

def test_evidence_string_has_precise_error():
    with pytest.raises(SemanticProtocolError, match='must be object'):
        _evidence(['hola'])

def test_valid_current_evidence():
    assert _evidence([{'source':'user','quote':'hola','history_index':None}])[0].history_index is None

def test_history_zero_allowed():
    assert _evidence([{'source':'history','quote':'hola','history_index':0}])[0].history_index == 0
