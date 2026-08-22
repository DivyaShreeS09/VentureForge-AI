import { ChoiceCard } from "../../primitives";
import { useLanguage } from "../../context/LanguageContext";

interface Props {
  stage: string;
  onSelect: (stage: string) => void;
}

const STAGES = [
  {
    value: "Just an idea",
    key: "whereYouAre.stage.idea",
  },
  {
    value: "Validating",
    key: "whereYouAre.stage.validating",
  },
  {
    value: "Building",
    key: "whereYouAre.stage.building",
  },
  {
    value: "Early customers",
    key: "whereYouAre.stage.earlyCustomers",
  },
  {
    value: "Growing",
    key: "whereYouAre.stage.growing",
  },
] as const;

export function WhereYouAreScene({
  stage,
  onSelect,
}: Props) {
  const { t } = useLanguage();

  const question = t("whereYouAre.question");

  const translatedStages = STAGES.map((item) => ({
    ...item,
    label: t(item.key),
  }));

  return (
    <div className="flex w-full max-w-[680px] flex-col gap-6">
      <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
        {question}
      </h1>

      <div
        role="radiogroup"
        aria-label={question}
        className="grid grid-cols-1 gap-3 forge-sm:grid-cols-5"
      >
        {translatedStages.map((item) => (
          <ChoiceCard
            key={item.value}
            label={item.label}
            selected={stage === item.value}
            onSelect={() => onSelect(item.value)}
          />
        ))}
      </div>
    </div>
  );
}