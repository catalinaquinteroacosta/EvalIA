"""Offline fault injection. Synthetic observations do not validate semantics."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend/evaluators'))
from crisis_semantic.domain import Input,Turn,load_contracts,package_codes,PACKAGES
from crisis_semantic.predicate_catalog import definitions,POSITIVE,NEGATIVE
from crisis_semantic.pipeline import CrisisEvaluator
from crisis_semantic.openai_private import ProviderBlocked
from crisis_semantic.research_tables import aggregate

OBSERVATIONS=[]
CTX=Input(Turn(1,'Contexto simulado evaluable.','Respuesta simulada evaluable.','isolated-test'))

class IsolatedProvider:
    def __init__(self,mode='absence',recovered=False):self.mode=mode;self.recovered=recovered;self.requests=[]
    def run(self,stage,system,content,schema,ids,identity):
        self.requests.append((stage,copy.deepcopy(content)))
        if self.mode=='technical':raise ProviderBlocked('injected_transport_failure')
        items=[]
        for key,d in content['predicates'].items():
            state='no'
            if key.endswith('.gate'):state='yes'
            if key.endswith('.a') and self.mode in ('conflict','invalid','partial','adequate','full','recover'):state='yes'
            if self.mode=='adequate' and key.endswith('.b'):state='yes'
            if self.mode=='full' and key.endswith(('.b','.c')):state='yes'
            if self.mode=='conflict' and stage=='verify' and key.endswith('.a'):state='no'
            if self.mode=='unknown' and not key.endswith('.gate'):state='unknown'
            if self.mode=='inactive' and key.endswith('.gate'):state='no'
            if self.mode=='uncertain_gate' and key.endswith('.gate'):state='unknown'
            quote=content['conversation']['current_ai']
            if self.mode=='invalid' and key.endswith('.a'):quote='FABRICATED QUOTE NOT IN INPUT'
            if self.mode=='recover' and not identity['recovery'] and key.endswith('.a') and stage=='verify':state='no'
            citations=[{'source':'current_ai','history_index':None,'quote':quote}] if state=='yes' else []
            items.append({'id':key,'state':state,'citations':citations,'reason':'Isolated simulated observation; no semantic claim.'})
        if self.mode=='missing':items=items[:-1]
        return {'reviewed_entire_context':True,'claims':items}

class FreezeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.contracts,_,_=load_contracts()
    def setUp(self):
        self.network=patch('urllib.request.urlopen',side_effect=AssertionError('NETWORK FORBIDDEN'));self.network.start();self.addCleanup(self.network.stop)
    def test_safety_now_adjudication_retains_other_verified_components(self):
        import json
        from crisis_semantic.domain import DOCS
        from crisis_semantic.scoring import resolve_score
        data=json.loads((DOCS/'freeze8/AC9_SAFETY_ADJUDICATION.json').read_text(encoding='utf-8'))
        self.assertEqual(data['facts'],{'a':False,'b':False,'c':False,'opposite':False})
        self.assertEqual(resolve_score('CR-AC9',data['facts'],self.contracts),(0,None))
        self.assertFalse(data['independent_API_reverification'] if 'independent_API_reverification' in data else data['adjudicated_component']['independent_API_reverification'])
        self.assertEqual(len(data['other_components_retained']),3)
        self.assertIn('NO acredita seguimiento',definitions(self.contracts,['CR-AC9'])['CR-AC9.a']['text'])
    def batch(self,mode,package='P2',recovery=False):
        provider=IsolatedProvider(mode)
        result=CrisisEvaluator(provider,recovery=recovery).evaluate(CTX,package_codes(self.contracts,package))
        OBSERVATIONS.append({'mode':mode,'package':package,'recovery':recovery,'input':CTX.payload(),'results':result,'calls':len(provider.requests)})
        return result,provider
    def test_unresolved_disagreement_and_invalid_evidence_block(self):
        for mode in ('conflict','invalid','unknown','missing','technical'):
            result,_=self.batch(mode)
            row=next(r for r in result['results'] if r['code']=='CR-CS1')
            self.assertEqual(row['status'],'BLOCKED',mode);self.assertIsNone(row['score']);self.assertIsNone(row['official_descriptor'])
    def test_complete_packages_distinguish_omission_and_negative_absence(self):
        for package in PACKAGES:
            result,_=self.batch('absence',package)
            for row in result['results']:
                short=row['code'][3:]
                if short in POSITIVE and short!='CE10':self.assertEqual((row['status'],row['score']),('SCORED',0),short)
                if short in NEGATIVE:self.assertEqual((row['status'],row['score']),('SCORED',3),short)
    def test_partial_and_complete_are_not_na(self):
        for mode,score in [('partial',1),('adequate',2),('full',3)]:
            result,_=self.batch(mode)
            row=next(r for r in result['results'] if r['code']=='CR-CS1')
            self.assertEqual((row['status'],row['score']),('SCORED',score))
    def test_conditional_gate_inactive_active_and_unresolved(self):
        code=next(c for c in package_codes(self.contracts,'P2') if self.contracts[c]['applicability']['kind']=='conditional')
        for mode,status in [('inactive','N/A'),('absence','SCORED'),('uncertain_gate','BLOCKED')]:
            result,_=self.batch(mode)
            row=next(r for r in result['results'] if r['code']==code)
            self.assertEqual(row['status'],status)
            if status!='SCORED':self.assertIsNone(row['score'])
    def test_all_conditional_gates_in_complete_packages(self):
        for package in PACKAGES:
            inactive,_=self.batch('inactive',package)
            unknown,_=self.batch('uncertain_gate',package)
            for result,expected in ((inactive,'N/A'),(unknown,'BLOCKED')):
                for row in result['results']:
                    if self.contracts[row['code']]['applicability']['kind']=='conditional' and row['code']!='CR-CE10':self.assertEqual(row['status'],expected,row['code'])
                    if self.contracts[row['code']]['applicability']['kind']=='general':self.assertNotEqual(row['status'],'N/A',row['code'])
    def test_ce10_official_two_prior_turn_gate(self):
        for count in (0,1,2):
            ctx=Input(Turn(count+1,CTX.current.user,CTX.current.ai,CTX.current.model),tuple(Turn(n+1,'previous user','previous AI',CTX.current.model) for n in range(count)))
            provider=IsolatedProvider();provider.qualified_components={'CR-CE10'}
            result=CrisisEvaluator(provider,recovery=False).evaluate(ctx,package_codes(self.contracts,'P4'))
            row=next(r for r in result['results'] if r['code']=='CR-CE10')
            self.assertEqual(row['status'],'SCORED' if count==2 else 'N/A')
            OBSERVATIONS.append({'mode':'CE10_gate','prior_turns':count,'input':ctx.payload(),'result':row,'qualification':'Synthetic qualified provider, not a new live certificate.'})
    def test_recovery_requires_new_verified_observations(self):
        old,_=self.batch('conflict',recovery=True)
        fixed,provider=self.batch('recover',recovery=True)
        before=next(r for r in old['results'] if r['code']=='CR-CS1')
        after=next(r for r in fixed['results'] if r['code']=='CR-CS1')
        self.assertEqual(before['status'],'BLOCKED');self.assertEqual(after['score'],1)
        self.assertEqual(len(provider.requests),4)
        decision=after['verified_decisions']['CR-CS1.a']
        self.assertIn('previous_attempt',decision);self.assertTrue(decision['value']);self.assertFalse(decision['issues'])
    def test_blocked_and_pending_prevent_complete_percentage(self):
        for row in [{'status':'BLOCKED','score':None},{'status':'SCORED','score':0,'validation_pending':True}]:
            result=aggregate([{'status':'SCORED','score':3},row],2,percentage_method_confirmed=True)
            OBSERVATIONS.append({'aggregation_input':row,'output':result})
            self.assertIsNone(result['denominator']);self.assertIsNone(result['percentage']);self.assertFalse(result['technical_complete'])
        self.assertEqual(aggregate([{'status':'SCORED','score':0},{'status':'SCORED','score':3},{'status':'N/A','score':None}],3,percentage_method_confirmed=True)['percentage'],50)
    def test_blind_verification_and_temporal_isolation(self):
        _,provider=self.batch('partial')
        self.assertEqual(provider.requests[0][1],provider.requests[1][1])
        self.assertNotIn('score',provider.requests[1][1]);self.assertNotIn('extraction',provider.requests[1][1])
        turns=[CTX.current,Turn(2,'future','future','isolated-test'),Turn(1,'foreign','foreign','other')]
        self.assertEqual(Input.from_conversation(turns,1,'isolated-test'),CTX)
        for history in [(turns[1],),(turns[2],)]:
            with self.assertRaises(ValueError):Input(CTX.current,history)

if __name__=='__main__':unittest.main()
