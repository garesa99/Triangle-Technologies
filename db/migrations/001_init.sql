-- Triangle Mesh — canonical schema (schema_version 1).
-- The brain auto-applies this shape on startup (brain/app/db.py). This file is the reviewable
-- source of record and the migration seed for a Postgres/PostGIS deployment.
--
-- SQLite (default, zero-setup local/field mode): types as below.
-- PostGIS (optional, for scale): replace (lat REAL, lon REAL) columns with GEOGRAPHY(Point,4326)
--   and add GIST indexes; all geo math otherwise lives in brain/app/geo.py so this is optional.

CREATE TABLE IF NOT EXISTS nodes (
    node_id       TEXT PRIMARY KEY,
    agent_version TEXT,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    alt_m         REAL,
    sensors_json  TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    last_seen     TEXT,
    last_health   TEXT
);

CREATE TABLE IF NOT EXISTS detections (
    detection_id            TEXT PRIMARY KEY,   -- idempotency key
    node_id                 TEXT NOT NULL,
    sensor_type             TEXT NOT NULL,      -- registered string, not a closed enum
    observed_at             TEXT NOT NULL,
    pps_precise             INTEGER NOT NULL,
    signature_class         TEXT NOT NULL,
    confidence              REAL NOT NULL,
    bearing_deg             REAL,
    bearing_uncertainty_deg REAL,
    signal_level            REAL,
    remote_id_payload       TEXT,
    raw_features            TEXT,
    lat                     REAL NOT NULL,
    lon                     REAL NOT NULL,
    alt_m                   REAL,
    time_source             TEXT NOT NULL,      -- gnss_pps | ntp | system
    schema_version          INTEGER NOT NULL,
    relayed_via             TEXT,               -- node_id of relay, else NULL
    track_id                TEXT,
    received_at             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_det_observed ON detections(observed_at);
CREATE INDEX IF NOT EXISTS idx_det_track ON detections(track_id);

CREATE TABLE IF NOT EXISTS tracks (
    track_id         TEXT PRIMARY KEY,
    first_seen       TEXT NOT NULL,
    last_seen        TEXT NOT NULL,
    localization     TEXT NOT NULL,             -- BEARING_ONLY | COARSE_FIX | PRECISE_FIX
    lat              REAL,
    lon              REAL,
    uncertainty_m    REAL,
    heading_deg      REAL,
    signature_class  TEXT,
    confidence       REAL,
    cooperative      INTEGER NOT NULL DEFAULT 0,
    threat_score     REAL,
    threat_breakdown TEXT,
    node_ids         TEXT,
    sensor_types     TEXT,
    relay_path       TEXT,
    state            TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id     TEXT PRIMARY KEY,
    track_id     TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    state        TEXT NOT NULL DEFAULT 'new',   -- new | acknowledged | closed
    threat_score REAL,
    evidence     TEXT,
    updated_at   TEXT
);

CREATE TABLE IF NOT EXISTS geofences (
    id           TEXT PRIMARY KEY,
    name         TEXT,
    kind         TEXT,                          -- protected | exclusion
    polygon_json TEXT NOT NULL,                 -- [[lat,lon],...]
    created_at   TEXT NOT NULL
);
