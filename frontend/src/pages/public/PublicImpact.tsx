import { Link } from "react-router-dom";
import { PublicLayout } from "../../layouts/PublicLayout";

const METRICS = [
  ["Resources moved", "0"],
  ["Donations completed", "0"],
  ["Food recovered", "0"],
  ["Waste diverted", "0"],
];

export function PublicImpact() {
  return (
    <PublicLayout>
      <div className="wrap page-enter" style={{ padding: "48px 0 72px" }}>
        <p className="eyebrow">Impact</p>
        <h1 className="display" style={{ fontSize: "clamp(2.2rem, 5vw, 3.4rem)" }}>
          Counted only after a journey completes.
        </h1>
        <p className="lede">
          These numbers stay at zero until real deliveries are accepted. We do not preview or invent
          impact.
        </p>
        <div className="hero-dash">
          <div className="metric-grid">
            {METRICS.map(([label, value]) => (
              <div key={label} className="metric">
                <strong>{value}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
        <div style={{ marginTop: 28 }}>
          <Link to="/register" className="btn btn-primary">
            Share surplus
          </Link>
        </div>
      </div>
    </PublicLayout>
  );
}
