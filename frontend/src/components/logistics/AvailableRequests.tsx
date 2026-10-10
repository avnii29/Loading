import { useEffect, useMemo, useRef, useState } from "react";
import { acceptOffer, declineOffer, listOffers, type VolunteerOffer } from "../../services/logistics";
import { readApiError } from "../../services/auth";
import { Button } from "../ui/Button";
import { EmptyState } from "../ui/States";
import { MapCanvas } from "../map/MapCanvas";
import { Modal } from "../ui/Modal";

function categoryLabel(value: string | null | undefined) {
  if (value === "OTHER") return "Miscellaneous";
  if (!value) return "Donation";
  return value.charAt(0) + value.slice(1).toLowerCase();
}

/**
 * Eligible pickup requests that are not yet assigned.
 * Each row is a real server offer. The countdown uses the offer's expires_at.
 */
export function AvailableRequests() {
  const [offers, setOffers] = useState<VolunteerOffer[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const seen = useRef(new Set<string>());

  async function refresh() {
    try {
      const rows = await listOffers();
      setOffers(rows.filter((row) => row.status === "PENDING" && new Date(row.expires_at).getTime() > Date.now()));
      setError("");
    } catch (err) {
      setError(readApiError(err));
    }
  }

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => void refresh(), 4000);
    const clock = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      window.clearInterval(poll);
      window.clearInterval(clock);
    };
  }, []);

  useEffect(() => {
    setSelectedId((current) => (current && offers.some((row) => row.id === current) ? current : offers[0]?.id || ""));
    const fresh = offers.find((row) => !seen.current.has(row.id));
    if (fresh) {
      offers.forEach((row) => seen.current.add(row.id));
      setSelectedId(fresh.id);
      setOpen(true);
    }
    if (!offers.length) setOpen(false);
  }, [offers]);

  const selected = useMemo(() => offers.find((row) => row.id === selectedId) || null, [offers, selectedId]);

  async function onAccept(offer: VolunteerOffer) {
    setBusy(offer.id);
    setError("");
    try {
      await acceptOffer(offer.id);
      setOpen(false);
      window.dispatchEvent(new Event("anuvartan-assignment-refresh"));
      await refresh();
    } catch (err) {
      setError(readApiError(err) || "This offer is no longer available.");
      await refresh();
    } finally {
      setBusy("");
    }
  }

  async function onDecline(offer: VolunteerOffer) {
    setBusy(offer.id);
    try {
      await declineOffer(offer.id);
      setOpen(false);
      await refresh();
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="stack">
      <div>
        <p className="eyebrow">Before assignment</p>
        <h2>Available pickup requests</h2>
        <p className="muted">These donations are waiting for a volunteer. Accepting a timed offer is what assigns you.</p>
      </div>
      {error ? <p className="field-error">{error}</p> : null}
      {!offers.length ? (
        <EmptyState
          title="No pickup requests right now"
          body="Eligible donations show up here before anyone is assigned."
        />
      ) : (
        <ul className="offer-list">
          {offers.map((offer) => {
            const remaining = Math.max(0, Math.ceil((new Date(offer.expires_at).getTime() - now) / 1000));
            return (
              <li key={offer.id}>
                <button
                  type="button"
                  className={`offer-row${offer.id === selectedId ? " is-selected" : ""}`}
                  onClick={() => {
                    setSelectedId(offer.id);
                    setOpen(true);
                  }}
                >
                  <span>
                    <strong>
                      {categoryLabel(offer.category)} · {offer.quantity} {offer.unit}
                    </strong>
                    <small>Near {offer.area_label || "a confirmed area"}</small>
                  </span>
                  <em>{remaining}s</em>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <OfferDialog
        offer={open ? selected : null}
        now={now}
        busy={busy}
        error={error}
        onClose={() => setOpen(false)}
        onAccept={onAccept}
        onDecline={onDecline}
      />
    </section>
  );
}

function OfferDialog({
  offer,
  now,
  busy,
  error,
  onClose,
  onAccept,
  onDecline,
}: {
  offer: VolunteerOffer | null;
  now: number;
  busy: string;
  error: string;
  onClose: () => void;
  onAccept: (offer: VolunteerOffer) => void;
  onDecline: (offer: VolunteerOffer) => void;
}) {
  const remaining = offer ? Math.max(0, Math.ceil((new Date(offer.expires_at).getTime() - now) / 1000)) : 0;
  const scheduled = offer?.pickup_schedule && offer.pickup_schedule !== "ASAP";
  const point =
    offer?.pickup_latitude != null &&
    offer.pickup_longitude != null &&
    Number.isFinite(offer.pickup_latitude) &&
    Number.isFinite(offer.pickup_longitude)
      ? { lat: offer.pickup_latitude, lng: offer.pickup_longitude }
      : null;

  return (
    <Modal open={Boolean(offer)} title="Timed pickup offer" onClose={onClose}>
      {offer ? (
        <div className="offer-dialog">
          <p className="eyebrow">
            {categoryLabel(offer.category)} · {offer.priority_class || "P?"} · {remaining}s left
          </p>
          <p className="offer-dialog-title">
            {offer.quantity} {offer.unit}
          </p>
          <p className="muted">{offer.description || offer.summary || "Pickup request"}</p>
          <p className="field-hint">Near {offer.area_label || "a confirmed area"}</p>
          <p className="field-hint">
            {scheduled ? `Scheduled pickup: ${offer.pickup_schedule}` : `Pickup: ${offer.pickup_schedule || "ASAP"}`}
          </p>
          {offer.reference_code ? <p className="field-hint">Ref {offer.reference_code}</p> : null}
          {point ? <MapCanvas mode="known" pickup={point} height={160} /> : null}
          {error ? <p className="field-error">{error}</p> : null}
          <div className="offer-dialog-actions">
            <Button type="button" onClick={() => void onAccept(offer)} disabled={busy === offer.id || remaining <= 0}>
              {busy === offer.id ? "Accepting…" : "Accept offer"}
            </Button>
            <Button type="button" variant="secondary" onClick={() => void onDecline(offer)} disabled={busy === offer.id}>
              Decline
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
