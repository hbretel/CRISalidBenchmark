"use client";

import { useState } from "react";
import { Calculator } from "lucide-react";
import type { GroupBenchmark } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { PercentileGauge } from "@/components/indicators/PercentileGauge";
import { ScoreBreakdownModal } from "@/components/benchmark/ScoreBreakdownModal";
import { GROUP_IMPACT_INDICATORS } from "@/lib/constants";
import { t } from "@/lib/i18n";

interface Props {
  benchmark: GroupBenchmark;
  profileName?: string;
}

const pct = (v: number | null | undefined) =>
  v == null ? t("common.dash") : `${v.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;

/** Reference institution on the group benchmark: P, global score and the impact indicators. */
export function GroupOverview({ benchmark, profileName }: Props) {
  const [showBreakdown, setShowBreakdown] = useState(false);
  const own = benchmark.rows.find((r) => r.is_own);
  if (!own) return null;

  return (
    <section className="mb-10">
      <h2 className="text-base font-semibold text-gray-800 mb-3">{t("groupOverview.title")}</h2>
      {!own.compared && (
        <p className="mb-3 text-xs text-amber-700">
          {t("groupOverview.belowThreshold", { min: benchmark.min_publications })}
        </p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div className="bg-white border rounded-lg p-4">
          <p className="text-sm font-medium text-gray-700">{t("indicator.p")}</p>
          <p className="text-2xl font-bold text-gray-900">{own.p?.toLocaleString("fr-FR") ?? t("common.dash")}</p>
          <p className="text-xs text-gray-500 mt-1">
            {t("groupOverview.period", { start: benchmark.period_start ?? "…", end: benchmark.period_end ?? "…" })}
          </p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <p className="text-sm font-medium text-gray-700">{t("groupOverview.score")}</p>
          {own.composite_score === null ? (
            <p className="text-2xl font-bold text-gray-400">{t("common.dash")}</p>
          ) : (
            <button
              type="button"
              onClick={() => setShowBreakdown(true)}
              className="inline-flex items-center gap-1.5 text-2xl font-bold text-brand-700 hover:underline"
            >
              <Calculator size={16} className="opacity-60" />
              {own.composite_score}
            </button>
          )}
          {own.rank !== null && (
            <p className="text-xs text-gray-500 mt-1">
              {t("groupOverview.rank", { rank: own.rank, n: benchmark.institutions_compared })}
            </p>
          )}
        </div>
      </div>

      <h3 className="text-sm font-semibold text-gray-700 mb-2">{t("axis.impact_scientifique")}</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {GROUP_IMPACT_INDICATORS.map((key) => (
          <div key={key} className="bg-white border rounded-lg p-4 flex flex-col gap-2">
            <span className="text-sm font-medium text-gray-700 flex items-center justify-between gap-2">
              {t(`indicator.${key}`)}
              <InfoTooltip text={t(`indicatorDescription.${key}`)} />
            </span>
            <span className="text-2xl font-bold text-gray-900">{pct(own.impact[key])}</span>
            <PercentileGauge percentile={own.impact_percentiles[key] ?? null} size="sm" />
          </div>
        ))}
      </div>

      {showBreakdown && own.composite_score !== null && (
        <ScoreBreakdownModal
          open
          onClose={() => setShowBreakdown(false)}
          institutionName={own.name ?? own.ror_id}
          compositeScore={own.composite_score}
          breakdown={own.breakdown}
          profileName={profileName}
        />
      )}
    </section>
  );
}
