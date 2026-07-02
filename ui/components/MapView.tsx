"use client";

import { useEffect, useRef } from "react";
import maplibregl, {
  type GeoJSONSource,
  type Map as MLMap,
  type MapMouseEvent,
} from "maplibre-gl";
import type {
  FeatureCollection,
  Feature,
  LineString,
  Polygon,
  Point,
} from "geojson";
import type { Geofence, MeshNode, Track } from "../lib/types";
import { baseStyle } from "../lib/mapStyle";
import { COLOR } from "../lib/theme";
import { circleRing, destination } from "../lib/geo";
import { coverageRadius, sensorGlyph } from "../lib/sensors";

interface Props {
  nodes: MeshNode[];
  tracks: Track[];
  geofences: Geofence[];
  alertStateByTrack: Record<string, string>; // track_id -> alert state (for pulse)
  showCoverage: boolean;
  drawing: boolean;
  draftPolygon: [number, number][]; // [lat, lon][]
  onMapClick: (lat: number, lon: number) => void;
  onSelectNode: (id: string) => void;
  onSelectTrack: (id: string) => void;
  onSelectGeofence: (id: string) => void;
}

const EMPTY_FC: FeatureCollection = { type: "FeatureCollection", features: [] };

// Ray draw length (m) — bearings are directional, not ranged.
const RAY_LEN_M = 1500;

export default function MapView(props: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MLMap | null>(null);
  const readyRef = useRef(false);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const fittedRef = useRef(false);

  // Keep latest callbacks/props for handlers registered once.
  const propsRef = useRef(props);
  propsRef.current = props;

  // ---- init map once ----
  useEffect(() => {
    if (mapRef.current || !containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: baseStyle(),
      center: [4.9, 52.37], // matches contract example node position
      zoom: 13,
      attributionControl: false,
      dragRotate: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    mapRef.current = map;

    map.on("load", () => {
      addLayers(map);
      readyRef.current = true;
      syncAll(map, propsRef.current);
    });

    map.on("click", (e: MapMouseEvent) => {
      const p = propsRef.current;
      if (p.drawing) {
        p.onMapClick(e.lngLat.lat, e.lngLat.lng);
      }
    });

    // Feature click routing (only when not drawing).
    const pick = (layer: string, cb: (id: string) => void) => {
      map.on("click", layer, (e) => {
        if (propsRef.current.drawing) return;
        const f = e.features?.[0];
        const id = f?.properties?.id as string | undefined;
        if (id) cb(id);
      });
      map.on("mouseenter", layer, () => {
        if (!propsRef.current.drawing) map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", layer, () => {
        map.getCanvas().style.cursor = "";
      });
    };
    pick("track-fix", (id) => propsRef.current.onSelectTrack(id));
    pick("track-ellipse-fill", (id) => propsRef.current.onSelectTrack(id));
    pick("ray-line", (id) => propsRef.current.onSelectTrack(id));
    pick("geofence-fill", (id) => propsRef.current.onSelectGeofence(id));

    return () => {
      map.remove();
      mapRef.current = null;
      readyRef.current = false;
    };
  }, []);

  // ---- re-sync when data changes ----
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    syncAll(map, props);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    props.nodes,
    props.tracks,
    props.geofences,
    props.showCoverage,
    props.drawing,
    props.draftPolygon,
    props.alertStateByTrack,
  ]);

  // Fit to nodes the first time we have any.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current || fittedRef.current) return;
    const pts = props.nodes
      .filter((n) => n.position?.lat != null && n.position?.lon != null)
      .map((n) => [n.position.lon, n.position.lat] as [number, number]);
    if (pts.length === 0) return;
    const b = new maplibregl.LngLatBounds(pts[0], pts[0]);
    pts.forEach((p) => b.extend(p));
    map.fitBounds(b, { padding: 120, maxZoom: 15, duration: 0 });
    fittedRef.current = true;
  }, [props.nodes]);

  function syncAll(map: MLMap, p: Props) {
    setData(map, "coverage-src", coverageFC(p.nodes, p.showCoverage));
    setData(map, "mesh-src", meshFC(p.nodes, p.tracks));
    setData(map, "geofence-src", geofenceFC(p.geofences));
    setData(map, "draft-src", draftFC(p.draftPolygon, p.drawing));
    setData(map, "ray-src", rayFC(p.tracks));
    setData(map, "ellipse-src", ellipseFC(p.tracks));
    setData(map, "heading-src", headingFC(p.tracks));
    syncMarkers(map, p);
  }

  function syncMarkers(map: MLMap, p: Props) {
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    // Node markers with sensor loadout + health color.
    for (const n of p.nodes) {
      if (n.position?.lat == null || n.position?.lon == null) continue;
      const el = document.createElement("div");
      el.className = "node-marker";
      const dot = document.createElement("div");
      dot.className = "node-dot" + (n.online ? " online" : "");
      el.appendChild(dot);
      const label = document.createElement("div");
      label.className = "node-label";
      label.textContent = n.node_id;
      el.appendChild(label);
      if (n.sensors?.length) {
        const s = document.createElement("div");
        s.className = "node-sensors";
        s.textContent = n.sensors.map((x) => sensorGlyph(x.sensor_type)).join(" ");
        el.appendChild(s);
      }
      el.onclick = (ev) => {
        ev.stopPropagation();
        if (!propsRef.current.drawing) propsRef.current.onSelectNode(n.node_id);
      };
      const mk = new maplibregl.Marker({ element: el })
        .setLngLat([n.position.lon, n.position.lat])
        .addTo(map);
      markersRef.current.push(mk);
    }

    // Track fix markers (PRECISE + COARSE that have a point). Orange = active.
    for (const t of p.tracks) {
      if (t.lat == null || t.lon == null) continue;
      const el = document.createElement("div");
      const alertState = p.alertStateByTrack[t.track_id];
      const isNew = alertState === "new";
      el.className =
        "track-marker active" + (isNew ? " new" : "");
      const dot = document.createElement("div");
      dot.className = "track-dot";
      el.appendChild(dot);
      el.onclick = (ev) => {
        ev.stopPropagation();
        if (!propsRef.current.drawing) propsRef.current.onSelectTrack(t.track_id);
      };
      const mk = new maplibregl.Marker({ element: el })
        .setLngLat([t.lon, t.lat])
        .addTo(map);
      markersRef.current.push(mk);
    }
  }

  return <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />;
}

// --------------------------------------------------------------------------- layers

function addLayers(map: MLMap) {
  const src = (id: string) =>
    map.addSource(id, { type: "geojson", data: EMPTY_FC });

  src("coverage-src");
  src("mesh-src");
  src("geofence-src");
  src("draft-src");
  src("ray-src");
  src("ellipse-src");
  src("heading-src");

  // Coverage (bottom).
  map.addLayer({
    id: "coverage-fill",
    type: "fill",
    source: "coverage-src",
    paint: { "fill-color": COLOR.coverage, "fill-opacity": 0.06 },
  });
  map.addLayer({
    id: "coverage-outline",
    type: "line",
    source: "coverage-src",
    paint: {
      "line-color": COLOR.coverage,
      "line-opacity": 0.35,
      "line-width": 1,
      "line-dasharray": [2, 3],
    },
  });

  // Mesh links.
  map.addLayer({
    id: "mesh-line",
    type: "line",
    source: "mesh-src",
    paint: {
      "line-color": [
        "case",
        ["get", "relay"],
        COLOR.relay,
        COLOR.mesh,
      ],
      "line-width": ["case", ["get", "relay"], 2, 1],
      "line-opacity": ["case", ["get", "relay"], 0.9, 0.5],
    },
  });

  // Geofences.
  map.addLayer({
    id: "geofence-fill",
    type: "fill",
    source: "geofence-src",
    paint: { "fill-color": COLOR.geofence, "fill-opacity": 0.08 },
  });
  map.addLayer({
    id: "geofence-outline",
    type: "line",
    source: "geofence-src",
    paint: { "line-color": COLOR.geofence, "line-width": 1.5 },
  });

  // Draft polygon (while drawing).
  map.addLayer({
    id: "draft-fill",
    type: "fill",
    source: "draft-src",
    paint: { "fill-color": COLOR.accent, "fill-opacity": 0.08 },
  });
  map.addLayer({
    id: "draft-line",
    type: "line",
    source: "draft-src",
    paint: {
      "line-color": COLOR.accent,
      "line-width": 1.5,
      "line-dasharray": [2, 2],
    },
  });
  map.addLayer({
    id: "draft-vertices",
    type: "circle",
    source: "draft-src",
    filter: ["==", ["geometry-type"], "Point"],
    paint: {
      "circle-radius": 3,
      "circle-color": COLOR.accent,
      "circle-stroke-color": COLOR.ground,
      "circle-stroke-width": 1,
    },
  });

  // Uncertainty ellipses (COARSE + PRECISE small ellipse).
  map.addLayer({
    id: "track-ellipse-fill",
    type: "fill",
    source: "ellipse-src",
    paint: {
      "fill-color": [
        "match",
        ["get", "tier"],
        "PRECISE_FIX",
        COLOR.precise,
        COLOR.coarse,
      ],
      "fill-opacity": 0.1,
    },
  });
  map.addLayer({
    id: "track-ellipse-line",
    type: "line",
    source: "ellipse-src",
    paint: {
      "line-color": [
        "match",
        ["get", "tier"],
        "PRECISE_FIX",
        COLOR.precise,
        COLOR.coarse,
      ],
      // B&W tier distinction: PRECISE is a solid bright ring, COARSE is a dashed dimmer ring.
      "line-dasharray": [
        "match",
        ["get", "tier"],
        "PRECISE_FIX",
        ["literal", [1, 0]],
        ["literal", [3, 3]],
      ],
      "line-width": ["match", ["get", "tier"], "PRECISE_FIX", 1.4, 1],
      "line-opacity": 0.8,
    },
  });

  // Bearing rays (BEARING_ONLY and any track with rays).
  map.addLayer({
    id: "ray-line",
    type: "line",
    source: "ray-src",
    paint: {
      "line-color": COLOR.bearing,
      "line-width": 1.5,
      "line-opacity": 0.85,
    },
  });
  // Bearing uncertainty wedge edges (dashed).
  map.addLayer({
    id: "ray-uncert",
    type: "line",
    source: "ray-src",
    filter: ["==", ["get", "kind"], "uncert"],
    paint: {
      "line-color": COLOR.bearing,
      "line-width": 0.75,
      "line-opacity": 0.4,
      "line-dasharray": [2, 2],
    },
  });

  // Heading arrow.
  map.addLayer({
    id: "heading-line",
    type: "line",
    source: "heading-src",
    paint: { "line-color": COLOR.accent, "line-width": 2 },
  });

  // Invisible fat hit target for precise fixes handled via HTML markers instead;
  // but add a small circle so COARSE centroids without markers still clickable.
  map.addLayer({
    id: "track-fix",
    type: "circle",
    source: "ellipse-src",
    filter: ["==", ["geometry-type"], "Point"],
    paint: {
      "circle-radius": 4,
      "circle-color": COLOR.accent,
      "circle-opacity": 0,
    },
  });
}

function setData(map: MLMap, id: string, fc: FeatureCollection) {
  const s = map.getSource(id) as GeoJSONSource | undefined;
  if (s) s.setData(fc);
}

// --------------------------------------------------------------------------- FC builders

function coverageFC(nodes: MeshNode[], show: boolean): FeatureCollection {
  if (!show) return EMPTY_FC;
  const features: Feature[] = [];
  for (const n of nodes) {
    if (n.position?.lat == null || n.position?.lon == null) continue;
    // One ring per distinct sensor radius (largest wins visually but draw each).
    const radii = new Set<number>();
    for (const s of n.sensors || []) radii.add(coverageRadius(s.sensor_type));
    if (radii.size === 0) radii.add(coverageRadius(""));
    for (const r of radii) {
      const poly: Polygon = {
        type: "Polygon",
        coordinates: [circleRing(n.position.lat, n.position.lon, r)],
      };
      features.push({
        type: "Feature",
        properties: { node_id: n.node_id, radius_m: r },
        geometry: poly,
      });
    }
  }
  return { type: "FeatureCollection", features };
}

function meshFC(nodes: MeshNode[], tracks: Track[]): FeatureCollection {
  const online = nodes.filter(
    (n) => n.online && n.position?.lat != null && n.position?.lon != null,
  );
  const pos: Record<string, [number, number]> = {};
  for (const n of nodes) {
    if (n.position?.lat != null && n.position?.lon != null) {
      pos[n.node_id] = [n.position.lon, n.position.lat];
    }
  }

  // Highlighted relay edges from any track's relay_path (consecutive hops).
  const relayEdges = new Set<string>();
  for (const t of tracks) {
    const path = t.relay_path || [];
    for (let i = 0; i < path.length - 1; i++) {
      relayEdges.add(edgeKey(path[i], path[i + 1]));
    }
    // Also connect relay hops to the detecting nodes so the chain is visible.
    if (path.length && t.node_ids?.length) {
      relayEdges.add(edgeKey(path[path.length - 1], t.node_ids[0]));
    }
  }

  const features: Feature[] = [];

  // Dim connectivity between online nodes (approximate full-mesh, capped by distance
  // implicitly via visual dimness — we draw all pairs to show reachability intent).
  for (let i = 0; i < online.length; i++) {
    for (let j = i + 1; j < online.length; j++) {
      const a = online[i];
      const b = online[j];
      const key = edgeKey(a.node_id, b.node_id);
      const line: LineString = {
        type: "LineString",
        coordinates: [pos[a.node_id], pos[b.node_id]],
      };
      features.push({
        type: "Feature",
        properties: { relay: relayEdges.has(key) },
        geometry: line,
      });
    }
  }

  // Relay edges that involve nodes not in the online-pair set (e.g. explicit path).
  for (const key of relayEdges) {
    const [a, b] = key.split(" ");
    if (pos[a] && pos[b]) {
      const line: LineString = {
        type: "LineString",
        coordinates: [pos[a], pos[b]],
      };
      features.push({
        type: "Feature",
        properties: { relay: true },
        geometry: line,
      });
    }
  }

  return { type: "FeatureCollection", features };
}

function edgeKey(a: string, b: string): string {
  return a < b ? `${a} ${b}` : `${b} ${a}`;
}

function geofenceFC(geofences: Geofence[]): FeatureCollection {
  const features: Feature[] = [];
  for (const g of geofences) {
    if (!g.polygon?.length) continue;
    // polygon is [[lat,lon],...] -> GeoJSON needs [lon,lat] and a closed ring.
    const ring = g.polygon.map(([lat, lon]) => [lon, lat] as [number, number]);
    if (
      ring.length &&
      (ring[0][0] !== ring[ring.length - 1][0] ||
        ring[0][1] !== ring[ring.length - 1][1])
    ) {
      ring.push(ring[0]);
    }
    const poly: Polygon = { type: "Polygon", coordinates: [ring] };
    features.push({
      type: "Feature",
      properties: { id: g.id, name: g.name, kind: g.kind },
      geometry: poly,
    });
  }
  return { type: "FeatureCollection", features };
}

function draftFC(draft: [number, number][], drawing: boolean): FeatureCollection {
  if (!drawing || draft.length === 0) return EMPTY_FC;
  const coords = draft.map(([lat, lon]) => [lon, lat] as [number, number]);
  const features: Feature[] = [];
  // Vertices.
  for (const c of coords) {
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "Point", coordinates: c } as Point,
    });
  }
  if (coords.length >= 2) {
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates: coords } as LineString,
    });
  }
  if (coords.length >= 3) {
    const ring = [...coords, coords[0]];
    features.push({
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [ring] } as Polygon,
    });
  }
  return { type: "FeatureCollection", features };
}

function rayFC(tracks: Track[]): FeatureCollection {
  const features: Feature[] = [];
  for (const t of tracks) {
    for (const r of t.rays || []) {
      if (r.bearing_deg == null) continue;
      const end = destination(r.lat, r.lon, r.bearing_deg, RAY_LEN_M);
      features.push({
        type: "Feature",
        properties: { id: t.track_id, kind: "ray", node_id: r.node_id },
        geometry: {
          type: "LineString",
          coordinates: [[r.lon, r.lat], end],
        } as LineString,
      });
      // Uncertainty wedge edges.
      const u = r.bearing_uncertainty_deg;
      if (u != null && u > 0) {
        for (const off of [-u, u]) {
          const e2 = destination(r.lat, r.lon, r.bearing_deg + off, RAY_LEN_M);
          features.push({
            type: "Feature",
            properties: { id: t.track_id, kind: "uncert", node_id: r.node_id },
            geometry: {
              type: "LineString",
              coordinates: [[r.lon, r.lat], e2],
            } as LineString,
          });
        }
      }
    }
  }
  return { type: "FeatureCollection", features };
}

function ellipseFC(tracks: Track[]): FeatureCollection {
  const features: Feature[] = [];
  for (const t of tracks) {
    if (t.lat == null || t.lon == null) continue;
    const r = t.uncertainty_m && t.uncertainty_m > 0 ? t.uncertainty_m : 30;
    const poly: Polygon = {
      type: "Polygon",
      coordinates: [circleRing(t.lat, t.lon, r)],
    };
    features.push({
      type: "Feature",
      properties: { id: t.track_id, tier: t.localization },
      geometry: poly,
    });
    // Point for hit-testing COARSE centroids (PRECISE has an HTML marker too).
    features.push({
      type: "Feature",
      properties: { id: t.track_id, tier: t.localization },
      geometry: { type: "Point", coordinates: [t.lon, t.lat] } as Point,
    });
  }
  return { type: "FeatureCollection", features };
}

function headingFC(tracks: Track[]): FeatureCollection {
  const features: Feature[] = [];
  for (const t of tracks) {
    if (t.lat == null || t.lon == null || t.heading_deg == null) continue;
    const len = Math.max(120, (t.uncertainty_m || 60) * 1.5);
    const tip = destination(t.lat, t.lon, t.heading_deg, len);
    // Arrowhead barbs.
    const left = destination(tip[1], tip[0], t.heading_deg + 150, len * 0.25);
    const right = destination(tip[1], tip[0], t.heading_deg - 150, len * 0.25);
    features.push({
      type: "Feature",
      properties: { id: t.track_id },
      geometry: {
        type: "LineString",
        coordinates: [[t.lon, t.lat], tip],
      } as LineString,
    });
    features.push({
      type: "Feature",
      properties: { id: t.track_id },
      geometry: {
        type: "LineString",
        coordinates: [left, tip, right],
      } as LineString,
    });
  }
  return { type: "FeatureCollection", features };
}
