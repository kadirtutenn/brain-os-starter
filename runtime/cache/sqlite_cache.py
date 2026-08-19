"""Small deterministic SQLite cache with explicit source/version keys."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class SQLiteCache:
    def __init__(self, path: str | Path, namespace: str):
        self.path = Path(path)
        self.namespace = namespace
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS cache_entries (
                    namespace TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    source_version TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    PRIMARY KEY(namespace, cache_key)
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def get(self, key: str, source_version: str) -> Any | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT value_json, expires_at, source_version FROM cache_entries "
                "WHERE namespace=? AND cache_key=?",
                (self.namespace, key),
            ).fetchone()
            if not row or row[2] != source_version or (row[1] and row[1] < time.time()):
                if row:
                    db.execute("DELETE FROM cache_entries WHERE namespace=? AND cache_key=?",
                               (self.namespace, key))
                return None
            return json.loads(row[0])

    def put(self, key: str, source_version: str, value: Any, ttl_seconds: int | None = None) -> None:
        now = time.time()
        expires = now + ttl_seconds if ttl_seconds else None
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO cache_entries VALUES (?, ?, ?, ?, ?, ?)",
                (self.namespace, key, source_version,
                 json.dumps(value, ensure_ascii=False, sort_keys=True), now, expires),
            )

    def clear(self) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM cache_entries WHERE namespace=?", (self.namespace,))
