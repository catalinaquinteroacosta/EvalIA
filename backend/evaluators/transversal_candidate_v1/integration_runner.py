"""Reversible isolated runner for authoritative response IDs; no database writes.

The response resolver and semantic readers are server dependencies, never HTTP
input. A separate ASGI mount selects this runner without changing main.py.
"""
from collections import defaultdict
from pathlib import Path
import json
from .frontend_candidate import CrisisEvaluator,evaluate_anxiety_turn,RELEASE
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn
from crisis_semantic.domain import Input,Turn,load_contracts

ROOT=Path(__file__).resolve().parents[3]

def aggregate_v2(rows,inventory):
    groups=defaultdict(list)
    valid=len(rows)==len(inventory) and {r['code'] for r in rows}==set(inventory)
    for row in rows:
        status=row['status'];score=row['score']
        if status=='SCORED':
            if type(score) is not int or score not in range(4): raise ValueError('invalid_scored_result')
            groups[inventory[row['code']]].append(score)
        elif status not in ('N/A','BLOCKED') or score is not None: raise ValueError('invalid_result_state')
        if status=='BLOCKED': valid=False
    criteria={family:round(sum(s)/(3*len(s))*100,2) for family,s in groups.items()}
    return dict(complete=valid,criteria_percentages=criteria,global_v2=round(sum(criteria.values())/len(criteria),2) if valid and criteria else None)

class IntegrationRunner:
    def __init__(self,resolve_response,*,anxiety_reader=None,crisis_provider=None,external_attestations=(),resource_checks=()):
        self.resolve_response=resolve_response
        self.anxiety_reader=anxiety_reader;self.crisis_provider=crisis_provider
        self.external_attestations=external_attestations;self.resource_checks=resource_checks

    def evaluate_response(self,response_id):
        if type(response_id) is not int or response_id<1: raise ValueError('invalid_response_id')
        record=self.resolve_response(response_id)
        rubric=record['rubric_type'];turn=record['turn'];model=record['model']
        originals=tuple(OriginalTurn(**r) for r in record['originals'])
        if rubric=='ansiedad_depresion':
            if self.anxiety_reader is None: raise RuntimeError('anxiety_reader_not_configured')
            result=evaluate_anxiety_turn(originals,record['conversation'],model,turn,reader=self.anxiety_reader,resource_checks=self.resource_checks)
            from backend.evaluators.ansiedad_semantic.official_contracts import EXPECTED
            rows=result['rows'];inventory={family+str(n):family for family,count in EXPECTED.items() for n in range(1,count+1)}
            engine='ANXIETY-ISOLATION-CANDIDATE-20261014-1'
        elif rubric=='crisis':
            if self.crisis_provider is None: raise RuntimeError('crisis_provider_not_configured')
            # Reuse the authoritative temporal validator for identities/gaps.
            from backend.evaluators.ansiedad_semantic.identified_context import authorized_context
            authorized_context(originals,record['conversation'],model,turn)
            permitted=sorted((r for r in originals if r.conversation==record['conversation'] and r.model==model and r.turn<=turn),key=lambda r:r.turn)
            context=Input(Turn(turn,permitted[-1].user,permitted[-1].response,model),tuple(Turn(r.turn,r.user,r.response,model) for r in permitted[:-1]))
            contracts=load_contracts()[0]
            result=CrisisEvaluator(self.crisis_provider,external_attestations=self.external_attestations).evaluate(context,list(contracts))
            rows=result['results'];inventory={c:d['family_code'] for c,d in contracts.items()}
            engine='CRISIS-NI6-v3 + B-CORRESPONDENCE-FIX-1 + COMPLETE-REVIEW-1'
        else: raise ValueError('unsupported_rubric')
        # Every canonical row, nullable score and evidence survives presentation.
        return dict(response_id=response_id,rubric_type=rubric,turn_number=turn,release=RELEASE,engine=engine,
                    indicator_results=rows,aggregation=aggregate_v2(rows,inventory),audit=result,
                    clinical_validation=False)

def create_app(runner):
    """ASGI HTTP integration mount; no FastAPI dependency or implicit provider.

    POST /api/responses/{id}/evaluate invokes the isolated selected runner.
    Stop/unmount this app to roll back; the existing app remains untouched.
    """
    async def app(scope,receive,send):
        if scope['type']=='lifespan':
            while True:
                event=await receive()
                if event['type']=='lifespan.startup': await send({'type':'lifespan.startup.complete'})
                elif event['type']=='lifespan.shutdown':
                    await send({'type':'lifespan.shutdown.complete'})
                    return
        if scope['type']!='http': raise ValueError('http_scope_required')
        parts=scope.get('path','').strip('/').split('/')
        status=200
        try:
            if len(parts)!=4 or parts[:2]!=['api','responses'] or parts[3]!='evaluate':
                status=404;data={'detail':'route_not_found'}
            elif scope.get('method')!='POST': status=405;data={'detail':'post_required'}
            else: data=runner.evaluate_response(int(parts[2]))
        except (ValueError,KeyError): status=422;data={'detail':'invalid_authoritative_response_context'}
        except RuntimeError as exc: status=503;data={'detail':str(exc)}
        body=json.dumps(data,ensure_ascii=False).encode()
        await send(dict(type='http.response.start',status=status,headers=[(b'content-type',b'application/json; charset=utf-8')]))
        await send(dict(type='http.response.body',body=body))
    return app

def connect_backend(*,get_response_context,build_evaluation_context,require_snapshot_current,**readers):
    """Connect the existing backend's authoritative lookup/snapshot functions.

    Pass main._get_response_context, main._build_evaluation_context and
    main._require_experiment_snapshot_current from the server composition root.
    The normal database lookup remains read-only; this app never saves results.
    """
    def resolve(response_id):
        raw=get_response_context(response_id)
        require_snapshot_current(int(raw['experiment_id']),raw['scenario_code'],int(raw['scenario_id']))
        context=build_evaluation_context(raw)
        if context.experiment_id!=int(raw['experiment_id']) or context.model_name!=raw['model_name']:
            raise ValueError('authoritative_context_identity_mismatch')
        conversation=str(context.experiment_id)+':'+context.scenario_code
        return dict(rubric_type=context.rubric_type,model=context.model_name,turn=int(raw['turn_number']),conversation=conversation,
                    originals=[dict(conversation=conversation,model=context.model_name,turn=t.turn_number,user=t.user_message,response=t.ai_response) for t in context.turns])
    return create_app(IntegrationRunner(resolve,**readers))
