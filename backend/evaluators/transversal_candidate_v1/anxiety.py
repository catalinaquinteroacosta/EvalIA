"""Per-indicator containment over frozen v3 contracts and scoring."""
from copy import deepcopy
from backend.evaluators.ansiedad_candidate_v3.engine import verify_frozen,adjudicate as frozen_adjudicate
from backend.evaluators.ansiedad_candidate_v3.reader_contract import candidate_request
from backend.evaluators.ansiedad_semantic import component_routes,em_component_adapter
from backend.evaluators.ansiedad_semantic.identified_context import authorized_context
from backend.evaluators.ansiedad_semantic.official_contracts import EXPECTED
from backend.evaluators.ansiedad_semantic.result_tables import aggregate
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn

VERSION='ANXIETY-ISOLATION-CANDIDATE-20261014-1'
def blocked(code,cause):return {'code':code,'status':'BLOCKED','score':None,'reason':cause}

def adjudicate(code,context,a,b,*,resource_checks=()):
    try:
        # Validate the required reasons before entering legacy .strip() calls.
        # Inactive components under a jointly absent gate remain irrelevant.
        required=set(component_routes.definitions(code)) if not code.startswith('EM') else set(em_component_adapter.COMPONENT_DESCRIPTIONS[code])
        readers=[r.get('components',{}) if isinstance(r,dict) else {} for r in (a,b)]
        if 'gate_present' in required and all(isinstance(r,dict) and isinstance(r.get('gate_present'),dict) and r['gate_present'].get('value') is False for r in readers):
            required={'gate_present'}
        if code=='ND1' and all(isinstance(r,dict) and isinstance(r.get('distorted_interpretation_identifiable'),dict) and r['distorted_interpretation_identifiable'].get('value') is False for r in readers):
            required={'distorted_interpretation_identifiable'}
        for role,rows in zip(('extract','independent_verify'),readers):
            if isinstance(rows,dict):
                for name in sorted(required):
                    row=rows.get(name)
                    if isinstance(row,dict):
                        if 'reason' not in row:return blocked(code,'missing_reason:'+role+':'+name)
                        if not isinstance(row['reason'],str):return blocked(code,'invalid_reason_type:'+role+':'+name)
                        if not row['reason'].strip():return blocked(code,'empty_reason:'+role+':'+name)
        if code=='PS5':return component_routes.adjudicate(code,context,a,b,resource_checks=resource_checks)
        return frozen_adjudicate(code,context,a,b)
    except (AttributeError,TypeError,ValueError,KeyError,IndexError) as error:
        # Diagnose the unmodified malformed observation; never cast a reason.
        for role,reading in [('extract',a),('independent_verify',b)]:
            if isinstance(reading,dict) and isinstance(reading.get('components'),dict):
                for name,row in reading['components'].items():
                    if isinstance(row,dict) and 'reason' in row and not isinstance(row['reason'],str):
                        return blocked(code,'invalid_reason_type:'+role+':'+name)
        return blocked(code,'invalid_indicator_protocol:'+type(error).__name__)

def run_family(identified,family,*,reader,resource_checks=()):
    """Reuse exact canonical request builders; only dispatch isolation changes."""
    requests=[]
    def capture(q):requests.append(deepcopy(q));return {}
    template=(em_component_adapter.run_family(identified,reader=capture) if family=='EM'
              else component_routes.run_family(identified,family,reader=capture,resource_checks=resource_checks))
    assert len(requests)==2 and [q['stage'] for q in requests]==['extract','independent_verify']
    requests=[candidate_request(q) for q in requests]
    codes=set(requests[0]['indicators']);assert codes==set(requests[1]['indicators'])
    fixed={c:deepcopy(r) for c,r in template['results'].items() if c not in codes}
    results=dict(fixed)
    try:
        a=reader(deepcopy(requests[0]));b=reader(deepcopy(requests[1]))
        for payload in (a,b):
            if not isinstance(payload,dict) or set(payload)!={'indicators'} or not isinstance(payload['indicators'],dict):
                raise ValueError('invalid_family_envelope')
            if set(payload['indicators'])-codes:raise ValueError('unrequested_indicator_in_family')
    except Exception as e:
        results.update({c:blocked(c,'family_transport_or_envelope:'+type(e).__name__+':'+str(e)) for c in codes})
        return {'results':results,'transport_error':str(e),'rule_version':VERSION}
    context=TurnContext(identified['user'],identified['response'],tuple(HistoryTurn(**r) for r in identified['prior_history']))
    for code in sorted(codes):
        if code not in a['indicators'] or code not in b['indicators']:
            results[code]=blocked(code,'missing_indicator_reading:'+code)
        else:results[code]=adjudicate(code,context,a['indicators'][code],b['indicators'][code],resource_checks=resource_checks)
    return {'results':results,'extraction':a,'independent_verification':b,'input_sha256':identified['input_sha256'],'rule_version':VERSION}

def evaluate_turn(originals,conversation,model,turn,*,reader,resource_checks=()):
    verify_frozen();identified=authorized_context(originals,conversation,model,turn);rows=[];families={}
    for family,count in EXPECTED.items():
        families[family]=run_family(identified,family,reader=reader,resource_checks=resource_checks)
        for n in range(1,count+1):
            r=families[family]['results'][family+str(n)];status=r['status']
            rows.append({**r,'conversation':conversation,'model':model,'turn':turn,'family':family,
               'input_sha256':identified['input_sha256'],'engine_version':VERSION,
               'applicability':'APPLICABLE' if status=='SCORED' else 'NOT_APPLICABLE' if status=='N/A' else 'UNRESOLVED',
               'gate_reason':r['reason'] if status=='N/A' else ''})
    return {'original':identified,'rows':rows,'families':families,'summary':aggregate(rows,expected_count=81),
            'clinical_validation':False,'engine_version':VERSION}
