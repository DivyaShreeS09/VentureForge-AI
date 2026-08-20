import { useState } from "react";
import { Slider, TagInput, TextField } from "../../primitives";
import { ChoiceCard } from "../../primitives";
import type { InputMode } from "../../context/NewAnalysisContext";
import { useLanguage } from "../../context/LanguageContext";
import type {
  CompanyMetrics,
  MarketEvidence,
  RevenueAssumptions,
} from "../../types/api";

interface Props {
  mode: InputMode;
  companyMetrics: CompanyMetrics;
  revenueAssumptions: RevenueAssumptions;
  marketEvidence: MarketEvidence;
  onCompanyMetricsChange: (patch: Partial<CompanyMetrics>) => void;
  onRevenueAssumptionsChange: (
    patch: Partial<RevenueAssumptions>,
  ) => void;
  onMarketEvidenceChange: (patch: Partial<MarketEvidence>) => void;
}

const numberField = (value: number | null | undefined) =>
  value === null || value === undefined ? "" : String(value);

function LabeledField({
  label,
  ...rest
}: {
  label: string;
} & Omit<React.ComponentProps<typeof TextField>, "label">) {
  return (
    <div className="flex flex-col gap-1.5">
      <span
        aria-hidden="true"
        className="text-forge-1 text-forge-text-tertiary"
      >
        {label}
      </span>

      <TextField label={label} {...rest} />
    </div>
  );
}

const GEOGRAPHIES = [
  "United States",
  "Europe",
  "Global",
  "Other",
] as const;

export function AdditionalDetailsScene({
  mode,
  companyMetrics,
  revenueAssumptions,
  marketEvidence,
  onCompanyMetricsChange,
  onRevenueAssumptionsChange,
  onMarketEvidenceChange,
}: Props) {
  const { t } = useLanguage();

  const isAdvanced = mode === "advanced";

  const knownGeography = GEOGRAPHIES.includes(
    (marketEvidence.geography ?? "") as (typeof GEOGRAPHIES)[number],
  )
    ? marketEvidence.geography
    : marketEvidence.geography
      ? "Other"
      : null;

  const [showOtherGeography, setShowOtherGeography] = useState(
    knownGeography === "Other",
  );

  const priceTiers: { label: string; value: number | null }[] = [
    {
      label: t("additionalDetails.price.free"),
      value: 0,
    },
    {
      label: t("additionalDetails.price.5_20"),
      value: 12,
    },
    {
      label: t("additionalDetails.price.20_100"),
      value: 50,
    },
    {
      label: t("additionalDetails.price.100_plus"),
      value: 150,
    },
    {
      label: t("additionalDetails.price.notSure"),
      value: null,
    },
  ];

  const geographyOptions = [
    {
      value: "United States",
      label: t("additionalDetails.geography.unitedStates"),
    },
    {
      value: "Europe",
      label: t("additionalDetails.geography.europe"),
    },
    {
      value: "Global",
      label: t("additionalDetails.geography.global"),
    },
    {
      value: "Other",
      label: t("additionalDetails.geography.other"),
    },
  ] as const;

  return (
    <div className="flex w-full max-w-[720px] flex-col gap-8">
      {/* Page heading */}
      <div>
        <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
          {t("additionalDetails.title")}
        </h1>

        <p className="mt-3 text-forge-3 text-forge-text-secondary">
          {t("additionalDetails.description")}
        </p>
      </div>

      {/* Price */}
      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {t("additionalDetails.price.question")}
        </h2>

        {isAdvanced ? (
          <LabeledField
            label="Price per customer / month (USD)"
            placeholder="e.g. 49"
            type="number"
            min={0}
            value={numberField(
              revenueAssumptions.price_per_customer_usd,
            )}
            onChange={(v) =>
              onRevenueAssumptionsChange({
                price_per_customer_usd:
                  v === "" ? null : Number(v),
              })
            }
          />
        ) : (
          <div
            role="radiogroup"
            aria-label={t("additionalDetails.price.question")}
            className="grid grid-cols-2 gap-3 forge-sm:grid-cols-5"
          >
            {priceTiers.map((tier) => (
              <ChoiceCard
                key={tier.label}
                label={tier.label}
                selected={
                  revenueAssumptions.price_per_customer_usd ===
                  tier.value
                }
                onSelect={() =>
                  onRevenueAssumptionsChange({
                    price_per_customer_usd: tier.value,
                  })
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Customers */}
      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {t("additionalDetails.customers.question")}
        </h2>

        <LabeledField
          label={t("additionalDetails.customers.label")}
          placeholder={t("additionalDetails.customers.placeholder")}
          type="number"
          min={0}
          value={numberField(
            revenueAssumptions.initial_customers,
          )}
          onChange={(v) =>
            onRevenueAssumptionsChange({
              initial_customers: v === "" ? null : Number(v),
            })
          }
        />
      </div>

      {/* Advanced fields */}
      {isAdvanced && (
        <div className="grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
          <Slider
            label="Expected monthly growth"
            value={
              revenueAssumptions.monthly_growth_rate_pct ?? 0
            }
            min={0}
            max={50}
            step={1}
            formatValue={(v) => `${v}%`}
            onChange={(v) =>
              onRevenueAssumptionsChange({
                monthly_growth_rate_pct: v,
              })
            }
          />

          <Slider
            label="Gross margin (what's left after direct costs)"
            value={revenueAssumptions.gross_margin_pct ?? 70}
            min={0}
            max={100}
            step={5}
            formatValue={(v) => `${v}%`}
            onChange={(v) =>
              onRevenueAssumptionsChange({
                gross_margin_pct: v,
              })
            }
          />
        </div>
      )}

      {/* Geography */}
      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {t("additionalDetails.geography.question")}
        </h2>

        <div
          role="radiogroup"
          aria-label={t("additionalDetails.geography.question")}
          className="grid grid-cols-2 gap-3 forge-sm:grid-cols-4"
        >
          {geographyOptions.map((geo) => (
            <ChoiceCard
              key={geo.value}
              label={geo.label}
              selected={knownGeography === geo.value}
              onSelect={() => {
                if (geo.value === "Other") {
                  setShowOtherGeography(true);

                  onMarketEvidenceChange({
                    geography:
                      marketEvidence.geography &&
                      knownGeography === "Other"
                        ? marketEvidence.geography
                        : "",
                  });
                } else {
                  setShowOtherGeography(false);

                  onMarketEvidenceChange({
                    geography: geo.value,
                  });
                }
              }}
            />
          ))}
        </div>

        {showOtherGeography && (
          <TextField
            label={t("additionalDetails.geography.question")}
            placeholder={t(
              "additionalDetails.geography.placeholder",
            )}
            value={marketEvidence.geography ?? ""}
            onChange={(v) =>
              onMarketEvidenceChange({
                geography: v || null,
              })
            }
          />
        )}
      </div>

      {/* Competitors */}
      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {t("additionalDetails.competitors.question")}
        </h2>

        <TagInput
          label={t("additionalDetails.competitors.label")}
          placeholder={t(
            "additionalDetails.competitors.placeholder",
          )}
          tags={marketEvidence.known_competitors ?? []}
          onChange={(tags) =>
            onMarketEvidenceChange({
              known_competitors: tags,
            })
          }
        />
      </div>

      {/* Advanced company details */}
      {isAdvanced && (
        <div className="flex flex-col gap-4 border-t border-forge-text/[.08] pt-6">
          <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-text-tertiary">
            Company details, if you already have a company
          </p>

          <div className="grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
            <LabeledField
              label="How much funding have you raised? (USD)"
              placeholder="e.g. 50000"
              type="number"
              min={0}
              value={numberField(
                companyMetrics.total_funding_usd,
              )}
              onChange={(v) =>
                onCompanyMetricsChange({
                  total_funding_usd:
                    v === "" ? null : Number(v),
                })
              }
            />

            <LabeledField
              label="How many funding rounds?"
              placeholder="e.g. 1"
              type="number"
              min={0}
              value={numberField(
                companyMetrics.funding_rounds,
              )}
              onChange={(v) =>
                onCompanyMetricsChange({
                  funding_rounds:
                    v === "" ? null : Number(v),
                })
              }
            />

            <LabeledField
              label="What year did you start?"
              placeholder="e.g. 2024"
              type="number"
              min={1900}
              max={2100}
              value={numberField(
                companyMetrics.founded_year,
              )}
              onChange={(v) =>
                onCompanyMetricsChange({
                  founded_year:
                    v === "" ? null : Number(v),
                })
              }
            />

            <LabeledField
              label="Which country is your company in?"
              placeholder="e.g. usa"
              value={companyMetrics.country_code ?? ""}
              onChange={(v) =>
                onCompanyMetricsChange({
                  country_code: v || null,
                })
              }
            />
          </div>
        </div>
      )}
    </div>
  );
}