import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from direct_recovery import validate,store,connect,initialize
class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.db=Path(self.temp.name)/'r.db';initialize(self.db);self.case=dict(id='case',code='EM3',response_id=1,source_hash='sealed',sources={'user':'miedo','response':'Entiendo ese miedo','history_0':'antes'})
  self.p=dict(id='case',status='SCORED',score=0,applicable=True,evidence=[dict(source='response',quote='Entiendo')],justification='Omite la conducta específica',upper_contrast='No ejecuta el siguiente nivel')
 def tearDown(self):
  import gc
  gc.collect();self.temp.cleanup()
 def test_preserves_zero_and_proposal(self):
  store(self.db,'c',self.case,self.p,'receipt');r=connect(self.db).execute('select *from decisions').fetchone();self.assertEqual((r['status'],r['score']),('SCORED',0));self.assertEqual(validate(self.case,self.p)['score'],0)
 def test_invalid_citation_exception_not_na(self):
  self.p['evidence'][0]['quote']='Inventado';store(self.db,'c',self.case,self.p,'receipt');r=connect(self.db).execute('select *from decisions').fetchone();self.assertEqual((r['status'],r['score']),('EXCEPTION',None))
 def test_no_overwrite_or_rescore(self):
  store(self.db,'c',self.case,self.p,'receipt');self.p['score']=3
  with self.assertRaises(ValueError):store(self.db,'c',self.case,self.p,'receipt')
 def test_history_scope(self):
  self.p['evidence']=[dict(source='history_5',quote='antes')]
  with self.assertRaises(ValueError):validate(self.case,self.p)
 def test_na_separate(self):
  self.p.update(status='N/A',score=None,applicable=False);self.assertIsNone(validate(self.case,self.p)['score'])
 def test_direct_score_not_python_rule(self):
  self.p['score']=2;self.assertEqual(validate(self.case,self.p)['score'],2)
 def test_uncertain_call_does_not_stop_independent_queue(self):
  from governed_parallel import GovernedLab
  import json
  lab=GovernedLab(Path(self.temp.name)/'queue.db');lab.initialize('1',workers=2)
  lab.enqueue_simulation('job',108,'1',[dict(body={'n':n},reserve='.01',response='r')for n in range(3)])
  self.assertEqual(lab.claim('owner'),'job')
  c=lab.connect()
  try:keys=[r['key']for r in c.execute('select key from requests order by position')]
  finally:c.close()
  class Provider:
   simulation_only=True
   def __call__(self,body):
    if body['n']==0:raise RuntimeError('simulated uncertain transmission')
    return '.001',{'fixture':body['n']}
  first=lab.execute_batch('job','owner',keys[:2],Provider(),Path(self.temp.name)/'wire',retain_owner_on_failure=True)
  self.assertEqual({r['state']for r in first},{'completed','uncertain'})
  second=lab.execute_batch('job','owner',keys[2:],Provider(),Path(self.temp.name)/'wire',retain_owner_on_failure=True)
  self.assertEqual(second[0]['state'],'completed')
  with self.assertRaises(ValueError):lab.execute_batch('job','owner',[keys[0]],Provider(),Path(self.temp.name)/'wire',retain_owner_on_failure=True)
if __name__=='__main__':unittest.main()
