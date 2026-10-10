import { useEffect, useId, useRef, useState } from "react";
import { useMapplsSdk, type MapplsMapInstance, type MapplsOverlay } from "../../hooks/useMapplsSdk";
import type { GeoPoint, MapMarker, MapMode } from "../../services/location/types";

type Props = {
  mode: MapMode;
  center?: GeoPoint | null;
  pickup?: GeoPoint | null;
  destination?: GeoPoint | null;
  route?: GeoPoint[] | null;
  markers?: MapMarker[];
  height?: number;
  interactive?: boolean;
  onSelect?: (point: GeoPoint) => void;
  onFailure?: () => void;
};

type ResizableMap = MapplsMapInstance & {
  resize?: () => void;
  invalidateSize?: () => void;
};

function zoomFor(point: GeoPoint | null | undefined, mode: MapMode) {
  if (!point) return 5;
  if (mode === "service-area") return 11;
  if (mode === "approximate") return 13;
  const accuracy = point.accuracy;
  if (accuracy == null || !Number.isFinite(accuracy)) return 16;
  if (accuracy <= 25) return 17;
  if (accuracy <= 80) return 16;
  if (accuracy <= 250) return 15;
  if (accuracy <= 800) return 14;
  return 13;
}

function eventPoint(event: unknown): GeoPoint | null {
  const raw = event as {
    latLng?: { lat: () => number; lng: () => number } | { lat: number; lng: number };
    lngLat?: { lat: number; lng: number };
  };
  const value = raw?.latLng || raw?.lngLat;
  if (!value) return null;
  const lat = typeof value.lat === "function" ? value.lat() : value.lat;
  const lng = typeof value.lng === "function" ? value.lng() : value.lng;
  if (typeof lat !== "number" || typeof lng !== "number") return null;
  return { lat, lng };
}

function forceFill(host: HTMLElement) {
  host.style.width = "100%";
  host.style.height = "100%";
  host.style.minHeight = "100%";
  host.style.display = "block";
  host.style.position = "relative";
  const kids = host.querySelectorAll<HTMLElement>(
    ".maplibregl-map, .mapboxgl-map, .mappls-map, canvas.maplibregl-canvas, canvas.mapboxgl-canvas, .maplibregl-canvas-container, .mapboxgl-canvas-container",
  );
  kids.forEach((node) => {
    node.style.width = "100%";
    node.style.height = "100%";
    node.style.minHeight = "100%";
  });
}

function resizeMap(map: ResizableMap | null, host: HTMLElement | null) {
  if (host) forceFill(host);
  try {
    map?.resize?.();
    map?.invalidateSize?.();
  } catch {
    /* SDK may throw during teardown */
  }
}

export function MapplsMap({
  mode,
  center,
  pickup,
  destination,
  route,
  markers = [],
  height = 320,
  interactive = false,
  onSelect,
  onFailure,
}: Props) {
  const { ready } = useMapplsSdk();
  const mapId = `mappls-map-${useId().replace(/:/g, "")}`;
  const hostRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<ResizableMap | null>(null);
  const layersRef = useRef<MapplsOverlay[]>([]);
  const interactiveRef = useRef(interactive);
  const onSelectRef = useRef(onSelect);
  const onFailureRef = useRef(onFailure);
  const viewRef = useRef({ center, pickup, destination, markers, mode });
  const focusRef = useRef("");
  const [loaded, setLoaded] = useState(false);
  interactiveRef.current = interactive;
  onSelectRef.current = onSelect;
  onFailureRef.current = onFailure;
  viewRef.current = { center, pickup, destination, markers, mode };

  useEffect(() => {
    if (!ready || !window.mappls || !hostRef.current) return;
    const parent = hostRef.current;
    let host: HTMLDivElement | null = null;
    let map: ResizableMap | null = null;
    let disposed = false;
    let loadTimer = 0;
    let resizeTimers: number[] = [];
    let observer: ResizeObserver | null = null;

    // Strict mode mounts, unmounts, then mounts again. Wait until layout has a real height.
    const startTimer = window.setTimeout(() => {
      if (disposed || !parent.isConnected || !window.mappls) return;
      const box = parent.getBoundingClientRect();
      if (box.height < 40 || box.width < 40) {
        // Container still collapsed — fail over so Leaflet fills the frame instead of beige void.
        onFailureRef.current?.();
        return;
      }

      host = document.createElement("div");
      host.id = mapId;
      host.className = "mappls-sdk-host";
      forceFill(host);
      parent.appendChild(host);

      const { center: viewCenter, pickup: viewPickup, destination: viewDestination, markers: viewMarkers, mode: viewMode } =
        viewRef.current;
      const start = viewCenter || viewPickup || viewDestination || viewMarkers[0]?.point;
      if (!start) {
        onFailureRef.current?.();
        return;
      }
      try {
        map = new window.mappls.Map(mapId, {
          center: [start.lat, start.lng],
          zoom: viewMode !== "service-area" ? 15 : 11,
          zoomControl: true,
          location: false,
          backgroundColor: "#e8e4dc",
        }) as ResizableMap;
      } catch {
        host.remove();
        host = null;
        onFailureRef.current?.();
        return;
      }
      mapRef.current = map;

      const click = (event: unknown) => {
        if (!interactiveRef.current || !onSelectRef.current) return;
        const point = eventPoint(event);
        if (point) onSelectRef.current(point);
      };
      map.addListener?.("click", click);
      map.on?.("click", click);

      const markLoaded = () => {
        if (disposed) return;
        setLoaded(true);
        resizeMap(map, host);
        // MapLibre often needs a second resize after first paint.
        resizeTimers.push(
          window.setTimeout(() => resizeMap(map, host), 50),
          window.setTimeout(() => resizeMap(map, host), 250),
          window.setTimeout(() => resizeMap(map, host), 800),
        );
        // If tiles still only occupy a sliver, fall back to Leaflet.
        resizeTimers.push(
          window.setTimeout(() => {
            if (disposed || !host) return;
            const canvas = host.querySelector("canvas") as HTMLCanvasElement | null;
            const hostH = host.getBoundingClientRect().height;
            const canvasH = canvas?.clientHeight ?? 0;
            if (hostH > 120 && canvasH > 0 && canvasH < hostH * 0.35) {
              onFailureRef.current?.();
            }
          }, 1200),
        );
      };
      map.addListener?.("load", markLoaded);
      map.on?.("load", markLoaded);
      loadTimer = window.setTimeout(markLoaded, 600);

      observer = new ResizeObserver(() => resizeMap(map, host));
      observer.observe(parent);
    }, 40);

    return () => {
      disposed = true;
      window.clearTimeout(startTimer);
      window.clearTimeout(loadTimer);
      resizeTimers.forEach((id) => window.clearTimeout(id));
      observer?.disconnect();
      setLoaded(false);
      layersRef.current.forEach((layer) => {
        try {
          layer.remove?.();
        } catch {
          /* ignore */
        }
      });
      layersRef.current = [];
      try {
        map?.remove?.();
      } catch {
        /* ignore */
      }
      mapRef.current = null;
      host?.remove();
    };
  }, [ready, mapId]);

  useEffect(() => {
    resizeMap(mapRef.current, hostRef.current?.querySelector(".mappls-sdk-host") as HTMLElement | null);
  }, [height, loaded]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !loaded || !map || !window.mappls) return;
    layersRef.current.forEach((layer) => layer.remove?.());
    layersRef.current = [];

    const addMarker = (point: GeoPoint, html: string, draggable = false) => {
      const marker = new window.mappls!.Marker({
        map,
        position: { lat: point.lat, lng: point.lng },
        draggable: draggable && interactive,
        html,
      });
      if (draggable) {
        marker.addListener?.("dragend", (event: unknown) => {
          const next = eventPoint(event);
          if (next) onSelectRef.current?.({ lat: next.lat, lng: next.lng });
        });
      }
      layersRef.current.push(marker);
    };

    if (pickup) {
      addMarker(pickup, `<span class="map-pin-dot pickup" title="Pickup"></span>`, interactive);
      if (typeof pickup.accuracy === "number" && pickup.accuracy > 0 && window.mappls.Circle) {
        const circle = new window.mappls.Circle({
          map,
          center: { lat: pickup.lat, lng: pickup.lng },
          radius: pickup.accuracy,
          fillColor: "#E65C24",
          fillOpacity: 0.08,
          strokeColor: "#E65C24",
        });
        layersRef.current.push(circle);
      }
    }
    if (destination) addMarker(destination, `<span class="map-pin-dot destination" title="Destination"></span>`);
    markers.forEach((item) => {
      addMarker(item.point, `<span class="map-pin-dot ${item.kind || "place"}" title="${item.label || ""}"></span>`);
    });
    if (route && route.length > 1 && window.mappls.addGeoJson) {
      const layer = window.mappls.addGeoJson({
        map,
        fitbounds: true,
        data: {
          type: "Feature",
          geometry: {
            type: "LineString",
            coordinates: route.map((point) => [point.lng, point.lat]),
          },
          properties: { stroke: "#E65C24", "stroke-width": 4 },
        },
      });
      if (layer) layersRef.current.push(layer);
    }
    const focus = center || pickup || destination;
    if (focus) {
      const signature = `${focus.lat.toFixed(6)}:${focus.lng.toFixed(6)}:${focus.accuracy ?? ""}:${mode}`;
      if (signature !== focusRef.current) {
        focusRef.current = signature;
        map.setCenter?.({ lat: focus.lat, lng: focus.lng });
        map.setZoom?.(zoomFor(focus, mode));
      }
    }
    resizeMap(map, hostRef.current?.querySelector(".mappls-sdk-host") as HTMLElement | null);
  }, [ready, loaded, pickup, destination, route, markers, center, interactive, mode]);

  return (
    <div
      ref={hostRef}
      className="mappls-canvas"
      style={{ height: "100%", width: "100%", minHeight: height }}
      aria-label="Map"
    />
  );
}
