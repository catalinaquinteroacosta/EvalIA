
"""Cach? privada y aut?noma de EM."""

import hashlib
import json
import sqlite3
import threading
import time

from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")

CACHE_SCHEMA_VERSION = '1'

_LOCK = threading.RLock()

EM_CACHE_PATH = (
    Path(__file__).resolve().parent
    / ".em_cache"
    / "semantic_cache.sqlite3"
)

def _canonical_json(value: Any) -> str:
    """
    Serialización determinista usada tanto para claves como para valores.
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_cache_key(
    *,
    extractor: str,
    extractor_version: str,
    model: str,
    prompt_version: str,
    schema_version: str,
    parameters: dict[str, Any] | None,
    inputs: dict[str, Any],
) -> str:
    """
    Construye una clave SHA-256 reproducible.

    Si cambia modelo, extractor, prompt, schema, parámetros o entrada,
    cambia la clave.
    """

    payload = {
        "cache_schema_version": CACHE_SCHEMA_VERSION,
        "extractor": extractor,
        "extractor_version": extractor_version,
        "model": model,
        "prompt_version": prompt_version,
        "schema_version": schema_version,
        "parameters": parameters or {},
        "inputs": inputs,
    }

    canonical = _canonical_json(payload)

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()



class EMPrivateCache:
    def __init__(self, path):
        self.path = Path(path)
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def _connect(self):
        return sqlite3.connect(self.path, timeout=30.0)

    def get(self, key):
        with _LOCK:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT payload FROM semantic_cache "
                    "WHERE cache_key = ?",
                    (key,),
                ).fetchone()

        if row is None:
            self.misses += 1
            return None

        self.hits += 1
        return json.loads(row[0])

    def set(self, key, value):
        payload = _canonical_json(value)

        with _LOCK:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO semantic_cache
                    (cache_key, payload, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (key, payload, time.time()),
                )

        self.writes += 1

    def count(self):
        with _LOCK:
            with self._connect() as connection:
                return connection.execute(
                    "SELECT COUNT(*) FROM semantic_cache"
                ).fetchone()[0]


class LazyPrivateCache:
    """Importing an anxiety evaluator must not open a database."""

    def __init__(self, path):
        self.path = Path(path)
        self._instance = None

    def _cache(self):
        with _LOCK:
            if self._instance is None:
                self._instance = EMPrivateCache(self.path)
            return self._instance

    def get(self, key):
        return self._cache().get(key)

    def set(self, key, value):
        return self._cache().set(key, value)

    def count(self):
        return self._cache().count()

    def delete(self, key):
        # Only this private namespace can be invalidated.
        with _LOCK, self._cache()._connect() as connection:
            connection.execute('DELETE FROM semantic_cache WHERE cache_key = ?', (key,))


_em_cache = LazyPrivateCache(EM_CACHE_PATH)


def cached_semantic_operation(
    *,
    extractor: str,
    extractor_version: str,
    model: str,
    prompt_version: str,
    schema_version: str,
    parameters: dict[str, Any] | None,
    inputs: dict[str, Any],
    execute: Callable[[], T],
    validate_result: Callable[[T], T],
) -> T:
    key = build_cache_key(
        extractor=extractor,
        extractor_version=extractor_version,
        model=model,
        prompt_version=prompt_version,
        schema_version=schema_version,
        parameters=parameters,
        inputs=inputs,
    )

    cached = _em_cache.get(key)

    if cached is not None:
        return validate_result(cached)

    raw = execute()
    validated = validate_result(raw)
    _em_cache.set(key, validated)

    return validated
