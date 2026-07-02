# FIELD TEST — validate with a REAL drone in an afternoon

Purpose: measure what the mesh actually does against ground truth, and write down the honest
numbers. Ideally fly a drone that **broadcasts Remote ID** so you get free ground-truth position
to compare the fused fix against.

## You need
- 2–3 Triangle nodes that PASSED their `RECON.md` steps, placed 50–200 m apart around an open
  area, each with a known surveyed position (enter it in `config.yaml`).
- The brain + UI running (`deploy/README.md`).
- One drone you are legally allowed to fly here. A Remote-ID-broadcasting model gives ground truth.
- A tape measure / a phone GPS to log the drone's real track, and a notebook.

## Safety & legality
Fly only where permitted, within VLOS and local UAS rules. This is a detection test, not a
counter-drone action — the system only observes.

## Procedure
1. **Baseline (silence):** with no drone, confirm the UI shows `No detections. N nodes listening.`
   Record any false positives over 5 minutes (wind, traffic, WiFi). This is your false-alarm rate.
2. **Approach runs:** fly the drone from ~300 m toward the nodes at a steady height. Note the range
   at which:
   - the first **acoustic** detection appears,
   - the first **RF** detection appears (if a band-capable SDR is installed),
   - the track reaches **COARSE_FIX**, and (if 3 PPS nodes) **PRECISE_FIX**.
3. **Localization error:** when Remote ID is broadcasting, the brain has the true position. For
   each COARSE/PRECISE track, record the distance between the fused fix and the Remote-ID truth
   (visible in the detection inspector). Do 5+ passes.
4. **Friend-or-foe:** with Remote ID ON, confirm the track shows `cooperative=true` and raises NO
   alert. Turn Remote ID OFF (if your aircraft/test rig allows) and confirm the same flight now
   flags **uncooperative** and alerts.
5. **Mesh resilience:** during a pass, drop one node's brain link (unplug its uplink or block the
   brain in its firewall). Confirm its detections **relay via a neighbor** (the track's
   `relay_path` shows the relay node) and nothing is lost. Restore and confirm catch-up.
6. **Cross-cue:** watch the agent logs — a strong detection on one node should log a cue on the
   others (`cue from … sensitivity raised`).

## Record this table
| pass | drone | RID truth? | acoustic 1st (m) | RF 1st (m) | tier reached | fix error (m) | alert? | relay ok? |
|------|-------|-----------|------------------|-----------|--------------|---------------|--------|-----------|
| 1 | | | | | | | | |
| 2 | | | | | | | | |

## What "good" looks like (set expectations honestly)
- Acoustic first-detection at tens–low-hundreds of metres, worse in wind — this is expected.
- COARSE fixes with an ellipse that CONTAINS the true position most of the time.
- PRECISE (if PPS) fix error small (tens of metres) with good node geometry; large or absent with
  poor geometry — and the UI says COARSE when it can't do better. That honesty is the pass
  criterion, not a heroic number.

Write the numbers into `CAPABILITIES.md` and `pitch/DIANA_ONEPAGER.md` — real, dated, per-site.
