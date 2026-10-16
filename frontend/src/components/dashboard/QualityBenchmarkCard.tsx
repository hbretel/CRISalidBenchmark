"use client";

import { useMemo } from "react";
import type { GroupBenchmark, GroupBenchmarkRow } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { PercentileGauge } from "@/components/indicators/PercentileGauge";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { t } from "@/lib/i18n";

const SUB_INDICATORS = ["qualite_ex_ante", "qualite_intrinseque", "qualite_ex_post"] as const;
const LEVELS = ["50", "25", "10"] as const;

const coef = (v: number) => `×${v.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}`;
const count = (v: number) => Math.round(v).toLocaleString("fr-FR");
const share = (v: number) => `${v.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;

/** Quality axis of the group benchmark: Leiden-like P / PP top x % in quality, estimated coefficients. */
export function QualityBenchmarkCard({ benchmark }: { benchmark: GroupBenchmark }) {
  const rows = useMemo(() => benchmark.rows.filter((r) => r.quality), [benchmark]);
  const own = benchmark.rows.find((r) => r.is_own);
  const quality = own?.quality;
  const weights = benchmark.category_weights;
  const active = new Set(benchmark.quality_active_categories);

  const columns = useMemo<Column<GroupBenchmarkRow>[]>(
    () => [
      {
        key: "name",
        label: t("comparisonTable.colInstitution"),
        sortValue: (r) => r.name ?? r.ror_id,
        render: (r) => (
          <>
            {r.name ?? r.ror_id}
            {r.is_own && <span className="ml-1.5 text-xs text-brand-600">{t("comparisonTable.ownTag")}</span>}
          </>
        ),
      },
      { key: "p", label: t("qualityBenchmark.colP"), numeric: true, sortValue: (r) => r.p, render: (r) => count(r.p ?? 0) },
      ...LEVELS.flatMap((level): Column<GroupBenchmarkRow>[] => [
        {
          key: `p_top_${level}`,
          label: t("qualityBenchmark.colPTop", { level }),
          numeric: true,
          sortValue: (r) => r.quality?.top[level]?.count ?? null,
          render: (r) => (r.quality?.top[level] ? count(r.quality.top[level].count) : t("common.dash")),
        },
        {
          key: `pp_top_${level}`,
          label: t("qualityBenchmark.colPPTop", { level }),
          numeric: true,
          sortValue: (r) => r.quality?.top[level]?.share ?? null,
          render: (r) => (r.quality?.top[level] ? share(r.quality.top[level].share) : t("common.dash")),
        },
      ]),
      {
        key: "coefficient",
        label: t("qualityBenchmark.colCoefficient"),
        numeric: true,
        sortValue: (r) => r.quality?.estimates.global ?? null,
        render: (r) => (r.quality ? coef(r.quality.estimates.global) : t("common.dash")),
      },
      {
        key: "axis_score",
        label: t("qualityBenchmark.colAxisScore"),
        numeric: true,
        sortValue: (r) => r.quality?.axis_score ?? null,
        render: (r) => r.quality?.axis_score ?? t("common.dash"),
      },
    ],
    [],
  );

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
        {t("qualityBenchmark.title")}
        <InfoTooltip text={t("qualityBenchmark.tooltip")} />
      </h3>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 leading-relaxed">
        <strong>{t("qualityBenchmark.methodLabel")}</strong>{" "}
        {t("qualityBenchmark.method", {
          start: benchmark.period_start ?? "…",
          end: benchmark.period_end ?? "…",
          min: benchmark.min_publications,
        })}{" "}
        {t("qualityBenchmark.weightsNote", {
          exAnte: Math.round(weights.qualite_ex_ante * 100),
          intrinsic: Math.round(weights.qualite_intrinseque * 100),
          exPost: Math.round(weights.qualite_ex_post * 100),
        })}
        {SUB_INDICATORS.some((k) => !active.has(k)) &&
          ` ${t("qualityBenchmark.inactiveNote", {
            categories: SUB_INDICATORS.filter((k) => !active.has(k)).map((k) => t(`indicator.${k}`)).join(", "),
          })}`}
      </div>

      {!quality || own?.p == null ? (
        <p className="text-sm text-gray-500">{t("qualityBenchmark.unavailable", { min: benchmark.min_publications })}</p>
      ) : (
        <>
          <div>
            <p className="text-xs font-semibold text-gray-600 mb-2">{t("qualityBenchmark.leidenTitle")}</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500">{t("qualityBenchmark.colP")}</p>
                <p className="text-2xl font-bold text-gray-900">{count(own.p)}</p>
              </div>
              {LEVELS.map((level) => (
                <div key={level}>
                  <p className="text-xs text-gray-500">{t("qualityBenchmark.topLabel", { level })}</p>
                  <p className="text-2xl font-bold text-gray-900">{share(quality.top[level].share)}</p>
                  <p className="text-xs text-gray-500">
                    {t("qualityBenchmark.topCount", { n: count(quality.top[level].count), level })}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-gray-600 mb-2">{t("qualityBenchmark.axisTitle")}</p>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500">{t("qualityBenchmark.global")}</p>
                <p className="text-2xl font-bold text-gray-900">{coef(quality.estimates.global)}</p>
                {quality.axis_score != null && (
                  <p className="text-xs text-gray-500">{t("qualityBenchmark.axisScore", { score: quality.axis_score })}</p>
                )}
              </div>
              {SUB_INDICATORS.map((key) => (
                <div key={key}>
                  <p className="text-xs text-gray-500 mb-1">
                    {t(`indicator.${key}`)} · {Math.round(weights[key] * 100)} %
                  </p>
                  <p className="text-sm font-semibold text-gray-800 mb-1">{coef(quality.estimates[key])}</p>
                  {active.has(key) ? (
                    <PercentileGauge percentile={quality.percentiles[key] ?? null} size="sm" />
                  ) : (
                    <p className="text-xs text-gray-400">{t("qualityBenchmark.inactive")}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {rows.length > 1 && (
            <div>
              <p className="text-xs font-semibold text-gray-600 mb-2">{t("qualityBenchmark.tableTitle")}</p>
              <DataTable
                columns={columns}
                rows={rows}
                rowKey={(r) => r.ror_id}
                initialSort={{ key: "pp_top_10", dir: "desc" }}
                isHighlighted={(r) => r.is_own}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
