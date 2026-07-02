# Deploy everything on Vercel (no backend, no infra)

For a presentation, the whole thing runs on **Vercel only** — two static/client Next.js projects,
no server, no database, no Hetzner. The console runs a **self-contained DEMO mode**: synthetic
audio through the *real* ported detector + fusion, entirely in the browser, clearly labeled
**"Simulated scenario."**

> This is the demo shop-window. The real field system still runs offline/local against the actual
> brain (see `deploy/README.md`); that part is not — and should not be — on Vercel.

## Two Vercel projects from the same repo
Both just need their **Root Directory** set (the repo root has no app — that's the only gotcha).

### Project 1 — Landing page
1. Import the repo in Vercel → **New Project**.
2. **Root Directory = `landing`**.
3. Add Environment Variable:
   - `NEXT_PUBLIC_DEMO_URL` = the console URL from Project 2 (fill in after you create it, then redeploy).
4. Deploy. (It's `noindex` until you remove the meta tag.)

### Project 2 — Operator console (DEMO)
1. Import the **same repo** again → **New Project** (a second project).
2. **Root Directory = `ui`**.
3. Add Environment Variable:
   - `NEXT_PUBLIC_DEMO_MODE` = `1`   ← this turns on the self-contained browser demo (no backend).
4. Deploy. Open it — you'll see the operator picture with a **moving track + alert** under a
   **"Simulated scenario"** banner. Acknowledge/Close work locally.
5. Copy this project's URL back into Project 1's `NEXT_PUBLIC_DEMO_URL` and redeploy the landing.

That's it. The landing page's nav "Live demo" / hero "Open the live console" now open the hosted,
self-contained demo. Nothing else to run.

## What the demo actually does (so you can speak to it honestly)
- Per node, it **synthesizes drone audio** whose level is set by the target's distance, and runs
  it through the **same detector algorithm** that runs on hardware (harmonic-comb + spectral
  flatness + broadband gating — ported to TypeScript in `ui/lib/demo/detector.ts`). The
  confidences are produced by the real algorithm, not typed in.
- It fuses the detections with the **same fusion math** (signal-weighted centroid → COARSE
  uncertainty ellipse, decomposable threat score, friend-or-foe) in `ui/lib/demo/fusion.ts`.
- Every track is flagged `bench_test`, so the console shows the **"Simulated scenario — synthetic
  audio through the real detection pipeline. Not live sensor data."** banner. It never claims to be
  a live field detection. No GNSS-PPS in the browser → it stays COARSE, exactly like the real
  bearing-less mesh.

## Local check before you deploy
```bash
cd ui && npm install
NEXT_PUBLIC_DEMO_MODE=1 npm run dev      # http://localhost:3000  (or add ?demo to any console URL)
```

## When you have real hardware
Turn demo mode OFF (unset `NEXT_PUBLIC_DEMO_MODE`) and point the console at a real brain via
`NEXT_PUBLIC_BRAIN_URL` / `NEXT_PUBLIC_BRAIN_TOKEN`. The same console is both the demo and the real
operator picture — only the data source changes. (A hosted *live* brain needs a real server, e.g.
the optional `deploy/hetzner/` path — not Vercel.)
