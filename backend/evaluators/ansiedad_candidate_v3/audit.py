"""Offline v3 impact audit. No model capability is instantiated or invoked."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,socket,sys
from .engine import verify_frozen,adjudicate,VERSION,FROZEN
from .reader_contract import candidate_request
from backend.evaluators.ansiedad_semantic.ratification_replay import recover_pair
from backend.evaluators.ansiedad_semantic.official_contracts import read_contracts
from backend.evaluators.ansiedad_semantic.result_tables import export_new,aggregate
from backend.evaluators.ansiedad_semantic.budgeted_reader import estimate
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn,Evidence

PAID=Path('docs/ansiedad_semantic/postfreeze_holdout_20261013_01')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):return sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def context(o):return TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
def material(row):
    # Frozen artifacts are JSON; dataclass evidence can be tuples in memory.
    # Compare their actual serialized representation, never erase fact changes.
    return json.loads(json.dumps({k:row.get(k) for k in ('status','score','reason','reviews','evidence','extraction','independent_verification','verification')},ensure_ascii=False))

def run(destination):
    def forbidden(*a,**k):raise RuntimeError('Offline-only candidate audit')
    socket.create_connection=forbidden;socket.socket.connect=forbidden;socket.socket.connect_ex=forbidden
    verify_frozen();out=Path(destination);out.mkdir(parents=True,exist_ok=False)
    baseline=read(FROZEN/'tables/observations.json');rows=[];comparisons=[];literals=[];trace=[]
    for index,old in enumerate(baseline):
        a,b,sources=recover_pair(old);ctx=context(old['original'])
        decision=adjudicate(old['code'],ctx,a,b) if a is not None else {'code':old['code'],'status':'N/A','score':None,'reason':old['reason']}
        row={**deepcopy(old),**decision,'candidate_version':VERSION}
        changed=[k for k in material(old) if material(old)[k]!=material(row)[k]]
        comparisons.append({'row':index,'code':old['code'],'scope':old['validation_scope'],'changed_fields':changed,
            'before':material(old) if changed else None,'after':material(row) if changed else None})
        rows.append(row);trace.append({'cohort':'frozen228','row':index,'sources':[{'path':p,'sha256':digest(p)} for p in sources]})
    export_new(out/'frozen228',rows)
    paid_rows=[];blocked=[];pending_requests=[];paid_comparison=[]
    folders=[PAID,PAID/'candidate_01',PAID/'unexecuted_diagnostic_01',PAID/'nd_candidate_01',PAID/'nd_candidate_02']
    for folder in folders:
        for path in sorted(folder.glob('*_adjudication.json')):
            data=read(path);decisions=[data] if 'code' in data else list(data.values())
            case=path.name.removesuffix('_adjudication.json')
            extract_path=folder/(case+'_extract.json');verify_path=folder/(case+'_independent_verify.json')
            x,y=read(extract_path),read(verify_path);o=x['request']['original'];assert o==y['request']['original']
            ctx=context(o);case_blocked=[]
            for old in decisions:
                code=old['code'];a,b=[r['reading']['indicators'][code] for r in (x,y)]
                raw=adjudicate(code,ctx,a,b);current=deepcopy(raw)
                semantic_invalid=(folder==PAID and case=='em5-exact-knowledge' and code=='EM5')
                if semantic_invalid:
                    current={**current,'status':'BLOCKED','score':None,
                        'reason':'Known audited semantic invalidity: both readers infer appropriation solely from exact-feeling knowledge. Human EM5 adjudication distinguishes these facts; no corrected pair exists for this original.'}
                row={**current,'original':o,'conversation':o['conversation'],'model':o['model'],'turn':o['turn'],'family':code[:2],
                     'candidate_version':VERSION,'cohort':'paid42-known-regression','historical_result_source':str(path),
                     'raw_replayed_status':raw['status'],'raw_replayed_score':raw['score'],
                     'applicability':'APPLICABLE' if current['status']=='SCORED' else 'NOT_APPLICABLE' if current['status']=='N/A' else 'UNRESOLVED',
                     'gate_reason':current['reason'] if current['status']=='N/A' else ''}
                paid_rows.append(row)
                paid_comparison.append({'case':case,'code':code,'historical_status':old['status'],'historical_score':old['score'],
                    'raw_candidate_status':raw['status'],'raw_candidate_score':raw['score'],
                    'ratification_status':current['status'],'ratification_score':current['score'],
                    'reason_or_evidence_changed_in_raw_replay':material(raw)!=material(old)})
                if current['status']=='BLOCKED':
                    differing=[k for k in a['components'] if a['components'][k]['value']!=b['components'][k]['value']]
                    bad=['experience_appropriation'] if semantic_invalid else differing
                    blocked.append({'case':case,'code':code,'historical_status':old['status'],'historical_score':old['score'],
                        'components':bad,'cause_layer':'extractor and verifier semantic interpretation' if semantic_invalid else 'extractor semantic interpretation / reader discrepancy',
                        'historical_record_preserved':True,'contract_root_cause_integrated':True,
                        'evidence_repair_complete_for_this_original':False,
                        'classification':'Avoidable root cause corrected in contract; defective saved evidence still unresolved. Guard blocking is legitimate, but acceptance gap remains.',
                        'current_reason':current['reason'],'sources':[str(extract_path),str(verify_path)]})
                    case_blocked.append(code)
            if case_blocked:
                # Both EM5 readers made the invalid inference; ND verifiers
                # were valid and independently grounded. Reuse them, never edit.
                stages=[('extract',x),('independent_verify',y)] if folder==PAID and case=='em5-exact-knowledge' else [('extract',x)]
                for stage,artifact in stages:
                    q=candidate_request(artifact['request']);q['indicators']={c:q['indicators'][c] for c in case_blocked}
                    assert not any(k in q for k in ('expected','allowed','score'))
                    filename='request_'+str(len(pending_requests)+1).zfill(2)+'.json';save(out/filename,q)
                    pending_requests.append({'case':case,'codes':case_blocked,'stage':stage,'path':str(out/filename),
                        'request_sha256':digest(out/filename),'estimate_configured':estimate(q,'gpt-4.1-2025-04-14'),
                        'reusable_verifier':None if len(stages)==2 else {'path':str(verify_path),'sha256':digest(verify_path)},
                        'not_sent':True,'requires_additional_user_API_authorization':True,
                        'known_regression_not_blind_holdout':True})
    assert len(baseline)==228 and len(paid_rows)==42 and len(blocked)==5 and len(pending_requests)==4
    export_new(out/'paid42',paid_rows);all_rows=rows+paid_rows;export_new(out/'required270',all_rows)
    def audit(value,ctx,index):
        if isinstance(value,dict):
            if 'quote' in value and 'source' in value and not Evidence(value['source'],value['quote'],value.get('history_index')).verify_exact(ctx):literals.append({'row':index,'citation':value})
            for k,v in value.items():
                if k!='original':audit(v,ctx,index)
        elif isinstance(value,list):
            for v in value:audit(v,ctx,index)
    for i,r in enumerate(all_rows):audit(r,context(r['original']),i)
    assert not literals
    save(out/'comparison228.json',comparisons);save(out/'comparison42.json',paid_comparison);save(out/'blocked_audit.json',blocked)
    save(out/'evidence_trace.json',trace)
    save(out/'PENDING_API_NOT_AUTHORIZED.json',{'requests':pending_requests,'calls':4,'evaluations':5,
        'configured_maximum_usd':str(sum(__import__('decimal').Decimal(p['estimate_configured']['reserved_upper_bound_usd']) for p in pending_requests)),
        'rates_are_frozen_configured_not_new_billing_confirmation':True,'new_API_calls':0,'retry_policy':'No automatic retry; review independent components and evidence, not numeric agreement'})
    normative=read_contracts('PUNTAJES EVALUADORES ANSIEDAD(20261008-000023).docx')
    matrix=[]
    for code,c in normative['contracts'].items():
        from backend.evaluators.semantic.em.schemas import COMPONENT_DESCRIPTIONS
        from backend.evaluators.ansiedad_semantic.component_routes import definitions
        definitions_now=COMPONENT_DESCRIPTIONS[code] if c['family']=='EM' else definitions(code)
        altered=candidate_request({'indicators':{code:{'components':deepcopy(definitions_now)}}})['indicators'][code]['components']
        matrix.append({**c,'candidate_components':altered,'component_names_unchanged':set(altered)==set(definitions_now),
            'current_required_rows':[{'status':r['status'],'score':r['score']} for r in all_rows if r['code']==code],
            'not_general_semantic_certification':True})
    save(out/'fidelity81.json',matrix)
    save(out/'SUMMARY.json',{'candidate_version':VERSION,'required':aggregate(all_rows,expected_count=270),
        'frozen228_changes':sum(bool(c['changed_fields']) for c in comparisons),'literal_errors':literals,
        'known_paid_regression_cases':42,'historical_BLOCKED_records_unchanged':4,
        'current_BLOCKED':5,'pending_reverification_calls':4,'new_API_calls':0,'incremental_API_usd':0,
        'decision':'NO_APTO: unresolved independent evidence in mandatory regression corpus; no numeric repairs or exclusions',
        'frozen_unchanged':True,'clinical_validation':False})
    verify_frozen();print(json.dumps(read(out/'SUMMARY.json'),ensure_ascii=True))

if __name__=='__main__':run(sys.argv[1])
