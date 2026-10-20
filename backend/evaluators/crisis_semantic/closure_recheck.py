"""Common focus/contrary-conduct correction, complete affected packages and controls."""
import argparse
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.closure_run import OUT,read,write,context
from crisis_semantic.closure_sources import SourceBackedProvider
from crisis_semantic.domain import load_contracts,package_codes
from crisis_semantic.pipeline import CrisisEvaluator
from crisis_semantic.span_provider import SpanProvider,fingerprint,CERTIFICATE
from crisis_semantic.scoring import resolve_score

def run(allow_api=False):
    path=OUT/'comparison_with_sources.json'
    data=read(path);contracts,_,_=load_contracts()
    affected={'judgmental_question':{'CR-NI8'},'false_rescue_dependency':{'CR-GA10'},'prompt_injection':{'CR-CT4'},'unsupported_diagnosis':{'CR-OP1'},'ordinary_support':{'CR-NI8','CR-GA10','CR-CT4','CR-OP1'},'imminent_safe':{'CR-NI8','CR-GA10','CR-CT4','CR-OP1'}}
    for report in data['reports']:
        codes=package_codes(contracts,report['package']);reread=affected.get(report['case'],set()) & set(codes)
        if not reread:continue
        cache=OUT/('recheck_'+report['case']+'_'+report['package']+'.json')
        if cache.exists() and read(cache).get('fingerprint')==fingerprint():
            report['evaluation']=read(cache)['evaluation'];continue
        provider=SourceBackedProvider(report['external_provenance'],allow_api=allow_api) if report.get('external_provenance') else SpanProvider(allow_api=allow_api)
        provider.reusable_regressions={'CR-RI2','CR-CE10'}
        provider.qualified_components=set(data['qualification']['components'])
        provider.seed={k:v for r in report['evaluation']['results'] if r['code'] not in reread for k,v in r.get('verified_decisions',{}).items()}
        print('FOCUS',report['case'],report['package'],sorted(reread),flush=True)
        report['evaluation']=CrisisEvaluator(provider,external_attestations=report.get('external_attestations',())).evaluate(context(report['context']),codes)
        write(cache,{'fingerprint':fingerprint(),'evaluation':report['evaluation']})
    proof=data['qualification'];proof['fingerprint']=fingerprint()
    for batch in data['reports']:
        for row in batch['evaluation']['results']:
            if row['code'] in proof['components'] and str(row.get('technical_cause')).startswith('known_live_semantic_regression'):
                facts={k.split('.',1)[1]:v['value'] for k,v in row['verified_decisions'].items()}
                score,cause=resolve_score(row['code'],facts,contracts)
                if score is not None:row.update(status='SCORED',score=score,technical_cause=cause,official_descriptor=contracts[row['code']]['levels'][str(score)]['text'])
    for code,checks in list(proof['components'].items()):
        for check in checks:
            batch=next(b for b in data['reports'] if b['case']==check['case'] and any(r['code']==code for r in b['evaluation']['results']))
            row=next(r for r in batch['evaluation']['results'] if r['code']==code)
            check['actual']=row['score'] if row['status']=='SCORED' else row['status'];check['passed']=check['actual']==check['expected']
        if not all(c['passed'] for c in checks):del proof['components'][code]
    write(CERTIFICATE,proof)
    data['fingerprint']=fingerprint()
    data['statuses']=dict(Counter(r['status'] for b in data['reports'] if not b['extra'] for r in b['evaluation']['results']))
    data['usage']=provider.store.summary()
    write(OUT/'final_comparison.json',data)
    print(data['statuses'],data['usage']['estimated_cost_usd'])
    return data

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--allow-api',action='store_true');run(parser.parse_args().allow_api)
