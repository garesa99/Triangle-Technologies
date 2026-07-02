"""Offline store-and-forward buffer. Every detection is persisted here first, then drained to
the brain (or a neighbor relay). Nothing is lost if the link is down; delivery is idempotent by
detection_id, so re-sends and relays are harmless.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any


class Buffer:
    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS outbox ("
            " detection_id TEXT PRIMARY KEY, payload TEXT NOT NULL,"
            " queued_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0)"
        )
        self._db.commit()

    def add(self, detection: dict[str, Any]) -> None:
        from datetime import datetime, timezone
        with self._lock:
            self._db.execute(
                "INSERT OR IGNORE INTO outbox (detection_id, payload, queued_at) VALUES (?,?,?)",
                (detection["detection_id"], json.dumps(detection),
                 datetime.now(timezone.utc).isoformat()),
            )
            self._db.commit()

    def pending(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT payload FROM outbox ORDER BY queued_at LIMIT ?", (limit,)
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def ack(self, detection_ids: list[str]) -> None:
        if not detection_ids:
            return
        with self._lock:
            self._db.executemany(
                "DELETE FROM outbox WHERE detection_id=?", [(d,) for d in detection_ids]
            )
            self._db.commit()

    def count(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]
