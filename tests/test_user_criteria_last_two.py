"""Check new interpretation provenance and prevent unratified gate overrides."""
import importlib.util
from pathlib import Path
PATH = Path(__file__).resolve().parents[1]/'docs/economic_readers_step3_2_20261016/record_user_criteria_last_two.py'
spec = importlib.util.spec_from_file_location('user_criteria_last_two', PATH)
record = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record)

def test_user_criteria_remain_separate_from_professional_and_official_evidence():
    rows = record.review.ops.read(record.OUT/'CRITERIOS_Y_PROCEDENCIA.json')
    assert {r['code'] for r in rows} == {'CR-RE1','CR-AC6'}
    contracts = record.review.reader.LunaProvider(None).contracts
    for r in rows:
        assert r['professional_adjudication'] is False and r['professional_identity'] is None
        assert r['applied_to_production'] is False
        assert r['official_gate']['text'] == contracts[r['code']]['applicability']['text']
        assert r['existing_evidence_sha256'] == record.review.ops.sha(r['existing_evidence_path'])
        assert r['gate_value'] is None and r['score'] is None and r['status']=='BLOCKED'

def test_no_new_budget_charge_or_protected_source_change():
    account = record.review.ops.read(record.OUT/'COSTOS_Y_SALDO.json')
    assert account['before'] == account['after']
    assert account['new_API_calls'] == 0 and account['new_spend_usd']=='0'
    for path, digest in record.review.ops.read(record.review.OUT/'ALCANCE.json')['source_hashes'].items():
        assert record.review.ops.sha(path) == digest
