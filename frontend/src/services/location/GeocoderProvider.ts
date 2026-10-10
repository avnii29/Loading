import { readApiError } from "../auth";
import { resolveMapplsPin, reverseGeocode, searchPlaces } from "./api";
import type { GeocodeResult, GeoPoint, LocationResult } from "./types";

export interface GeocoderProvider {
  search(query: string, bias?: GeoPoint, signal?: AbortSignal): Promise<GeocodeResult[]>;
  reverse(point: GeoPoint): Promise<string | null>;
  resolve(result: LocationResult): Promise<LocationResult>;
}

function toResult(row: LocationResult): GeocodeResult {
  const hasPoint =
    row.latitude != null &&
    row.longitude != null &&
    Number.isFinite(row.latitude) &&
    Number.isFinite(row.longitude) &&
    !(row.latitude === 0 && row.longitude === 0);
  return {
    label: row.formatted_address,
    point: hasPoint ? { lat: row.latitude as number, lng: row.longitude as number } : null,
    result: row,
  };
}

export class BackendGeocoder implements GeocoderProvider {
  async search(query: string, bias?: GeoPoint, signal?: AbortSignal): Promise<GeocodeResult[]> {
    if (!query.trim()) return [];
    try {
      const rows = await searchPlaces(query, bias, signal);
      return rows.map(toResult);
    } catch (error) {
      throw new Error(readApiError(error));
    }
  }

  async reverse(point: GeoPoint): Promise<string | null> {
    try {
      const row = await reverseGeocode(point);
      return row.formatted_address;
    } catch {
      return null;
    }
  }

  async resolve(result: LocationResult): Promise<LocationResult> {
    if ((result.latitude != null && result.longitude != null) || !result.mappls_pin) {
      return result;
    }
    return resolveMapplsPin(result.mappls_pin);
  }
}

export class NominatimGeocoder implements GeocoderProvider {
  private readonly endpoint?: string;

  constructor(endpoint?: string) {
    this.endpoint = endpoint;
  }

  private url() {
    return this.endpoint || "https://nominatim.openstreetmap.org";
  }

  async search(query: string): Promise<GeocodeResult[]> {
    if (!query.trim()) return [];
    const url = new URL(`${this.url()}/search`);
    url.searchParams.set("q", query);
    url.searchParams.set("format", "json");
    url.searchParams.set("limit", "5");
    const res = await fetch(url.toString(), { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error("Address lookup is unavailable right now.");
    const rows = (await res.json()) as { lat: string; lon: string; display_name: string }[];
    return rows.map((row) => ({
      label: row.display_name,
      point:
        Number(row.lat) === 0 && Number(row.lon) === 0
          ? null
          : { lat: Number(row.lat), lng: Number(row.lon) },
      result: {
        provider: "fallback",
        formatted_address: row.display_name,
        latitude: Number(row.lat),
        longitude: Number(row.lon),
        approximate: false,
      },
    }));
  }

  async reverse(point: GeoPoint): Promise<string | null> {
    const url = new URL(`${this.url()}/reverse`);
    url.searchParams.set("lat", String(point.lat));
    url.searchParams.set("lon", String(point.lng));
    url.searchParams.set("format", "json");
    const res = await fetch(url.toString(), { headers: { Accept: "application/json" } });
    if (!res.ok) return null;
    const row = (await res.json()) as { display_name?: string };
    return row.display_name ?? null;
  }

  async resolve(result: LocationResult): Promise<LocationResult> {
    return result;
  }
}
