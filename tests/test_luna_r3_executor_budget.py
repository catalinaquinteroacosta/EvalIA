import importlib.util
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.luna_budget import BudgetBlocked

def test_actual_executor_rejects_uncertain_or_settled_before_network():
    path=Path('docs/economic_readers_step3_20261015/corrections_02/execute_focal_r3.py')
    spec=importlib.util.spec_from_file_location('r3_budget_boundary',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden')) as network:
        with pytest.raises(BudgetBlocked,match='settled_or_uncertain'):
            module.api('POST','/v1/batches',b'{}')
        network.assert_not_called()
