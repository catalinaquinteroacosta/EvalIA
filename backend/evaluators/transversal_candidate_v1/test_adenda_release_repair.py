import unittest
from crisis_semantic.predicate_catalog import definitions
from transversal_candidate_v1.adenda_v1 import CrisisEvaluator as Base,final_definitions as prior
from transversal_candidate_v1.adenda_release_repair import CrisisEvaluator,final_definitions,resolve_adenda

class ReleaseRepair(unittest.TestCase):
    def test_scope_and_normative_contracts(self):
        old=Base(None);new=CrisisEvaluator(None)
        self.assertEqual(old.contracts,new.contracts)
        defs=definitions(new.contracts,list(new.contracts))
        before=prior(defs);after=final_definitions(defs)
        self.assertEqual({k for k in before if before[k]!=after[k]}, {'CR-RI2.inhibiting','CR-RI6.delayed','CR-OP4.possibility_limited','CR-OP4.unsupported_possibility'})
    def test_unknown_inhibition_not_forced(self):
        contract=CrisisEvaluator(None).contracts
        facts=dict(direct=True,inhibiting=None,nonjudgmental=False,clear=True,situated=True,vague=False)
        score,cause=resolve_adenda('CR-RI2',facts,contract)
        self.assertIsNone(score)
        self.assertEqual(cause,'unresolved_components_change_adenda_level')
