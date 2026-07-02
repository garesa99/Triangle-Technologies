// Data contract types — mirror the brain exactly (docs/CONTRACT.md,
// brain/app/main.py, brain/app/fusion.py). Do NOT rename fields.

export type Localization = "BEARING_ONLY" | "COARSE_FIX" | "PRECISE_FIX";
export type AlertState = "new" | "acknowledged" | "closed";

export interface Position {
  lat: number;
  lon: number;
  alt_m: number | null;
}

export interface SensorSpec {
  [k: string]: unknown;
}

export interface NodeSensor {
  sensor_type: string;
  signature_classes: string[];
  provides_bearing: boolean;
  spec: SensorSpec;
}

// Health is stored as arbitrary JSON by the brain (db.loads(last_health)); it may be
// null. We read a few conventional keys defensively.
export interface NodeHealth {
  gnss_lock?: boolean;
  pps_lock?: boolean;
  sensors_active?: number | string[];
  neighbors_seen?: number | string[];
  [k: string]: unknown;
}

export interface MeshNode {
  node_id: string;
  agent_version: string;
  position: Position;
  sensors: NodeSensor[];
  last_seen: string | null;
  online: boolean;
  health: NodeHealth | null;
}

export interface Ray {
  node_id: string;
  lat: number;
  lon: number;
  bearing_deg: number;
  bearing_uncertainty_deg: number | null;
}

export interface ThreatFactors {
  signature_confidence: number;
  corroboration_bonus: number;
  uncooperative_bonus: number;
  geofence_proximity: number;
  approach_vector: number;
  [k: string]: number;
}

export interface NearestGeofence {
  name: string | null;
  distance_m: number;
}

export interface ThreatBreakdown {
  score: number;
  factors: ThreatFactors;
  nearest_geofence: NearestGeofence | null;
}

export interface FriendOrFoe {
  cooperative: boolean;
  matched_serial: string | null;
  has_physical: boolean;
  has_remote_id: boolean;
  uncooperative: boolean;
}

export interface Track {
  track_id: string;
  first_seen: string;
  last_seen: string;
  localization: Localization;
  lat: number | null;
  lon: number | null;
  uncertainty_m: number | null;
  heading_deg: number | null;
  signature_class: string;
  confidence: number;
  cooperative: boolean;
  bench_test?: boolean; // provenance: bench-injected test signal, NOT a live field detection
  threat_score: number;
  threat_breakdown: ThreatBreakdown;
  node_ids: string[];
  sensor_types: string[];
  relay_path: string[];
  state: string;
  rays: Ray[];
  localization_note: string | null;
  friend_or_foe: FriendOrFoe;
}

export interface AlertEvidence {
  nodes: string[];
  sensors: string[];
  localization: Localization;
  cooperative: boolean;
  uncooperative: boolean;
  relay_path: string[];
  threat: ThreatBreakdown;
  note: string | null;
}

export interface Alert {
  alert_id: string;
  track_id: string;
  state: AlertState;
  threat_score: number;
  evidence: AlertEvidence;
}

export interface Geofence {
  id: string;
  name: string;
  kind: string;
  polygon: [number, number][]; // [[lat, lon], ...]
}

export interface Snapshot {
  nodes: MeshNode[];
  tracks: Track[];
  alerts: Alert[];
  geofences: Geofence[];
}

// WebSocket envelope: {type, data}
export type WsMessage =
  | { type: "snapshot"; data: Snapshot }
  | { type: "tracks"; data: Track[] }
  | { type: "alerts"; data: Alert[] }
  | { type: "nodes"; data: MeshNode[] }
  | { type: "mesh"; data: unknown };

export type ConnStatus = "LIVE" | "RECONNECTING" | "OFFLINE";
