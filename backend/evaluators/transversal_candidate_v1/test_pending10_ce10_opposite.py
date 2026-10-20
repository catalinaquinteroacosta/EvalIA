"""Scoped predicate correction and official precision/contradiction precedence."""
import unittest
from copy import deepcopy
from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.scoring import resolve_score
from transversal_candidate_v1.pending10_ce10_opposite import ce10_opposite_definitions, CE10_OPPOSITE

class CE10OppositeControls(unittest.TestCase):
    def setUp(self):
        self.contracts=load_contracts()[0]

    def test_only_ce10_opposite_changes_without_mutating_input(self):
        before=definitions(self.contracts,['CR-CE10','CR-RI2','CR-NI6'])
        snapshot=deepcopy(before)
        after=ce10_opposite_definitions(before)
        self.assertEqual(before,snapshot)
        changed=[key for key in before if before[key]!=after[key]]
        self.assertEqual(changed,['CR-CE10.opposite'])
        self.assertEqual(after['CR-CE10.opposite']['text'],CE10_OPPOSITE)
        self.assertEqual(after['CR-CE10.opposite']['kind'],'response')

    def test_secondary_precision_gap_is_two_when_not_contradicted(self):
        self.assertEqual(resolve_score('CR-CE10',{'a':True,'b':True,'c':False,'opposite':False},self.contracts),(2,None))

    def test_real_contradiction_retains_zero_precedence(self):
        self.assertEqual(resolve_score('CR-CE10',{'a':True,'b':True,'c':False,'opposite':True},self.contracts),(0,None))

    def test_unresolved_contradiction_is_not_invented_two_or_na(self):
        score,cause=resolve_score('CR-CE10',{'a':True,'b':True,'c':False,'opposite':None},self.contracts)
        self.assertIsNone(score)
        self.assertEqual(cause,'unresolved_components_change_official_level')

if __name__=='__main__': unittest.main()
