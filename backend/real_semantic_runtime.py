"""Opt-in real transports; ratified request builders and scorers are unchanged.

The private JSON journal is separate from every semantic SQLite cache. Unknown
billing consumes the full reservation; failed requests are never resent implicitly.
"""
import json
import os
import threading
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen

MODEL = 'gpt-4.1-2025-04-14'
LOCK = threading.RLock()


class Budget:
    def __init__(self, config):
        self.config = config
        self.root = Path(config['journal_directory']).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.root / 'active.lock'
        # Exclusive process ownership prevents duplicate spending after restart.
        self.owner = self.lock_path.open('x')
        self.owner.write(str(os.getpid())); self.owner.flush()
        self.path = self.root / 'ledger.jsonl'
        authorization=self.root/'authorization.json'
        if authorization.exists() and json.loads(authorization.read_text(encoding='utf-8'))!=config:
            self.close(); raise ValueError('El registro pertenece a otra autorización')
        if not authorization.exists():authorization.write_text(json.dumps(config,ensure_ascii=False),encoding='utf-8')
        self.cap = Decimal(str(config['max_usd']))
        if self.cap <= 0 or int(config['max_calls']) <= 0:
            self.close(); raise ValueError('Invalid authorization limits')

    def close(self):
        if getattr(self, 'owner', None):
            self.owner.close(); self.owner = None
            self.lock_path.unlink(missing_ok=True)

    def events(self):
        return [json.loads(line) for line in self.path.read_text(encoding='utf-8').splitlines()] if self.path.exists() else []

    def append(self, event):
        with self.path.open('a', encoding='utf-8') as out:
            out.write(json.dumps(event, ensure_ascii=False)+'\n'); out.flush(); os.fsync(out.fileno())

    def request(self, body, endpoint):
        if body.get('model')!=MODEL or endpoint not in ('responses','chat/completions'):
            raise ValueError('Solicitud fuera del modelo o endpoint autorizado')
        wire = json.dumps(body, ensure_ascii=False).encode()
        key = sha256(endpoint.encode()+wire).hexdigest()
        output = body.get('max_output_tokens', body.get('max_completion_tokens'))
        reserve = Decimal((2*len(wire)+8192)*2 + output*8)/1000000
        with LOCK:
            events = self.events()
            previous = [e for e in events if e.get('key') == key]
            settled = next((e for e in reversed(previous) if e['kind']=='settled'), None)
            if settled:
                data=(self.root/settled['artifact']).read_bytes()
                if sha256(data).hexdigest()!=settled['artifact_sha256']:
                    raise RuntimeError('Evidencia de proveedor alterada')
                return json.loads(data)
            if previous: raise RuntimeError('Solicitud anterior sin conciliar; no se reenvía')
            attempts = [e for e in events if e['kind']=='reserved']
            costs = {e['attempt']:Decimal(e['reserved_usd']) for e in attempts}
            for e in events:
                if e['kind']=='settled': costs[e['attempt']]=Decimal(e['actual_usd'])
            if len(attempts)>=int(self.config['max_calls']) or sum(costs.values(),Decimal(0))+reserve>self.cap:
                raise RuntimeError('Límite autorizado de llamadas o presupuesto alcanzado')
            secret = os.environ.get('OPENAI_API_KEY')
            if not secret: raise RuntimeError('OPENAI_API_KEY no disponible en el servidor')
            attempt=len(attempts)+1
            request_file=f'request_{attempt:05d}.json'
            (self.root/request_file).write_bytes(wire)
            self.append(dict(kind='reserved',attempt=attempt,key=key,reserved_usd=str(reserve),
                request_artifact=request_file,request_sha256=sha256(wire).hexdigest()))
        # No retry handler, SDK retry, key logging, or browser credential exposure.
        request=Request('https://api.openai.com/v1/'+endpoint,data=wire,
            headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json'},method='POST')
        try:
            with urlopen(request,timeout=180) as response: raw=json.load(response)
            usage=raw['usage']
            inp=usage.get('input_tokens',usage.get('prompt_tokens'))
            out=usage.get('output_tokens',usage.get('completion_tokens'))
            if type(inp) is not int or type(out) is not int or min(inp,out)<0:
                raise ValueError('Uso no conciliable')
            details=usage.get('input_tokens_details',usage.get('prompt_tokens_details',{})) or {}
            cached=details.get('cached_tokens',0)
            if type(cached) is not int or not 0<=cached<=inp:raise ValueError('Uso cacheado inválido')
            actual=(Decimal((inp-cached)*2+out*8)+Decimal(cached)/2)/1000000
            if raw.get('model')!=MODEL or actual>reserve: raise ValueError('Identidad o reserva incompatible')
            artifact=f'response_{attempt:05d}.json'
            data=json.dumps(raw,ensure_ascii=False).encode('utf-8')
            with LOCK:
                (self.root/artifact).write_bytes(data)
                self.append(dict(kind='settled',attempt=attempt,key=key,actual_usd=str(actual),artifact=artifact,
                    artifact_sha256=sha256(data).hexdigest(),input_tokens=inp,output_tokens=out,cached_tokens=cached))
            return raw
        except Exception as error:
            with LOCK:self.append(dict(kind='failure',attempt=attempt,key=key,error_type=type(error).__name__))
            raise RuntimeError('Fallo de API; reserva conservada y sin reintento automático') from None


class CrisisStore:
    """Compatibility store for the unchanged OpenAIPrivate.run decoder."""
    def __init__(self, root): self.path=root/'decoder.json'; self.values={}
    def cached(self,key): return self.values.get(key)
    def put(self,key,value): self.values[key]=value
    def reserve(self,*args): return 1
    def settle(self,*args): pass


def configure(app, path):
    config=json.loads(Path(path).read_text(encoding='utf-8'))
    if config.get('explicit_user_approval') is not True:
        raise ValueError('Autorización de presupuesto pendiente')
    if config.get('model')!=MODEL or not config.get('authorization_id'):
        raise ValueError('Modelo o identidad de autorización inválidos')
    if not os.environ.get('OPENAI_API_KEY'):raise ValueError('Falta OPENAI_API_KEY en entorno seguro')
    from backend.integrated_evaluation import AdendaV11Provider
    from backend.evaluators.ansiedad_semantic.budgeted_reader import envelope
    from backend.evaluators.ansiedad_semantic.indexed_citations import catalog, resolve_indices
    from backend.evaluators.ansiedad_semantic.reader_schema import structurally_valid
    budget=Budget(config)
    provider=AdendaV11Provider()
    provider.store=CrisisStore(budget.root)
    provider.allow_api=True
    provider.timeout=180
    provider.credential_getter=lambda:os.environ.get('OPENAI_API_KEY')
    provider.transport=lambda body,key:budget.request(json.loads(body),'responses')
    def anxiety(request):
        raw=budget.request(envelope(request,MODEL),'chat/completions')
        choice=raw['choices'][0]
        if choice['finish_reason']!='stop' or choice['message'].get('refusal'):
            raise ValueError('Lectura incompleta o rechazada')
        reading=json.loads(choice['message']['content'])
        if '_response_schema' not in request:reading=resolve_indices(reading,catalog(request))
        if not structurally_valid(request,reading):raise ValueError('Salida fuera del contrato ratificado')
        return reading
    app.state.evaluation_dependencies=dict(crisis_provider=provider,anxiety_reader=anxiety,
        anxiety_model=MODEL,allowed_experiment_ids=config.get('allowed_experiment_ids',[]),
        evaluation_lock=LOCK,authorization_id=config['authorization_id'])
    return budget
