import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Bell,
  Building2,
  ClipboardList,
  HeartHandshake,
  Home,
  Leaf,
  LogOut,
  Package,
  Route,
  Shield,
  Sparkles,
  Truck,
  UserRound,
} from "lucide-react";
import { Wordmark } from "../components/ui/BrandMark";
import { useAuth } from "../providers/AuthProvider";
import { UserRole } from "../types/models";
import type { LucideIcon } from "lucide-react";

type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean };

function navFor(role: UserRole): NavItem[] {
  if (role === UserRole.DONOR) {
    return [
      { to: "/app", label: "Home", icon: Home, end: true },
      { to: "/app/donate", label: "Donate", icon: HeartHandshake },
      { to: "/app/history", label: "My Donations", icon: Package },
      { to: "/app/organisations", label: "Organisations", icon: Building2 },
      { to: "/app/impact", label: "Impact", icon: Sparkles },
      { to: "/app/notifications", label: "Notifications", icon: Bell },
      { to: "/app/profile", label: "Profile", icon: UserRound },
    ];
  }
  if (role === UserRole.VOLUNTEER) {
    return [
      { to: "/volunteer", label: "My pickups", icon: Route, end: true },
      { to: "/volunteer/donate", label: "Donate", icon: HeartHandshake },
      { to: "/volunteer/donations", label: "My donations", icon: Package },
      { to: "/volunteer/profile", label: "Profile", icon: UserRound },
    ];
  }
  if (role === UserRole.DRIVER) {
    return [
      { to: "/driver", label: "Jobs", icon: Truck, end: true },
      { to: "/driver/history", label: "History", icon: ClipboardList },
      { to: "/driver/profile", label: "Profile", icon: UserRound },
    ];
  }
  if (role === UserRole.ORGANIZATION) {
    return [
      { to: "/organisation", label: "Intake", icon: Building2, end: true },
      { to: "/organisation/history", label: "History", icon: ClipboardList },
      { to: "/organisation/profile", label: "Profile", icon: UserRound },
    ];
  }
  if (role === UserRole.FARM_OPERATOR) {
    return [
      { to: "/recovery", label: "Recovery", icon: Leaf, end: true },
      { to: "/recovery/history", label: "History", icon: ClipboardList },
      { to: "/recovery/profile", label: "Profile", icon: UserRound },
    ];
  }
  return [
    { to: "/admin", label: "Operations", icon: Shield, end: true },
    { to: "/admin/destinations", label: "Destinations", icon: Building2 },
    { to: "/admin/audit", label: "Audit", icon: ClipboardList },
    { to: "/admin/profile", label: "Profile", icon: UserRound },
  ];
}

function mobileNav(role: UserRole, items: NavItem[]): NavItem[] {
  if (role === UserRole.DONOR) {
    return [
      items[0],
      items[1],
      items[2],
      items[3],
      items[6],
    ];
  }
  return items.slice(0, 5);
}

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  const items = navFor(user.role);
  const tabs = mobileNav(user.role, items);

  return (
    <div className="app-shell" data-theme={user.role}>
      <aside className="sidenav">
        <Wordmark to={items[0].to} size={40} />
        <nav>
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} end={item.end}>
                <Icon size={18} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="sidenav-foot">
          <button
            type="button"
            className="nav-item"
            onClick={async () => {
              await logout();
              navigate("/");
            }}
          >
            <LogOut size={18} />
            Sign out
          </button>
        </div>
      </aside>

      <div>
        <header className="mobile-topbar">
          <Wordmark to={items[0].to} size={36} />
          {user.role === UserRole.DONOR ? (
            <NavLink to="/app/notifications" aria-label="Notifications">
              <Bell size={20} />
            </NavLink>
          ) : (
            <span className="avatar">{user.full_name.slice(0, 1).toUpperCase()}</span>
          )}
        </header>
        <main className="app-main page-enter">
          <Outlet />
        </main>
      </div>

      <nav className="tabbar" aria-label="Primary">
        {tabs.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <Icon size={18} />
              {item.label}
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}
