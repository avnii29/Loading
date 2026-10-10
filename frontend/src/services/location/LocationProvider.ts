import type { GeoPoint } from "./types";

export type LocationStatus = "idle" | "loading" | "refining" | "success" | "denied" | "error" | "unavailable";

/** High-accuracy request options — not a guarantee of centimetre GPS. */
const ACQUIRE_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  timeout: 25000,
  maximumAge: 0,
};

const REFINE_OPTIONS: PositionOptions = {
  enableHighAccuracy: true,
  timeout: 20000,
  maximumAge: 0,
};

const ACQUIRE_MAX_MS = 22000;
const TARGET_ACCURACY_M = 25;
const ACCEPTABLE_ACCURACY_M = 80;
const MIN_SAMPLES_BEFORE_ACCEPT = 2;
const REFINE_MS = 18000;
const USEFUL_ACCURACY_M = 20;

function readPoint(pos: GeolocationPosition): GeoPoint {
  const accuracy = pos.coords.accuracy;
  return {
    lat: pos.coords.latitude,
    lng: pos.coords.longitude,
    ...(Number.isFinite(accuracy) ? { accuracy } : {}),
    capturedAt: new Date(pos.timestamp || Date.now()).toISOString(),
    fresh: true,
  };
}

function mapError(error: GeolocationPositionError) {
  const mapped = new Error(
    error.code === 1
      ? "Location permission denied. Enable location for this site in your browser settings, or search / drop a pin."
      : error.code === 3
        ? "Location request timed out. Move outdoors or near a window, then try again — or search / drop a pin."
        : "This device could not determine a location. Check that Location Services are on, then try again.",
  );
  (mapped as Error & { code: number }).code = error.code;
  return mapped;
}

function isBetter(candidate: GeoPoint, current: GeoPoint | null): boolean {
  if (!current) return true;
  const next = candidate.accuracy ?? Number.POSITIVE_INFINITY;
  const prev = current.accuracy ?? Number.POSITIVE_INFINITY;
  if (next < prev) return true;
  if (next === prev) {
    // Prefer a newer sample when accuracy ties.
    return (candidate.capturedAt || "") > (current.capturedAt || "");
  }
  return false;
}

export class BrowserLocationProvider {
  private watchId: number | null = null;
  private refineTimer = 0;

  stop() {
    if (this.watchId != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(this.watchId);
    }
    this.watchId = null;
    if (this.refineTimer) {
      window.clearTimeout(this.refineTimer);
      this.refineTimer = 0;
    }
  }

  /**
   * Collect multiple high-accuracy samples and keep the best device-reported fix.
   * Browser geolocation remains an estimate — this maximises quality, it does not invent precision.
   */
  async request(onSample?: (point: GeoPoint) => void): Promise<GeoPoint> {
    if (!window.isSecureContext) {
      const err = new Error("Location needs HTTPS or localhost. Search or drop a pin instead.");
      (err as Error & { code: string }).code = "unavailable";
      throw err;
    }
    if (!navigator.geolocation) {
      const err = new Error("Location is unavailable in this browser. Search or drop a pin instead.");
      (err as Error & { code: string }).code = "unavailable";
      throw err;
    }

    if (navigator.permissions?.query) {
      try {
        const permission = await navigator.permissions.query({ name: "geolocation" as PermissionName });
        if (permission.state === "denied") {
          const err = new Error(
            "Location permission denied. Enable location for this site in your browser settings, or search / drop a pin.",
          );
          (err as Error & { code: number }).code = 1;
          throw err;
        }
      } catch (error) {
        if ((error as Error & { code?: number }).code === 1) throw error;
        // permissions.query is optional — continue to getCurrentPosition / watch.
      }
    }

    this.stop();

    return new Promise((resolve, reject) => {
      let best: GeoPoint | null = null;
      let samples = 0;
      let settled = false;
      const started = Date.now();

      const finish = (point: GeoPoint) => {
        if (settled) return;
        settled = true;
        this.stop();
        resolve(point);
      };

      const fail = (error: GeolocationPositionError) => {
        if (settled) return;
        // If we already have a usable sample, return it instead of failing on a late watch error.
        if (best && (best.accuracy == null || best.accuracy <= ACCEPTABLE_ACCURACY_M * 2)) {
          finish(best);
          return;
        }
        settled = true;
        this.stop();
        reject(mapError(error));
      };

      const consider = (pos: GeolocationPosition) => {
        const point = readPoint(pos);
        samples += 1;
        if (isBetter(point, best)) {
          best = point;
          onSample?.(point);
        }
        const accuracy = best?.accuracy ?? Number.POSITIVE_INFINITY;
        const elapsed = Date.now() - started;
        if (accuracy <= TARGET_ACCURACY_M && samples >= 1) {
          finish(best!);
          return;
        }
        if (accuracy <= ACCEPTABLE_ACCURACY_M && samples >= MIN_SAMPLES_BEFORE_ACCEPT && elapsed >= 6000) {
          finish(best!);
          return;
        }
        if (elapsed >= ACQUIRE_MAX_MS && best) {
          finish(best);
        }
      };

      // Seed with one fresh getCurrentPosition, then improve via watch.
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          consider(pos);
          if (settled) return;
          this.watchId = navigator.geolocation.watchPosition(consider, fail, ACQUIRE_OPTIONS);
          this.refineTimer = window.setTimeout(() => {
            if (best) finish(best);
            else {
              settled = true;
              this.stop();
              reject(
                mapError({
                  code: 3,
                  message: "Timeout",
                  PERMISSION_DENIED: 1,
                  POSITION_UNAVAILABLE: 2,
                  TIMEOUT: 3,
                } as GeolocationPositionError),
              );
            }
          }, ACQUIRE_MAX_MS);
        },
        (error) => {
          // Still try watch — some browsers fail getCurrentPosition but succeed on watch.
          this.watchId = navigator.geolocation.watchPosition(consider, fail, ACQUIRE_OPTIONS);
          this.refineTimer = window.setTimeout(() => {
            if (best) finish(best);
            else {
              settled = true;
              this.stop();
              reject(mapError(error));
            }
          }, ACQUIRE_MAX_MS);
        },
        ACQUIRE_OPTIONS,
      );
    });
  }

  /**
   * Continuous device watch for an active job. Caller must stop() when the job ends.
   * Does not invent movement — only forwards Geolocation API samples.
   */
  watch(onPoint: (point: GeoPoint) => void, onError?: (error: Error) => void) {
    this.stop();
    if (!navigator.geolocation || !window.isSecureContext) {
      onError?.(new Error("Location is unavailable on this device or browser."));
      return;
    }
    this.watchId = navigator.geolocation.watchPosition(
      (pos) => onPoint(readPoint(pos)),
      (error) => onError?.(mapError(error)),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
    );
  }

  /**
   * After an explicit user request, listen briefly for a tighter device fix.
   * The caller must call stop() when the user moves the pin or the view unmounts.
   */
  refine(seed: GeoPoint, onBetter: (point: GeoPoint) => void) {
    this.stop();
    if (!navigator.geolocation || !window.isSecureContext) return;
    let best = seed;
    const started = Date.now();
    const finish = () => this.stop();
    this.watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const point = readPoint(pos);
        if (isBetter(point, best)) {
          best = point;
          onBetter(point);
        }
        const accuracy = best.accuracy ?? Number.POSITIVE_INFINITY;
        if (accuracy <= USEFUL_ACCURACY_M || Date.now() - started >= REFINE_MS) finish();
      },
      finish,
      REFINE_OPTIONS,
    );
    this.refineTimer = window.setTimeout(finish, REFINE_MS);
  }
}
