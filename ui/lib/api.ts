"use client";

// Thin REST client for the brain. All calls send Authorization: Bearer <token>.

import type { Alert, Geofence, MeshNode, Track } from "./types";

function headers(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
}

function base(brainUrl: string): string {
  return brainUrl.trim().replace(/\/+$/, "");
}

async function req<T>(
  brainUrl: string,
  token: string,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${base(brainUrl)}${path}`, {
    ...init,
    headers: { ...headers(token), ...(init?.headers || {}) },
  });
  if (!res.ok) {
    throw new Error(`${init?.method || "GET"} ${path} -> ${res.status}`);
  }
  // Some endpoints return {ok:true}; callers that don't care can ignore.
  const text = await res.text();
  return (text ? JSON.parse(text) : {}) as T;
}

export const api = {
  getNodes: (b: string, t: string) => req<MeshNode[]>(b, t, "/nodes"),
  getTracks: (b: string, t: string) => req<Track[]>(b, t, "/tracks"),
  getAlerts: (b: string, t: string) => req<Alert[]>(b, t, "/alerts"),
  getGeofences: (b: string, t: string) => req<Geofence[]>(b, t, "/geofences"),

  ackAlert: (b: string, t: string, id: string) =>
    req<{ ok: boolean }>(b, t, `/alerts/${encodeURIComponent(id)}/ack`, {
      method: "POST",
    }),
  closeAlert: (b: string, t: string, id: string) =>
    req<{ ok: boolean }>(b, t, `/alerts/${encodeURIComponent(id)}/close`, {
      method: "POST",
    }),

  createGeofence: (
    b: string,
    t: string,
    body: { name: string; kind: string; polygon: [number, number][] },
  ) =>
    req<{ ok: boolean; id: string }>(b, t, "/geofences", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteGeofence: (b: string, t: string, id: string) =>
    req<{ ok: boolean }>(b, t, `/geofences/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
};
