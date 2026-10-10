import { useEffect, useMemo, useState } from "react";
import { MapCanvas } from "./MapCanvas";
import { DirectionsPanel } from "./DirectionsPanel";
import { routingProvider } from "../../services/location";
import type { GeoPoint, RouteResult } from "../../services/location/types";

type Props = {
  pickup: GeoPoint | null;
  destination: GeoPoint | null;
  volunteer?: GeoPoint | null;
  /** Donation status — switches route leg after pickup (Dil Se Daan behaviour). */
  status?: string | null;
  height?: number;
  showDirections?: boolean;
};

/**
 * Status-aware mission map from Dil Se Daan MapComponent:
 * volunteer→pickup before collect; pickup/volunteer→org after IN_TRANSIT.
 */
export function LiveMissionMap({
  pickup,
  destination,
  volunteer = null,
  status = null,
  height = 360,
  showDirections = true,
}: Props) {
  const [route, setRoute] = useState<RouteResult | null>(null);

  const headingToOrg = ["IN_TRANSIT", "DELIVERED", "COMPLETED", "PICKED_UP"].includes(
    (status || "").toUpperCase(),
  );

  const leg = useMemo(() => {
    if (headingToOrg && pickup && destination) {
      return { from: volunteer || pickup, to: destination, label: "To destination" };
    }
    if (volunteer && pickup) {
      return { from: volunteer, to: pickup, label: "To pickup" };
    }
    if (pickup && destination) {
      return { from: pickup, to: destination, label: "Planned path" };
    }
    return null;
  }, [headingToOrg, pickup, destination, volunteer]);

  useEffect(() => {
    let cancelled = false;
    if (!leg) {
      setRoute(null);
      return;
    }
    routingProvider.route(leg.from, leg.to).then((row) => {
      if (!cancelled) setRoute(row);
    });
    return () => {
      cancelled = true;
    };
  }, [leg?.from.lat, leg?.from.lng, leg?.to.lat, leg?.to.lng, leg?.label]);

  const markers = [
    ...(volunteer ? [{ id: "vol", point: volunteer, kind: "volunteer" as const }] : []),
  ];

  const eta =
    route?.durationSeconds != null ? Math.max(1, Math.round(route.durationSeconds / 60)) : null;

  return (
    <div className="live-mission stack">
      <div className="live-mission-map">
        {route?.distanceMeters != null && eta != null ? (
          <div className="map-eta-chip">
            <strong>{eta} min</strong>
            <span>
              {(route.distanceMeters / 1000).toFixed(1)} km · {leg?.label || "Route"}
            </span>
          </div>
        ) : null}
        <MapCanvas
          pickup={pickup}
          destination={destination}
          route={route?.geometry?.length ? route.geometry : leg ? [leg.from, leg.to] : null}
          markers={markers}
          height={height}
        />
      </div>
      {leg && !route?.geometry?.length ? (
        <p className="field-hint">Dashed line is a straight-line preview, not a road route or travel time.</p>
      ) : null}
      {showDirections && leg ? (
        <DirectionsPanel from={leg.from} to={leg.to} title={leg.label} />
      ) : null}
    </div>
  );
}
