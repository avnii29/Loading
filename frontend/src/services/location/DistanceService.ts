import type { GeoPoint, RouteResult, RouteStep } from "./types";

function toRad(value: number) {
  return (value * Math.PI) / 180;
}

/**
 * Straight-line + OSRM road routing helpers — ported from Dil Se Daan.
 * Never invents geometry when OSRM fails; returns null instead.
 */
export const DistanceService = {
  /** Great-circle distance in kilometres. */
  km(a: GeoPoint, b: GeoPoint): number {
    return Math.round((this.meters(a, b) / 1000) * 100) / 100;
  },

  /** Great-circle distance in metres (Dil Se Daan getStraightLineDistance). */
  meters(a: GeoPoint, b: GeoPoint): number {
    const dLat = toRad(b.lat - a.lat);
    const dLng = toRad(b.lng - a.lng);
    const lat1 = toRad(a.lat);
    const lat2 = toRad(b.lat);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 2 * 6371000 * Math.asin(Math.min(1, Math.sqrt(h)));
  },

  /**
   * Public OSRM driving route. Used as Leaflet fallback when Mappls routing is unavailable.
   */
  async getRoute(
    from: GeoPoint,
    to: GeoPoint,
    options: { steps?: boolean; signal?: AbortSignal } = {},
  ): Promise<RouteResult | null> {
    const controller = options.signal ? null : new AbortController();
    const signal = options.signal || controller?.signal;
    const timer = controller ? window.setTimeout(() => controller.abort(), 4500) : 0;
    try {
      const url =
        `https://router.project-osrm.org/route/v1/driving/${from.lng},${from.lat};${to.lng},${to.lat}` +
        `?overview=full&geometries=geojson${options.steps ? "&steps=true" : ""}`;
      const res = await fetch(url, signal ? { signal } : undefined);
      if (!res.ok) return null;
      const data = (await res.json()) as {
        routes?: {
          distance: number;
          duration: number;
          geometry: { coordinates: [number, number][] };
          legs?: {
            steps?: {
              name?: string;
              distance?: number;
              duration?: number;
              maneuver?: { type?: string; modifier?: string; location?: [number, number] };
            }[];
          }[];
        }[];
      };
      const route = data.routes?.[0];
      if (!route) return null;

      const steps: RouteStep[] = [];
      if (options.steps && route.legs) {
        for (const leg of route.legs) {
          for (const step of leg.steps || []) {
            const maneuver = step.maneuver || {};
            const instruction = [maneuver.type || "turn", maneuver.modifier || "", step.name ? `onto ${step.name}` : ""]
              .filter(Boolean)
              .join(" ")
              .replace(/\s+/g, " ")
              .trim();
            steps.push({
              instruction: instruction || "Continue",
              distanceMeters: step.distance || 0,
              durationSeconds: step.duration || 0,
              location: maneuver.location
                ? { lat: maneuver.location[1], lng: maneuver.location[0] }
                : null,
            });
          }
        }
      }

      return {
        provider: "osrm",
        geometry: route.geometry.coordinates.map(([lng, lat]) => ({ lat, lng })),
        distanceMeters: route.distance,
        durationSeconds: route.duration,
        trafficAware: false,
        steps,
      };
    } catch {
      return null;
    } finally {
      if (timer) window.clearTimeout(timer);
    }
  },
};
