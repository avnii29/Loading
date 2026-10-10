import { previewRoute } from "./api";
import type { GeoPoint, RouteResult } from "./types";

export interface RoutingProvider {
  route(from: GeoPoint, to: GeoPoint, travelMode?: string, options?: { steps?: boolean }): Promise<RouteResult | null>;
}

/**
 * Road routes come from the backend OpenStreetMap router (OSRM).
 * A failed request returns null — the UI must say the route is unavailable.
 */
export class BackendRoutingProvider implements RoutingProvider {
  async route(
    from: GeoPoint,
    to: GeoPoint,
    travelMode = "DRIVING",
    _options: { steps?: boolean } = {},
  ): Promise<RouteResult | null> {
    if (![from.lat, from.lng, to.lat, to.lng].every((n) => Number.isFinite(n))) return null;
    if (from.lat === 0 && from.lng === 0) return null;
    if (to.lat === 0 && to.lng === 0) return null;
    try {
      const backend = await previewRoute(from, to, travelMode);
      if (!backend?.geometry?.length) return null;
      return backend;
    } catch {
      return null;
    }
  }
}

export class ConfigurableRoutingProvider implements RoutingProvider {
  private readonly endpoint?: string;

  constructor(endpoint?: string) {
    this.endpoint = endpoint;
  }

  async route(from: GeoPoint, to: GeoPoint): Promise<RouteResult | null> {
    if (!this.endpoint) return null;
    const url = new URL(this.endpoint);
    url.searchParams.set("from", `${from.lng},${from.lat}`);
    url.searchParams.set("to", `${to.lng},${to.lat}`);
    try {
      const res = await fetch(url.toString());
      if (!res.ok) return null;
      return (await res.json()) as RouteResult;
    } catch {
      return null;
    }
  }
}
