import api from "./api";
import type { Donation, DonationCategory, DonationStream } from "../types/models";

export type DonationCreate = {
  category: DonationCategory;
  stream?: DonationStream;
  title?: string;
  description?: string;
  quantity: number;
  unit: string;
  notes?: string;
  condition?: string;
  pickup_address?: string;
  pickup_latitude?: number;
  pickup_longitude?: number;
  location_accuracy_m?: number;
  location_source?: string;
  location_provider?: string;
  mappls_pin?: string;
  geocode_precision?: string;
  location_captured_at?: string;
  location_confirmed_at?: string;
  pickup_landmark?: string;
  pickup_pincode?: string;
  food_source?: string;
  packaging_state?: string;
  diet_type?: string;
  urgency?: string;
  quality_checklist?: Record<string, string | boolean>;
  idempotency_key?: string;
  preferred_centre_id?: string;
  cluster_window?: string;
  prepared_at?: string;
  pickup_deadline?: string;
  commercial?: {
    event_type?: string;
    estimated_servings?: number;
    packaging_state?: string;
    pickup_window_start?: string;
    pickup_window_end?: string;
  };
};

export async function createDonation(payload: DonationCreate) {
  const { data } = await api.post<Donation>("/donations", payload);
  return data;
}

export async function listDonations() {
  const { data } = await api.get<Donation[]>("/donations");
  return data;
}

export async function getDonation(id: string) {
  const { data } = await api.get<Donation>(`/donations/${id}`);
  return data;
}

export async function cancelDonation(id: string) {
  const { data } = await api.post<Donation>(`/donations/${id}/cancel`);
  return data;
}

export async function refreshVerificationCode(id: string) {
  const { data } = await api.post<{ verification_code: string; reference_code: string }>(
    `/donations/${id}/verification-code`,
  );
  return data;
}

export async function uploadDonationPhoto(id: string, file: File) {
  const body = new FormData();
  body.append("file", file);
  const { data } = await api.post<Donation>(`/donations/${id}/photos`, body, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function addQualityCheck(
  id: string,
  payload: {
    result: "ACCEPTABLE" | "REJECTED" | "REQUIRES_REVIEW" | "PENDING";
    notes?: string;
    stage?: "DONOR_SELF" | "PICKUP" | "INTAKE" | "RECOVERY" | "REVIEW";
    responses?: Record<string, string | boolean>;
  },
) {
  const { data } = await api.post<Donation>(`/donations/${id}/quality-checks`, payload);
  return data;
}
