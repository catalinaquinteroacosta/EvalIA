"""Re-evaluate whole OP+CE+GA packages with scoped external evidence."""
import argparse
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.closure_run import OUT,read,write,context
from crisis_semantic.closure_sources import SourceBackedProvider,bundle,SOURCES
from crisis_semantic.domain import load_contracts,package_codes
from crisis_semantic.pipeline import CrisisEvaluator

def run(allow_api=False):
    data=read(OUT/'comparison.json');contracts,_,_=load_contracts()
    for report in data['reports']:
        if report['package']!='P4' or report['case'] not in ('ordinary_support','imminent_safe','history_consistent_control'):continue
        ctx=context(report['context']);reference=bundle(report['case'],ctx)
        provider=SourceBackedProvider(reference,allow_api=allow_api)
        provider.reusable_regressions={'CR-CE10','CR-RI2'}
        provider.seed={k:v for r in report['evaluation']['results'] for k,v in r.get('verified_decisions',{}).items() if v['value'] is not None}
        print('START sources',report['case'],'P4',flush=True)
        report['evaluation']=CrisisEvaluator(provider,external_attestations=('CR-OP3.a',)).evaluate(ctx,package_codes(contracts,'P4'))
        report['external_provenance']=reference
        report['external_attestations']=['CR-OP3.a']
        print('DONE',dict(Counter(r['status'] for r in report['evaluation']['results'])),flush=True)
    data['statuses']=dict(Counter(r['status'] for b in data['reports'] if not b['extra'] for r in b['evaluation']['results']))
    data['usage']=provider.store.summary()
    write(OUT/'external_sources.json',SOURCES)
    write(OUT/'comparison_with_sources.json',data)
    print(data['statuses'],data['usage']['estimated_cost_usd'])
    return data

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--allow-api',action='store_true');run(parser.parse_args().allow_api)
