/** Device-reported accuracy UX helpers — not physical guarantees. */

export type AccuracyBand = "high" | "moderate" | "low" | "unavailable";

/** Configurable application thresholds (metres). */
export const ACCURACY_HIGH_MAX_M = 25;
export const ACCURACY_MODERATE_MAX_M = 100;

export function accuracyBand(meters?: number | null): AccuracyBand {
  if (meters == null || !Number.isFinite(meters) || meters < 0) return "unavailable";
  if (meters <= ACCURACY_HIGH_MAX_M) return "high";
  if (meters <= ACCURACY_MODERATE_MAX_M) return "moderate";
  return "low";
}

export function accuracyLabel(meters?: number | null): string {
  const band = accuracyBand(meters);
  if (band === "unavailable") return "Device did not report an accuracy radius.";
  const rounded = Math.round(meters as number);
  if (band === "high") {
    return `Device-reported accuracy ≈ ${rounded} m (high — still an estimate).`;
  }
  if (band === "moderate") {
    return `Device-reported accuracy ≈ ${rounded} m (moderate). Adjust the pin if needed.`;
  }
  return `Device-reported accuracy ≈ ${rounded} m (low). Prefer adjusting the pin or retrying outdoors.`;
}

export function mapLocationSource(
  source?: "device" | "search" | "map" | "typed" | null,
): string {
  if (source === "device") return "DEVICE_GEOLOCATION";
  if (source === "search") return "MAPPLS_SEARCH";
  if (source === "map") return "MANUAL_PIN";
  if (source === "typed") return "MANUAL_ADDRESS";
  return "MANUAL_ADDRESS";
}
