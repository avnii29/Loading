import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="state" role="status">
      <span className="spinner" aria-hidden />
      <p>{label}</p>
    </div>
  );
}

export function EmptyState({
  title,
  body,
  icon,
}: {
  title: string;
  body?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="state state-empty">
      <div className="state-icon" aria-hidden>
        {icon ?? <Inbox size={22} />}
      </div>
      <h3>{title}</h3>
      {body ? <p className="muted">{body}</p> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <h3>We hit a snag</h3>
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-header">
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h2>{title}</h2>
      {children}
    </header>
  );
}

export function SectionHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="section-head">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

export function StatusBadge({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "ok" | "amber" | "warn" | "mint" | "neutral";
}) {
  return <span className={`badge badge-${tone}`}>{label}</span>;
}

export function ProgressIndicator({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="wizard-progress" aria-label="Progress">
      {steps.map((step, index) => (
        <li
          key={step}
          className={index === current ? "is-current" : index < current ? "is-done" : ""}
          aria-current={index === current ? "step" : undefined}
        >
          <span className="step-dot">{index < current ? "✓" : index + 1}</span>
          {step}
        </li>
      ))}
    </ol>
  );
}
