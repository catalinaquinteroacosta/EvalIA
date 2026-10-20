import pytest
from backend.evaluators.ps.pilot import validate_cases, main

def test_dry_run_does_not_need_api_key(capsys, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    assert main(['--codes','PS2','PS3']) == 0
    output=capsys.readouterr().out
    assert '"api_calls": 0' in output
    assert '"PS2"' in output

def test_invalid_history_rejected():
    with pytest.raises(ValueError):
        validate_cases([{'id':'x','user':'hi','response':'hello','prior_history':[{'role':'system','text':'bad'}]}])

def test_duplicate_case_rejected():
    case={'id':'x','user':'hi','response':'hello','prior_history':[]}
    with pytest.raises(ValueError):validate_cases([case,case])
