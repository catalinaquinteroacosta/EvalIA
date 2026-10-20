"""Autonomous worker hook and separate status publication; disabled by default."""
import json,os,hashlib
from pathlib import Path
from .engine import Circuit,wire,digest,catalog
from .authorization import active
def status(lab,job):
    con=lab.connect()
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE name='adjudication_manifests'").fetchone():return dict(enabled=False,registered=False,paid_calls=0)
        row=con.execute('SELECT payload FROM adjudication_manifests WHERE job=?',(job,)).fetchone()
        if not row:return dict(enabled=False,registered=False,paid_calls=0)
        m=json.loads(row[0]);results=[]
        for c in m['cases']:
            r=lab.load_result(job,'adjudication:'+c['id'])
            if r:
                decision=r['result']['indicator_results'][0]
                results.append({**decision,'case_id':c['id'],'model':c['original']['model'],'turn':c['original']['turn'],'code':c['code'],'family':catalog()[c['code']]['family_name']})
        keys={digest(r['body']) for r in m['requests']};requests=[dict(r) for r in con.execute('SELECT key,status,actual,reserve FROM requests WHERE job=?',(job,)) if r['key']in keys]
        return dict(version=m['version'],registered=True,cases=len(m['cases']),resolved=sum(r['status']in('SCORED','N/A') for r in results),exceptions=sum(r['status']=='EXCEPTION' for r in results),received=sum(r['status']=='completed' for r in requests),uncertain=sum(r['status']=='uncertain' for r in requests),results=results,requests=requests,historical_results_unchanged=True)
    finally:con.close()
def original_progress(lab,job,state):
    """Adjudication requests/results never inflate the original 850/25 counters."""
    con=lab.connect()
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE name='adjudication_parent_snapshots'").fetchone():return state
        row=con.execute('SELECT payload FROM adjudication_parent_snapshots WHERE job=?',(job,)).fetchone()
        if not row:return state
        keys=set(json.loads(row[0])['original_keys']);rows=con.execute('SELECT key,status FROM requests WHERE job=?',(job,)).fetchall()
        result={**state,'completed':sum(r['key']in keys and r['status']=='completed' for r in rows),'total':len(keys)}
        result['responses_saved']=con.execute("SELECT count(*) FROM results WHERE job=? AND response NOT LIKE 'adjudication:%'",(job,)).fetchone()[0]
        result['definitive_responses']=con.execute("SELECT coalesce(sum(definitive),0) FROM response_quality WHERE job=? AND response NOT LIKE 'adjudication:%'",(job,)).fetchone()[0]
        return result
    finally:con.close()
def publish(lab,job,path):
    path=Path(path);temp=path.with_suffix('.tmp');temp.write_text(wire(status(lab,job)),encoding='utf8');os.replace(temp,path)
def dispatch(lab,job,owner,config,provider_factory=None):
    con=lab.connect()
    try:
        exists=con.execute("SELECT 1 FROM sqlite_master WHERE name='adjudication_manifests'").fetchone()
        row=con.execute('SELECT payload FROM adjudication_manifests WHERE job=?',(job,)).fetchone() if exists else None
    finally:con.close()
    if not row:return False
    enabled=config.get('double_resolution_enabled')is True
    if not enabled and provider_factory is None:raise ValueError('double resolution explicitly disabled')
    m=json.loads(row[0])
    if provider_factory:provider=provider_factory(lab,job,dict(adjudication=True,manifest=m))
    else:
        permission=active(lab,m) # Before loading ANY credential.
        from .release import verify
        verify(permission)
        if config.get('explicit_real_activation')is not True:raise ValueError('real activation disabled')
        if permission.get('openai_project')!=config.get('openai_project'):raise ValueError('approved project differs')
        os.environ['OPENAI_PROJECT']=config['openai_project']
        from .connector import CampaignProvider
        provider=CampaignProvider(lab,job,permission['transport_authorization_path'],Path(config['wire'])/('adjudication-native-'+job),m)
        from backend.luna_credentials import load
        if not load():raise RuntimeError('confirmed pre-send unavailable credential')
    Circuit(lab).run(job,owner,provider,config['wire'])
    if config.get('adjudication_status_path'):publish(lab,job,config['adjudication_status_path'])
    with lab.tx()as con:
        current=con.execute('SELECT status FROM jobs WHERE id=?',(job,)).fetchone()[0]
        if current=='running':
            uncertain=con.execute("SELECT 1 FROM requests WHERE job=? AND status IN('sending','uncertain')",(job,)).fetchone()
            con.execute('UPDATE jobs SET status=?,owner=NULL WHERE id=?',('pending_reconciliation' if uncertain else 'stopped_requires_review',job))
    return True
