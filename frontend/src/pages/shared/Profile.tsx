import { useState, type FormEvent } from "react";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Field";
import { LanguageSelect } from "../../components/ui/LanguageSelect";
import { useAuth } from "../../providers/AuthProvider";
import { authService, readApiError } from "../../services/auth";
import { ROLE_LABEL } from "../../constants/roles";

export function Profile() {
  const { user, refresh } = useAuth();
  const [name, setName] = useState(user?.full_name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await authService.updateProfile({ full_name: name, phone });
      await refresh();
      setMessage("Saved.");
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <form className="wizard-panel" style={{ maxWidth: 560 }} onSubmit={onSubmit}>
      <p className="eyebrow">Account</p>
      <h1>Profile</h1>
      <p className="muted" style={{ margin: "8px 0 20px" }}>
        {user.email} · {ROLE_LABEL[user.role]}
        {user.organization_name ? ` · ${user.organization_name}` : ""}
      </p>
      {user.verification_status ? (
        <p className="muted">Verification: {user.verification_status.toLowerCase()}</p>
      ) : null}
      <div className="stack">
        <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <Input label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <label className="field">
          <span>Language</span>
          <LanguageSelect />
        </label>
        {message ? <p className="ok">{message}</p> : null}
        {error ? <p className="field-error">{error}</p> : null}
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
}
