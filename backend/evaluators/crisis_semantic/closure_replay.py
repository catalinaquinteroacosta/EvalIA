"""Read-only final package replay, with integrity and deterministic recalculation."""
from collections import Counter
from .closure_run import OUT,read
from .span_provider import fingerprint
from .domain import load_contracts
from .scoring import resolve_score

def run(selected=None):
    from .domain import DOCS
    version=DOCS/'ac9_live8'/'final_comparison.json'
    approved=DOCS/'ac9_live8'/'release.json'
    data=read(version if approved.exists() and read(approved).get('semantic_regression_passed') is True else OUT/'final_comparison.json')
    if data['fingerprint']!=fingerprint():raise ValueError('closure_fingerprint_mismatch')
    contracts,_,_=load_contracts()
    if selected and set(selected)-{b['case'] for b in data['reports']}:raise ValueError('unknown_case')
    batches=[b for b in data['reports'] if not selected or b['case'] in selected]
    for batch in batches:
        for row in batch['evaluation']['results']:
            if row['status']=='SCORED':
                score,cause=resolve_score(row['code'],{k.split('.',1)[1]:v['value'] for k,v in row['verified_decisions'].items()},contracts)
                if row['score']!=score or cause or row['official_descriptor']!=contracts[row['code']]['levels'][str(score)]['text']:raise ValueError('closure_score_integrity_failure')
            elif row['score'] is not None:raise ValueError('non_numeric_state_has_score')
    statuses=dict(Counter(r['status'] for batch in batches if not batch['extra'] for r in batch['evaluation']['results']))
    return {**data,'reports':batches,'statuses':statuses,'selected_cases':selected,'replay_only':True,'new_api_calls':0}
