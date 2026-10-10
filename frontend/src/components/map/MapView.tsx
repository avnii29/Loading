import { MapContainer, Marker, TileLayer, Circle, Polyline, useMap, useMapEvents } from "react-leaflet";
import { useEffect, useRef, useState } from "react";
import type { GeoPoint, MapMarker } from "../../services/location";
import { houseIcon, orgIcon, gpsDotIcon, iconForKind } from "./mapIcons";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

/** Starting camera only. Not a selected pickup and not the user's GPS. */
const HYDERABAD: GeoPoint = { lat: 17.385, lng: 78.4867 };
const HYDERABAD_ZOOM = 13;

function ResizeMap() {
  const map = useMap();
  useEffect(() => {
    const fix = () => map.invalidateSize();
    fix();
    const timer = window.setTimeout(fix, 250);
    window.addEventListener("resize", fix);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("resize", fix);
    };
  }, [map]);
  return null;
}

/** Fly to real points only. Never invent a city centre. */
function MapController({ points, lockView = false }: { points: GeoPoint[]; lockView?: boolean }) {
  const map = useMap();
  const lastKey = useRef("");
  useEffect(() => {
    if (lockView || !points.length) return;
    const key = points.map((p) => `${p.lat.toFixed(4)},${p.lng.toFixed(4)}`).join("|");
    if (key === lastKey.current) return;
    lastKey.current = key;
    if (points.length === 1) {
      map.flyTo([points[0].lat, points[0].lng], 16, { duration: 0.7 });
      return;
    }
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lng] as [number, number]));
    map.flyToBounds(bounds, { padding: [48, 48], duration: 1.0 });
  }, [map, points, lockView]);
  return null;
}

function MapUIControls({ onLocateMe }: { onLocateMe?: () => void }) {
  const map = useMap();
  return (
    <div className="map-ui-controls" aria-label="Map controls">
      {onLocateMe ? (
        <button type="button" className="map-ui-btn" onClick={onLocateMe} title="Locate me">
          ⊕
        </button>
      ) : null}
      <div className="map-ui-zoom">
        <button type="button" className="map-ui-btn" onClick={() => map.zoomIn()} title="Zoom in">
          +
        </button>
        <button type="button" className="map-ui-btn" onClick={() => map.zoomOut()} title="Zoom out">
          −
        </button>
      </div>
    </div>
  );
}

function Compass() {
  const [heading, setHeading] = useState<number | null>(null);
  useEffect(() => {
    const onOrient = (event: DeviceOrientationEvent) => {
      const webkit = (event as DeviceOrientationEvent & { webkitCompassHeading?: number }).webkitCompassHeading;
      const value = typeof webkit === "number" ? webkit : event.alpha;
      if (typeof value === "number" && Number.isFinite(value)) setHeading(value);
    };
    window.addEventListener("deviceorientation", onOrient);
    return () => window.removeEventListener("deviceorientation", onOrient);
  }, []);
  if (heading == null) return null;
  return (
    <div className="map-compass" aria-label={`Device heading ${Math.round(heading)} degrees`}>
      <span style={{ transform: `rotate(${heading}deg)` }}>N</span>
    </div>
  );
}

function HouseMarker({
  pickup,
  interactive,
  onSelect,
}: {
  pickup: GeoPoint;
  interactive: boolean;
  onSelect?: (point: GeoPoint) => void;
}) {
  const markerRef = useRef<L.Marker | null>(null);
  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) return;
    const here = marker.getLatLng();
    if (Math.abs(here.lat - pickup.lat) > 1e-7 || Math.abs(here.lng - pickup.lng) > 1e-7) {
      marker.setLatLng([pickup.lat, pickup.lng]);
    }
  }, [pickup.lat, pickup.lng]);

  return (
    <Marker
      ref={markerRef}
      position={[pickup.lat, pickup.lng]}
      icon={houseIcon}
      draggable={interactive}
      eventHandlers={
        interactive && onSelect
          ? {
              dragend: (event) => {
                const next = event.target.getLatLng();
                onSelect({ lat: next.lat, lng: next.lng });
              },
            }
          : undefined
      }
    />
  );
}

function Pick({ onSelect }: { onSelect: (point: GeoPoint) => void }) {
  useMapEvents({
    click(event) {
      onSelect({ lat: event.latlng.lat, lng: event.latlng.lng });
    },
  });
  return null;
}

export function MapView({
  pickup,
  destination,
  route,
  markers,
  height = 280,
  interactive = false,
  onSelect,
  overviewCenter = null,
  deviceGps = null,
  lockView = false,
  onLocateMe,
  showPickupBanner = false,
}: {
  pickup?: GeoPoint | null;
  destination?: GeoPoint | null;
  route?: [number, number][] | null;
  markers?: MapMarker[];
  height?: number;
  interactive?: boolean;
  onSelect?: (point: GeoPoint) => void;
  overviewCenter?: GeoPoint | null;
  /** Separate blue GPS sample — never silently moves the house pin. */
  deviceGps?: GeoPoint | null;
  lockView?: boolean;
  onLocateMe?: () => void;
  showPickupBanner?: boolean;
}) {
  const tiles = import.meta.env.VITE_MAP_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const attribution =
    import.meta.env.VITE_MAP_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
  const extra = (markers ?? []).map((item) => item.point);
  const points = [pickup, destination, ...extra].filter(Boolean) as GeoPoint[];
  const center = points[0] || deviceGps || overviewCenter || HYDERABAD;
  const located = Boolean(points.length || deviceGps);

  return (
    <div className="map-frame-rich" style={{ height, width: "100%" }}>
      {showPickupBanner && pickup && interactive ? (
        <div className="map-pickup-banner">This is the pickup location — drag the green house pin to adjust</div>
      ) : null}
      <MapContainer
        center={[center.lat, center.lng]}
        zoom={located ? (pickup ? 15 : HYDERABAD_ZOOM) : HYDERABAD_ZOOM}
        scrollWheelZoom
        zoomControl={false}
        style={{ height, width: "100%" }}
      >
        <TileLayer attribution={attribution} url={tiles} maxZoom={19} />
        <ResizeMap />
        {interactive && onSelect ? <Pick onSelect={onSelect} /> : null}
        <MapController points={points.length ? points : deviceGps ? [deviceGps] : []} lockView={lockView} />
        <MapUIControls onLocateMe={onLocateMe} />
        <Compass />

        {pickup ? <HouseMarker pickup={pickup} interactive={interactive} onSelect={onSelect} /> : null}
        {pickup?.accuracy && !deviceGps ? (
          <Circle
            center={[pickup.lat, pickup.lng]}
            radius={pickup.accuracy}
            pathOptions={{ color: "#E65C24", fillOpacity: 0.08, weight: 1 }}
          />
        ) : null}
        {destination ? <Marker position={[destination.lat, destination.lng]} icon={orgIcon} /> : null}
        {markers?.map((item, index) => (
          <Marker
            key={item.id ?? index}
            position={[item.point.lat, item.point.lng]}
            icon={iconForKind(item.kind)}
          />
        ))}
        {route && route.length > 1 ? (
          <Polyline
            positions={route.map(([lat, lng]) => [lat, lng])}
            pathOptions={{ color: "#E8721C", weight: 4, opacity: 0.85, dashArray: "8 6" }}
          />
        ) : null}
        {deviceGps ? (
          <>
            {deviceGps.accuracy != null ? (
              <Circle
                center={[deviceGps.lat, deviceGps.lng]}
                radius={deviceGps.accuracy}
                pathOptions={{ color: "#3B82F6", fillColor: "#3B82F6", fillOpacity: 0.1, weight: 1 }}
              />
            ) : null}
            <Marker position={[deviceGps.lat, deviceGps.lng]} icon={gpsDotIcon} interactive={false} />
          </>
        ) : null}
      </MapContainer>
    </div>
  );
}
