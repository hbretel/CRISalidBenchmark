"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { QualityBenchmark } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { PercentileGauge } from "@/components/indicators/PercentileGauge";
import { t } from "@/lib/i18n";

const SUB_INDICATORS = ["qualite_ex_ante", "qualite_intrinseque", "qualite_ex_post"] as const;

/** Reference institution on the benchmark's peer-comparable quality axis. */
export function QualityBenchmarkCard({ peerGroupId }: { peerGroupId: number }) {
  const { data } = useSWR<QualityBenchmark>(`/quality/benchmark?peer_group_id=${peerGroupId}`, (url: string) =>
    api.get<QualityBenchmark>(url),
  );
  if (!data) return null;

  return (
    <div className="bg-white border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        {t("qualityBenchmark.title")}
        <InfoTooltip text={t("qualityBenchmark.tooltip", { n: data.n_criteria })} />
      </h3>
      {!data.available || !data.estimates || !data.percentiles ? (
        <p className="text-sm text-gray-500">{t("qualityBenchmark.unavailable")}</p>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-gray-500">{t("qualityBenchmark.global")}</p>
              <p className="text-2xl font-bold text-gray-900">×{data.estimates.global.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}</p>
              {data.global_percentile != null && (
                <p className="text-xs text-gray-500">{t("qualityBenchmark.percentile", { p: data.global_percentile })}</p>
              )}
            </div>
            {SUB_INDICATORS.map((key) => (
              <div key={key}>
                <p className="text-xs text-gray-500 mb-1">{t(`indicator.${key}`)}</p>
                <p className="text-sm font-semibold text-gray-800 mb-1">
                  ×{data.estimates![key].toLocaleString("fr-FR", { maximumFractionDigits: 2 })}
                </p>
                <PercentileGauge percentile={data.percentiles![key]} size="sm" />
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-3">
            {t("qualityBenchmark.coverage", { n: data.institutions_with_data, total: data.group_size + 1 })}
          </p>
        </>
      )}
    </div>
  );
}
