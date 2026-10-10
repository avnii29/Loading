export const UserRole = {
  DONOR: "DONOR",
  VOLUNTEER: "VOLUNTEER",
  DRIVER: "DRIVER",
  ORGANIZATION: "ORGANIZATION",
  FARM_OPERATOR: "FARM_OPERATOR",
  ADMIN: "ADMIN",
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const DonorType = {
  HOUSEHOLD: "HOUSEHOLD",
  RESTAURANT: "RESTAURANT",
  FUNCTION_HALL: "FUNCTION_HALL",
  INSTITUTION: "INSTITUTION",
} as const;
export type DonorType = (typeof DonorType)[keyof typeof DonorType];

export const DonationCategory = {
  FOOD: "FOOD",
  CLOTHES: "CLOTHES",
  BOOKS: "BOOKS",
  TOYS: "TOYS",
  ORGANIC_RECOVERY: "ORGANIC_RECOVERY",
  OTHER: "OTHER",
} as const;
export type DonationCategory = (typeof DonationCategory)[keyof typeof DonationCategory];

export const DonationStream = {
  HUMAN_CONSUMPTION: "HUMAN_CONSUMPTION",
  RECOVERY: "RECOVERY",
} as const;
export type DonationStream = (typeof DonationStream)[keyof typeof DonationStream];

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: UserRole;
  donor_type: DonorType | null;
  organization_name: string | null;
  organization_id: string | null;
  verification_status: string | null;
};

export type Donation = {
  id: string;
  reference_code: string;
  stream: DonationStream;
  category: DonationCategory;
  status: string;
  status_label: string;
  title: string | null;
  description: string | null;
  quantity: number;
  unit: string;
  notes: string | null;
  pickup_address: string | null;
  pickup_latitude: number | null;
  pickup_longitude: number | null;
  location_accuracy_m: number | null;
  location_source: string | null;
  location_captured_at?: string | null;
  location_confirmed_at?: string | null;
  pickup_landmark?: string | null;
  prepared_at: string | null;
  pickup_deadline: string | null;
  distribution_deadline: string | null;
  cluster_window?: string | null;
  destination_id: string | null;
  created_at: string;
  updated_at: string;
  photos: { id: string; url: string; mime_type: string; created_at: string }[];
  history: { from_status: string | null; to_status: string; note: string | null; created_at: string }[];
  quality_checks: { id: string; stage: string; result: string; notes: string | null; created_at: string }[];
  verification_code?: string | null;
  assignee_name?: string | null;
  eta_minutes?: number | null;
  is_donor?: boolean;
};

export type Organization = {
  id: string;
  name: string;
  description: string | null;
  verification_status: string;
  intake_status: string;
  address: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  mappls_pin?: string | null;
  location_provider?: string | null;
  accepted_categories: string[] | null;
  distance_km: number | null;
  phone?: string | null;
  source_note?: string | null;
  approximate?: boolean;
};

export type AppNotification = {
  id: string;
  type: string;
  title: string;
  body: string;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  created_at: string;
};

export type ImpactSummary = {
  meals_distributed: number;
  items_delivered: number;
  kg_recovered: number;
  donations_completed: number;
  has_events: boolean;
};
