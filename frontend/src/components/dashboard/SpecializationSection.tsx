"use client";

import type { GroupBenchmark } from "@/types/api";
import { PercentileGauge } from "@/components/indicators/PercentileGauge";
import { t } from "@/lib/i18n";

interface Props {
  benchmark: GroupBenchmark;
  domain: string;
}

const fmt = (v: number) => v.toLocaleString("fr-FR", { maximumFractionDigits: 1 });

/** "Taux de spécialisation" (specificity axis, OpenAlex domains). */
export function SpecializationSection({ benchmark, domain }: Props) {
  const own = benchmark.rows.find((r) => r.is_own);
  const compared = benchmark.rows
    .filter((r) => r.compared && r.specialization_rate !== null)
    .map((r) => r.specialization_rate as number)
    .sort((a, b) => a - b);
  const median = compared.length
    ? compared.length % 2
      ? compared[(compared.length - 1) / 2]
      : (compared[compared.length / 2 - 1] + compared[compared.length / 2]) / 2
    : null;

  return (
    <section className="mb-10">
      <h2 className="text-base font-semibold text-gray-800 mb-1">{t("specialization.title")}</h2>
      <p className="text-sm text-gray-500 mb-2">{t("specialization.subtitle")}</p>

      <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 leading-relaxed">
        <strong>{t("specialization.methodLabel")}</strong> {t("specialization.method")}
      </div>

      <div className="space-y-6">
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            {t("specialization.cardTitle", { domain: t(`openalexDomain.${domain}`) })}
          </h3>
          {!benchmark.specialization_applicable ? (
            <p className="text-sm text-gray-600">{t("specialization.notApplicable")}</p>
          ) : !own || own.specialization_rate === null ? (
            <p className="text-sm text-gray-500">{t("specialization.noData")}</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
              <div>
                <div className="text-3xl font-bold text-gray-900">{fmt(own.specialization_rate)} %</div>
                {own.p !== null && (
                  <p className="text-xs text-gray-500 mt-1">
                    {t("specialization.counts", { field: own.p.toLocaleString("fr-FR") })}
                  </p>
                )}
                {median !== null && (
                  <p className="text-xs text-gray-500 mt-1">
                    {t("specialization.groupStats", {
                      median: fmt(median),
                      max: fmt(compared[compared.length - 1]),
                      n: compared.length,
                    })}
                  </p>
                )}
              </div>
              <PercentileGauge percentile={own.specialization_percentile} label={t("percentileGauge.groupLabel")} />
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
