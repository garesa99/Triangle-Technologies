// Per-sensor-type approximate detection radius (m) for the COVERAGE view, and a
// short glyph for node loadout labels. Sensor types are open strings in the
// contract, so we key by prefix/known values and fall back to a default.

export const COVERAGE_RADIUS_M: Record<string, number> = {
  acoustic: 300,
  rf24: 800,
  rf58: 800,
  rf: 800,
  remote_id: 1200,
  pir: 60,
  seismic: 150,
  magnetometer: 120,
};

export const DEFAULT_COVERAGE_RADIUS_M = 400;

export function coverageRadius(sensorType: string): number {
  if (sensorType in COVERAGE_RADIUS_M) return COVERAGE_RADIUS_M[sensorType];
  if (sensorType.startsWith("rf")) return COVERAGE_RADIUS_M.rf;
  return DEFAULT_COVERAGE_RADIUS_M;
}

const GLYPH: Record<string, string> = {
  acoustic: "AC",
  rf24: "24",
  rf58: "58",
  remote_id: "RID",
  pir: "PIR",
  seismic: "SEIS",
  magnetometer: "MAG",
};

export function sensorGlyph(sensorType: string): string {
  if (sensorType in GLYPH) return GLYPH[sensorType];
  if (sensorType.startsWith("rf")) return sensorType.slice(2).toUpperCase() || "RF";
  return sensorType.slice(0, 4).toUpperCase();
}
