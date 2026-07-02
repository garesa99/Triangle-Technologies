# Triangle Mesh — System Contract (single source of truth)

Every component (`node-agent`, `brain`, `ui`, `db`) builds against this document.
Change this first, then the code. `schema_version` below is bumped on any breaking change.

Current `schema_version`: **1**

---

## 1. Detection (the one row everything normalizes to)

A detection is the atomic output of any sensor on any node. JSON Schema:
`db/detection.schema.json`. Fields:

| field | type | null? | notes |
|---|---|---|---|
| `detection_id` | string (uuid) | no | client-generated; **idempotency key** — brain dedupes on this |
| `node_id` | string | no | stable id of the emitting node |
| `sensor_type` | string | no | registered string, NOT a hard enum: `acoustic\|rf24\|rf58\|remote_id\|pir\|seismic\|magnetometer\|<new>` |
| `observed_at` | string (ISO-8601 UTC) | no | detection time |
| `pps_precise` | bool | no | true only if `observed_at` was disciplined by GNSS-PPS |
| `signature_class` | string | no | e.g. `multirotor_acoustic`, `fpv_video_link`, `mavic_remoteid`, `unknown` |
| `confidence` | number 0..1 | no | probability the signature is a drone; NEVER a binary claim |
| `bearing_deg` | number 0..360 | yes | true-north bearing from node, null if sensor can't bear |
| `bearing_uncertainty_deg` | number | yes | 1-sigma, null when `bearing_deg` null |
| `signal_level` | number | yes | dB or normalized level, sensor-defined |
| `remote_id_payload` | object | yes | parsed F3411 fields when `sensor_type=remote_id` |
| `raw_features` | object | yes | sensor-specific feature dump (MFCC stats, band power, …) |
| `node_position` | {lat, lon, alt_m?} | no | node's own fixed position at time of detection |
| `time_source` | string | no | `gnss_pps\|ntp\|system` — localization tier depends on this |
| `schema_version` | integer | no | must equal brain's supported version |
| `relayed_via` | string | yes | node_id of relay if store-and-forward was used, else null |

**Hard rules**
- No detection is ever synthesized into the live picture. Silence is reported as silence (node health), not as a row.
- `confidence` and `time_source` are required on EVERY row.
- A PRECISE (TDOA) fix is only permitted when the contributing rows have `pps_precise=true` AND `time_source=gnss_pps`.

---

## 2. Node manifest (registration handshake)

`POST /register` body — sent by node on startup and on loadout change:

```json
{
  "node_id": "node-alpha",
  "agent_version": "0.1.0",
  "position": { "lat": 52.37, "lon": 4.90, "alt_m": 3 },
  "sensors": [
    { "sensor_type": "acoustic", "signature_classes": ["multirotor_acoustic"],
      "provides_bearing": false, "spec": { "channels": 1, "sample_rate": 48000 } }
  ],
  "schema_version": 1
}
```

The brain stores the loadout; the UI renders coverage/legend/node-cards from it. Sensor logic in
the brain keys off `sensor_type`/`signature_class`/`provides_bearing` — never a hardcoded list.

---

## 3. Brain HTTP API

| method | path | auth | body/notes |
|---|---|---|---|
| `POST` | `/register` | bearer | node manifest (§2). Upserts node + loadout. |
| `POST` | `/detections` | bearer | `{ "detections": [Detection, …] }`. Idempotent by `detection_id`. Accepts `relayed_via`. |
| `GET` | `/nodes` | bearer | registered nodes + loadout + last_seen + health |
| `POST` | `/nodes/{id}/health` | bearer | heartbeat: GNSS/PPS lock, neighbors, jam/spoof state |
| `GET` | `/tracks` | bearer | current fused tracks with localization tier |
| `GET` | `/alerts` | bearer | alert list + evidence chains |
| `POST` | `/alerts/{id}/ack` | bearer | new → acknowledged |
| `POST` | `/alerts/{id}/close` | bearer | → closed |
| `GET` | `/health` | none | liveness (no secrets) |
| `WS` | `/ws` | bearer (query token) | pushes `{type: tracks\|alerts\|nodes\|mesh, ...}` |

Auth: `Authorization: Bearer <TRIANGLE_TOKEN>`. Same token node→brain and node→node.

---

## 4. Mesh (node ↔ node)

- **Discovery**: mDNS service `_triangle-node._tcp` (+ UDP-broadcast fallback on multicast-blocking APs). Brain advertises `_triangle-brain._tcp`.
- **Cross-cue** (UDP multicast, NOT a detection): `{ node_id, sensor_type, signature_class, confidence, bearing_deg?, observed_at, ttl_s }`. Neighbors may raise sensitivity for `ttl_s`. Cues NEVER enter the detection table.
- **Relay**: if brain unreachable, node POSTs buffered detections to a reachable neighbor's `/relay`, which forwards to the brain with `relayed_via` set to the relaying node. Idempotent by `detection_id`.

---

## 5. Localization tiers (UI must always show which one)

- `BEARING_ONLY` — 1 node, 1 bearing → a ray.
- `COARSE_FIX` — 2+ concurrent detections → bearing intersection OR signal-weighted centroid → **uncertainty ellipse**.
- `PRECISE_FIX` — 3+ nodes with `pps_precise` GNSS-PPS timestamps → TDOA multilateration → point + small ellipse. Code MUST downgrade to COARSE if PPS is absent.

---

## 6. Threat score (decomposable, never a bare number)

`score = signature_confidence × corroboration_bonus × geofence_proximity × uncooperative_bonus × approach_vector`
Each factor is stored and shown. `uncooperative_bonus` applies when a physical detection has NO matching Remote ID within the association window.
