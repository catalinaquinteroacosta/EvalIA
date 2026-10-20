"""Recover only saved real API outputs after interruption; never send another call."""
from pathlib import Path
from hashlib import sha256
import copy,json
from .identified_context import OriginalTurn
from .claim_verifier import ClaimAuditReader
from .engine import evaluate_turn
from .result_tables import export_new
from .run_authorized_validation import save

def run(target):
    target=Path(target)
    if (target/'engine_result.json').exists():raise ValueError('Do not overwrite an existing integration result')
    case=json.loads((target/'reserved_case.json').read_text(encoding='utf-8'));o=case['original']
    originals=[]
    for index in range(0,len(o['prior_history']),2):
        originals.append(OriginalTurn(o['conversation'],o['model'],index//2+1,o['prior_history'][index]['text'],o['prior_history'][index+1]['text']))
    originals.append(OriginalTurn(o['conversation'],o['model'],o['turn'],o['user'],o['response']))
    originals.append(OriginalTurn(o['conversation'],o['model'],o['turn']+1,'FUTURE_POISON_DO_NOT_USE','FUTURE_POISON_DO_NOT_USE'))
    originals.append(OriginalTurn(o['conversation'],'OTHER_MODEL_DO_NOT_USE',1,'OTHER_MODEL_POISON_DO_NOT_USE','OTHER_MODEL_POISON_DO_NOT_USE'))
    recorded={}
    for file in target.glob('call_*.json'):
        if '_plan' in file.name:continue
        packet=json.loads(file.read_text(encoding='utf-8'));q=packet['request']
        recorded[(q['stage'],tuple(q['indicators']))]=packet
    missing=[]
    def replay(q):
        packet=recorded.get((q['stage'],tuple(q['indicators'])))
        if packet is None:
            missing.append({'stage':q['stage'],'codes':list(q['indicators'])})
            raise ValueError('Real API pair incomplete after financial reconciliation interruption; no synthetic replacement')
        if packet['request']['original']!=q['original'] or packet['request']['indicators']!=q['indicators']:
            raise ValueError('Saved response belongs to a different original or contract')
        return copy.deepcopy(packet['reading'])
    result=evaluate_turn(originals,o['conversation'],o['model'],o['turn'],reader=ClaimAuditReader(replay))
    result['recovery']={'new_api_calls':0,'real_saved_outputs':len(recorded),'missing_stages':missing,
        'integration_status':'INTERRUPTED_FOR_GLOBAL_RESERVE_RECONCILIATION'}
    save(target/'engine_result.json',result);export_new(target/'tables',result['rows'])
    before=json.loads((target/'source_hashes_before.json').read_text(encoding='utf-8'))
    unchanged=all(Path(path).is_file() and sha256(Path(path).read_bytes()).hexdigest()==value for path,value in before.items())
    save(target/'integration_checks.json',{'entry_point':'backend.evaluators.ansiedad_semantic.engine.evaluate_turn',
        'real_provider_outputs':len(recorded),'recovery_api_calls':0,'rows':len(result['rows']),
        'families':len(result['families']),'codes_exact':len({r['code'] for r in result['rows']})==81,
        'history_equals_reserved_prior':result['original']['prior_history']==o['prior_history'],
        'own_history_only':all('POISON_DO_NOT_USE' not in json.dumps(p['request'],ensure_ascii=False) for p in recorded.values()),
        'original_source_hashes_unchanged_before_recovery':unchanged,'missing_stages':missing,
        'integration_complete':not missing,'summary':result['summary'],
        'deployment_scope':'Actual isolated research-engine path, partial real API verification; no production runner change.'})
    print(json.dumps(result['recovery']))

if __name__=='__main__':
    import sys
    run(sys.argv[1])
