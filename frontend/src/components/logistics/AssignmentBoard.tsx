import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAssignments, markArrived, verifyHandoff, type LogisticsAssignmentRow } from "../../services/logistics";
import { getDonation, addQualityCheck } from "../../services/donations";
import { readApiError } from "../../services/auth";
import { useCurrentLocation } from "../../hooks/useCurrentLocation";
import { googleMapsDirectionsUrl } from "../../services/mapsLinks";
import { destinationOptions, proposeDestination, type DestinationOption } from "../../services/destinations";
import { LiveMissionMap } from "../map/LiveMissionMap";
import { Button } from "../ui/Button";
import { Input } from "../ui/Field";
import { FoodChecks, rowsFor } from "../food/FoodChecks";
import { EmptyState } from "../ui/States";
import { useJobLocationPublisher } from "../../hooks/useJobLocationPublisher";
import { donationDetailPath } from "../../constants/roles";
import { useAuth } from "../../providers/AuthProvider";
import { UserRole, type Donation } from "../../types/models";

/**
 * Active volunteer/driver assignments with OTP verify + pickup quality record.
 * Never marks complete locally — only after server OTP / quality responses.
 */
export function AssignmentBoard() {
  const { user } = useAuth();
  const gps = useCurrentLocation();
  const [rows, setRows] = useState<LogisticsAssignmentRow[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [arrivedNote, setArrivedNote] = useState("");
  const [otp, setOtp] = useState<Record<string, string>>({});
  const [quality, setQuality] = useState<Record<string, Record<string, string>>>({});
  const [detail, setDetail] = useState<Record<string, Donation | null>>({});
  const [options, setOptions] = useState<Record<string, { note: string; preferred_name: string | null; preferred_in_shortlist: boolean; options: DestinationOption[] }>>({});
  const [proposed, setProposed] = useState<Record<string, string>>({});
  const trackingId = rows.find((row) => ["ACCEPTED", "EN_ROUTE"].includes(row.status))?.id ?? null;
  useJobLocationPublisher(trackingId);

  useEffect(() => {
    void gps.requestCurrentLocation().catch(() => {
      /* optional — directions still offer Google Maps from pickup */
    });
  }, []);

  async function refresh() {
    try {
      const next = await listAssignments();
      setRows(next.filter((row) => ["ACCEPTED", "EN_ROUTE"].includes(row.status)));
      setError("");
    } catch (err) {
      setError(readApiError(err));
    }
  }

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => void refresh(), 8000);
    const onAssigned = () => void refresh();
    window.addEventListener("anuvartan-assignment-refresh", onAssigned);
    return () => {
      window.clearInterval(poll);
      window.removeEventListener("anuvartan-assignment-refresh", onAssigned);
    };
  }, []);

  async function loadDetail(donationId: string) {
    if (detail[donationId]) return;
    try {
      const row = await getDonation(donationId);
      setDetail((prev) => ({ ...prev, [donationId]: row }));
    } catch {
      setDetail((prev) => ({ ...prev, [donationId]: null }));
    }
  }

  async function onVerify(donationId: string) {
    const code = (otp[donationId] || "").trim();
    if (code.length < 4) {
      setError("Enter the donor’s pickup OTP.");
      return;
    }
    setBusy(`otp-${donationId}`);
    setError("");
    try {
      await verifyHandoff(donationId, "PICKUP", code);
      await refresh();
      const row = await getDonation(donationId);
      setDetail((prev) => ({ ...prev, [donationId]: row }));
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy("");
    }
  }

  async function onArrive(donationId: string) {
    setBusy(`arr-${donationId}`);
    setError("");
    try {
      const result = await markArrived(donationId);
      setArrivedNote(result.message);
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy("");
    }
  }

  async function onQuality(donationId: string) {
    const answers = quality[donationId] || {};
    if (!rowsFor("pickup").every((row) => answers[row.key])) {
      setError("Answer every pickup check. Not checked and Unknown stay unresolved.");
      return;
    }
    setBusy(`q-${donationId}`);
    setError("");
    try {
      const row = await addQualityCheck(donationId, {
        result: "PENDING",
        stage: "PICKUP",
        responses: answers,
        notes: "Pickup observation",
      });
      setDetail((prev) => ({ ...prev, [donationId]: row }));
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy("");
    }
  }

  if (!rows.length) {
    return (
      <EmptyState
        title="No active assignment yet"
        body="Browse available pickup requests to get started."
      />
    );
  }

  return (
    <div className="assignment-board stack">
      {error ? <p className="field-error">{error}</p> : null}
      {arrivedNote ? <p className="field-hint">{arrivedNote}</p> : null}
      {rows.map((row) => {
        const donation = detail[row.donation_id];
        const pickupDone = donation?.status === "IN_TRANSIT" || donation?.history?.some((h) => h.to_status === "IN_TRANSIT");
        const hasPickupQuality = donation?.quality_checks?.some((q) => q.stage === "PICKUP");
        return (
          <article key={row.id} className="surface-card stack assignment-card">
            <p className="eyebrow">
              {row.priority_class || "P?"} · {row.status}
            </p>
            <h3>
              {row.quantity} {row.unit} · {row.category}
            </h3>
            <p className="muted">{row.pickup_address || "Address unlocked after accept"}</p>
            {row.pickup_schedule ? <p className="field-hint">Pickup schedule: {row.pickup_schedule}</p> : null}
            <p className="field-hint">Ref {row.reference_code}</p>
            <div className="row-actions">
              <Button type="button" variant="secondary" onClick={() => void loadDetail(row.donation_id)}>
                Load handoff
              </Button>
              <Link to={donationDetailPath(user?.role || UserRole.VOLUNTEER, row.donation_id)} className="btn btn-ghost">
                Open donation
              </Link>
            </div>

            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                void destinationOptions(row.donation_id).then((next) =>
                  setOptions((prev) => ({ ...prev, [row.donation_id]: next })),
                )
              }
            >
              Destination options
            </Button>
            {options[row.donation_id] ? (
              <div className="stack">
                <p className="field-hint">{options[row.donation_id].note}</p>
                {options[row.donation_id].preferred_name ? (
                  <p className="field-hint">
                    Donor preference: {options[row.donation_id].preferred_name}
                    {options[row.donation_id].preferred_in_shortlist ? "" : " (not in these two closest listings)"}
                  </p>
                ) : (
                  <p className="field-hint">The donor has not chosen a preference.</p>
                )}
                {options[row.donation_id].options.map((item) => (
                  <label key={item.id} className="surface-card">
                    <input
                      type="radio"
                      name={`dest-${row.donation_id}`}
                      checked={proposed[row.donation_id] === item.id}
                      onChange={() => {
                        setProposed((prev) => ({ ...prev, [row.donation_id]: item.id }));
                        const reason = item.donor_preferred ? "donor_preference" : "closer_eligible";
                        void proposeDestination(row.donation_id, item.id, reason);
                      }}
                    />{" "}
                    <strong>{item.name}</strong>
                    <span className="muted">
                      {" "}
                      · {item.locality || "Locality on file"} · about {item.distance_km} km straight-line
                      {item.donor_preferred ? " · donor preference" : ""}
                    </span>
                  </label>
                ))}
                <p className="field-hint">Selecting a listing proposes it. The organisation has not confirmed receipt.</p>
              </div>
            ) : null}
            {row.pickup_latitude != null && row.pickup_longitude != null ? (
              <LiveMissionMap
                pickup={{ lat: row.pickup_latitude, lng: row.pickup_longitude }}
                volunteer={gps.coords}
                destination={
                  options[row.donation_id]?.options.find((item) => item.id === proposed[row.donation_id])?.latitude !=
                  null
                    ? {
                        lat: options[row.donation_id].options.find((item) => item.id === proposed[row.donation_id])!
                          .latitude as number,
                        lng: options[row.donation_id].options.find((item) => item.id === proposed[row.donation_id])!
                          .longitude as number,
                      }
                    : null
                }
                status={donation?.status}
                showDirections={false}
                height={280}
              />
            ) : null}
            {row.pickup_latitude != null && row.pickup_longitude != null ? (
              <a
                className="btn btn-secondary"
                href={googleMapsDirectionsUrl({
                  origin: gps.coords,
                  destination: { lat: row.pickup_latitude, lng: row.pickup_longitude },
                })}
                target="_blank"
                rel="noreferrer"
              >
                Navigate to pickup
              </a>
            ) : (
              <p className="field-hint">Pickup coordinates are missing, so navigation cannot be opened.</p>
            )}
            <p className="field-hint">
              Navigate to organisation stays unavailable until a destination is confirmed by the receiving organisation.
              A proposal is not confirmation.
            </p>

            {donation ? (
              <>
                {!pickupDone ? (
                  <div className="handoff-box stack">
                    <p className="eyebrow">Pickup OTP</p>
                    <p className="muted">Ask the donor for their in-app code. Verification is server-side only.</p>
                    <Input
                      label="6-digit code"
                      inputMode="numeric"
                      maxLength={6}
                      value={otp[row.donation_id] || ""}
                      onChange={(e) =>
                        setOtp((prev) => ({
                          ...prev,
                          [row.donation_id]: e.target.value.replace(/\D/g, "").slice(0, 6),
                        }))
                      }
                    />
                    <Button
                      type="button"
                      onClick={() => void onVerify(row.donation_id)}
                      disabled={busy === `otp-${row.donation_id}`}
                    >
                      {busy === `otp-${row.donation_id}` ? "Verifying…" : "Verify pickup"}
                    </Button>
                  </div>
                ) : (
                  <div className="handoff-box stack">
                    <p className="ok">Pickup verified — donation is in transit.</p>
                    <p className="muted">
                      When you reach the organisation, mark arrival. That creates their receipt code. You will not see
                      the code.
                    </p>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => void onArrive(row.donation_id)}
                      disabled={busy === `arr-${row.donation_id}`}
                    >
                      {busy === `arr-${row.donation_id}` ? "Sending…" : "I've reached the organisation"}
                    </Button>
                  </div>
                )}

                {!hasPickupQuality ? (
                  <div className="handoff-box stack">
                    <FoodChecks
                      role="pickup"
                      value={quality[row.donation_id] || {}}
                      onChange={(next) => setQuality((prev) => ({ ...prev, [row.donation_id]: next }))}
                    />
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => void onQuality(row.donation_id)}
                      disabled={busy === `q-${row.donation_id}`}
                    >
                      {busy === `q-${row.donation_id}` ? "Saving…" : "Record pickup check"}
                    </Button>
                  </div>
                ) : (
                  <p className="field-hint">Pickup quality already recorded.</p>
                )}
              </>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
