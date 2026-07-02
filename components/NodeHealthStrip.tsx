"use client";

import type { MeshNode } from "../lib/types";
import { COLOR } from "../lib/theme";
import { ago } from "../lib/format";
import { SectionHeader } from "./AlertFeed";

interface Props {
  nodes: MeshNode[];
  onSelectNode: (id: string) => void;
}

// Coerce loosely-typed health values into a display count.
function count(v: unknown): number | null {
  if (typeof v === "number") return v;
  if (Array.isArray(v)) return v.length;
  return null;
}

function lock(v: unknown): "OK" | "n/a" | "NO" {
  if (v === true) return "OK";
  if (v === false) return "NO";
  return "n/a";
}

export default function NodeHealthStrip(props: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <SectionHeader
        title="Node health"
        right={`${props.nodes.filter((n) => n.online).length}/${props.nodes.length} online`}
      />
      {props.nodes.length === 0 && (
        <div className="dim" style={{ padding: "10px 12px", fontSize: 11 }}>
          No nodes registered.
        </div>
      )}
      {props.nodes.map((n) => {
        const h = n.health || {};
        const activeSensors =
          count(h.sensors_active) ?? n.sensors?.length ?? 0;
        const neighbors = count(h.neighbors_seen);
        return (
          <button
            key={n.node_id}
            onClick={() => props.onSelectNode(n.node_id)}
            className="hairline"
            style={{
              border: "none",
              borderBottom: `1px solid ${COLOR.hairline}`,
              textAlign: "left",
              textTransform: "none",
              letterSpacing: 0,
              padding: "8px 12px",
              display: "block",
              width: "100%",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  background: n.online ? COLOR.online : COLOR.stale,
                  display: "inline-block",
                }}
              />
              <span style={{ color: COLOR.text }}>{n.node_id}</span>
              <span className="dim" style={{ marginLeft: "auto", fontSize: 10 }}>
                {ago(n.last_seen)} ago
              </span>
            </div>
            <div
              className="dim"
              style={{ marginTop: 4, fontSize: 10, display: "flex", gap: 12, flexWrap: "wrap" }}
            >
              <span>
                sensors <span style={{ color: COLOR.text }}>{activeSensors}</span>/
                {n.sensors?.length ?? 0}
              </span>
              <span>
                gnss <Lock v={lock(h.gnss_lock)} />
              </span>
              <span>
                pps <Lock v={lock(h.pps_lock)} />
              </span>
              <span>
                neigh <span style={{ color: COLOR.text }}>{neighbors ?? "n/a"}</span>
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function Lock({ v }: { v: "OK" | "n/a" | "NO" }) {
  const color = v === "OK" ? COLOR.online : v === "NO" ? COLOR.stale : COLOR.textDim;
  return <span style={{ color }}>{v}</span>;
}
