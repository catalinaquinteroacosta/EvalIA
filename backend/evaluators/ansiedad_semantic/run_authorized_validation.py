"""Explicitly authorized, resumable anxiety validation; append-only evidence."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
import json
from .budgeted_reader import Reader, ROOT, estimate
from .live_regression_cases import prepared_requests
from . import component_routes as routes, em_component_adapter as em
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn

AUTH={'explicit_user_approval':True,'authorization_id':'ANXIETY-20261012-ADDITIONAL-9.90',
      'additional_cap_usd':'9.90','extraction_model':'gpt-4.1-mini-2025-04-14',
      'verification_model':'gpt-4.1-2025-04-14','outstanding_reservations_usd':'0.5733136',
      'historical_reserve_source':'docs/crisis_semantic/ac9_live8/api_accounting.json: committed minus estimated; eight unknown-billing entries remain uncleared',
      'authority':'User confirmed si to additional maximum USD9.90 including reservations; no transfer from CRISIS.'}

def save(path,value):
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,ensure_ascii=False,indent=2)

def accounting():
    events=[json.loads(line) for line in (ROOT/'ledger.jsonl').read_text().splitlines()] if (ROOT/'ledger.jsonl').exists() else []
    reserved={e['attempt']:Decimal(e['reserved_usd']) for e in events if e['kind']=='reserved' and e['authorization']==AUTH['authorization_id']}
    settled={e['attempt']:Decimal(e['actual_usd']) for e in events if e['kind']=='settled' and e['attempt'] in reserved}
    committed=sum((settled.get(k,v) for k,v in reserved.items()),Decimal(0))
    historical=Decimal(AUTH['outstanding_reservations_usd'])
    return {'attempts':len(reserved),'settled':len(settled),'actual_usd':str(sum(settled.values(),Decimal(0))),
        'uncertain_reserves_usd':str(sum((v for k,v in reserved.items() if k not in settled),Decimal(0))),
        'committed_usd':str(committed),'historical_uncertain_reserves_usd':str(historical),
        'available_after_reserves_usd':str(Decimal('9.90')-committed-historical)}

def focal(directory, strong=False):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    authorization={**AUTH,'extraction_model':'gpt-4.1-2025-04-14'} if strong else AUTH
    save(directory/'authorization.json',authorization)
    reader=Reader(authorization);results=[]
    for case in prepared_requests():
        name=case['code']+'_'+case['case']+'.json'
        candidates=[Path('docs/ansiedad_semantic/live_990_20261012')/phase/name for phase in ('focal_4','focal_3','focal_2')]
        prior=next((p for p in candidates if p.exists() and json.loads(p.read_text(encoding='utf-8'))['matches_expected']),candidates[0])
        if prior.exists():
            old=json.loads(prior.read_text(encoding='utf-8'))
            if old['matches_expected']:
                results.append(old)
                save(directory/(case['code']+'_'+case['case']+'.json'),{**old,'reused_verified_evidence':str(prior)})
                continue
        readings=[]
        for request in case['requests']:
            model=authorization['extraction_model' if request['stage']=='extract' else 'verification_model']
            print(json.dumps({'case':case['case'],'code':case['code'],'stage':request['stage'],'estimate':estimate(request,model)}),flush=True)
            try:readings.append(reader(request))
            except Exception as error:
                save(directory/'transport_block.json',{'type':type(error).__name__,'message':str(error),'accounting':accounting()})
                save(directory/'results.json',results)
                raise
        original=case['requests'][0]['original']
        context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**r) for r in original['prior_history']))
        a,b=[r['indicators'][case['code']] for r in readings]
        decision=em.adjudicate(case['code'],context,a,b) if case['code'].startswith('EM') else routes.adjudicate(case['code'],context,a,b)
        result={'case':case['case'],'code':case['code'],'original':original,'expected_status':case['expected_status'],
            'expected_score':case['expected_score'],'decision':decision,
            'matches_expected':(decision['status'],decision['score'])==(case['expected_status'],case['expected_score'])}
        results.append(result);save(directory/(case['code']+'_'+case['case']+'.json'),result)
        print(json.dumps({'case':case['case'],'code':case['code'],'status':decision['status'],'score':decision['score'],'matches_expected':result['matches_expected']}),flush=True)
    save(directory/'results.json',results)
    save(directory/'summary.json',{'cases':len(results),'accepted':sum(r['matches_expected'] for r in results),
        'discrepancies':sum(not r['matches_expected'] for r in results),'accounting':accounting(),'clinical_validation':False})

def corpus(directory,pilot=False):
    from .identified_context import OriginalTurn, authorized_context
    from .official_contracts import EXPECTED
    from .result_tables import export_new, grouped
    from concurrent.futures import ThreadPoolExecutor
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    save(directory/'authorization.json',AUTH)
    source=Path('backend/evaluators/semantic/em/reports/experiment72_dataset.json')
    data=json.loads(source.read_text(encoding='utf-8-sig'))
    originals=[OriginalTurn('experiment072',r['model'],r['turn'],r['user_message'],r['ai_response']) for r in data]
    rows={(r.model,r.turn,f'{family}{i}'):{'conversation':r.conversation,'model':r.model,'turn':r.turn,
        'family':family,'code':f'{family}{i}','status':'PENDING','score':None,'applicability':'NOT_YET_VERIFIED'}
        for r in originals for family,count in EXPECTED.items() for i in range(1,count+1)}
    previous=Path('docs/ansiedad_semantic/live_990_20261012')
    for path in sorted(previous.glob('corpus_*/*_*.json')):
        saved=json.loads(path.read_text(encoding='utf-8'))
        for row in saved.get('results',[]):
            if row['status'] in ('SCORED','N/A'):
                rows[row['model'],row['turn'],row['code']]={**row,'reused_verified_evidence':str(path)}
    for path in sorted(previous.glob('targeted_*/*_*.json')):
        saved=json.loads(path.read_text(encoding='utf-8'))
        row=saved.get('after',{})
        if row.get('status') in ('SCORED','N/A'):
            rows[row['model'],row['turn'],row['code']]={**row,'reused_verified_evidence':str(path)}
    baselines=sorted(previous.glob('targeted_*/tables/observations.json'))
    baseline=baselines[-1] if baselines else previous/'targeted_1/tables/observations.json'
    if baseline.exists():
        for row in json.loads(baseline.read_text(encoding='utf-8')):
            if row['status']!='PENDING':
                rows[row['model'],row['turn'],row['code']]={**row,'reused_verified_evidence':str(baseline)}
    # Documentary review found a false-positive agreement: scheduling a worry
    # period is not by itself a review of the plan's results. Preserve the
    # historical 3, but hold current adjudication until focused verification.
    for key,row in rows.items():
        if key==('ChatGPT',1,'PA8') and row['status']=='SCORED':
            rows[key]={**row,'historical_score':row['score'],'status':'BLOCKED','score':None,
                'applicability':'UNRESOLVED',
                'reason':'Auditoría literal: revisar preocupaciones se confundió con revisar resultados o ajustar el plan; concordancia insuficiente.'}
        if key==('ChatGPT',1,'PS6') and row['status']=='SCORED':
            rows[key]={**row,'historical_score':row['score'],'status':'BLOCKED','score':None,
                'applicability':'UNRESOLVED',
                'reason':'Auditoría: gate sustentado en posibilidad genérica de asumir rol y límite inferido exclusivamente de derivación; no basta para validar la decisión PS6.'}
    reader=Reader(AUTH);strong_reader=Reader({**AUTH,'extraction_model':'gpt-4.1-2025-04-14'});stop=None
    # Turn ordering covers every model before progressing longitudinally.
    selected_originals=sorted(originals,key=lambda r:(r.turn,r.model))
    for r in (selected_originals[:1] if pilot else selected_originals):
        if not pilot and r.model=='ChatGPT' and r.turn==1:
            continue  # unresolved gates under human review; no paid repeated polling
        original=authorized_context(originals,r.conversation,r.model,r.turn)
        context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        if original['turn']==1 and not original['prior_history']:
            fixed=routes.run_family(original,'CE',reader=lambda _: (_ for _ in ()).throw(OSError('gate-only')))['results']['CE10']
            rows[r.model,r.turn,'CE10']={**fixed,'conversation':r.conversation,'model':r.model,
                'turn':r.turn,'family':'CE','input_sha256':original['input_sha256'],
                'applicability':'NOT_APPLICABLE','gate_reason':fixed['reason']}
        for family in EXPECTED:
            needed={f'{family}{i}' for i in range(1,EXPECTED[family]+1)
                    if rows[r.model,r.turn,f'{family}{i}']['status'] not in ('SCORED','N/A')}
            if not needed:continue
            requests=[]
            def collect(request):
                request['indicators']={code:value for code,value in request['indicators'].items() if code in needed}
                request['instruction']+=' Usa razones concisas; citas mínimas suficientes, exactas y contextualizadas. No repitas explicaciones extensas.'
                requests.append(request);return {}
            if family=='EM':em.run_family(original,reader=collect)
            else:routes.run_family(original,family,reader=collect)
            selected=strong_reader if pilot or family in ('ND','EM') else reader
            reserve=sum(Decimal(estimate(q,selected.authorization['extraction_model' if q['stage']=='extract' else 'verification_model'])['reserved_upper_bound_usd']) for q in requests)
            if reserve>Decimal(accounting()['available_after_reserves_usd']):
                stop='Límite adicional: no alcanza para reservar ambas lecturas de la siguiente familia.';break
            print(json.dumps({'model':r.model,'turn':r.turn,'family':family,'pair_reserve_usd':str(reserve),'accounting':accounting()}),flush=True)
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    a,b=list(pool.map(selected,requests))
            except Exception as error:
                stop=f'{type(error).__name__}: {error}'
                for code in needed:
                    rows[r.model,r.turn,code].update(status='BLOCKED',score=None,
                        reason=stop,applicability='UNRESOLVED')
                save(directory/(original['input_sha256']+'_'+family+'_transport.json'),
                    {'original':original,'results':[rows[r.model,r.turn,c] for c in needed],'transport_error':stop})
                break
            decisions=[]
            for code in requests[0]['indicators']:
                try:
                    x,y=a['indicators'][code],b['indicators'][code]
                    d=em.adjudicate(code,context,x,y) if family=='EM' else routes.adjudicate(code,context,x,y)
                except Exception as error:d={'code':code,'status':'BLOCKED','score':None,'reason':f'{type(error).__name__}: {error}'}
                row={**d,'conversation':r.conversation,'model':r.model,'turn':r.turn,'family':family,
                     'input_sha256':original['input_sha256'],'applicability':'APPLICABLE' if d['status']=='SCORED' else 'NOT_APPLICABLE' if d['status']=='N/A' else 'UNRESOLVED',
                     'gate_reason':d['reason'] if d['status']=='N/A' else ''}
                rows[r.model,r.turn,code]=row;decisions.append(row)
            save(directory/(original['input_sha256']+'_'+family+'.json'),{'original':original,'extraction':a,'independent_verification':b,'results':decisions})
            print(json.dumps({'family':family,'statuses':{s:sum(d['status']==s for d in decisions) for s in ('SCORED','N/A','BLOCKED')}}),flush=True)
        if stop:break
    values=list(rows.values());export_new(directory/'tables',values)
    save(directory/'groups.json',{name:grouped(values,fields) for name,fields in {'indicator':('code',),'family':('family',),
        'model':('model',),'turn':('model','turn'),'conversation':('conversation','model')}.items()})
    save(directory/'accounting.json',{'accounting':accounting(),'stop_reason':stop,'clinical_validation':False})

def targeted(directory):
    from .identified_context import OriginalTurn,authorized_context
    from .result_tables import export_new
    from backend.evaluators.nd.docx_components import contracts
    from concurrent.futures import ThreadPoolExecutor
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    save(directory/'authorization.json',AUTH)
    rows=json.loads(Path('docs/ansiedad_semantic/live_990_20261012/targeted_1/tables/observations.json').read_text(encoding='utf-8'))
    for row in rows:
        if (row['model'],row['turn'],row['code'])==('ChatGPT',1,'PA8'):
            row.update(status='BLOCKED',score=None,
                reason='Auditoría: revisar preocupaciones no acredita por sí solo revisar resultados o ajustar el plan.')
    source=json.loads(Path('backend/evaluators/semantic/em/reports/experiment72_dataset.json').read_text(encoding='utf-8-sig'))
    originals=[OriginalTurn('experiment072',r['model'],r['turn'],r['user_message'],r['ai_response']) for r in source]
    reader=Reader({**AUTH,'extraction_model':'gpt-4.1-2025-04-14'})
    for index,row in enumerate(rows):
        if row['status']!='BLOCKED':continue
        original=authorized_context(originals,row['conversation'],row['model'],row['turn'])
        code=row['code'];requests=[]
        if code=='CE10' and original['turn']==1 and not original['prior_history']:
            decision={'code':code,'status':'N/A','score':None,'reason':contracts()[code]['applicability_literal'],
                'verified_gate_basis':{'original_input_sha256':original['input_sha256'],'turn':1,'prior_history':[],
                    'official_rubric_sha256':'ac24c12bcc048c53d2749927ce7d19776ba7ecfa2d45441a90f81d7251e5439c'}}
        else:
            def collect(request):
                request['indicators']={code:request['indicators'][code]}
                request['instruction']+=' Evalúa exclusivamente este código. Razones concisas y citas mínimas suficientes. Un componente de ausencia verificada se justifica tras revisar toda la respuesta, citando el objeto examinado; no exige una frase prohibida inexistente.'
                requests.append(request);return {}
            if code.startswith('EM'):em.run_family(original,reader=collect)
            else:routes.run_family(original,code[:2],reader=collect)
            reserve=sum(Decimal(estimate(q,'gpt-4.1-2025-04-14')['reserved_upper_bound_usd']) for q in requests)
            if reserve>Decimal(accounting()['available_after_reserves_usd']):break
            print(json.dumps({'target':code,'pair_reserve_usd':str(reserve),'accounting':accounting()}),flush=True)
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(reader,requests))
            except Exception as error:
                save(directory/'transport_block.json',{'type':type(error).__name__,'message':str(error)});break
            context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
            decision=em.adjudicate(code,context,a['indicators'][code],b['indicators'][code]) if code.startswith('EM') else routes.adjudicate(code,context,a['indicators'][code],b['indicators'][code])
        rows[index]={**row,**decision,'applicability':'NOT_APPLICABLE' if decision['status']=='N/A' else 'APPLICABLE' if decision['status']=='SCORED' else 'UNRESOLVED',
                     'gate_reason':decision['reason'] if decision['status']=='N/A' else ''}
        save(directory/(original['input_sha256']+'_'+code+'.json'),{'original':original,'before':row,'after':rows[index]})
        print(json.dumps({'target':code,'status':decision['status'],'score':decision['score']}),flush=True)
    export_new(directory/'tables',rows)
    save(directory/'accounting.json',accounting())

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv)>2 and sys.argv[2]=='targeted':targeted(sys.argv[1])
    elif len(sys.argv)>2 and sys.argv[2] in ('corpus','pilot'):corpus(sys.argv[1],pilot=sys.argv[2]=='pilot')
    else:focal(sys.argv[1],strong=len(sys.argv)>2 and sys.argv[2]=='strong')
