import type { GeoPoint } from "./location/types";

type PointLike = { lat?: number | null; lng?: number | null; lon?: number | null };

function point(p?: PointLike | null): string | null {
  if (!p || p.lat == null) return null;
  const lng = p.lng ?? p.lon;
  if (lng == null) return null;
  return `${Number(p.lat)},${Number(lng)}`;
}

/**
 * Google Maps directions deep-link (no Google API key).
 * Ported from Dil Se Daan — opens Maps app / site with real coordinates only.
 */
export function googleMapsDirectionsUrl({
  origin,
  destination,
  waypoints = [],
}: {
  origin?: PointLike | null;
  destination?: PointLike | null;
  waypoints?: PointLike[];
} = {}): string {
  const params = new URLSearchParams({ api: "1", travelmode: "driving" });
  const o = point(origin);
  const d = point(destination);
  if (o) params.set("origin", o);
  if (d) params.set("destination", d);
  const via = (waypoints || []).map(point).filter(Boolean) as string[];
  if (via.length) params.set("waypoints", via.join("|"));
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

export function googleMapsPlaceUrl(pointIn: GeoPoint): string {
  return `https://www.google.com/maps/search/?api=1&query=${pointIn.lat},${pointIn.lng}`;
}
