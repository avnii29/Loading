import { useEffect, useState } from "react";
import { Package } from "lucide-react";
import { ActivityCard } from "../../components/ui/ActivityCard";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { listDonations } from "../../services/donations";
import { readApiError } from "../../services/auth";
import { useAuth } from "../../providers/AuthProvider";
import { UserRole, type Donation } from "../../types/models";

export function History() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Donation[] | null>(null);
  const [error, setError] = useState("");
  const mine = rows?.filter((row) => row.is_donor !== false) ?? null;

  useEffect(() => {
    listDonations()
      .then(setRows)
      .catch((err) => setError(readApiError(err)));
  }, []);

  return (
    <div>
      <p className="eyebrow">Journeys</p>
      <h1>My donations</h1>
      <p className="muted" style={{ marginBottom: 20 }}>
        {user?.role === UserRole.VOLUNTEER
          ? "Donations you submitted. Pickup requests you can collect stay under My pickups."
          : "Every share you have started, in motion or complete."}
      </p>
      {error ? <ErrorState message={error} /> : null}
      {!rows && !error ? <LoadingState /> : null}
      {mine && mine.length === 0 ? (
        <EmptyState
          title="No donations yet"
          body="When you share something, its journey will appear here."
          icon={<Package size={22} />}
        />
      ) : null}
      <div className="stack">
        {mine?.map((row) => (
          <ActivityCard key={row.id} donation={row} />
        ))}
      </div>
    </div>
  );
}
