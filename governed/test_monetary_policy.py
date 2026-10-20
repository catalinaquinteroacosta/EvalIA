import sys,tempfile,unittest,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from governed_parallel import GovernedLab

class MonetaryPolicyTests(unittest.TestCase):
 def test_monitor_allows_exact_batch_above_caps_and_records_cost(self):
  with tempfile.TemporaryDirectory()as folder:
   lab=GovernedLab(Path(folder)/'test.db');lab.initialize('.001',workers=2)
   lab.enqueue_simulation('job',999,'.001',[dict(body={'n':i},reserve='.01',response='r')for i in range(3)])
   with lab.tx()as c:
    c.execute('create table monetary_policy(id INTEGER PRIMARY KEY,mode TEXT)');c.execute("insert into monetary_policy values(1,'monitor_only')")
   self.assertEqual(lab.claim('owner'),'job')
   c=lab.connect();keys=[r[0]for r in c.execute('select key from requests order by position')];c.close()
   rows=lab.reserve_batch('job','owner',keys[:2],2);self.assertEqual(len(rows),2)
   for r in rows:lab.mark_sending(r['key'],'owner');lab.receipt(r['key'],'.02',{'key':r['key']})
   self.assertEqual(len(lab.reserve_batch('job','owner',keys[2:],2)),1)
   with self.assertRaises(ValueError):lab.reserve_batch('job','owner',keys,2)
   c=lab.connect();self.assertEqual(c.execute('select sum(actual)from requests').fetchone()[0],40000000);self.assertEqual(c.execute('select blocked from safety').fetchone()[0],0);self.assertEqual(c.execute('select count(*)from requests').fetchone()[0],3);c.close();gc.collect()
 def test_default_retains_enforced_policy(self):
  with tempfile.TemporaryDirectory()as folder:
   lab=GovernedLab(Path(folder)/'test.db');lab.initialize('.001',workers=2)
   lab.enqueue_simulation('job',999,'.001',[dict(body={'n':0},reserve='.01',response='r')]);lab.claim('owner')
   c=lab.connect();key=c.execute('select key from requests').fetchone()[0];c.close()
   self.assertEqual(lab.reserve_batch('job','owner',[key],2),[]);gc.collect()
if __name__=='__main__':unittest.main()
