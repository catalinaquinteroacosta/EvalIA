import csv
import json
from pathlib import Path
from backend.evaluators.ansiedad_semantic.live_regression_cases import prepared_requests
from backend.evaluators.ansiedad_semantic.result_tables import aggregate

ROOT=Path(__file__).resolve().parents[2]/'docs/ansiedad_semantic/integral_20261012'

def test_matrix_exact_coverage_and_no_live_claim():
    matrix=json.loads((ROOT/'fidelity_matrix.json').read_text(encoding='utf-8'))
    assert len(matrix['indicators'])==81 and len(matrix['counts'])==9
    assert all(set(r['levels'])=={'0','1','2','3'} and r['components'] and
        not r['live_semantics_of_this_route_validated'] for r in matrix['indicators'])

def test_pending_072_json_csv_and_no_complete_percentage():
    rows=json.loads((ROOT/'experiment072_pending/observations.json').read_text(encoding='utf-8'))
    assert len(rows)==2025 and len({r['model'] for r in rows})==5
    assert all(r['status']=='PENDING' and r['score'] is None for r in rows)
    assert aggregate(rows,expected_count=2025)['percentage'] is None
    with (ROOT/'experiment072_pending/observations.csv').open(encoding='utf-8',newline='') as source:
        csvrows=list(csv.DictReader(source))
    assert len(csvrows)==2025 and all(r['score']=='' and r['status']=='PENDING' for r in csvrows)
    assert [(r['model'],str(r['turn']),r['code'],r['input_sha256']) for r in rows]==[
        (r['model'],r['turn'],r['code'],r['input_sha256']) for r in csvrows]

def test_regressions_are_blind_paired_requests_not_claimed_live_scores():
    cases=prepared_requests()
    assert len(cases)==12
    for case in cases:
        a,b=case['requests']
        assert a['stage']=='extract' and b['stage']=='independent_verify'
        assert a['original']==b['original'] and set(a['indicators'])=={case['code']}
        assert not any(k in b for k in ('extraction','score','verification_result'))
