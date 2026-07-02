"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMeshState } from "../lib/useMeshState";
import { loadConfig, saveConfig } from "../lib/config";
import { api } from "../lib/api";
import { COLOR } from "../lib/theme";
import MapView from "./MapView";
import Legend from "./Legend";
import TopBar from "./TopBar";
import AlertFeed from "./AlertFeed";
import Inspector, { type Selection } from "./Inspector";
import NodeHealthStrip from "./NodeHealthStrip";

export default function Console() {
  // Config (env defaults, overridable + persisted).
  const [cfg, setCfg] = useState(() => loadConfig());
  const { brainUrl, token } = cfg;

  const { nodes, tracks, alerts, geofences, status, refreshGeofences } =
    useMeshState(brainUrl, token);

  const [selection, setSelection] = useState<Selection>(null);
  const [showCoverage, setShowCoverage] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<[number, number][]>([]);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [banner, setBanner] = useState<string | null>(null);

  // Alert state per track (drives the orange pulse on the map).
  const alertStateByTrack = useMemo(() => {
    const m: Record<string, string> = {};
    for (const a of alerts) {
      // Prefer the most urgent state if multiple alerts share a track.
      const rank = (s: string) => (s === "new" ? 0 : s === "acknowledged" ? 1 : 2);
      if (!(a.track_id in m) || rank(a.state) < rank(m[a.track_id])) {
        m[a.track_id] = a.state;
      }
    }
    return m;
  }, [alerts]);

  const flash = useCallback((msg: string) => {
    setBanner(msg);
    setTimeout(() => setBanner(null), 3500);
  }, []);

  // --- alert actions ---
  const withBusy = useCallback(
    async (id: string, fn: () => Promise<unknown>) => {
      setBusy((b) => ({ ...b, [id]: true }));
      try {
        await fn();
      } catch (e) {
        flash(`Action failed: ${(e as Error).message}`);
      } finally {
        setBusy((b) => ({ ...b, [id]: false }));
      }
    },
    [flash],
  );

  const onAck = useCallback(
    (id: string) => withBusy(id, () => api.ackAlert(brainUrl, token, id)),
    [brainUrl, token, withBusy],
  );
  const onCloseAlert = useCallback(
    (id: string) => withBusy(id, () => api.closeAlert(brainUrl, token, id)),
    [brainUrl, token, withBusy],
  );

  // --- geofence drawing ---
  const onMapClick = useCallback(
    (lat: number, lon: number) => {
      if (drawing) setDraft((d) => [...d, [lat, lon]]);
    },
    [drawing],
  );

  const toggleDraw = useCallback(() => {
    setDrawing((d) => {
      if (d) setDraft([]); // cancel discards
      return !d;
    });
  }, []);

  const finishDraw = useCallback(async () => {
    if (draft.length < 3) {
      flash("A zone needs at least 3 vertices.");
      return;
    }
    const name = window.prompt("Zone name", "protected zone") || "zone";
    try {
      await api.createGeofence(brainUrl, token, {
        name,
        kind: "protected",
        polygon: draft,
      });
      await refreshGeofences();
      flash("Zone saved.");
    } catch (e) {
      flash(`Save failed: ${(e as Error).message}`);
    } finally {
      setDrawing(false);
      setDraft([]);
    }
  }, [draft, brainUrl, token, refreshGeofences, flash]);

  const onDeleteGeofence = useCallback(
    async (id: string) => {
      try {
        await api.deleteGeofence(brainUrl, token, id);
        await refreshGeofences();
        setSelection(null);
        flash("Zone deleted.");
      } catch (e) {
        flash(`Delete failed: ${(e as Error).message}`);
      }
    },
    [brainUrl, token, refreshGeofences, flash],
  );

  // Drop a stale selection if the underlying entity vanished handled in Inspector.
  // Persist config on change.
  const applyConfig = useCallback((url: string, tok: string) => {
    const next = { brainUrl: url, token: tok };
    saveConfig(next);
    setCfg(next);
  }, []);

  // Keyboard: Esc cancels drawing / closes inspector.
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (drawing) {
          setDrawing(false);
          setDraft([]);
        } else {
          setSelection(null);
        }
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [drawing]);

  const hasTracks = tracks.length > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <TopBar
        status={status}
        brainUrl={brainUrl}
        token={token}
        nodeCount={nodes.length}
        trackCount={tracks.length}
        onSave={applyConfig}
        showCoverage={showCoverage}
        onToggleCoverage={() => setShowCoverage((v) => !v)}
        drawing={drawing}
        onToggleDraw={toggleDraw}
      />

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        {/* MAP */}
        <div style={{ position: "relative", flex: 1, minWidth: 0 }}>
          <MapView
            nodes={nodes}
            tracks={tracks}
            geofences={geofences}
            alertStateByTrack={alertStateByTrack}
            showCoverage={showCoverage}
            drawing={drawing}
            draftPolygon={draft}
            onMapClick={onMapClick}
            onSelectNode={(id) => setSelection({ kind: "node", id })}
            onSelectTrack={(id) => setSelection({ kind: "track", id })}
            onSelectGeofence={(id) => setSelection({ kind: "geofence", id })}
          />

          <Legend />

          {/* Honest empty state — NEVER seed fake contacts. */}
          {!hasTracks && (
            <div
              style={{
                position: "absolute",
                top: 12,
                left: "50%",
                transform: "translateX(-50%)",
                background: "rgba(14,14,16,0.92)",
                border: `1px solid ${COLOR.hairline}`,
                padding: "8px 14px",
                letterSpacing: "0.06em",
                zIndex: 5,
                pointerEvents: "none",
              }}
            >
              No detections. {nodes.length} node{nodes.length === 1 ? "" : "s"}{" "}
              listening.
            </div>
          )}

          {/* Drawing toolbar */}
          {drawing && (
            <div
              style={{
                position: "absolute",
                top: 12,
                right: 12,
                background: COLOR.panel,
                border: `1px solid ${COLOR.accent}`,
                padding: 10,
                zIndex: 10,
                maxWidth: 240,
              }}
            >
              <div style={{ color: COLOR.accent, marginBottom: 6, letterSpacing: "0.08em" }}>
                DRAW GEOFENCE
              </div>
              <div className="dim" style={{ fontSize: 10, marginBottom: 8 }}>
                Click the map to add vertices ({draft.length}). Min 3. Esc to
                cancel.
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => setDraft((d) => d.slice(0, -1))} disabled={!draft.length}>
                  Undo
                </button>
                <button className="accent" onClick={finishDraw} disabled={draft.length < 3}>
                  Save
                </button>
              </div>
            </div>
          )}

          {/* Transient banner */}
          {banner && (
            <div
              style={{
                position: "absolute",
                bottom: 12,
                left: "50%",
                transform: "translateX(-50%)",
                background: COLOR.panel,
                border: `1px solid ${COLOR.hairline}`,
                padding: "6px 12px",
                zIndex: 15,
                fontSize: 11,
              }}
            >
              {banner}
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div
          style={{
            width: 360,
            flex: "0 0 360px",
            borderLeft: `1px solid ${COLOR.hairline}`,
            background: COLOR.panel,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {selection && (
            <Inspector
              selection={selection}
              tracks={tracks}
              nodes={nodes}
              geofences={geofences}
              onClose={() => setSelection(null)}
              onDeleteGeofence={onDeleteGeofence}
            />
          )}
          <AlertFeed
            alerts={alerts}
            onAck={onAck}
            onClose={onCloseAlert}
            onSelectTrack={(id) => setSelection({ kind: "track", id })}
            busy={busy}
          />
          <NodeHealthStrip
            nodes={nodes}
            onSelectNode={(id) => setSelection({ kind: "node", id })}
          />
        </div>
      </div>
    </div>
  );
}
