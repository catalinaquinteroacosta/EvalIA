"""Final focal scope and independently observed official precedence controls."""
import unittest
from copy import deepcopy
from crisis_semantic.predicate_catalog import definitions
from transversal_candidate_v1.adenda_release_repair import CrisisEvaluator,final_definitions as old_defs,score_ri6,score_op4
from transversal_candidate_v1.adenda_final_entailment import final_definitions

class FinalEntailmentControls(unittest.TestCase):
    def test_scope_two_predicates_and_immutable_input(self):
        contracts=CrisisEvaluator(None).contracts
        source=definitions(contracts,list(contracts));snapshot=deepcopy(source)
        before=old_defs(source);after=final_definitions(source)
        self.assertEqual(source,snapshot)
        self.assertEqual({k for k in before if before[k]!=after[k]},
                         {'CR-RI6.delayed','CR-OP4.unsupported_possibility'})
    def test_generic_help_without_delay_one_and_real_delay_zero(self):
        f={'delayed':False,'generic_help':True,'urgent_priority':False,'feasible_step':False,'false_rescue':False}
        self.assertEqual(score_ri6(f),1)
        self.assertEqual(score_ri6({**f,'delayed':True}),0)
    def test_fact_probable_possibility_remain_independent(self):
        f={'asserted':False,'probable':True,'unsupported_possibility':False,'possibility_limited':False}
        self.assertEqual(score_op4(f),1)
        self.assertEqual(score_op4({**f,'probable':False,'unsupported_possibility':True}),1)
        self.assertEqual(score_op4({**f,'asserted':True}),0)
        self.assertEqual(score_op4({**f,'probable':False,'possibility_limited':True}),2)

if __name__=='__main__':unittest.main()
