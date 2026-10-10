import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../providers/AuthProvider";
import { ROLE_HOME } from "../constants/roles";
import { LoadingState } from "../components/ui/States";
import type { UserRole } from "../types/models";

export function ProtectedRoute({ roles }: { roles?: UserRole[] }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingState label="Opening your space…" />;
  if (!user) return <Navigate to="/login" replace />;
  const home = ROLE_HOME[user.role];
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={home || "/login"} replace />;
  }
  return <Outlet />;
}

export function GuestRoute() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingState />;
  const home = user ? ROLE_HOME[user.role] : "";
  if (home) return <Navigate to={home} replace />;
  return <Outlet />;
}
