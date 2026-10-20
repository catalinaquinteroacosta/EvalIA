"""Execute one authorized5A unit; assistant reviews results between units."""
import json,sys
from pathlib import Path
from decimal import Decimal
from hashlib import sha256
from .budgeted_reader import Reader,ROOT,estimate,canonical
from .step5a_authorized import AUTH as BASE_AUTH
from . import component_routes as routes
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

BASE=Path('docs/ansiedad_semantic/closure6_20261013/offline_04')
WORK=Path('docs/ansiedad_semantic/closure6_20261013')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def events():return [json.loads(s) for s in (ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]
def cash():
    es=events();snapshot=read(WORK/'live_5A_01/ledger_before.json')
    confirmation=WORK/'integral_live/continuation_1501/financial_confirmation.json'
    balance=Decimal('4')
    if confirmation.exists():
        snapshot=read(confirmation)
        balance=Decimal(snapshot['confirmed_balance_usd'])
    prefix=es[:snapshot['event_count']]
    old={r['attempt'] for r in prefix if r['kind']=='settled'}
    settled={r['attempt']:r for r in es if r['kind']=='settled'}
    pending=sum((Decimal(r['reserved_usd']) for r in es if r['kind']=='reserved' and r['attempt'] not in settled),Decimal(0))
    spent=sum((Decimal(r['actual_usd']) for a,r in settled.items() if a not in old),Decimal(0))
    return balance-Decimal('0.5733136')-pending-spent

def run(code):
    if code not in ('PA1','IR2','PS6','CE3'):raise ValueError('Outside authorized5A scope')
    out=WORK/('continue_5A_'+code);out.mkdir(exist_ok=False)
    def save(name,value):
        with (out/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    if code=='PA1':
        auth={**BASE_AUTH,'authorization_id':'ANXIETY-20261013-PA1-CORRECTED-0087052','additional_cap_usd':'0.087052',
              'authority':'Current user explicitly authorizes corrected PA1 verification maxUSD0.087052 subject to all-reserve cash check; reuse extraction.'}
        requests=[read(WORK/'live_5A_02/PA1_corrected_verifier_NOT_AUTHORIZED.json')]
        extraction=read(WORK/'live_5A_02/critical-PA1_extract.json')['reading']
    else:
        auth=BASE_AUTH
        group=next(p for p in read(BASE/'VALIDATION_PLAN_MINIMUM.json')['plans'] if p['id']=='critical-'+code)
        requests=[read(BASE/c['request']) for c in group['calls']]
        for c,q in zip(group['calls'],requests):assert sha256(canonical(q).encode()).hexdigest()==c['request_sha256']
        extraction=None
    for q in requests:
        assert all(v['components']==routes.definitions(c) for c,v in q['indicators'].items())
    required=sum((Decimal(estimate(q,'gpt-4.1-2025-04-14')['reserved_upper_bound_usd']) for q in requests),Decimal(0))
    if code=='PA1':assert required<=Decimal('0.087052')
    save('authorization.json',auth);save('financial_before.json',{'free_cash_usd':str(cash()),'package_upper_usd':str(required),'historical_holds_released':0})
    stop=None;result=None
    try:
        if cash()<required:raise PermissionError('Insufficient global cash preserving all historical holds')
        reader=Reader(auth)
        for q in requests:
            if cash()<Decimal(estimate(q,'gpt-4.1-2025-04-14')['reserved_upper_bound_usd']):raise PermissionError('Global cash changed')
            print(json.dumps({'case':code,'stage':q['stage']}),flush=True)
            r=reader(q);save(q['stage']+'.json',{'request':q,'reading':r})
            if q['stage']=='extract':extraction=r
            else:verification=r
        o=q['original'];ctx=TurnContext(o['user'],o['response'],tuple(HistoryTurn(**h) for h in o['prior_history']))
        result={c:routes.adjudicate(c,ctx,extraction['indicators'][c],verification['indicators'][c]) for c in q['indicators']}
        save('adjudication.json',result)
        if any(r['status']=='BLOCKED' for r in result.values()):stop='Semantic/evidence discrepancy: paid work stopped for offline analysis, no automatic retries'
    except Exception as e:stop=type(e).__name__+': '+str(e)
    es=events();settled={r['attempt']:r for r in es if r['kind']=='settled'}
    own=[r for r in es if r['kind']=='reserved' and r['authorization']==auth['authorization_id']]
    summary={'step':'PASO5A','case':code,'stop':stop,'results':result,'free_cash_usd':str(cash()),
        'authorization_attempts':len(own),'authorization_usage_cost_usd':str(sum((Decimal(settled[r['attempt']]['actual_usd']) for r in own if r['attempt'] in settled),Decimal(0))),
        'authorization_uncertain_holds_usd':str(sum((Decimal(r['reserved_usd']) for r in own if r['attempt'] not in settled),Decimal(0))),
        'semantic_retries_automatic':0,'freeze':'NO APTO until remaining criteria verified'}
    save('summary.json',summary)
    print(json.dumps({'case':code,'stop':stop,'results':[(c,r['status'],r['score']) for c,r in (result or {}).items()],'free_cash':str(cash())}),flush=True)

if __name__=='__main__':run(sys.argv[1])
