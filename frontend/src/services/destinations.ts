import api from "./api";

export type DestinationOption = {
  id: string;
  name: string;
  facility_type?: string | null;
  address?: string | null;
  locality?: string | null;
  distance_km: number;
  distance_kind: string;
  approximate?: boolean;
  operational_status: string;
  verification_status?: string;
  category_hint?: boolean;
  eligible_as_final_destination?: boolean;
  caveat?: string | null;
  donor_preferred?: boolean;
  latitude?: number | null;
  longitude?: number | null;
};

export type RecommendationList = {
  search: string;
  distance_kind: string;
  note: string;
  options: DestinationOption[];
};

export async function recommendDestinations(lat: number, lng: number, category: string, limit = 3) {
  const { data } = await api.get<RecommendationList>("/organizations/recommendations", {
    params: { lat, lng, category, limit },
  });
  return data;
}

export async function destinationOptions(donationId: string) {
  const { data } = await api.get<{
    search: string;
    note: string;
    preferred_centre_id: string | null;
    preferred_name: string | null;
    preferred_in_shortlist: boolean;
    options: DestinationOption[];
  }>(`/logistics/donations/${donationId}/destination-options`);
  return data;
}

export async function proposeDestination(donationId: string, centreId: string, reason: string) {
  const { data } = await api.post<{ ok: boolean; proposed_centre_id: string; confirmed: boolean }>(
    `/logistics/donations/${donationId}/destination-proposal`,
    { centre_id: centreId, reason },
  );
  return data;
}
