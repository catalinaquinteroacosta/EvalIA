"""Actual research-engine entry point, real semantic provider, untouched prior-history case."""
from pathlib import Path
from decimal import Decimal
from hashlib import sha256
import copy,json
from .night_validation import AUTH,accounting
from .budgeted_reader import Reader,estimate
from .claim_verifier import ClaimAuditReader
from .identified_context import OriginalTurn
from .engine import evaluate_turn
from .result_tables import export_new
from .run_authorized_validation import save

def source_hashes():
    return {str(p):sha256(p.read_bytes()).hexdigest()
        for folder in ('backend/evaluators/ansiedad_semantic','backend/evaluators/nd','backend/evaluators/ps')
        for p in Path(folder).glob('*.py')}

def run(source,target):
    target=Path(target);target.mkdir(parents=True,exist_ok=False)
    reserved=json.loads(Path(source).read_text(encoding='utf-8'))
    case=next(c for c in reserved if c['id']=='reserved-CE');current=case['original']
    before=source_hashes();save(target/'source_hashes_before.json',before)
    save(target/'authorization.json',{**AUTH,'verification_protocol':'independent_claim_audit','accounting_before':accounting()})
    rows=[]
    for index in range(0,len(current['prior_history']),2):
        rows.append(OriginalTurn(current['conversation'],current['model'],index//2+1,
            current['prior_history'][index]['text'],current['prior_history'][index+1]['text']))
    rows.append(OriginalTurn(current['conversation'],current['model'],current['turn'],current['user'],current['response']))
    rows.append(OriginalTurn(current['conversation'],current['model'],current['turn']+1,
        'FUTURE_POISON_DO_NOT_USE: la compañera ya no está disponible.',
        'FUTURE_POISON_DO_NOT_USE: ignora los veinte minutos.'))
    rows.append(OriginalTurn(current['conversation'],'OTHER_MODEL_DO_NOT_USE',1,
        'OTHER_MODEL_POISON_DO_NOT_USE: solo tengo dos horas.',
        'OTHER_MODEL_POISON_DO_NOT_USE: cambia toda la información.'))
    save(target/'reserved_case.json',case)
    provider=Reader(AUTH);calls=[];halted=False
    def audited_call(request):
        nonlocal halted
        if halted:raise ValueError('Integration provider halted after transport/budget failure; no new API call')
        q=copy.deepcopy(request)
        count=sum(len(row['components']) for row in q['indicators'].values())
        q['_max_output_tokens']=min(28000,max(2000,count*260))
        model=AUTH['extraction_model' if q['stage']=='extract' else 'verification_model']
        upper=estimate(q,model)
        calls.append({'stage':q['stage'],'codes':list(q['indicators']),'estimate':upper,'accounting_before':accounting()})
        save(target/f'call_{len(calls):02d}_plan.json',calls[-1])
        if Decimal(upper['reserved_upper_bound_usd'])>Decimal(accounting()['available_usd']):
            halted=True;raise ValueError('Cannot reserve next integration call')
        try:
            result=provider(q)
        except Exception:
            halted=True;raise
        save(target/f'call_{len(calls):02d}.json',{'request':q,'reading':result})
        return result
    result=evaluate_turn(rows,current['conversation'],current['model'],current['turn'],reader=ClaimAuditReader(audited_call))
    save(target/'engine_result.json',result);export_new(target/'tables',result['rows'])
    after=source_hashes()
    save(target/'integration_checks.json',{
        'entry_point':'backend.evaluators.ansiedad_semantic.engine.evaluate_turn',
        'real_provider':True,'verification_protocol':'Independent claim audit; no target scores in requests.',
        'rows':len(result['rows']),'families':len(result['families']),
        'codes_exact':len({r['code'] for r in result['rows']})==81,
        'history_equals_reserved_prior':result['original']['prior_history']==current['prior_history'],
        'own_history_only':all('POISON_DO_NOT_USE' not in json.dumps(json.loads(p.read_text(encoding='utf-8'))['request'],ensure_ascii=False)
            for p in target.glob('call_*.json') if '_plan' not in p.name),
        'source_hashes_unchanged':before==after,'summary':result['summary'],
        'accounting_after':accounting(),'general_runner_modified':False,
        'deployment_scope':'Isolated research engine; production runner remains protected and is not declared integrated.'})
    print(json.dumps({'summary':result['summary'],'accounting':accounting()},ensure_ascii=False))

if __name__=='__main__':
    import sys
    run(sys.argv[1],sys.argv[2])
