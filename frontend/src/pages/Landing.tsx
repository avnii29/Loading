import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Bike,
  Building2,
  Handshake,
  Package,
  Route,
  Search,
  Sparkles,
} from "lucide-react";
import { PublicLayout } from "../layouts/PublicLayout";

const JOURNEY = [
  { title: "Surplus", body: "Someone has extra food, clothes, books or usable goods.", icon: Package },
  { title: "Assess", body: "We understand what it is and which stream it belongs to.", icon: Search },
  { title: "Match", body: "A verified destination is chosen only when one actually exists.", icon: Handshake },
  { title: "Move", body: "A volunteer or driver is assigned when that work is ready.", icon: Bike },
  { title: "Accept / Recover", body: "The destination verifies, accepts, or routes recovery separately.", icon: Building2 },
  { title: "Impact", body: "Completed journeys are counted. Nothing is invented beforehand.", icon: Sparkles },
];

function HeroStory() {
  return (
    <div className="hero-story" aria-hidden>
      <div className="story-map">
        <svg className="story-route" viewBox="0 0 420 420" fill="none">
          <path
            d="M48 92 C 120 80, 140 180, 190 210 C 250 246, 250 140, 330 92 C 360 180, 280 300, 340 340"
            stroke="#E65C24"
            strokeWidth="3"
            strokeDasharray="8 8"
            opacity="0.7"
          />
        </svg>
      </div>
      <article className="story-card story-package">
        <span className="story-icon">
          <Package size={18} />
        </span>
        <div>
          <strong>Donation ready</strong>
          <small>Surplus waiting to move</small>
        </div>
      </article>
      <article className="story-card story-rider">
        <span className="story-icon">
          <Bike size={18} />
        </span>
        <div>
          <strong>Local rider</strong>
          <small>Assigned when a real job exists</small>
        </div>
      </article>
      <article className="story-card story-org">
        <span className="story-icon">
          <Building2 size={18} />
        </span>
        <div>
          <strong>Organisation</strong>
          <small>Verified destination only</small>
        </div>
      </article>
      <span className="story-chip">
        <Route size={14} /> Route opens after a match
      </span>
      <article className="story-card story-impact">
        <span className="story-icon">
          <Sparkles size={18} />
        </span>
        <div>
          <strong>Impact</strong>
          <small>Counted after delivery</small>
        </div>
      </article>
    </div>
  );
}

export function Landing() {
  const [active, setActive] = useState(0);

  return (
    <PublicLayout>
      <div className="wrap page-enter">
        <section className="hero-split">
          <div>
            <p className="eyebrow">Anuvarthan</p>
            <h1 className="display">Pass It Forward.</h1>
            <p className="lede">
              Helping surplus food, resources and usable goods reach the right destination before they
              become waste.
            </p>
            <div className="hero-actions">
              <Link to="/register" className="btn btn-primary">
                Share surplus
              </Link>
              <a href="#how" className="btn btn-secondary">
                See how it works
              </a>
            </div>
          </div>
          <HeroStory />
        </section>

        <section id="how" className="journey-block">
          <div className="journey-head">
            <div>
              <p className="eyebrow">The loop</p>
              <h2>From extra to useful, without the waste.</h2>
            </div>
            <p className="muted" style={{ maxWidth: 360 }}>
              {JOURNEY[active].body}
            </p>
          </div>
          <div className="journey-track">
            {JOURNEY.map((step, index) => {
              const Icon = step.icon;
              return (
                <button
                  key={step.title}
                  type="button"
                  className={`journey-step ${active === index ? "is-on" : ""}`}
                  onClick={() => setActive(index)}
                  onMouseEnter={() => setActive(index)}
                >
                  <span>
                    <Icon size={16} />
                  </span>
                  <strong>{step.title}</strong>
                  <small className="muted">{step.body}</small>
                </button>
              );
            })}
          </div>
        </section>

        <section className="landing-grid">
          <article>
            <p className="eyebrow">Human</p>
            <h3>Warm, not administrative</h3>
            <p className="muted">Share what is extra. The system coordinates movement, verification and destination.</p>
          </article>
          <article>
            <p className="eyebrow">Streams</p>
            <h3>Food and recovery stay apart</h3>
            <p className="muted">Human-consumption surplus never mixes with recovery material for convenience.</p>
          </article>
          <article>
            <p className="eyebrow">Honest</p>
            <h3>Real journeys only</h3>
            <p className="muted">No invented organisations, routes or impact. Empty states stay empty until work happens.</p>
          </article>
        </section>

        <section className="surface-card" style={{ marginBottom: 48 }}>
          <p className="eyebrow">Ready</p>
          <h2>Start with what you already have.</h2>
          <p className="lede">Households, kitchens, halls and institutions can all share surplus through the same careful loop.</p>
          <Link to="/register" className="btn btn-primary">
            Create an account <ArrowRight size={16} />
          </Link>
        </section>
      </div>
    </PublicLayout>
  );
}
