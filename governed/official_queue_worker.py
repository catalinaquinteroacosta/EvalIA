"""Official evaluator worker managed by the local server.
No automatic uncertain retry. Configure dependencies once per process.
"""
import json,hashlib,time,threading,sqlite3
from pathlib import Path
from governed_parallel import GovernedLab
from supervision import claimed_worker

def body_key(body):return hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def validate_context(record,original):
    current=[r for r in record['originals'] if r['turn']==record['turn']]
    if len(current)!=1:raise ValueError('current context missing')
    history=[]
    for row in record['originals']:
        if row['turn']<record['turn']:history.extend([dict(role='user',text=row['user']),dict(role='assistant',text=row['response'])])
    if original['conversation']!=record['conversation'] or original['model']!=record['model'] or original['turn']!=record['turn'] or original['user']!=current[0]['user'] or original['response']!=current[0]['response'] or original['prior_history']!=history:raise ValueError('sealed context changed or includes foreign/future history')

def run_job(main,lab,job,owner,info,provider,wire_root,certificates,recovery_config=None):
    from historical_recovery_gate import check,ReplacementApprovalRequired
    from backend import luna_reader as reader,luna_runner
    from backend.integrated_evaluation import authoritative_record,using_dependencies,evaluate_response
    path=Path(info['manifest']);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=info['manifest_sha256']:raise ValueError('job manifest changed')
    manifest=json.loads(raw);grouped={}
    for row in manifest['requests']:
        if row['endpoint']!='chat/completions':
            # CRISIS uses its separate original Responses body contract; never convert it.
            if row['endpoint']!='responses':raise ValueError('unsupported official endpoint')
            conversation=json.loads(row['body']['input'][1]['content'])['conversation']
            original=dict(model=conversation['model_evaluated'],turn=conversation['current_turn'],user=conversation['current_user'],response=conversation['current_ai'],prior_history=[],crisis_history=conversation['history'])
            for h in conversation['history']:
                if h['model']!=original['model'] or h['number']>=original['turn']:raise ValueError('foreign/future crisis history')
                original['prior_history'].extend([dict(role='user',text=h['user']),dict(role='assistant',text=h['ai'])])
        else:original=json.loads(row['body']['messages'][1]['content'])['original']
        if original is None:raise ValueError('unrecognized original context contract')
        grouped.setdefault((original['model'],original['turn']),[]).append((body_key(row['body']),original))
    def replay(body,endpoint):
        k=body_key(body);c=lab.connect()
        try:r=c.execute('SELECT job,status,receipt,receipt_hash FROM requests WHERE key=?',(k,)).fetchone()
        finally:c.close()
        if not r or r['job']!=job or r['status']!='completed' or hashlib.sha256(r['receipt'].encode()).hexdigest()!=r['receipt_hash']:raise RuntimeError('reader barrier incomplete or foreign receipt')
        return json.loads(r['receipt'])
    if recovery_config and recovery_config.get('throughput_runtime')=='continuous12-v1' and not recovery_config.get('_stream_publication'):
        response_keys={};key_response={}
        # Every response context is validated before any independent prefetch.
        for pending_rid in info['response_ids']:
            record=authoritative_record(main,main._get_response_context(pending_rid))
            scoped=grouped[(record['model'],record['turn'])]
            for key,original in scoped:
                if 'crisis_history' in original:
                    if manifest['allowed_experiment_ids']!=[info['experiment']]:raise ValueError('crisis experiment grant differs')
                    original={**original,'conversation':record['conversation']}
                validate_context(record,original)
            response_keys[pending_rid]=[key for key,_ in scoped]
            for key in response_keys[pending_rid]:key_response[key]=pending_rid
        published=set()
        def publish_ready(result):
            if result['state']!='completed':return
            rid=key_response[result['key']]
            if rid in published:return
            connection=lab.connect()
            try:complete=all(connection.execute('select status from requests where job=? and key=?',(job,key)).fetchone()[0]=='completed'for key in response_keys[rid])
            finally:connection.close()
            if complete:
                run_job(main,lab,job,owner,{**info,'response_ids':[rid]},provider,wire_root,certificates,recovery_config={**recovery_config,'_stream_publication':True})
                published.add(rid)
        connection=lab.connect()
        try:ready={r[0]for r in connection.execute("select key from requests where job=? and status='ready'",(job,))}
        finally:connection.close()
        dispatch=[]
        for key in key_response:
            if key not in ready:continue
            try:check(lab,job,key)
            except ReplacementApprovalRequired:continue
            dispatch.append(key)
        if dispatch:lab.stream(job,owner,dispatch,provider,wire_root,stop=lambda:bool(info.get('stop_path')and Path(info['stop_path']).exists()),on_result=publish_ready)
    for rid in info['response_ids']:
        saved=lab.load_result(job,str(rid))
        if saved is not None:
            c=lab.connect()
            try:keys=json.loads(c.execute('SELECT keys_json FROM response_contracts WHERE job=? AND response=?',(job,str(rid))).fetchone()[0])
            finally:c.close()
            # Repairs only missing quality metadata after a crash, without inference.
            lab.persist_result(job,str(rid),keys,saved);continue
        record=authoritative_record(main,main._get_response_context(rid));scoped=grouped[(record['model'],record['turn'])]
        for _,original in scoped:
            # CRISIS seals experiment ownership in the parent manifest, not API body.
            if 'crisis_history' in original:
                if manifest['allowed_experiment_ids']!=[info['experiment']]:raise ValueError('crisis experiment grant differs')
                original={**original,'conversation':record['conversation']}
            validate_context(record,original)
        keys=[k for k,_ in scoped]
        try:
            for key in keys:check(lab,job,key)
        except ReplacementApprovalRequired:
            # No reservation/intent. Other independent responses may progress.
            continue
        c=lab.connect()
        try:ready={r[0] for r in c.execute("SELECT key FROM requests WHERE job=? AND status='ready'",(job,))}
        finally:c.close()
        missing=[k for k in keys if k in ready];limit=lab.policy()['internal_requests']
        def token_bound(body):
            b=reader.estimate_reserve(body,'sync');return b['estimated_input_token_bound']+b['output_token_cap']
        while True:
            c=lab.connect()
            try:missing=[k for k in keys if c.execute('SELECT status FROM requests WHERE key=?',(k,)).fetchone()[0]=='ready']
            finally:c.close()
            if not missing:break
            if info.get('stop_path') and Path(info['stop_path']).exists():
                with lab.tx() as c:c.execute("UPDATE jobs SET status='stopped_requires_review',owner=NULL WHERE id=?",(job,))
                return False
            if recovery_config and recovery_config.get('throughput_runtime')=='continuous12-v1':
                results=lab.stream(job,owner,missing,provider,wire_root,stop=lambda:bool(info.get('stop_path')and Path(info['stop_path']).exists()))
            else:
                results=lab.execute_batch(job,owner,missing[:limit],provider,wire_root,token_bound=token_bound,retain_owner_on_failure=True)
            if not results:return False
            # Unknown/possibly transmitted requests are not ready and cannot retry.
            # Independently ready requests can continue behind the scoring barrier.
        c=lab.connect()
        try:complete=all(c.execute("SELECT status FROM requests WHERE job=? AND key=?",(job,k)).fetchone()[0]=='completed' for k in keys)
        finally:c.close()
        if not complete:continue
        if manifest.get('reader_version')=='LUNA-LITERAL-STAGE0-20261017-1':
            from governed.double_resolution_v1.stage_zero import factories
            factory,native_provider,anxiety=factories(replay,certificates=certificates)
        else:
            factory=luna_runner.IntegrationRunner;native_provider=reader.LunaProvider(replay,certificates=certificates);anxiety=lambda req:reader.read_anxiety(req,replay)
        deps=dict(runner_factory=factory,crisis_provider=native_provider,anxiety_reader=anxiety,anxiety_model=reader.MODEL,allowed_experiment_ids=frozenset((info['experiment'],)),evaluation_lock=threading.RLock(),replay_only=True,paid_submission_enabled=False,paid_mode='disabled',authorization_id='governed-prefetched-'+job)
        started=time.perf_counter()
        with using_dependencies(deps):result=evaluate_response(main,rid)
        # Includes decode, deterministic scoring, mapping and official DB publication;
        # it is explicitly not pure scorer CPU time.
        lab.metric(job,str(rid),'scoring',time.perf_counter()-started)
        started=time.perf_counter()
        lab.persist_result(job,str(rid),keys,dict(experiment=info['experiment'],model=record['model'],turn=record['turn'],result=result['result'],source_status=result['status']))
        lab.metric(job,str(rid),'persistence',time.perf_counter()-started)
    if recovery_config and recovery_config.get('_stream_publication'):return True
    finished=lab.finish_if_complete(job,owner)
    if not finished and recovery_config:
        from partial_transport_closure import close_missing
        finished=close_missing(main,lab,job,info,certificates,owner)
    if finished and info.get('experiment')!=72:
        # Queue preparation is offline. A new exact paid grant is still required.
        # Each persisted BLOCKED becomes a direct case, while valid A stays intact.
        if recovery_config:
            cfg=recovery_config
            if cfg.get('direct_recovery_auto_prepare') is True:
                from direct_recovery import prepare
                root=Path(cfg['project_root'])/'.evalia-private/direct_recovery'
                folder=root/str(info['experiment'])
                if not (folder/'manifest.json').exists():prepare(cfg,info['experiment'],root/'recovery.db',folder)
                if cfg.get('direct_recovery_auto_start') is True:
                    from automatic_direct_recovery import start
                    start(cfg,info['experiment'])
    if not finished:
        with lab.tx() as c:c.execute("UPDATE jobs SET status='pending_reconciliation',owner=NULL WHERE id=? AND owner=?",(job,owner))
    return finished

def worker_loop(config,provider_factory=None):
    # Imports and credential loading happen only inside an explicitly launched worker.
    import os,sys
    project=Path(config['project_root']).resolve();sys.path[:0]=[str(project),str(project/'venv/Lib/site-packages')]
    from backend import database
    database.DB_PATH=Path(config['database']).resolve();database.DATABASE_DIR=database.DB_PATH.parent
    from backend import main,luna_reader
    def connection():
        c=sqlite3.connect(database.DB_PATH,timeout=15);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
    main.get_connection=connection
    from throughput_runtime import make_lab
    lab=make_lab(config);owner='worker-'+str(os.getpid())+'-'+os.urandom(6).hex()
    while True:
        with claimed_worker(lab,owner,config['fences']) as job:
            if job is None:return
            try:
                from governed.double_resolution_v1.runtime import dispatch
                if dispatch(lab,job,owner,config,provider_factory):continue
                info=json.loads((Path(config['bindings'])/(job+'.json')).read_text(encoding='utf8'))
                if provider_factory:provider=provider_factory(lab,job,info)
                else:
                    policy=lab.policy()
                    if config.get('explicit_real_activation') is not True or policy['mode']!='real' or not policy['rpm'] or not policy['tpm']:raise RuntimeError('explicit activation and verified quotas required')
                    c=lab.connect();grant=c.execute('SELECT explicit_approval FROM grants WHERE job=?',(job,)).fetchone();c.close()
                    if not grant or grant[0]!=1:raise RuntimeError('job grant required before credentials')
                    from sealed_governed_provider import SealedGovernedProvider
                    provider=SealedGovernedProvider(lab,job,info['authorization'],Path(config['wire'])/('backend-'+job))
                    from backend.luna_credentials import load
                    if not load():raise RuntimeError('confirmed pre-send unavailable credential')
                run_job(main,lab,job,owner,info,provider,config['wire'],json.loads(Path(config['certificates']).read_text(encoding='utf8')),recovery_config=config)
            except Exception as exc:
                with lab.tx() as c:
                    c.execute('CREATE TABLE IF NOT EXISTS worker_errors(job TEXT,at REAL,error_type TEXT)')
                    c.execute('INSERT INTO worker_errors VALUES(?,?,?)',(job,time.time(),type(exc).__name__))
                    uncertain=c.execute("SELECT 1 FROM requests WHERE job=? AND status IN ('sending','uncertain')",(job,)).fetchone()
                    c.execute("UPDATE jobs SET status=?,owner=NULL WHERE id=?",('pending_reconciliation' if uncertain else 'stopped_requires_review',job))

if __name__=='__main__':
    import argparse,multiprocessing
    multiprocessing.freeze_support();p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
    worker_loop(json.loads(Path(args.config).read_text(encoding='utf8')))
