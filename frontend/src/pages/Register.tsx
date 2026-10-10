import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bike,
  Building2,
  Check,
  GraduationCap,
  Home,
  Leaf,
  Truck,
  Users,
  UtensilsCrossed,
} from "lucide-react";
import { AuthAtmosphere } from "../components/ui/AuthAtmosphere";
import { BrandMark } from "../components/ui/BrandMark";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Field";
import { useAuth } from "../providers/AuthProvider";
import { ROLE_HOME } from "../constants/roles";
import { readApiError } from "../services/auth";
import { UserRole, type DonorType } from "../types/models";

type Card = {
  group: "DONATE" | "MOVE" | "RECEIVE";
  role: UserRole;
  donorType?: DonorType;
  title: string;
  badge: string;
  hint: string;
  icon: typeof Home;
};

const CARDS: Card[] = [
  {
    group: "DONATE",
    role: UserRole.DONOR,
    donorType: "HOUSEHOLD",
    title: "Household",
    badge: "Home",
    hint: "Share extra food and goods from home.",
    icon: Home,
  },
  {
    group: "DONATE",
    role: UserRole.DONOR,
    donorType: "RESTAURANT",
    title: "Restaurant",
    badge: "Kitchen",
    hint: "Move leftover meals before they expire.",
    icon: UtensilsCrossed,
  },
  {
    group: "DONATE",
    role: UserRole.DONOR,
    donorType: "FUNCTION_HALL",
    title: "Function Hall",
    badge: "Venue",
    hint: "Clear event surplus with a planned pickup.",
    icon: Users,
  },
  {
    group: "DONATE",
    role: UserRole.DONOR,
    donorType: "INSTITUTION",
    title: "Institution",
    badge: "Campus",
    hint: "Hostels, offices and campuses with leftover stock.",
    icon: GraduationCap,
  },
  {
    group: "MOVE",
    role: UserRole.VOLUNTEER,
    title: "Volunteer",
    badge: "Neighbourhood",
    hint: "Help move clustered local donations.",
    icon: Bike,
  },
  {
    group: "MOVE",
    role: UserRole.DRIVER,
    title: "Driver",
    badge: "Logistics",
    hint: "Take commercial and recovery jobs.",
    icon: Truck,
  },
  {
    group: "RECEIVE",
    role: UserRole.ORGANIZATION,
    title: "Organisation",
    badge: "Destination",
    hint: "Receive, review and distribute surplus.",
    icon: Building2,
  },
  {
    group: "RECEIVE",
    role: UserRole.FARM_OPERATOR,
    title: "Recovery Partner",
    badge: "Recover",
    hint: "Receive compatible recovery material only.",
    icon: Leaf,
  },
];

const GROUPS: { id: Card["group"]; label: string; cols: "four" | "two" }[] = [
  { id: "DONATE", label: "Donate", cols: "four" },
  { id: "MOVE", label: "Move", cols: "two" },
  { id: "RECEIVE", label: "Receive / Recover", cols: "two" },
];

export function Register() {
  const { register, login } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<"role" | "details">("role");
  const [selected, setSelected] = useState<Card>(CARDS[0]);
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const needsOrg = selected.role === UserRole.ORGANIZATION || selected.role === UserRole.FARM_OPERATOR;
  const passwordsMatch = password === confirm;
  const disabled = busy || password.length < 8 || !passwordsMatch || !fullName.trim();
  const subtitle = useMemo(() => selected.hint, [selected]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!passwordsMatch) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await register({
        email,
        password,
        full_name: fullName,
        phone: phone || undefined,
        role: selected.role,
        donor_type: selected.role === UserRole.DONOR ? selected.donorType : undefined,
        organization_name: needsOrg ? organizationName : undefined,
      });
      setDone(true);
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function continueIn() {
    setBusy(true);
    try {
      const user = await login(email, password);
      navigate(ROLE_HOME[user.role], { replace: true });
    } catch (err) {
      setError(readApiError(err));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="auth-page auth-shell">
        <AuthAtmosphere />
        <div className="enroll-card narrow success-panel">
          <div className="success-check" aria-hidden>
            <Check size={36} />
          </div>
          <h1>You’re in.</h1>
          <p className="muted">Your account is ready. Continue to your space.</p>
          <Button onClick={continueIn} disabled={busy}>
            {busy ? "Opening…" : "Continue"}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page auth-shell">
      <AuthAtmosphere />
      <div className="enroll-card">
        <div className="enroll-brand">
          <Link to="/">
            <BrandMark size={88} />
          </Link>
          <p className="eyebrow">Join Anuvarthan</p>
          <h1>{step === "role" ? "How will you take part?" : "A few details."}</h1>
          <p className="muted">{step === "role" ? "Choose the space that fits you. You can keep it simple." : subtitle}</p>
        </div>

        {step === "role" ? (
          <div className="role-groups page-enter">
            {GROUPS.map((group) => (
              <section key={group.id} className="role-group">
                <h3>{group.label}</h3>
                <div className={`role-cards ${group.cols === "two" ? "two" : ""}`}>
                  {CARDS.filter((card) => card.group === group.id).map((card) => {
                    const Icon = card.icon;
                    const on = selected === card || (selected.title === card.title && selected.role === card.role);
                    return (
                      <button
                        key={card.title}
                        type="button"
                        className={`role-card ${on ? "is-on" : ""}`}
                        onClick={() => setSelected(card)}
                      >
                        <span className="role-ico">
                          <Icon size={18} />
                        </span>
                        <span className="badge">{card.badge}</span>
                        <strong>{card.title}</strong>
                        <span className="muted">{card.hint}</span>
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
            <Button type="button" onClick={() => setStep("details")}>
              Continue as {selected.title}
            </Button>
            <p className="auth-switch muted">
              Already have an account? <Link to="/login">Sign in</Link>
            </p>
          </div>
        ) : (
          <form className="auth-fields page-enter" onSubmit={onSubmit}>
            <button type="button" className="text-link" onClick={() => setStep("role")}>
              ← {selected.title}
            </button>
            <Input label="Name" value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" required />
            {needsOrg ? (
              <Input
                label={selected.role === UserRole.FARM_OPERATOR ? "Recovery partner name" : "Organisation name"}
                value={organizationName}
                onChange={(e) => setOrganizationName(e.target.value)}
                required
              />
            ) : null}
            <Input
              label="Email address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
            <Input
              label="Phone no."
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoComplete="tel"
            />
            <div className="password-wrap">
              <Input
                label="Password"
                type={show ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
              />
              <button type="button" className="text-link show-pass" onClick={() => setShow((v) => !v)}>
                {show ? "Hide" : "Show"}
              </button>
            </div>
            <Input
              label="Confirm password"
              type={show ? "text" : "password"}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
              error={confirm && !passwordsMatch ? "Passwords do not match." : undefined}
            />
            {error ? <p className="field-error">{error}</p> : null}
            <Button type="submit" disabled={disabled}>
              {busy ? "Creating account…" : "Create account"}
            </Button>
            <p className="muted">
              Already have an account? <Link to="/login">Sign in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
