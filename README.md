# Triangle Mesh

Public website for **Triangle Mesh**, a passive, distributed drone detection mesh.
Built for the NATO DIANA application.

- **`/`** marketing page.
- **`/console`** operator console. Runs a self-contained browser **demo** (no backend) when
  `NEXT_PUBLIC_DEMO_MODE=1`. The demo synthesizes audio and runs it through the real detection and
  fusion logic in the browser, and is labeled "Simulated scenario." It never claims to be live
  sensor data.

Next.js (App Router, TypeScript) + MapLibre. Fully black and white, noindex.

## Run locally
```bash
npm install
NEXT_PUBLIC_DEMO_MODE=1 npm run dev     # http://localhost:3000  (console at /console)
```

## Deploy to Vercel
Import this repo. The app is at the repo root, so Vercel auto-detects Next.js with **no Root
Directory setting**. Add one environment variable, then deploy:

```
NEXT_PUBLIC_DEMO_MODE = 1
```

The site is `noindex` until launch. It uses no NATO or DIANA marks; the wording "Built for the NATO
DIANA application" only.

## Structure
```
app/            routes: / (landing) and /console (operator console), layout, styles
components/      console UI (map, alerts, inspector, health, legend, top bar)
lib/            console data layer + the browser demo engine (lib/demo)
public/          images + credits
```
