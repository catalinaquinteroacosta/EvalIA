"""User-invoked local review launcher; no credentials or paid transport."""
import argparse
import json
import threading
import time
import webbrowser
from urllib.request import urlopen
from backend.validation_runtime import configure, OUTPUT
from backend.local_server import serve

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8879);parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args();url=f'http://127.0.0.1:{args.port}'
    from backend.luna_credentials import load
    try:load()
    except RuntimeError:print('Credencial cifrada no accesible: usa CONFIGURAR_CREDENCIAL_LUNA.cmd; no se mostrará ninguna clave.',flush=True)
    def running():
        try:
            with urlopen(url+'/api/status',timeout=1) as response:data=json.load(response)
            if data.get('project')!='EvalIA' or not data.get('real_mode_available'):return False
            with urlopen(url+'/api/real/status',timeout=1) as response:real=json.load(response)
            return real.get('model')=='gpt-6-luna'
        except Exception:return False
    if running():
        print('EvalIA de validación ya está abierta: '+url,flush=True)
        if not args.no_browser:webbrowser.open(url+'/nuevo-experimento')
        return
    import sqlite3
    from backend.validation_runtime import ROOT
    workbench=ROOT/'.evalia-private/luna_ui/application.db'
    if not workbench.exists():
        workbench.parent.mkdir(parents=True,exist_ok=True)
        source=sqlite3.connect('file:'+(OUTPUT/'verified/application.db').resolve().as_posix()+'?mode=ro',uri=True)
        target=sqlite3.connect(workbench);source.backup(target);source.close();target.close()
    main,_=configure(workbench)
    if not args.no_browser:
        def open_when_ready():
            for _ in range(50):
                if running():webbrowser.open(url+'/nuevo-experimento');return
                time.sleep(.2)
        threading.Thread(target=open_when_ready,daemon=True).start()
    serve(main.app,args.port)

if __name__=='__main__':main()
