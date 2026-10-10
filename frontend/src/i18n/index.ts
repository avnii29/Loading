import { en, type Messages } from "./en";

export const LOCALES = [
  { id: "en", label: "English", ready: true },
  { id: "te", label: "తెలుగు", ready: false },
  { id: "hi", label: "हिन्दी", ready: false },
  { id: "ta", label: "தமிழ்", ready: false },
  { id: "kn", label: "ಕನ್ನಡ", ready: false },
  { id: "ml", label: "മലയാളം", ready: false },
  { id: "mr", label: "मराठी", ready: false },
  { id: "bn", label: "বাংলা", ready: false },
] as const;

export type LocaleId = (typeof LOCALES)[number]["id"];

const catalog: Record<string, Messages> = { en };

export function getMessages(locale: LocaleId): Messages {
  return catalog[locale] ?? en;
}
