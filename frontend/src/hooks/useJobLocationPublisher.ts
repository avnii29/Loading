import { useEffect, useRef } from "react";
import { BrowserLocationProvider } from "../services/location/LocationProvider";
import { publishJobLocation } from "../services/logistics";
import type { GeoPoint } from "../services/location/types";

function movedMeters(a: GeoPoint, b: GeoPoint) {
  const toRad = (n: number) => (n * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.min(1, Math.sqrt(h)));
}

/**
 * Publishes real device GPS for one active assignment. Stops the watch on unmount or when assignmentId is null.
 */
export function useJobLocationPublisher(assignmentId: string | null) {
  const last = useRef<{ point: GeoPoint; at: number } | null>(null);
  const gps = useRef(new BrowserLocationProvider());

  useEffect(() => {
    if (!assignmentId) return;
    let cancelled = false;
    const provider = gps.current;
    provider.watch(
      (point) => {
        if (cancelled) return;
        const prev = last.current;
        const now = Date.now();
        if (prev && now - prev.at < 8000 && movedMeters(prev.point, point) < 12) return;
        last.current = { point, at: now };
        void publishJobLocation(assignmentId, point).catch(() => {
          /* server rejects stale jobs; do not invent a fix */
        });
      },
      () => {
        /* permission or timeout — UI keeps last server fix */
      },
    );
    return () => {
      cancelled = true;
      provider.stop();
    };
  }, [assignmentId]);
}
