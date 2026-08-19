import { useLanguage, type Language } from "../../context/LanguageContext";

const LANGUAGES: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "ta", label: "தமிழ்" },
  { value: "te", label: "తెలుగు" },
  { value: "hi", label: "हिन्दी" },
];

export function LanguageSelector() {
  const { language, setLanguage } = useLanguage();

  return (
    <div
      style={{
        position: "fixed",
        top: "24px",
        right: "24px",
        zIndex: 9999,
      }}
    >
      <label htmlFor="language-selector" className="sr-only">
        Language
      </label>

      <select
        id="language-selector"
        value={language}
        onChange={(event) =>
          setLanguage(event.target.value as Language)
        }
        className="rounded-lg border border-forge-border bg-forge-surface px-3 py-2 text-forge-2 text-forge-text outline-none transition focus:border-forge-accent"
      >
        {LANGUAGES.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>
    </div>
  );
}