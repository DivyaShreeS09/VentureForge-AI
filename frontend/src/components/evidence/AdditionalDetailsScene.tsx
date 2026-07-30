import { useState } from "react";
import { Slider, TagInput, TextField } from "../../primitives";
import { ChoiceCard } from "../../primitives";
import type { InputMode } from "../../context/NewAnalysisContext";
import type { CompanyMetrics, MarketEvidence, RevenueAssumptions } from "../../types/api";

interface Props {
  mode: InputMode;
  companyMetrics: CompanyMetrics;
  revenueAssumptions: RevenueAssumptions;
  marketEvidence: MarketEvidence;
  onCompanyMetricsChange: (patch: Partial<CompanyMetrics>) => void;
  onRevenueAssumptionsChange: (patch: Partial<RevenueAssumptions>) => void;
  onMarketEvidenceChange: (patch: Partial<MarketEvidence>) => void;
}

const numberField = (value: number | null | undefined) => (value === null || value === undefined ? "" : String(value));

function LabeledField({ label, ...rest }: { label: string } & Omit<React.ComponentProps<typeof TextField>, "label">) {
  return (
    <div className="flex flex-col gap-1.5">
      <span aria-hidden="true" className="text-forge-1 text-forge-text-tertiary">
        {label}
      </span>
      <TextField label={label} {...rest} />
    </div>
  );
}

const PRICE_TIERS: { label: string; value: number | null }[] = [
  { label: "Free", value: 0 },
  { label: "$5–20/mo", value: 12 },
  { label: "$20–100/mo", value: 50 },
  { label: "$100+/mo", value: 150 },
  { label: "Not sure yet", value: null },
];

const GEOGRAPHIES = ["United States", "Europe", "Global", "Other"] as const;

/** Founder Input Experience Redesign. Every field here is genuinely optional and none can block
 * Continue — but the *set* of fields now depends on `mode` (see NewAnalysisContext): Beginner
 * shows only what a first-time founder can plausibly answer (a price range, a customer count, a
 * region, competitor names); Advanced adds exact pricing, growth/margin assumptions, and company
 * funding history — the fields the audit flagged as jargon-or-context-only-useful-when-known.
 * "Target market" and "Customer type" no longer exist as separate asks here — both were the same
 * real-world question already answered in Discovery ("who buys this?", the confirmed sector
 * chips), now merged in at submit time (see `buildMarketEvidence`) instead of asked twice. */
export function AdditionalDetailsScene({
  mode,
  companyMetrics,
  revenueAssumptions,
  marketEvidence,
  onCompanyMetricsChange,
  onRevenueAssumptionsChange,
  onMarketEvidenceChange,
}: Props) {
  const isAdvanced = mode === "advanced";
  const knownGeography = GEOGRAPHIES.includes((marketEvidence.geography ?? "") as (typeof GEOGRAPHIES)[number])
    ? marketEvidence.geography
    : marketEvidence.geography
      ? "Other"
      : null;
  const [showOtherGeography, setShowOtherGeography] = useState(knownGeography === "Other");

  return (
    <div className="flex w-full max-w-[720px] flex-col gap-8">
      <div>
        <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
          A few optional details, if you have them
        </h1>
        <p className="mt-3 text-forge-3 text-forge-text-secondary">
          These sharpen the revenue estimate and market read later — skip anything you don't know
          yet and Continue works either way.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          What would someone pay for this, per month?
        </h2>
        {isAdvanced ? (
          <LabeledField
            label="Price per customer / month (USD)"
            placeholder="e.g. 49"
            type="number"
            min={0}
            value={numberField(revenueAssumptions.price_per_customer_usd)}
            onChange={(v) => onRevenueAssumptionsChange({ price_per_customer_usd: v === "" ? null : Number(v) })}
          />
        ) : (
          <div role="radiogroup" aria-label="What would someone pay for this, per month?" className="grid grid-cols-2 gap-3 forge-sm:grid-cols-5">
            {PRICE_TIERS.map((tier) => (
              <ChoiceCard
                key={tier.label}
                label={tier.label}
                selected={revenueAssumptions.price_per_customer_usd === tier.value}
                onSelect={() => onRevenueAssumptionsChange({ price_per_customer_usd: tier.value })}
              />
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          How many customers do you have (or expect first)?
        </h2>
        <LabeledField
          label="Initial customer count"
          placeholder="e.g. 10"
          type="number"
          min={0}
          value={numberField(revenueAssumptions.initial_customers)}
          onChange={(v) => onRevenueAssumptionsChange({ initial_customers: v === "" ? null : Number(v) })}
        />
      </div>

      {isAdvanced && (
        <div className="grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
          <Slider
            label="Expected monthly growth"
            value={revenueAssumptions.monthly_growth_rate_pct ?? 0}
            min={0}
            max={50}
            step={1}
            formatValue={(v) => `${v}%`}
            onChange={(v) => onRevenueAssumptionsChange({ monthly_growth_rate_pct: v })}
          />
          <Slider
            label="Gross margin (what's left after direct costs)"
            value={revenueAssumptions.gross_margin_pct ?? 70}
            min={0}
            max={100}
            step={5}
            formatValue={(v) => `${v}%`}
            onChange={(v) => onRevenueAssumptionsChange({ gross_margin_pct: v })}
          />
        </div>
      )}

      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">Where are your first customers?</h2>
        <div role="radiogroup" aria-label="Where are your first customers?" className="grid grid-cols-2 gap-3 forge-sm:grid-cols-4">
          {GEOGRAPHIES.map((geo) => (
            <ChoiceCard
              key={geo}
              label={geo}
              selected={knownGeography === geo}
              onSelect={() => {
                if (geo === "Other") {
                  setShowOtherGeography(true);
                  onMarketEvidenceChange({ geography: marketEvidence.geography && knownGeography === "Other" ? marketEvidence.geography : "" });
                } else {
                  setShowOtherGeography(false);
                  onMarketEvidenceChange({ geography: geo });
                }
              }}
            />
          ))}
        </div>
        {showOtherGeography && (
          <TextField
            label="Where are your first customers?"
            placeholder="e.g. Southeast Asia"
            value={marketEvidence.geography ?? ""}
            onChange={(v) => onMarketEvidenceChange({ geography: v || null })}
          />
        )}
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          Who else is already solving this?
        </h2>
        <TagInput
          label="Known competitors or alternatives"
          placeholder="Type a name and press Enter"
          tags={marketEvidence.known_competitors ?? []}
          onChange={(tags) => onMarketEvidenceChange({ known_competitors: tags })}
        />
      </div>

      {isAdvanced && (
        <div className="flex flex-col gap-4 border-t border-forge-text/[.08] pt-6">
          <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-text-tertiary">
            Company &amp; funding, if this is already a registered company
          </p>
          <div className="grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
            <LabeledField
              label="Total funding raised (USD)"
              placeholder="e.g. 50000"
              type="number"
              min={0}
              value={numberField(companyMetrics.total_funding_usd)}
              onChange={(v) => onCompanyMetricsChange({ total_funding_usd: v === "" ? null : Number(v) })}
            />
            <LabeledField
              label="Funding rounds so far"
              placeholder="e.g. 1"
              type="number"
              min={0}
              value={numberField(companyMetrics.funding_rounds)}
              onChange={(v) => onCompanyMetricsChange({ funding_rounds: v === "" ? null : Number(v) })}
            />
            <LabeledField
              label="Year founded"
              placeholder="e.g. 2024"
              type="number"
              min={1900}
              max={2100}
              value={numberField(companyMetrics.founded_year)}
              onChange={(v) => onCompanyMetricsChange({ founded_year: v === "" ? null : Number(v) })}
            />
            <LabeledField
              label="Country code"
              placeholder="e.g. usa"
              value={companyMetrics.country_code ?? ""}
              onChange={(v) => onCompanyMetricsChange({ country_code: v || null })}
            />
          </div>
        </div>
      )}
    </div>
  );
}
