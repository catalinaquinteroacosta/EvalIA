"""Regression gates on live evidence, not numerical agreement alone."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend/evaluators'))
from crisis_semantic.domain import DOCS,load_contracts
from crisis_semantic.closure_run import context
from crisis_semantic.predicate_catalog import definitions
from crisis_semantic.evidence import literal_check
from crisis_semantic.scoring import resolve_score
from crisis_semantic.span_provider import SpanProvider,fingerprint

class AC9LiveTests(unittest.TestCase):
    def test_live_evidence_distinguishes_safety_initial_urgency_and_followup(self):
        directory=DOCS/'ac9_live8'
        path=max(directory.glob('regression_attempt_*.json'),key=lambda p:int(p.stem.rsplit('_',1)[1]))
        data=json.loads(path.read_text(encoding='utf-8'))
        self.assertTrue(data['passed']);self.assertFalse(data['findings'])
        rows={r['case']:r['after'] for r in data['cases']}
        self.assertEqual(len(rows),8)
        for case in ('primary_imminent_safe_1','conversation_complete_changing_risk_2','safety_now_only'):
            row=rows[case];self.assertEqual((row['status'],row['score']),('SCORED',0))
            self.assertIs(row['verified_decisions']['CR-AC9.a']['value'],False)
            self.assertIs(row['verified_decisions']['CR-AC9.b']['value'],False)
        for case in ('primary_ordinary_support_1','complete_true_followup'):self.assertEqual(rows[case]['score'],3)
        self.assertEqual(rows['minimal_true_followup']['score'],1)
        contracts,_,_=load_contracts();defs=definitions(contracts,['CR-AC9'])
        for item in data['cases']:
            row=item['after'];facts={k.split('.',1)[1]:v['value'] for k,v in row['verified_decisions'].items()}
            raw=json.loads((directory/(item['case']+'.json')).read_text(encoding='utf-8'))['batch']['context']
            self.assertEqual(resolve_score('CR-AC9',facts,contracts),(row['score'],None))
            for key,decision in row['verified_decisions'].items():
                self.assertFalse(decision['issues'])
                self.assertEqual(decision['extraction']['state'],decision['verification']['state'])
                for stage in ('extraction','verification'):
                    self.assertEqual(literal_check(decision[stage],defs[key],context(raw),True,()),[])
        for claim in data['independent_descriptor_audit']['claims']:self.assertEqual(claim['state'],'yes')
        self.assertTrue((directory/'first_attempt_rejection.json').exists())
    def test_versioned_results_preserve_other_indicators_and_qualification(self):
        directory=DOCS/'ac9_live8'
        for name in ('final_comparison.json','conversation_api_attempt.json'):
            before=json.loads((DOCS/'closure8'/name).read_text(encoding='utf-8'))
            after=json.loads((directory/name).read_text(encoding='utf-8'))
            self.assertEqual(len(before['reports']),len(after['reports']))
            for old,new in zip(before['reports'],after['reports']):
                self.assertEqual(old['context'],new['context'])
                for a,b in zip(old['evaluation']['results'],new['evaluation']['results']):
                    if a['code']!='CR-AC9':self.assertEqual(a,b)
        proof=json.loads((directory/'qualification.json').read_text(encoding='utf-8'))
        self.assertEqual(proof['fingerprint'],fingerprint())
        self.assertTrue(proof['ac9_live_revision']['unchanged_RI2_CE10_components'])
        self.assertEqual(SpanProvider().qualified_components,{'CR-RI2','CR-CE10'})

if __name__=='__main__':unittest.main()
