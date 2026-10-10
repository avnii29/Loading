import type { GeoPoint } from "./types";

export type DistancePair = {
  origin: GeoPoint;
  destination: GeoPoint;
  distanceMeters: number;
  durationSeconds?: number;
  provider: string;
};

export interface DistanceProvider {
  matrix(origin: GeoPoint, destinations: GeoPoint[]): Promise<DistancePair[]>;
}

export class HaversineDistanceProvider implements DistanceProvider {
  async matrix(origin: GeoPoint, destinations: GeoPoint[]): Promise<DistancePair[]> {
    return destinations.map((destination) => ({
      origin,
      destination,
      distanceMeters: haversineMeters(origin, destination),
      provider: "fallback",
    }));
  }
}

function haversineMeters(a: GeoPoint, b: GeoPoint) {
  const r = 6371000;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * r * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}
