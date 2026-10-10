import { useState } from "react";
import { MapView } from "./MapView";
import { MapplsMap } from "./MapplsMap";
import { useMapplsSdk } from "../../hooks/useMapplsSdk";
import type { GeoPoint, MapMarker, MapMode } from "../../services/location/types";

const NO_MARKERS: MapMarker[] = [];

type Props = {
  mode?: MapMode;
  pickup?: GeoPoint | null;
  destination?: GeoPoint | null;
  route?: GeoPoint[] | null;
  markers?: MapMarker[];
  height?: number;
  interactive?: boolean;
  onSelect?: (point: GeoPoint) => void;
  emptyLabel?: string;
  /** Overview centre only — never treated as the user's current location. */
  serviceAreaCenter?: GeoPoint | null;
  deviceGps?: GeoPoint | null;
  lockView?: boolean;
  onLocateMe?: () => void;
  showPickupBanner?: boolean;
};

function providerName() {
  return (import.meta.env.VITE_MAP_PROVIDER || "leaflet").toLowerCase();
}

export function MapCanvas({
  mode,
  pickup,
  destination,
  route,
  markers = NO_MARKERS,
  height = 320,
  interactive = false,
  onSelect,
  serviceAreaCenter = null,
  deviceGps = null,
  lockView = false,
  onLocateMe,
  showPickupBanner = false,
}: Props) {
  const { ready, configured, state } = useMapplsSdk();
  const [mapFailed, setMapFailed] = useState(false);
  const points = [pickup, destination, ...markers.map((item) => item.point)].filter(Boolean) as GeoPoint[];
  const resolvedMode: MapMode = mode || (points.length ? "known" : "unknown");
  const requested = providerName();

  const useLeaflet = requested !== "mappls" || !configured || state === "error" || mapFailed;
  const fallbackReason =
    requested !== "mappls"
      ? "Map data © OpenStreetMap contributors"
      : null;

  if (useLeaflet) {
    return (
      <div className="map-shell">
        <div className="map-frame" style={{ height }}>
          <MapView
            pickup={pickup}
            destination={destination}
            route={route?.map((point) => [point.lat, point.lng])}
            markers={markers}
            height={height}
            interactive={interactive}
            onSelect={onSelect}
            overviewCenter={serviceAreaCenter}
            deviceGps={deviceGps}
            lockView={lockView}
            onLocateMe={onLocateMe}
            showPickupBanner={showPickupBanner}
          />
        </div>
        {fallbackReason ? <p className="map-attr">{fallbackReason}</p> : null}
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="loc-placeholder" style={{ height, minHeight: height }}>
        Loading map…
      </div>
    );
  }

  return (
    <div className="map-shell">
      <div className="map-frame mappls-frame" style={{ height }}>
        <MapplsMap
          mode={resolvedMode}
          center={pickup || destination || markers[0]?.point || serviceAreaCenter || undefined}
          pickup={pickup}
          destination={destination}
          route={route}
          markers={markers}
          height={height}
          interactive={interactive}
          onSelect={onSelect}
          onFailure={() => setMapFailed(true)}
        />
      </div>
      <p className="map-attr">Map provider: Mappls · Built using Mappls APIs.</p>
    </div>
  );
}
