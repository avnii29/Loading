import { useEffect, useState } from "react";
import { Bike, Leaf, Shield } from "lucide-react";
import { EmptyState, ErrorState, LoadingState, StatusBadge } from "../../components/ui/States";
import { Button } from "../../components/ui/Button";
import { LocationPicker, type ConfirmedLocation } from "../../components/map/LocationPicker";
import { MapCanvas } from "../../components/map/MapCanvas";
import { AssignmentBoard } from "../../components/logistics/AssignmentBoard";
import { AvailableRequests } from "../../components/logistics/AvailableRequests";
import { OrgIntakeBoard } from "../../components/logistics/OrgIntakeBoard";
import { Input, Textarea } from "../../components/ui/Field";
import { useAuth } from "../../providers/AuthProvider";
import { getMyOrganization, updateMyOrganization } from "../../services/organizations";
import { readApiError } from "../../services/auth";
import api from "../../services/api";
import type { Organization } from "../../types/models";

export function VolunteerHome() {
  return (
    <div className="role-board stack">
      <section className="role-hero">
        <p className="eyebrow">Volunteer</p>
        <h1>Pickup requests</h1>
        <p className="muted">
          These are other people’s pickup requests. Donations you submit stay under My donations and are not offered to
          you. Accept a timed offer to be assigned, then verify pickup with OTP.
        </p>
      </section>
      <AvailableRequests />
      <section>
        <p className="eyebrow">After you accept</p>
        <h2>My active assignment</h2>
      </section>
      <AssignmentBoard />
    </div>
  );
}

export function VolunteerHistory() {
  return (
    <div>
      <p className="eyebrow">Volunteer</p>
      <h1>Completion history</h1>
      <EmptyState title="No completed routes" body="Finished neighbourhood runs will collect here." icon={<Bike size={22} />} />
    </div>
  );
}

export function DriverHome() {
  return (
    <div className="role-board stack">
      <section className="role-hero">
        <p className="eyebrow">Driver</p>
        <h1>Commercial jobs</h1>
        <p className="muted">Timed offers, OTP handoffs and quality checks follow the same race-safe server rules.</p>
      </section>
      <AvailableRequests />
      <section>
        <p className="eyebrow">After you accept</p>
        <h2>My active assignment</h2>
      </section>
      <AssignmentBoard />
    </div>
  );
}

export function DriverHistory() {
  return (
    <div>
      <p className="eyebrow">Driver</p>
      <h1>Finished jobs</h1>
      <EmptyState title="No completed jobs" body="Finished commercial and recovery runs will appear after real assignments complete." />
    </div>
  );
}

export function FarmHome() {
  return (
    <div className="role-board">
      <section className="role-hero">
        <p className="eyebrow">Recovery partner</p>
        <h1>Compatible material only</h1>
        <p className="muted">
          Recovery jobs appear after a human-consumption donation is separately re-evaluated. Nothing is auto-sent.
        </p>
      </section>
      <div className="role-cols">
        <EmptyState
          title="No compatible jobs"
          body="Incoming material will show compatibility status when recovery matching is live."
          icon={<Leaf size={22} />}
        />
        <article className="surface-card">
          <p className="eyebrow">Compatibility</p>
          <h3>Awaiting review</h3>
          <p className="muted">Organic recovery is a distinct stream. It never shares the food intake queue.</p>
        </article>
      </div>
    </div>
  );
}

export function FarmHistory() {
  return (
    <div>
      <p className="eyebrow">Recovery</p>
      <h1>Recovered loads</h1>
      <EmptyState title="No recovery events" body="Recovered loads will appear after real recovery events." />
    </div>
  );
}

export function OrganizationHome() {
  const { user } = useAuth();
  const [org, setOrg] = useState<Organization | null>(null);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState("");
  const [city, setCity] = useState("");
  const [address, setAddress] = useState("");
  const [place, setPlace] = useState<ConfirmedLocation>({
    address: "",
    point: null,
    approximate: false,
    confirmed: false,
  });
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState("");

  useEffect(() => {
    getMyOrganization()
      .then((row) => {
        setOrg(row);
        setNotes(row.description || "");
        setCity(row.city || "");
        setAddress(row.address || "");
        setPlace({
          address: row.address || "",
          point:
            row.latitude != null && row.longitude != null
              ? { lat: Number(row.latitude), lng: Number(row.longitude) }
              : null,
          mappls_pin: row.mappls_pin,
          provider: row.location_provider || undefined,
          approximate: false,
          confirmed: row.latitude != null,
        });
      })
      .catch((err) => setError(readApiError(err)));
  }, []);

  async function save() {
    if (place.point && !place.confirmed) {
      setError("Confirm the organisation map pin before saving.");
      return;
    }
    setBusy(true);
    setSaved("");
    setError("");
    try {
      const next = await updateMyOrganization({
        description: notes,
        city,
        address: place.address || address,
        latitude: place.point?.lat,
        longitude: place.point?.lng,
        mappls_pin: place.mappls_pin || undefined,
        location_provider: place.provider,
      });
      setOrg(next);
      setSaved("Saved.");
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (!org) return <LoadingState />;

  return (
    <div className="role-board">
      <section className="role-hero">
        <p className="eyebrow">Organisation</p>
        <div className="welcome-row">
          <div>
            <h1>{org.name}</h1>
            <p className="muted">Incoming donations, capacity and needs stay empty until real matches exist.</p>
          </div>
          <StatusBadge label={org.verification_status.toLowerCase()} />
        </div>
      </section>
      <div className="role-cols">
        <div className="stack">
          <h2>Incoming</h2>
          <p className="muted">
            {user?.full_name}: delivery OTP and intake quality appear only for donations matched to your organisation.
          </p>
          <OrgIntakeBoard />
        </div>
        <article className="surface-card stack">
          <p className="eyebrow">Capacity & needs</p>
          <h3>Your intake profile</h3>
          <p className="muted">Verification is decided by Anuvarthan, not by this form.</p>
          <Textarea label="About" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <Input label="City" value={city} onChange={(e) => setCity(e.target.value)} />
          <LocationPicker value={place} onChange={setPlace} height={280} />
          <p className="muted">Finding the organisation on the map does not verify it.</p>
          {saved ? <p className="ok">{saved}</p> : null}
          <Button type="button" onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save profile"}
          </Button>
        </article>
      </div>
    </div>
  );
}

export function OrganizationHistory() {
  return (
    <div>
      <p className="eyebrow">Organisation</p>
      <h1>Accepted deliveries</h1>
      <EmptyState title="No intake history" body="Accepted deliveries will appear after completed intake events." />
    </div>
  );
}

type AdminOrg = Organization & { id: string };

export function AdminHome() {
  const [rows, setRows] = useState<AdminOrg[] | null>(null);
  const [ops, setOps] = useState<{
    organizations: { id: string; name: string; latitude: number; longitude: number; verification_status: string }[];
    donations: { id: string; reference: string; category: string; status: string; latitude: number; longitude: number }[];
  } | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "orgs" | "donations">("all");

  function load() {
    api
      .get<AdminOrg[]>("/admin/organizations")
      .then((res) => setRows(res.data))
      .catch((err) => setError(readApiError(err)));
    api
      .get("/admin/operations-map")
      .then((res) => setOps(res.data))
      .catch(() => setOps(null));
  }

  useEffect(() => {
    load();
  }, []);

  async function verify(id: string, status: "VERIFIED" | "REJECTED" | "PENDING_REVIEW") {
    setBusyId(id);
    try {
      await api.post(`/admin/organizations/${id}/verification`, { status });
      load();
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusyId(null);
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!rows) return <LoadingState />;

  return (
    <div className="role-board">
      <section className="role-hero">
        <p className="eyebrow">Admin</p>
        <h1>Operations command</h1>
        <p className="muted">Verify destinations. Audit follows real events only.</p>
      </section>
      <div className="metric-grid">
        <div className="metric">
          <strong>{rows.length}</strong>
          <span>Organisation records</span>
        </div>
        <div className="metric">
          <strong>{rows.filter((row) => row.verification_status === "VERIFIED").length}</strong>
          <span>Verified</span>
        </div>
        <div className="metric">
          <strong>{rows.filter((row) => row.verification_status !== "VERIFIED").length}</strong>
          <span>Awaiting review</span>
        </div>
        <div className="metric">
          <strong>0</strong>
          <span>Open incidents</span>
        </div>
      </div>
      {ops ? (
        <article className="surface-card" style={{ marginBottom: 20 }}>
          <div className="welcome-row">
            <div>
              <p className="eyebrow">Live operations</p>
              <h3>Current map</h3>
              <p className="muted">Only saved Anuvarthan records. Mappls POIs are not destinations.</p>
            </div>
            <div className="row-actions">
              <Button type="button" variant={filter === "all" ? "primary" : "secondary"} onClick={() => setFilter("all")}>
                All
              </Button>
              <Button type="button" variant={filter === "orgs" ? "primary" : "secondary"} onClick={() => setFilter("orgs")}>
                Organisations
              </Button>
              <Button type="button" variant={filter === "donations" ? "primary" : "secondary"} onClick={() => setFilter("donations")}>
                Food / goods
              </Button>
            </div>
          </div>
          <MapCanvas
            mode={ops.organizations.length || ops.donations.length ? "known" : "unknown"}
            markers={[
              ...(filter !== "donations"
                ? ops.organizations.map((row) => ({
                    id: row.id,
                    kind: "organisation" as const,
                    label: `${row.name} · ${row.verification_status}`,
                    point: { lat: row.latitude, lng: row.longitude },
                  }))
                : []),
              ...(filter !== "orgs"
                ? ops.donations.map((row) => ({
                    id: row.id,
                    kind: "donation" as const,
                    label: `${row.reference} · ${row.category} · ${row.status}`,
                    point: { lat: row.latitude, lng: row.longitude },
                  }))
                : []),
            ]}
            height={420}
            emptyLabel="No mapped operations yet."
          />
        </article>
      ) : null}
      {rows.length === 0 ? (
        <EmptyState title="No organisations yet" body="When an organisation registers, review them here." icon={<Shield size={22} />} />
      ) : (
        <div className="stack">
          {rows.map((row) => (
            <article key={row.id} className="activity-card">
              <div>
                <strong>{row.name}</strong>
                <p className="muted">{row.verification_status}</p>
              </div>
              <div className="row-actions">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={busyId === row.id}
                  onClick={() => verify(row.id, "PENDING_REVIEW")}
                >
                  Review
                </Button>
                <Button type="button" disabled={busyId === row.id} onClick={() => verify(row.id, "VERIFIED")}>
                  Verify
                </Button>
                <Button
                  type="button"
                  variant="danger"
                  disabled={busyId === row.id}
                  onClick={() => verify(row.id, "REJECTED")}
                >
                  Reject
                </Button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export function AdminDestinations() {
  return (
    <div>
      <p className="eyebrow">Admin</p>
      <h1>Destinations</h1>
      <EmptyState
        title="Destination records"
        body="Destination records are created when organisations register. Only verified and active ones join matching later."
      />
    </div>
  );
}

export function AdminAudit() {
  const [rows, setRows] = useState<{ id: string; action: string; entity_type: string; created_at: string }[] | null>(
    null,
  );
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/admin/audit")
      .then((res) => setRows(res.data))
      .catch((err) => setError(readApiError(err)));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!rows) return <LoadingState />;
  if (rows.length === 0) return <EmptyState title="No audit events yet" />;

  return (
    <div>
      <p className="eyebrow">Admin</p>
      <h1>Audit</h1>
      <ul className="timeline" style={{ marginTop: 20 }}>
        {rows.map((row) => (
          <li key={row.id} className="is-done">
            <div>
              <strong>{row.action}</strong>
              <span className="muted">
                {row.entity_type} · {new Date(row.created_at).toLocaleString()}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
