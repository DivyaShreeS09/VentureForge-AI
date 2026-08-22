import { useState } from "react";
import {
  ChoiceCard,
  Slider,
  TagInput,
  TextField,
} from "../../primitives";
import type { InputMode } from "../../context/NewAnalysisContext";
import { useLanguage } from "../../context/LanguageContext";
import type {
  CompanyMetrics,
  MarketEvidence,
  RevenueAssumptions,
} from "../../types/api";
import { voiceAgent } from "../voice/VoiceAgent";

interface Props {
  mode: InputMode;
  companyMetrics: CompanyMetrics;
  revenueAssumptions: RevenueAssumptions;
  marketEvidence: MarketEvidence;

  onCompanyMetricsChange: (
    patch: Partial<CompanyMetrics>,
  ) => void;

  onRevenueAssumptionsChange: (
    patch: Partial<RevenueAssumptions>,
  ) => void;

  onMarketEvidenceChange: (
    patch: Partial<MarketEvidence>,
  ) => void;
}

const numberField = (
  value: number | null | undefined,
) =>
  value === null || value === undefined
    ? ""
    : String(value);

function LabeledField({
  label,
  ...rest
}: {
  label: string;
} & Omit<
  React.ComponentProps<typeof TextField>,
  "label"
>) {
  return (
    <div className="flex flex-col gap-1.5">
      <span
        aria-hidden="true"
        className="text-forge-1 text-forge-text-tertiary"
      >
        {label}
      </span>

      <TextField
        label={label}
        {...rest}
      />
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

  const isAdvanced =
    mode === "advanced";

  const knownGeography =
    GEOGRAPHIES.includes(
      (marketEvidence.geography ??
        "") as (typeof GEOGRAPHIES)[number],
    )
      ? marketEvidence.geography
      : marketEvidence.geography
        ? "Other"
        : null;

  const [
    showOtherGeography,
    setShowOtherGeography,
  ] = useState(
    knownGeography === "Other",
  );

  const title =
    t("additionalDetails.title");

  const description =
    t("additionalDetails.description");

  const priceQuestion =
    t(
      "additionalDetails.price.question",
    );

  const customersQuestion =
    t(
      "additionalDetails.customers.question",
    );

  const geographyQuestion =
    t(
      "additionalDetails.geography.question",
    );

  const competitorsQuestion =
    t(
      "additionalDetails.competitors.question",
    );

  const priceTiers: {
    label: string;
    value: number | null;
  }[] = [
    {
      label: t(
        "additionalDetails.price.free",
      ),
      value: 0,
    },
    {
      label: t(
        "additionalDetails.price.5_20",
      ),
      value: 12,
    },
    {
      label: t(
        "additionalDetails.price.20_100",
      ),
      value: 50,
    },
    {
      label: t(
        "additionalDetails.price.100_plus",
      ),
      value: 150,
    },
    {
      label: t(
        "additionalDetails.price.notSure",
      ),
      value: null,
    },
  ];

  const geographyOptions = [
    {
      value: "United States",
      label: t(
        "additionalDetails.geography.unitedStates",
      ),
    },
    {
      value: "Europe",
      label: t(
        "additionalDetails.geography.europe",
      ),
    },
    {
      value: "Global",
      label: t(
        "additionalDetails.geography.global",
      ),
    },
    {
      value: "Other",
      label: t(
        "additionalDetails.geography.other",
      ),
    },
  ] as const;

  const expectedGrowthLabel =
    "Expected monthly growth";

  const grossMarginLabel =
    "Gross margin (what's left after direct costs)";

  const companyDetailsTitle =
    "Company details, if you already have a company";

  /*
   * Find the visible price option
   * matching the current stored value.
   */
  const selectedPrice =
    priceTiers.find(
      (tier) =>
        tier.value ===
        revenueAssumptions.price_per_customer_usd,
    )?.label ?? "";

  /*
   * Find translated geography
   * corresponding to current selection.
   */
  const selectedGeography =
    geographyOptions.find(
      (geo) =>
        geo.value ===
        knownGeography,
    )?.label ??
    marketEvidence.geography ??
    "";

  /*
   * ONE SPEAKER FOR THE WHOLE PAGE.
   */
  function speakWholePage() {
    const competitors =
      marketEvidence
        .known_competitors?.length
        ? marketEvidence
            .known_competitors
            .join(", ")
        : "No competitors entered yet.";

    const speechParts: string[] = [
      title,
      description,

      priceQuestion,
    ];

    if (isAdvanced) {
      speechParts.push(
        revenueAssumptions
          .price_per_customer_usd !==
          null &&
          revenueAssumptions
            .price_per_customer_usd !==
            undefined
          ? `Current price per customer per month is ${revenueAssumptions.price_per_customer_usd} dollars.`
          : "No price entered yet.",
      );
    } else {
      speechParts.push(
        `Options are ${priceTiers
          .map((tier) => tier.label)
          .join(", ")}.`,
      );

      speechParts.push(
        selectedPrice
          ? `Selected answer is ${selectedPrice}.`
          : "No price option selected yet.",
      );
    }

    speechParts.push(
      customersQuestion,

      revenueAssumptions
        .initial_customers !==
        null &&
        revenueAssumptions
          .initial_customers !==
          undefined
        ? `Current customer count is ${revenueAssumptions.initial_customers}.`
        : "No customer count entered yet.",
    );

    if (isAdvanced) {
      speechParts.push(
        `${expectedGrowthLabel}. Current value is ${
          revenueAssumptions
            .monthly_growth_rate_pct ??
          0
        } percent.`,

        `${grossMarginLabel}. Current value is ${
          revenueAssumptions
            .gross_margin_pct ??
          70
        } percent.`,
      );
    }

    speechParts.push(
      geographyQuestion,

      `Options are ${geographyOptions
        .map((geo) => geo.label)
        .join(", ")}.`,

      selectedGeography
        ? `Selected geography is ${selectedGeography}.`
        : "No geography selected yet.",

      competitorsQuestion,

      `Current competitors are ${competitors}.`,
    );

    if (isAdvanced) {
      speechParts.push(
        companyDetailsTitle,

        companyMetrics
          .total_funding_usd !==
          null &&
          companyMetrics
            .total_funding_usd !==
            undefined
          ? `Funding raised is ${companyMetrics.total_funding_usd} dollars.`
          : "No funding amount entered yet.",

        companyMetrics
          .funding_rounds !==
          null &&
          companyMetrics
            .funding_rounds !==
            undefined
          ? `Funding rounds are ${companyMetrics.funding_rounds}.`
          : "No funding rounds entered yet.",

        companyMetrics
          .founded_year !==
          null &&
          companyMetrics
            .founded_year !==
            undefined
          ? `Company started in ${companyMetrics.founded_year}.`
          : "No founding year entered yet.",

        companyMetrics.country_code
          ? `Company country is ${companyMetrics.country_code}.`
          : "No company country entered yet.",
      );
    }

    const speechText =
      speechParts
        .filter(Boolean)
        .join(" ");

    voiceAgent.speak(
      speechText,
      {
        rate: 0.85,
        pitch: 1,
        volume: 1,
        lang: "en-US",
      },
    );
  }

  return (
    <div className="flex w-full max-w-[720px] flex-col gap-8">

      {/* ======================================
          TITLE + ONE GLOBAL SPEAKER
          ====================================== */}

      <div>
        <div className="flex items-start justify-between gap-3">
          <h1 className="flex-1 font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
            {title}
          </h1>

          <button
            type="button"
            onClick={speakWholePage}
            aria-label="Read this page aloud"
            title="Read this page aloud"
            className="shrink-0 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-lg transition hover:bg-white/10"
          >
            🔊
          </button>
        </div>

        <p className="mt-3 text-forge-3 text-forge-text-secondary">
          {description}
        </p>
      </div>

      {/* ======================================
          PRICE
          ====================================== */}

      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {priceQuestion}
        </h2>

        {isAdvanced ? (
          <LabeledField
            label="Price per customer / month (USD)"
            placeholder="e.g. 49"
            type="number"
            min={0}
            value={numberField(
              revenueAssumptions
                .price_per_customer_usd,
            )}
            onChange={(v) =>
              onRevenueAssumptionsChange({
                price_per_customer_usd:
                  v === ""
                    ? null
                    : Number(v),
              })
            }
          />
        ) : (
          <div
            role="radiogroup"
            aria-label={priceQuestion}
            className="grid grid-cols-2 gap-3 forge-sm:grid-cols-5"
          >
            {priceTiers.map(
              (tier) => (
                <ChoiceCard
                  key={tier.label}
                  label={tier.label}
                  selected={
                    revenueAssumptions
                      .price_per_customer_usd ===
                    tier.value
                  }
                  onSelect={() =>
                    onRevenueAssumptionsChange({
                      price_per_customer_usd:
                        tier.value,
                    })
                  }
                />
              ),
            )}
          </div>
        )}
      </div>

      {/* ======================================
          CUSTOMERS
          ====================================== */}

      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {customersQuestion}
        </h2>

        <LabeledField
          label={t(
            "additionalDetails.customers.label",
          )}
          placeholder={t(
            "additionalDetails.customers.placeholder",
          )}
          type="number"
          min={0}
          value={numberField(
            revenueAssumptions
              .initial_customers,
          )}
          onChange={(v) =>
            onRevenueAssumptionsChange({
              initial_customers:
                v === ""
                  ? null
                  : Number(v),
            })
          }
        />
      </div>

      {/* ======================================
          ADVANCED REVENUE VALUES
          ====================================== */}

      {isAdvanced && (
        <div className="grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
          <LabeledField
            label={
              expectedGrowthLabel
            }
            value={String(
              revenueAssumptions
                .monthly_growth_rate_pct ??
                0,
            )}
            readOnly
          />

          <LabeledField
            label={
              grossMarginLabel
            }
            value={String(
              revenueAssumptions
                .gross_margin_pct ??
                70,
            )}
            readOnly
          />

          <div className="grid grid-cols-1 gap-6 forge-sm:col-span-2 forge-sm:grid-cols-2">
            <Slider
              label={
                expectedGrowthLabel
              }
              value={
                revenueAssumptions
                  .monthly_growth_rate_pct ??
                0
              }
              min={0}
              max={50}
              step={1}
              formatValue={(v) =>
                `${v}%`
              }
              onChange={(v) =>
                onRevenueAssumptionsChange({
                  monthly_growth_rate_pct:
                    v,
                })
              }
            />

            <Slider
              label={
                grossMarginLabel
              }
              value={
                revenueAssumptions
                  .gross_margin_pct ??
                70
              }
              min={0}
              max={100}
              step={5}
              formatValue={(v) =>
                `${v}%`
              }
              onChange={(v) =>
                onRevenueAssumptionsChange({
                  gross_margin_pct:
                    v,
                })
              }
            />
          </div>
        </div>
      )}

      {/* ======================================
          GEOGRAPHY
          ====================================== */}

      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {geographyQuestion}
        </h2>

        <div
          role="radiogroup"
          aria-label={
            geographyQuestion
          }
          className="grid grid-cols-2 gap-3 forge-sm:grid-cols-4"
        >
          {geographyOptions.map(
            (geo) => (
              <ChoiceCard
                key={geo.value}
                label={geo.label}
                selected={
                  knownGeography ===
                  geo.value
                }
                onSelect={() => {
                  if (
                    geo.value ===
                    "Other"
                  ) {
                    setShowOtherGeography(
                      true,
                    );

                    onMarketEvidenceChange({
                      geography:
                        marketEvidence.geography &&
                        knownGeography ===
                          "Other"
                          ? marketEvidence.geography
                          : "",
                    });
                  } else {
                    setShowOtherGeography(
                      false,
                    );

                    onMarketEvidenceChange({
                      geography:
                        geo.value,
                    });
                  }
                }}
              />
            ),
          )}
        </div>

        {showOtherGeography && (
          <LabeledField
            label={
              geographyQuestion
            }
            placeholder={t(
              "additionalDetails.geography.placeholder",
            )}
            value={
              marketEvidence.geography ??
              ""
            }
            onChange={(v) =>
              onMarketEvidenceChange({
                geography:
                  v || null,
              })
            }
          />
        )}
      </div>

      {/* ======================================
          COMPETITORS
          ====================================== */}

      <div className="flex flex-col gap-3">
        <h2 className="font-forge-serif text-forge-4 font-semibold text-forge-text">
          {competitorsQuestion}
        </h2>

        <TagInput
          label={t(
            "additionalDetails.competitors.label",
          )}
          placeholder={t(
            "additionalDetails.competitors.placeholder",
          )}
          tags={
            marketEvidence
              .known_competitors ??
            []
          }
          onChange={(tags) =>
            onMarketEvidenceChange({
              known_competitors:
                tags,
            })
          }
        />
      </div>

      {/* ======================================
          ADVANCED COMPANY DETAILS
          ====================================== */}

      {isAdvanced && (
        <div className="flex flex-col gap-4 border-t border-forge-text/[.08] pt-6">
          <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-text-tertiary">
            {companyDetailsTitle}
          </p>

          <div className="grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
            <LabeledField
              label="How much funding have you raised? (USD)"
              placeholder="e.g. 50000"
              type="number"
              min={0}
              value={numberField(
                companyMetrics
                  .total_funding_usd,
              )}
              onChange={(v) =>
                onCompanyMetricsChange({
                  total_funding_usd:
                    v === ""
                      ? null
                      : Number(v),
                })
              }
            />

            <LabeledField
              label="How many funding rounds?"
              placeholder="e.g. 1"
              type="number"
              min={0}
              value={numberField(
                companyMetrics
                  .funding_rounds,
              )}
              onChange={(v) =>
                onCompanyMetricsChange({
                  funding_rounds:
                    v === ""
                      ? null
                      : Number(v),
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
                companyMetrics
                  .founded_year,
              )}
              onChange={(v) =>
                onCompanyMetricsChange({
                  founded_year:
                    v === ""
                      ? null
                      : Number(v),
                })
              }
            />

            <LabeledField
              label="Which country is your company in?"
              placeholder="e.g. usa"
              value={
                companyMetrics
                  .country_code ??
                ""
              }
              onChange={(v) =>
                onCompanyMetricsChange({
                  country_code:
                    v || null,
                })
              }
            />
          </div>
        </div>
      )}
    </div>
  );
}