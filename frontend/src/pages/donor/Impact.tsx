import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { getImpact } from "../../services/notifications";
import { getRewards, type RewardsSummary } from "../../services/rewards";
import { readApiError } from "../../services/auth";
import { useI18n } from "../../providers/I18nProvider";
import type { ImpactSummary } from "../../types/models";

export function DonorImpact() {
  const { t } = useI18n();
  const [impact, setImpact] = useState<ImpactSummary | null>(null);
  const [rewards, setRewards] = useState<RewardsSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getImpact(), getRewards()])
      .then(([summary, points]) => {
        setImpact(summary);
        setRewards(points);
      })
      .catch((err) => setError(readApiError(err)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!impact) return <LoadingState />;

  return (
    <div>
      <p className="eyebrow">Impact</p>
      <h1>What has actually moved</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        {impact.has_events ? "Completed deliveries only." : t.impactEmpty}
      </p>
      <section className="hero-dash">
        <div className="metric-grid">
          <div className="metric">
            <strong>{impact.items_delivered}</strong>
            <span>Resources moved</span>
          </div>
          <div className="metric">
            <strong>{impact.donations_completed}</strong>
            <span>Donations completed</span>
          </div>
          <div className="metric">
            <strong>{impact.meals_distributed}</strong>
            <span>Food recovered</span>
          </div>
          <div className="metric">
            <strong>{impact.kg_recovered}</strong>
            <span>Waste diverted</span>
          </div>
        </div>
      </section>
      {rewards ? (
        <section className="surface-card stack" style={{ marginTop: 20 }}>
          <p className="eyebrow">Eco-points</p>
          <h2>
            {rewards.balance} · {rewards.level}
          </h2>
          <p className="muted">
            Points are added only after a delivery is verified.
            {rewards.next_level_at != null ? ` Next level at ${rewards.next_level_at}.` : ""}
          </p>
          <ul className="quality-log">
            {rewards.catalog.map((item) => (
              <li key={item.id}>
                <strong>{item.title}</strong> · {item.cost} points
                <span className="muted"> {item.reason}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {!impact.has_events ? (
        <div style={{ marginTop: 20 }}>
          <EmptyState title="No completed journeys yet" body="Share surplus and these numbers will fill in after delivery." />
        </div>
      ) : null}
    </div>
  );
}
