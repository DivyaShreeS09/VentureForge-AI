import { useState } from "react";
import { TextField } from "./TextField";

export interface TagInputProps {
  label: string;
  placeholder?: string;
  tags: string[];
  onChange: (tags: string[]) => void;
}

// Founder Input Experience Redesign: replaces a raw comma-separated free-text field (real typing
// friction, and the founder has to remember the delimiter). Still genuinely free text per tag —
// company names can't be chosen from a fixed list — but each one becomes a removable, visibly
// distinct token instead of an unstructured string, and Enter/comma commits a tag without the
// founder ever typing a comma character themselves.
export function TagInput({ label, placeholder, tags, onChange }: TagInputProps) {
  const [draft, setDraft] = useState("");

  function commit(raw: string) {
    const value = raw.trim().replace(/,$/, "");
    if (!value || tags.includes(value)) {
      setDraft("");
      return;
    }
    onChange([...tags, value]);
    setDraft("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit(draft);
    } else if (e.key === "Backspace" && draft === "" && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  }

  function removeTag(tag: string) {
    onChange(tags.filter((t) => t !== tag));
  }

  return (
    <div className="flex flex-col gap-2">
      {tags.length > 0 && (
        <ul className="flex flex-wrap gap-2" aria-label={`${label}, selected`}>
          {tags.map((tag) => (
            <li key={tag}>
              <span className="inline-flex items-center gap-1.5 rounded-forge-sm border border-forge-text/[.16] bg-forge-surface-1 py-1 pl-3 pr-1.5 text-forge-2 text-forge-text">
                {tag}
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  aria-label={`Remove ${tag}`}
                  className="flex h-5 w-5 items-center justify-center rounded-full text-forge-text-tertiary hover:bg-forge-text/[.12] hover:text-forge-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-forge-accent"
                >
                  <span aria-hidden="true">&times;</span>
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <TextField
        label={label}
        placeholder={placeholder}
        value={draft}
        onChange={setDraft}
        onKeyDown={handleKeyDown}
        onBlur={() => commit(draft)}
      />
    </div>
  );
}
