"use client";

import { COLOR } from "../lib/theme";

// Persistent localization-quality legend. Always visible.
export default function Legend() {
  return (
    <div
      style={{
        position: "absolute",
        left: 12,
        bottom: 44,
        background: "rgba(14,14,16,0.92)",
        border: `1px solid ${COLOR.hairline}`,
        padding: "8px 10px",
        pointerEvents: "none",
        maxWidth: 240,
        zIndex: 5,
      }}
    >
      <div
        style={{
          fontSize: 9,
          letterSpacing: "0.12em",
          color: COLOR.textDim,
          marginBottom: 6,
          textTransform: "uppercase",
        }}
      >
        Localization quality
      </div>
      <Row color={COLOR.bearing} label="BEARING_ONLY: ray from node">
        <svg width="26" height="10">
          <line x1="0" y1="5" x2="26" y2="5" stroke={COLOR.bearing} strokeWidth="1.5" />
        </svg>
      </Row>
      <Row color={COLOR.coarse} label="COARSE_FIX: uncertainty ellipse">
        <svg width="26" height="14">
          <ellipse
            cx="13"
            cy="7"
            rx="11"
            ry="5"
            fill="none"
            stroke={COLOR.coarse}
            strokeWidth="1"
          />
        </svg>
      </Row>
      <Row color={COLOR.precise} label="PRECISE_FIX: point and small ellipse">
        <svg width="26" height="14">
          <ellipse cx="13" cy="7" rx="7" ry="4" fill="none" stroke={COLOR.precise} strokeWidth="1" />
          <rect x="10" y="4" width="6" height="6" fill={COLOR.accent} transform="rotate(45 13 7)" />
        </svg>
      </Row>
      <div style={{ height: 1, background: COLOR.hairline, margin: "6px 0" }} />
      <Row color={COLOR.accent} label="Active / unacknowledged track">
        <span style={{ width: 26, textAlign: "center", color: COLOR.accent }}>◆</span>
      </Row>
      <Row color={COLOR.relay} label="Relay path (highlighted)">
        <svg width="26" height="10">
          <line x1="0" y1="5" x2="26" y2="5" stroke={COLOR.relay} strokeWidth="2" />
        </svg>
      </Row>
    </div>
  );
}

function Row({
  label,
  children,
}: {
  color: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
      <div style={{ width: 26, display: "flex", justifyContent: "center" }}>
        {children}
      </div>
      <div style={{ fontSize: 10, color: COLOR.text }}>{label}</div>
    </div>
  );
}
