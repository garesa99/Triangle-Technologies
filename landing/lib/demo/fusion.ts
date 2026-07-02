// In-browser port of the brain's fusion math (brain/app/geo.py, localization.py, scoring.py,
// remote_id.py). The DEMO runs entirely bearing-less + without GNSS-PPS, so localization is
// always COARSE (signal-weighted centroid + uncertainty ellipse) — exactly what the Python
// bench injector produces. Same decomposable threat model, same friend-or-foe rule.

import type { FriendOrFoe, ThreatBreakdown } from '../types';

const R = 6_378_137;

export function haversineM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const p1 = (lat1 * Math.PI) / 180;
  const p2 = (lat2 * Math.PI) / 180;
  const dp = ((lat2 - lat1) * Math.PI) / 180;
  const dl = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

export function bearingDeg(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const p1 = (lat1 * Math.PI) / 180;
  const p2 = (lat2 * Math.PI) / 180;
  const dl = ((lon2 - lon1) * Math.PI) / 180;
  const y = Math.sin(dl) * Math.cos(p2);
  const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

// Signal-weighted centroid → { lat, lon, spread_m } (spread = weighted RMS distance = honest ellipse).
export function weightedCentroid(points: { lat: number; lon: number; w: number }[]): {
  lat: number;
  lon: number;
  spread: number;
} {
  let wsum = 0;
  for (const p of points) wsum += p.w;
  if (wsum === 0) wsum = 1;
  let lat = 0;
  let lon = 0;
  for (const p of points) {
    lat += p.lat * p.w;
    lon += p.lon * p.w;
  }
  lat /= wsum;
  lon /= wsum;
  let varSum = 0;
  for (const p of points) varSum += p.w * haversineM(p.lat, p.lon, lat, lon) ** 2;
  return { lat, lon, spread: Math.sqrt(varSum / wsum) };
}

function pointToPolygonM(lat: number, lon: number, poly: [number, number][]): number {
  const segDist = (px: number, py: number, ax: number, ay: number, bx: number, by: number): number => {
    const dx = bx - ax;
    const dy = by - ay;
    if (dx === 0 && dy === 0) return Math.hypot(px - ax, py - ay);
    const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
    return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
  };
  let inside = false;
  let j = poly.length - 1;
  for (let i = 0; i < poly.length; i++) {
    const [yi, xi] = poly[i];
    const [yj, xj] = poly[j];
    if (xi > lon !== xj > lon && lat < ((yj - yi) * (lon - xi)) / (xj - xi) + yi) inside = !inside;
    j = i;
  }
  if (inside) return 0;
  let best = Infinity;
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i];
    const b = poly[(i + 1) % poly.length];
    best = Math.min(best, segDist(lat, lon, a[0], a[1], b[0], b[1]));
  }
  return best * 111_000;
}

const CORROB_MAX = 1.6;
const UNCOOP_BONUS = 1.6;
const GEOFENCE_MAX = 1.5;
const APPROACH_MAX = 1.3;

export function scoreTrack(args: {
  signatureConfidence: number;
  nNodes: number;
  nSensorTypes: number;
  uncooperative: boolean;
  lat: number | null;
  lon: number | null;
  headingDeg: number | null;
  geofences: { name: string; polygon: [number, number][] }[];
}): ThreatBreakdown {
  const corroboration_bonus = Math.min(
    CORROB_MAX,
    1 + 0.15 * (args.nNodes - 1) + 0.1 * (args.nSensorTypes - 1),
  );
  const uncooperative_bonus = args.uncooperative ? UNCOOP_BONUS : 1;
  let geofence_proximity = 1;
  let approach_vector = 1;
  let nearest: { name: string | null; distance_m: number } | null = null;

  if (args.lat != null && args.lon != null && args.geofences.length) {
    let best: { d: number; g: { name: string; polygon: [number, number][] } } | null = null;
    for (const g of args.geofences) {
      if (!g.polygon.length) continue;
      const d = pointToPolygonM(args.lat, args.lon, g.polygon);
      if (!best || d < best.d) best = { d, g };
    }
    if (best) {
      nearest = { name: best.g.name, distance_m: Math.round(best.d * 10) / 10 };
      geofence_proximity = 1 + (GEOFENCE_MAX - 1) * Math.max(0, 1 - best.d / 2000);
      if (args.headingDeg != null) {
        const poly = best.g.polygon;
        let cy = 0;
        let cx = 0;
        for (const p of poly) {
          cy += p[0];
          cx += p[1];
        }
        cy /= poly.length;
        cx /= poly.length;
        const brgToZone = bearingDeg(args.lat, args.lon, cy, cx);
        const diff = Math.abs(((brgToZone - args.headingDeg + 180) % 360) - 180);
        approach_vector = 1 + (APPROACH_MAX - 1) * Math.max(0, 1 - diff / 180);
      }
    }
  }

  const r3 = (n: number) => Math.round(n * 1000) / 1000;
  const factors = {
    signature_confidence: r3(args.signatureConfidence),
    corroboration_bonus: r3(corroboration_bonus),
    uncooperative_bonus: r3(uncooperative_bonus),
    geofence_proximity: r3(geofence_proximity),
    approach_vector: r3(approach_vector),
  };
  let raw = 1;
  for (const v of Object.values(factors)) raw *= v;
  return {
    score: Math.round(Math.min(1, raw) * 10000) / 10000,
    factors,
    nearest_geofence: nearest,
  };
}

// Friend-or-foe: the demo has only physical (acoustic) detections and NO Remote ID → uncooperative.
export function classifyFoe(): FriendOrFoe {
  return {
    cooperative: false,
    matched_serial: null,
    has_physical: true,
    has_remote_id: false,
    uncooperative: true,
  };
}
