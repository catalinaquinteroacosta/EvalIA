"""Unmounted isolated runner selecting the exact pending-ten final candidate."""
from .integration_runner import IntegrationRunner as Previous,aggregate_v2,create_app
from .adenda_release_next import CrisisEvaluator
VERSION='CRISIS-ADENDA-CANDIDATE-20261014-1'
from backend.evaluators.ansiedad_semantic.identified_context import OriginalTurn,authorized_context
from crisis_semantic.domain import Input,Turn,load_contracts

class IntegrationRunner(Previous):
    def evaluate_response(self,response_id):
        if type(response_id) is not int or response_id<1:raise ValueError('invalid_response_id')
        record=self.resolve_response(response_id)
        if record['rubric_type']!='crisis':
            # Reuse the exact authoritative record; no second lookup with changing data.
            delegate=Previous(lambda _:record,anxiety_reader=self.anxiety_reader,
                crisis_provider=self.crisis_provider,external_attestations=self.external_attestations,
                resource_checks=self.resource_checks)
            return delegate.evaluate_response(response_id)
        if self.crisis_provider is None:raise RuntimeError('crisis_provider_not_configured')
        model=record['model'];turn=record['turn'];conversation=record['conversation']
        originals=tuple(OriginalTurn(**r) for r in record['originals'])
        authorized_context(originals,conversation,model,turn)
        permitted=sorted((r for r in originals if r.conversation==conversation and r.model==model and r.turn<=turn),key=lambda r:r.turn)
        context=Input(Turn(turn,permitted[-1].user,permitted[-1].response,model),
            tuple(Turn(r.turn,r.user,r.response,model) for r in permitted[:-1]))
        contracts=load_contracts()[0]
        result=CrisisEvaluator(self.crisis_provider,external_attestations=self.external_attestations).evaluate(context,list(contracts))
        rows=result['results'];inventory={c:d['family_code'] for c,d in contracts.items()}
        return dict(response_id=response_id,rubric_type='crisis',turn_number=turn,
            release=VERSION,engine=VERSION,indicator_results=rows,
            aggregation=aggregate_v2(rows,inventory),audit=result,clinical_validation=False,
            review_required=[dict(code=r['code'],cause=r['technical_cause']) for r in rows if r['score'] is None and r['status']!='N/A'])
