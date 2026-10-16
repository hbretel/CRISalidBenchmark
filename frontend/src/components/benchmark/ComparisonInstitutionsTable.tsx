"use client";

import { useMemo, useState } from "react";
import { Calculator } from "lucide-react";
import { DataTable, type Column } from "@/components/ui/DataTable";
import type { GroupBenchmark, GroupBenchmarkRow } from "@/types/api";
import { ScoreBreakdownModal } from "./ScoreBreakdownModal";
import { t } from "@/lib/i18n";

interface Props {
  benchmark: GroupBenchmark;
  profileName?: string;
  domain: string;
}

const dash = () => t("common.dash");
const percent = (v: number | null | undefined) =>
  v != null ? `${v.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %` : dash();

// Impact columns shown in the summary table (the others are in the cards and
// in each score breakdown — keeps the table within the page width).
const TABLE_IMPACT = ["pp_top_10", "pp_top_1", "pp_oa", "pp_int_collab"] as const;

function weightPct(benchmark: GroupBenchmark, axis: string): number {
  return Math.round((benchmark.axis_weights[axis] ?? 0) * 100);
}

export function ComparisonInstitutionsTable({ benchmark, profileName, domain }: Props) {
  const [selected, setSelected] = useState<GroupBenchmarkRow | null>(null);

  const columns = useMemo<Column<GroupBenchmarkRow>[]>(() => {
    const cols: Column<GroupBenchmarkRow>[] = [
      { key: "rank", label: t("comparisonTable.colRank"), numeric: true, sortValue: (r) => r.rank, render: (r) => r.rank ?? dash() },
      {
        key: "name",
        label: t("comparisonTable.colInstitution"),
        sortValue: (r) => r.name ?? r.ror_id,
        render: (r) => (
          <>
            {r.name ?? r.ror_id}
            {r.is_own && <span className="ml-1.5 text-xs text-brand-600">{t("comparisonTable.ownTag")}</span>}
            {r.country_code && <span className="ml-1.5 text-xs text-gray-400">{r.country_code}</span>}
            {!r.has_data && <span className="block text-xs text-gray-400">{t("comparisonTable.noData")}</span>}
            {r.has_data && !r.compared && (
              <span className="block text-xs text-gray-400">{t("comparisonTable.belowThreshold")}</span>
            )}
          </>
        ),
      },
      {
        key: "p",
        label: t("indicator.p"),
        numeric: true,
        sortValue: (r) => r.p,
        render: (r) => (r.p != null ? r.p.toLocaleString("fr-FR") : dash()),
      },
      {
        key: "p_top_10",
        label: t("indicator.p_top_10"),
        numeric: true,
        sortValue: (r) => r.volume.p_top_10 ?? null,
        render: (r) => r.volume.p_top_10?.toLocaleString("fr-FR") ?? dash(),
      },
      ...TABLE_IMPACT.map(
        (key): Column<GroupBenchmarkRow> => ({
          key,
          label: t(`indicator.${key}`),
          numeric: true,
          sortValue: (r) => r.impact[key] ?? null,
          render: (r) => percent(r.impact[key]),
        }),
      ),
    ];
    if (benchmark.specialization_applicable) {
      cols.push({
        key: "specialization_rate",
        label: t("comparisonTable.colSpecialization"),
        numeric: true,
        sortValue: (r) => r.specialization_rate,
        render: (r) => percent(r.specialization_rate),
      });
    }
    cols.push(
      {
        key: "quality_coefficient",
        label: t("comparisonTable.colQuality"),
        numeric: true,
        sortValue: (r) => r.quality?.estimates.global ?? null,
        render: (r) =>
          r.quality ? `×${r.quality.estimates.global.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}` : dash(),
      },
      {
        key: "quality_pp_top10",
        label: t("comparisonTable.colQualityTop10"),
        numeric: true,
        sortValue: (r) => r.quality?.top["10"]?.share ?? null,
        render: (r) => percent(r.quality?.top["10"]?.share),
      },
      {
        key: "composite_score",
        label: t("comparisonTable.colScore"),
        numeric: true,
        sortValue: (r) => r.composite_score,
        render: (r) =>
          r.composite_score === null ? (
            dash()
          ) : (
            <button
              type="button"
              onClick={() => setSelected(r)}
              className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline"
              aria-label={t("comparisonTable.scoreButtonLabel", { name: r.name ?? r.ror_id })}
            >
              <Calculator size={12} className="opacity-60" />
              {r.composite_score}
            </button>
          ),
      },
    );
    return cols;
  }, [benchmark]);

  const domainLabel = t(`openalexDomain.${domain}`);

  return (
    <section className="mb-10">
      <h2 className="text-base font-semibold text-gray-800 mb-2">{t("comparisonTable.title")}</h2>

      <div className="mb-3 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-900 space-y-1 leading-relaxed">
        <p className="font-semibold">{t("comparisonTable.explainTitle")}</p>
        <p>
          <strong>{t("comparisonTable.explainImpactLabel")}</strong>{" "}
          {t("comparisonTable.explainImpact", {
            start: benchmark.period_start ?? "…",
            end: benchmark.period_end ?? "…",
            domain: domainLabel,
          })}
        </p>
        <p>
          <strong>{t("comparisonTable.explainVolumeLabel")}</strong> {t("comparisonTable.explainVolume")}
        </p>
        <p>
          <strong>{t("comparisonTable.explainSpecializationLabel")}</strong>{" "}
          {benchmark.specialization_applicable
            ? t("comparisonTable.explainSpecialization", { domain: domainLabel })
            : t("comparisonTable.explainSpecializationNA")}
        </p>
        <p>
          <strong>{t("comparisonTable.explainQualityLabel")}</strong> {t("comparisonTable.explainQuality")}
        </p>
        <p>
          <strong>{t("comparisonTable.explainScoreLabel")}</strong>{" "}
          {t("comparisonTable.explainScore", {
            impact: weightPct(benchmark, "impact_scientifique"),
            volume: weightPct(benchmark, "volume_publications"),
            spec: weightPct(benchmark, "specificite_disciplinaire"),
            quality: weightPct(benchmark, "qualite"),
            profile: profileName ?? "",
            min: benchmark.min_publications,
          })}
        </p>
      </div>

      <DataTable
        columns={columns}
        rows={benchmark.rows}
        rowKey={(r) => r.ror_id}
        initialSort={{ key: "composite_score", dir: "desc" }}
        isHighlighted={(r) => r.is_own}
      />

      {selected && selected.composite_score !== null && (
        <ScoreBreakdownModal
          open
          onClose={() => setSelected(null)}
          institutionName={selected.name ?? selected.ror_id}
          compositeScore={selected.composite_score}
          breakdown={selected.breakdown}
          profileName={profileName}
        />
      )}
    </section>
  );
}
