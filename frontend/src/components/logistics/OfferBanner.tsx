import { useEffect, useState } from "react";
import { acceptOffer, declineOffer, listOffers, type VolunteerOffer } from "../../services/logistics";
import { readApiError } from "../../services/auth";
import { Button } from "../ui/Button";

/**
 * Server-timed volunteer offer UI. Countdown is visual only — accept is validated server-side.
 */
export function OfferBanner() {
  const [offers, setOffers] = useState<VolunteerOffer[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [now, setNow] = useState(() => Date.now());

  async function refresh() {
    try {
      const rows = await listOffers();
      setOffers(rows.filter((row) => row.status === "PENDING"));
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

  const active = offers.find((row) => new Date(row.expires_at).getTime() > now);
  if (!active) return error ? <p className="field-hint">{error}</p> : null;

  const offer = active;
  const remaining = Math.max(0, Math.ceil((new Date(offer.expires_at).getTime() - now) / 1000));

  async function onAccept() {
    setBusy(offer.id);
    try {
      await acceptOffer(offer.id);
      await refresh();
    } catch (err) {
      setError(readApiError(err) || "This offer is no longer available.");
      await refresh();
    } finally {
      setBusy("");
    }
  }

  async function onDecline() {
    setBusy(offer.id);
    try {
      await declineOffer(offer.id);
      await refresh();
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy("");
    }
  }

  return (
    <aside className="offer-banner" role="dialog" aria-label="Timed pickup offer">
      <p className="eyebrow">
        Timed offer · {remaining}s left · {offer.priority_class || "P?"}
      </p>
      <h3>{offer.summary || "Pickup available"}</h3>
      <p className="muted">
        Near {offer.area_label || "confirmed area"}
        {offer.quantity ? ` · ${offer.quantity} ${offer.unit || ""}` : ""}. Exact address unlocks after accept.
      </p>
      <p className="field-hint">
        {remaining <= 0
          ? "Window closed locally — server will reject late accepts."
          : "Countdown is visual only. Race-safe accept is validated server-side (FOR UPDATE)."}
      </p>
      {error ? <p className="field-error">{error}</p> : null}
      <div className="row-actions">
        <Button type="button" onClick={() => void onAccept()} disabled={busy === offer.id || remaining <= 0}>
          {busy === offer.id ? "Accepting…" : "Accept"}
        </Button>
        <Button type="button" variant="secondary" onClick={() => void onDecline()} disabled={busy === offer.id}>
          Decline
        </Button>
      </div>
    </aside>
  );
}
