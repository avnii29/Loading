import api from "./api";
import type { AppNotification, ImpactSummary } from "../types/models";

export async function listNotifications() {
  const { data } = await api.get<AppNotification[]>("/notifications");
  return data;
}

export async function markNotificationRead(id: string) {
  const { data } = await api.post<AppNotification>(`/notifications/${id}/read`);
  return data;
}

export async function getImpact() {
  const { data } = await api.get<ImpactSummary>("/impact");
  return data;
}
