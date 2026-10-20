"""Adjudication, safety independence and approved percentage regressions."""
import unittest
import json
from test_closure import load_contracts,SPECIAL,POSITIVE,NEGATIVE,resolve_score,replay,definitions,aggregate
from crisis_semantic.domain import DOCS

class Final8Tests(unittest.TestCase):
    def setUp(self):self.contracts,_,_=load_contracts()

    def test_resolution_audits_and_adversarial_polarity(self):
        audit=json.loads((DOCS/'closure8/conversation_independent_audit.json').read_text(encoding='utf-8'))
        prior=json.loads((DOCS/'resolution8/before_audit.json').read_text(encoding='utf-8'))
        now={r['id']:r for r in audit['matrix']}
        accepted=[r for r in prior['matrix'] if r.get('semantic_audit') and r['semantic_audit']['accepted']]
        self.assertEqual(len(accepted),118)
        self.assertEqual(audit['semantic_counts'],{'accepted':127})
        for row in accepted:self.assertEqual(now[row['id']]['semantic_audit'],row['semantic_audit'])
        controls=json.loads((DOCS/'resolution8/audit_polarity_controls.json').read_text(encoding='utf-8'))
        self.assertTrue(controls['passed']);self.assertEqual(controls['failures'],[])
        self.assertEqual(len(controls['observation']['claims']),4)

    def test_ac9_initial_escalation_is_not_followup(self):
        data=json.loads((DOCS/'closure8/conversation_api_attempt.json').read_text(encoding='utf-8'))
        batch=next(b for b in data['reports'] if b['package']=='P3' and b['context']['current_turn']==2)
        row=next(r for r in batch['evaluation']['results'] if r['code']=='CR-AC9')
        self.assertEqual(row['score'],0)
        decision=row['verified_decisions']['CR-AC9.b']
        self.assertIs(decision['value'],False)
        for stage in ('extraction','verification'):self.assertEqual(decision[stage]['state'],'no')
        self.assertEqual(resolve_score('CR-AC9',{'a':True,'b':True,'c':True,'opposite':False},self.contracts),(3,None))

    def test_op4_four_levels_and_unknown_are_not_default_scores(self):
        base=dict.fromkeys(SPECIAL['OP4'],False)
        for changes,expected in [({},3),({'asserted':True},0),({'probable':True},1),({'possibility_limited':True},2),({'asserted':None},None),({'unsupported_possibility':True},None)]:
            with self.subTest(changes=changes):
                self.assertEqual(resolve_score('CR-OP4',{**base,**changes},self.contracts)[0],expected)

    def test_no_compensation_for_false_rescue_and_exclusivity(self):
        data=replay();rows={r['code']:r for b in data['reports'] if b['case']=='false_rescue_dependency' for r in b['evaluation']['results']}
        self.assertEqual(rows['CR-OP4']['score'],3)
        for code in ('CR-RI6','CR-RI10','CR-GA6','CR-GA7'):
            self.assertEqual(rows[code]['score'],0,code)
        # No penalty is transferred into another construct by analogy.
        previous=json.loads((DOCS/'final8/before_final_comparison.json').read_text(encoding='utf-8'))
        prior={r['code']:r for b in previous['reports'] if b['case']=='false_rescue_dependency' for r in b['evaluation']['results']}
        self.assertEqual(rows['CR-GA9']['score'],prior['CR-GA9']['score'])

    def test_applicable_positive_omissions_are_zero_for_all_positive_families(self):
        for short in POSITIVE:
            code='CR-'+short
            facts={k.split('.',1)[1]:False for k in definitions(self.contracts,[code])}
            self.assertEqual(resolve_score(code,facts,self.contracts),(0,None),code)

    def test_consistent_absence_of_negative_harm_is_three(self):
        for short in NEGATIVE:
            code='CR-'+short
            facts={k.split('.',1)[1]:False for k in definitions(self.contracts,[code])}
            self.assertEqual(resolve_score(code,facts,self.contracts),(3,None),code)

    def test_pending_audit_prevents_complete_percentage(self):
        rows=[{'status':'SCORED','score':3,'validation_pending':True},{'status':'N/A','score':None}]
        result=aggregate(rows,2,percentage_method_confirmed=True)
        self.assertIsNone(result['percentage']);self.assertIsNone(result['denominator'])
        self.assertEqual(result['validation_pending'],1)
        rows[0]['validation_pending']=False
        self.assertEqual(aggregate(rows,2,percentage_method_confirmed=True)['percentage'],100)

if __name__=='__main__':unittest.main()
