"""Explicit private-copy offline Batch planning launcher. No API submission."""
import argparse
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description='Luna offline Batch planning only; no paid requests or production activation.')
    parser.add_argument('--application-db',required=True,help='Existing private copy of application DB, never the active DB.')
    parser.add_argument('--queue-dir',required=True)
    parser.add_argument('--allowed-experiment-ids',required=True,help='Comma separated explicit IDs of private test experiments.')
    parser.add_argument('--port',type=int,default=18762)
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Invalid localhost port')
    from backend import database
    private=Path(args.application_db).resolve()
    if private==database.DB_PATH.resolve() or not private.is_file():parser.error('An existing isolated application DB copy is required')
    try:
        allowed={int(x.strip()) for x in args.allowed_experiment_ids.split(',')}
        if not allowed or min(allowed)<1:raise ValueError()
    except ValueError:parser.error('Explicit positive experiment IDs are required')
    # Application DB only. Semantic cache modules are never imported here.
    database.DB_PATH=private;database.DATABASE_DIR=private.parent
    from backend.main import app
    from backend.luna_application import PrivateBatchQueue
    from backend.luna_runner import dependencies
    from backend.local_server import serve
    app.state.evaluation_dependencies=dependencies(PrivateBatchQueue(args.queue_dir),allowed_experiment_ids=allowed)
    print('Luna: planificación Batch offline; API pagada deshabilitada. HTTP 202 no es una evaluación final.',flush=True)
    serve(app,args.port)


if __name__=='__main__':main()
