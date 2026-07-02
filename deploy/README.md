# Deploy

Three things get deployed independently. The **field system** (brain + UI) never needs the
internet; the **landing page** is the only internet-facing component and shares nothing with it.

## 1. Brain + Operator UI (one machine, offline)
A field laptop, a Pi, or a small VPS. Nodes reach it over the LAN.

### With Docker
```bash
cd deploy
export TRIANGLE_TOKEN="$(openssl rand -hex 16)"        # strong shared token
export BRAIN_PUBLIC_URL="http://<this-machine-LAN-IP>:8000"   # what operator browsers hit
docker compose up --build
# UI:    http://<LAN-IP>:3000
# Brain: http://<LAN-IP>:8000  (health: /health)
```
Data persists in the `brain-data` volume. Everything runs with no internet.

### Without Docker (bare)
```bash
# brain
cd brain && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
TRIANGLE_TOKEN=... uvicorn app.main:app --host 0.0.0.0 --port 8000
# ui (separate shell)
cd ui && npm install && NEXT_PUBLIC_BRAIN_URL=http://<LAN-IP>:8000 NEXT_PUBLIC_BRAIN_TOKEN=... npm run build && npm run start
```

Seed node identities + a protected zone (optional — nodes also self-register on startup):
```bash
cd db/seed && python seed_nodes.py --brain http://<LAN-IP>:8000 --token "$TRIANGLE_TOKEN" --file nodes.example.json
```

If you host the operator UI anywhere reachable off the field LAN, put it behind a passcode and
`noindex` (guardrail).

## 2. Nodes (each Raspberry Pi)
See `node-agent/README.md`. Summary: `sudo ./install.sh`, edit `/etc/triangle/config.yaml`
(node_id, position, brain_url, token), `sudo systemctl enable --now triangle-node`. Nodes also
discover the brain and each other via mesh beacons.

## 3. Landing page (public, Vercel)
See `landing/README.md`. Static export (`output: 'export'`).
```bash
cd landing && npm install && npm run build     # emits out/
vercel deploy --prebuilt        # or: import the repo in Vercel, root = landing/
```
Keep it `noindex` until the launch decision. No NATO logos; "Built for the NATO DIANA
application" wording only.

> Security note: the landing app is a **static export served from a CDN** — it has no Node
> server, middleware, or runtime image optimization, so the Next.js server-side advisories
> flagged by `npm audit` are not reachable in this deployment. Re-check before any change that
> introduces a server runtime.
