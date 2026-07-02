// Single source of truth for the operational palette.
// FULLY BLACK & WHITE: no hue anywhere. Threat/urgency is conveyed by BRIGHTNESS, PULSE, and
// WEIGHT; localization tiers are distinguished by SHAPE + LINE STYLE + brightness, never colour.

export const COLOR = {
  ground: "#0A0A0B",
  panel: "#0E0E10",
  panelAlt: "#141417",
  hairline: "#26262B",
  text: "#D7D7DB",
  textDim: "#7C7C85",
  // THE accent — pure white, reserved for ACTIVE / UNACKNOWLEDGED tracks + alerts.
  accent: "#FFFFFF",
  // Node health — brightness, not colour.
  online: "#E6E6EA",
  stale: "#4A4A52",
  // Localization tiers — greys by confidence (brighter = more precise). Shape + dash in MapView
  // carry the real distinction: ray (line) / coarse (dashed ellipse) / precise (solid + point).
  bearing: "#8A8A92", // ray
  coarse: "#B4B4BC", // uncertainty ellipse (dashed)
  precise: "#F4F4F5", // precise fix (solid, brightest)
  // Mesh links.
  mesh: "#2B2B33",
  relay: "#FFFFFF",
  // Coverage.
  coverage: "#3A3A42",
  // Geofence.
  geofence: "#7C7C85",
} as const;
