// Small geodesy helpers for drawing rays and circles on the map (approximate,
// local-tangent flat-earth is fine at operator scales).

const R = 6371000; // earth radius m
const DEG = Math.PI / 180;

// Destination lon/lat given start lat/lon, true-north bearing (deg), distance (m).
// Returns [lon, lat] (GeoJSON order).
export function destination(
  lat: number,
  lon: number,
  bearingDeg: number,
  distanceM: number,
): [number, number] {
  const br = bearingDeg * DEG;
  const lat1 = lat * DEG;
  const lon1 = lon * DEG;
  const dr = distanceM / R;
  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(dr) +
      Math.cos(lat1) * Math.sin(dr) * Math.cos(br),
  );
  const lon2 =
    lon1 +
    Math.atan2(
      Math.sin(br) * Math.sin(dr) * Math.cos(lat1),
      Math.cos(dr) - Math.sin(lat1) * Math.sin(lat2),
    );
  return [lon2 / DEG, lat2 / DEG];
}

// A closed polygon ring approximating a circle. Returns [lon,lat][] with the
// first point repeated at the end (GeoJSON linear ring requirement).
export function circleRing(
  lat: number,
  lon: number,
  radiusM: number,
  steps = 48,
): [number, number][] {
  const ring: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const brg = (i / steps) * 360;
    ring.push(destination(lat, lon, brg, radiusM));
  }
  return ring;
}
