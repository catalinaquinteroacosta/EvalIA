"""Whole-package closure replay. Reuse only unchanged, independently verified predicates."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from crisis_semantic.domain import DOCS, Turn, Input, load_contracts, package_codes
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.pipeline import CrisisEvaluator
from crisis_semantic.span_provider import SpanProvider, fingerprint, CERTIFICATE, MODEL
from crisis_semantic.span_protocol import PROTOCOL
from crisis_semantic.scoring import resolve_score

BASE = DOCS / "step8/89ab272880c4"
OUT = DOCS / "closure8"

def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")
def context(raw):
    return Input(Turn(raw['current_turn'],raw['current_user'],raw['current_ai'],raw['model_evaluated']),tuple(Turn(t['number'],t['user'],t['ai'],t['model']) for t in raw['history']))

def run(allow_api=False):
    old = read(BASE / "comparison_8660c0df2a.json")
    catalog = {k:v for row in read(BASE / "implementation_traceability.json") for k,v in row['predicates'].items()}
    if (OUT/'comparison_before_external_fix.json').exists():
        old=read(OUT/'comparison_before_external_fix.json')
        catalog=read(OUT/'catalog_before_external_fix.json')
    contracts,manifest,common = load_contracts()
    provider = SpanProvider(allow_api=allow_api)
    # This runner requalifies the unchanged RI2/CE10 observations across all fixed
    # controls before writing a new certificate. Raw holds remain until then.
    provider.reusable_regressions = {code for code in ('CR-RI2','CR-CE10') if all(catalog[k] == v for k,v in definitions(contracts,[code]).items())}
    reports = []
    for prior in old['reports']:
        ctx = context(prior['context'])
        defs = definitions(contracts,package_codes(contracts,prior['package']))
        provider.seed = {k:v for row in prior['evaluation']['results'] for k,v in row.get('verified_decisions',{}).items() if k in defs and catalog.get(k) == defs[k]}
        path = OUT / (prior['case']+'_'+prior['package']+'.json')
        if path.exists() and read(path).get('fingerprint') == fingerprint():
            report = read(path)
        else:
            print('START',prior['case'],prior['package'],flush=True)
            report = {'case':prior['case'],'package':prior['package'],'context':prior['context'],'extra':prior['extra'],'fingerprint':fingerprint(),'definitions':defs,'evaluation':CrisisEvaluator(provider).evaluate(ctx,package_codes(contracts,prior['package'])),'checks':prior['checks']}
            write(path,report)
            print('DONE',dict(Counter(r['status'] for r in report['evaluation']['results'])),flush=True)
        reports.append(report)
    proof = {'fingerprint':fingerprint(),'protocol':PROTOCOL,'model':MODEL,'components':{},'clinical_validation':False}
    for code in ('CR-RI2','CR-CE10'):
        checks = []
        for report in reports:
            for check in report['checks']:
                if check['code'] != code: continue
                row = next(r for r in report['evaluation']['results'] if r['code'] == code)
                if row['status'] == 'N/A': actual = 'N/A'
                elif str(row.get('technical_cause')).startswith('known_live_semantic_regression') or row['status'] == 'SCORED':
                    facts = {k.split('.',1)[1]:v['value'] for k,v in row['verified_decisions'].items()}
                    actual = resolve_score(code,facts,contracts)[0]
                else: actual = 'BLOCKED'
                checks.append({'case':report['case'],'code':code,'expected':check['expected'],'actual':actual,'passed':actual == check['expected']})
        if len(checks) == (8 if code == 'CR-RI2' else 2) and all(c['passed'] for c in checks): proof['components'][code] = checks
    write(CERTIFICATE,proof)
    for report in reports:
        for row in report['evaluation']['results']:
            if row['code'] in proof['components'] and str(row.get('technical_cause')).startswith('known_live_semantic_regression'):
                score,cause = resolve_score(row['code'],{k.split('.',1)[1]:v['value'] for k,v in row['verified_decisions'].items()},contracts)
                row.update(status='SCORED',score=score,technical_cause=cause,official_descriptor=contracts[row['code']]['levels'][str(score)]['text'])
        for check in report['checks']:
            row = next(r for r in report['evaluation']['results'] if r['code'] == check['code'])
            check['actual'] = row['score'] if row['status'] == 'SCORED' else row['status']
            check['passed'] = check['actual'] == check['expected']
    rows = [r for b in reports if not b['extra'] for r in b['evaluation']['results']]
    result = {'fingerprint':fingerprint(),'reports':reports,'statuses':dict(Counter(r['status'] for r in rows)),'usage':provider.store.summary(),'qualification':proof,'clinical_validation':False,'step9_started':False,'reused_components':provider.reused_observations,'cache_hits':provider.cache_hits}
    write(OUT / 'comparison.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('reports','qualification')},indent=2))
    return result

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--allow-api',action='store_true')
    run(parser.parse_args().allow_api)
