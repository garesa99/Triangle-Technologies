"use client";

import { useState } from "react";
import type { ConnStatus } from "../lib/types";
import { COLOR } from "../lib/theme";
import { usingRealTiles } from "../lib/mapStyle";

interface Props {
  status: ConnStatus;
  brainUrl: string;
  token: string;
  nodeCount: number;
  trackCount: number;
  onSave: (brainUrl: string, token: string) => void;
  showCoverage: boolean;
  onToggleCoverage: () => void;
  drawing: boolean;
  onToggleDraw: () => void;
}

const STATUS_COLOR: Record<ConnStatus, string> = {
  LIVE: COLOR.online,
  RECONNECTING: COLOR.bearing,
  OFFLINE: COLOR.stale,
};

export default function TopBar(props: Props) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState(props.brainUrl);
  const [tok, setTok] = useState(props.token);

  return (
    <div
      className="hairline"
      style={{
        height: 40,
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "0 12px",
        background: COLOR.panel,
        flex: "0 0 auto",
      }}
    >
      <div style={{ letterSpacing: "0.16em", fontWeight: 600 }}>
        TRIANGLE MESH
        <span className="dim" style={{ marginLeft: 8, letterSpacing: "0.1em" }}>
          OPERATOR PICTURE
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span
          style={{
            width: 8,
            height: 8,
            background: STATUS_COLOR[props.status],
            display: "inline-block",
            animation:
              props.status === "RECONNECTING"
                ? "triangle-pulse 1.4s infinite"
                : undefined,
          }}
        />
        <span style={{ color: STATUS_COLOR[props.status], letterSpacing: "0.08em" }}>
          {props.status}
        </span>
      </div>

      <div className="dim" style={{ fontSize: 11 }}>
        {props.nodeCount} NODES · {props.trackCount} TRACKS ·{" "}
        {usingRealTiles() ? "TILES" : "OFFLINE MAP"}
      </div>

      <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
        <button
          className={props.showCoverage ? "accent" : ""}
          onClick={props.onToggleCoverage}
        >
          Coverage
        </button>
        <button
          className={props.drawing ? "accent" : ""}
          onClick={props.onToggleDraw}
        >
          {props.drawing ? "Drawing…" : "Draw zone"}
        </button>
        <button onClick={() => setOpen((v) => !v)}>Settings</button>
      </div>

      {open && (
        <div
          style={{
            position: "absolute",
            top: 44,
            right: 12,
            background: COLOR.panel,
            border: `1px solid ${COLOR.hairline}`,
            padding: 12,
            width: 320,
            zIndex: 20,
          }}
        >
          <div className="dim" style={{ marginBottom: 8, letterSpacing: "0.1em" }}>
            CONNECTION
          </div>
          <label style={{ display: "block", marginBottom: 8 }}>
            <div className="dim" style={{ marginBottom: 3 }}>
              Brain URL
            </div>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              style={{ width: "100%" }}
              placeholder="http://localhost:8000"
            />
          </label>
          <label style={{ display: "block", marginBottom: 12 }}>
            <div className="dim" style={{ marginBottom: 3 }}>
              Bearer token
            </div>
            <input
              value={tok}
              onChange={(e) => setTok(e.target.value)}
              style={{ width: "100%" }}
              placeholder="triangle-dev-token"
            />
          </label>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button
              onClick={() => {
                setUrl(props.brainUrl);
                setTok(props.token);
                setOpen(false);
              }}
            >
              Cancel
            </button>
            <button
              className="accent"
              onClick={() => {
                props.onSave(url.trim(), tok.trim());
                setOpen(false);
              }}
            >
              Apply
            </button>
          </div>
          <div className="dim" style={{ marginTop: 10, fontSize: 10, lineHeight: 1.5 }}>
            Persisted to localStorage. Reconnects the websocket on apply.
          </div>
        </div>
      )}
    </div>
  );
}
