"""Acceptance checks for this offline audit, not engine semantic validation."""
import json
from pathlib import Path
from decimal import Decimal
from backend.evaluators.ansiedad_semantic.budgeted_reader import estimate

ROOT=Path('docs/ansiedad_semantic/closure6_20261013/offline_04')
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))

def test_all81_have_specific_context_and_literal_descriptors():
    rows=read('contextual_review_81.json')
    assert len(rows)==len({r['code'] for r in rows})==81
    assert len({r['code'][:2] for r in rows})==9
    for r in rows:
        assert set(r['official']['levels'])=={'0','1','2','3'}
        assert r['contextual_review'] and r['applicability_rule']
        assert not r['implementation_defect_demonstrated_by_missing_level_alone']

def test_eleven_raw_pairs_preserved_and_literal():
    rows=read('eleven_case_audit.json')
    assert len(rows)==11
    assert sum(r['kind']=='critical_alert' for r in rows)==5
    for r in rows:
        assert r['replacement_score'] is None
        assert all(c['valid'] for c in r['literal_checks'])

def test_request_plan_is_deduplicated_and_financially_bounded():
    hashes=[];total=Decimal(0)
    for plan in read('paid_minimum_plan_NOT_AUTHORIZED.json'):
        assert plan['paid_execution_authorized'] is False
        for call in plan['calls']:
            q=read(call['request'])
            assert not ({'expected','expected_hypothesis','score','target_score'}&set(q))
            assert 'hypothesis' not in q.get('offline_review_question',{})
            assert estimate(q,call['model'])['reserved_upper_bound_usd']==call['cost_max_usd']
            total+=Decimal(call['cost_max_usd']);hashes.append(call['request_sha256'])
    budget=read('paid_budget_NOT_AUTHORIZED.json')
    assert len(hashes)==len(set(hashes))==budget['total_calls']
    assert total==Decimal(budget['total_configured_max_usd'])

def test_ce_only_verifier_preserves_saved_extraction():
    q=read('requests/CE_verifier_current_NOT_SENT.json')
    old=json.loads(Path('docs/ansiedad_semantic/finish_20261013/step3_engine_01/call_17.json').read_text(encoding='utf-8'))
    assert q['stage']=='independent_verify'
    assert q['original']==old['request']['original']
    assert q['untrusted_proposed_components']==old['reading']

def test_protected_scope_and_ledger_unchanged():
    d=read('integrity.json')
    assert d['crisis_differences']==[] and d['crisis_entries']==62
    assert d['ledger_unchanged'] and not d['shared_sqlite_opened'] and d['api_calls']==0

def test_reuse_does_not_claim_self_replay_certifies_semantics():
    reused=[p for p in read('paid_minimum_plan_NOT_AUTHORIZED.json') if p.get('reused_extraction')]
    assert reused
    for p in reused:
        assert len(p['calls'])==1 and p['calls'][0]['stage']=='independent_verify'
        assert 'not semantically certified' in p['reused_extraction']['qualification']
