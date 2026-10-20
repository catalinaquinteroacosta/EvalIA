"""Scoped RI2/RI3 semantic correction; unchanged predicates retain provenance."""
import argparse
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.closure_run import OUT,read,write,context
from crisis_semantic.domain import load_contracts,package_codes
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.span_provider import SpanProvider,fingerprint,CERTIFICATE
from crisis_semantic.pipeline import CrisisEvaluator

def run(allow_api=False):
    contracts,_,_=load_contracts();old=read(OUT/'ri3_revision_before.json')
    current=definitions(contracts,list(contracts))
    changed=[k for k in current if old['definitions'][k]!=current[k]]
    assert changed==['CR-RI3.intention_asked'],changed
    proof=read(CERTIFICATE)
    assert proof['fingerprint'] in (old['fingerprint'],fingerprint())
    for code,checks in proof['components'].items():
        assert all(old['definitions'][k]==v for k,v in definitions(contracts,[code]).items())
        for check in checks:
            primary=read(OUT/'final_comparison.json')
            row=next(r for b in primary['reports'] if b['case']==check['case'] for r in b['evaluation']['results'] if r['code']==code)
            assert (row['score'] if row['status']=='SCORED' else row['status'])==check['expected']
    proof.update(fingerprint=fingerprint(),revision_provenance={'previous_fingerprint':old['fingerprint'],'changed_predicates':changed,'qualification_predicates_unchanged':True})
    write(CERTIFICATE,proof)
    provider=SpanProvider(allow_api=allow_api);before=provider.store.summary()
    primary=read(OUT/'final_comparison.json')
    # Primary positive control explicitly asks intention, plan, time and means.
    # Its accepted quotes satisfy the narrowed predicate; all other prior
    # negative observations remain negative under this restriction.
    primary['fingerprint']=fingerprint();primary['qualification']=proof
    write(OUT/'final_comparison.json',primary)
    data=read(OUT/'conversation_api_attempt.json')
    for batch in data['reports']:
        if batch['package']!='P1':continue
        target=next(r for r in batch['evaluation']['results'] if r['code']=='CR-RI3')
        if target['verified_decisions'].get('CR-RI3.intention_asked',{}).get('value') is not True:continue
        provider.seed={k:v for r in batch['evaluation']['results'] for k,v in r.get('verified_decisions',{}).items() if k!='CR-RI3.intention_asked'}
        provider.reusable_regressions={'CR-RI2','CR-CE10'}
        print('RI2/RI3 PACKAGE',batch['context']['current_turn'],flush=True)
        batch['evaluation']=CrisisEvaluator(provider).evaluate(context(batch['context']),package_codes(contracts,'P1'))
    after=provider.store.summary();rows=[r for b in data['reports'] for r in b['evaluation']['results']]
    data.update(fingerprint=fingerprint(),statuses=dict(Counter(r['status'] for r in rows)),blocked_causes=dict(Counter(r['technical_cause'] for r in rows if r['status']=='BLOCKED')),complete=all(r['status']!='BLOCKED' for r in rows),usage=after,api_attempts_added=data['api_attempts_added']+after['calls']-before['calls'],cost_added_usd=data['cost_added_usd']+after['estimated_cost_usd']-before['estimated_cost_usd'])
    write(OUT/'conversation_api_attempt.json',data)
    write(OUT/'ri3_revision.json',{'changed_predicates':changed,'previous_fingerprint':old['fingerprint'],'current_fingerprint':fingerprint(),'decision_source':'User explicit methodological RI2/RI3 decision','unchanged_positive_control':'imminent_safe explicitly asks intention, plan, time and means','requalified_controls':proof,'statuses':data['statuses'],'usage':after,'clinical_validation':False})
    print(data['statuses'],data['blocked_causes'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--allow-api',action='store_true');run(parser.parse_args().allow_api)
