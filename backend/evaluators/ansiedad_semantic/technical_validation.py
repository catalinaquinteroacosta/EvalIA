"""Controlled synthetic validation, same night ledger/cap, never experiment completion."""
from pathlib import Path
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import json
from .technical_corpus import cases
from .night_validation import AUTH,accounting
from .budgeted_reader import Reader,estimate
from .run_authorized_validation import save
from . import component_routes as routes,em_component_adapter as em
from .result_tables import export_new,aggregate
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

def prepare(case):
    requests=[];family=case['codes'][0][:2]
    def collect(q):
        q['indicators']={c:v for c,v in q['indicators'].items() if c in case['codes']}
        q['instruction']+=' Razones concisas. Acredita cada hecho verdadero con cita propia exacta. No confundas desconocimiento del lector con defecto textual; una mejora opcional no es insuficiencia. No atribuyas requisitos de otro indicador.'
        requests.append(q);return {}
    if family=='EM':em.run_family(case['original'],reader=collect)
    else:routes.run_family(case['original'],family,reader=collect)
    return requests

def run(directory,critical=False):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    if critical:
        from .technical_critical_cases import cases as critical_cases
        corpus=critical_cases()
    else:corpus=cases()
    authorization={**AUTH,'extraction_model':'gpt-4.1-2025-04-14'} if critical else AUTH
    save(directory/'corpus_preregistered.json',corpus)
    save(directory/'authorization.json',authorization)
    # Reader sees no split, expectation, descriptor-based expected note or outcome.
    plans=[]
    for case in corpus:
        requests=prepare(case)
        plans.append({'id':case['id'],'calls':len(requests),'reserved_pair_usd':str(sum(
            Decimal(estimate(q,authorization['extraction_model' if q['stage']=='extract' else 'verification_model'])['reserved_upper_bound_usd']) for q in requests))})
    save(directory/'estimate.json',{'accounting_before':accounting(),'plans':plans,
        'total_conservative_usd':str(sum(Decimal(p['reserved_pair_usd']) for p in plans)),
        'retry_allowance':0,'policy':'Only each complete fitting pair sent; total estimate is not authorized spending above cap.'})
    rows=[];outcomes=[];stop=None
    # Development cases first; reserve heldout evidence without modifying fixtures.
    for case,plan in zip(corpus,plans):
        requests=prepare(case)
        if not requests:
            # CE10 first turn: canonical official gate, no paid request required.
            decisions={'CE10':{'code':'CE10','status':'N/A','score':None,'reason':'Official first-turn gate, no prior history.'}}
            a=b=None
        else:
            if Decimal(plan['reserved_pair_usd'])>Decimal(accounting()['available_usd']):
                stop='Insufficient budget to reserve next complete pair';break
            print(json.dumps({'case':case['id'],'estimate':plan,'accounting':accounting()}),flush=True)
            try:
                reader=Reader(authorization)
                with ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(reader,requests))
            except Exception as error:
                stop=type(error).__name__+': '+str(error)
                save(directory/'transport_block.json',{'case':case['id'],'error':stop,'accounting':accounting()});break
            original=case['original'];context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
            decisions={}
            for code in requests[0]['indicators']:
                try:
                    x,y=a['indicators'][code],b['indicators'][code]
                    decisions[code]=em.adjudicate(code,context,x,y) if code.startswith('EM') else routes.adjudicate(code,context,x,y)
                except Exception as error:decisions[code]={'code':code,'status':'BLOCKED','score':None,'reason':str(error)}
            if 'CE10' in case['codes'] and 'CE10' not in decisions:
                decisions['CE10']={'code':'CE10','status':'N/A','score':None,'reason':'Official first-turn gate, no prior history.'}
        save(directory/(case['id']+'.json'),{'case':case,'extraction':a,'independent_verification':b,'decisions':decisions})
        for code,d in decisions.items():
            expected=case['expected'].get(code,'UNSPECIFIED')
            match=None if expected=='UNSPECIFIED' else (d['status'],d['score'])==('N/A' if expected is None else 'SCORED',expected)
            outcomes.append({'case':case['id'],'code':code,'split':case['split'],'expected':expected,
                'status':d['status'],'score':d['score'],'matches':match,'reason':d['reason']})
            rows.append({**d,'conversation':case['original']['conversation'],'model':case['original']['model'],
                'turn':case['original']['turn'],'family':code[:2],'applicability':'APPLICABLE' if d['status']=='SCORED' else 'NOT_APPLICABLE' if d['status']=='N/A' else 'UNRESOLVED',
                'gate_reason':d['reason'] if d['status']=='N/A' else ''})
        print(json.dumps({'case':case['id'],'results':[(c,d['status'],d['score']) for c,d in decisions.items()]}),flush=True)
    save(directory/'outcomes.json',outcomes);export_new(directory/'tables',rows)
    save(directory/'summary.json',{'results':aggregate(rows),'cases_completed':len(set(r['case'] for r in outcomes)),
        'codes_exercised':len(set(r['code'] for r in outcomes)),'matches':sum(r['matches'] is True for r in outcomes),
        'discrepancies':sum(r['matches'] is False for r in outcomes),'accounting':accounting(),'stop_reason':stop,
        'clinical_validation':False,'qualification':'No automatic freeze by numeric agreement; review discrepancies and coverage.'})

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8');run(sys.argv[1],critical=len(sys.argv)>2 and sys.argv[2]=='critical')
