import { useI18n } from "../../providers/I18nProvider";

export function LanguageSelect({ compact = false }: { compact?: boolean }) {
  const { locale, locales, setLocale } = useI18n();
  return (
    <label className="lang">
      <span className="visually-hidden">Language</span>
      <select
        value={locale}
        aria-label="Language"
        onChange={(e) => setLocale(e.target.value as typeof locale)}
      >
        {locales.map((item) => (
          <option key={item.id} value={item.id} disabled={!item.ready}>
            {compact ? item.id.toUpperCase() : item.label}
            {item.ready ? "" : " — soon"}
          </option>
        ))}
      </select>
    </label>
  );
}
