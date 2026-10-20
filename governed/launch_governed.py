"""Explicit local launcher. Opening UI never grants spending or loads a key."""
import argparse,json,sys,time,threading,webbrowser
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'venv/Lib/site-packages'))
from deploy_bootstrap import create_app
def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--no-browser',action='store_true');args=p.parse_args()
    path=Path(args.config).resolve();config=json.loads(path.read_text(encoding='utf8'));config['config_path']=str(path)
    url='http://127.0.0.1:'+str(config['port'])
    def running():
        try:
            with urlopen(url+'/api/multi/status',timeout=1) as response:state=json.load(response)
            return 'governance' in state
        except Exception:return False
    if running():
        if not args.no_browser:webbrowser.open(url+'/laboratorio?experiment_id=108')
        return
    app=create_app(config)
    if config.get('start_authorized_workers') is True:
        # local_server has no ASGI lifespan; explicit operator flag still required.
        app.state.governed_supervisor.start()
    if not args.no_browser:
        def open_ready():
            for _ in range(50):
                if running():webbrowser.open(url+'/laboratorio?experiment_id=108');return
                time.sleep(.2)
        threading.Thread(target=open_ready,daemon=True).start()
    from backend.local_server import serve
    serve(app,config['port'])
if __name__=='__main__':main()
