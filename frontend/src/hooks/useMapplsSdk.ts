import { useEffect, useState } from "react";

const SCRIPT_ID = "mappls-web-sdk";
const SDK_URL = "https://sdk.mappls.com/map/sdk/web";

type SdkState = "idle" | "loading" | "ready" | "missing" | "error";

function key() {
  return import.meta.env.VITE_MAPPLS_WEB_KEY?.trim() || "";
}

export function mapplsWebKeyConfigured() {
  return Boolean(key());
}

export function useMapplsSdk() {
  const [state, setState] = useState<SdkState>(() => {
    if (!key()) return "missing";
    if (window.mappls?.Map) return "ready";
    return "idle";
  });

  useEffect(() => {
    const requested = (import.meta.env.VITE_MAP_PROVIDER || "leaflet").toLowerCase();
    if (requested !== "mappls") {
      setState("missing");
      return;
    }
    const token = key();
    if (!token) {
      setState("missing");
      return;
    }
    if (window.mappls?.Map) {
      setState("ready");
      return;
    }
    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener("load", () => setState("ready"));
      existing.addEventListener("error", () => setState("error"));
      setState("loading");
      return;
    }
    setState("loading");
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.async = true;
    script.src = `${SDK_URL}?v=3.0&access_token=${encodeURIComponent(token)}`;
    script.onload = () => setState(window.mappls?.Map ? "ready" : "error");
    script.onerror = () => setState("error");
    document.head.appendChild(script);
  }, []);

  return { state, ready: state === "ready", configured: Boolean(key()) };
}

declare global {
  interface Window {
    mappls?: {
      Map: new (id: string | HTMLElement, options?: Record<string, unknown>) => MapplsMapInstance;
      Marker: new (options: Record<string, unknown>) => MapplsOverlay;
      Circle?: new (options: Record<string, unknown>) => MapplsOverlay;
      addGeoJson?: (options: Record<string, unknown>) => MapplsOverlay;
      remove?: (options: Record<string, unknown>) => void;
    };
  }
}

export type MapplsOverlay = {
  setPosition?: (position: { lat: number; lng: number }) => void;
  addListener?: (name: string, handler: (event?: unknown) => void) => void;
  remove?: () => void;
};

export type MapplsMapInstance = {
  setCenter?: (position: { lat: number; lng: number }) => void;
  setZoom?: (zoom: number) => void;
  fitBounds?: (bounds: unknown, options?: unknown) => void;
  addListener?: (name: string, handler: (event?: unknown) => void) => void;
  on?: (name: string, handler: (event?: unknown) => void) => void;
  remove?: () => void;
};
