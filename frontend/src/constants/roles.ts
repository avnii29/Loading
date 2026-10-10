import { UserRole } from "../types/models";

export const PUBLIC_ROLES: { value: UserRole; label: string; hint: string }[] = [
  { value: UserRole.DONOR, label: "Donor", hint: "Share surplus from a home, kitchen, hall or institution." },
  { value: UserRole.VOLUNTEER, label: "Volunteer", hint: "Help move clustered neighbourhood donations." },
  { value: UserRole.DRIVER, label: "Driver", hint: "Take commercial and recovery logistics jobs." },
  { value: UserRole.ORGANIZATION, label: "Organisation", hint: "Receive, review and distribute surplus." },
  { value: UserRole.FARM_OPERATOR, label: "Recovery Partner", hint: "Receive compatible recovery material only." },
];

export const DONOR_TYPES = [
  { value: "HOUSEHOLD", label: "Household" },
  { value: "RESTAURANT", label: "Restaurant" },
  { value: "FUNCTION_HALL", label: "Function hall" },
  { value: "INSTITUTION", label: "Institution" },
] as const;

export function donationListPath(role: UserRole) {
  return role === UserRole.VOLUNTEER ? "/volunteer/donations" : "/app/history";
}

export function donationDetailPath(role: UserRole, id: string) {
  return role === UserRole.VOLUNTEER ? `/volunteer/donations/${id}` : `/app/donations/${id}`;
}

export function homePath(role: UserRole) {
  return ROLE_HOME[role];
}

export const ROLE_HOME: Record<UserRole, string> = {
  DONOR: "/app",
  VOLUNTEER: "/volunteer",
  DRIVER: "/driver",
  ORGANIZATION: "/organisation",
  FARM_OPERATOR: "/recovery",
  ADMIN: "/admin",
};

export const ROLE_LABEL: Record<UserRole, string> = {
  DONOR: "Donor",
  VOLUNTEER: "Volunteer",
  DRIVER: "Driver",
  ORGANIZATION: "Organisation",
  FARM_OPERATOR: "Recovery Partner",
  ADMIN: "Admin",
};
