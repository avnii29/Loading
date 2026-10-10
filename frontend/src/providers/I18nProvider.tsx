import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import { LOCALES, getMessages, type LocaleId } from "../i18n";
import type { Messages } from "../i18n/en";

type Ctx = {
  locale: LocaleId;
  t: Messages;
  locales: typeof LOCALES;
  setLocale: (id: LocaleId) => void;
};

const I18nContext = createContext<Ctx | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<LocaleId>("en");
  const ready = LOCALES.find((item) => item.id === locale)?.ready;
  const value = useMemo(
    () => ({
      locale: ready ? locale : "en",
      t: getMessages(ready ? locale : "en"),
      locales: LOCALES,
      setLocale: (id: LocaleId) => {
        const next = LOCALES.find((item) => item.id === id);
        if (next?.ready) setLocaleState(id);
      },
    }),
    [locale, ready],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
