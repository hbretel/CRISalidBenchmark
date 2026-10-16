"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { ImpactIndicators } from "@/types/api";
import { SubIndicatorCard } from "@/components/indicators/SubIndicatorCard";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { FilterChip } from "@/components/ui/FilterChip";
import { LEIDEN_DOMAINS } from "@/lib/constants";
import { t } from "@/lib/i18n";

interface Props {
  peerGroupId: number | null;
  coreOnly: boolean;
  field: string;
}

export function ImpactCitationsSection({ peerGroupId, coreOnly, field }: Props) {
  const { data, isLoading, error } = useSWR<ImpactIndicators>(
    peerGroupId
      ? `/indicators/impact-scientifique?peer_group_id=${peerGroupId}&field=${encodeURIComponent(field)}&core_only=${coreOnly}`
      : null,
    (url: string) => api.get<ImpactIndicators>(url),
  );

  const headline = data?.indicators.impact_normalise_leiden;
  const headlineLabel =
    headline?.leiden_column === "pp_10_cits" ? t("impact.headlinePp10Cits") : t("impact.headlinePpTop10");
  const hIndexLabel =
    data?.period_start && data?.period_end
      ? t("impact.hIndexWithPeriod", { start: data.period_start, end: data.period_end })
      : t("impact.hIndex");

  return (
    <section className="mb-10">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <h2 className="text-base font-semibold text-gray-800">{t("impact.title")}</h2>
      </div>
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        <FilterChip label={coreOnly ? t("filters.core") : t("filters.allPublications")} variant="active" />
        {data?.period_start && data?.period_end && (
          <FilterChip label={`${data.period_start}–${data.period_end}`} />
        )}
        <FilterChip
          label={t(`leidenDomain.${LEIDEN_DOMAINS.find((d) => d.value === field)?.value ?? field}`)}
          variant={field !== "All sciences" ? "active" : "neutral"}
        />
        <InfoTooltip text={t("filters.sectionFiltersNote")} />
      </div>

      <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
        <strong>{t("impact.methodologyNoteLabel")}</strong> {t("impact.methodologyNote", { year: data?.snapshot_year ?? "…" })}
        {headline?.leiden_column === "pp_10_cits" && t("impact.toggleNonEquivalenceNote")}
      </div>

      {isLoading && <div className="text-gray-500 text-sm">{t("common.computing")}</div>}
      {error && <div className="text-red-600 text-sm">{t("impact.computeError")}</div>}

      {data && (
        <>
          <div className="text-xs text-gray-400 mb-4">
            {t("impact.percentileNote", { count: data.peer_group_size })}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SubIndicatorCard label={headlineLabel} indicator={data.indicators.impact_normalise_leiden} unit="%" />
            <SubIndicatorCard label={t("impact.mncs")} indicator={data.indicators.mncs} />
            <SubIndicatorCard
              label={t("impact.citationsAvg")}
              indicator={data.indicators.citations_brutes_moyennes}
              formatValue={(v) => v.toFixed(1)}
            />
            <SubIndicatorCard label={hIndexLabel} indicator={data.indicators.h_index_core} />
            <SubIndicatorCard label={t("impact.oaPct")} indicator={data.indicators.oa_pct} unit="%" />
            <SubIndicatorCard label={t("impact.collabPct")} indicator={data.indicators.collab_intl_pct} unit="%" />
          </div>
        </>
      )}
    </section>
  );
}
