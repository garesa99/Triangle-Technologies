"""SQLite storage — zero-setup local mode. PostGIS is a drop-in for scale (see db/README).

All geo math is done in Python (app/geo.py), so no spatial extension is required in the field.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Iterable, Optional

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    node_id       TEXT PRIMARY KEY,
    agent_version TEXT,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    alt_m         REAL,
    sensors_json  TEXT NOT NULL,   -- sensor loadout + capabilities
    registered_at TEXT NOT NULL,
    last_seen     TEXT,
    last_health   TEXT             -- json: gnss_pps lock, neighbors, etc.
);

CREATE TABLE IF NOT EXISTS detections (
    detection_id  TEXT PRIMARY KEY,           -- idempotency key
    node_id       TEXT NOT NULL,
    sensor_type   TEXT NOT NULL,
    observed_at   TEXT NOT NULL,
    pps_precise   INTEGER NOT NULL,
    signature_class TEXT NOT NULL,
    confidence    REAL NOT NULL,
    bearing_deg   REAL,
    bearing_uncertainty_deg REAL,
    signal_level  REAL,
    remote_id_payload TEXT,
    raw_features  TEXT,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    alt_m         REAL,
    time_source   TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    relayed_via   TEXT,
    track_id      TEXT,
    received_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_det_observed ON detections(observed_at);
CREATE INDEX IF NOT EXISTS idx_det_track ON detections(track_id);

CREATE TABLE IF NOT EXISTS tracks (
    track_id      TEXT PRIMARY KEY,
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    localization  TEXT NOT NULL,     -- BEARING_ONLY | COARSE_FIX | PRECISE_FIX
    lat           REAL,
    lon           REAL,
    uncertainty_m REAL,
    heading_deg   REAL,
    signature_class TEXT,
    confidence    REAL,
    cooperative   INTEGER NOT NULL DEFAULT 0,
    threat_score  REAL,
    threat_breakdown TEXT,
    node_ids      TEXT,              -- json list contributing nodes
    sensor_types  TEXT,              -- json list contributing sensors
    relay_path    TEXT,              -- json list relayed_via seen
    bench_test    INTEGER NOT NULL DEFAULT 0,  -- provenance: bench-injected test signal, NOT a live field detection
    state         TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id      TEXT PRIMARY KEY,
    track_id      TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    state         TEXT NOT NULL DEFAULT 'new',  -- new | acknowledged | closed
    threat_score  REAL,
    evidence      TEXT,             -- json evidence chain
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS geofences (
    id            TEXT PRIMARY KEY,
    name          TEXT,
    kind          TEXT,             -- protected | exclusion
    polygon_json  TEXT NOT NULL,    -- [[lat,lon],...]
    created_at    TEXT NOT NULL
);
"""


def init(db_path: str) -> None:
    global _conn
    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(SCHEMA)
    # defensive migration for DBs created before bench_test existed
    try:
        _conn.execute("ALTER TABLE tracks ADD COLUMN bench_test INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already present
    _conn.commit()


def conn() -> sqlite3.Connection:
    assert _conn is not None, "db.init() not called"
    return _conn


def execute(sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    with _lock:
        cur = _conn.execute(sql, tuple(params))
        _conn.commit()
        return cur


def query(sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with _lock:
        return _conn.execute(sql, tuple(params)).fetchall()


def query_one(sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
    with _lock:
        return _conn.execute(sql, tuple(params)).fetchone()


def j(v: Any) -> Optional[str]:
    return None if v is None else json.dumps(v)


def loads(v: Optional[str]) -> Any:
    return None if v in (None, "") else json.loads(v)
