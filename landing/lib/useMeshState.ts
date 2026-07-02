"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Alert,
  ConnStatus,
  Geofence,
  MeshNode,
  Track,
  WsMessage,
} from "./types";
import { api } from "./api";
import { wsUrl } from "./config";

interface MeshState {
  nodes: MeshNode[];
  tracks: Track[];
  alerts: Alert[];
  geofences: Geofence[];
  status: ConnStatus;
  refreshGeofences: () => Promise<void>;
}

// Merge an incoming array of items into an existing list keyed by id.
function mergeBy<T>(existing: T[], incoming: T[], key: (t: T) => string): T[] {
  const map = new Map(existing.map((e) => [key(e), e]));
  for (const item of incoming) map.set(key(item), item);
  return Array.from(map.values());
}

export function useMeshState(brainUrl: string, token: string, enabled = true): MeshState {
  const [nodes, setNodes] = useState<MeshNode[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [status, setStatus] = useState<ConnStatus>("RECONNECTING");

  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closedRef = useRef<boolean>(false);

  const refreshGeofences = useCallback(async () => {
    try {
      const gf = await api.getGeofences(brainUrl, token);
      setGeofences(gf);
    } catch {
      /* keep last known on transient failure */
    }
  }, [brainUrl, token]);

  const handleMessage = useCallback((msg: WsMessage) => {
    switch (msg.type) {
      case "snapshot":
        setNodes(msg.data.nodes || []);
        // Only active tracks are pushed; snapshot is authoritative -> replace.
        setTracks(msg.data.tracks || []);
        setAlerts(msg.data.alerts || []);
        setGeofences(msg.data.geofences || []);
        break;
      case "nodes":
        setNodes(msg.data || []);
        break;
      case "tracks":
        setTracks((prev) =>
          mergeBy(prev, msg.data || [], (t) => t.track_id).filter(
            (t) => t.state === "active",
          ),
        );
        break;
      case "alerts":
        setAlerts((prev) =>
          mergeBy(prev, msg.data || [], (a) => a.alert_id),
        );
        break;
      case "mesh":
        // Mesh connectivity is derived client-side from node online state;
        // nothing to store from this event type today.
        break;
    }
  }, []);

  useEffect(() => {
    closedRef.current = false;
    if (!enabled) return; // demo mode: no brain connection

    function scheduleReconnect() {
      if (closedRef.current) return;
      retryRef.current = Math.min(retryRef.current + 1, 6);
      const delay = Math.min(1000 * 2 ** (retryRef.current - 1), 15000);
      setStatus(retryRef.current >= 4 ? "OFFLINE" : "RECONNECTING");
      timerRef.current = setTimeout(connect, delay);
    }

    function connect() {
      if (closedRef.current) return;
      let ws: WebSocket;
      try {
        ws = new WebSocket(wsUrl(brainUrl, token));
      } catch {
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setStatus("LIVE");
      };
      ws.onmessage = (ev) => {
        try {
          handleMessage(JSON.parse(ev.data) as WsMessage);
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          /* noop */
        }
      };
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
        scheduleReconnect();
      };
    }

    connect();

    return () => {
      closedRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          /* noop */
        }
        wsRef.current = null;
      }
    };
  }, [brainUrl, token, handleMessage, enabled]);

  return { nodes, tracks, alerts, geofences, status, refreshGeofences };
}
