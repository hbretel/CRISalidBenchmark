"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { WorldRanking, WorldRow } from "@/types/api";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { FilterChip } from "@/components/ui/FilterChip";
import { PercentileGauge } from "@/components/indicators/PercentileGauge";
import { t } from "@/lib/i18n";

interface Props {
  field: string;
  coreOnly: boolean;
}

// Proportions are already in % (backend services/world_ranking.py); MNCS/MCS are ratios.
const RATIO_INDICATORS = new Set(["mncs", "mcs"]);

function formatIndicator(key: string, value: number | string | boolean | null | undefined): string {
  if (typeof value !== "number") return t("common.dash");
  if (key === "p") return Math.round(value).toLocaleString("fr-FR");
  if (RATIO_INDICATORS.has(key)) return value.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;
}

/** "Monde entier": the Leiden Ranking as published, the reference institution's ranks — no global score. */
export function WorldTab({ field, coreOnly }: Props) {
  const { data, isLoading, error } = useSWR<WorldRanking>(
    `/indicators/world-ranking?field=${encodeURIComponent(field)}&core_only=${coreOnly}`,
    (url: string) => api.get<WorldRanking>(url),
  );
  const [country, setCountry] = useState("all");

  const countries = useMemo(
    () => [...new Set((data?.rows ?? []).map((r) => r.country_code).filter((c): c is string => !!c))].sort(),
    [data],
  );
  const ownCountry = data?.rows.find((r) => r.is_own)?.country_code ?? null;

  const columns = useMemo<Column<WorldRow>[]>(() => {
    if (!data) return [];
    const indicatorColumns = ["p", ...data.indicators].map(
      (key): Column<WorldRow> => ({
        key,
        label: t(`worldIndicator.${key}`),
        tooltip: t(`worldIndicatorDescription.${key}`),
        numeric: true,
        sortValue: (r) => (typeof r[key] === "number" ? (r[key] as number) : null),
        render: (r) => formatIndicator(key, r[key]),
      }),
    );
    return [
      {
        key: "name",
        label: t("world.colUniversity"),
        sortValue: (r) => r.name ?? r.ror_id,
        render: (r) => (
          <>
            {r.name ?? r.ror_id}
            {r.is_own && <span className="ml-1.5 text-xs text-brand-600">{t("comparisonTable.ownTag")}</span>}
            {!r.compared && <span className="ml-1.5 text-xs text-gray-400">{t("world.belowThreshold")}</span>}
          </>
        ),
      },
      { key: "country_code", label: t("world.colCountry"), sortValue: (r) => r.country_code, render: (r) => r.country_code ?? t("common.dash") },
      ...indicatorColumns,
    ];
  }, [data]);

  const rows = useMemo(
    () => (data?.rows ?? []).filter((r) => country === "all" || r.country_code === country),
    [data, country],
  );

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        <FilterChip label={coreOnly ? t("filters.core") : t("filters.allPublications")} variant="active" />
        {data?.period && <FilterChip label={data.period} />}
        <FilterChip label={t(`leidenDomain.${field}`)} variant={field !== "All sciences" ? "active" : "neutral"} />
        {data?.snapshot_year && <FilterChip label={t("world.edition", { year: data.snapshot_year })} />}
      </div>

      <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-900 leading-relaxed space-y-1">
        <p>
          <strong>{t("world.methodLabel")}</strong> {t("world.method", { min: data?.min_publications ?? "…" })}
        </p>
        <p>{coreOnly ? t("world.coreNote") : t("world.allPublicationsNote")}</p>
      </div>

      {isLoading && <div className="text-gray-500 text-sm">{t("common.loading")}</div>}
      {error && <div className="text-red-600 text-sm">{t("world.loadError")}</div>}
      {data && data.rows.length === 0 && <p className="text-sm text-gray-500">{t("world.noData")}</p>}

      {data && data.rows.length > 0 && (
        <>
          <section className="mb-8">
            <h2 className="text-base font-semibold text-gray-800 mb-3">{t("world.ownTitle")}</h2>
            {!data.own ? (
              <p className="text-sm text-gray-500">{t("world.ownNotRanked")}</p>
            ) : (
              <>
                {!data.own.compared && (
                  <p className="mb-3 text-xs text-amber-700">{t("world.ownBelowThreshold", { min: data.min_publications })}</p>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {["p", ...data.indicators].map((key) => {
                    const ind = data.own!.indicators[key];
                    return (
                      <div key={key} className="bg-white border rounded-lg p-4 flex flex-col gap-2">
                        <span className="text-sm font-medium text-gray-700">{t(`worldIndicator.${key}`)}</span>
                        <span className="text-2xl font-bold text-gray-900">{formatIndicator(key, ind?.value)}</span>
                        {ind?.rank != null && (
                          <span className="text-xs text-gray-500">
                            {t("world.rank", { rank: ind.rank.toLocaleString("fr-FR"), n: ind.n.toLocaleString("fr-FR") })}
                          </span>
                        )}
                        <PercentileGauge percentile={ind?.percentile ?? null} size="sm" />
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </section>

          <section>
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <h2 className="text-base font-semibold text-gray-800">{t("world.tableTitle")}</h2>
              <label className="text-xs text-gray-500 flex items-center gap-1.5">
                {t("world.countryFilter")}
                <select
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="all">{t("world.allCountries")}</option>
                  {ownCountry && <option value={ownCountry}>{t("world.myCountry", { country: ownCountry })}</option>}
                  {countries.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </label>
            </div>
            <DataTable
              columns={columns}
              rows={rows}
              rowKey={(r) => r.ror_id}
              initialSort={{ key: "p", dir: "desc" }}
              isHighlighted={(r) => r.is_own}
            />
          </section>
        </>
      )}
    </div>
  );
}
