import { useState } from "react";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../../components/ui/States";
import { Button } from "../../components/ui/Button";
import { MapCanvas } from "../../components/map/MapCanvas";
import { useCurrentLocation } from "../../hooks/useCurrentLocation";
import { listOrganizations } from "../../services/organizations";
import { readApiError } from "../../services/auth";
import type { Organization } from "../../types/models";

export function Organizations() {
  const gps = useCurrentLocation();
  const [rows, setRows] = useState<Organization[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState<string | null>(null);

  async function load(coords?: { lat: number; lng: number }) {
    setError("");
    setLoading(true);
    try {
      const next = await listOrganizations(coords);
      setRows(next);
      setActive(next[0]?.id ?? null);
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setLoading(false);
    }
  }

  async function nearMe() {
    try {
      const point = await gps.requestCurrentLocation();
      await load({ lat: point.lat, lng: point.lng });
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const selected = rows?.find((row) => row.id === active) ?? null;
  const markers = (rows ?? [])
    .filter((row) => row.latitude != null && row.longitude != null)
    .map((row) => ({
      id: row.id,
      point: { lat: Number(row.latitude), lng: Number(row.longitude) },
    }));

  return (
    <div>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">Destinations</p>
          <h1>Organisations near you</h1>
          <p className="muted">
            Verified Anuvartan organisations and published directory facilities within about 40 km. A directory pin is the
            published locality, not a confirmed door.
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={nearMe} disabled={gps.isLoading}>
          {gps.isLoading ? "Locating…" : "Use my location"}
        </Button>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {loading ? <LoadingState /> : null}
      {!rows && !error && !loading ? (
        <EmptyState
          title="Use your location to see destinations"
          body="We only list verified organisations near the coordinates you share. Nothing from another city is filled in."
        />
      ) : null}
      {rows && rows.length === 0 ? (
        <EmptyState
          title="No eligible destinations are currently available in this area."
          body="Only verified organisations with real coordinates inside about 40 km are listed. Nothing from another city is substituted."
        />
      ) : null}
      {rows && rows.length > 0 ? (
        <div className="discover-layout" style={{ marginTop: 20 }}>
          <div className="org-list">
            {rows.map((org) => (
              <button
                key={org.id}
                type="button"
                className={`org-card ${active === org.id ? "is-on" : ""}`}
                onClick={() => setActive(org.id)}
              >
                <div className="org-mark" aria-hidden>
                  {org.name.slice(0, 1)}
                </div>
                <div>
                  <strong>{org.name}</strong>
                  <p className="muted">{org.city || org.address || "Location to be confirmed"}</p>
                  {org.approximate ? <p className="field-hint">Approximate area from the published address.</p> : null}
                  {org.description ? <p className="muted">{org.description}</p> : null}
                  {org.accepted_categories?.length ? (
                    <p className="muted">{org.accepted_categories.join(" · ")}</p>
                  ) : null}
                </div>
                <div>
                  <StatusBadge
                    label={org.verification_status === "DIRECTORY" ? "directory" : org.verification_status.toLowerCase()}
                    tone={org.verification_status === "VERIFIED" ? "ok" : "neutral"}
                  />
                  {org.distance_km != null ? <p className="muted">{org.distance_km} km straight-line</p> : null}
                  <p className="muted">{org.intake_status.toLowerCase()}</p>
                </div>
              </button>
            ))}
          </div>
          <div className="loc-box">
            {markers.length ? (
              <MapCanvas
                mode="known"
                pickup={
                  selected?.latitude != null && selected?.longitude != null
                    ? { lat: Number(selected.latitude), lng: Number(selected.longitude) }
                    : markers[0].point
                }
                markers={markers.map((item) => ({ ...item, kind: "organisation" as const }))}
                height={520}
              />
            ) : (
              <div className="loc-placeholder">
                Organisations will appear on the map once they have real coordinates.
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
