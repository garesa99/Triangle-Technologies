# Triangle Mesh — Operator Picture (UI)

The operator console for the Triangle Mesh drone-detection mesh. Next.js (App
Router, TypeScript) + MapLibre GL. **Runs fully offline** — no internet is
required at runtime.

## Quick start

```bash
cd ui
npm install
npm run dev        # http://localhost:3000
```

Production:

```bash
npm run build
npm start
```

Node 20+ (developed/verified against Node 24).

## Connecting to the brain

The UI talks to the brain over REST (Bearer token) and a websocket
(`/ws?token=…`). Defaults:

| Setting  | Env var                    | Default                  |
| -------- | -------------------------- | ------------------------ |
| Brain URL | `NEXT_PUBLIC_BRAIN_URL`    | `http://localhost:8000`  |
| Token     | `NEXT_PUBLIC_BRAIN_TOKEN`  | `triangle-dev-token`     |

Copy `.env.example` to `.env.local` to change the build-time defaults, **or**
override at runtime via the in-app **Settings** panel (top-right). Runtime
overrides persist to `localStorage` and reconnect the websocket on apply.

The websocket pushes `{type, data}` frames (`snapshot | tracks | alerts | nodes
| mesh`). On connect the brain sends a full `snapshot`; the UI merges
incremental frames after that. A reconnecting websocket drives the status
indicator: **LIVE / RECONNECTING / OFFLINE**.

## Offline map / tiles

By default the map uses a **bundled offline style** (`lib/mapStyle.ts`): a single
near-black background layer with **no tile source, no sprite, no glyph server**.
All operational geometry (nodes, tracks, rays, ellipses, geofences, mesh links,
coverage) is drawn at runtime as GeoJSON + HTML markers, so the map renders with
**zero network access**.

To use a real basemap when a tile server *is* available (still self-hostable,
e.g. a local `tileserver-gl`), set a raster tile template:

```bash
# .env.local
NEXT_PUBLIC_TILE_URL=http://localhost:8080/styles/dark/{z}/{x}/{y}.png
```

When set, tiles are dimmed/desaturated so the signal-orange accent stays
dominant. **Leaving it unset keeps the app fully offline** — this is the
default and the supported baseline.

## What's on screen

**Map**
- **Node markers** with sensor-loadout glyphs and health color (green online /
  grey stale).
- **Tracks by localization tier:**
  - `BEARING_ONLY` → bearing **ray(s)** from the node(s) (with dashed
    uncertainty wedge when `bearing_uncertainty_deg` is present).
  - `COARSE_FIX` → **uncertainty ellipse** (circle of radius `uncertainty_m`).
  - `PRECISE_FIX` → **point marker + small ellipse**.
  - **Heading arrow** whenever `heading_deg` is present.
- **Geofences** — draw/edit polygons (click-to-add-vertex, POST `/geofences`),
  inspect and delete them.
- **Mesh links** — dim lines between online nodes; when a track carries a
  non-empty `relay_path`, those hops are highlighted brighter in the accent.
- **Alert pulse** — the orange pulse animates **only** while an alert is `new`
  (unacknowledged).
- **Coverage view** — toggle to draw each node's approximate detection radius per
  sensor type (acoustic 300 m, rf 800 m, remote_id 1200 m, … configurable in
  `lib/sensors.ts`) so the operator can see mesh gaps.
- **Persistent localization-quality legend** (ray vs ellipse vs fix), bottom-left.

**Right panel**
- **Alert feed** with full evidence chains (nodes, sensors, localization + note,
  friend/foe, relay path, threat factors) and **Acknowledge / Close** buttons
  wired to the REST endpoints.
- **Inspector** (click any node / track / geofence) — track shows node_ids,
  sensor_types, signature, confidence, localization tier + note, decomposed
  threat breakdown, relay path, friend-or-foe.
- **Node-health strip** — per node: online, sensors active, GNSS/PPS lock (from
  `health`), neighbors seen, last-seen age.

**Honest empty state**
- With no tracks: `No detections. N nodes listening.` The app contains **no
  mock/demo detection data** — node markers render only from the real `/nodes`
  list, and detections/tracks/alerts come only from the live brain.

## Theme

Near-black ground (`#0A0A0B` / `#0E0E10`), a single signal-orange accent
(`#FF6A00`) reserved for active/unacknowledged tracks and alerts, monospace type
for all data/timestamps, hairline rules, sharp corners. Palette lives in
`lib/theme.ts` and `app/globals.css`.

## Project layout

```
app/            layout, page (client-only Console via dynamic import), globals.css
components/      Console, MapView, TopBar, Legend, AlertFeed, Inspector, NodeHealthStrip
lib/            types (data contract), api (REST), useMeshState (WS + reconnect),
                mapStyle (offline style), geo, sensors, theme, format, config
```

Timestamps are rendered in **UTC** (the brain emits ISO-8601 UTC) to avoid
operator-locale ambiguity.

## Demo mode (self-contained, Vercel-only, no backend)

Set **`NEXT_PUBLIC_DEMO_MODE=1`** (or append `?demo` to the URL) and the console runs entirely in
the browser with **no brain, no websocket, no database**. It synthesizes drone audio and runs it
through the *real* ported detector (`lib/demo/detector.ts`) + fusion (`lib/demo/fusion.ts`,
`lib/demo/engine.ts`) to produce a moving COARSE track + alert, labeled **"Simulated scenario."**
Acknowledge/Close work locally. This is what lets the demo deploy on Vercel with zero infra — see
`deploy/VERCEL_DEMO.md`.

```bash
NEXT_PUBLIC_DEMO_MODE=1 npm run dev     # or: open http://localhost:3000/?demo
```

Leave it unset for the real operator picture (connects to a brain via `NEXT_PUBLIC_BRAIN_URL`).
