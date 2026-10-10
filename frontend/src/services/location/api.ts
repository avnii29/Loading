import api from "../api";
import type { GeoPoint, LocationConfig, LocationResult, RouteResult } from "./types";

export async function fetchLocationConfig() {
  const { data } = await api.get<LocationConfig>("/location/config");
  return data;
}

export async function searchPlaces(query: string, bias?: GeoPoint, signal?: AbortSignal) {
  const { data } = await api.get<LocationResult[]>("/location/search", {
    params: {
      q: query,
      lat: bias?.lat,
      lng: bias?.lng,
    },
    signal,
  });
  return data;
}

export async function reverseGeocode(point: GeoPoint) {
  const { data } = await api.post<LocationResult>("/location/reverse-geocode", {
    latitude: point.lat,
    longitude: point.lng,
  });
  return data;
}

export async function resolveMapplsPin(pin: string) {
  const { data } = await api.get<LocationResult>(`/location/places/${encodeURIComponent(pin)}`);
  return data;
}

export async function previewRoute(origin: GeoPoint, destination: GeoPoint, travelMode = "DRIVING") {
  const { data } = await api.post<{
    provider: string;
    distance_meters: number;
    duration_seconds: number;
    geometry: { latitude: number; longitude: number }[];
    traffic_aware: boolean;
  }>("/location/routes/preview", {
    origin: { latitude: origin.lat, longitude: origin.lng },
    destination: { latitude: destination.lat, longitude: destination.lng },
    travel_mode: travelMode,
  });
  const result: RouteResult = {
    provider: data.provider,
    distanceMeters: data.distance_meters,
    durationSeconds: data.duration_seconds,
    trafficAware: data.traffic_aware,
    geometry: data.geometry.map((item) => ({ lat: item.latitude, lng: item.longitude })),
  };
  return result;
}
