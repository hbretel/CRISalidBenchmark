"use client";

import type { Indicator } from "@/types/api";
import { PercentileGauge } from "./PercentileGauge";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { t } from "@/lib/i18n";

interface Props {
  label: string;
  indicator: Indicator;
  unit?: string;
  formatValue?: (v: number) => string;
}

const SOURCE_LABEL_KEYS: Record<string, string> = {
  leiden: "subIndicatorCard.sourceLeiden",
  openalex: "subIndicatorCard.sourceOpenalex",
  "openalex+leiden": "subIndicatorCard.sourceBoth",
};

export function SubIndicatorCard({ label, indicator, unit = "", formatValue }: Props) {
  const display =
    indicator.value !== null
      ? formatValue
        ? formatValue(indicator.value)
        : `${indicator.value}${unit}`
      : t("common.dash");

  return (
    <div className="bg-white border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <InfoTooltip text={indicator.description} />
      </div>

      <div className="text-2xl font-bold text-gray-900">{display}</div>

      <PercentileGauge percentile={indicator.percentile} label={t("subIndicatorCard.percentileLabel")} />

      <div className="text-xs text-gray-400">
        {t("subIndicatorCard.sourceLabel", {
          source: SOURCE_LABEL_KEYS[indicator.source] ? t(SOURCE_LABEL_KEYS[indicator.source]) : indicator.source,
        })}
      </div>
    </div>
  );
}
