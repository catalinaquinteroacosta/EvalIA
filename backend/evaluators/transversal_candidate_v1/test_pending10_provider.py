"""Qualification control tests; stipulated records do not certify semantics."""
import copy
import unittest
from unittest.mock import patch
from crisis_semantic.domain import load_contracts
from crisis_semantic.predicate_catalog import definitions
from transversal_candidate_v1.pending10_provider import Pending10Provider, MODEL


class QualificationControls(unittest.TestCase):
    def setUp(self):
        self.defs = definitions(load_contracts()[0], ['CR-CE10'])
        with patch('sqlite3.connect', side_effect=AssertionError('SQLite forbidden')):
            self.provider = Pending10Provider()

    def proof(self):
        return {'identity': self.provider.qualification_identity(self.defs), 'cases': [
            {'expected': level, 'actual': level, 'descriptor_review_passed': True,
             'readings': [{'stage': stage, 'request_digest': f'{level}:{stage}',
                           'response_path': f'evidence/{level}_{stage}.json', 'model': MODEL,
                           'reviewed_entire_context': True, 'literal_and_provenance_passed': True}
                          for stage in ('extract', 'verify')]}
            for level in range(4)]}

    def test_historical_ce10_does_not_open_all_levels(self):
        self.assertNotIn('CR-CE10', self.provider.qualified_components)
        self.assertIn('CR-RI2', self.provider.qualified_components)

    def test_new_complete_attestation_binds_exact_definitions(self):
        proof = self.proof()
        self.provider.accept_ce10_qualification(proof, self.defs)
        self.assertIn('CR-CE10', self.provider.qualified_components)
        proof['cases'][0]['actual'] = 3
        self.assertEqual(self.provider.qualification_records['CR-CE10']['cases'][0]['actual'], 0)

    def test_rejects_wrong_model_prompt_fingerprint_or_catalog(self):
        for key in self.proof()['identity']:
            with self.subTest(key=key):
                proof = self.proof()
                proof['identity'][key] = 'different'
                with self.assertRaisesRegex(ValueError, 'identity_mismatch'):
                    self.provider.accept_ce10_qualification(proof, self.defs)
        self.assertNotIn('CR-CE10', self.provider.qualified_components)

    def test_rejects_missing_level_failed_case_same_reading_or_unreviewed(self):
        bad = []
        proof = self.proof(); proof['cases'].pop(); bad.append(proof)
        proof = self.proof(); proof['cases'][0]['actual'] = 3; bad.append(proof)
        proof = self.proof(); proof['cases'][0]['readings'][1]['request_digest'] = '0:extract'; bad.append(proof)
        proof = self.proof(); proof['cases'][0]['readings'][0]['literal_and_provenance_passed'] = False; bad.append(proof)
        for proof in bad:
            with self.assertRaises(ValueError):
                self.provider.accept_ce10_qualification(proof, self.defs)
        self.assertNotIn('CR-CE10', self.provider.qualified_components)


if __name__ == '__main__':
    unittest.main()
