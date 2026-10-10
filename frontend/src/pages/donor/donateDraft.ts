import type { DonationCategory } from "../../types/models";
import type { ConfirmedLocation } from "../../components/map/LocationPicker";

export type DonateDraft = {
  userId: string;
  step: number;
  category: DonationCategory | null;
  quantity: string;
  unit: string;
  notes: string;
  householdScale: "COOKED_LEFTOVERS" | "DRY_RATIONS" | "PRIVATE_FUNCTION";
  catererName: string;
  foodSource: string;
  packaging: "PACKED" | "UNPACKED";
  timing: string;
  customPickup: string;
  condition: "GOOD" | "FAIR";
  pickupDate: string;
  pickupSlot: string;
  checks: Record<string, string>;
  location: ConfirmedLocation;
  photos: File[];
  previews: string[];
};

let draft: DonateDraft | null = null;

export function peekDonateDraft(userId: string) {
  return draft?.userId === userId ? draft : null;
}

export function saveDonateDraft(next: DonateDraft) {
  draft = next;
}

export function clearDonateDraft() {
  draft = null;
}
