export type GeoPoint = {
  lat: number;
  lng: number;
  /** Device-reported horizontal accuracy radius in metres (Geolocation API). */
  accuracy?: number;
  /** When this device fix was acquired (ISO string or epoch ms). */
  capturedAt?: string;
  /** True when this point came from a fresh getCurrentPosition, not a saved pin. */
  fresh?: boolean;
};

export type LocationKind = "place" | "area" | "street" | "city" | "pin" | "unknown";

export type LocationResult = {
  provider: string;
  name?: string | null;
  formatted_address: string;
  locality?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  landmark?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  mappls_pin?: string | null;
  provider_place_id?: string | null;
  confidence?: number | null;
  precision?: string | null;
  kind?: string | null;
  approximate: boolean;
};

export type LocationSource = "device" | "search" | "map" | "typed";

export type GeocodeResult = {
  label: string;
  point: GeoPoint | null;
  result: LocationResult;
};

export type RouteStep = {
  instruction: string;
  distanceMeters: number;
  durationSeconds: number;
  location?: GeoPoint | null;
};

export type RouteResult = {
  provider: string;
  geometry: GeoPoint[];
  durationSeconds?: number;
  distanceMeters?: number;
  trafficAware?: boolean;
  steps?: RouteStep[];
};

export type LocationConfig = {
  provider: string;
  configured: boolean;
  search: boolean;
  geocoding: boolean;
  reverse_geocoding: boolean;
  routing: boolean;
  distance_matrix: boolean;
  route_optimisation: string;
  service_area_name: string | null;
  service_area_center: { latitude: number; longitude: number } | null;
  service_area_radius_km: number | null;
};

export type MapMode = "known" | "approximate" | "service-area" | "unknown";

export type MapMarkerKind = "donation" | "organisation" | "volunteer" | "driver" | "recovery" | "pickup" | "destination";

export type MapMarker = {
  id?: string;
  point: GeoPoint;
  kind?: MapMarkerKind;
  label?: string;
};
