"""User-confirmed, sealed synchronous Luna jobs. Preparing a job never sends HTTP."""
import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from backend.luna_application import ProcessLock, BatchPending, request_key
from backend.luna_budget import BudgetJournal, money
from backend import luna_reader as reader, luna_runner, luna_sync_runtime
from backend import luna_credentials

ROOT=Path(__file__).resolve().parents[1]
CERTIFICATES=ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016/qualification_v19/CERTIFICATES_COMPATIBLE_V7.json'
FORBIDDEN_UNCERTAIN_REQUESTS=frozenset((
    '5ef1a01c4b73c77e79d2bb3d0a01e960bfd15a7443d54d2c158ee317852eb944',
    '6b13d0d68c47880c06d62f0bcc77c79c2309c7353edb22796f365c093d0082dd'))

def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def stamp():return datetime.now(timezone.utc).isoformat()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid4().hex+'.tmp')
    with temporary.open('x',encoding='utf8') as out:
        json.dump(value,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
    os.replace(temporary,path)

class RealService:
    def __init__(self,main,root=None,transport_factory=None,archive=None):
        self.main=main;self.root=Path(root or ROOT/'.evalia-private/luna_ui').resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.lock=ProcessLock(self.root/'.jobs.lock')
        self.execution=threading.Lock();self.threads={}
        self.transport_factory=transport_factory or luna_sync_runtime.SealedSyncTransport
        if archive is None:
            path=ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016/followup_v17/ENTREGA_FINAL/LINaje_56_Cuerpos.json'
            # Historical receipts are local research data, not a source dependency.
            archive={r['key']:r for r in read(path)} if path.is_file() else {}
        self.archive=archive

    def archived(self,body,endpoint):
        key=request_key(body,endpoint)[0];row=self.archive.get(key)
        if row is None:return None
        raw=Path(row['raw_response']).read_bytes();proof=read(row['receipt'])
        if row['body']!=body or proof.get('request_sha256')!=key or proof.get('response_sha256')!=sha256(raw).hexdigest() or proof.get('http_status')!=200:raise RuntimeError('historical_receipt_integrity_failure')
        return json.loads(raw)

    def folder(self,pid):
        if len(pid)!=32 or any(c not in '0123456789abcdef' for c in pid):raise HTTPException(404,'Plan no encontrado')
        folder=self.root/'plans'/pid
        if not (folder/'state.json').is_file():raise HTTPException(404,'Plan no encontrado')
        return folder

    def state(self,pid):
        folder=self.folder(pid);state=read(folder/'state.json')
        receipts=[read(p) for p in (folder/'receipts').rglob('*.receipt.json')]
        state.update(completed_requests=len(receipts),actual_cost_usd=str(sum((money(r['actual_usd']) for r in receipts),Decimal(0))))
        state['worker_running']=pid in self.threads and self.threads[pid].is_alive()
        if state['status']=='running' and not state['worker_running']:
            state['status']='interrupted_requires_review'
        state['uncertain_requests']=sum(not p.with_name(p.name.replace('.intent.json','.receipt.json')).exists() for p in (folder/'receipts').rglob('*.intent.json'))
        state['errors']=[{k:read(p).get(k) for k in ('http_status','error_type','network_reason_type')} for p in (folder/'receipts').rglob('*.failure.json')]
        state['in_flight_requests']=state['uncertain_requests'] if state['worker_running'] and not state['errors'] else 0
        if state['in_flight_requests']:state['uncertain_requests']=0
        state['reserved_usd']=BudgetJournal(folder/'budget.json').snapshot()['reserved_usd'] if (folder/'budget.json').exists() else '0'
        state['remaining_reservation_excluding_known_cost_usd']=str(max(money(state['reserved_usd'])-money(state['actual_cost_usd']),Decimal(0)))
        state['completed_responses']=len({r['response_id'] for r in state.get('results',[]) if r['status'] in ('evaluated','already_evaluated')})
        state['budget_remaining_usd']=str(max(money(state.get('user_approved_ceiling_usd',0))-money(state['actual_cost_usd'])-money(state['reserved_usd']),Decimal(0)))
        state['can_resume']=state.get('confirmed') is True and not state['worker_running'] and state['status'] not in ('complete','complete_requires_review') and state['uncertain_requests']==0 and not list((folder/'receipts').rglob('*.failure.json'))
        grant=folder/'recovery-grant.json'
        if grant.exists():
            g=read(grant)
            state['recovery_prepared']=True
            state['original_uncertain_retained']=True
            state['historical_uncertain_requests']=1
            state['replacement_attempts']=len(list((folder/'receipts'/'replacement-123-1').rglob('*.intent.json')))
            state['completed_unique_requests']=len({r['request_sha256'] for r in receipts})
            if g.get('execution_approved') is True and g.get('installation_approved') is True:
                from backend.recovery_108 import inspect_recovery
                try:
                    check=inspect_recovery(folder/'authorization.json',grant)
                    state['historical_errors']=state['errors']
                    state['errors']=[{k:read(p).get(k) for k in ('http_status','error_type','network_reason_type')} for p in check['new_failure_paths']]
                    state['uncertain_requests']=check['new_uncertain_requests']
                    state['in_flight_requests']=check['new_uncertain_requests'] if state['worker_running'] and not state['errors'] else 0
                    state['original_reserve_retained_usd']='0.092545'
                    state['locally_recoverable_requests']=check['locally_recoverable_requests']
                    state['can_resume']=check['execution_approved'] and check['new_uncertain_requests']==check['locally_recoverable_requests'] and not check['new_failure_paths'] and not state['worker_running'] and state['status'] not in ('complete','complete_requires_review')
                except Exception:state['can_resume']=False
        return state

    def status(self):
        committed=Decimal(0)
        historical=ROOT/'.evalia-private/economic_readers_budget.json'
        ledgers=([historical] if historical.exists() else [])+list((self.root/'plans').glob('*/budget.json'))
        for ledger in ledgers:
            snapshot=BudgetJournal(ledger).snapshot()
            committed+=money(snapshot['spent_usd'])+money(snapshot['reserved_usd'])
        return dict(model=reader.MODEL,credential_present=luna_credentials.available(),
            safety_budget_remaining_usd=str(max(Decimal(100)-committed,Decimal(0))),
            real_mode_available=True,requires_explicit_confirmation=True,
            connection_test_paid_requests=sum(len(list(p.glob('*.receipt.json'))) for p in (self.root/'plans').glob('*/receipts') if read(p.parent/'state.json').get('connection_test')),
            extraction_and_verification='separate blind requests, same GPT-6 Luna model',
            connection=read(self.root/'connection.json') if (self.root/'connection.json').exists() else
                dict(status='not_tested_in_this_interface',historical_receipts_available=True),
            plans=[self.state(p.parent.name) for p in sorted((self.root/'plans').glob('*/state.json'))])

    def prepare(self,response_ids,connection_test=False):
        from backend.integrated_evaluation import authoritative_record
        if type(connection_test)is not bool or not isinstance(response_ids,list) or any(type(r)is not int or r<=0 for r in response_ids):raise HTTPException(422,'Selección inválida')
        if connection_test and response_ids or not connection_test and not 1<=len(response_ids)<=25 or len(set(response_ids))!=len(response_ids):raise HTTPException(422,'Selecciona entre 1 y 25 respuestas únicas, o una prueba de conexión')
        if not connection_test and not CERTIFICATES.is_file():
            raise HTTPException(409,'Faltan los certificados locales de calificacion. Restaura la configuracion de investigacion antes de evaluar.')
        rows={};experiments=set();reused=set();forbidden_found=set()
        def capture(body,endpoint):
            key=request_key(body,endpoint)[0]
            if key in FORBIDDEN_UNCERTAIN_REQUESTS:
                forbidden_found.add(key);raise BatchPending([key])
            old=self.archived(body,endpoint)
            if old is not None:reused.add(key);return old
            rows[key]=dict(body=body,endpoint=endpoint.removeprefix('/v1/'))
            raise BatchPending([key]) # Existing capture signal only; no Batch endpoint or submission.
        if connection_test:
            for stage in ('extraction','independent_verification'):
                body=dict(model=reader.MODEL,store=False,reasoning={'effort':'none'},max_output_tokens=64,
                    input=[{'role':'system','content':'Prueba de conexión '+stage+'. Devuelve únicamente el objeto solicitado.'},
                           {'role':'user','content':'Devuelve {"ok":true}.'}],
                    text={'format':{'type':'json_schema','name':'connection_check','strict':True,'schema':{'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}}})
                rows[request_key(body,'responses')[0]]=dict(endpoint='responses',body=body)
        else:
            for rid in response_ids:
                raw=self.main._get_response_context(rid);eid=int(raw['experiment_id'])
                if eid==72:raise HTTPException(403,'El Experimento 072 está protegido')
                experiments.add(eid)
                self.main._require_experiment_snapshot_current(eid,raw['scenario_code'],int(raw['scenario_id']))
                try:self.main._load_saved_evaluation(rid)
                except HTTPException as error:
                    if error.status_code!=404:raise
                else:raise HTTPException(409,'La selección incluye una respuesta ya evaluada; se conserva sin duplicar API')
                from backend.integrated_evaluation import load_review
                previous=load_review(self.main,rid)
                if previous and previous['result'].get('evaluation_state')=='complete':raise HTTPException(409,'La respuesta ya tiene una evaluación completa guardada')
                record=authoritative_record(self.main,raw)
                if getattr(self,'literal_context_enabled',False):
                    from governed.double_resolution_v1.stage_zero import factories
                    factory,provider,anxiety=factories(capture)
                else:
                    factory=luna_runner.IntegrationRunner;provider=reader.LunaProvider(capture);anxiety=lambda request:reader.read_anxiety(request,capture)
                runner=factory(lambda _:record,crisis_provider=provider,anxiety_reader=anxiety)
                runner.evaluate_response(rid)
        if forbidden_found:raise HTTPException(409,'Solicitud histórica incierta protegida: no se retransmite')
        if len(experiments)>1:raise HTTPException(422,'Un plan corresponde a un solo experimento')
        reserve=sum((money(reader.estimate_reserve(r['body'],'sync')['reserved_usd']) for r in rows.values()),Decimal(0))
        pid=uuid4().hex;folder=self.root/'plans'/pid;folder.mkdir(parents=True)
        sources={name:sha256(Path(module.__file__).read_bytes()).hexdigest() for name,module in
                 (('luna_reader',reader),('luna_runner',luna_runner),('luna_sync_runtime',luna_sync_runtime))}
        write(folder/'manifest.json',dict(reader_version=('LUNA-LITERAL-STAGE0-20261017-1' if getattr(self,'literal_context_enabled',False) else reader.VERSION),reader_sha256=sources['luna_reader'],runtime_sources=sources,
            allowed_experiment_ids=sorted(experiments) or [1],requests=list(rows.values())))
        from backend import database
        write(folder/'state.json',dict(id=pid,status='prepared',confirmed=False,created_at=stamp(),historical_reused_requests=len(reused),
            response_ids=response_ids,experiment_ids=sorted(experiments),connection_test=connection_test,
            database_sha_scope=str(database.DB_PATH.resolve()),estimated_reserve_usd=str(reserve),
            total_requests=len(rows),completed_requests=0,actual_cost_usd='0',
            note='Preparación sin gasto. La confirmación posterior autoriza exclusivamente este plan; no utiliza ni modifica el saldo histórico.'))
        if not rows and response_ids:
            from backend.integrated_evaluation import using_dependencies,evaluate_response
            provider=reader.LunaProvider(lambda body,endpoint:self.archived(body,endpoint),certificates=read(CERTIFICATES))
            deps=dict(runner_factory=luna_runner.IntegrationRunner,crisis_provider=provider,
                anxiety_reader=lambda request:reader.read_anxiety(request,lambda body,endpoint:self.archived(body,endpoint)),
                anxiety_model=reader.MODEL,allowed_experiment_ids=frozenset(experiments))
            with using_dependencies(deps):
                for rid in response_ids:evaluate_response(self.main,rid)
            state=read(folder/'state.json');state.update(status='complete',note='Recibos históricos exactos reutilizados; cero inferencias y cero gasto nuevo.');write(folder/'state.json',state)
        return self.state(pid)

    def confirm(self,pid,confirmation,max_usd,start=True):
        if confirmation!='AUTORIZO':raise HTTPException(403,'Escribe AUTORIZO para confirmar el costo máximo de este plan')
        if not luna_credentials.available():raise HTTPException(503,'Credencial del lector no disponible en el servidor')
        folder=self.folder(pid)
        try:cap=money(max_usd)
        except ValueError:raise HTTPException(422,'Límite de presupuesto inválido')
        with self.lock:
            state=read(folder/'state.json')
            from backend import database
            if str(database.DB_PATH.resolve())!=state['database_sha_scope']:raise HTTPException(409,'El plan pertenece a otra base de trabajo')
            if state.get('confirmed'):
                if start and self.state(pid)['can_resume']:self.start(pid)
                return self.state(pid)
            sequential=state['experiment_ids']==[108] and not state['connection_test']
            required=max((money(reader.estimate_reserve(r['body'],'sync')['reserved_usd']) for r in read(folder/'manifest.json')['requests']),default=Decimal(0)) if sequential else money(state['estimated_reserve_usd'])
            if not required<=cap<=(3 if sequential else 100):raise HTTPException(422,'El límite debe cubrir la siguiente reserva y no superar US$3 para #0108' if sequential else 'El límite debe cubrir la reserva calculada y no superar US$100')
            committed=Decimal(0)
            historical=ROOT/'.evalia-private/economic_readers_budget.json'
            if historical.exists():
                old=BudgetJournal(historical).snapshot();committed+=money(old['spent_usd'])+money(old['reserved_usd'])
            for ledger in (self.root/'plans').glob('*/budget.json'):
                if ledger.parent==folder:continue
                other=BudgetJournal(ledger).snapshot();committed+=money(other['spent_usd'])+money(other['reserved_usd'])
            if committed+(cap if sequential else money(state['estimated_reserve_usd']))>100:raise HTTPException(422,'El compromiso acumulado excedería el techo absoluto de US$100')
            index=read(self.root/'index.json') if (self.root/'index.json').exists() else {}
            manifest=read(folder/'manifest.json')
            for request in manifest['requests']:
                request_digest=request_key(request['body'],request['endpoint'])[0]
                if request_digest in FORBIDDEN_UNCERTAIN_REQUESTS:raise HTTPException(409,'Solicitud histórica incierta protegida')
                key='request:'+request_digest
                if key in index and index[key]!=pid:raise HTTPException(409,'Ya existe un plan autorizado para esta solicitud exacta. Consulta su estado; no se duplica.')
            for rid in state['response_ids']:
                key=state['database_sha_scope']+':'+str(rid)
                if key in index and index[key]!=pid:raise HTTPException(409,'La respuesta tiene un plan ya autorizado. Consulta y reanuda ese plan; no se retransmite en otro.')
            for rid in state['response_ids']:index[state['database_sha_scope']+':'+str(rid)]=pid
            for request in manifest['requests']:index['request:'+request_key(request['body'],request['endpoint'])[0]]=pid
            write(self.root/'index.json',index)
            journal=BudgetJournal(folder/'budget.json')
            journal.initialize(prior_evidence='Explicit future user confirmation in local EVALIA interface for '+pid,cap_usd=str(cap))
            manifest=read(folder/'manifest.json')
            authorization=dict(mode='sync',model=reader.MODEL,explicit_user_approval=True,allowed_experiment_ids=manifest['allowed_experiment_ids'],
                manifest_path=str(folder/'manifest.json'),sealed_manifest_sha256=sha256((folder/'manifest.json').read_bytes()).hexdigest(),
                private_directory=str(folder/'receipts'),budget_journal=str(folder/'budget.json'),run_id='ui_'+pid,
                scope='User-confirmed interface plan; at most 25 supplied responses; no model generation',
                max_requests=state['total_requests'],max_usd=str(cap) if sequential else state['estimated_reserve_usd'],allow_definitive_950=False,
                execution_policy='sequential_per_request' if sequential else 'whole_manifest',
                authorization_context='New explicit user UI confirmation for this plan only; previous economic authorization remains untouched.')
            write(folder/'authorization.json',authorization)
            if not sequential:
                journal.reserve(authorization['run_id'],authorization['sealed_manifest_sha256'],
                    reservation_usd=authorization['max_usd'],requests=authorization['max_requests'],authorization=authorization,scope=authorization['scope'])
            state.update(confirmed=True,confirmed_at=stamp(),user_approved_ceiling_usd=str(cap),status='authorized')
            write(folder/'state.json',state)
        if start:self.start(pid)
        return self.state(pid)

    def start(self,pid):
        with self.lock:
            if pid in self.threads and self.threads[pid].is_alive():return
            state=self.state(pid)
            if not state['confirmed'] or state['uncertain_requests'] or list((self.folder(pid)/'receipts').glob('*.failure.json')):raise HTTPException(409,'Plan no autorizado o transmisión incierta: no se reintenta')
            stop=self.folder(pid)/'stop.requested'
            if stop.exists():stop.unlink()
            thread=threading.Thread(target=self.work,args=(pid,),daemon=True,name='evalia-ui-'+pid)
            self.threads[pid]=thread;thread.start()

    def work(self,pid):
        from backend.integrated_evaluation import evaluate_response, using_dependencies
        folder=self.folder(pid)
        with self.execution:
            state=read(folder/'state.json');state.setdefault('historical_error',state.get('error'));state.pop('error',None);state.update(status='running',started_at=stamp());write(folder/'state.json',state)
            sequential=False
            try:
                from backend import database
                if str(database.DB_PATH.resolve())!=state['database_sha_scope']:raise RuntimeError('workbench_scope_changed')
                if not luna_credentials.load():raise RuntimeError('credential_unavailable')
                authorization=read(folder/'authorization.json')
                sequential=authorization.get('execution_policy')=='sequential_per_request'
                if sequential:
                    from backend.luna_sequential import SequentialTransport
                    grant=folder/'recovery-grant.json'
                    if grant.exists():
                        from backend.recovery_108 import Recovery108
                        transport=Recovery108(folder/'authorization.json',grant)
                    else:transport=SequentialTransport(folder/'authorization.json')
                else:transport=self.transport_factory(folder/'authorization.json')
                def call(body,endpoint):
                    previous=self.archived(body,endpoint)
                    if previous is not None:return previous
                    if (folder/'stop.requested').exists():raise RuntimeError('user_requested_stop_before_next_request')
                    raw=transport(body,endpoint)
                    state['last_completed_at']=stamp();write(folder/'state.json',state)
                    return raw
                if state['connection_test']:
                    for row in read(folder/'manifest.json')['requests']:
                        raw=call(row['body'],row['endpoint']);wire,_=reader.select_final(raw)
                        reader.validate_schema(wire,row['body']['text']['format']['schema'])
                        if wire!={'ok':True}:raise RuntimeError('connection_schema_not_confirmed')
                    write(self.root/'connection.json',dict(status='verified_by_two_real_requests',verified_at=stamp(),model=reader.MODEL,plan_id=pid))
                else:
                    provider=reader.LunaProvider(call,certificates=read(CERTIFICATES))
                    deps=dict(runner_factory=luna_runner.IntegrationRunner,crisis_provider=provider,
                        anxiety_reader=lambda request:reader.read_anxiety(request,call),anxiety_model=reader.MODEL,
                        allowed_experiment_ids=frozenset(state['experiment_ids']),evaluation_lock=transport.lock,
                        paid_mode='sync',paid_submission_enabled=True,authorization_id=pid)
                    with using_dependencies(deps):
                        for rid in state['response_ids']:
                            # Preserve previously analyzed reviews as well as definitive results.
                            if any(r['response_id']==rid for r in state.get('results',[])):continue
                            if sequential:
                                from backend.integrated_evaluation import authoritative_record
                                record=authoritative_record(self.main,self.main._get_response_context(rid))
                                for request in read(folder/'manifest.json')['requests']:
                                    body=request['body'];original=json.loads(body['messages'][1]['content'])['original']
                                    if original['model']==record['model'] and original['turn']==record['turn']:
                                        call(body,request['endpoint'])
                            result=evaluate_response(self.main,rid)
                            if hasattr(transport,'assert_continuable'):transport.assert_continuable()
                            elif list((folder/'receipts').rglob('*.failure.json')):raise RuntimeError('uncertain_transmission_no_retry')
                            if not any(r['response_id']==rid for r in state.get('results',[])):
                                state.setdefault('results',[]).append(dict(response_id=rid,status=result['status']))
                            write(folder/'state.json',state)
                complete=not sequential or all(r['status'] in ('evaluated','already_evaluated') for r in state.get('results',[]))
                state.update(status='complete' if complete else 'complete_requires_review',finished_at=stamp())
            except Exception as error:
                # Private diagnostic: never included in the public state or exports.
                import traceback
                trace=traceback.extract_tb(error.__traceback__)
                write(folder/'recovery-diagnostic.json',dict(error_type=type(error).__name__,site=trace[-1].name if trace else None,detail=str(error)[:500] if isinstance(error,(RuntimeError,ValueError)) else None))
                # Error details/HTTP artifacts remain private. No credentials or provider response are echoed.
                state.update(status='stopped_requires_review',finished_at=stamp(),
                    error='La ejecución se detuvo. Consulta costo y recibos; no se reintentó ninguna transmisión incierta. Las respuestas permanecen guardadas.')
                from backend.luna_budget import BudgetBlocked
                if isinstance(error,BudgetBlocked):
                    state['status']=('pending_reconciliation' if 'uncertain' in str(error) else 'stopped_budget' if any(word in str(error) for word in ('budget','cap','exceeds','reservation')) else 'stopped_requires_review') if hasattr(locals().get('transport'),'assert_continuable') else ('pending_reconciliation' if 'uncertain' in str(error) else 'stopped_budget')
                elif sequential and list((folder/'receipts').rglob('*.failure.json')):
                    if hasattr(locals().get('transport'),'assert_continuable'):
                        try:transport.assert_continuable()
                        except Exception:state['status']='pending_reconciliation'
                    else:state['status']='pending_reconciliation'
            write(folder/'state.json',state)

def mount(main):
    service=RealService(main);main.app.state.luna_real_service=service
    def local(request):
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).hostname not in ('localhost','127.0.0.1','::1'):raise HTTPException(403,'Solo se permiten confirmaciones desde la interfaz local')
    @main.app.get('/api/real/status')
    def status():return service.status()
    @main.app.post('/api/real/prepare')
    async def prepare(request:Request):
        local(request);data=await request.json()
        return service.prepare(data.get('response_ids',[]),data.get('connection_test',False))
    @main.app.post('/api/real/{pid}/confirm')
    async def confirm(pid:str,request:Request):
        local(request);data=await request.json()
        return service.confirm(pid,data.get('confirmation'),data.get('max_usd'))
    @main.app.get('/api/real/{pid}')
    def state(pid:str):return service.state(pid)
    @main.app.post('/api/real/{pid}/resume')
    def resume(pid:str,request:Request):
        local(request)
        if not service.state(pid)['can_resume']:raise HTTPException(409,'No se puede reanudar un plan incierto o terminado')
        service.start(pid);return service.state(pid)
    @main.app.post('/api/real/{pid}/stop')
    def stop(pid:str,request:Request):
        local(request);(service.folder(pid)/'stop.requested').touch(exist_ok=True)
        return {'status':'stop_requested_after_current_synchronous_request'}
