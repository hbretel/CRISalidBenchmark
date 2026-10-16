"use client";

import { t } from "@/lib/i18n";

interface Props {
  percentile: number | null;
  label?: string;
  size?: "sm" | "md";
}

/**
 * Horizontal bar showing peer-group percentile position.
 * "80e percentile" = better than 80% of peer institutions.
 * Shown as a filled bar with the institution marker at the percentile position.
 */
export function PercentileGauge({ percentile, label, size = "md" }: Props) {
  if (percentile === null) {
    return (
      <span className="text-xs text-gray-400 italic">
        {t("percentileGauge.notComputable")}
      </span>
    );
  }

  const barH = size === "sm" ? "h-2" : "h-3";
  const color =
    percentile >= 75
      ? "bg-green-500"
      : percentile >= 50
        ? "bg-brand-500"
        : percentile >= 25
          ? "bg-amber-500"
          : "bg-red-400";

  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>{label}</span>
          <span className="font-semibold text-gray-700">{t("percentileGauge.nth", { percentile })}</span>
        </div>
      )}
      <div className={`relative w-full ${barH} bg-gray-200 rounded-full overflow-hidden`}>
        <div
          className={`${barH} ${color} rounded-full transition-all duration-500`}
          style={{ width: `${percentile}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-400 mt-0.5">
        <span>0</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  );
}
