// Single source of truth for the dark operational palette.
// ONE signal-orange accent, reserved for ACTIVE / UNACKNOWLEDGED tracks + alerts.

export const COLOR = {
  ground: "#0A0A0B",
  panel: "#0E0E10",
  panelAlt: "#141417",
  hairline: "#26262B",
  text: "#D7D7DB",
  textDim: "#7C7C85",
  // THE accent — do not reuse for anything non-urgent.
  accent: "#FF6A00",
  // Node health.
  online: "#3FB950",
  stale: "#6E7681",
  // Localization tiers (kept distinct from the orange accent).
  bearing: "#E3B341", // ray
  coarse: "#58A6FF", // uncertainty ellipse
  precise: "#2DD4BF", // precise fix
  // Mesh links.
  mesh: "#2B2B33",
  relay: "#FF6A00",
  // Coverage.
  coverage: "#1F6FEB",
  // Geofence.
  geofence: "#C25A2E",
} as const;
