"use client";

// Self-contained DEMO engine — runs ENTIRELY in the browser, no backend.
// Each tick it synthesizes drone audio per node (level set by distance), runs it through the
// REAL ported detector (detector.ts) to get genuine confidences, then fuses them with the REAL
// ported fusion math (fusion.ts) into one moving COARSE track + alert. Everything is flagged
// bench_test → the console shows a "SIMULATED SCENARIO" banner. Honest: synthetic input, real
// algorithms, clearly labeled. This is what lets the demo run on Vercel with zero infrastructure.

import { useEffect, useRef, useState } from "react";
import type { Alert, AlertState, Geofence, MeshNode, Track } from "../types";
import { acousticFeatures, scoreDrone } from "./detector";
import { bearingDeg, classifyFoe, haversineM, scoreTrack, weightedCentroid } from "./fusion";

const SR = 16000;
const N = 8192;
const ALERT_THRESHOLD = 0.55;
const TICK_MS = 1500;

const NODE_POS: Record<string, [number, number]> = {
  "node-alpha": [52.3702, 4.8952],
  "node-bravo": [52.3728, 4.901],
  "node-charlie": [52.3675, 4.9008],
};

const GEOFENCE: Geofence = {
  id: "gf-apron",
  name: "Protected apron",
  kind: "protected",
  polygon: [
    [52.3695, 4.8975],
    [52.3695, 4.8995],
    [52.371, 4.8995],
    [52.371, 4.8975],
  ],
};

const PATH: [number, number][] = [
  [52.3675, 4.9012], [52.3682, 4.9004], [52.369, 4.8998], [52.3697, 4.8992],
  [52.3702, 4.8986], [52.3706, 4.8982], [52.37, 4.8978], [52.3692, 4.8982], [52.3684, 4.899],
];

function synthDroneAt(amp: number, f0 = 118): Float64Array {
  const x = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    const t = i / SR;
    let s = 0;
    for (let h = 1; h <= 6; h++) s += (amp / h) * Math.sin(2 * Math.PI * f0 * h * t);
    s += 0.15 * (Math.random() * 2 - 1);
    x[i] = s;
  }
  let peak = 1e-9;
  for (let i = 0; i < N; i++) peak = Math.max(peak, Math.abs(x[i]));
  for (let i = 0; i < N; i++) x[i] /= peak;
  return x;
}

const ampForDistance = (d: number): number => 1.3 * Math.exp(-d / 300);
const nowIso = (): string => new Date().toISOString();

interface Snapshot {
  nodes: MeshNode[];
  tracks: Track[];
  alerts: Alert[];
  geofences: Geofence[];
}

class DemoEngine {
  private step = 0;
  private firstSeen = nowIso();
  private prev: { lat: number; lon: number } | null = null;
  private alertState: AlertState = "new";
  private trackId = "trk-demo";
  private alertId = "alt-demo";
  private lastTrack: Track | null = null;
  private lastAlert: Alert | null = null;

  nodes(activeSensors: string[]): MeshNode[] {
    const ids = Object.keys(NODE_POS);
    return ids.map((id) => {
      const [lat, lon] = NODE_POS[id];
      return {
        node_id: id,
        agent_version: "demo",
        position: { lat, lon, alt_m: 2 },
        sensors: [
          { sensor_type: "acoustic", signature_classes: ["multirotor_acoustic"], provides_bearing: false, spec: { channels: 1 } },
        ],
        last_seen: nowIso(),
        online: true,
        health: {
          pps_lock: false,
          gnss_lock: false,
          time_source: "system",
          sensors_active: activeSensors,
          neighbors_seen: ids.filter((n) => n !== id),
        },
      };
    });
  }

  tick(): Snapshot {
    const target = PATH[this.step % PATH.length];
    this.step += 1;

    // per-node: synth audio at distance-set level -> REAL detector -> genuine confidence
    const dets: { node_id: string; lat: number; lon: number; confidence: number }[] = [];
    for (const [id, [lat, lon]] of Object.entries(NODE_POS)) {
      const dist = haversineM(lat, lon, target[0], target[1]);
      const audio = synthDroneAt(ampForDistance(dist));
      const { confidence, signature } = scoreDrone(acousticFeatures(audio, SR));
      if (signature === "multirotor_acoustic" && confidence >= 0.45) {
        dets.push({ node_id: id, lat, lon, confidence });
      }
    }

    const nodes = this.nodes(["acoustic"]);
    if (dets.length < 2) {
      // not enough concurrent detections for a COARSE fix — honest: no track this tick
      return { nodes, tracks: this.lastTrack ? [this.lastTrack] : [], alerts: this.activeAlerts(), geofences: [GEOFENCE] };
    }

    const centroid = weightedCentroid(dets.map((d) => ({ lat: d.lat, lon: d.lon, w: Math.max(0.05, d.confidence) })));
    const heading = this.prev ? bearingDeg(this.prev.lat, this.prev.lon, centroid.lat, centroid.lon) : null;
    this.prev = { lat: centroid.lat, lon: centroid.lon };

    const foe = classifyFoe();
    const conf = Math.max(...dets.map((d) => d.confidence));
    const nodeIds = dets.map((d) => d.node_id).sort();
    const threat = scoreTrack({
      signatureConfidence: conf,
      nNodes: nodeIds.length,
      nSensorTypes: 1,
      uncooperative: true,
      lat: centroid.lat,
      lon: centroid.lon,
      headingDeg: heading,
      geofences: [{ name: GEOFENCE.name, polygon: GEOFENCE.polygon }],
    });

    const track: Track = {
      track_id: this.trackId,
      first_seen: this.firstSeen,
      last_seen: nowIso(),
      localization: "COARSE_FIX",
      lat: centroid.lat,
      lon: centroid.lon,
      uncertainty_m: Math.max(150, centroid.spread),
      heading_deg: heading,
      signature_class: "multirotor_acoustic",
      confidence: conf,
      cooperative: false,
      bench_test: true,
      threat_score: threat.score,
      threat_breakdown: threat,
      node_ids: nodeIds,
      sensor_types: ["acoustic"],
      relay_path: [],
      state: "active",
      rays: [],
      localization_note: "signal-weighted centroid — simulated scenario (no bearings, no PPS → COARSE)",
      friend_or_foe: foe,
    };
    this.lastTrack = track;

    // alert lifecycle (local): raise once threatening + uncooperative, unless operator closed it
    let alerts: Alert[] = [];
    if (threat.score >= ALERT_THRESHOLD && this.alertState !== "closed") {
      const alert: Alert = {
        alert_id: this.alertId,
        track_id: this.trackId,
        state: this.alertState,
        threat_score: threat.score,
        evidence: {
          nodes: nodeIds,
          sensors: ["acoustic"],
          localization: "COARSE_FIX",
          cooperative: false,
          uncooperative: true,
          relay_path: [],
          threat,
          note: track.localization_note,
        },
      };
      this.lastAlert = alert;
      alerts = [alert];
    } else if (this.lastAlert && this.alertState === "closed") {
      alerts = [{ ...this.lastAlert, state: "closed" }];
    }

    return { nodes, tracks: [track], alerts, geofences: [GEOFENCE] };
  }

  private activeAlerts(): Alert[] {
    return this.lastAlert ? [{ ...this.lastAlert, state: this.alertState }] : [];
  }

  setAlertState(s: AlertState): void {
    this.alertState = s;
  }

  snapshot(): Snapshot {
    return {
      nodes: this.nodes(["acoustic"]),
      tracks: this.lastTrack ? [this.lastTrack] : [],
      alerts: this.activeAlerts(),
      geofences: [GEOFENCE],
    };
  }
}

export interface DemoMesh {
  nodes: MeshNode[];
  tracks: Track[];
  alerts: Alert[];
  geofences: Geofence[];
  ackAlert: (id: string) => void;
  closeAlert: (id: string) => void;
}

export function useDemoMesh(enabled: boolean): DemoMesh {
  const engineRef = useRef<DemoEngine | null>(null);
  if (enabled && !engineRef.current) engineRef.current = new DemoEngine();
  const [snap, setSnap] = useState<Snapshot>({ nodes: [], tracks: [], alerts: [], geofences: [] });

  useEffect(() => {
    if (!enabled || !engineRef.current) return;
    const eng = engineRef.current;
    setSnap(eng.tick());
    const t = setInterval(() => setSnap(eng.tick()), TICK_MS);
    return () => clearInterval(t);
  }, [enabled]);

  return {
    nodes: snap.nodes,
    tracks: snap.tracks,
    alerts: snap.alerts,
    geofences: snap.geofences,
    ackAlert: () => {
      engineRef.current?.setAlertState("acknowledged");
      if (engineRef.current) setSnap(engineRef.current.snapshot());
    },
    closeAlert: () => {
      engineRef.current?.setAlertState("closed");
      if (engineRef.current) setSnap(engineRef.current.snapshot());
    },
  };
}
