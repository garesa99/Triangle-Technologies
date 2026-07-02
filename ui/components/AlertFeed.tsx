"use client";

import type { Alert } from "../lib/types";
import { COLOR } from "../lib/theme";
import { pct } from "../lib/format";

interface Props {
  alerts: Alert[];
  onAck: (id: string) => void;
  onClose: (id: string) => void;
  onSelectTrack: (id: string) => void;
  busy: Record<string, boolean>;
}

const STATE_LABEL: Record<string, string> = {
  new: "NEW",
  acknowledged: "ACK",
  closed: "CLOSED",
};

export default function AlertFeed(props: Props) {
  // Show open alerts first; hide closed at the bottom, dimmed.
  const sorted = [...props.alerts].sort((a, b) => {
    const rank = (s: string) => (s === "new" ? 0 : s === "acknowledged" ? 1 : 2);
    const r = rank(a.state) - rank(b.state);
    return r !== 0 ? r : b.threat_score - a.threat_score;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <SectionHeader
        title="Alert feed"
        right={`${props.alerts.filter((a) => a.state !== "closed").length} open`}
      />
      {sorted.length === 0 && (
        <div className="dim" style={{ padding: "10px 12px", fontSize: 11 }}>
          No alerts.
        </div>
      )}
      {sorted.map((a) => {
        const isNew = a.state === "new";
        const isClosed = a.state === "closed";
        const ev = a.evidence;
        return (
          <div
            key={a.alert_id}
            className={isNew ? "pulse hairline" : "hairline"}
            style={{
              padding: "8px 12px",
              background: isNew ? "rgba(255,255,255,0.05)" : "transparent",
              opacity: isClosed ? 0.5 : 1,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  color: isNew ? COLOR.accent : COLOR.textDim,
                  fontWeight: 600,
                  letterSpacing: "0.08em",
                }}
              >
                {STATE_LABEL[a.state] || a.state.toUpperCase()}
              </span>
              <button
                onClick={() => props.onSelectTrack(a.track_id)}
                style={{
                  border: "none",
                  padding: 0,
                  textTransform: "none",
                  letterSpacing: 0,
                  color: COLOR.text,
                  textDecoration: "underline dotted",
                }}
                title="Inspect track"
              >
                {a.track_id}
              </button>
              <span style={{ marginLeft: "auto" }} className="dim">
                threat {pct(a.threat_score)}
              </span>
            </div>

            {/* Evidence chain */}
            <div style={{ marginTop: 6, fontSize: 10, lineHeight: 1.6 }}>
              <EvRow k="nodes" v={ev.nodes?.join(", ") || "—"} />
              <EvRow k="sensors" v={ev.sensors?.join(", ") || "—"} />
              <EvRow
                k="localization"
                v={ev.localization + (ev.note ? ` · ${ev.note}` : "")}
              />
              <EvRow
                k="foe"
                v={
                  ev.uncooperative
                    ? "UNCOOPERATIVE (no matching Remote ID)"
                    : ev.cooperative
                      ? "cooperative"
                      : "unknown"
                }
                accent={ev.uncooperative}
              />
              {ev.relay_path?.length > 0 && (
                <EvRow k="relay" v={ev.relay_path.join(" → ")} />
              )}
              {ev.threat?.nearest_geofence && (
                <EvRow
                  k="near"
                  v={`${ev.threat.nearest_geofence.name ?? "zone"} @ ${Math.round(
                    ev.threat.nearest_geofence.distance_m,
                  )}m`}
                />
              )}
            </div>

            {/* Threat factors */}
            {ev.threat?.factors && (
              <div
                className="dim"
                style={{ marginTop: 4, fontSize: 9, letterSpacing: "0.02em" }}
              >
                {Object.entries(ev.threat.factors)
                  .map(([k, v]) => `${abbr(k)} ${v}`)
                  .join("  ")}
              </div>
            )}

            {!isClosed && (
              <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                {a.state === "new" && (
                  <button
                    className="accent"
                    disabled={props.busy[a.alert_id]}
                    onClick={() => props.onAck(a.alert_id)}
                  >
                    Acknowledge
                  </button>
                )}
                <button
                  disabled={props.busy[a.alert_id]}
                  onClick={() => props.onClose(a.alert_id)}
                >
                  Close
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function EvRow({
  k,
  v,
  accent,
}: {
  k: string;
  v: string;
  accent?: boolean;
}) {
  return (
    <div style={{ display: "flex", gap: 8 }}>
      <span className="dim" style={{ width: 74, flex: "0 0 auto" }}>
        {k}
      </span>
      <span style={{ color: accent ? COLOR.accent : COLOR.text }}>{v}</span>
    </div>
  );
}

function abbr(k: string): string {
  return k
    .split("_")
    .map((p) => p.slice(0, 3))
    .join("·");
}

export function SectionHeader({
  title,
  right,
}: {
  title: string;
  right?: string;
}) {
  return (
    <div
      className="hairline"
      style={{
        padding: "8px 12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: COLOR.panelAlt,
        position: "sticky",
        top: 0,
        zIndex: 2,
      }}
    >
      <span style={{ letterSpacing: "0.12em", textTransform: "uppercase", fontSize: 11 }}>
        {title}
      </span>
      {right && (
        <span className="dim" style={{ fontSize: 10 }}>
          {right}
        </span>
      )}
    </div>
  );
}
