"""Offline preview/copy test and explicit recovery of a terminal experiment."""
import sys,json,sqlite3,argparse,tempfile,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'governed'),str(ROOT/'venv/Lib/site-packages')]
def run(experiment,apply=False):
 from governed_parallel import GovernedLab
 from backend import main,database
 from partial_transport_closure import close_missing
 cfg=json.loads((ROOT/'.evalia-private/governed_joint_install_20261017/config.json').read_text())
 with tempfile.TemporaryDirectory(dir=ROOT/'.evalia-private',ignore_cleanup_errors=True)as temporary:
  if not apply:
   for k in ('database','coordinator'):
    target=Path(temporary)/(k+'.db')
    with sqlite3.connect(cfg[k])as source,sqlite3.connect(target)as copy:source.backup(copy)
    cfg[k]=str(target)
  def connection():
   c=sqlite3.connect(cfg['database']);c.row_factory=sqlite3.Row;return c
  main.get_connection=connection;database.DB_PATH=Path(cfg['database'])
  lab=GovernedLab(cfg['coordinator'])
  with lab.connect()as c:
   job=dict(c.execute('select * from jobs where experiment=?',(experiment,)).fetchone())
   assert job['owner'] is None
   before={r['key']:(r['status'],r['receipt_hash'],r['actual'],r['reserve'])for r in c.execute('select * from requests where job=?',(job['id'],))}
  info=json.loads((Path(cfg['bindings'])/(job['id']+'.json')).read_text())
  closed=close_missing(main,lab,job['id'],info,json.loads(Path(cfg['certificates']).read_text()))
  with lab.connect()as c:
   after={r['key']:(r['status'],r['receipt_hash'],r['actual'],r['reserve'])for r in c.execute('select * from requests where job=?',(job['id'],))}
   assert before==after
   count=c.execute('select count(*) from results where job=?',(job['id'],)).fetchone()[0]
   assert count==len(info['response_ids'])
  print(json.dumps(dict(experiment=experiment,closed=closed,responses=count,receipts_and_spend_unchanged=True,copy_test=not apply)))
  gc.collect()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('experiment',type=int);p.add_argument('--apply',action='store_true');a=p.parse_args();run(a.experiment,a.apply)
