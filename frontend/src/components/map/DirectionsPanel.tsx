import { useEffect, useState } from "react";
import { ExternalLink, Navigation } from "lucide-react";
import { routingProvider } from "../../services/location";
import { googleMapsDirectionsUrl } from "../../services/mapsLinks";
import type { GeoPoint, RouteResult } from "../../services/location/types";

function formatM(meters?: number | null) {
  if (meters == null) return "";
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}

/**
 * Dil Se Daan VolunteerDirections — turn-by-turn when available + Google Maps deep-link.
 */
export function DirectionsPanel({
  from,
  to,
  title = "Directions",
}: {
  from: GeoPoint | null;
  to: GeoPoint | null;
  title?: string;
}) {
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!from || !to) {
      setRoute(null);
      return;
    }
    setError("");
    routingProvider
      .route(from, to, "DRIVING", { steps: true })
      .then((row) => {
        if (!cancelled) setRoute(row);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load route. Retry when GPS updates.");
      });
    return () => {
      cancelled = true;
    };
  }, [from?.lat, from?.lng, to?.lat, to?.lng]);

  if (!from || !to) {
    return <p className="muted">Waiting for confirmed coordinates to build directions…</p>;
  }

  const mapsUrl = googleMapsDirectionsUrl({ origin: from, destination: to });
  const eta =
    route?.durationSeconds != null ? Math.max(1, Math.round(route.durationSeconds / 60)) : null;

  return (
    <aside className="directions-panel stack">
      <div className="welcome-row">
        <div className="ai-row">
          <Navigation size={18} aria-hidden />
          <h3 style={{ margin: 0 }}>{title}</h3>
        </div>
        {route?.distanceMeters != null ? (
          <strong className="dir-meta">
            {formatM(route.distanceMeters)}
            {eta != null ? ` · ~${eta} min` : ""}
          </strong>
        ) : null}
      </div>
      {error ? <p className="field-error">{error}</p> : null}
      {!route && !error ? <p className="muted">Calculating road route…</p> : null}
      {route?.steps && route.steps.length > 0 ? (
        <ol className="directions-steps">
          {route.steps.slice(0, 24).map((step, i) => (
            <li key={`${i}-${step.instruction}`}>
              <span className="step-num">{i + 1}</span>
              <div>
                <strong>{step.instruction}</strong>
                <small className="muted">{formatM(step.distanceMeters)}</small>
              </div>
            </li>
          ))}
        </ol>
      ) : null}
      <a className="btn btn-secondary" href={mapsUrl} target="_blank" rel="noreferrer">
        Open in Google Maps <ExternalLink size={14} aria-hidden />
      </a>
      {route?.provider ? (
        <p className="field-hint">Route via {route.provider}. ETA is a provider estimate, not a promise.</p>
      ) : null}
    </aside>
  );
}
