"""Authorized anxiety-only units, bounded by the remaining conservatively covered cash.

No implicit retries. Outputs and ledger remain append-only. Review between units
is performed by the assistant, never an automatic ordinal expectation.
"""
import json,sys
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
from .budgeted_reader import Reader,estimate,ROOT,canonical
from .technical_validation import prepare
from .step5a_continue import cash
from .claim_verifier import verification_request
from .cash_safe_transport import prepared_https_transport
from . import component_routes as routes,em_component_adapter as em
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

WORK=Path('docs/ansiedad_semantic/closure6_20261013')
BASE=WORK/'offline_04'
LIVE=WORK/'integral_live'
MODEL='gpt-4.1-2025-04-14'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,value):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)

def authorization():
    LIVE.mkdir(exist_ok=True)
    p=LIVE/'authorization.json'
    newer=LIVE/'continuation_1501/authorization.json'
    if newer.exists():return read(newer)
    if p.exists():return read(p)
    auth={'explicit_user_approval':True,'authorization_id':'ANXIETY-20261013-INTEGRAL-REMAINING-CASH',
        'additional_cap_usd':str(max(Decimal(0),cash())),'outstanding_reservations_usd':'0',
        'extraction_model':MODEL,'verification_model':MODEL,
        'authority':'User explicitly authorizes pending requests and necessary anxiety completion work, without further per-indicator budget requests. Self-imposed cash ceiling preserves all historical holds and costs, based on confirmed USD4; not unlimited spending.',
        'no_shared_cache':True,'historical_holds_released':0}
    save(p,auth);return auth

def source(unit):
    if unit=='CE3-grounded-verify':
        d=read(LIVE/'continuation_1501/CE3_extraction_recovered.json')
        return {'id':unit,'codes':['CE3'],'original':d['request']['original']},d['reading']
    if unit in ('CE3-grounded','CE3-grounded-verify'):
        case,_=source('CE3-functional')
        return {**case,'id':unit},None
    if unit=='GD7-only':
        case,_=source('critical-GD2')
        return {**case,'id':unit,'codes':['GD7']},None
    if unit=='PA3-adjudicated':
        d=read(LIVE/'critical-PA3_02/independent_verify.json')
        return {'id':unit,'codes':['PA3'],'original':d['request']['original']},{'_reuse_stage':'independent_verify','reading':d['reading']}
    if unit=='IR2':
        a=read(WORK/'continue_5A_IR2/extract.json')
        return {'id':unit,'codes':['IR2'],'original':a['request']['original']},a['reading']
    if unit=='CEscope':
        a=read(WORK/'continue_5A_CE3/extract.json')
        return {'id':unit,'codes':['CE3','CE9'],'original':a['request']['original']},None
    if unit=='CE3-functional':
        a=read(WORK/'continue_5A_CE3/extract.json')
        return {'id':unit,'codes':['CE3'],'original':a['request']['original']},None
    if unit.startswith('IR-omission'):
        rows=read('docs/ansiedad_semantic/finish_20261013/final_02/tables/observations.json')
        r=next(r for r in rows if r['case']=='IR-omission' and r['code']=='IR1')
        d=read(r['source']);codes=['IR'+str(i) for i in range(1,9)]
        if ':' in unit:codes=unit.split(':')[1].split(',')
        return {'id':unit,'codes':codes,'original':d['case']['original']},None
    if unit.startswith('negative-'):
        code=unit.split('-',1)[1]
        if code not in ['CP8','CE4','CE5','CE6','CE10','PS8']:raise ValueError('Unregistered negative case')
        d=read(Path('docs/ansiedad_semantic/finish_20261013/step2_coverage_02')/('coverage-'+code+'-0.json'))
        return {'id':unit,'codes':[code],'original':d['case']['original']},None
    if unit.startswith('CEverify'):
        d=read('docs/ansiedad_semantic/finish_20261013/step3_engine_01/call_17.json')
        codes=list(d['reading']['indicators'])
        if ':' in unit:codes=unit.split(':')[1].split(',')
        assert set(codes)<=set(d['reading']['indicators'])
        return {'id':unit,'codes':codes,'original':d['request']['original']},{'indicators':{c:d['reading']['indicators'][c] for c in codes}}
    group=next(g for g in read(BASE/'VALIDATION_PLAN_MINIMUM.json')['plans'] if g['id']==unit)
    q=read(BASE/group['calls'][0]['request'])
    return {'id':unit,'codes':group['codes'],'original':q['original']},None

def run(unit,version):
    auth=authorization();case,reuse=source(unit)
    out=LIVE/(unit.replace(':','_').replace(',','_')+'_'+version);out.mkdir(exist_ok=False)
    requests=prepare(case)
    for q in requests:
        q['_max_output_tokens']=min(28000,max(4000,sum(len(v['components']) for v in q['indicators'].values())*240))
        q['instruction']+=' Distingue omisión de conducta contraria y defecto principal de secundario. Para CE3/CE9 examina estructura real, sin pertinencia temática. No selecciones notas.'
    if unit in ('CE3-grounded','CE3-grounded-verify'):
        from .ce3_relation_grounding import request_with_relation_audit
        requests=[request_with_relation_audit(q) for q in requests]
    if reuse is not None:
        requests=[q for q in requests if q['stage']==('extract' if reuse.get('_reuse_stage')=='independent_verify' else 'independent_verify')]
        # IR2 is a targeted claim check. CE reuses the extraction in Python;
        # its verifier remains blind to it to avoid re-reading huge proposals.
        if unit=='IR2':requests=[verification_request(q,reuse) for q in requests]
    plan=[{'stage':q['stage'],'estimate':estimate(q,MODEL),'request_sha256':sha256(canonical(q).encode()).hexdigest()} for q in requests]
    for q in requests:save(out/(q['stage']+'_request.json'),q)
    save(out/'plan.json',{'unit':unit,'original_sha256':case['original']['input_sha256'],'requests':plan,
        'free_cash_before_usd':str(cash()),'reuse_extraction':reuse is not None and reuse.get('_reuse_stage')!='independent_verify',
        'reuse_verification_source':str(LIVE/'critical-PA3_02/independent_verify.json') if unit=='PA3-adjudicated' else None,
        'blind_CE_verifier':unit.startswith('CEverify')})
    required=sum((Decimal(p['estimate']['reserved_upper_bound_usd']) for p in plan),Decimal(0))
    result=None;stop=None;before_events=len((ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines())
    try:
        if required>cash():raise PermissionError('Insufficient conservatively covered cash for this complete unit; no paid call')
        provider=Reader(auth);a=reuse
        if reuse is not None and reuse.get('_reuse_stage')=='independent_verify':
            b=reuse['reading'];a=None
        for q,p in zip(requests,plan):
            if Decimal(p['estimate']['reserved_upper_bound_usd'])>cash():raise PermissionError('Cash changed before request')
            print(json.dumps({'unit':unit,'stage':q['stage'],'max_usd':p['estimate']['reserved_upper_bound_usd']}),flush=True)
            # Resolve before creating any paid reservation. Pin TCP address
            # while retaining normal TLS hostname verification and HTTP Host.
            provider.transport=prepared_https_transport()
            r=provider(q);save(out/(q['stage']+'.json'),{'request':q,'reading':r})
            if q['stage']=='extract':a=r
            else:b=r
        o=case['original'];ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
        if unit in ('CE3-grounded','CE3-grounded-verify'):
            from .ce3_relation_grounding import validate_relation_reading
            for reading in (a,b):validate_relation_reading(o,reading)
        result={c:(em.adjudicate(c,ctx,a['indicators'][c],b['indicators'][c]) if c.startswith('EM') else routes.adjudicate(c,ctx,a['indicators'][c],b['indicators'][c])) for c in case['codes']}
        save(out/'adjudication.json',result)
        if any(r['status']=='BLOCKED' for r in result.values()):stop='Needs offline diagnosis; no automatic paid retry'
    except Exception as e:stop=type(e).__name__+': '+str(e)
    es=[json.loads(s) for s in (ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    fresh=es[before_events:];attempts=[r for r in fresh if r['kind']=='reserved'];settled={r['attempt']:r for r in es if r['kind']=='settled'}
    summary={'unit':unit,'stop':stop,'results':result,'new_attempts':len(attempts),
        'new_usage_usd':str(sum((Decimal(settled[r['attempt']]['actual_usd']) for r in attempts if r['attempt'] in settled),Decimal(0))),
        'new_uncertain_reserves_usd':str(sum((Decimal(r['reserved_usd']) for r in attempts if r['attempt'] not in settled),Decimal(0))),
        'free_cash_after_usd':str(cash()),'freeze':'NO APTO until all required checks pass'}
    save(out/'summary.json',summary)
    print(json.dumps({'unit':unit,'stop':stop,'results':[(c,r['status'],r['score']) for c,r in (result or {}).items()],'free_cash':str(cash())}),flush=True)

if __name__=='__main__':run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else '01')
