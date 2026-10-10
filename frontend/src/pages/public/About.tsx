import { PublicLayout } from "../../layouts/PublicLayout";

export function About() {
  return (
    <PublicLayout>
      <div className="wrap page-enter" style={{ padding: "48px 0 72px", maxWidth: 760 }}>
        <p className="eyebrow">Anuvarthan</p>
        <h1 className="display" style={{ fontSize: "clamp(2.2rem, 5vw, 3.4rem)" }}>
          Pass It Forward.
        </h1>
        <p className="lede">
          Anuvarthan helps surplus food, resources and usable goods reach the right destination before
          they become waste.
        </p>
        <div className="stack" style={{ gap: 20 }}>
          <article className="surface-card">
            <h3>Civic, not extractive</h3>
            <p className="muted">
              Household donations are not charged. Commercial recovery logistics may later include a
              contribution — that payment engine is not live yet.
            </p>
          </article>
          <article className="surface-card">
            <h3>Two streams, never mixed</h3>
            <p className="muted">
              Food meant for people stays separate from recovery material. A rejected human-consumption
              donation is re-evaluated before it can enter recovery.
            </p>
          </article>
          <article className="surface-card">
            <h3>Verified destinations only</h3>
            <p className="muted">
              Organisations and recovery partners appear in matching after Anuvarthan verifies them.
              Self-signup does not grant operational trust.
            </p>
          </article>
        </div>
      </div>
    </PublicLayout>
  );
}
