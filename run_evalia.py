"""Portable entry point; existing research installation takes precedence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent
LOCAL_CONFIG = ROOT / '.evalia-private/governed_joint_install_20261017/config.json'


def base_app():
    """Initialize a separate empty local database, never a research database."""
    sys.path.insert(0, str(ROOT / 'backend'))
    from backend import database
    database.DB_PATH = ROOT / '.evalia-private/local/application.db'
    database.DATABASE_DIR = database.DB_PATH.parent
    new_database = not database.DB_PATH.exists()
    sys.modules['database'] = database
    if new_database:
        from backend import seed_data, seed_rubrics, seed_turns, prompt_loader
        database.create_tables()
        seed_data.main()
        for rubric in ('ansiedad_depresion', 'crisis'):
            seed_rubrics.import_rubric(rubric)
        active = json.loads((prompt_loader.BANKS_DIR / 'ACTIVE.json').read_text(encoding='utf8'))
        seed_turns.PROMPTS_DIR = prompt_loader.BANKS_DIR / active['version']
        with database.get_connection() as connection:
            for name in seed_turns.PROMPTS_DIR.glob('*.json'):
                if name.name == 'MANIFEST.json':
                    continue
                prompt_loader.load_official_prompt(name.stem)
                prompt = seed_turns.load_prompt_file(name)
                scenario = seed_turns.sync_scenario(connection.cursor(), prompt)
                seed_turns.sync_scenario_turns(connection.cursor(), scenario['scenario_id'], prompt)
    from backend.main import app
    return app


def main():
    parser = argparse.ArgumentParser(description='Iniciar EvalIA localmente')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--fresh', action='store_true', help='Usar la instalacion base separada')
    parser.add_argument('--port', type=int, default=8879)
    args = parser.parse_args()
    os.chdir(ROOT)
    if LOCAL_CONFIG.is_file() and not args.fresh:
        command = [sys.executable, '-B', str(ROOT / 'governed/launch_governed.py'),
                   '--config', str(LOCAL_CONFIG)]
        if args.no_browser:
            command.append('--no-browser')
        return subprocess.call(command, cwd=ROOT)
    app = base_app()
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
