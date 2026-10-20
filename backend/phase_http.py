"""Isolated transport candidate. No HTTP on import, no secrets in diagnostics.
One explicit POST only; no redirects/retries. Proxy CONNECT is not API dispatch.
The caller retains budgeting/authorization and durable raw/receipt settlement.
"""
import http.client,json,time,os,ssl
from pathlib import Path
from urllib.request import HTTPSHandler,HTTPRedirectHandler,build_opener,Request
from urllib.error import URLError,HTTPError

class PhaseLog:
    def __init__(self,path,identity):
        self.path=Path(path);self.identity=identity;self.phase='preflight';self.api_dispatch=False;self.started=time.monotonic()
        if self.path.exists():raise ValueError('existing attempt: replay/reconcile only, never resend')
        self.path.parent.mkdir(parents=True,exist_ok=True)
    def emit(self,phase,**fields):
        row=dict(identity=self.identity,phase=phase,elapsed_seconds=time.monotonic()-self.started,**fields)
        with self.path.open('a',encoding='utf8') as f:f.write(json.dumps(row,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
        self.phase=phase
        if phase=='api_dispatch_started':self.api_dispatch=True
    def failure(self,error):
        reason=error.reason if isinstance(error,URLError) else error
        # Do not serialize repr/str: URLs, proxy credentials or payload could leak.
        fields=dict(error_type=type(error).__name__,reason_type=type(reason).__name__,errno=getattr(reason,'errno',None),winerror=getattr(reason,'winerror',None),tls_verify_code=getattr(reason,'verify_code',None),http_status=getattr(error,'code',None),failed_phase=self.phase,classification='uncertain_no_retry' if self.api_dispatch else 'confirmed_no_api_send')
        self.emit('failure',**fields);return fields

class ObservedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self,*args,phase_log,read_timeout=180,**kwargs):
        super().__init__(*args,**kwargs);self.log=phase_log;self.read_timeout=read_timeout;self.in_connect=False
    def connect(self):
        self.log.emit('connect_started');self.in_connect=True
        try:super().connect()
        finally:self.in_connect=False
        self.sock.settimeout(self.read_timeout);self.log.emit('tls_ready')
    def send(self,data):
        if self.sock is None:self.connect()
        # During an HTTPS proxy tunnel CONNECT, no API POST has been sent.
        if not self.in_connect and not self.log.api_dispatch:self.log.emit('api_dispatch_started')
        return super().send(data)

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class ObservedHTTPSHandler(HTTPSHandler):
    def __init__(self,log,read_timeout):super().__init__();self.log=log;self.read_timeout=read_timeout
    def https_open(self,req):
        def factory(*args,**kwargs):return ObservedHTTPSConnection(*args,phase_log=self.log,read_timeout=self.read_timeout,**kwargs)
        return self.do_open(factory,req,context=self._context,check_hostname=self._check_hostname)

def open_once(body,endpoint,secret,log,*,connect_timeout=30,read_timeout=180,opener=None):
    if endpoint not in ('chat/completions','responses') or not secret:raise ValueError('confirmed invalid preflight; no API')
    if not 1<=connect_timeout<=180 or not 1<=read_timeout<=600:raise ValueError('invalid explicit timeouts')
    wire=json.dumps(body,ensure_ascii=False).encode()
    request=Request('https://api.openai.com/v1/'+endpoint,data=wire,method='POST',headers={'Authorization':'Bearer '+secret,'Content-Type':'application/json'})
    # build_opener preserves environment/system proxy support; TLS verification intact.
    opener=opener or build_opener(ObservedHTTPSHandler(log,read_timeout),NoRedirect())
    log.emit('request_prepared')
    try:
        with opener.open(request,timeout=connect_timeout) as response:
            log.emit('headers_received',http_status=response.status,remote_request_id=response.headers.get('x-request-id'))
            raw=response.read();log.emit('body_received',bytes=len(raw))
            return raw
    except Exception as exc:
        log.failure(exc);raise

def disposition(log,*,verified_receipt=False):
    if verified_receipt:return 'replay_without_network'
    if log.api_dispatch:return 'retain_reserve_and_stop_this_scope'
    return 'confirmed_no_api_send_reconcile_locally'

class LoggedResponse:
    def __init__(self,response,log):self.response=response;self.log=log;self.headers=response.headers;self.status=response.status
    def __enter__(self):self.response.__enter__();return self
    def __exit__(self,*args):return self.response.__exit__(*args)
    def read(self):
        try:
            raw=self.response.read();self.log.emit('body_received',bytes=len(raw));return raw
        except Exception as exc:self.log.failure(exc);raise

def open_request_observed(request,log,*,connect_timeout=30,read_timeout=180,opener_factory=None):
    # Wrapper for the existing official RecordedSync flow; body/auth untouched.
    log.emit('request_prepared')
    opener=opener_factory(log) if opener_factory else build_opener(ObservedHTTPSHandler(log,read_timeout),NoRedirect())
    try:
        response=opener.open(request,timeout=connect_timeout)
        log.emit('headers_received',http_status=response.status,remote_request_id=response.headers.get('x-request-id'))
        return LoggedResponse(response,log)
    except Exception as exc:log.failure(exc);raise
