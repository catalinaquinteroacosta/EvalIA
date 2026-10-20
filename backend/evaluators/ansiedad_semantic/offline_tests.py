"""Run explicitly selected offline tests with network disabled and temporary SQLite only.

Does not load project providers, credentials, or caches itself.
"""
from pathlib import Path
import builtins
import io
import os
import socket
import sqlite3
import sys
import tempfile


def forbidden(*args, **kwargs):
    raise RuntimeError('Offline anxiety tests prohibit network and SQLite access')


def main():
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root))
    # Reuse installed pure Python dependencies without repairing the old venv.
    sys.path.append(str(root / 'venv/Lib/site-packages'))
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    connect = sqlite3.connect
    temporary_root = Path(tempfile.gettempdir()).resolve()

    def temporary_database(database, *args, **kwargs):
        if database == ':memory:':
            return connect(database, *args, **kwargs)
        path = Path(database).resolve()
        if not path.is_relative_to(temporary_root):
            return forbidden()
        return connect(database, *args, **kwargs)

    sqlite3.connect = temporary_database
    socket.create_connection = forbidden
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    for module in (builtins, io):
        original = module.open

        def guarded(file, *args, _original=original, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                name = Path(os.fsdecode(file)).name.lower()
                if name == '.env' or name.startswith('.env.'):
                    raise RuntimeError('Offline tests prohibit reading credentials files')
            return _original(file, *args, **kwargs)

        module.open = guarded
    import pytest
    class PrivateCacheIsolation:
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_protocol(self, item, nextitem):
            from backend.evaluators.ansiedad_semantic import private_cache
            directory = tempfile.mkdtemp(prefix='evalia_anxiety_test_')
            if directory:  # Preserve isolated test databases; never delete evidence.
                previous = private_cache.semantic_cache.path
                previous_instance = private_cache.semantic_cache._instance
                private_cache.semantic_cache.path = Path(directory) / 'private.sqlite3'
                private_cache.semantic_cache._instance = None
                try:
                    yield
                finally:
                    private_cache.semantic_cache.path = previous
                    private_cache.semantic_cache._instance = previous_instance

    return pytest.main(['-p', 'no:cacheprovider', *sys.argv[1:]], plugins=[PrivateCacheIsolation()])


if __name__ == '__main__':
    raise SystemExit(main())
