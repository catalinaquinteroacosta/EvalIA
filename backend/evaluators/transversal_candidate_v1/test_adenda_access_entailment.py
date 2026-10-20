import unittest
from copy import deepcopy
from crisis_semantic.domain import Input,Turn
from crisis_semantic.predicate_catalog import definitions
from transversal_candidate_v1.adenda_release_next import final_definitions as previous
from transversal_candidate_v1.adenda_release_access import CrisisEvaluator,final_definitions

class AccessEntailment(unittest.TestCase):
    def test_scope_and_reader_route(self):
        seen=[]
        class Reader:
            qualified_components=set()
            def run(self,stage,system,content,schema,ids,identity):
                seen.append((stage,deepcopy(content['predicates'])))
                return dict(reviewed_entire_context=True,claims=[dict(id=k,state='unknown',citations=[],reason='Transport fixture only.') for k in ids])
        evaluator=CrisisEvaluator(Reader())
        defs=definitions(evaluator.contracts,['CR-RI6'])
        before=previous(defs);after=final_definitions(defs)
        self.assertEqual({k for k in before if before[k]!=after[k]},{'CR-RI6.feasible_step'})
        result=evaluator.evaluate(Input(Turn(1,'Necesito ayuda.','Podemos hablar.','m')),['CR-RI6'])
        self.assertEqual([s for s,d in seen],['extract','verify'])
        self.assertTrue(all(d==after for s,d in seen))
        self.assertIsNone(result['results'][0]['score'])
        self.assertEqual(final_definitions(definitions(evaluator.contracts,['CR-RI2','CR-CE10'])),previous(definitions(evaluator.contracts,['CR-RI2','CR-CE10'])))
