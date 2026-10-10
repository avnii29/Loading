import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { MapCanvas } from "./MapCanvas";
import { routingProvider } from "../../services/location";
import { googleMapsDirectionsUrl } from "../../services/mapsLinks";
import type { GeoPoint, RouteResult } from "../../services/location/types";

type Props = {
  origin: GeoPoint | null;
  destination: GeoPoint | null;
  height?: number;
};

/**
 * Real road route (Mappls BFF → OSRM fallback). Never invents geometry.
 */
export function RoutePreview({ origin, destination, height = 280 }: Props) {
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!origin || !destination) {
      setRoute(null);
      setError("");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");
    routingProvider
      .route(origin, destination)
      .then((row) => {
        if (!cancelled) {
          setRoute(row);
          if (!row) setError("Route preview unavailable.");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRoute(null);
          setError("Route preview unavailable.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [origin?.lat, origin?.lng, destination?.lat, destination?.lng]);

  if (!origin || !destination) {
    return (
      <div className="loc-placeholder" style={{ minHeight: height }}>
        Route preview needs confirmed pickup and destination coordinates.
      </div>
    );
  }

  const mapsUrl = googleMapsDirectionsUrl({ origin, destination });
  const eta =
    route?.durationSeconds != null ? Math.max(1, Math.round(route.durationSeconds / 60)) : null;

  return (
    <div className="route-preview stack">
      <div className="live-mission-map">
        {route?.distanceMeters != null && eta != null ? (
          <div className="map-eta-chip">
            <strong>{eta} min</strong>
            <span>
              {(route.distanceMeters / 1000).toFixed(1)} km · {route.provider}
            </span>
          </div>
        ) : null}
        <MapCanvas
          pickup={origin}
          destination={destination}
          route={route?.geometry?.length ? route.geometry : null}
          height={height}
        />
      </div>
      {loading ? <p className="muted">Loading road route…</p> : null}
      {route?.distanceMeters != null ? (
        <p className="field-hint">
          Road distance ≈ {(route.distanceMeters / 1000).toFixed(1)} km
          {eta != null ? ` · est. ${eta} min (provider estimate, not a guarantee)` : ""}
          {route.trafficAware ? " · traffic-aware" : ""}
        </p>
      ) : null}
      {error ? (
        <p className="field-hint">
          {error} Showing endpoints only — not a fabricated path.
        </p>
      ) : null}
      <a className="btn btn-secondary" href={mapsUrl} target="_blank" rel="noreferrer">
        Open in Google Maps <ExternalLink size={14} aria-hidden />
      </a>
    </div>
  );
}
