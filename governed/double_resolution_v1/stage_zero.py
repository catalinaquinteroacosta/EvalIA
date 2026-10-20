"""Opt-in new-manifest normal evaluation. Historical jobs retain their reader."""
import copy
from backend import luna_reader,luna_runner
from backend.evaluators.nd.contracts import TurnContext,HistoryTurn
from backend.evaluators.ansiedad_semantic.result_tables import aggregate
from backend.evaluators.transversal_candidate_v1.integration_runner import aggregate_v2
from .literal_context import enrich_body
from .scoring_adapter import candidate,REG
RELEASE='LUNA-LITERAL-STAGE0-20261017-1'
def factories(transport,certificates=None):
    def literal_transport(body,endpoint):return transport(enrich_body(body),endpoint)
    class LiteralProvider(luna_reader.LunaProvider):
        def qualified_for_pair(self,code,context,audit_start):
            # Do not reuse an older certificate whose prompt omitted the rubric.
            proof=(certificates or {}).get(code,{})
            if not isinstance(proof,dict) or proof.get('literal_context_release')!=RELEASE:return False
            return super().qualified_for_pair(code,context,audit_start)
    provider=LiteralProvider(literal_transport,certificates=certificates)
    class Runner(luna_runner.IntegrationRunner):
        def evaluate_response(self,rid):
            native=super().evaluate_response(rid)
            native['normal_reader_release']=RELEASE
            if native['rubric_type']!='ansiedad_depresion':return native
            audit=native['audit'];original=audit['original'];ctx=TurnContext(original['user'],original['response'],tuple(HistoryTurn(**r) for r in original['prior_history']))
            old=copy.deepcopy(native['indicator_results']);rows=copy.deepcopy(old);corrections=[]
            for row in rows:
                code=row['code']
                if row['status']!='BLOCKED' or code not in REG:continue
                family=audit['families'][row['family']]
                a=row.get('extraction') or family.get('extraction',{}).get('indicators',{}).get(code)
                b=row.get('independent_verification') or row.get('verification') or family.get('independent_verification',{}).get('indicators',{}).get(code)
                if not a or not b:continue
                r=candidate(code,ctx,a,b)
                if r['status']not in('SCORED','N/A'):continue
                row.update(status=r['status'],score=r['score'],reason=r['reason'],applicability='APPLICABLE' if r['status']=='SCORED' else 'NOT_APPLICABLE',gate_reason=r['reason'] if r['status']=='N/A' else '',validation_release='negative-coverage-v2')
                corrections.append(dict(code=code,status=r['status'],score=r['score']))
            native['original_rows_before_validation_correction']=old;native['indicator_results']=rows
            audit['rows']=rows;audit['summary']=aggregate(rows,expected_count=81)
            native['aggregation']=aggregate_v2(rows,{r['code']:r['family'] for r in rows});native['local_validation_corrections']=corrections
            return native
    return Runner,provider,lambda request:luna_reader.read_anxiety(request,literal_transport)
