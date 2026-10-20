"""Validate a genuinely new source checkout without credentials or API calls."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import run_evalia
    if (ROOT / '.evalia-private').exists():
        raise SystemExit('Run this check in a clean checkout, not an existing research installation.')
    app = run_evalia.base_app()
    from backend import database
    with database.get_connection() as connection:
        counts = {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                  for table in ('scenarios', 'conversation_turns', 'ai_models', 'experiments')}
    assert counts == dict(scenarios=38, conversation_turns=190, ai_models=5, experiments=0), counts
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        assert client.get('/static/styles.css').status_code == 200
        assert client.get('/api/experiments').status_code == 200
        response = client.post('/api/real/prepare', json={'response_ids': [1]})
        assert response.status_code == 409, response.text
    assert not list((ROOT / '.evalia-private/luna_ui/plans').glob('*'))
    print('Clean checkout: UI, 38 scenarios, 190 turns, exports dependencies and qualification guard OK.')


if __name__ == '__main__':
    main()
