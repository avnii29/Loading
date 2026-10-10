import { Link } from "react-router-dom";
import { PublicLayout } from "../../layouts/PublicLayout";

const STEPS = [
  ["Surplus", "You share food, clothes, books, toys or other usable items."],
  ["Assess", "The system understands the category and which stream it belongs to."],
  ["Match", "A destination is matched only when a verified record exists."],
  ["Move", "A volunteer or driver is assigned when that work is actually ready."],
  ["Accept / Recover", "The destination verifies. Recovery is a separate, later decision."],
  ["Impact", "Completed deliveries are counted. Nothing is invented beforehand."],
];

export function HowItWorksPublic() {
  return (
    <PublicLayout>
      <div className="wrap page-enter" style={{ padding: "48px 0 72px" }}>
        <p className="eyebrow">How it works</p>
        <h1 className="display" style={{ fontSize: "clamp(2.2rem, 5vw, 3.4rem)" }}>
          A careful loop from extra to useful.
        </h1>
        <p className="lede">
          Anuvarthan is a civic logistics product. It coordinates surplus, movement and destinations —
          it does not invent them.
        </p>
        <div className="landing-grid">
          {STEPS.map(([title, body]) => (
            <article key={title}>
              <h3>{title}</h3>
              <p className="muted">{body}</p>
            </article>
          ))}
        </div>
        <Link to="/register" className="btn btn-primary">
          Share surplus
        </Link>
      </div>
    </PublicLayout>
  );
}
