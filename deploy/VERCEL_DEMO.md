# Deploy the whole site on Vercel — ONE project

The marketing site **and** the operator console are now a **single Next.js app** in `landing/`.
The console lives at the internal route **`/console`** and the demo runs **entirely in the
browser** (synthetic audio → the real ported detector + fusion → a moving track/alert), so there
is **no backend, no database, no websocket** — just one static site on Vercel.

- Landing page → `/`
- Operator console (demo) → `/console`   (linked from the nav, hero, and contact section)
- "← Back to site" link on the console returns to `/`.

> The real field system still runs offline/local against the actual brain (see `deploy/README.md`
> and the standalone `ui/` app). Only this demo site goes on the public internet.

## Deploy (one project)
1. Vercel → **New Project** → import the repo.
2. **Root Directory = `landing`**  ← the only setting that matters (the repo root has no app).
3. **Environment Variables** → add:
   - `NEXT_PUBLIC_DEMO_MODE` = `1`   ← makes `/console` run the self-contained browser demo.
4. Deploy. Open the site → click **Live demo** (or **Open the live console**) → the operator
   picture appears with a moving track + alert under a **"Simulated scenario"** banner.

That's it. One project, one deploy, fully navigable. No `NEXT_PUBLIC_DEMO_URL` needed (the link is
internal); set it only if you ever host the console on a different URL.

## What the demo actually does (say this honestly)
- Per node it **synthesizes drone audio** at a level set by the target's distance and runs it
  through the **same detector algorithm** that runs on hardware (harmonic-comb + spectral flatness
  + broadband gating, ported to TS in `landing/lib/demo/detector.ts` — verified to match the
  Python). The confidences are produced by the real algorithm, not typed in.
- It fuses them with the **same fusion math** (`landing/lib/demo/fusion.ts`): signal-weighted
  centroid → COARSE uncertainty ellipse, decomposable threat score, friend-or-foe.
- Every track is flagged `bench_test` → the **"Simulated scenario — synthetic audio through the
  real detection pipeline. Not live sensor data."** banner. No GNSS-PPS in a browser → it stays
  COARSE, exactly like the real bearing-less mesh. Acknowledge/Close work locally.

## Local check
```bash
cd landing && npm install
NEXT_PUBLIC_DEMO_MODE=1 npm run dev     # http://localhost:3000  →  landing;  /console → demo
# (or leave the env unset and open /console?demo)
```

## Running the console against a REAL brain (field / live)
Build/run without `NEXT_PUBLIC_DEMO_MODE` and set `NEXT_PUBLIC_BRAIN_URL` /
`NEXT_PUBLIC_BRAIN_TOKEN`; `/console` then connects to a live brain. A hosted *live* brain needs a
real server (not Vercel) — see the optional `deploy/hetzner/` path, or run the offline stack from
`deploy/README.md`.
