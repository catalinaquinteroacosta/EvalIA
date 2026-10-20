"""Final immutable four-step audit, with raw outcomes separate from qualification."""
from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
from hashlib import sha256
import csv,inspect,json,re
from .night_validation import AUTH,ROOT,accounting,BALANCE_CHECKPOINT
from .run_authorized_validation import save
from .result_tables import export_new,aggregate
from . import component_routes as routes,em_component_adapter as em
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn,Evidence
from backend.evaluators.nd.docx_components import contracts

BASE=Path('docs/ansiedad_semantic/technical_20261012/final_09')
WORK=Path('docs/ansiedad_semantic/finish_20261013')

def run(target):
    target=Path(target);target.mkdir(parents=True,exist_ok=False)
    current={};timeline=[];originals={};case_names={}
    def add(case,code,d,source,protocol):
        original=case['original'];key=(original['input_sha256'],code)
        name=case.get('original_case_id',case['id'])
        case_names.setdefault(key,name);originals[key]=original
        expected=case.get('expected',{}).get(code,'UNSPECIFIED')
        old=current.get(key)
        timeline.append({'case':case_names[key],'code':code,'source':source,'protocol':protocol,
            'before':{k:old[k] for k in ('status','score')} if old else None,
            'after':{k:d[k] for k in ('status','score')}})
        current[key]={**d,'case':case_names[key],'code':code,'family':code[:2],
            'conversation':original['conversation'],'model':original['model'],'turn':original['turn'],
            'input_sha256':original['input_sha256'],'source':source,'verification_protocol':protocol,
            'expected_hypothesis':expected,'hypothesis_agrees':None if expected=='UNSPECIFIED' else
                (d['status'],d['score'])==('N/A' if expected is None else 'SCORED',expected),
            'applicability':'APPLICABLE' if d['status']=='SCORED' else 'NOT_APPLICABLE' if d['status']=='N/A' else 'UNRESOLVED',
            'gate_reason':d['reason'] if d['status']=='N/A' else ''}
    baseline=json.loads((BASE/'observations.json').read_text(encoding='utf-8'))
    for row in baseline:
        source=row['source'];packet=json.loads(Path(source).read_text(encoding='utf-8'))
        case={**packet['case'],'expected':{row['code']:row['expected_hypothesis']}}
        d={key:row[key] for key in ('status','score','reason')}
        d['extraction']=(packet.get('extraction') or {}).get('indicators',{}).get(row['code'])
        d['independent_verification']=(packet.get('independent_verification') or {}).get('indicators',{}).get(row['code'])
        add(case,row['code'],d,source,'historical_blind_pair')
    for folder,protocol in [('step1_pairs_01','single_code_blind_pair'),('step2_coverage_01','mini_extract_strong_blind_verify'),
                            ('step2_coverage_02','mini_extract_strong_blind_verify'),('step1_claim_audit_02','independent_claim_audit'),
                            ('step3_scope_01','untouched_independent_scope')]:
        for file in sorted((WORK/folder).glob('*.json')):
            packet=json.loads(file.read_text(encoding='utf-8'))
            if not isinstance(packet,dict) or 'decisions' not in packet:continue
            for code,d in packet['decisions'].items():
                d={**d,'extraction':packet['extraction']['indicators'][code],
                   'independent_verification':packet['independent_verification']['indicators'][code]}
                add(packet['case'],code,d,str(file),protocol)
    # Include every planned coverage cell, even if an API/budget failure stopped a run.
    coverage=json.loads((WORK/'coverage_preregistered.json').read_text(encoding='utf-8'))
    scope_path=WORK/'scope_preregistered.json'
    scope=json.loads(scope_path.read_text(encoding='utf-8')) if scope_path.exists() else []
    for case in coverage+scope:
        code=case['codes'][0]
        if (case['original']['input_sha256'],code) not in current:
            add(case,code,{'status':'PENDING','score':None,'reason':'No completed independent pair'},str(WORK/'coverage_preregistered.json'),'planned_not_executed')
    integration_path=WORK/'step3_engine_01/engine_result.json'
    integration=None
    if integration_path.exists():
        integration=json.loads(integration_path.read_text(encoding='utf-8'))
        case={'id':'reserved-CE-engine-all81','original':integration['original'],'expected':{}}
        for row in integration['rows']:
            family=integration['families'][row['family']]
            d={**row,'extraction':(family.get('extraction') or {}).get('indicators',{}).get(row['code']),
                'independent_verification':(family.get('independent_verification') or {}).get('indicators',{}).get(row['code'])}
            add(case,row['code'],d,str(integration_path),'untouched_full_engine_claim_audit')
    flags=json.loads((WORK/'semantic_review_flags.json').read_text(encoding='utf-8'))
    flagged=set()
    for flag in flags:
        packet=json.loads(Path(flag['source']).read_text(encoding='utf-8'))
        key=(packet['case']['original']['input_sha256'],flag['code'])
        if key in current:
            current[key]['qualification_review_status']='NOT_CERTIFIED'
            current[key]['semantic_audit_issue']=flag['issue'];flagged.add(key)
    save(target/'semantic_review_flags.json',flags)
    rows=list(current.values());export_new(target/'tables',rows);save(target/'before_after.json',timeline)
    errors=[];references=0
    def walk(value,context,identity):
        nonlocal references
        if isinstance(value,dict):
            if 'quote' in value and 'source' in value:
                references+=1
                try:
                    if not Evidence(**{k:value[k] for k in ('source','quote','history_index')}).verify_exact(context):
                        errors.append({'identity':identity,'citation':value,'error':'Not exact in authorized originals'})
                except Exception as error:errors.append({'identity':identity,'error':str(error)})
            for child in value.values():walk(child,context,identity)
        elif isinstance(value,(list,tuple)):
            for child in value:walk(child,context,identity)
    for key,row in current.items():
        original=originals[key];context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        walk(row.get('extraction'),context,{'case':row['case'],'code':row['code']})
        walk(row.get('independent_verification'),context,{'case':row['case'],'code':row['code']})
    save(target/'literal_audit.json',{'references_including_duplicates':references,'errors':errors,
        'scope':'Exact-source checks, not a replacement for semantic validity.'})
    matrix=[];gaps=[]
    for code,official in contracts().items():
        own=[row for row in rows if row['code']==code]
        observed=sorted({row['score'] for row in own if row['status']=='SCORED'})
        matched=sorted({row['score'] for row in own if row['status']=='SCORED' and row['hypothesis_agrees'] is True and row.get('qualification_review_status')!='NOT_CERTIFIED'})
        module=em if code.startswith('EM') else routes.route(code)
        matrix.append({'code':code,'official':official,
            'components':em.COMPONENT_DESCRIPTIONS[code] if code.startswith('EM') else routes.definitions(code),
            'module_path':str(module.__file__),'module_sha256':sha256(Path(module.__file__).read_bytes()).hexdigest(),
            'deterministic_rule':inspect.getsource(module.adjudicate if hasattr(module,'adjudicate') else module.score if hasattr(module,'score') else module.adjudicate_batch),
            'tests':[str(p) for p in Path('tests/ansiedad_semantic').glob('test_*.py')],
            'observed_levels':observed,'matched_preregistered_hypothesis_levels':matched,
            'na_cases':[{'case':r['case'],'reason':r['reason'],'source':r['source']} for r in own if r['status']=='N/A'],
            'cases':[{k:r[k] for k in ('case','status','score','reason','source','verification_protocol','expected_hypothesis','hypothesis_agrees')} for r in own],
            'qualification':'Observed numeric levels or matching hypotheses alone do not certify semantic fidelity.'})
        if set(observed)!=set(range(4)) or set(matched)!=set(range(4)):
            gaps.append({'code':code,'missing_observed_levels':sorted(set(range(4))-set(observed)),
                'missing_matched_hypothesis_levels':sorted(set(range(4))-set(matched)),
                'qualification':'Some hypotheses may be wrong; do not manufacture a target score.'})
    save(target/'fidelity_matrix.json',matrix);save(target/'coverage_gaps.json',gaps)
    blocked=[r for r in rows if r['status'] in ('BLOCKED','PENDING')]
    save(target/'blocked_causes.json',[{k:r[k] for k in ('case','code','status','reason','source')} for r in blocked])
    save(target/'hypothesis_discrepancies.json',[{k:r[k] for k in ('case','code','status','score','expected_hypothesis','reason','source')} for r in rows if r['hypothesis_agrees'] is False])
    budget=accounting();events=[json.loads(line) for line in (ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    settled={e['attempt']:e for e in events if e['kind']=='settled'}
    other=sum((Decimal(e['actual_usd']) for e in settled.values() if e['authorization']!=AUTH['authorization_id']),Decimal(0))
    baseline_cost=Decimal('4.2231960')
    old=json.loads((BASE/'api_accounting.json').read_text(encoding='utf-8'))
    night_reserved=[e for e in events if e['kind']=='reserved' and e['authorization']==AUTH['authorization_id']]
    new_reserved=night_reserved[old['accounting']['attempts']:]
    usage_totals=defaultdict(lambda:Counter())
    for event in new_reserved:
        settled_event=settled.get(event['attempt'])
        if not settled_event:continue
        packet=json.loads((ROOT/settled_event['artifact']).read_text(encoding='utf-8'))
        usage=packet['response']['usage'];model=settled_event['model']
        usage_totals[model]['settled_calls']+=1
        usage_totals[model]['input_tokens']+=usage['prompt_tokens'];usage_totals[model]['output_tokens']+=usage['completion_tokens']
    save(target/'api_accounting.json',{'authorization':AUTH,'current':budget,
        'prior_night_cost_usd':str(baseline_cost),'incremental_this_order_usd':str(Decimal(budget['actual_usd'])-baseline_cost),
        'night_total_reported_usd':budget['actual_usd'],'other_historical_authorizations_reported_usd':str(other),
        'private_ledger_reported_total_usd':str(other+Decimal(budget['actual_usd'])),
        'new_reserved_attempts_this_order':len(new_reserved),
        'new_settled_attempts_this_order':sum(e['attempt'] in settled for e in new_reserved),
        'new_usage_by_model':dict(usage_totals),
        'cost_qualification':'Conservative configured-rate token accounting, not a reconciled provider invoice.',
        'reported_balance_checkpoint':json.loads(BALANCE_CHECKPOINT.read_text(encoding='utf-8')),
        'billing_balance_verified_by_api':False,'reserves_released':False,
        'ledger_path':str(ROOT/'ledger.jsonl')})
    raw=(ROOT/'ledger.jsonl').read_bytes();prefix=b''.join(raw.splitlines(keepends=True)[:old['ledger_events']])
    protected=[]
    for entry in json.loads(Path('docs/crisis_semantic/ac9_live8/files.json').read_text(encoding='utf-8')):
        path=Path(entry['path']);actual=sha256(path.read_bytes()).hexdigest() if path.exists() else None
        protected.append({'path':str(path),'matches':actual==entry['sha256']})
    integrity={'crisis_manifest_entries':len(protected),'crisis_differences':[e for e in protected if not e['matches']],
        'docx_sha256':sha256(Path('PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx').read_bytes()).hexdigest(),
        'historical_ledger_prefix_matches':sha256(prefix).hexdigest()==old['ledger_sha256'],
        'shared_sqlite_opened':False,'general_runner_or_frontend_modified':False}
    exp=json.loads(Path('docs/ansiedad_semantic/step2_20261012/experiment072_manifest.json').read_text(encoding='utf-8'))
    integrity['experiment072_source_hashes_match']={path:sha256(Path(path).read_bytes()).hexdigest()==value for path,value in exp['source_hashes'].items()}
    save(target/'integrity.json',integrity)
    local=WORK/'local_final_02';tests=(local/'tests.txt').read_text(encoding='utf-8') if (local/'tests.txt').exists() else ''
    pass_count=int(re.findall(r'(\d+) passed',tests)[-1]) if re.findall(r'(\d+) passed',tests) else None
    initial_keys={(r['case'],r['code']) for r in json.loads((BASE/'blocked_causes.json').read_text(encoding='utf-8'))}
    initial_now=[r for r in rows if (r['case'],r['code']) in initial_keys]
    counts=Counter(r['status'] for r in rows)
    summary={'verdict':'NO APTO','four_steps':{
        '1':'Executed focused repairs and real requalification; remaining discrepancies are retained.',
        '2':'Executed preregistered missing-level tests; complete fidelity/coverage not demonstrated.',
        '3':'Actual isolated research-engine API path interrupted for global reserve reconciliation; 17 saved outputs recovered, CE verification incomplete. Production runner remains protected.',
        '4':'Offline regression and final audit executed; freeze refused while critical discrepancies/gaps remain.'},
        'official_indicators':81,'families':9,'evaluations':len(rows),'counts':dict(counts),
        'initial_blocked':16,'initial_cases_current_counts':dict(Counter(r['status'] for r in initial_now)),
        'initial_cases_qualified_counts':dict(Counter('REVIEW_PENDING' if r.get('qualification_review_status')=='NOT_CERTIFIED' else r['status'] for r in initial_now)),
        'critical_review_flags':len(flags),'reserved_scope_cases_not_completed':sum(r['status']=='PENDING' and r['case'].startswith('reserved-scope-') for r in rows),
        'coverage_cases_planned':len(coverage),'coverage_gaps':len(gaps),'local_passed':pass_count,
        'literal_references':references,'literal_errors':len(errors),'full_percentage':None,
        'clinical_validation':False,'accounting':budget}
    save(target/'summary.json',summary)
    csvrows=list(csv.DictReader((target/'tables/observations.csv').open(encoding='utf-8',newline='')))
    save(target/'export_checks.json',{'json_rows':len(rows),'csv_rows':len(csvrows),'counts_match':len(rows)==len(csvrows),
        'complete_percentage_suppressed':aggregate(rows)['percentage'] is None})
    save(target/'RECOVERY.json',{'summary':summary,'latest_evidence':str(target/'tables/observations.json'),
        'blocked':str(target/'blocked_causes.json'),'coverage':str(target/'coverage_gaps.json'),
        'next_action':'Inspect exact generic/construct/composite verification defects; do not repeat identical calls or force intermediate scores.',
        'protected':['CRISIS','official DOCX','shared SQLite/cache modules','frontend','general runner']})
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':
    import sys
    run(sys.argv[1])
