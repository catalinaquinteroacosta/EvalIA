"""Batch correction of action follow-up versus initial emergency guidance."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.closure_run import OUT,read,write,context
from crisis_semantic.domain import load_contracts,package_codes
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.span_provider import SpanProvider,fingerprint,CERTIFICATE
from crisis_semantic.pipeline import CrisisEvaluator

DEST=OUT.parent/'resolution8'

def run(allow_api=False):
    contracts,_,_=load_contracts();baseline=read(DEST/'component_baseline.json')
    current=definitions(contracts,list(contracts))
    changed=[k for k in current if current[k]!=baseline['definitions'][k]]
    assert changed==['CR-AC9.b'],changed
    primary=read(OUT/'final_comparison.json');conversation=read(OUT/'conversation_api_attempt.json')
    proof=read(CERTIFICATE)
    assert proof['fingerprint'] in (baseline['fingerprint'],fingerprint())
    for code,checks in proof['components'].items():
        assert all(baseline['definitions'][k]==v for k,v in definitions(contracts,[code]).items())
        for check in checks:
            row=next(r for b in primary['reports'] if b['case']==check['case'] for r in b['evaluation']['results'] if r['code']==code)
            assert (row['score'] if row['status']=='SCORED' else row['status'])==check['expected']
    proof.update(fingerprint=fingerprint(),ac9_revision={'changed_predicates':changed,'qualification_predicates_unchanged':True,'previous_fingerprint':baseline['fingerprint']})
    write(CERTIFICATE,proof)
    jobs=[(name,b) for name,data in [('primary',primary),('conversation',conversation)] for b in data['reports'] if b['package']=='P3']
    def evaluate(job):
        name,batch=job;ctx=context(batch['context'])
        path=DEST/f"ac9_{name}_{batch['case']}_{ctx.current.number}.json"
        if path.exists() and read(path)['fingerprint']==fingerprint():return name,batch,read(path)['evaluation']
        provider=SpanProvider(allow_api=allow_api)
        provider.seed={k:v for r in batch['evaluation']['results'] if r['code']!='CR-AC9' for k,v in r.get('verified_decisions',{}).items()}
        print('AC9 PACKAGE',name,batch['case'],ctx.current.number,flush=True)
        result=CrisisEvaluator(provider).evaluate(ctx,package_codes(contracts,'P3'))
        write(path,{'fingerprint':fingerprint(),'context':ctx.payload(),'evaluation':result})
        return name,batch,result
    transitions=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for name,batch,result in pool.map(evaluate,jobs):
            old=next(r for r in batch['evaluation']['results'] if r['code']=='CR-AC9')
            new=next(r for r in result['results'] if r['code']=='CR-AC9')
            transitions.append({'corpus':name,'case':batch['case'],'turn':batch['context']['current_turn'],'before':{'status':old['status'],'score':old['score']},'after':{'status':new['status'],'score':new['score']},'decisions':new.get('verified_decisions',{})})
            batch['evaluation']=result
    primary.update(fingerprint=fingerprint(),qualification=proof,statuses=dict(Counter(r['status'] for b in primary['reports'] if not b['extra'] for r in b['evaluation']['results'])))
    rows=[r for b in conversation['reports'] for r in b['evaluation']['results']]
    conversation.update(fingerprint=fingerprint(),statuses=dict(Counter(r['status'] for r in rows)),blocked_causes=dict(Counter(r['technical_cause'] for r in rows if r['status']=='BLOCKED')),complete=all(r['status']!='BLOCKED' for r in rows))
    write(OUT/'final_comparison.json',primary);write(OUT/'conversation_api_attempt.json',conversation)
    write(DEST/'ac9_revision.json',{'changed_predicates':changed,'transitions':transitions,'qualification':proof,'clinical_validation':False})
    print([(r['case'],r['turn'],r['before'],r['after']) for r in transitions])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--allow-api',action='store_true');run(parser.parse_args().allow_api)
