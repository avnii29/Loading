import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Info, X } from "lucide-react";
import { AuthAtmosphere } from "../components/ui/AuthAtmosphere";
import { BrandMark } from "../components/ui/BrandMark";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Field";
import { useAuth } from "../providers/AuthProvider";
import { ROLE_HOME } from "../constants/roles";
import { readApiError } from "../services/auth";

const SAMPLES = [
  { id: "abc", password: "abc123", label: "Household donor" },
  { id: "def", password: "def123", label: "Function hall" },
  { id: "ghi", password: "ghi123", label: "NSS volunteer" },
  { id: "jkl", password: "jkl123", label: "Gig rider" },
  { id: "org", password: "org123", label: "Organisation NGO" },
];

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [samplesOpen, setSamplesOpen] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const user = await login(email, password);
      navigate(ROLE_HOME[user.role], { replace: true });
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  function useSample(id: string, pass: string) {
    setEmail(id);
    setPassword(pass);
    setSamplesOpen(false);
  }

  return (
    <div className="auth-page auth-shell">
      <AuthAtmosphere />
      <form className="enroll-card narrow" onSubmit={onSubmit}>
        <button
          type="button"
          className={`sample-info-btn ${samplesOpen ? "is-on" : ""}`}
          aria-expanded={samplesOpen}
          aria-controls="sample-logins-panel"
          aria-label={samplesOpen ? "Close sample logins" : "Sample logins"}
          onClick={() => setSamplesOpen((open) => !open)}
        >
          {samplesOpen ? <X size={16} strokeWidth={2.4} /> : <Info size={16} strokeWidth={2.4} />}
        </button>

        {samplesOpen ? (
          <aside id="sample-logins-panel" className="sample-popover" role="dialog" aria-label="Sample logins">
            <p className="eyebrow">Sample logins</p>
            <p className="muted">Tap a row to fill. Full emails are *@anuvarthan.test.</p>
            <ul className="sample-logins">
              {SAMPLES.map((item) => (
                <li key={item.id}>
                  <button type="button" onClick={() => useSample(item.id, item.password)}>
                    <span>{item.label}</span>
                    <strong>
                      {item.id} · {item.password}
                    </strong>
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        ) : null}

        <div className="enroll-brand">
          <Link to="/">
            <BrandMark size={88} />
          </Link>
          <p className="eyebrow">Welcome back</p>
          <h1>Sign in to Anuvarthan</h1>
          <p className="muted">Continue the journeys you have already started.</p>
        </div>
        <div className="auth-fields">
          <Input
            label="Email or short id"
            type="text"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <div className="password-wrap">
            <Input
              label="Password"
              type={show ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button type="button" className="text-link show-pass" onClick={() => setShow((v) => !v)}>
              {show ? "Hide" : "Show"}
            </button>
          </div>
          {error ? <p className="field-error">{error}</p> : null}
          <Button type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </Button>
          <p className="muted">
            New here? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </form>
    </div>
  );
}
