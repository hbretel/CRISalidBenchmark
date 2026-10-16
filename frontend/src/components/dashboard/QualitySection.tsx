"use client";

import { useState } from "react";
import useSWR from "swr";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { FileCheck2, Gauge, ListChecks } from "lucide-react";
import { api } from "@/lib/api";
import type { GroupBenchmark, QualityHistogramBin, QualitySummary, QualityWorksPage } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { FilterChip } from "@/components/ui/FilterChip";
import { QualityCriteriaTable } from "./QualityCriteriaTable";
import { QualityWorkModal } from "./QualityWorkModal";
import { QualityBenchmarkCard } from "./QualityBenchmarkCard";
import { t } from "@/lib/i18n";

interface Props {
  /** Group benchmark (quality axis of every institution of the group), if a group is selected. */
  benchmark?: GroupBenchmark;
  periodStart: number | null;
  periodEnd: number | null;
}

// The "Groupes de comparaison" tab has no "core publications" filter: the
// whole synced corpus is evaluated.
const coreOnly = false;

function formatDate(iso: string | null | undefined): string {
  return iso ? new Intl.DateTimeFormat("fr-FR").format(new Date(iso)) : t("common.dash");
}

function StatCard({
  label,
  value,
  icon: Icon,
  tooltip,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  tooltip: string;
}) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-center justify-between text-gray-500 text-sm mb-2">
        <span className="flex items-center gap-2">
          <Icon size={15} />
          {label}
        </span>
        <InfoTooltip text={tooltip} />
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
    </div>
  );
}

function binLabel(bin: QualityHistogramBin): string {
  return bin.open_ended
    ? t("quality.histogramRangeOpen", { start: bin.start })
    : t("quality.histogramRange", { start: bin.start, end: bin.end });
}

export function QualitySection({ benchmark, periodStart, periodEnd }: Props) {
  const { data, error, isLoading } = useSWR<QualitySummary>(
    `/quality/summary?core_only=${coreOnly}`,
    (url: string) => api.get<QualitySummary>(url),
  );

  return (
    <section className="mt-10">
      <h2 className="text-base font-semibold text-gray-800 mb-1">{t("quality.title")}</h2>
      <p className="text-sm text-gray-500 mb-2">{t("quality.subtitle")}</p>
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        <FilterChip label={t("filters.allPublications")} variant="active" />
        {periodStart && periodEnd && <FilterChip label={`${periodStart}–${periodEnd}`} />}
        <FilterChip label={t("quality.allDomainsChip")} />
        <InfoTooltip text={t("quality.domainNote")} />
      </div>

      {isLoading && <div className="text-gray-500 text-sm">{t("common.loading")}</div>}
      {error && <div className="text-red-600 text-sm">{t("quality.loadError")}</div>}
      {data && !data.available && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-500">
          {data.running ? (
            t("quality.running")
          ) : (
            <>
              {t("quality.notAvailableBefore")}
              <em>{t("nav.configuration")}</em>
              {t("quality.notAvailableAfter")}
            </>
          )}
        </div>
      )}
      {data?.available && <QualityContent data={data} benchmark={benchmark} />}
    </section>
  );
}

function QualityContent({ data, benchmark }: { data: QualitySummary; benchmark?: GroupBenchmark }) {
  const coefficient = data.coefficient;
  const sources = data.sources;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label={t("quality.worksEvaluated")}
          value={t("quality.worksEvaluatedValue", {
            n: (data.n_works ?? 0).toLocaleString("fr-FR"),
            total: data.n_corpus.toLocaleString("fr-FR"),
          })}
          icon={FileCheck2}
          tooltip={t("quality.worksEvaluatedTooltip", { date: formatDate(data.computed_at) })}
        />
        <StatCard
          label={t("quality.medianCoefficient")}
          value={coefficient ? coefficient.median.toLocaleString("fr-FR") : t("common.dash")}
          icon={Gauge}
          tooltip={t("quality.medianCoefficientTooltip")}
        />
        <StatCard
          label={t("quality.criteriaCovered")}
          value={t("quality.criteriaCoveredValue", { n: data.n_criteria_reached ?? 0, total: data.n_criteria_grid ?? 0 })}
          icon={ListChecks}
          tooltip={t("quality.criteriaCoveredTooltip", { grid: data.grid_file ?? "" })}
        />
      </div>

      {benchmark && <QualityBenchmarkCard benchmark={benchmark} />}

      {coefficient && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            {t("quality.histogramTitle")}
            <InfoTooltip
              text={t("quality.histogramTooltip", {
                p10: coefficient.p10,
                median: coefficient.median,
                p90: coefficient.p90,
              })}
            />
          </h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={coefficient.histogram} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <XAxis
                  dataKey="start"
                  tick={{ fontSize: 10, fill: "#6b7280" }}
                  tickFormatter={(v: number) => v.toLocaleString("fr-FR")}
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 10, fill: "#6b7280" }} width={40} allowDecimals={false} />
                <Tooltip
                  formatter={(value: number) => [value.toLocaleString("fr-FR"), t("quality.histogramPublications")]}
                  labelFormatter={(_label, payload) =>
                    payload?.[0] ? binLabel(payload[0].payload as QualityHistogramBin) : ""
                  }
                  contentStyle={{ fontSize: 12 }}
                />
                <Bar dataKey="count" fill="#2563eb" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {data.categories && <QualityCriteriaTable categories={data.categories} />}

      <QualityWorksList />

      {sources && (
        <div className="text-xs text-gray-400 space-y-1">
          <p>
            {t("quality.sourcesFooter", {
              grid: data.grid_file ?? "",
              crossref: sources.crossref_records.toLocaleString("fr-FR"),
              hal: sources.hal_deposits.toLocaleString("fr-FR"),
              pubmed: sources.pubmed_records.toLocaleString("fr-FR"),
              doaj: formatDate(sources.doaj_dump_date),
              rw: formatDate(sources.retraction_watch_dump_date),
            })}
            {sources.llm_model &&
              t("quality.sourcesFooterLlm", { n: sources.llm_journals, model: sources.llm_model })}
          </p>
          {!!data.n_errors && <p>{t("quality.errorsNote", { n: data.n_errors })}</p>}
        </div>
      )}
    </div>
  );
}

function QualityWorksList() {
  const [order, setOrder] = useState<"desc" | "asc">("desc");
  const [selected, setSelected] = useState<string | null>(null);
  const { data } = useSWR<QualityWorksPage>(
    `/quality/works?core_only=${coreOnly}&order=${order}&limit=10`,
    (url: string) => api.get<QualityWorksPage>(url),
  );

  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">{t("quality.worksTitle")}</h3>
        <div className="flex text-xs border rounded-md overflow-hidden">
          {(["desc", "asc"] as const).map((o) => (
            <button
              key={o}
              onClick={() => setOrder(o)}
              className={`px-2.5 py-1 ${order === o ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-50"}`}
            >
              {o === "desc" ? t("quality.worksHighest") : t("quality.worksLowest")}
            </button>
          ))}
        </div>
      </div>
      {data && data.works.length === 0 && <p className="text-xs text-gray-400">{t("quality.worksEmpty")}</p>}
      <ul className="divide-y">
        {data?.works.map((w) => (
          <li key={w.id}>
            <button
              onClick={() => setSelected(w.id)}
              className="w-full flex items-center justify-between gap-3 py-2 text-left hover:bg-gray-50 px-1 rounded"
            >
              <span className="text-sm text-gray-800 truncate">
                {w.title ?? w.id}
                {w.publication_year && <span className="ml-1.5 text-xs text-gray-400">{w.publication_year}</span>}
              </span>
              <span className="text-sm font-semibold text-brand-700 tabular-nums shrink-0">
                ×{w.coefficient.toLocaleString("fr-FR")}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <QualityWorkModal workId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
