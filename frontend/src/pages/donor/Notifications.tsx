import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell } from "lucide-react";
import { EmptyState, ErrorState, LoadingState } from "../../components/ui/States";
import { listNotifications, markNotificationRead } from "../../services/notifications";
import { readApiError } from "../../services/auth";
import { useI18n } from "../../providers/I18nProvider";
import { formatWhen } from "../../constants/donations";
import type { AppNotification } from "../../types/models";

export function Notifications() {
  const { t } = useI18n();
  const [rows, setRows] = useState<AppNotification[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listNotifications()
      .then(setRows)
      .catch((err) => setError(readApiError(err)));
  }, []);

  async function open(row: AppNotification) {
    if (!row.is_read) {
      const next = await markNotificationRead(row.id);
      setRows((current) => current?.map((item) => (item.id === next.id ? next : item)) ?? null);
    }
  }

  return (
    <div>
      <p className="eyebrow">Updates</p>
      <h1>Notifications</h1>
      {error ? <ErrorState message={error} /> : null}
      {!rows && !error ? <LoadingState /> : null}
      {rows && rows.length === 0 ? (
        <EmptyState title={t.emptyNotifications} icon={<Bell size={22} />} />
      ) : null}
      <ul className="note-list" style={{ marginTop: 16 }}>
        {rows?.map((row) => (
          <li key={row.id} className={row.is_read ? "is-read" : ""}>
            <button type="button" onClick={() => open(row)}>
              <strong>{row.title}</strong>
              <p>{row.body}</p>
              <time className="muted">{formatWhen(row.created_at)}</time>
            </button>
            {row.entity_type === "donation" && row.entity_id ? (
              <Link to={`/app/donations/${row.entity_id}`} className="text-link">
                Open donation
              </Link>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
