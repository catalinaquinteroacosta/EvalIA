"""Build the local read-only report cache for an existing governed installation."""
import argparse
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from backend.global_results import report, workbook

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
    config=json.loads(Path(args.config).read_text(encoding='utf8'))
    def connection():
        db=sqlite3.connect(Path(config['database']).resolve().as_uri()+'?mode=ro',uri=True)
        db.row_factory=sqlite3.Row
        return db
    app=SimpleNamespace(state=SimpleNamespace(direct_recovery_config=config,
        direct_recovery_database=str(Path(config['project_root'])/'.evalia-private/direct_recovery/recovery.db')))
    data=report(SimpleNamespace(app=app,get_connection=connection))
    target=Path(config['project_root'])/'exports/resultados_globales';target.mkdir(parents=True,exist_ok=True)
    (target/'EvalIA_resultados_globales.xlsx').write_bytes(workbook(data))
    print(json.dumps(dict(scenarios=len(data['experiments']),responses=len(data['responses']),
        numeric=sum(r['numeric'] for r in data['responses']),na=sum(r['na'] for r in data['responses']),
        pending=sum(r['pending'] for r in data['responses']),
        groups=[dict(title=g['title'],scenarios=g['scenarios'],values={m['model']:m['percentage'] for m in g['models']}) for g in data['groups']]),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
