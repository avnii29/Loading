import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { Bike, MapPin } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../../components/ui/States";
import { MapCanvas } from "../../components/map/MapCanvas";
import { LiveMissionMap } from "../../components/map/LiveMissionMap";
import { cancelDonation, getDonation, refreshVerificationCode } from "../../services/donations";
import { getCollectorLocation, issueHandoff, type CollectorLocation } from "../../services/logistics";
import { listNotifications } from "../../services/notifications";
import { listOrganizations } from "../../services/organizations";
import { readApiError } from "../../services/auth";
import { accuracyLabel } from "../../services/location/accuracy";
import { TRACK_STAGES, categoryMeta, statusTone, trackIndex } from "../../constants/donations";
import { donationListPath } from "../../constants/roles";
import { useAuth } from "../../providers/AuthProvider";
import type { Donation, Organization } from "../../types/models";

type LocState = { verification_code?: string };

export function DonationDetail() {
  const { id } = useParams();
  const location = useLocation();
  const { user } = useAuth();
  const seeded = (location.state as LocState | null)?.verification_code;
  const [donation, setDonation] = useState<Donation | null>(null);
  const [destination, setDestination] = useState<Organization | null>(null);
  const [code, setCode] = useState(seeded || "");
  const [handoffCode, setHandoffCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [collector, setCollector] = useState<CollectorLocation | null>(null);

  useEffect(() => {
    if (!id) return;
    getDonation(id)
      .then(async (row) => {
        setDonation(row);
        if (!row.destination_id) {
          setDestination(null);
          return;
        }
        try {
          const orgs = await listOrganizations(
            row.pickup_latitude != null && row.pickup_longitude != null
              ? { lat: Number(row.pickup_latitude), lng: Number(row.pickup_longitude) }
              : undefined,
          );
          setDestination(orgs.find((item) => item.id === row.destination_id) || null);
        } catch {
          setDestination(null);
        }
      })
      .catch((err) => setError(readApiError(err)));
  }, [id]);

  useEffect(() => {
    if (!id || !donation?.assignee_name) return;
    let cancelled = false;
    const pull = () => {
      getCollectorLocation(id)
        .then((row) => {
          if (!cancelled) setCollector(row);
        })
        .catch(() => {
          if (!cancelled) setCollector({ available: false, freshness: "unavailable" });
        });
    };
    pull();
    const timer = window.setInterval(pull, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [id, donation?.assignee_name, donation?.status]);

  useEffect(() => {
    if (!donation || !user || (user.role !== "DONOR" && !donation.is_donor)) return;
    listNotifications()
      .then((rows) => {
        const note = rows.find((row) => row.entity_id === donation.id && /Pickup code: \d{6}/.test(row.body));
        const match = note?.body.match(/Pickup code: (\d{6})/);
        if (match) setHandoffCode(match[1]);
      })
      .catch(() => undefined);
  }, [donation?.id, donation?.is_donor, user?.id, user?.role]);

  if (error) return <ErrorState message={error} />;
  if (!donation) return <LoadingState />;

  const assigned = Boolean(donation.assignee_name);
  const deviceAccuracy =
    donation.location_accuracy_m != null &&
    (donation.location_source === "DEVICE_GEOLOCATION" || donation.location_source === "gps");
  const pickup =
    donation.pickup_latitude != null && donation.pickup_longitude != null
      ? {
          lat: Number(donation.pickup_latitude),
          lng: Number(donation.pickup_longitude),
          ...(deviceAccuracy ? { accuracy: Number(donation.location_accuracy_m) } : {}),
        }
      : null;
  const destPoint =
    destination?.latitude != null && destination?.longitude != null
      ? { lat: Number(destination.latitude), lng: Number(destination.longitude) }
      : null;
  const current = trackIndex(donation.status);
  const meta = categoryMeta(donation.category);

  async function rotate() {
    if (!donation) return;
    setBusy(true);
    try {
      const next = await refreshVerificationCode(donation.id);
      setCode(next.verification_code);
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function issuePickupOtp() {
    if (!donation) return;
    setBusy(true);
    setError("");
    try {
      const next = await issueHandoff(donation.id, "PICKUP");
      setHandoffCode(next.code);
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function onCancel() {
    if (!donation) return;
    setBusy(true);
    try {
      const next = await cancelDonation(donation.id);
      setDonation(next);
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="detail">
      <p className="eyebrow">
        {meta.label} · {donation.reference_code}
      </p>
      <div className="welcome-row">
        <div>
          <h1>
            {donation.quantity} {donation.unit}
          </h1>
          <p className="muted">{donation.description || donation.pickup_address || "Donation in progress"}</p>
        </div>
        <StatusBadge label={donation.status_label} tone={statusTone(donation.status)} />
      </div>

      <div className="track-layout" style={{ marginTop: 22 }}>
        <div className="loc-box stack">
          {pickup && destPoint ? (
            <LiveMissionMap
              pickup={pickup}
              destination={destPoint}
              status={donation.status}
              height={420}
              volunteer={
                collector?.available &&
                collector.freshness !== "stale" &&
                collector.latitude != null &&
                collector.longitude != null
                  ? {
                      lat: collector.latitude,
                      lng: collector.longitude,
                      ...(collector.accuracy_m != null ? { accuracy: collector.accuracy_m } : {}),
                    }
                  : null
              }
            />
          ) : pickup ? (
            <MapCanvas mode="known" pickup={pickup} height={420} showPickupBanner />
          ) : (
            <div className="loc-placeholder">
              <MapPin size={22} />
              This donation does not have coordinates yet.
            </div>
          )}
          {donation.cluster_window ? <p className="field-hint">Pickup schedule: {donation.cluster_window}</p> : null}
          {donation.pickup_address ? <p className="muted">{donation.pickup_address}</p> : null}
          {donation.pickup_landmark ? <p className="field-hint">Landmark: {donation.pickup_landmark}</p> : null}
          {deviceAccuracy ? (
            <p className="field-hint">{accuracyLabel(Number(donation.location_accuracy_m))}</p>
          ) : donation.location_source ? (
            <p className="field-hint">Saved location source: {donation.location_source} (not a live GPS fix).</p>
          ) : null}
          {donation.location_confirmed_at ? (
            <p className="muted">Confirmed {new Date(donation.location_confirmed_at).toLocaleString()}</p>
          ) : null}
        </div>
        <aside className="track-panel">
          {user && (user.role === "DONOR" || donation.is_donor) ? (
            <section className="code-box handoff-box" style={{ marginTop: 0 }}>
              <p className="eyebrow">Pickup OTP (handoff)</p>
              {handoffCode ? (
                <>
                  <strong>{handoffCode}</strong>
                  <p className="muted">
                    Created when a volunteer accepted. Share it at the door. It is not created when they arrive. SMS was
                    not sent.
                  </p>
                </>
              ) : (
                <p className="muted">
                  Your pickup code appears here when a volunteer accepts. Nothing is generated on arrival.
                </p>
              )}
              {assigned && donation.status !== "IN_TRANSIT" ? (
                <Button type="button" variant="ghost" onClick={() => void issuePickupOtp()} disabled={busy}>
                  {busy ? "Working…" : "Send a new pickup code"}
                </Button>
              ) : null}
            </section>
          ) : null}

          {code ? (
            <section className="code-box" style={{ marginTop: 12 }}>
              <p className="eyebrow">Legacy receive code</p>
              <strong>{code}</strong>
              <p className="muted">Optional secondary code. Prefer the pickup OTP above for handoff.</p>
              <Button type="button" variant="ghost" onClick={rotate} disabled={busy}>
                {busy ? "Working…" : "Resend code"}
              </Button>
            </section>
          ) : null}

          {donation.quality_checks?.length ? (
            <section className="stack" style={{ marginTop: 16 }}>
              <h3>Quality record</h3>
              <ul className="quality-log">
                {donation.quality_checks.map((check) => (
                  <li key={check.id}>
                    <strong>{check.stage}</strong> · {check.result}
                    <span className="muted"> {new Date(check.created_at).toLocaleString()}</span>
                  </li>
                ))}
              </ul>
              <p className="field-hint">Donor · volunteer pickup · org intake — three parties when each has recorded.</p>
            </section>
          ) : null}

          {assigned ? (
            <section className="accepted">
              <div className="rider" aria-hidden>
                <Bike size={22} />
              </div>
              <div>
                <h3>{donation.assignee_name} is assigned</h3>
                <p className="muted">
                  {collector?.freshness === "live"
                    ? "Collector location is live."
                    : collector?.freshness === "recent"
                      ? `Last updated ${collector.recorded_at ? new Date(collector.recorded_at).toLocaleTimeString() : "recently"}.`
                      : collector?.freshness === "stale"
                        ? "Collector location is stale — not shown as live."
                        : "Collector location unavailable."}
                </p>
                {collector?.accuracy_m != null && collector.freshness !== "stale" ? (
                  <p className="field-hint">Device-reported accuracy ±{collector.accuracy_m} m</p>
                ) : null}
              </div>
            </section>
          ) : (
            <EmptyState
              title="Awaiting assignment"
              body="We will show an assigned person, route and ETA only when those records exist."
            />
          )}

          <h3 style={{ marginTop: 20 }}>Journey</h3>
          <ol className="timeline">
            {TRACK_STAGES.map((stage, index) => {
              const cls = index < current ? "is-done" : index === current ? "is-current" : "";
              const hist = donation.history.find((item) => stage.match.includes(item.to_status));
              return (
                <li key={stage.id} className={cls}>
                  <div>
                    <strong>{stage.label}</strong>
                    {hist ? <span className="muted">{new Date(hist.created_at).toLocaleString()}</span> : null}
                  </div>
                </li>
              );
            })}
          </ol>
        </aside>
      </div>

      <div className="row-actions" style={{ marginTop: 22 }}>
        {user &&
        (user.role === "DONOR" || donation.is_donor) &&
        ["SUBMITTED", "ASSESSING", "MATCHING"].includes(donation.status) ? (
          <Button type="button" variant="danger" onClick={onCancel} disabled={busy}>
            Cancel donation
          </Button>
        ) : null}
        <Link
          to={user?.role === "VOLUNTEER" ? (donation.is_donor ? donationListPath(user.role) : "/volunteer") : "/app"}
          className="text-link"
        >
          Back
        </Link>
      </div>
    </article>
  );
}
