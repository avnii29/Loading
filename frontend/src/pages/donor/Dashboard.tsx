import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Package } from "lucide-react";
import { ActivityCard } from "../../components/ui/ActivityCard";
import { CategoryTiles } from "../../components/ui/CategoryTiles";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { useAuth } from "../../providers/AuthProvider";
import { listDonations } from "../../services/donations";
import { getImpact } from "../../services/notifications";
import { readApiError } from "../../services/auth";
import { ROLE_LABEL } from "../../constants/roles";
import type { Donation, DonationCategory, ImpactSummary } from "../../types/models";

export function DonorDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [donations, setDonations] = useState<Donation[] | null>(null);
  const [impact, setImpact] = useState<ImpactSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([listDonations(), getImpact()])
      .then(([rows, summary]) => {
        setDonations(rows);
        setImpact(summary);
      })
      .catch((err) => setError(readApiError(err)));
  }, []);

  const firstName = user?.full_name.split(" ")[0] || "there";
  const locationHint = user?.organization_name || "India";

  return (
    <div className="dash">
      <div className="welcome-row">
        <div>
          <p className="eyebrow">
            {user ? ROLE_LABEL[user.role].toUpperCase() : "DONOR"} · {locationHint}
          </p>
          <h1>Welcome back, {firstName}</h1>
          <p className="muted">What can you give today?</p>
        </div>
        <div className="row-actions">
          <Link to="/app/donate" className="btn btn-primary">
            Donate now
          </Link>
          <Link to="/app/organisations" className="btn btn-secondary">
            Find organisations
          </Link>
        </div>
      </div>

      <section className="hero-dash">
        <p className="eyebrow">Your impact</p>
        <h2>Moved only when a journey completes.</h2>
        <div className="metric-grid">
          <div className="metric">
            <strong>{impact?.items_delivered ?? 0}</strong>
            <span>Resources moved</span>
          </div>
          <div className="metric">
            <strong>{impact?.donations_completed ?? 0}</strong>
            <span>Donations completed</span>
          </div>
          <div className="metric">
            <strong>{impact?.meals_distributed ?? 0}</strong>
            <span>Food recovered</span>
          </div>
          <div className="metric">
            <strong>{impact?.kg_recovered ?? 0}</strong>
            <span>Waste diverted</span>
          </div>
        </div>
      </section>

      <section>
        <h2 className="choose-title">What can I give today?</h2>
        <p className="muted" style={{ marginBottom: 16 }}>
          Choose a category to start a donation.
        </p>
        <CategoryTiles onSelect={(id: DonationCategory) => navigate(`/app/donate?category=${id}`)} />
      </section>

      <section>
        <h2>Recent activity</h2>
        {error ? <ErrorState message={error} /> : null}
        {!donations && !error ? <LoadingState /> : null}
        {donations && donations.length === 0 ? (
          <EmptyState
            title="Nothing on the move yet"
            body="When you share surplus, its journey will collect here."
            icon={<Package size={22} />}
          />
        ) : null}
        <div className="stack" style={{ marginTop: 12 }}>
          {donations?.map((row) => (
            <ActivityCard key={row.id} donation={row} />
          ))}
        </div>
      </section>
    </div>
  );
}
