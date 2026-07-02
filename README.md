# Triangle Mesh

Software for a mesh of low-cost, self-built passive sensor nodes — assembled from commercially available components — that detect **uncooperative** drones
— drones that do not broadcast their position — by signatures they cannot suppress (propeller
**sound**, control/video **RF**), use the **absence** of a Remote ID broadcast as a friend-or-foe
filter, fuse detections across nodes, and localize to an **honestly-labeled** tier. Many low-cost
bearings → one confident fix. Triangle.

> Non-negotiable: **real signals only.** No synthetic drones or fake tracks ever reach the live
> picture. Test fixtures live in `tests/` and never feed the UI. Every detection carries which
> sensor produced it, its confidence, its time source, and its localization quality.

## Layout
| dir | what |
|---|---|
| `node-agent/` | runs on each node: plugin sensors, on-node detection, mesh, buffered idempotent delivery |
| `brain/` | FastAPI + SQLite fusion server: ingest, association, tiered localization, scoring, alerts, websocket. Fully offline. |
| `landing/` | **the public website (one Vercel project):** marketing page at `/` and the operator console at `/console`. The console runs a self-contained browser **demo** (no backend) when `NEXT_PUBLIC_DEMO_MODE=1`, or connects to a real brain otherwise. Noindex. |
| `ui/` | standalone copy of the operator console, for the optional self-hosted **live** deployment (docker / Hetzner) against a real brain |
| `db/` | schema migration + node seed |
| `deploy/` | docker-compose (brain + console), `VERCEL_DEMO.md` (deploy the website), Hetzner docs |
| `tests/` | brain fusion, acoustic DSP, full-spine integration, synthetic eval |
| `docs/CONTRACT.md` | the single source of truth (schema, API, WS, tiers) — read this first |
| `RECON.md` `CAPABILITIES.md` `FIELD_TEST.md` | honest hardware recon, limits, and real-drone validation |
| `pitch/DIANA_ONEPAGER.md` | the pitch, generated from the true build state |

## Quick start (local, offline, no hardware)
```bash
# 1) Brain
python3 -m venv .venv && . .venv/bin/activate
pip install -r brain/requirements.txt
TRIANGLE_TOKEN=dev uvicorn app.main:app --app-dir brain --host 0.0.0.0 --port 8000
# health: curl localhost:8000/health

# 2) Website: marketing page + operator console (new shell)
cd landing && npm install
NEXT_PUBLIC_DEMO_MODE=1 npm run dev         # http://localhost:3000  (console at /console, browser demo)
# For the live operator picture instead, unset the flag and set NEXT_PUBLIC_BRAIN_URL to the brain.

# 3) A node (new shell) — no sensors present on a laptop, so it registers and reports silence
cd node-agent && pip install -r requirements.txt
cp config.example.yaml config.yaml         # set brain_url/token
python agent.py -c config.yaml
```
On real hardware, run `RECON.md` first, then the node-agent detects live sensors automatically.

## Run the tests
```bash
. .venv/bin/activate
pip install -r brain/requirements.txt pytest numpy
python -m pytest tests/ -q                  # 16 tests: fusion, PPS guard, TDOA, relay, DSP, spine
python tests/eval_acoustic_synthetic.py     # prints acoustic precision/recall (synthetic)
```

## Deploy
- Website (marketing + `/console` demo) on one Vercel project: `deploy/VERCEL_DEMO.md`.
- Field system (brain + console on one offline machine): `deploy/README.md`.
- Nodes (each node): `node-agent/README.md`.
- Optional hosted live console (brain on a real server): `deploy/hetzner/README.md`.

## Build order (the spine first)
Sensor recon → schema + plugin interface → **acoustic detection into the brain and onto the map**
→ Remote ID → RF (if band-capable) → registration + multi-node association + COARSE → mesh
discovery/cue/relay → PPS-guarded PRECISE/TDOA → scoring + alerts → UI → landing → field test →
DIANA one-pager. See each phase's status in `pitch/DIANA_ONEPAGER.md`.

## Honesty
Detection is probabilistic and range-limited. The system labels its own uncertainty and refuses to
draw a precision the data doesn't support. See `CAPABILITIES.md` for what each layer can and cannot
do. No NATO branding; "built for the NATO DIANA application" wording only.
