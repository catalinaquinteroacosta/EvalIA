"""Isolated Luna composition over immutable family scoring and aggregation."""
from backend.evaluators.transversal_candidate_v1.integration_runner import IntegrationRunner as Previous,aggregate_v2
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn,authorized_context
from crisis_semantic.domain import Input,Turn,load_contracts
from backend.luna_application import BatchPending

VERSION='LUNA-ISOLATED-UNQUALIFIED-STEP3-20261015'


class IntegrationRunner(Previous):
    def evaluate_response(self,response_id):
        if type(response_id) is not int or response_id<1:raise ValueError('invalid_response_id')
        record=self.resolve_response(response_id)
        if record['rubric_type']!='crisis':
            result=Previous(lambda _:record,crisis_provider=self.crisis_provider,anxiety_reader=self.anxiety_reader,
                external_attestations=self.external_attestations,resource_checks=self.resource_checks).evaluate_response(response_id)
            result['reader_model']='gpt-6-luna'
            result['reader_release']=VERSION
            return result
        from backend.luna_reader import LunaCrisisEvaluator
        model=record['model'];turn=record['turn'];conversation=record['conversation']
        originals=tuple(OriginalTurn(**r) for r in record['originals'])
        authorized_context(originals,conversation,model,turn)
        permitted=sorted((r for r in originals if r.conversation==conversation and r.model==model and r.turn<=turn),key=lambda r:r.turn)
        context=Input(Turn(turn,permitted[-1].user,permitted[-1].response,model),
            tuple(Turn(r.turn,r.user,r.response,model) for r in permitted[:-1]))
        contracts=load_contracts()[0]
        # Own focal qualification is valid only for exact single-code scope.
        # Compose disjoint code sets; never rescore or replace an observation.
        evaluator=LunaCrisisEvaluator(self.crisis_provider,external_attestations=self.external_attestations)
        special=('CR-RI2','CR-CE10')
        native=evaluator.evaluate(context,[code for code in contracts if code not in special])
        isolated=[]
        for code in special:
            part=evaluator.evaluate(context,[code]);isolated.append(part)
            native['results'].extend(part['results'])
        native['isolated_qualification_routes']=isolated
        if len(native['results'])!=len(contracts) or {r['code'] for r in native['results']}!=set(contracts):
            raise ValueError('luna_composed_indicator_inventory_mismatch')
        rows=native['results'];inventory={c:d['family_code'] for c,d in contracts.items()}
        return dict(response_id=response_id,rubric_type='crisis',turn_number=turn,release=VERSION,engine=VERSION,
            reader_model='gpt-6-luna',indicator_results=rows,aggregation=aggregate_v2(rows,inventory),audit=native,
            clinical_validation=False)


def dependencies(queue,*,allowed_experiment_ids,certificate=None):
    """Opt-in server dependency injection; no key, network or default activation.

    All requests are planned before surfacing pending. Placeholders are never
    persisted: the factory raises BatchPending after complete family traversal.
    """
    from backend.luna_reader import LunaProvider,adapt_body,decode_anxiety
    from backend.evaluators.ansiedad_semantic.budgeted_reader import envelope
    def anxiety(request):
        body=envelope(request,'gpt-6-luna')
        # envelope's original API returns a request body; no schema rewriting.
        body=adapt_body(body,family='ansiedad_depresion',stage=request['stage'])
        try:raw=queue(body,'chat/completions')
        except BatchPending:return {'indicators':{}}
        return decode_anxiety(raw,request)
    # Provider verifies each proof against its own reader identity and evidence;
    # absent/old/incompatible proofs leave RI2/CE10 technically blocked.
    provider=LunaProvider(queue,certificates=certificate)
    class PendingSafeRunner(IntegrationRunner):
        def evaluate_response(self,response_id):
            queue.pending.clear()
            selected=super().evaluate_response(response_id)
            if queue.pending:raise BatchPending(queue.pending)
            return selected
    return dict(runner_factory=PendingSafeRunner,crisis_provider=provider,anxiety_reader=anxiety,
        anxiety_model='gpt-6-luna',allowed_experiment_ids=frozenset(allowed_experiment_ids),evaluation_lock=queue.lock,
        paid_mode='batch',paid_submission_enabled=False)
