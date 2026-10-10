import { Link } from "react-router-dom";
import { StatusBadge } from "./States";
import { categoryMeta, formatWhen, statusTone } from "../../constants/donations";
import { donationDetailPath } from "../../constants/roles";
import { useAuth } from "../../providers/AuthProvider";
import { UserRole, type Donation } from "../../types/models";

export function ActivityCard({ donation }: { donation: Donation }) {
  const { user } = useAuth();
  const meta = categoryMeta(donation.category);
  return (
    <Link to={donationDetailPath(user?.role || UserRole.DONOR, donation.id)} className="activity-card">
      <div>
        <p className="eyebrow">{meta.label}</p>
        <h3>
          {donation.quantity} {donation.unit}
        </h3>
        <p className="muted">
          {donation.pickup_address || "Pickup to be confirmed"}
          {donation.destination_id ? " · Destination assigned" : ""}
        </p>
        {donation.cluster_window ? <p className="field-hint">Pickup: {donation.cluster_window}</p> : null}
        <p className="muted">
          {donation.reference_code} · {formatWhen(donation.created_at)}
        </p>
      </div>
      <StatusBadge label={donation.status_label} tone={statusTone(donation.status)} />
    </Link>
  );
}
