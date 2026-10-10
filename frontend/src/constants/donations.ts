import { DonationCategory } from "../types/models";

export const HOUSEHOLD_CATEGORIES: {
  id: DonationCategory;
  label: string;
  hint: string;
  image?: string;
  tint: string;
}[] = [
  {
    id: DonationCategory.FOOD,
    label: "Food",
    hint: "Meals and unused groceries still good to share",
    image: "/images/food.jpg",
    tint: "food",
  },
  {
    id: DonationCategory.CLOTHES,
    label: "Clothes",
    hint: "Wearable garments in usable condition",
    image: "/images/clothes.jpg",
    tint: "clothes",
  },
  {
    id: DonationCategory.BOOKS,
    label: "Books",
    hint: "Textbooks, stories and study material",
    image: "/images/books.jpg",
    tint: "books",
  },
  {
    id: DonationCategory.TOYS,
    label: "Toys",
    hint: "Clean toys children can still enjoy",
    image: "/images/toys.jpg",
    tint: "toys",
  },
  {
    id: DonationCategory.OTHER,
    label: "Miscellaneous",
    hint: "Usable goods that still have a home",
    image: "/images/miscellaneous.jpg",
    tint: "other",
  },
];

export const OTHER_CATEGORY = HOUSEHOLD_CATEGORIES[4];

export const UNITS: Record<DonationCategory, string[]> = {
  FOOD: ["meals", "kg", "packets", "boxes", "litres"],
  CLOTHES: ["pieces", "pairs", "sets", "bags"],
  BOOKS: ["books", "sets", "boxes"],
  TOYS: ["pieces", "sets", "boxes"],
  OTHER: ["pieces", "boxes", "bags", "units"],
  ORGANIC_RECOVERY: ["kg", "bags", "crates"],
};

export const WIZARD_STEPS = ["What", "Details", "Pickup", "Review"];

export function categoryMeta(id: DonationCategory) {
  return HOUSEHOLD_CATEGORIES.find((item) => item.id === id) ?? OTHER_CATEGORY;
}

export function statusTone(status: string): "ok" | "amber" | "warn" | "mint" | "neutral" {
  const value = status.toUpperCase();
  if (["COMPLETED", "ACCEPTED", "DELIVERED", "RECOVERED"].includes(value)) return "ok";
  if (["IN_TRANSIT", "ASSIGNED", "PICKUP_PENDING", "MATCHED", "MATCHING"].includes(value)) return "amber";
  if (["RECOVERY_PENDING", "RECOVERY_ASSIGNED", "REJECTED", "CANCELLED", "EXPIRED"].includes(value)) return "warn";
  if (["SUBMITTED", "ASSESSING", "UNDER_REVIEW"].includes(value)) return "mint";
  return "neutral";
}

export const TRACK_STAGES = [
  { id: "SUBMITTED", label: "Submitted", match: ["SUBMITTED", "ASSESSING"] },
  { id: "MATCHED", label: "Matched", match: ["MATCHING", "MATCHED"] },
  { id: "ASSIGNED", label: "Assigned", match: ["ASSIGNED", "PICKUP_PENDING"] },
  { id: "PICKED", label: "Picked up", match: [] },
  { id: "TRANSIT", label: "In transit", match: ["IN_TRANSIT"] },
  { id: "DELIVERED", label: "Delivered", match: ["DELIVERED", "UNDER_REVIEW"] },
  { id: "ACCEPTED", label: "Accepted", match: ["ACCEPTED", "COMPLETED", "RECOVERED"] },
];

export function trackIndex(status: string) {
  const value = status.toUpperCase();
  if (["ACCEPTED", "COMPLETED", "RECOVERED"].includes(value)) return 6;
  if (["DELIVERED", "UNDER_REVIEW"].includes(value)) return 5;
  if (value === "IN_TRANSIT") return 4;
  if (["ASSIGNED", "PICKUP_PENDING"].includes(value)) return 2;
  if (["MATCHING", "MATCHED"].includes(value)) return 1;
  return 0;
}

export function formatWhen(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
