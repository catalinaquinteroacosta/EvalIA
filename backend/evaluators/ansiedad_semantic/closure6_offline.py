"""Read-only recovery audit. No provider, cache or ledger mutation."""
from pathlib import Path
import copy
import hashlib
import json
from decimal import Decimal
from .claim_verifier import verification_request
from .budgeted_reader import estimate

BASE = Path('docs/ansiedad_semantic/finish_20261013')
OUT = Path('docs/ansiedad_semantic/closure6_20261013/offline_01')

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def run():
    OUT.mkdir(parents=True, exist_ok=False)
    def save(name, value):
        (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    baseline=BASE/'final_02'
    integrity=[]
    for item in read(baseline/'files.json'):
        p=Path(item['path'])
        actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        integrity.append({'path':str(p),'expected':item['sha256'],'actual':actual,'matches':actual==item['sha256']})
    save('baseline_hash_checks.json',integrity)
    matrix=read(baseline/'fidelity_matrix.json')
    contracts={r['code']:r['official'] for r in matrix}
    blocks=read(baseline/'blocked_causes.json')
    flags=read(baseline/'semantic_review_flags.json')
    save('critical_alerts_preserved.json',flags)
    register=[]
    for i,row in enumerate(blocks):
        reason=row.get('reason','')
        category=('insufficient_evidence' if 'evidencia' in reason.lower() or 'cita' in reason.lower()
                  else 'reader_contract')
        register.append({'id':f'blocked-{i+1:03d}',**row,'cause_class':category,
            'official':contracts[row['code']], 'state':'BLOCKED','priority':1,
            'action':'Inspect original paired components; preserve accepted readings; require independently verified correction of the exact disputed facts.',
            'closure_criterion':'Literal valid evidence and coherent agreed components support an official deterministic descriptor; no target score imposed.'})
    gaps={r['code']:r for r in read(baseline/'coverage_gaps.json')}
    discrepancies=read(baseline/'hypothesis_discrepancies.json')
    coverage=[]
    for r in matrix:
        code=r['code']
        coverage.append({'code':code,'official':contracts[code],
            'implementation_traceability':r,
            'observed_gap':gaps.get(code),
            'hypothesis_mismatches':[d for d in discrepancies if d['code']==code],
            'reachability_state':'NEEDS_CONTEXT_REVIEW' if code in gaps else 'OBSERVED_COVERAGE',
            'rule':'Missing observed levels are not proof of a defect or an obligation to realize all levels in every context. Match each fixture to the full descriptor and active gate before designing another call.',
            'independent_validation_complete':False if code in gaps else None})
    save('coverage_review_81.json',coverage)
    save('CLOSURE_REGISTER.json',register)
    ledger=Path('backend/evaluators/ansiedad_semantic/private/integral_reader/ledger.jsonl')
    raw=ledger.read_bytes()
    events=[json.loads(s) for s in raw.decode('utf-8').splitlines()]
    settled={e['attempt'] for e in events if e['kind']=='settled'}
    pending=[e for e in events if e['kind']=='reserved' and e['attempt'] not in settled]
    save('ledger_reconciliation.json',{'sha256':hashlib.sha256(raw).hexdigest(),
        'events':len(events),'pending_reservations':pending,
        'all_anxiety_uncertain_usd':str(sum((Decimal(e['reserved_usd']) for e in pending),Decimal(0))),
        'external_crisis_retention_usd':'0.5733136','released_reserves':0,'paid_calls':0,
        'binding_accounting':read(baseline/'summary.json')['accounting'],
        'policy':'No new operational funds or paid authorization. No inference of billing settlement.'})
    saved=read(BASE/'step3_engine_01/call_17.json')
    request=copy.deepcopy(saved['request'])
    request['stage']='independent_verify'
    request=verification_request(request,saved['reading'])
    save('CE_verifier_request_PREPARED_NOT_SENT.json',request)
    save('CE_verifier_plan.json',{'state':'BLOCKED','paid_calls':0,
        'model':'gpt-4.1-2025-04-14', 'configured_rate_estimate':estimate(request,'gpt-4.1-2025-04-14'),
        'historical_plan':read(BASE/'step3_engine_01/call_18_plan.json'),
        'reuse':'17 outputs retained; extraction call_17 reused; pending attempt968 reservation not released.',
        'prerequisites':['Reconcile real cash and all holds','Revalidate current request contract and dedup hash before sending','Obtain genuine independent CE output; never synthesize verifier']})
    save('step_states.json',{'1':'CLOSED: recovery register and offline accounting; no paid calls',
        '2':'BLOCKED: PA1/IR2 definition refinements require independent semantic validation; PS6/CE3/CE9 preserved unqualified',
        '3':'BLOCKED: six original disputed readings preserved; no manual conversion',
        '4':'BLOCKED: 81-code source matrix recovered; per-context reachability review not completed',
        '5':'BLOCKED: verifier prepared, not sent; 17 outputs preserved',
        '6':'BLOCKED: NO APTO until critical semantic checks and coverage resolved'})
    assert ledger.read_bytes()==raw
    print(json.dumps({'output':str(OUT),'indicators':len(coverage),'blocked_entries':len(register),'api_calls':0}))

if __name__=='__main__':run()
