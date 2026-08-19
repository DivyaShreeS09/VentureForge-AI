import { useLanguage, type Language } from "../../context/LanguageContext";

const languages: { code: Language; label: string }[] = [
  { code: "en", label: "English" },
  { code: "ta", label: "தமிழ்" },
  { code: "te", label: "తెలుగు" },
  { code: "hi", label: "हिन्दी" },
];

export function LanguageSelector() {
  const { language, setLanguage } = useLanguage();

  return (
    <select
      value={language}
      onChange={(event) =>
        setLanguage(event.target.value as Language)
      }
      aria-label="Select language"
      className="rounded-lg border border-forge-border bg-forge-surface px-3 py-2 text-sm text-forge-text shadow-lg outline-none"
    >
      {languages.map((item) => (
        <option key={item.code} value={item.code}>
          {item.label}
        </option>
      ))}
    </select>
  );
}