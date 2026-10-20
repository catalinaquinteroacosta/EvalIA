"""Only the explicitly authorized eight saved5A requests; no automatic retries."""
from pathlib import Path
from decimal import Decimal
from hashlib import sha256
import json,os
from .budgeted_reader import Reader,ROOT,canonical,estimate
from .technical_validation import prepare
from . import component_routes as routes
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

BASE=Path('docs/ansiedad_semantic/closure6_20261013/offline_04')
OUT=Path('docs/ansiedad_semantic/closure6_20261013/live_5A_01')
AUTH={'explicit_user_approval':True,'authorization_id':'ANXIETY-20261013-STEP5A-0751592',
      'additional_cap_usd':'0.751592','outstanding_reservations_usd':'0',
      'extraction_model':'gpt-4.1-2025-04-14','verification_model':'gpt-4.1-2025-04-14',
      'authority':'User yes to confirmation of current USD4 balance and eight5A calls maxUSD0.751592, zero retries. No other packages authorized.'}
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(name,value):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def events():return [json.loads(s) for s in (ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]

def run():
    OUT.mkdir(parents=True,exist_ok=False)
    old=events();baseline_settled={e['attempt'] for e in old if e['kind']=='settled'}
    save('authorization.json',AUTH);save('ledger_before.json',{'sha256':sha256((ROOT/'ledger.jsonl').read_bytes()).hexdigest(),'event_count':len(old)})
    allowed={'critical-PA1','critical-IR2','critical-PS6','critical-CE3'}
    groups=[g for g in load(BASE/'VALIDATION_PLAN_MINIMUM.json')['plans'] if g['id'] in allowed]
    assert len(groups)==4 and sum(len(g['calls']) for g in groups)==8
    def free():
        rows=events();settled={r['attempt']:r for r in rows if r['kind']=='settled'}
        holds=sum((Decimal(r['reserved_usd']) for r in rows if r['kind']=='reserved' and r['attempt'] not in settled),Decimal(0))
        new_spend=sum((Decimal(r['actual_usd']) for r in settled.values() if r['attempt'] not in baseline_settled),Decimal(0))
        return Decimal('4')-Decimal('0.5733136')-holds-new_spend
    # All contract/cost checks precede any paid request.
    for g in groups:
        for c in g['calls']:
            q=load(BASE/c['request']);assert sha256(canonical(q).encode()).hexdigest()==c['request_sha256']
            current=next(r for r in prepare({'original':q['original'],'codes':g['codes']}) if r['stage']==q['stage'])
            assert all(q['indicators'][code]['components']==current['indicators'][code]['components'] for code in g['codes'])
            assert estimate(q,c['model'])['reserved_upper_bound_usd']==c['cost_max_usd']
    outcomes=[];stop=None
    try:
        if not os.environ.get('OPENAI_API_KEY'):raise PermissionError('API key not present in process environment; no credentials files read and no requests reserved.')
        reader=Reader(AUTH)
        for g in groups:
            if free()<sum((Decimal(c['cost_max_usd']) for c in g['calls']),Decimal(0)):raise PermissionError('Global cash cannot cover complete pair including every historical hold')
            readings=[]
            for c in g['calls']:
                q=load(BASE/c['request'])
                if free()<Decimal(c['cost_max_usd']):raise PermissionError('Global cash insufficient for next request')
                print(json.dumps({'case':g['id'],'stage':q['stage'],'reserve':c['cost_max_usd']}),flush=True)
                result=reader(q);save(g['id']+'_'+q['stage']+'.json',{'request':q,'reading':result})
                readings.append(result)
            original=q['original'];ctx=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
            result={code:routes.adjudicate(code,ctx,readings[0]['indicators'][code],readings[1]['indicators'][code]) for code in g['codes']}
            save(g['id']+'_adjudication.json',result);outcomes.append({'case':g['id'],'results':result})
            if any(r['status']=='BLOCKED' for r in result.values()):raise ValueError('Unresolved semantic/evidence discrepancy; stop all paid work')
            # Stop between pairs for independent assistant review of semantic meaning.
            print(json.dumps({'pair_complete':g['id'],'results':[(c,r['status'],r['score']) for c,r in result.items()]}),flush=True)
            if g is not groups[-1]:
                save('REVIEW_REQUIRED.json',{'completed':g['id'],'next':'Review literal meaning offline before authorizing continuation within the same eight-call package; do not rerun completed requests.'})
                stop='Pause after first pair for literal-semantic review';break
    except Exception as e:stop=type(e).__name__+': '+str(e)
    now=events();settled={r['attempt']:r for r in now if r['kind']=='settled'}
    own=[r for r in now if r['kind']=='reserved' and r['authorization']==AUTH['authorization_id']]
    save('summary.json',{'step':'PASO5A','stop':stop,'outcomes':outcomes,'attempts':len(own),
        'cost_from_usage_usd':str(sum((Decimal(settled[r['attempt']]['actual_usd']) for r in own if r['attempt'] in settled),Decimal(0))),
        'uncertain_reserves_usd':str(sum((Decimal(r['reserved_usd']) for r in own if r['attempt'] not in settled),Decimal(0))),
        'conservative_free_cash_usd':str(free()),'freeze':'NO APTO','retries':0})
    print(json.dumps(load(OUT/'summary.json'),ensure_ascii=False),flush=True)

if __name__=='__main__':
    import sys
    if len(sys.argv)>1:
        if sys.argv[1]!='outside-sandbox':raise ValueError('Unknown invocation')
        OUT=Path('docs/ansiedad_semantic/closure6_20261013/live_5A_02')
    run()
