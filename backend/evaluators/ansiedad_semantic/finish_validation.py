"""Focused one-indicator blind pairs, stable amended ledger, immutable outputs."""
from pathlib import Path
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import json
from .night_validation import AUTH,accounting
from .technical_validation import prepare
from .budgeted_reader import Reader,estimate
from .run_authorized_validation import save
from . import component_routes as routes,em_component_adapter as em
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

def run(corpus,target,*,strong_extraction=True,claim_audit=False):
    target=Path(target);target.mkdir(parents=True,exist_ok=False)
    authorization={**AUTH,**({'extraction_model':'gpt-4.1-2025-04-14'} if strong_extraction else {})}
    # Keep an explicit planning allowance for untouched independent cases.
    planning_floor=Decimal('0') if strong_extraction else Decimal('1.20')
    authorization['outstanding_reservations_usd']=str(planning_floor)
    save(target/'corpus_preregistered.json',corpus)
    save(target/'authorization.json',{**authorization,'verification_protocol':'independent_claim_audit' if claim_audit else 'blind_dual_reading'})
    plans=[]
    for case in corpus:
        requests=prepare(case)
        upper=sum(Decimal(estimate(q,authorization['extraction_model' if q['stage']=='extract' else 'verification_model'])['reserved_upper_bound_usd']) for q in requests)
        if claim_audit:
            # Reserve extra input capacity for the proposal before extracting.
            upper+=Decimal('0.12')
        plans.append({'case':case['id'],'calls':len(requests),'reserved_upper_bound_usd':str(upper)})
    save(target/'estimate.json',{'accounting_before':accounting(),'plans':plans,
        'batch_upper_bound_usd':str(sum(Decimal(p['reserved_upper_bound_usd']) for p in plans)),
        'atomic_budget_lot':'Each complete pair; full plan is not spent/reserved upfront.',
        'claim_audit_planning_note':('Proposal allowance is provisional; verifier is an independently estimated/reserved atomic call after extraction.' if claim_audit else None),
        'holdout_planning_allowance_usd':str(planning_floor),
        'automatic_retries':0,'actual_account_balance':'Not available through the configured API; authorization is not account credit.'})
    rows=[];stop=None
    for case,plan in zip(corpus,plans):
        if Decimal(plan['reserved_upper_bound_usd'])+planning_floor>Decimal(accounting()['available_usd']):
            stop='Next complete pair cannot be reserved';break
        q=prepare(case)
        print(json.dumps({'case':case['id'],'reserve_usd':plan['reserved_upper_bound_usd']}),flush=True)
        try:
            reader=Reader(authorization)
            if claim_audit:
                from .claim_verifier import verification_request
                a=reader(q[0]);verification=verification_request(q[1],a)
                exact=Decimal(estimate(verification,authorization['verification_model'])['reserved_upper_bound_usd'])
                save(target/(case['id']+'_verifier_estimate.json'),{'upper_bound_usd':str(exact),'accounting_before':accounting(),
                    'policy':'Exact proposal-inclusive call is reserved by Reader before transport.'})
                if exact+planning_floor>Decimal(accounting()['available_usd']):raise ValueError('Cannot reserve verifier including proposal; extraction retained in private ledger')
                b=reader(verification)
            else:
                with ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(reader,q))
        except Exception as error:
            stop=type(error).__name__+': '+str(error)
            save(target/'transport_block.json',{'case':case['id'],'error':stop,'accounting':accounting()});break
        original=case['original'];ctx=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        decisions={}
        for code in q[0]['indicators']:
            x,y=a['indicators'][code],b['indicators'][code]
            decisions[code]=em.adjudicate(code,ctx,x,y) if code.startswith('EM') else routes.adjudicate(code,ctx,x,y)
            rows.append({'case':case['id'],'code':code,**{k:decisions[code][k] for k in ('status','score','reason')}})
        save(target/(case['id']+'.json'),{'case':case,'extraction':a,'independent_verification':b,'decisions':decisions})
        print(json.dumps(rows[-len(decisions):],ensure_ascii=False),flush=True)
    save(target/'summary.json',{'rows':rows,'accounting':accounting(),'stop_reason':stop,
        'policy':'No automatic freeze, numeric expectations are hypotheses and never sent to readers.'})

def unresolved(source):
    corpus=[]
    for file in sorted(Path(source).glob('*.json')):
        packet=json.loads(file.read_text(encoding='utf-8'))
        for code,d in packet['decisions'].items():
            if d['status']!='BLOCKED':continue
            case=packet['case']
            corpus.append({**case,'id':case['id']+'__'+code,'original_case_id':case['id'],
                'codes':[code],'before':{k:d[k] for k in ('status','score','reason')},
                'qualification':'Single-code requalification after demonstrated contract repair; not a fresh holdout.'})
    return corpus

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    source=Path(sys.argv[1]);corpus=unresolved(source) if source.is_dir() else json.loads(source.read_text(encoding='utf-8'))
    mode=sys.argv[3] if len(sys.argv)>3 else ''
    run(corpus,sys.argv[2],strong_extraction=not mode.startswith('mini_extract'),claim_audit='claim' in mode)
