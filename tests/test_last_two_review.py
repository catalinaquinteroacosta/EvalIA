"""Focal integrity and official reconciliation checks; never invoke an API."""
import importlib.util
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'docs/economic_readers_step3_2_20261016/review_last_two.py'
spec = importlib.util.spec_from_file_location('last_two_review', PATH)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

def test_two_original_pairs_reconcile_without_overriding_unknowns():
    previous = {r['code']:r for r in review.ops.read(review.OLD/'ESTADO_DIEZ_V16.json')}
    for code in review.CODES:
        result = review.focal_replay(code)
        expected = previous[code]['indicator']['verified_decisions']
        assert result['values'] == {k.split('.',1)[1]:v['value'] for k,v in expected.items()}
        assert result['status'] == 'BLOCKED' and result['score'] is None
        assert result['values']['gate'] is None
        assert len(result['evidence']) == 2 and result['new_API_calls'] == 0

def test_official_availability_requirement_and_production_focus_agree():
    contract = review.reader.LunaProvider(None).contracts['CR-AC6']
    assert 'segura y realmente disponible' in contract['applicability']['text']
    focus = review.reader._RELATIONAL_READING['CR-AC6']
    assert 'No exigir confirmación ritual' in focus
    official = review.ops.read(review.OUT/'TEXTOS_OFICIALES.json')
    ac6 = next(r for r in official if r['code']=='CR-AC6')
    assert ac6['applicability']['text'] == contract['applicability']['text']
    assert ac6['levels_0_1_2_3'] == contract['levels']

def test_focal_delivery_preserves_balance_and_original_sources():
    account = review.ops.read(review.OUT/'COSTOS_Y_SALDO.json')
    assert account['before'] == account['after']
    assert account['new_API_calls'] == 0 and account['new_spend_usd']=='0'
    scope = review.ops.read(review.OUT/'ALCANCE.json')
    assert scope['codes'] == list(review.CODES)
    assert scope['other_indicators_evaluated'] == scope['database_writes'] == scope['shared_cache_writes'] == 0
    for path, digest in scope['source_hashes'].items():
        assert review.ops.sha(path) == digest
