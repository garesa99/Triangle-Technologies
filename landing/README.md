# Triangle Mesh — Landing Page

Public marketing landing page for **Triangle Mesh**, a passive, distributed,
attritable drone-detection mesh. Standalone Next.js (App Router, TypeScript)
app that **static-exports** and deploys to Vercel.

> This app is **completely separate** from the field system. It shares no code,
> secrets, or configuration with the sensor/brain codebase.

## Pre-launch status: NOINDEX

The site ships with `<meta name="robots" content="noindex, nofollow">` (set in
`app/layout.tsx`). **It will not be indexed by search engines.** Remove the
`robots` metadata / meta tag only when you are ready for public launch.

## Local development

```bash
npm install
npm run dev      # http://localhost:3000
```

## Build (static export)

`next.config.mjs` sets `output: 'export'`, so a production build emits a fully
static site to `out/`:

```bash
npm install
npm run build    # produces ./out
```

`out/` is a plain static bundle (HTML/CSS/JS) — no Node server required to
serve it. Fonts (Inter, JetBrains Mono) are self-hosted via `next/font`.

## Deploy to Vercel

This is a **monorepo** — the Next.js app is in `landing/`, and the repo root has
no `package.json`. So the one setting that matters is **Root Directory**.

> If you see `Error: No Next.js version detected` on Vercel, it means the Root
> Directory is pointing at the repo root (no `next` there). Set it to `landing`.

**Option A — Git integration (recommended):**

1. Import the repo in the Vercel dashboard.
2. **Set Root Directory to `landing`** (Project → Settings → Build & Deployment →
   Root Directory, or during import). This is the fix for the monorepo.
3. Framework preset: **Next.js** (auto-detected once Root Directory is `landing`).
   Vercel sees `output: 'export'` and serves the static build from `out/`. Leave
   Build Command / Output Directory on their Next.js defaults.
4. Deploy. Set `NEXT_PUBLIC_DEMO_URL` in Environment Variables if you have a
   hosted console.

Do **not** add a custom `vercel.json` at the repo root with `framework: null` —
the dashboard's Next.js preset overrides it and detection still fails. Pointing
Root Directory at `landing` is the correct, single fix.

**Option B — Vercel CLI:**

```bash
npm i -g vercel
vercel            # preview
vercel --prod     # production
```

If you prefer to deploy the raw static bundle as a static site:

```bash
npm run build
vercel deploy --prebuilt   # after `vercel build`, or point any static host at ./out
```

## Imagery & licensing

Photos are Unsplash hotlinks (Unsplash License — free commercial use, no
attribution required). See [`public/images/CREDITS.md`](public/images/CREDITS.md).
Images degrade gracefully: if a hotlink is unreachable, the layout is unaffected
and a dark solid block is shown instead. Core layout never depends on a runtime
image fetch.

The three technical diagrams are original inline SVGs (ours), labeled
"Illustrative". There are no fabricated live-detection screenshots anywhere on
the page.

## Operator console — same site, `/console`

This app is BOTH the marketing site (`/`) and the operator console (`/console`). The nav, hero,
and contact links point at the internal `/console` route. On the console, a "← Back to site" link
returns to `/`. The console's styling is fully scoped under `.console-shell` so it never leaks into
the marketing pages.

Set **`NEXT_PUBLIC_DEMO_MODE=1`** so `/console` runs the self-contained browser demo (no backend).
Full deploy steps: [`../deploy/VERCEL_DEMO.md`](../deploy/VERCEL_DEMO.md). Console internals live in
`components/` and `lib/` (incl. `lib/demo/`). Override the link with `NEXT_PUBLIC_DEMO_URL` only if
you host the console elsewhere.

## Design system

- Fully **black & white**: background near-black `#0A0A0B`, white display type with
  tight tracking (`-0.04em`). The single "accent" is pure white; hierarchy comes
  from weight, size, and hairlines, not colour.
- Inter (display/body) + JetBrains Mono (specs/labels/captions) via `next/font`.
- Hairline rules, sharp corners, generous negative space, full-bleed imagery
  treated to pure `grayscale(1)` so photos read as stark monochrome silhouettes.
- Scroll-triggered reveals (fade + small translate-y) via `IntersectionObserver`
  in `app/components/Reveal.tsx`. Respects `prefers-reduced-motion`.
