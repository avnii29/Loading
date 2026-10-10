import { Link } from "react-router-dom";

export function BrandMark({ size = 44 }: { size?: number }) {
  return (
    <span className="brand-mark-wrap" style={{ width: size, height: size }}>
      <img src="/brand/logo.png" alt="Anuvarthan" className="brand-mark" />
    </span>
  );
}

export function Wordmark({
  to = "/",
  size = 44,
}: {
  to?: string;
  size?: number;
}) {
  return (
    <Link to={to} className="wordmark">
      <BrandMark size={size} />
      <span className="wordmark-copy">
        <span className="wordmark-text">Anuvarthan</span>
        <span className="wordmark-tag">Pass It Forward.</span>
      </span>
    </Link>
  );
}
