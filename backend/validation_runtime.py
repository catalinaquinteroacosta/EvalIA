"""Explicit isolated replay server; never sends an API request or opens shared cache."""
import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from backend.luna_application import request_key, ProcessLock
from backend import database

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/economic_readers_step3_2_20261016/adjudicated_final_20261016'
OUTPUT=ROOT/'docs/step4_final_20261016'

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))

class ExactReplay:
    def __init__(self):
        self.rows={r['key']:r for r in read(EVIDENCE/'followup_v17/ENTREGA_FINAL/LINaje_56_Cuerpos.json')}
        self.used=[]
    def __call__(self,body,endpoint):
        key=request_key(body,endpoint)[0]
        row=self.rows.get(key)
        if row is None or row['body']!=body:
            raise RuntimeError('offline_validation_has_no_original_receipt_for_request')
        raw=Path(row['raw_response']).read_bytes();receipt=read(row['receipt'])
        if receipt.get('request_sha256')!=key or receipt.get('response_sha256')!=sha256(raw).hexdigest() or receipt.get('http_status')!=200:
            raise RuntimeError('original_receipt_integrity_failure')
        self.used.append(key)
        return json.loads(raw)

def configure(db_path):
    path=Path(db_path).resolve()
    workbench=(ROOT/'.evalia-private/luna_ui').resolve()
    if path==database.DB_PATH.resolve() or not (path.is_relative_to(OUTPUT.resolve()) or path.is_relative_to(workbench)) or not path.is_file():
        raise ValueError('existing_isolated_step4_database_required')
    database.DB_PATH=path;database.DATABASE_DIR=path.parent
    from backend import main,luna_reader,luna_runner
    def connect():
        con=sqlite3.connect(path);con.row_factory=sqlite3.Row;con.execute('PRAGMA foreign_keys=ON');return con
    main.get_connection=connect
    replay=ExactReplay()
    provider=luna_reader.LunaProvider(replay,certificates=read(EVIDENCE/'qualification_v19/CERTIFICATES_COMPATIBLE_V7.json'))
    main.app.state.evaluation_dependencies=dict(runner_factory=luna_runner.IntegrationRunner,
        crisis_provider=provider,anxiety_reader=lambda request:luna_reader.read_anxiety(request,replay),
        anxiety_model=luna_reader.MODEL,allowed_experiment_ids=frozenset((99,101)),
        evaluation_lock=ProcessLock(OUTPUT/'.validation.lock'),replay_only=True,
        paid_submission_enabled=False,paid_mode='disabled',authorization_id='step4_original_receipts_only')
    return main,replay

def main():
    import argparse
    from backend.local_server import serve
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8878)
    args=parser.parse_args()
    app,_=configure(OUTPUT/'verified/application.db')
    serve(app.app,args.port)

if __name__=='__main__':main()
