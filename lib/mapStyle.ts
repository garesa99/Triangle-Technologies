import type { StyleSpecification } from "maplibre-gl";
import { TILE_URL } from "./config";

// Ground/base colors for the dark operational theme.
export const GROUND = "#0A0A0B";
export const GROUND_ALT = "#0E0E10";

// A fully OFFLINE style: a single background layer, no glyphs, no sprite, no
// tile sources. MapLibre renders this with zero network access. All data layers
// (nodes, tracks, geofences, mesh, coverage) are added at runtime by MapView.
const OFFLINE_STYLE: StyleSpecification = {
  version: 8,
  name: "triangle-offline-dark",
  // Empty glyphs/sprite intentionally omitted: we use only circle/line/fill
  // layers plus HTML markers, so no font/sprite fetch is ever required.
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": GROUND },
    },
  ],
};

// A raster style used only when a tile URL is provided at build time. Still
// self-hostable (the operator points it at a local tileserver).
function rasterStyle(tileUrl: string): StyleSpecification {
  return {
    version: 8,
    name: "triangle-raster-dark",
    sources: {
      basemap: {
        type: "raster",
        tiles: [tileUrl],
        tileSize: 256,
      },
    },
    layers: [
      {
        id: "background",
        type: "background",
        paint: { "background-color": GROUND },
      },
      {
        id: "basemap",
        type: "raster",
        source: "basemap",
        // Dim + desaturate real tiles so the white accent stays dominant.
        paint: { "raster-brightness-max": 0.55, "raster-saturation": -0.6 },
      },
    ],
  };
}

// Default MUST work offline. Only use raster when NEXT_PUBLIC_TILE_URL is set.
export function baseStyle(): StyleSpecification {
  if (TILE_URL) return rasterStyle(TILE_URL);
  return OFFLINE_STYLE;
}

export function usingRealTiles(): boolean {
  return !!TILE_URL;
}
