"use client";

import type { Indicator } from "@/types/api";
import { PercentileGauge } from "./PercentileGauge";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface Props {
  label: string;
  indicator: Indicator;
  unit?: string;
  formatValue?: (v: number) => string;
}

const SOURCE_LABELS: Record<string, string> = {
  leiden:           "Leiden Ranking",
  openalex:         "OpenAlex (nocturne)",
  "openalex+leiden": "OpenAlex + Leiden",
};

export function SubIndicatorCard({ label, indicator, unit = "", formatValue }: Props) {
  const display =
    indicator.value !== null
      ? formatValue
        ? formatValue(indicator.value)
        : `${indicator.value}${unit}`
      : "—";

  return (
    <div className="bg-white border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <InfoTooltip text={indicator.description} />
      </div>

      <div className="text-2xl font-bold text-gray-900">{display}</div>

      <PercentileGauge percentile={indicator.percentile} label="Au sein du groupe de comparaison" />

      <div className="text-xs text-gray-400">
        Source : {SOURCE_LABELS[indicator.source] ?? indicator.source}
      </div>
    </div>
  );
}
