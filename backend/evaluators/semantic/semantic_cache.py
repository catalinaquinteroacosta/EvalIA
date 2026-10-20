"""
EvalIA - Caché semántico persistente.

Objetivo:
Evitar llamadas repetidas al modelo local cuando una operación semántica
idéntica ya fue resuelta previamente.

Principios:
- El caché NO modifica resultados.
- El caché NO puntúa indicadores.
- El caché NO interpreta lenguaje.
- La clave depende de todos los elementos que pueden cambiar la salida:
  extractor, versión, modelo, prompt/schema y entrada.
- Los datos se almacenan localmente en SQLite.
- Si cambia cualquiera de los elementos versionados, se genera otra clave
  y el resultado anterior no se reutiliza.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any
from contextlib import closing


CACHE_SCHEMA_VERSION = "1"

DEFAULT_CACHE_PATH = (
    Path(__file__).resolve().parents[3]
    / ".evalia_cache"
    / "semantic_cache.sqlite3"
)

_LOCK = threading.RLock()


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


class SemanticCache:
    """
    Caché persistente SQLite para resultados semánticos.
    """

    def __init__(
        self,
        path: str | Path = DEFAULT_CACHE_PATH,
        *,
        enabled: bool = True,
    ) -> None:
        self.path = Path(path)
        self.enabled = bool(enabled)

        self.hits = 0
        self.misses = 0
        self.writes = 0

        if self.enabled:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(
        self.path,
        timeout=30.0,
    )

    def _initialize(self) -> None:
        with _LOCK:
            with closing(self._connect()) as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS semantic_cache (
                        cache_key TEXT PRIMARY KEY,
                        payload TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                    """
                )

                connection.commit()

    def get(
        self,
        cache_key: str,
    ) -> Any | None:
        """
        Devuelve el resultado almacenado o None si no existe.

        Se devuelve una estructura reconstruida desde JSON,
        evitando compartir objetos mutables en memoria.
        """

        if not self.enabled:
            self.misses += 1
            return None

        with _LOCK:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    """
                    SELECT payload
                    FROM semantic_cache
                    WHERE cache_key = ?
                    """,
                    (cache_key,),
                ).fetchone()

        if row is None:
            self.misses += 1
            return None

        self.hits += 1
        return json.loads(row[0])

    def set(
        self,
        cache_key: str,
        value: Any,
    ) -> None:
        """
        Guarda un resultado JSON-serializable.

        INSERT OR REPLACE permite regenerar de forma explícita
        una entrada si fuera necesario.
        """

        if not self.enabled:
            return

        payload = _canonical_json(value)

        with _LOCK:
            with closing(self._connect()) as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO semantic_cache (
                        cache_key,
                        payload,
                        created_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        cache_key,
                        payload,
                        time.time(),
                    ),
                )

                connection.commit()

        self.writes += 1

    def delete(
        self,
        cache_key: str,
    ) -> bool:
        if not self.enabled:
            return False

        with _LOCK:
            with closing(self._connect()) as connection:
                cursor = connection.execute(
                    """
                    DELETE FROM semantic_cache
                    WHERE cache_key = ?
                    """,
                    (cache_key,),
                )

                connection.commit()

                return cursor.rowcount > 0

    def clear(self) -> int:
        """
        Borra únicamente el caché semántico de EvalIA.
        """

        if not self.enabled:
            return 0

        with _LOCK:
            with closing(self._connect()) as connection:
                count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM semantic_cache
                    """
                ).fetchone()[0]

                connection.execute(
                    """
                    DELETE FROM semantic_cache
                    """
                )

                connection.commit()

        return int(count)

    def count(self) -> int:
        if not self.enabled:
            return 0

        with _LOCK:
            with closing(self._connect()) as connection:
                return int(
                    connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM semantic_cache
                        """
                    ).fetchone()[0]
                )

    def stats(self) -> dict[str, int | bool | str]:
        return {
            "enabled": self.enabled,
            "path": str(self.path),
            "entries": self.count(),
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
        }


semantic_cache = SemanticCache()