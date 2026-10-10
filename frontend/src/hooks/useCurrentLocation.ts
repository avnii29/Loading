import { useCallback, useEffect, useState } from "react";
import { locationProvider } from "../services/location";
import type { GeoPoint } from "../services/location";
import type { LocationStatus } from "../services/location/LocationProvider";

function statusForAccuracy(point: GeoPoint, refining: boolean): string {
  if (point.accuracy == null || !Number.isFinite(point.accuracy)) {
    return refining
      ? "Location found. Device did not report an accuracy radius. Still refining…"
      : "Location found. Device did not report an accuracy radius.";
  }
  const meters = Math.round(point.accuracy);
  if (refining) {
    return `Improving fix… Device-reported accuracy ≈ ±${meters} m (estimate, not exact).`;
  }
  if (meters <= 25) {
    return `Strong device fix ≈ ±${meters} m (device-reported estimate). Confirm or nudge the pin to the door.`;
  }
  if (meters <= 100) {
    return `Device-reported accuracy ≈ ±${meters} m. Prefer outdoors / near a window, or adjust the pin.`;
  }
  return `Weak device fix ≈ ±${meters} m. Move outdoors if you can, then retry — or drop the pin manually.`;
}

export function useCurrentLocation() {
  const [status, setStatus] = useState<LocationStatus>("idle");
  const [message, setMessage] = useState("");
  const [coords, setCoords] = useState<GeoPoint | null>(null);

  const stop = useCallback(() => {
    locationProvider.stop();
    setStatus((current) => (current === "loading" || current === "refining" ? "success" : current));
  }, []);

  useEffect(() => () => locationProvider.stop(), []);

  const requestCurrentLocation = useCallback(async (onBetter?: (point: GeoPoint) => void) => {
    setStatus("loading");
    setMessage("Requesting a fresh high-accuracy fix from this device…");
    try {
      const point = await locationProvider.request((sample) => {
        setCoords(sample);
        setMessage(statusForAccuracy(sample, true));
        onBetter?.(sample);
      });
      setCoords(point);
      setStatus("refining");
      setMessage(statusForAccuracy(point, true));
      locationProvider.refine(point, (better) => {
        setCoords(better);
        setStatus("refining");
        setMessage(statusForAccuracy(better, true));
        onBetter?.(better);
      });
      window.setTimeout(() => {
        setStatus((current) => {
          if (current === "refining") {
            setMessage((msg) => msg.replace("Improving fix… ", "").replace(" Still refining…", ""));
            return "success";
          }
          return current;
        });
      }, 18500);
      return point;
    } catch (error) {
      locationProvider.stop();
      const err = error as Error & { code?: number | string };
      if (err.code === 1) setStatus("denied");
      else if (err.code === "unavailable") setStatus("unavailable");
      else setStatus("error");
      setMessage(err.message || "We couldn't get your location. Search or drop a pin instead.");
      throw error;
    }
  }, []);

  return {
    status,
    message,
    coords,
    requestCurrentLocation,
    stop,
    isLoading: status === "loading" || status === "refining",
  };
}
