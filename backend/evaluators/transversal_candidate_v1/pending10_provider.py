"""Cache-free official span reader with explicit current qualification evidence.

Transport is supplied by the authorized focal executor. No SQLite is constructed.
Historical CE10 0/3 checks do not qualify untested levels 1/2.
"""
import copy
import json
from crisis_semantic.domain import DOCS, digest, load_contracts
from crisis_semantic.span_provider import SpanProvider, MODEL, PROMPT, VERIFY, fingerprint
from crisis_semantic.span_protocol import PROTOCOL


class Pending10Provider(SpanProvider):
    def __init__(self):
        self.model = MODEL
        self.seed = {}
        self.reusable_regressions = set()
        self.reused_observations = 0
        self.qualified_components = set()
        contracts, _, _ = load_contracts()
        self.official_focus = {code: [item['text'] for item in c['focus']] for code, c in contracts.items()}
        # RI2's historical certificate explicitly includes its held level 1.
        proof = json.loads((DOCS / 'ac9_live8/qualification.json').read_text(encoding='utf-8'))
        if (proof.get('fingerprint') == fingerprint() and proof.get('protocol') == PROTOCOL
                and proof.get('model') == MODEL):
            cases = proof.get('components', {}).get('CR-RI2', [])
            if cases and all(c.get('passed') is True for c in cases) and any(
                    c.get('expected') == 1 and c.get('actual') == 1 for c in cases):
                self.qualified_components.add('CR-RI2')
        self.qualification_records = {}

    @staticmethod
    def qualification_identity(definitions):
        return {'model': MODEL, 'protocol': PROTOCOL, 'fingerprint': fingerprint(),
                'span_prompt_sha256': digest(PROMPT + VERIFY),
                'component_contract_sha256': digest(definitions)}

    def accept_ce10_qualification(self, proof, definitions):
        """Fail closed unless new independent evidence covers every official level.

The executor reviews entailment against descriptors, retains raw requests/responses,
and records their paths and request identities. This method checks that attestation
is complete; it does not claim to perform semantic review itself.
        """
        expected_identity = self.qualification_identity(definitions)
        if proof.get('identity') != expected_identity:
            raise ValueError('qualification_provider_or_contract_identity_mismatch')
        cases = proof.get('cases', [])
        if len(cases) != 4 or {r.get('expected') for r in cases} != {0, 1, 2, 3}:
            raise ValueError('qualification_official_level_coverage_incomplete')
        for row in cases:
            if row.get('actual') != row['expected'] or row.get('descriptor_review_passed') is not True:
                raise ValueError('qualification_case_not_demonstrated')
            stages = row.get('readings', [])
            if len(stages) != 2 or {s.get('stage') for s in stages} != {'extract', 'verify'}:
                raise ValueError('qualification_independent_readings_missing')
            if len({s.get('request_digest') for s in stages}) != 2 or any(
                    not s.get('request_digest') or not s.get('response_path')
                    or s.get('model') != MODEL or s.get('reviewed_entire_context') is not True
                    or s.get('literal_and_provenance_passed') is not True for s in stages):
                raise ValueError('qualification_reading_evidence_invalid')
        self.qualification_records['CR-CE10'] = copy.deepcopy(proof)
        self.qualified_components.add('CR-CE10')
