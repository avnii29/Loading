import { BackendGeocoder } from "./GeocoderProvider";
import { BrowserLocationProvider } from "./LocationProvider";
import { BackendRoutingProvider } from "./RoutingProvider";
import { DistanceService } from "./DistanceService";

export const locationProvider = new BrowserLocationProvider();
export const geocoderProvider = new BackendGeocoder();
export const routingProvider = new BackendRoutingProvider();
export { DistanceService };
export type { GeoPoint, GeocodeResult, LocationResult, RouteResult, LocationConfig, LocationSource, MapMode, MapMarker } from "./types";
