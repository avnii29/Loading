import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./providers/AuthProvider";
import { I18nProvider } from "./providers/I18nProvider";
import { ToastProvider } from "./providers/ToastProvider";
import { AppShell } from "./layouts/AppShell";
import { GuestRoute, ProtectedRoute } from "./layouts/ProtectedRoute";
import { Landing } from "./pages/Landing";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { HowItWorksPublic } from "./pages/public/HowItWorksPublic";
import { About } from "./pages/public/About";
import { PublicImpact } from "./pages/public/PublicImpact";
import { PublicOrganisations } from "./pages/public/PublicOrganisations";
import { DonorDashboard } from "./pages/donor/Dashboard";
import { Donate } from "./pages/donor/Donate";
import { DonationDetail } from "./pages/donor/DonationDetail";
import { Organizations } from "./pages/donor/Organizations";
import { Notifications } from "./pages/donor/Notifications";
import { History } from "./pages/donor/History";
import { DonorImpact } from "./pages/donor/Impact";
import { Profile } from "./pages/shared/Profile";
import { HowItWorks } from "./pages/shared/HowItWorks";
import {
  AdminAudit,
  AdminDestinations,
  AdminHome,
  DriverHistory,
  DriverHome,
  FarmHistory,
  FarmHome,
  OrganizationHistory,
  OrganizationHome,
  VolunteerHistory,
  VolunteerHome,
} from "./pages/roles/RoleShells";
import { UserRole } from "./types/models";

export default function App() {
  return (
    <I18nProvider>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/how-it-works" element={<HowItWorksPublic />} />
              <Route path="/organisations" element={<PublicOrganisations />} />
              <Route path="/impact" element={<PublicImpact />} />
              <Route path="/about" element={<About />} />
              <Route element={<GuestRoute />}>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
              </Route>

              <Route element={<ProtectedRoute roles={[UserRole.DONOR]} />}>
                <Route element={<AppShell />}>
                  <Route path="/app" element={<DonorDashboard />} />
                  <Route path="/app/donate" element={<Donate />} />
                  <Route path="/app/donations/:id" element={<DonationDetail />} />
                  <Route path="/app/organisations" element={<Organizations />} />
                  <Route path="/app/notifications" element={<Notifications />} />
                  <Route path="/app/history" element={<History />} />
                  <Route path="/app/impact" element={<DonorImpact />} />
                  <Route path="/app/profile" element={<Profile />} />
                  <Route path="/app/how-it-works" element={<HowItWorks />} />
                </Route>
              </Route>

              <Route element={<ProtectedRoute roles={[UserRole.VOLUNTEER]} />}>
                <Route element={<AppShell />}>
                  <Route path="/volunteer" element={<VolunteerHome />} />
                  <Route path="/volunteer/donate" element={<Donate />} />
                  <Route path="/volunteer/donations" element={<History />} />
                  <Route path="/volunteer/donations/:id" element={<DonationDetail />} />
                  <Route path="/volunteer/history" element={<VolunteerHistory />} />
                  <Route path="/volunteer/profile" element={<Profile />} />
                </Route>
              </Route>

              <Route element={<ProtectedRoute roles={[UserRole.DRIVER]} />}>
                <Route element={<AppShell />}>
                  <Route path="/driver" element={<DriverHome />} />
                  <Route path="/driver/history" element={<DriverHistory />} />
                  <Route path="/driver/profile" element={<Profile />} />
                </Route>
              </Route>

              <Route element={<ProtectedRoute roles={[UserRole.ORGANIZATION]} />}>
                <Route element={<AppShell />}>
                  <Route path="/organisation" element={<OrganizationHome />} />
                  <Route path="/organisation/history" element={<OrganizationHistory />} />
                  <Route path="/organisation/profile" element={<Profile />} />
                </Route>
              </Route>

              <Route element={<ProtectedRoute roles={[UserRole.FARM_OPERATOR]} />}>
                <Route element={<AppShell />}>
                  <Route path="/recovery" element={<FarmHome />} />
                  <Route path="/recovery/history" element={<FarmHistory />} />
                  <Route path="/recovery/profile" element={<Profile />} />
                </Route>
              </Route>

              <Route element={<ProtectedRoute roles={[UserRole.ADMIN]} />}>
                <Route element={<AppShell />}>
                  <Route path="/admin" element={<AdminHome />} />
                  <Route path="/admin/destinations" element={<AdminDestinations />} />
                  <Route path="/admin/audit" element={<AdminAudit />} />
                  <Route path="/admin/profile" element={<Profile />} />
                </Route>
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </I18nProvider>
  );
}
