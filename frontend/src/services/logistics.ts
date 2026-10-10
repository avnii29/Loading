import api from "./api";

export type VolunteerOffer = {
  id: string;
  donation_id: string;
  status: string;
  priority_class: string | null;
  summary: string | null;
  area_label: string | null;
  created_at: string;
  expires_at: string;
  seconds_remaining: number;
  category?: string | null;
  quantity?: string | null;
  unit?: string | null;
  description?: string | null;
  pickup_schedule?: string | null;
  pickup_latitude?: number | null;
  pickup_longitude?: number | null;
  reference_code?: string | null;
};

export type LogisticsAssignmentRow = {
  id: string;
  donation_id: string;
  status: string;
  reference_code: string | null;
  category: string | null;
  quantity: string | null;
  unit: string | null;
  pickup_address: string | null;
  pickup_latitude: number | null;
  pickup_longitude: number | null;
  priority_class: string | null;
  donation_status: string | null;
  pickup_schedule?: string | null;
};

export async function listOffers() {
  const { data } = await api.get<VolunteerOffer[]>("/logistics/offers");
  return data;
}

export async function acceptOffer(offerId: string) {
  const { data } = await api.post<{ assignment_id: string; donation_id: string; status: string }>(
    `/logistics/offers/${offerId}/accept`,
  );
  return data;
}

export async function declineOffer(offerId: string) {
  const { data } = await api.post<{ id: string; status: string }>(`/logistics/offers/${offerId}/decline`);
  return data;
}

export async function listAssignments() {
  const { data } = await api.get<LogisticsAssignmentRow[]>("/logistics/assignments");
  return data;
}

export async function markArrived(donationId: string) {
  const { data } = await api.post<{ ok: boolean; shown_to: string; message: string }>(
    `/logistics/donations/${donationId}/handoff/arrived`,
  );
  return data;
}

export async function issueHandoff(donationId: string, stage: "PICKUP" | "DELIVERY") {
  const { data } = await api.post<{
    stage: string;
    delivery: string;
    message: string;
    code: string;
    ttl_seconds: number;
  }>(`/logistics/donations/${donationId}/handoff/issue`, { stage });
  return data;
}

export type CollectorLocation = {
  available: boolean;
  freshness: "live" | "recent" | "stale" | "unavailable";
  latitude?: number;
  longitude?: number;
  accuracy_m?: number | null;
  heading_deg?: number | null;
  speed_mps?: number | null;
  recorded_at?: string;
  assignment_status?: string;
  assignee_name?: string | null;
};

export async function publishJobLocation(
  assignmentId: string,
  point: { lat: number; lng: number; accuracy?: number },
  extras?: { heading_deg?: number | null; speed_mps?: number | null },
) {
  const { data } = await api.post<{ id: string; stored: boolean; recorded_at: string; freshness: string }>(
    `/logistics/assignments/${assignmentId}/location`,
    {
      latitude: point.lat,
      longitude: point.lng,
      accuracy_m: point.accuracy != null ? Math.round(point.accuracy) : null,
      heading_deg: extras?.heading_deg ?? null,
      speed_mps: extras?.speed_mps ?? null,
    },
  );
  return data;
}

export async function getCollectorLocation(donationId: string) {
  const { data } = await api.get<CollectorLocation>(`/logistics/donations/${donationId}/collector-location`);
  return data;
}

export async function verifyHandoff(donationId: string, stage: "PICKUP" | "DELIVERY", code: string) {
  const { data } = await api.post<{ ok: boolean; stage: string; donation_status: string }>(
    `/logistics/donations/${donationId}/handoff/verify`,
    { stage, code },
  );
  return data;
}
