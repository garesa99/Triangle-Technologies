"use client";

// Runtime config: env defaults, overridable in-app and persisted to localStorage.

export interface RuntimeConfig {
  brainUrl: string;
  token: string;
}

const LS_KEY = "triangle-mesh-config";

export const DEFAULT_BRAIN_URL =
  process.env.NEXT_PUBLIC_BRAIN_URL || "http://localhost:8000";
export const DEFAULT_TOKEN =
  process.env.NEXT_PUBLIC_BRAIN_TOKEN || "triangle-dev-token";

// Optional real-tile URL template. Unset => bundled offline dark style is used.
export const TILE_URL: string | null = process.env.NEXT_PUBLIC_TILE_URL || null;

export function loadConfig(): RuntimeConfig {
  const fallback: RuntimeConfig = {
    brainUrl: DEFAULT_BRAIN_URL,
    token: DEFAULT_TOKEN,
  };
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(LS_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw) as Partial<RuntimeConfig>;
    return {
      brainUrl: parsed.brainUrl?.trim() || fallback.brainUrl,
      token: parsed.token?.trim() || fallback.token,
    };
  } catch {
    return fallback;
  }
}

export function saveConfig(cfg: RuntimeConfig): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LS_KEY, JSON.stringify(cfg));
}

// Derive the ws:// or wss:// URL from an http(s) brain base URL.
export function wsUrl(brainUrl: string, token: string): string {
  let base = brainUrl.trim().replace(/\/+$/, "");
  base = base.replace(/^http/, "ws"); // http->ws, https->wss
  return `${base}/ws?token=${encodeURIComponent(token)}`;
}
