export function HowItWorks() {
  return (
    <article className="wizard-panel">
      <p className="eyebrow">About</p>
      <h1>How Anuvarthan works</h1>
      <div className="landing-grid" style={{ paddingTop: 24 }}>
        <article className="surface-card">
          <h3>Share</h3>
          <p className="muted">You share surplus — food, clothes, books, toys, or other usable items.</p>
        </article>
        <article className="surface-card">
          <h3>Assess</h3>
          <p className="muted">The system assesses what it is and which stream it belongs to.</p>
        </article>
        <article className="surface-card">
          <h3>Match</h3>
          <p className="muted">A destination is matched only when a real, verified record exists.</p>
        </article>
        <article className="surface-card">
          <h3>Move</h3>
          <p className="muted">Movement is assigned to a volunteer or driver when that work is actually ready.</p>
        </article>
        <article className="surface-card">
          <h3>Accept</h3>
          <p className="muted">The destination verifies and accepts. Impact is counted only then.</p>
        </article>
        <article className="surface-card">
          <h3>Honest</h3>
          <p className="muted">Household donations are not charged. Commercial recovery payment is not live yet.</p>
        </article>
      </div>
    </article>
  );
}
