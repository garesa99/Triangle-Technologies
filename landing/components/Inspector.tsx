"use client";

import type { Geofence, MeshNode, Track } from "../lib/types";
import { COLOR } from "../lib/theme";
import { fmtTime, num, pct } from "../lib/format";

export type Selection =
  | { kind: "track"; id: string }
  | { kind: "node"; id: string }
  | { kind: "geofence"; id: string }
  | null;

interface Props {
  selection: Selection;
  tracks: Track[];
  nodes: MeshNode[];
  geofences: Geofence[];
  onClose: () => void;
  onDeleteGeofence: (id: string) => void;
}

export default function Inspector(props: Props) {
  const sel = props.selection;
  if (!sel) return null;

  let body: React.ReactNode = null;
  let title = "Inspector";

  if (sel.kind === "track") {
    const t = props.tracks.find((x) => x.track_id === sel.id);
    title = "Track";
    body = t ? <TrackBody t={t} /> : <Gone label="track" />;
  } else if (sel.kind === "node") {
    const n = props.nodes.find((x) => x.node_id === sel.id);
    title = "Node";
    body = n ? <NodeBody n={n} /> : <Gone label="node" />;
  } else if (sel.kind === "geofence") {
    const g = props.geofences.find((x) => x.id === sel.id);
    title = "Geofence";
    body = g ? (
      <GeofenceBody g={g} onDelete={() => props.onDeleteGeofence(g.id)} />
    ) : (
      <Gone label="geofence" />
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <div
        className="hairline"
        style={{
          padding: "8px 12px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: COLOR.panelAlt,
        }}
      >
        <span style={{ letterSpacing: "0.12em", textTransform: "uppercase", fontSize: 11 }}>
          {title} · inspector
        </span>
        <button
          onClick={props.onClose}
          style={{ border: "none", padding: 0, letterSpacing: 0 }}
        >
          ✕
        </button>
      </div>
      <div style={{ padding: "8px 12px" }}>{body}</div>
    </div>
  );
}

function Gone({ label }: { label: string }) {
  return <div className="dim">This {label} is no longer active.</div>;
}

function Field({
  k,
  v,
  accent,
}: {
  k: string;
  v: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 3, fontSize: 11 }}>
      <span className="dim" style={{ width: 92, flex: "0 0 auto" }}>
        {k}
      </span>
      <span style={{ color: accent ? COLOR.accent : COLOR.text, wordBreak: "break-word" }}>
        {v}
      </span>
    </div>
  );
}

function TIER_COLOR(t: string): string {
  return t === "PRECISE_FIX"
    ? COLOR.precise
    : t === "COARSE_FIX"
      ? COLOR.coarse
      : COLOR.bearing;
}

function TrackBody({ t }: { t: Track }) {
  const foe = t.friend_or_foe;
  const tb = t.threat_breakdown;
  return (
    <div>
      <Field k="track_id" v={t.track_id} />
      <Field
        k="localization"
        v={<span style={{ color: TIER_COLOR(t.localization) }}>{t.localization}</span>}
      />
      {t.localization_note && <Field k="note" v={t.localization_note} />}
      <Field k="signature" v={t.signature_class} />
      <Field k="confidence" v={pct(t.confidence)} />
      <Field k="threat" v={pct(t.threat_score)} accent={t.threat_score >= 0.6} />
      <Field
        k="friend/foe"
        v={
          foe.uncooperative
            ? "UNCOOPERATIVE"
            : foe.cooperative
              ? `cooperative${foe.matched_serial ? ` (${foe.matched_serial})` : ""}`
              : "unknown"
        }
        accent={foe.uncooperative}
      />
      <Field k="position" v={t.lat != null ? `${num(t.lat, 5)}, ${num(t.lon, 5)}` : "no fix (ray only)"} />
      <Field k="uncertainty" v={t.uncertainty_m != null ? `${num(t.uncertainty_m, 0)} m` : "n/a"} />
      <Field k="heading" v={t.heading_deg != null ? `${num(t.heading_deg, 0)}°` : "n/a"} />
      <Field k="nodes" v={t.node_ids.join(", ") || "n/a"} />
      <Field k="sensors" v={t.sensor_types.join(", ") || "n/a"} />
      <Field k="relay path" v={t.relay_path.length ? t.relay_path.join(" → ") : "n/a"} />
      <Field k="first seen" v={fmtTime(t.first_seen)} />
      <Field k="last seen" v={fmtTime(t.last_seen)} />

      <div style={{ height: 1, background: COLOR.hairline, margin: "8px 0" }} />
      <div className="dim" style={{ marginBottom: 4, letterSpacing: "0.1em" }}>
        THREAT BREAKDOWN
      </div>
      {tb?.factors &&
        Object.entries(tb.factors).map(([k, v]) => (
          <div key={k} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
            <span className="dim" style={{ width: 150, fontSize: 10 }}>
              {k}
            </span>
            <div style={{ flex: 1, height: 4, background: COLOR.panelAlt }}>
              <div
                style={{
                  width: `${Math.min(100, (v / 1.6) * 100)}%`,
                  height: "100%",
                  background: COLOR.accent,
                  opacity: 0.7,
                }}
              />
            </div>
            <span style={{ width: 38, textAlign: "right", fontSize: 10 }}>{v}</span>
          </div>
        ))}
      {tb?.nearest_geofence && (
        <Field
          k="nearest zone"
          v={`${tb.nearest_geofence.name ?? "zone"} @ ${Math.round(
            tb.nearest_geofence.distance_m,
          )} m`}
        />
      )}
    </div>
  );
}

function NodeBody({ n }: { n: MeshNode }) {
  const h = n.health || {};
  return (
    <div>
      <Field k="node_id" v={n.node_id} />
      <Field k="agent" v={n.agent_version} />
      <Field
        k="status"
        v={<span style={{ color: n.online ? COLOR.online : COLOR.stale }}>{n.online ? "ONLINE" : "STALE"}</span>}
      />
      <Field k="last seen" v={fmtTime(n.last_seen)} />
      <Field
        k="position"
        v={`${num(n.position.lat, 5)}, ${num(n.position.lon, 5)}${
          n.position.alt_m != null ? ` · ${num(n.position.alt_m, 0)}m` : ""
        }`}
      />
      <div style={{ height: 1, background: COLOR.hairline, margin: "8px 0" }} />
      <div className="dim" style={{ marginBottom: 4, letterSpacing: "0.1em" }}>
        LOADOUT
      </div>
      {n.sensors?.length ? (
        n.sensors.map((s, i) => (
          <div key={i} style={{ marginBottom: 4, fontSize: 11 }}>
            <span style={{ color: COLOR.text }}>{s.sensor_type}</span>
            <span className="dim">
              {s.provides_bearing ? " · bearing" : " · no bearing"}
              {s.signature_classes?.length ? ` · ${s.signature_classes.join(", ")}` : ""}
            </span>
          </div>
        ))
      ) : (
        <div className="dim">No sensors registered.</div>
      )}
      {Object.keys(h).length > 0 && (
        <>
          <div style={{ height: 1, background: COLOR.hairline, margin: "8px 0" }} />
          <div className="dim" style={{ marginBottom: 4, letterSpacing: "0.1em" }}>
            HEALTH
          </div>
          <pre style={{ margin: 0, fontSize: 10, color: COLOR.textDim, whiteSpace: "pre-wrap" }}>
            {JSON.stringify(h, null, 2)}
          </pre>
        </>
      )}
    </div>
  );
}

function GeofenceBody({ g, onDelete }: { g: Geofence; onDelete: () => void }) {
  return (
    <div>
      <Field k="id" v={g.id} />
      <Field k="name" v={g.name} />
      <Field k="kind" v={g.kind} />
      <Field k="vertices" v={String(g.polygon?.length ?? 0)} />
      <div style={{ marginTop: 8 }}>
        <button className="accent" onClick={onDelete}>
          Delete zone
        </button>
      </div>
    </div>
  );
}
