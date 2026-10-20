"""One controlled blind recheck of unresolved synthetic cases, no accepted replays."""
from pathlib import Path
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import json
from .technical_validation import prepare
from .technical_expectations import CORRECTIONS
from .night_validation import AUTH,accounting
from .budgeted_reader import Reader,estimate
from .run_authorized_validation import save
from . import component_routes as routes,em_component_adapter as em
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

def run(source,directory,*,recover_length=False):
    source=Path(source);directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    save(directory/'authorization.json',{**AUTH,'extraction_model':'gpt-4.1-2025-04-14'})
    save(directory/'fixture_errata.json',[{'case':c,'code':k,'expected':v,'official_reason':why} for (c,k),(v,why) in CORRECTIONS.items()])
    results=[];stop=None
    for file in sorted(source.glob('*.json')):
        packet=json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(packet,dict) or 'decisions' not in packet:continue
        case=packet['case'];needed=[]
        for code,d in packet['decisions'].items():
            expected=CORRECTIONS.get((case['id'],code),(case['expected'].get(code,'UNSPECIFIED'),''))[0]
            matches=None if expected=='UNSPECIFIED' else (d['status'],d['score'])==('N/A' if expected is None else 'SCORED',expected)
            if d['status'] in ('BLOCKED','PENDING') or matches is False:needed.append(code)
        if not needed:continue
        revised={**case,'codes':needed};requests=prepare(revised)
        if recover_length and case['id']=='PA-omission':
            # The saved extractor stopped at finish_reason=length (10,400).
            # Its valid blind verifier request is kept byte-identical for reuse.
            requests[0]['_max_output_tokens']=20000
        if not requests:continue
        reserve=sum(Decimal(estimate(q,'gpt-4.1-2025-04-14')['reserved_upper_bound_usd']) for q in requests)
        save(directory/(case['id']+'_estimate.json'),{'codes':needed,'upper_bound_usd':str(reserve),'accounting':accounting()})
        if reserve>Decimal(accounting()['available_usd']):stop='Next complete strong pair exceeds remaining authorization';break
        print(json.dumps({'case':case['id'],'codes':needed,'pair_upper_bound_usd':str(reserve)}),flush=True)
        try:
            reader=Reader({**AUTH,'extraction_model':'gpt-4.1-2025-04-14'})
            with ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(reader,requests))
        except Exception as error:stop=type(error).__name__+': '+str(error);break
        original=case['original'];context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        decisions={}
        for code in requests[0]['indicators']:
            try:
                x,y=a['indicators'][code],b['indicators'][code]
                decisions[code]=em.adjudicate(code,context,x,y) if code.startswith('EM') else routes.adjudicate(code,context,x,y)
            except Exception as error:decisions[code]={'code':code,'status':'BLOCKED','score':None,'reason':str(error)}
        save(directory/(case['id']+'.json'),{'case':case,'before':{c:packet['decisions'][c] for c in needed},
             'extraction':a,'independent_verification':b,'decisions':decisions,'source':str(file)})
        results.extend({'case':case['id'],'code':c,'status':d['status'],'score':d['score'],'reason':d['reason']} for c,d in decisions.items())
        print(json.dumps({'case':case['id'],'results':[(c,d['status'],d['score']) for c,d in decisions.items()]}),flush=True)
    save(directory/'summary.json',{'results':results,'accounting':accounting(),'stop_reason':stop,
        'qualification':'Strong blind pairs; prior failed cases are development/requalification, not an untouched holdout.'})

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8');run(sys.argv[1],sys.argv[2],recover_length=len(sys.argv)>3 and sys.argv[3]=='recover_length')
