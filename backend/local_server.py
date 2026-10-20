"""Local-only development HTTP bridge for the actual FastAPI ASGI application.

No test readers, credentials, or semantic SQLite caches are created.
Real readers require an explicit server-side authorization file and environment key.
Useful where Windows application control blocks uvicorn/click's ctypes import.
"""
import asyncio
import argparse
import os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit


def serve(app,port):
    class Handler(BaseHTTPRequestHandler):
        def request(self):
            parsed=urlsplit(self.path)
            try:length=int(self.headers.get('Content-Length',0))
            except ValueError:self.send_error(400);return
            if length<0 or length>8*1024*1024:self.send_error(413);return
            body=self.rfile.read(length);events=[]
            scope=dict(type='http',asgi={'version':'3.0','spec_version':'2.4'},http_version='1.1',method=self.command,
                scheme='http',path=parsed.path,raw_path=parsed.path.encode(),query_string=parsed.query.encode(),root_path='',
                headers=[(k.lower().encode('latin-1'),v.encode('latin-1')) for k,v in self.headers.items()],
                server=('127.0.0.1',port),client=self.client_address)
            async def receive():return {'type':'http.request','body':body,'more_body':False}
            async def send(event):events.append(event)
            try:asyncio.run(app(scope,receive,send))
            except Exception:
                import traceback;traceback.print_exc()
                if not any(e['type']=='http.response.start' for e in events):self.send_error(500);return
            start=next(e for e in events if e['type']=='http.response.start')
            self.send_response(start['status'])
            for key,value in start.get('headers',[]):self.send_header(key.decode('latin-1'),value.decode('latin-1'))
            self.end_headers()
            try:
                for event in events:
                    if event['type']=='http.response.body':self.wfile.write(event.get('body',b''))
            except (BrokenPipeError,ConnectionResetError):pass
        do_GET=request;do_POST=request;do_HEAD=request
        def log_message(self,*args):pass
    class LocalServer(ThreadingHTTPServer):allow_reuse_address=False
    server=LocalServer(('127.0.0.1',port),Handler)
    enabled=bool(getattr(app.state,'evaluation_dependencies',None))
    replay=bool((getattr(app.state,'evaluation_dependencies',None) or {}).get('replay_only'))
    mode='consulta sin gasto; modo REAL disponible mediante confirmación en la interfaz.' if replay else 'configurada con límite autorizado.' if enabled else 'deshabilitada sin configuración autorizada.'
    print(f'EvalIA local: http://127.0.0.1:{port} — API semántica '+mode,flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Puerto inválido')
    from backend.main import app
    budget=None
    if os.environ.get('EVALIA_LUNA_SYNC_AUTHORIZATION') and os.environ.get('EVALIA_SEMANTIC_AUTHORIZATION'):
        raise ValueError('Seleccione una sola autorización de lector semántico')
    if os.environ.get('EVALIA_LUNA_SYNC_AUTHORIZATION'):
        from backend.luna_sync_runtime import configure
        budget=configure(app,os.environ['EVALIA_LUNA_SYNC_AUTHORIZATION'])
    elif os.environ.get('EVALIA_SEMANTIC_AUTHORIZATION'):
        from backend.real_semantic_runtime import configure
        budget=configure(app,os.environ['EVALIA_SEMANTIC_AUTHORIZATION'])
    try:serve(app,args.port)
    finally:
        if budget:budget.close()


if __name__=='__main__':main()
