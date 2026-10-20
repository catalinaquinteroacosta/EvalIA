"""Seal the offline deliverable; only new files under offline_04 are written."""
from pathlib import Path
from collections import Counter
from hashlib import sha256
from decimal import Decimal
import json

OUT=Path('docs/ansiedad_semantic/closure6_20261013/offline_04')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

def run():
    plans=read(OUT/'paid_minimum_plan_NOT_AUTHORIZED.json')
    essential=[p for p in plans if p['tier'].startswith('A_')]
    contingent=[p for p in plans if p['tier'].startswith('B_')]
    amount=sum((Decimal(c['cost_max_usd']) for p in essential for c in p['calls']),Decimal(0))
    save('VALIDATION_PLAN_MINIMUM.json',{'status':'PREPARED_NOT_AUTHORIZED_NOT_SENT',
        'calls':sum(len(p['calls']) for p in essential),'configured_max_usd':str(amount),'retry_allowance':0,
        'plans':essential,'remaining_coverage_policy':'Do not automatically execute B. Read CONTEXTUAL_COVERAGE_DECISIONS.json. The minimum resolves current critical questions, not a promise that all unknown future outcomes will pass.'})
    save('CONTEXTUAL_COVERAGE_DECISIONS.json',{'status':'DESIGN_REVIEW_ONLY_NOT_AN_API_ORDER',
        'reviewed_codes':81,'retired_unsupported_hypotheses':len(read(OUT/'retired_hypotheses_not_deleted.json')),
        'contingent_candidates':[{'id':p['id'],'codes':p['codes'],'official':p['official'],'questions':p['semantic_questions'],
            'existing_evidence':p['existing_evidence_to_reuse'],'possible_reuse':p.get('reused_extraction'),
            'action':'After critical results, determine whether this distinction remains material to the verified scope. Never order every unobserved level. Valid 0/3 results may retire a wrong 1/2 hypothesis.'} for p in contingent],
        'draft_contingency_calls':sum(len(p['calls']) for p in contingent),
        'draft_contingency_bound_usd':str(sum((Decimal(c['cost_max_usd']) for p in contingent for c in p['calls']),Decimal(0))),
        'unknown_reachability':{r['code']:r['unestablished_reachability'] for r in read(OUT/'contextual_review_81.json') if r['unestablished_reachability']},
        'qualification':'The combined draft132-call envelope is not the indispensable minimum and is not authorized. No new fixtures or payments are justified solely by missing levels.'})
    blocks=read('docs/ansiedad_semantic/closure6_20261013/offline_01/CLOSURE_REGISTER.json')
    registry=[]
    for row in blocks:
        reason=row['reason'];code=row['code']
        category=('infrastructure_missing_verifier' if 'incomplete after financial' in reason else
                  'unexecuted_preregistered_contrast' if row['status']=='PENDING' else
                  'insufficient_literal_or_source_evidence' if any(s in reason.lower() for s in ('cita','evidencia','soporte')) else
                  'semantic_component_disagreement' if any(s in reason.lower() for s in ('discrepan','incertidumbre')) else
                  'incompatible_component_reading')
        registry.append({**row,'cause_class':category,'contextual_review':'contextual_review_81.json#'+code,
            'offline_analysis':'Completed; preserve unresolved evidence as such. Not automatically an engine error or a required paid retry.',
            'state':'BLOCKED' if row['status']=='BLOCKED' else 'PENDING'})
    for r in read(OUT/'eleven_case_audit.json'):
        if r['kind']=='critical_alert':registry.append({'id':'alert-'+r['code'],'code':r['code'],'source':r['source'],
            'cause_class':r['root_cause'],'state':'SEMANTIC_VALIDATION_PENDING','priority':1,
            'evidence':'eleven_case_audit.json#'+r['code'],'closure_criterion':'New literal independent facts adjudicable under the official descriptor; no historical score override.'})
    save('CLOSURE_REGISTER.json',registry)
    save('step_states.json',{
        'offline_phase':'OFFLINE_COMPLETO','technical_freeze':'NO APTO',
        '1':{'offline':'CLOSED','live':'Not applicable','basis':'81 contextual reviews, individual classifications, ledger unchanged.'},
        '2':{'offline':'CLOSED','live':'BLOCKED','basis':'Five critical reader-contract confusions specified; factual regression pending. No prompt-only certification.'},
        '3':{'offline':'CLOSED','live':'BLOCKED','basis':'Six original cases audited; 181 literal references across eleven cases checked. No disputed fact replaced.'},
        '4':{'offline':'CLOSED','live':'PARTIAL','basis':'Reachability unknowns and78 unsupported target hypotheses documented. No universal four-level or automatic new-call requirement.'},
        '5':{'offline':'CLOSED','live':'BLOCKED','basis':'17 real outputs retained; CE verifier and14 other affected integration results require evidence. Only affected codes planned.'},
        '6':{'offline':'CLOSED','live':'BLOCKED','basis':'564 focal/route/fail-closed/context/export tests passed; previous3382 not rerun. No complete percentage or freeze.'}})
    code_paths=[
        'backend/evaluators/ansiedad_semantic/functional_review.py',
        'backend/evaluators/ansiedad_semantic/gd_component_review.py',
        'backend/evaluators/ansiedad_semantic/guardrail_review.py',
        'backend/evaluators/ansiedad_semantic/closure6_context_notes.py',
        'backend/evaluators/ansiedad_semantic/closure6_complete_offline.py',
        'backend/evaluators/ansiedad_semantic/closure6_seal_offline.py',
        'tests/ansiedad_semantic/test_closure6_offline_contrasts.py',
        'tests/ansiedad_semantic/test_closure6_delivery.py']
    save('code_hashes.json',[{'path':p,'sha256':sha256(Path(p).read_bytes()).hexdigest(),'bytes':Path(p).stat().st_size} for p in code_paths])
    save('summary.json',{'offline_complete':True,'freeze_verdict':'NO APTO','api_calls':0,'api_incremental_usd':'0',
        'contextual_reviews':81,'families':9,'critical_alerts_audited':5,'original_blocks_audited':6,
        'literal_references_checked':181,'literal_errors':0,'new_semantic_certifications':0,
        'focal_tests_passed':564,'focal_test_exit_code':read(OUT/'focused_command.json')['exit_code'],
        'full_regression_repeated':False,'prior_full_passed':3382,
        'essential_prepared_paid_calls':sum(len(p['calls']) for p in essential),'essential_configured_max_usd':str(amount),
        'financial_state':read(OUT/'ledger_reconciliation_unchanged.json')['binding_accounting'],
        'remaining_offline_defects_demonstrated_but_unfixed':[],
        'qualification':'Offline completion means the current analysis/preparation requirements are exhausted, not real-reader validation, full coverage or freezing.'})
    print(json.dumps({'offline_complete':True,'essential_calls':sum(len(p['calls']) for p in essential),'configured_bound':str(amount),'api_calls':0}))

if __name__=='__main__':run()
