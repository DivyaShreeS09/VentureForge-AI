export interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  formatValue?: (value: number) => string;
}

// Founder Input Experience Redesign: a natural-range input (percentages, growth rates) reads and
// operates faster than typing a number, and a native <input type="range"> gets keyboard (arrow
// keys, Home/End), screen-reader (implicit role="slider" with min/max/valuenow), and touch support
// for free — no custom widget to maintain accessibility parity with. The visible numeric readout
// stays in sync so the value is never conveyed by position alone (Design Bible §13).
export function Slider({ label, value, min, max, step = 1, onChange, formatValue }: SliderProps) {
  const display = formatValue ? formatValue(value) : String(value);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="text-forge-1 text-forge-text-tertiary">{label}</span>
        <span className="text-forge-2 font-medium text-forge-text tabular-nums">{display}</span>
      </div>
      <input
        type="range"
        aria-label={label}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-forge-text/[.16] accent-forge-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-accent"
      />
    </div>
  );
}
