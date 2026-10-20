"""Append-only USD7 night authorization; reuse verified 072 rows, no SQLite."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from .budgeted_reader import Reader, ROOT, estimate
from .run_authorized_validation import save
from .identified_context import OriginalTurn, authorized_context
from .result_tables import export_new, grouped, aggregate
from .official_contracts import EXPECTED
from . import component_routes as routes, em_component_adapter as em
from backend.evaluators.nd.contracts import TurnContext, HistoryTurn

AUTH = {'explicit_user_approval': True,
        'authorization_id': 'ANXIETY-20261012-NIGHT-ADDITIONAL-7.00',
        'additional_cap_usd': '12.00',
        'extraction_model': 'gpt-4.1-mini-2025-04-14',
        'verification_model': 'gpt-4.1-2025-04-14',
        'outstanding_reservations_usd': '0',
        'authority': 'ca98b3b4-d3d6-40fa-8a6d-be323195b576/Pasted text.txt: explicit USD5 amendment to original USD7; same stable ledger authorization, total USD12; all historical reservations retained; no CRISIS funds.',
        'original_cap_usd':'7.00','amendment_usd':'5.00'}
BALANCE_CHECKPOINT=ROOT/'balance_checkpoint_20261013_global.json'
if not BALANCE_CHECKPOINT.exists():BALANCE_CHECKPOINT=ROOT/'balance_checkpoint_20261013.json'
if BALANCE_CHECKPOINT.exists():
    balance_record=json.loads(BALANCE_CHECKPOINT.read_text(encoding='utf-8'))
    AUTH['authorized_total_cap_usd']=AUTH['additional_cap_usd']
    AUTH['additional_cap_usd']=str(min(Decimal(AUTH['additional_cap_usd']),Decimal(balance_record['cumulative_operational_cap_usd'])))
    AUTH['user_reported_balance_checkpoint']=str(BALANCE_CHECKPOINT)
BASE = Path('docs/ansiedad_semantic/live_990_20261012')

def accounting():
    events = [json.loads(s) for s in (ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    reserves = {e['attempt']: Decimal(e['reserved_usd']) for e in events
                if e['kind']=='reserved' and e['authorization']==AUTH['authorization_id']}
    settled = {e['attempt']: Decimal(e['actual_usd']) for e in events
               if e['kind']=='settled' and e['attempt'] in reserves}
    committed = sum((settled.get(k,v) for k,v in reserves.items()), Decimal(0))
    return {'attempts': len(reserves), 'settled': len(settled),
            'actual_usd': str(sum(settled.values(),Decimal(0))),
            'uncertain_reserves_usd': str(sum((v for k,v in reserves.items() if k not in settled),Decimal(0))),
            'committed_usd':str(committed), 'available_usd':str(max(Decimal(0),Decimal(AUTH['additional_cap_usd'])-committed)),
            'reserve_shortfall_usd':str(max(Decimal(0),committed-Decimal(AUTH['additional_cap_usd'])))}

def initial_rows():
    rows=json.loads((BASE/'corpus_8/tables/observations.json').read_text(encoding='utf-8'))
    updates=[]
    p=BASE/'pa8_final_contrast_v2/original_072.json'
    saved=json.loads(p.read_text(encoding='utf-8'))
    updates.append(('PA8',saved['decision'],saved['original'],p))
    p=BASE/'role_gates_final_v2/results.json'
    saved=json.loads(p.read_text(encoding='utf-8'))
    updates.extend((c,d,saved['original'],p) for c,d in saved['results'].items())
    for code,decision,original,path in updates:
        for row in rows:
            if (row['model'],row['turn'],row['code'])==('ChatGPT',1,code):
                row.update(**decision)
                row.update(input_sha256=original['input_sha256'],
                           verified_evidence=str(path),
                           applicability='APPLICABLE' if decision['status']=='SCORED' else 'NOT_APPLICABLE',
                           gate_reason=decision['reason'] if decision['status']=='N/A' else '')
    consolidated=sorted(BASE.glob('night_consolidated_*/tables/observations.json'))
    if consolidated:
        rows=json.loads(consolidated[-1].read_text(encoding='utf-8'))
    return rows

def run(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    save(directory/'authorization.json',AUTH)
    save(directory/'ledger_before.json',{'accounting':accounting(),
         'ledger_sha256':sha256((ROOT/'ledger.jsonl').read_bytes()).hexdigest()})
    rows=initial_rows()
    # Resume immutable night outputs if a prior invocation already completed pairs.
    for path in sorted(directory.parent.glob('night_*/pair_*.json')):
        if path.parent==directory:continue
        packet=json.loads(path.read_text(encoding='utf-8'))
        for update in packet.get('results',[]):
            for index,row in enumerate(rows):
                if tuple(row[k] for k in ('model','turn','code'))==tuple(update[k] for k in ('model','turn','code')):
                    rows[index]={**update,'verified_evidence':str(path)}
    save(directory/'baseline.json',aggregate(rows))
    data=json.loads(Path('backend/evaluators/semantic/em/reports/experiment72_dataset.json').read_text(encoding='utf-8-sig'))
    originals=[OriginalTurn('experiment072',r['model'],r['turn'],r['user_message'],r['ai_response']) for r in data]
    index={(r['model'],r['turn'],r['code']):i for i,r in enumerate(rows)}
    pairs=[]
    # Breadth first: untouched originals before retrying previous discrepancies.
    for state in ('PENDING','BLOCKED'):
        for original in sorted(originals,key=lambda r:(r.turn,r.model)):
            for family,count in EXPECTED.items():
                codes=[f'{family}{n}' for n in range(1,count+1)
                       if rows[index[original.model,original.turn,f'{family}{n}']]['status']==state]
                if codes:pairs.append((state,original,family,codes))
    stop=None;attempted=set()
    for number,(state,r,family,codes) in enumerate(pairs,1):
        codes=[c for c in codes if (r.model,r.turn,c) not in attempted
               and rows[index[r.model,r.turn,c]]['status'] not in ('SCORED','N/A')]
        if not codes:continue
        original=authorized_context(originals,r.conversation,r.model,r.turn)
        requests=[]
        def collect(q):
            q['indicators']={c:v for c,v in q['indicators'].items() if c in codes}
            q['instruction']+=' Razones breves y citas suficientes. Distingue conducta central del indicador de ayuda general; comprueba contradicciones entre componentes. No puntúes.'
            requests.append(q);return {}
        if family=='EM':em.run_family(original,reader=collect)
        else:routes.run_family(original,family,reader=collect)
        if not requests:continue
        auth={**AUTH,'extraction_model':'gpt-4.1-2025-04-14'} if state=='BLOCKED' or family in ('ND','EM') else AUTH
        reserve=sum(Decimal(estimate(q,auth['extraction_model' if q['stage']=='extract' else 'verification_model'])['reserved_upper_bound_usd']) for q in requests)
        plan={'model':r.model,'turn':r.turn,'family':family,'codes':codes,'prior_state':state,
              'pair_upper_bound_usd':str(reserve),'retry_allowance':0,'accounting':accounting()}
        save(directory/f'estimate_{number:04d}.json',plan)
        if reserve>Decimal(accounting()['available_usd']):
            stop='Next full pair cannot fit reserved USD7 night budget.';break
        print(json.dumps(plan),flush=True)
        reader=Reader(auth)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:a,b=list(pool.map(reader,requests))
        except Exception as error:
            stop=f'{type(error).__name__}: {error}'
            save(directory/f'transport_{number:04d}.json',{'original':original,'error':stop,'accounting':accounting()})
            for code in codes:
                rows[index[r.model,r.turn,code]].update(status='BLOCKED',score=None,applicability='UNRESOLVED',reason=stop)
            break
        context=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**h) for h in original['prior_history']))
        decisions=[]
        for code in requests[0]['indicators']:
            attempted.add((r.model,r.turn,code))
            try:
                x,y=a['indicators'][code],b['indicators'][code]
                d=em.adjudicate(code,context,x,y) if family=='EM' else routes.adjudicate(code,context,x,y)
            except Exception as error:d={'code':code,'status':'BLOCKED','score':None,'reason':f'{type(error).__name__}: {error}'}
            row={**d,'conversation':r.conversation,'model':r.model,'turn':r.turn,'family':family,
                 'input_sha256':original['input_sha256'],
                 'applicability':'APPLICABLE' if d['status']=='SCORED' else 'NOT_APPLICABLE' if d['status']=='N/A' else 'UNRESOLVED',
                 'gate_reason':d['reason'] if d['status']=='N/A' else '',
                 'verified_evidence':str(directory/f'pair_{number:04d}.json')}
            rows[index[r.model,r.turn,code]]=row;decisions.append(row)
        save(directory/f'pair_{number:04d}.json',{'original':original,'extraction':a,'independent_verification':b,'results':decisions})
        print(json.dumps({'pair':number,'counts':dict(Counter(d['status'] for d in decisions)),'accounting':accounting()}),flush=True)
    export_new(directory/'tables',rows)
    save(directory/'groups.json',{n:grouped(rows,fields) for n,fields in
         {'family':('family',),'indicator':('code',),'model':('model',),'turn':('model','turn'),'conversation':('conversation','model')}.items()})
    save(directory/'summary.json',{'results':aggregate(rows),'accounting':accounting(),'stop_reason':stop,'clinical_validation':False})

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8');run(sys.argv[1])
