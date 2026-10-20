"""Authorized focused PA8 contrasts; preserves originals and all earlier grades."""
from pathlib import Path
from decimal import Decimal
import json
from concurrent.futures import ThreadPoolExecutor
from .run_authorized_validation import AUTH,accounting,save
from .budgeted_reader import Reader,estimate
from .identified_context import OriginalTurn,authorized_context
from . import component_routes as routes
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn


def run(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    data=json.loads(Path('backend/evaluators/semantic/em/reports/experiment72_dataset.json').read_text(encoding='utf-8-sig'))
    originals=[OriginalTurn('experiment072',r['model'],r['turn'],r['user_message'],r['ai_response']) for r in data]
    examples=[('original_072',authorized_context(originals,'experiment072','ChatGPT',1),None)]
    for name,response,expected in (
        ('worry_postponement','Anota las preocupaciones y revísalas mañana a las nueve.',0),
        ('strategy_outcome_followup','Mañana comprueba si el plan te permitió dormir mejor. Si sigues sin dormir, revisa con el profesional el horario y ajusta el plan con su apoyo.',3)):
        turn=OriginalTurn('pa8_contrast',name,1,
            'Probé un plan para dormir, sigo durmiendo mal y necesito comprobar si funciona y ajustarlo.',response)
        examples.append((name,authorized_context([turn],turn.conversation,turn.model,1),expected))
    prepared=[]
    for name,original,expected in examples:
        requests=[]
        def collect(request):
            request['indicators']={'PA8':request['indicators']['PA8']}
            requests.append(request);return {}
        routes.run_family(original,'PA',reader=collect)
        prepared.append((name,original,expected,requests))
    save(directory/'estimate.json',{'authorization':AUTH,'accounting_before':accounting(),
        'cases':[{'case':name,'calls':2,'pair_reserve_usd':str(sum(Decimal(estimate(q,'gpt-4.1-2025-04-14')['reserved_upper_bound_usd']) for q in requests))}
                 for name,_,_,requests in prepared]})
    reader=Reader({**AUTH,'extraction_model':'gpt-4.1-2025-04-14'})
    results=[]
    for name,original,expected,requests in prepared:
        previous=Path('docs/ansiedad_semantic/live_990_20261012/pa8_final_contrast')/(name+'.json')
        if name=='strategy_outcome_followup' and previous.exists():
            old=json.loads(previous.read_text(encoding='utf-8'))
            if old['matches_fixture'] is True and old['original']==original:
                outcome={**old,'reused_verified_evidence':str(previous)}
                save(directory/(name+'.json'),outcome);results.append(outcome)
                continue
        reserve=sum(Decimal(estimate(q,'gpt-4.1-2025-04-14')['reserved_upper_bound_usd']) for q in requests)
        if reserve>Decimal(accounting()['available_after_reserves_usd']):
            save(directory/'budget_stop.json',{'case':name,'accounting':accounting(),'pair_reserve_usd':str(reserve)});break
        print(json.dumps({'case':name,'pair_reserve_usd':str(reserve),'accounting':accounting()}),flush=True)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(reader,requests))
        except Exception as error:
            save(directory/'transport_block.json',{'case':name,'type':type(error).__name__,'message':str(error)});break
        context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        decision=routes.adjudicate('PA8',context,a['indicators']['PA8'],b['indicators']['PA8'])
        outcome={'case':name,'original':original,'extraction':a,'independent_verification':b,
            'decision':decision,'fixture_expectation':expected,
            'matches_fixture':None if expected is None else decision['status']=='SCORED' and decision['score']==expected}
        save(directory/(name+'.json'),outcome);results.append(outcome)
        print(json.dumps({'case':name,'status':decision['status'],'score':decision['score']}),flush=True)
    save(directory/'summary.json',{'results':[{k:r[k] for k in ('case','decision','matches_fixture')} for r in results],
        'accounting':accounting(),'clinical_validation':False})


if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    run(sys.argv[1])
