"""Offline Batch planning/replay only; this module never sends network requests.

Pending results cannot be persisted as scored evaluations. Submission and import
require a separately authorized executor and exact sealed request identities.
"""
import json
import os
import threading
import time
from decimal import Decimal
from hashlib import sha256
from pathlib import Path


class ProcessLock:
    """Reentrant thread lock plus OS lock; process exit releases ownership.

    The lock file remains in place to avoid unlink/recreation races. No stale
    lock is inferred from a timestamp and no other process is terminated.
    """
    def __init__(self, path):
        self.path=Path(path)
        self.thread_lock=threading.RLock()
        self.local=threading.local()

    def __enter__(self):
        self.thread_lock.acquire()
        depth=getattr(self.local,'depth',0)
        if depth:
            self.local.depth=depth+1
            return self
        handle=None
        try:
            handle=self.path.open('a+b')
            handle.seek(0,2)
            if not handle.tell():handle.write(b'0');handle.flush()
            deadline=time.monotonic()+10
            while True:
                try:
                    handle.seek(0)
                    if os.name=='nt':
                        import msvcrt
                        msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic()>=deadline:raise RuntimeError('batch_queue_process_lock_timeout')
                    time.sleep(.02)
            self.local.handle=handle;self.local.depth=1
            return self
        except BaseException:
            if handle:handle.close()
            self.thread_lock.release()
            raise

    def __exit__(self,*args):
        self.local.depth-=1
        if not self.local.depth:
            handle=self.local.handle
            try:
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
            finally:handle.close()
        self.thread_lock.release()


class BatchPending(RuntimeError):
    batch_pending = True
    def __init__(self, keys):
        self.keys = tuple(sorted(keys))
        super().__init__('Luna Batch pendiente: '+str(len(self.keys))+' solicitudes; no hay evaluación final.')


def request_key(body, endpoint):
    endpoint=endpoint.removeprefix('/v1/')
    wire = json.dumps({'endpoint':endpoint,'body':body},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return sha256(wire).hexdigest(), wire


class PrivateBatchQueue:
    """Durable isolated plan and verified replay; no implicit paid authorization."""
    def __init__(self, directory):
        self.root=Path(directory).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.pending=set()
        self.lock=ProcessLock(self.root/'.queue.lock')

    def __call__(self, body, endpoint):
        if body.get('model')!='gpt-6-luna' or endpoint not in ('responses','chat/completions','/v1/responses','/v1/chat/completions'):
            raise ValueError('luna_queue_identity_mismatch')
        key,wire=request_key(body,endpoint)
        with self.lock:
            plan=self.root/(key+'.request.json')
            if plan.exists() and plan.read_bytes()!=wire:raise ValueError('sealed_request_changed')
            if not plan.exists():
                with plan.open('xb') as out:out.write(wire);out.flush();os.fsync(out.fileno())
            result=self.root/(key+'.result.json')
            receipt=self.root/(key+'.receipt.json')
            if result.exists() and receipt.exists():
                raw=result.read_bytes();proof=json.loads(receipt.read_text(encoding='utf-8'))
                if proof.get('request_sha256')!=sha256(wire).hexdigest() or proof.get('result_sha256')!=sha256(raw).hexdigest():
                    raise ValueError('batch_replay_integrity_failure')
                self._verify_import(key,json.loads(raw),proof.get('provenance'),proof['batch_id'],proof['custom_id'])
                self.pending.discard(key)
                return json.loads(raw)
            self.pending.add(key)
            raise BatchPending([key])

    def manifest(self, estimate):
        with self.lock:
            return self._manifest_locked(estimate)

    def _manifest_locked(self, estimate):
        rows=[]
        for path in sorted(self.root.glob('*.request.json')):
            sealed=json.loads(path.read_text(encoding='utf-8'))
            reservation=estimate(sealed['body'],mode='batch')
            if isinstance(reservation,dict):reservation=reservation['reserved_usd']
            rows.append(dict(key=path.name.split('.')[0],endpoint=sealed['endpoint'],body=sealed['body'],
                reserve_usd=str(reservation)))
        return dict(mode='batch',submission_authorized=False,requests=rows,
            request_count=len(rows),reserve_usd=str(sum((Decimal(r['reserve_usd']) for r in rows),Decimal(0))))

    def _verify_import(self,key,raw,provenance,batch_id,custom_id):
        if not isinstance(provenance,dict):raise ValueError('batch_downloaded_provenance_required')
        from backend.luna_qualification import verify_batch_binding
        request=provenance['request'];response=provenance['response']
        sealed=json.loads((self.root/(key+'.request.json')).read_text(encoding='utf-8'))
        actual_key,_=request_key(request['body'],request['url'])
        if actual_key!=key or request['body']!=sealed['body']:
            raise ValueError('batch_import_original_request_mismatch')
        if response.get('response',{}).get('body')!=raw or raw.get('model')!='gpt-6-luna':
            raise ValueError('batch_import_original_response_mismatch')
        execution=provenance.get('execution_adapter') or {}
        reading=dict(batch_id=batch_id,custom_id=custom_id,request_id=response.get('response',{}).get('request_id'),
            execution_identity=dict(model='gpt-6-luna',reader_source_sha256=execution.get('sha256')))
        try:verified=verify_batch_binding(provenance,request,response,reading)
        except (KeyError,TypeError,ValueError,OSError):verified=False
        if not verified:
            raise ValueError('batch_import_provenance_mismatch')

    def import_result(self,key,raw,*,request_sha256,batch_id,custom_id,provenance=None):
        """Import exact downloaded artifact after executor's identity check.

        No replacement, retry, fabricated identity or inferred Batch ownership.
        Raw response provenance is retained alongside the request digest.
        """
        if len(key)!=64 or any(c not in '0123456789abcdef' for c in key):raise ValueError('invalid_request_key')
        if not batch_id or not custom_id:raise ValueError('missing_batch_provenance')
        with self.lock:
            plan=self.root/(key+'.request.json')
            if not plan.exists() or sha256(plan.read_bytes()).hexdigest()!=request_sha256:
                raise ValueError('batch_request_identity_mismatch')
            self._verify_import(key,raw,provenance,batch_id,custom_id)
            data=json.dumps(raw,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
            result=self.root/(key+'.result.json')
            if result.exists():
                if result.read_bytes()!=data:raise ValueError('batch_result_overwrite_forbidden')
                receipt_path=self.root/(key+'.receipt.json')
                if not receipt_path.exists():raise ValueError('batch_import_incomplete_requires_review')
                old=json.loads(receipt_path.read_text(encoding='utf-8'))
                if old.get('batch_id')!=batch_id or old.get('custom_id')!=custom_id or old.get('provenance')!=provenance:
                    raise ValueError('batch_result_provenance_replacement_forbidden')
                return
            with result.open('xb') as out:out.write(data);out.flush();os.fsync(out.fileno())
            proof=dict(request_sha256=request_sha256,result_sha256=sha256(data).hexdigest(),batch_id=batch_id,custom_id=custom_id,provenance=provenance)
            with (self.root/(key+'.receipt.json')).open('x',encoding='utf-8') as out:
                json.dump(proof,out,sort_keys=True);out.flush();os.fsync(out.fileno())
            self.pending.discard(key)
