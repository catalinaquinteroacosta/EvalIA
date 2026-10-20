import json
from pathlib import Path
from backend.evaluators.ansiedad_semantic import component_routes as routes
from backend.evaluators.nd.contracts import TurnContext

def test_real_pa1_disagreement_remains_blocked_without_score_override():
    p=Path('docs/ansiedad_semantic/closure6_20261013/live_5A_02')
    a=json.loads((p/'critical-PA1_extract.json').read_text(encoding='utf-8'))
    b=json.loads((p/'critical-PA1_independent_verify.json').read_text(encoding='utf-8'))
    original=a['request']['original']
    result=routes.adjudicate('PA1',TurnContext(original['user'],original['response'],()),
        a['reading']['indicators']['PA1'],b['reading']['indicators']['PA1'])
    assert result['status']=='BLOCKED' and result['score'] is None
    assert 'secondary_precision_or_adaptation_defect' in result['reason']

def test_pa1_contract_requires_adequate_function_for_secondary_defect():
    assert 'si central_function_realized es false' in routes.definitions('PA1')['secondary_precision_or_adaptation_defect']
