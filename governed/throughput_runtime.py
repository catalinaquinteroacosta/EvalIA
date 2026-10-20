"""Isolated throughput candidate. No live activation, credentials or HTTP."""
import sys,json,math,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'governed'),str(ROOT),str(ROOT/'venv/Lib/site-packages')]
from governed_parallel import GovernedLab
from monetary_policy import monitoring

from throughput_token_budget import quota_tokens

class ThroughputLab(GovernedLab):
    def __init__(self,path,*,live_allowed=False):
        self.live_allowed=live_allowed
        super().__init__(path)
    def receipt(self,key,actual,raw):
        super().receipt(key,actual,raw)
        usage=raw.get('usage',{})if isinstance(raw,dict)else{}
        actual_input=usage.get('prompt_tokens',usage.get('input_tokens'))
        if type(actual_input)is not int:return
        c=self.connect()
        try:body=json.loads(c.execute('select body from requests where key=?',(key,)).fetchone()[0])
        finally:c.close()
        cap=body.get('max_completion_tokens',body.get('max_output_tokens'))
        if actual_input>quota_tokens(body)-cap:
            with self.tx()as c:
                c.execute('create table if not exists token_count_alerts(key TEXT,actual_input INTEGER,estimated_input INTEGER)')
                c.execute('insert into token_count_alerts values(?,?,?)',(key,actual_input,quota_tokens(body)-cap))
                c.execute('update safety set blocked=1')
    def reserve_batch(self,job,owner,keys,limit=2,*,allow_independent_uncertain=False):
        if len(keys)!=1:raise ValueError('One exact independent request per streaming slot')
        with self.tx()as c:
            j=c.execute('select *from jobs where id=?',(job,)).fetchone()
            if not j or j['owner']!=owner or j['status']!='running':raise ValueError('foreign owner/state')
            if c.execute('select blocked from safety').fetchone()[0]:raise ValueError('safety stop')
            row=c.execute("select *from requests where job=? and key=? and status='ready'",(job,keys[0])).fetchone()
            if not row:raise ValueError('Duplicate, completed, uncertain or foreign request')
            if not monitoring(c):
                def committed(where='',args=()):
                    value=c.execute("select coalesce(sum(actual+case when status in ('reserved','sending','uncertain')then reserve else 0 end),0)from requests "+where,args).fetchone()[0]
                    if c.execute("select 1 from sqlite_master where name='legacy_commitments'").fetchone():value+=c.execute('select coalesce(sum(spent+held),0)from legacy_commitments '+where,args).fetchone()[0]
                    return value
                if committed()+row['reserve']>c.execute('select cap from settings').fetchone()[0] or committed('where job=?',(job,))+row['reserve']>j['cap']:return []
            c.execute("update requests set status='reserved'where key=?",(row['key'],));return [dict(row)]
    def stream(self,job,owner,keys,provider,root,*,stop=lambda:False,on_result=None):
        if getattr(provider,'simulation_only',False)is not True and not self.live_allowed:raise ValueError('Live activation required')
        root=Path(root).resolve()
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate input key')
        result={};pending=iter(keys);workers=self.policy()['internal_requests']
        def one(key):return self.execute_batch(job,owner,[key],provider,root,token_bound=quota_tokens,retain_owner_on_failure=True)[0]
        with ThreadPoolExecutor(max_workers=workers)as pool:
            active={}
            def refill():
                while len(active)<workers and not stop():
                    key=next(pending,None)
                    if key is None:break
                    active[pool.submit(one,key)]=key
            refill()
            while active:
                done,_=wait(active,return_when=FIRST_COMPLETED)
                for future in done:
                    key=active.pop(future);result[key]=future.result()
                    if on_result:on_result(result[key])
                refill()
        return [result[k]for k in keys if k in result]

def make_lab(config):
    if config.get('throughput_runtime')!='continuous12-v1':return GovernedLab(config['coordinator'])
    lab=ThroughputLab(config['coordinator'],live_allowed=config.get('explicit_real_activation')is True)
    p=lab.policy()
    if p['global_requests']!=12 or p['internal_requests']!=12:raise ValueError('Activation policy mismatch')
    return lab
