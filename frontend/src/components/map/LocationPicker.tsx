import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Crosshair, Home, MapPinned } from "lucide-react";
import { MapCanvas } from "./MapCanvas";
import { Button } from "../ui/Button";
import { Input } from "../ui/Field";
import { useCurrentLocation } from "../../hooks/useCurrentLocation";
import { fetchLocationConfig, reverseGeocode } from "../../services/location/api";
import { DistanceService, geocoderProvider } from "../../services/location";
import type { GeoPoint, LocationConfig, LocationResult, LocationSource } from "../../services/location/types";
import { accuracyLabel } from "../../services/location/accuracy";
import { readApiError } from "../../services/auth";
import { googleMapsPlaceUrl } from "../../services/mapsLinks";

export type ConfirmedLocation = {
  address: string;
  point: GeoPoint | null;
  mappls_pin?: string | null;
  provider?: string;
  precision?: string | null;
  source?: LocationSource;
  approximate: boolean;
  confirmed: boolean;
  landmark?: string;
  pincode?: string;
};

type Props = {
  value: ConfirmedLocation;
  onChange: (next: ConfirmedLocation) => void;
  height?: number;
  /** Screenshot B: controls left, map right with house pin. */
  layout?: "default" | "pickup";
};

function kindLabel(kind?: string | null) {
  const value = (kind || "").toUpperCase();
  if (value.includes("PIN")) return "PIN";
  if (value.includes("CITY") || value.includes("VILLAGE")) return "City";
  if (value.includes("STREET") || value.includes("HOUSE")) return "Street";
  if (value.includes("LOCAL") || value.includes("AREA")) return "Area";
  if (value.includes("POI") || value.includes("PLACE")) return "Place";
  return "Place";
}

function sourceLabel(source?: LocationSource) {
  if (source === "device") return "Fresh device location (not a saved address). Confirm if this is the pickup point.";
  if (source === "search") return "Search result — adjust the pin if the door is different.";
  if (source === "map") return "Manually selected pin — GPS accuracy no longer applies.";
  if (source === "typed") return "Typed address — drop a pin for coordinates when possible.";
  return "Search for a place or use Locate me to set your pickup point.";
}

function metersBetween(a: GeoPoint, b: GeoPoint) {
  const toRad = (value: number) => (value * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.min(1, Math.sqrt(h)));
}

export function LocationPicker({ value, onChange, height = 360, layout = "default" }: Props) {
  const gps = useCurrentLocation();
  const [query, setQuery] = useState(value.address);
  const [results, setResults] = useState<LocationResult[]>([]);
  const [active, setActive] = useState(0);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [config, setConfig] = useState<LocationConfig | null>(null);
  const [searching, setSearching] = useState(false);
  const [gpsPrompt, setGpsPrompt] = useState<GeoPoint | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const quietQuery = useRef(false);
  const skipInitialSearch = useRef(Boolean(value.address));
  const userMoved = useRef(false);
  const ticket = useRef(0);
  const pointRef = useRef(value.point);
  const biasRef = useRef(value.point);
  const valueRef = useRef(value);
  pointRef.current = value.point;
  biasRef.current = value.point;
  valueRef.current = value;
  const pincodeTyped = /^\d{6}$/.test(query.trim());
  const isPickup = layout === "pickup";

  useEffect(() => {
    fetchLocationConfig()
      .then(setConfig)
      .catch(() => setConfig(null));
  }, []);

  useEffect(() => () => gps.stop(), [gps.stop]);

  useEffect(() => {
    if (skipInitialSearch.current) {
      skipInitialSearch.current = false;
      return;
    }
    if (quietQuery.current) {
      quietQuery.current = false;
      setResults([]);
      return;
    }
    if (query.trim().length < 3 || (config && !config.search)) {
      setResults([]);
      setActive(0);
      return;
    }
    const timer = window.setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setSearching(true);
      setError("");
      try {
        const rows = await geocoderProvider.search(query, biasRef.current || undefined, controller.signal);
        setResults(rows.map((row) => row.result));
        setActive(0);
        if (!rows.length) setStatus("No location results.");
      } catch (err) {
        if (
          (err as Error).name === "CanceledError" ||
          (err as Error).name === "AbortError" ||
          (err as { code?: string }).code === "ERR_CANCELED"
        ) {
          return;
        }
        setError((err as Error).message || readApiError(err));
      } finally {
        setSearching(false);
      }
    }, 320);
    return () => window.clearTimeout(timer);
  }, [query, config]);

  const mapPoint = useMemo(() => {
    if (!value.point) return null;
    if (value.source === "device") return value.point;
    return { lat: value.point.lat, lng: value.point.lng };
  }, [value.point, value.source]);

  const mode = useMemo(() => {
    if (value.point && value.approximate) return "approximate" as const;
    if (value.point) return "known" as const;
    return "unknown" as const;
  }, [value]);

  function rememberQuery(next: string) {
    quietQuery.current = true;
    setQuery(next);
  }

  function takeOver() {
    userMoved.current = true;
    gps.stop();
  }

  async function applyPoint(point: GeoPoint, extras?: Partial<ConfirmedLocation>, reverse = true) {
    const id = ++ticket.current;
    const current = valueRef.current;
    const source = extras?.source ?? "map";
    const device = source === "device";
    const nextPoint: GeoPoint = {
      lat: point.lat,
      lng: point.lng,
      ...(device && point.accuracy != null && Number.isFinite(point.accuracy) ? { accuracy: point.accuracy } : {}),
      ...(device && point.capturedAt ? { capturedAt: point.capturedAt } : {}),
    };
    let address = extras?.address ?? current.address;
    let pin = extras?.mappls_pin ?? current.mappls_pin ?? null;
    let precision = extras?.precision ?? current.precision ?? null;
    const approximate = extras?.approximate ?? false;
    const provider = extras?.provider ?? (device ? "gps" : "map");
    const commit = () => {
      onChange({
        address,
        point: nextPoint,
        mappls_pin: pin,
        provider,
        precision,
        source,
        approximate,
        confirmed: false,
        landmark: current.landmark,
        pincode: current.pincode,
      });
    };
    setError("");
    commit();
    if (address) rememberQuery(address);
    setResults([]);
    if (!reverse) {
      if (device && nextPoint.accuracy != null) {
        setStatus(`Location found. Accuracy: ±${Math.round(nextPoint.accuracy)} m`);
      } else if (address) {
        setStatus(source === "map" ? "Pin moved. Confirm this pickup point." : "Location found");
      }
      return;
    }
    setStatus(device ? "Finding the address for this location…" : "Finding the address…");
    const row = await reverseGeocode(nextPoint).catch(() => null);
    if (id !== ticket.current) return;
    if (row?.formatted_address) {
      address = row.formatted_address;
      rememberQuery(address);
    }
    if (row?.mappls_pin) pin = row.mappls_pin;
    if (row?.precision) precision = row.precision;
    commit();
    if (device && nextPoint.accuracy != null) {
      setStatus(`Location found. Accuracy: ±${Math.round(nextPoint.accuracy)} m`);
    } else if (address) {
      setStatus(source === "map" ? "House pin moved. Confirm this pickup point." : "Location found");
    } else {
      setStatus("Pin placed. The address could not be resolved, but these coordinates are kept.");
    }
  }

  async function locateMe() {
    userMoved.current = false;
    setError("");
    setStatus("Getting a fresh high-accuracy fix from this device…");
    try {
      let lastReverseAt = 0;
      const point = await gps.requestCurrentLocation((better) => {
        if (userMoved.current) return;
        const previous = pointRef.current;
        const moved = previous ? metersBetween(previous, better) > 12 : true;
        const accuracyImproved =
          previous?.accuracy != null &&
          better.accuracy != null &&
          better.accuracy + 5 < previous.accuracy;
        const shouldReverse = moved && (accuracyImproved || Date.now() - lastReverseAt > 4000);
        if (shouldReverse) lastReverseAt = Date.now();
        void applyPoint(better, { source: "device", provider: "gps", approximate: false }, shouldReverse);
      });
      if (!userMoved.current) {
        await applyPoint(point, { source: "device", provider: "gps", approximate: false }, true);
        const meters = point.accuracy != null ? Math.round(point.accuracy) : null;
        setStatus(
          meters != null
            ? `Current location set (device-reported ≈ ±${meters} m). Confirm the pin or nudge it to the exact pickup point.`
            : "Current location set. Confirm the pin or nudge it to the exact pickup point.",
        );
      }
    } catch (err) {
      setStatus("");
      setError((err as Error).message);
    }
  }

  async function choose(result: LocationResult) {
    takeOver();
    const id = ++ticket.current;
    abortRef.current?.abort();
    setError("");
    const resolved = await geocoderProvider.resolve(result).catch(() => result);
    if (id !== ticket.current) return;
    const hasPoint = resolved.latitude != null && resolved.longitude != null;
    const approximate = Boolean(resolved.approximate || pincodeTyped);
    const digits = query.trim().match(/^\d{6}$/)?.[0];
    onChange({
      address: resolved.formatted_address,
      point: hasPoint ? { lat: resolved.latitude as number, lng: resolved.longitude as number } : null,
      mappls_pin: resolved.mappls_pin,
      provider: resolved.provider,
      precision: resolved.precision,
      source: "search",
      approximate,
      confirmed: false,
      landmark: value.landmark,
      pincode: digits || value.pincode,
    });
    rememberQuery(resolved.formatted_address);
    setResults([]);
    setStatus(
      approximate
        ? "This is an area, not an exact door. Move the house pin to the pickup point."
        : hasPoint
          ? "Confirm this pickup point."
          : "Address selected. Drop a pin on the map if the exact point is missing.",
    );
  }

  function onSearchKey(event: KeyboardEvent<HTMLInputElement>) {
    if (!results.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => (index - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      const row = results[active];
      if (row) void choose(row);
    } else if (event.key === "Escape") {
      setResults([]);
    }
  }

  const deviceAccuracy = value.source === "device" && value.point?.accuracy != null ? Math.round(value.point.accuracy) : null;
  const manualPin = value.source === "map" || value.source === "search" || value.source === "typed";
  const deviceGpsOverlay =
    gps.coords && manualPin && value.point
      ? gps.coords
      : value.source === "device" && value.point?.accuracy != null
        ? null
        : gps.coords && !value.point
          ? gps.coords
          : null;

  // Dil Se Daan: when GPS is far from the house pin, offer update — never auto-move.
  useEffect(() => {
    if (!gps.coords || !value.point || !manualPin) {
      setGpsPrompt(null);
      return;
    }
    const dist = DistanceService.meters(value.point, gps.coords);
    setGpsPrompt(dist > 80 ? gps.coords : null);
  }, [gps.coords?.lat, gps.coords?.lng, gps.coords?.accuracy, value.point?.lat, value.point?.lng, manualPin]);

  const controls = (
    <aside className="location-card">
      <p className="eyebrow">{isPickup ? "Confirm pickup" : "Pickup location"}</p>
      <h3>{value.address || (value.confirmed ? "Confirmed" : value.point ? "Pinned" : "Not set yet")}</h3>
      <p className="muted">{status || gps.message || sourceLabel(value.source)}</p>
      {deviceAccuracy != null ? <p className="field-hint">{accuracyLabel(deviceAccuracy)}</p> : null}
      {value.source === "device" && value.point?.capturedAt ? (
        <p className="field-hint">Acquired {new Date(value.point.capturedAt).toLocaleString()}</p>
      ) : null}
      {value.confirmed ? <p className="field-hint">Pickup point confirmed for this donation.</p> : null}
      {value.approximate ? (
        <p className="field-hint">Approximate area. Move the house pin to the actual pickup point.</p>
      ) : null}

      <Button
        type="button"
        className="locate-primary"
        onClick={() => void locateMe()}
        disabled={gps.status === "loading" || gps.status === "refining"}
      >
        <Crosshair size={16} aria-hidden />
        {gps.status === "loading" || gps.status === "refining" ? "Finding your location…" : "Use my current location"}
      </Button>
      {gpsPrompt ? (
        <div className="gps-prompt">
          <p className="field-hint">
            More precise GPS is available (~{gpsPrompt.accuracy != null ? `±${Math.round(gpsPrompt.accuracy)} m` : "fresh"}
            ), about {Math.round(DistanceService.meters(value.point!, gpsPrompt))} m from your pin.
          </p>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setGpsPrompt(null);
              void applyPoint(gpsPrompt, { source: "device", provider: "gps", approximate: false }, true);
            }}
          >
            Use GPS instead
          </Button>
        </div>
      ) : null}

      <div className="pin-fallback">
        <p className="field-hint">
          Or enter a 6-digit PIN. A PIN is a locality — place the house pin on the real door or gate after lookup.
        </p>
        <Input
          id="pickup-pincode"
          label="PIN code"
          inputMode="numeric"
          maxLength={6}
          value={value.pincode || ""}
          onChange={(e) => {
            const digits = e.target.value.replace(/\D/g, "").slice(0, 6);
            takeOver();
            onChange({ ...value, pincode: digits, confirmed: false });
            if (digits.length === 6) setQuery(digits);
          }}
          placeholder="e.g. 500028"
        />
      </div>

      <Input
        id="pickup-search"
        label="Search place, street or landmark"
        value={query}
        onKeyDown={onSearchKey}
        onChange={(e) => {
          takeOver();
          setQuery(e.target.value);
          onChange({
            ...value,
            address: e.target.value,
            source: value.point ? value.source : "typed",
            confirmed: false,
          });
        }}
        placeholder="Place, landmark, street or PIN"
        role="combobox"
        aria-expanded={results.length > 0}
        aria-controls="pickup-results"
        aria-autocomplete="list"
      />
      {pincodeTyped ? <p className="field-hint">A PIN covers an area. Move the pin to the door or landmark.</p> : null}
      {searching ? <p className="muted">Searching…</p> : null}
      {results.length ? (
        <ul className="place-results" id="pickup-results" role="listbox">
          {results.map((row, index) => (
            <li key={`${row.mappls_pin || "place"}-${row.formatted_address}-${index}`}>
              <button
                type="button"
                role="option"
                aria-selected={index === active}
                className={index === active ? "is-active" : undefined}
                onMouseEnter={() => setActive(index)}
                onClick={() => void choose(row)}
              >
                <span className="place-kind">{kindLabel(row.kind)}</span>
                <strong>{row.name || row.formatted_address}</strong>
                <small>{row.formatted_address}</small>
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <Input
        id="pickup-landmark"
        label="Landmark / gate notes (optional)"
        value={value.landmark || ""}
        onChange={(e) => onChange({ ...value, landmark: e.target.value, confirmed: false })}
        placeholder="e.g. Apartment gate B, service entrance"
      />

      <div className="row-actions">
        <Button
          type="button"
          disabled={!value.address.trim() && !value.point}
          onClick={() =>
            onChange({
              ...value,
              confirmed: true,
              address: query.trim() || value.address,
            })
          }
        >
          Confirm this pickup point
        </Button>
        {value.point || value.address ? (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              document.getElementById("pickup-search")?.focus();
            }}
          >
            Change location
          </Button>
        ) : null}
      </div>
      {error ? <p className="field-error">{error}</p> : null}
      {value.mappls_pin ? <p className="muted">Mappls Pin {value.mappls_pin}</p> : null}
      {!config?.configured ? (
        <p className="field-hint">Address search is temporarily unavailable. You can still use GPS or drop a pin.</p>
      ) : null}
    </aside>
  );

  const map = (
    <div className="loc-box">
      {isPickup && mapPoint ? (
        <div className="map-house-hint" aria-hidden>
          <Home size={14} />
          <span>Drag the house pin to your door</span>
        </div>
      ) : null}
      <MapCanvas
        mode={mode}
        pickup={mapPoint}
        height={height}
        interactive
        showPickupBanner={isPickup && Boolean(mapPoint)}
        lockView={false}
        deviceGps={deviceGpsOverlay}
        onLocateMe={() => void locateMe()}
        emptyLabel="Use Locate me, a PIN, or search. This map will not assume a city."
        onSelect={(point) => {
          takeOver();
          void applyPoint(
            { lat: point.lat, lng: point.lng },
            { source: "map", provider: "map", mappls_pin: null, approximate: false },
            true,
          );
        }}
      />
      {value.point ? (
        <a
          className="map-external-link"
          href={googleMapsPlaceUrl(value.point)}
          target="_blank"
          rel="noreferrer"
        >
          <MapPinned size={14} aria-hidden /> Open pin in Maps
        </a>
      ) : null}
    </div>
  );

  return (
    <div className={`location-picker${isPickup ? " layout-pickup" : ""}`}>
      {isPickup ? (
        <>
          {controls}
          {map}
        </>
      ) : (
        <>
          {map}
          {controls}
        </>
      )}
    </div>
  );
}
