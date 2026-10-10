import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDonations, getDonation, addQualityCheck } from "../../services/donations";
import { verifyHandoff } from "../../services/logistics";
import { listNotifications } from "../../services/notifications";
import { readApiError } from "../../services/auth";
import { Button } from "../ui/Button";
import { Input } from "../ui/Field";
import { FoodChecks, rowsFor } from "../food/FoodChecks";
import { ChoiceChips } from "../ui/ChoiceChips";
import { EmptyState } from "../ui/States";
import type { Donation } from "../../types/models";

/**
 * Organisation receiving board — delivery OTP + intake quality (party 3).
 */
export function OrgIntakeBoard() {
  const [rows, setRows] = useState<Donation[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [otp, setOtp] = useState<Record<string, string>>({});
  const [issued, setIssued] = useState<Record<string, string>>({});
  const [quality, setQuality] = useState<Record<string, Record<string, string>>>({});
  const [holdReason, setHoldReason] = useState<Record<string, string>>({});

  async function refresh() {
    try {
      const all = await listDonations();
      setRows(
        all.filter((row) =>
          ["IN_TRANSIT", "DELIVERED", "ASSIGNED", "PICKUP_PENDING", "MATCHED"].includes(row.status),
        ),
      );
      setError("");
    } catch (err) {
      setError(readApiError(err));
    }
  }

  useEffect(() => {
    void refresh();
    const pullCodes = () => {
      listNotifications()
        .then((notes) => {
          const next: Record<string, string> = {};
          for (const note of notes) {
            const match = note.body.match(/Receipt code: (\d{6})/);
            if (match && note.entity_id) next[note.entity_id] = match[1];
          }
          setIssued((prev) => ({ ...next, ...prev }));
        })
        .catch(() => undefined);
    };
    pullCodes();
    const poll = window.setInterval(() => {
      void refresh();
      pullCodes();
    }, 10000);
    return () => window.clearInterval(poll);
  }, []);

  async function onVerify(donationId: string) {
    const code = (otp[donationId] || issued[donationId] || "").trim();
    if (code.length < 4) {
      setError("Enter the delivery OTP.");
      return;
    }
    setBusy(`v-${donationId}`);
    setError("");
    try {
      await verifyHandoff(donationId, "DELIVERY", code);
      const row = await getDonation(donationId);
      setRows((prev) => prev.map((item) => (item.id === donationId ? row : item)));
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy("");
    }
  }

  async function onQuality(donationId: string) {
    const answers = quality[donationId] || {};
    if (!rowsFor("intake").every((row) => answers[row.key])) return;
    setBusy(`q-${donationId}`);
    setError("");
    try {
      const row = await addQualityCheck(donationId, {
        result: "PENDING",
        stage: "INTAKE",
        responses: answers,
        notes: holdReason[donationId] || undefined,
      });
      setRows((prev) => prev.map((item) => (item.id === donationId ? row : item)));
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy("");
    }
  }

  if (!rows.length) {
    return (
      <EmptyState
        title="No incoming deliveries"
        body="Matched and in-transit donations for your organisation appear here with real OTP and intake checks."
      />
    );
  }

  return (
    <div className="assignment-board stack">
      {error ? <p className="field-error">{error}</p> : null}
      {rows.map((row) => {
        const hasIntake = row.quality_checks?.some((q) => q.stage === "INTAKE");
        const delivered = ["DELIVERED", "COMPLETED"].includes(row.status);
        return (
          <article key={row.id} className="surface-card stack assignment-card">
            <p className="eyebrow">{row.status_label}</p>
            <h3>
              {row.quantity} {row.unit} · {row.category}
            </h3>
            <p className="muted">{row.reference_code}</p>
            <Link to={`/app/donations/${row.id}`} className="text-link">
              Open donation
            </Link>

            {!delivered ? (
              <div className="handoff-box stack">
                <p className="eyebrow">Receipt code</p>
                <p className="muted">
                  This code appears when the volunteer reaches you. Share it with them. It is not created earlier. SMS
                  was not sent.
                </p>
                {issued[row.id] ? (
                  <p className="code-box">
                    <strong>{issued[row.id]}</strong>
                  </p>
                ) : (
                  <p className="field-hint">Waiting for the volunteer to arrive.</p>
                )}
                <Input
                  label="Verify code"
                  inputMode="numeric"
                  maxLength={6}
                  value={otp[row.id] || ""}
                  onChange={(e) =>
                    setOtp((prev) => ({
                      ...prev,
                      [row.id]: e.target.value.replace(/\D/g, "").slice(0, 6),
                    }))
                  }
                />
                <Button type="button" onClick={() => void onVerify(row.id)} disabled={busy === `v-${row.id}`}>
                  {busy === `v-${row.id}` ? "Verifying…" : "Verify delivery"}
                </Button>
              </div>
            ) : (
              <p className="ok">Delivery verified on server.</p>
            )}

            {!hasIntake ? (
              <div className="handoff-box stack">
                <FoodChecks
                  role="intake"
                  value={quality[row.id] || {}}
                  onChange={(next) => setQuality((prev) => ({ ...prev, [row.id]: next }))}
                />
                {quality[row.id]?.accepted === "HOLD" || quality[row.id]?.accepted === "REJECT" ? (
                  <ChoiceChips
                    label="Reason"
                    value={holdReason[row.id]}
                    onChange={(v) => setHoldReason((prev) => ({ ...prev, [row.id]: v }))}
                    columns={2}
                    options={[
                      { value: "Spoilage concern", label: "Spoilage concern" },
                      { value: "Packaging damaged", label: "Packaging damaged" },
                      { value: "Temperature concern", label: "Temperature concern" },
                      { value: "Quantity mismatch", label: "Quantity mismatch" },
                      { value: "Other", label: "Other" },
                    ]}
                  />
                ) : null}
                <Button type="button" variant="secondary" onClick={() => void onQuality(row.id)} disabled={busy === `q-${row.id}`}>
                  Record receipt
                </Button>
              </div>
            ) : (
              <p className="field-hint">Intake quality recorded.</p>
            )}
          </article>
        );
      })}
    </div>
  );
}
