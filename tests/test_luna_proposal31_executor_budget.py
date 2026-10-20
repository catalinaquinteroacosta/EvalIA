"""Real executor boundary with a private journal and forbidden network."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.luna_budget import BudgetJournal, BudgetBlocked


def executor(tmp_path, monkeypatch):
    path = Path('docs/economic_readers_step3_20261015/corrections_02/execute_proposal31.py')
    spec = importlib.util.spec_from_file_location('proposal31_budget_boundary', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    auth = dict(explicit_user_approval=True, max_usd='.05', max_requests=12,
                allow_definitive_950=False, scope='sealed twelve only',
                sealed_manifest_sha256='a' * 64)
    journal = BudgetJournal(tmp_path / 'budget.json')
    journal.initialize(prior_evidence='controlled offline test, not API usage')
    monkeypatch.setattr(module, 'journal', lambda: journal)
    monkeypatch.setattr(module, 'verify', lambda: None)
    monkeypatch.setattr(module, 'read', lambda _: auth)
    return module, journal, auth


@pytest.mark.parametrize('status', ['uncertain', 'settled'])
def test_current_executor_rejects_closed_or_uncertain_run_before_network(tmp_path, monkeypatch, status):
    module, journal, auth = executor(tmp_path, monkeypatch)
    journal.reserve('proposal31', 'a' * 64, reservation_usd='.05', requests=12,
                    authorization=auth, scope=auth['scope'])
    if status == 'uncertain':
        journal.mark_uncertain('proposal31', reason='controlled lost response')
    else:
        journal.settle('proposal31', actual_usd='.01', actual_requests=12,
                       usage_evidence='controlled complete usage', fully_reconciled=True)
    with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')) as network:
        with pytest.raises(BudgetBlocked, match='uncertain_or_settled'):
            module.api('POST', '/v1/batches', b'{}')
        network.assert_not_called()


def test_current_executor_rejects_insufficient_authorization_before_network(tmp_path, monkeypatch):
    module, journal, auth = executor(tmp_path, monkeypatch)
    auth['max_requests'] = 11
    with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')) as network:
        with pytest.raises(BudgetBlocked, match='authorization_limit_exceeded'):
            module.api('POST', '/v1/files', b'controlled fixture')
        network.assert_not_called()
    assert journal.snapshot()['reserved_usd'] == '0'
