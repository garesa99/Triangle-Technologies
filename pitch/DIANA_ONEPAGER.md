# Triangle Mesh — NATO DIANA one-pager

*Built for the NATO DIANA application. Not affiliated with, endorsed by, or representing NATO.*
*Generated from the true state of the build — what is live today is marked LIVE; the rest is ROADMAP.*

## Problem
Cooperative air-awareness (Remote ID, ADS-B) only sees aircraft that **announce themselves**. The
threat — a low-cost uncooperative drone over a base, border, airport, or event — does not. Conventional
counter-air is far too expensive to point at a €500 quadcopter. There is a cost-asymmetry gap and a
sensing gap at the low, slow, small end of the airspace.

## Solution
A mesh of **passive, attritable** sensor nodes (~€150 of commodity hardware each) that detect drones
by the signatures they cannot suppress — **propeller acoustics** and **control/video RF** — and use
the **absence** of a Remote ID broadcast as a friend-or-foe filter. Nodes emit nothing. The
intelligence is in the **fusion layer and the mesh**, not any single sensor. Many low-cost bearings →
one confident fix. Triangle.

## What is LIVE today (working software, tested)
- **On-node detection** — plugin sensor architecture; acoustic drone detector (zero-training DSP
  heuristic; synthetic sanity-check precision 1.000 / recall 0.875 / F1 0.933 — a discrimination
  number, not a field claim); Remote ID reader; band-gated 2.4/5.8 GHz RF energy detector; GNSS/PPS
  time + jam/spoof health. Any sensor subset; honest hardware probing.
- **Fusion brain** — idempotent ingest, cross-node association, **tiered localization**
  (BEARING-ONLY ray → COARSE ellipse → PRECISE TDOA fix) with a hard code-level **PPS guard** that
  refuses a precise fix it hasn't earned, decomposable threat scoring, alert lifecycle, live
  websocket. Runs fully **offline** on a laptop. 16 automated tests green, incl. a full spine
  integration (real detector → brain → track) and mesh store-and-forward relay to a live brain.
- **Operator picture** — offline Next.js + MapLibre console: nodes/health, bearing rays, uncertainty
  ellipses, precise fixes, mesh links + relay highlight, always-on localization-quality legend,
  alert feed with evidence chains, coverage view, honest empty state (no fabricated contacts).
- **Mesh** — zero-config discovery (mDNS + UDP-broadcast fallback), cross-cueing, and HTTP
  store-and-forward relay so a dropped link never loses data.
- **Public site** — austere DIANA-ready landing page (static, noindex, no NATO marks).

## What is ROADMAP (honestly not done)
- Real-world range/accuracy numbers from a live drone fly-by. The software and procedure are ready
  (`FIELD_TEST.md`); this step is **gated on obtaining flight authorizations and a permitted test
  site** — including an exemption to fly a non-broadcasting *uncooperative* drone for ground truth
  (Remote ID is legally mandated). With permissions in hand it is an afternoon of work.
- Trained acoustic model on an open dataset (training script shipped; heuristic is today's default).
- PIR / seismic / magnetometer detectors (plugin stubs prove the path; `detect()` is TODO).
- Hardening for contested RF, wind robustness, and larger meshes.

## Why now
Commodity SDRs, MEMS mics, and OpenDroneID receivers are inexpensive and widely available; small-drone
incursions at airports and critical infrastructure are a recurring, publicly-reported problem.
Passive, distributed, attritable sensing is the affordable counter to an affordable threat.

## Unit economics (one node, indicative BOM)
| item | ~€ |
|---|---|
| Quad-core ARM64 single-board computer | 55–80 |
| USB / I2S microphone (or small array) | 10–30 |
| SDR for 2.4/5.8 GHz (RTL-SDR+upconverter / HackRF) | 30–120 |
| ESP32 OpenDroneID receiver | 8 |
| u-blox GNSS (+PPS) | 15–25 |
| enclosure, power, SD | 20–30 |
| **≈ per node** | **~€150 (± by SDR choice)** |
Coverage scales roughly linearly with node count; losing a node degrades, never blinds.

## The differentiator: honest uncertainty
The system labels its own confidence and localization quality on every track and refuses to draw a
precision it can't support. **Systems that overclaim get people hurt.** In a defense evaluation,
calibrated honesty is a feature, not a caveat.

**Contact:** ogabrielreyes99@gmail.com
