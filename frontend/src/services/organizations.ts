import api from "./api";
import type { Organization } from "../types/models";

export async function listOrganizations(coords?: { lat: number; lng: number }) {
  const { data } = await api.get<Organization[]>("/organizations", {
    params: coords ? { lat: coords.lat, lng: coords.lng } : undefined,
  });
  return data;
}

export async function getMyOrganization() {
  const { data } = await api.get<Organization>("/organizations/me");
  return data;
}

export async function updateMyOrganization(payload: Partial<Organization> & { capacity_notes?: string }) {
  const { data } = await api.patch<Organization>("/organizations/me", payload);
  return data;
}
