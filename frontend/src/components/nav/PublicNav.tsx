import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Wordmark } from "../ui/BrandMark";
import { LanguageSelect } from "../ui/LanguageSelect";

const LINKS = [
  { to: "/how-it-works", label: "How it works" },
  { to: "/organisations", label: "Organisations" },
  { to: "/impact", label: "Impact" },
  { to: "/about", label: "About" },
];

export function PublicNav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="public-nav">
      <div className="public-nav-inner">
        <Wordmark size={42} />
        <nav className="public-links" aria-label="Primary">
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="public-nav-actions">
          <LanguageSelect compact />
          <Link to="/login" className="text-link">
            Sign in
          </Link>
          <Link to="/register" className="btn btn-primary">
            Share surplus
          </Link>
          <button
            type="button"
            className="nav-toggle"
            aria-expanded={open}
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>
      <div className={`mobile-menu ${open ? "open" : ""}`}>
        {LINKS.map((link) => (
          <NavLink key={link.to} to={link.to} onClick={() => setOpen(false)}>
            {link.label}
          </NavLink>
        ))}
        <Link to="/login" onClick={() => setOpen(false)}>
          Sign in
        </Link>
        <LanguageSelect />
      </div>
    </header>
  );
}
