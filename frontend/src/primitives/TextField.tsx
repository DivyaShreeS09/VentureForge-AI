import { forwardRef } from "react";

export interface TextFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "size"> {
  multiline?: boolean;
  onChange?: (value: string) => void;
  label?: string;
}

// Design System Bible §7 — borderless until focus, where a single hairline underline
// in the accent color appears. This is the one place the product breaks from "border
// only when ambiguous" (§14 Implementation Master Plan / §7 Design Bible), because a
// focused text field's edges are genuinely ambiguous without it.
export const TextField = forwardRef<HTMLInputElement | HTMLTextAreaElement, TextFieldProps>(
  function TextField({ multiline, onChange, label, className = "", ...rest }, ref) {
    const shared =
      "w-full bg-transparent text-forge-text placeholder:text-forge-text-tertiary " +
      "text-forge-3 font-body border-0 border-b-2 border-transparent " +
      "focus:border-forge-accent focus:outline-none transition-colors " +
      `${className}`;

    const handleChange = (
      e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => onChange?.(e.target.value);

    return (
      <label className="block w-full">
        {label && <span className="sr-only">{label}</span>}
        {multiline ? (
          <textarea
            ref={ref as React.Ref<HTMLTextAreaElement>}
            className={`${shared} min-h-[8rem] resize-none py-3`}
            onChange={handleChange}
            {...(rest as React.TextareaHTMLAttributes<HTMLTextAreaElement>)}
          />
        ) : (
          <input
            ref={ref as React.Ref<HTMLInputElement>}
            className={`${shared} py-3`}
            onChange={handleChange}
            {...rest}
          />
        )}
      </label>
    );
  },
);
