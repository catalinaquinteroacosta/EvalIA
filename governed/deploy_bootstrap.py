"""Future explicit entry point. Never replaces main.py or starts on import."""
import json,sys,sqlite3
from pathlib import Path
def create_app(config):
    import os
    if config.get('openai_project'):os.environ['OPENAI_PROJECT']=config['openai_project']
    project=Path(config['project_root']).resolve();sys.path.insert(0,str(project))
    from backend import database
    if config.get('validation_runtime') is True:
        from backend.validation_runtime import configure
        main,_=configure(Path(config['database']).resolve())
    else:
        database.DB_PATH=Path(config['database']).resolve();database.DATABASE_DIR=database.DB_PATH.parent
        from backend import main
    def connect():
        c=sqlite3.connect(database.DB_PATH,timeout=15);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
    main.get_connection=connect
    from governed_routes import mount
    service=main.app.state.luna_real_service
    if config.get('service_root'):service.root=Path(config['service_root']).resolve()
    mount(main,service,{**config,'bind_primary_flow':True})
    from direct_recovery_routes import mount as mount_direct_recovery
    mount_direct_recovery(main,config)
    if config.get('start_authorized_workers') is True:
        from governed_supervisor import Supervisor
        supervisor=Supervisor(config['config_path'])
        # The local runtime has no ASGI lifespan and starts supervision explicitly
        # in launch_governed. Full FastAPI installations may provide this hook.
        if hasattr(main.app,'add_event_handler'):
            main.app.add_event_handler('startup',supervisor.start)
        main.app.state.governed_supervisor=supervisor
    return main.app
if __name__=='__main__':
    import argparse,uvicorn
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args()
    path=Path(a.config).resolve();config=json.loads(path.read_text(encoding='utf8'));config['config_path']=str(path)
    uvicorn.run(create_app(config),host='127.0.0.1',port=int(config.get('port',8895)))
