"""Opt-in bridge to official prepare/scoring/results. Not mounted by production.
Default read-only panel; real confirmations require explicitly enabled deployment.
"""
import json,hashlib
from decimal import Decimal
from pathlib import Path
from governed_parallel import GovernedLab
from queue_lab import units

class Bridge:
    def __init__(self,main,service,config):
        self.main=main;self.service=service;self.config=config;self.lab=GovernedLab(config['coordinator'])
    def refresh_activation(self):
        path=self.config.get('config_path')
        if path:
            try:
                current=json.loads(Path(path).read_text(encoding='utf8'))
                if any(current.get(k)!=self.config.get(k) for k in ('project_root','database','coordinator')):raise ValueError('deployment binding changed')
                self.config['explicit_real_activation']=current.get('explicit_real_activation') is True
            except (OSError,ValueError,TypeError):self.config['explicit_real_activation']=False
    def confirm(self,pid,confirmation,max_usd):
        self.refresh_activation()
        from fastapi import HTTPException
        from backend import database,luna_reader as reader
        from backend.luna_real_ui import read,write,FORBIDDEN_UNCERTAIN_REQUESTS
        from backend.luna_application import request_key
        if self.config.get('explicit_real_activation') is not True:raise HTTPException(403,'Ejecución real todavía deshabilitada')
        p=self.lab.policy()
        if p['mode']!='real' or not p['rpm'] or not p['tpm']:raise HTTPException(403,'Faltan cuotas verificadas y activación')
        if confirmation!='AUTORIZO':raise HTTPException(403,'Falta confirmación de gasto')
        folder=self.service.folder(pid)
        with self.service.lock:
            state=read(folder/'state.json');manifest_path=folder/'manifest.json';manifest=read(manifest_path)
            if state['connection_test'] or len(state['experiment_ids'])!=1 or state['experiment_ids']==[72]:raise HTTPException(409,'Ámbito no permitido')
            if state['database_sha_scope']!=str(database.DB_PATH.resolve()):raise HTTPException(409,'Base de trabajo diferente')
            cap=units(max_usd);c=self.lab.connect()
            from monetary_policy import monitoring
            monitor_only=monitoring(c)
            try:
                old=c.execute('SELECT cap FROM jobs WHERE id=?',(pid,)).fetchone();global_cap=c.execute('SELECT cap FROM settings').fetchone()[0]
            finally:c.close()
            if old:
                if old[0]!=cap:raise HTTPException(409,'No se cambia el presupuesto al reanudar')
                return self.status()
            bodies=[];contracts={}
            from backend.integrated_evaluation import authoritative_record
            for rid in state['response_ids']:
                record=authoritative_record(self.main,self.main._get_response_context(rid));contracts[(record['model'],record['turn'])]=str(rid)
            for row in manifest['requests']:
                body=row['body']
                if 'messages' in body:
                    o=json.loads(body['messages'][1]['content'])['original'];context=(o['model'],o['turn'])
                else:
                    o=json.loads(body['input'][1]['content'])['conversation'];context=(o['model_evaluated'],o['current_turn'])
                bodies.append(dict(body=body,reserve=reader.estimate_reserve(body,'sync')['reserved_usd'],response=contracts[context]))
            if not monitor_only and not max(units(r['reserve']) for r in bodies)<=cap<=global_cap:raise HTTPException(422,'Límite insuficiente para una solicitud o superior al global autorizado')
            index=read(self.service.root/'index.json') if (self.service.root/'index.json').exists() else {}
            keys=['request:'+request_key(r['body'],r['endpoint'])[0] for r in manifest['requests']]+[state['database_sha_scope']+':'+str(r) for r in state['response_ids']]
            if any(k.removeprefix('request:') in FORBIDDEN_UNCERTAIN_REQUESTS or k in index and index[k]!=pid for k in keys):raise HTTPException(409,'Respuesta o solicitud ya autorizada/incierta')
            # Conservative crash order: indexes and sealed binding precede claimable job.
            index.update({k:pid for k in keys});write(self.service.root/'index.json',index)
            seal=hashlib.sha256(manifest_path.read_bytes()).hexdigest();auth_path=folder/'governed-authorization.json'
            auth=dict(mode='sync',model=reader.MODEL,explicit_user_approval=True,allowed_experiment_ids=manifest['allowed_experiment_ids'],manifest_path=str(manifest_path),sealed_manifest_sha256=seal,run_id='governed_'+pid,scope='exact sealed manifest only',max_requests=len(bodies),max_usd=str(max_usd))
            write(auth_path,auth)
            binding=dict(experiment=state['experiment_ids'][0],response_ids=state['response_ids'],manifest=str(manifest_path),manifest_sha256=seal,authorization=str(auth_path),stop_path=str(folder/'stop.requested'))
            write(Path(self.config['bindings'])/(pid+'.json'),binding)
            self.lab.enqueue_simulation(pid,binding['experiment'],max_usd,bodies,initial_status='awaiting_authorization')
            c=self.lab.connect()
            try:scope=[tuple(r) for r in c.execute('SELECT position,key FROM requests WHERE job=? ORDER BY position',(pid,))]
            finally:c.close()
            self.lab.authorize_real_job(pid,dict(job=pid,experiment=binding['experiment'],max_usd=str(max_usd),scope='exact sealed manifest only',explicit_user_approval=True,body_scope_sha256=hashlib.sha256(json.dumps(scope).encode()).hexdigest()))
            return self.status()
    def plan_state(self,pid,original_state):
        c=self.lab.connect()
        try:exists=c.execute('SELECT 1 FROM jobs WHERE id=?',(pid,)).fetchone()
        finally:c.close()
        if not exists:
            result=original_state(pid)
            result['budget_mode']=self.status().get('budget_mode','enforced')
            proposed=self.config.get('proposed_experiment_caps',{}).get(str(result['experiment_ids'][0])) if len(result.get('experiment_ids',[]))==1 else None
            if proposed is not None and not result.get('confirmed'):result.update(proposed_cap_usd=str(proposed),execution_policy='governed_per_request')
            return result
        state=json.loads((self.service.folder(pid)/'state.json').read_text(encoding='utf8'));s=self.status();j=next(j for j in s['jobs'] if j['id']==pid)
        from governed.double_resolution_v1.runtime import original_progress
        j=original_progress(self.lab,pid,j)
        j={**j,'spent':j['spent']+j.get('historical_spent',0),'pending':j['pending']+j.get('historical_reserved',0)}
        c=self.lab.connect()
        try:
            results=[dict(response_id=int(r['response']),**json.loads(r['payload'])) for r in c.execute("SELECT response,payload FROM results WHERE job=? AND response NOT LIKE 'adjudication:%'",(pid,))]
            uncertain=c.execute("SELECT count(*) FROM requests WHERE job=? AND status IN ('sending','uncertain')",(pid,)).fetchone()[0]
        finally:c.close()
        from supervision import Fence
        fence=Fence(Path(self.config['fences'])/(pid+'.worker.lock'));free=fence.acquire()
        if free:fence.release()
        live=j['status']=='running' and not free
        status=j.get('display_status',j['status'])
        if j['status']=='running' and not live:status='interrupted_requires_review'
        usd=lambda n:str(Decimal(n)/Decimal(10**9))
        state.update(confirmed=True,status=status,worker_running=live,completed_requests=j['completed'],completed_unique_requests=j['completed'],total_requests=j['total'],actual_cost_usd=usd(j['spent']),reserved_usd=usd(j['pending']),original_reserve_retained_usd=usd(j.get('historical_reserved',0)),budget_remaining_usd=usd(j['cap']-j['spent']-j['pending']),completed_responses=j.get('definitive_responses',0),results=results,uncertain_requests=uncertain,can_resume=False,execution_policy='governed_per_request',errors=[])
        state['budget_pause']=j.get('budget_pause')
        state['global_budget_remaining_usd']=usd(s['global_cap']-s['history']['spent']-s['history']['held']-sum(x['spent']+x['pending'] for x in s['jobs']))
        state['requires_economic_authorization']=not self.config.get('explicit_real_activation',False)
        state['budget_mode']=s.get('budget_mode','enforced')
        if state['budget_mode']=='monitor_only':state.update(budget_pause=None,budget_remaining_usd=None,global_budget_remaining_usd=None)
        return state
    def status(self):
        self.refresh_activation()
        result=self.lab.snapshot();c=self.lab.connect()
        result['execution_enabled']=self.config.get('explicit_real_activation',False)
        try:
            from monetary_policy import monitoring
            result['budget_mode']='monitor_only'if monitoring(c)else'enforced'
            result['global_cap']=c.execute('SELECT cap FROM settings').fetchone()[0]
            result['history']=dict(c.execute('SELECT coalesce(sum(spent),0) spent,coalesce(sum(held),0) held FROM legacy_commitments').fetchone()) if c.execute("SELECT 1 FROM sqlite_master WHERE name='legacy_commitments'").fetchone() else dict(spent=0,held=0)
            from governed.double_resolution_v1.runtime import original_progress
            result['jobs']=[original_progress(self.lab,j['id'],j) for j in result['jobs']]
            for j in result['jobs']:
                j['response_total']=c.execute("SELECT count(*) FROM response_contracts WHERE job=? AND response NOT LIKE 'adjudication:%'",(j['id'],)).fetchone()[0]
                j['results_url']='/resultados?experiment_id='+str(j['experiment'])
        finally:c.close()
        return result

def mount(main,service,config):
    from fastapi import Request
    from fastapi.responses import HTMLResponse
    bridge=Bridge(main,service,config)
    if config.get('bind_primary_flow') is True:
        if service is None:raise ValueError('official service required')
        service.literal_context_enabled=config.get('literal_context_enabled') is True
        original_state=service.state
        service.state=lambda pid:bridge.plan_state(pid,original_state)
        def primary_confirm(pid,confirmation,max_usd,start=True):
            bridge.confirm(pid,confirmation,max_usd)
            return service.state(pid)
        service.confirm=primary_confirm
        original_status=service.status
        def primary_status():
            s=bridge.status();remaining=s['global_cap']-s['history']['spent']-s['history']['held']-sum(j['spent']+j['pending'] for j in s['jobs'])
            from backend.luna_real_ui import read
            plans=[service.state(p.parent.name) for p in (service.root/'plans').glob('*/state.json')]
            from backend.luna_reader import MODEL
            return dict(plans=plans,model=MODEL,budget_mode=s.get('budget_mode','enforced'),safety_budget_remaining_usd=None if s.get('budget_mode')=='monitor_only'else str(Decimal(remaining)/Decimal(10**9)),requires_explicit_confirmation=True,real_mode_available=config.get('explicit_real_activation') is True)
        service.status=primary_status
        # Never call the legacy thread start outside the authoritative ledger.
        def guarded_start(pid):
            from fastapi import HTTPException
            raise HTTPException(409,'La reanudación requiere conciliación y autorización administrativa del coordinador')
        service.start=guarded_start
    @main.app.get('/api/adjudication/{pid}/status')
    def adjudication_status(pid:str):
        from governed.double_resolution_v1.runtime import status
        return status(bridge.lab,pid)

    @main.app.get('/api/multi/status')
    def status():return bridge.status()
    @main.app.get('/multiexperimento',response_class=HTMLResponse)
    def panel():return Path(__file__).with_name('panel_governed.html').read_text(encoding='utf8')
    @main.app.post('/api/multi/{pid}/confirm')
    async def confirm(pid:str,request:Request):
        from urllib.parse import urlsplit
        from fastapi import HTTPException
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).hostname not in ('127.0.0.1','localhost','::1'):raise HTTPException(403,'Solo confirmación local')
        d=await request.json();return bridge.confirm(pid,d.get('confirmation'),d.get('max_usd'))
    return bridge
