import { Link } from "react-router-dom";
import { Building2, MapPin, ShieldCheck } from "lucide-react";
import { PublicLayout } from "../../layouts/PublicLayout";

export function PublicOrganisations() {
  return (
    <PublicLayout>
      <div className="wrap page-enter" style={{ padding: "48px 0 72px" }}>
        <p className="eyebrow">Organisations</p>
        <h1 className="display" style={{ fontSize: "clamp(2.2rem, 5vw, 3.4rem)" }}>
          Destinations that can actually receive.
        </h1>
        <p className="lede">
          Verified organisations appear on the map after you sign in. Nothing is listed here until those
          records exist.
        </p>
        <div className="landing-grid">
          <article>
            <span className="story-icon">
              <ShieldCheck size={18} />
            </span>
            <h3>Verified first</h3>
            <p className="muted">Signup creates a profile. Anuvarthan decides verification separately.</p>
          </article>
          <article>
            <span className="story-icon">
              <Building2 size={18} />
            </span>
            <h3>Intake, not a directory dump</h3>
            <p className="muted">Each destination shows what it can accept when that data is real.</p>
          </article>
          <article>
            <span className="story-icon">
              <MapPin size={18} />
            </span>
            <h3>Nearby when you allow it</h3>
            <p className="muted">Distance appears only after you share a location.</p>
          </article>
        </div>
        <Link to="/register" className="btn btn-primary">
          Join as an organisation
        </Link>
      </div>
    </PublicLayout>
  );
}
