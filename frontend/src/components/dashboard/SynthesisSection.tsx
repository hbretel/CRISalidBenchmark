"use client";

import useSWR from "swr";
import { FileText, TrendingUp, Award } from "lucide-react";
import { api } from "@/lib/api";
import type { ImpactIndicators, InstitutionSummary, SynthesisCounts } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { FilterChip } from "@/components/ui/FilterChip";
import { ComparisonInstitutionsTable } from "@/components/benchmark/ComparisonInstitutionsTable";
import { LEIDEN_DOMAINS } from "@/lib/constants";
import { t } from "@/lib/i18n";

interface Props {
  summary: InstitutionSummary;
  coreOnly: boolean;
  peerGroupId: number | null;
  weightProfileId: number | null;
  field: string;
}

function StatCard({
  label,
  value,
  icon: Icon,
  tooltip,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  tooltip?: string;
}) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <div className="flex items-center justify-between text-gray-500 text-sm mb-2">
        <span className="flex items-center gap-2">
          <Icon size={15} />
          {label}
        </span>
        {tooltip && <InfoTooltip text={tooltip} />}
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
    </div>
  );
}

function formatCount(v: number | null | undefined): string {
  return v != null ? Math.round(v).toLocaleString("fr-FR") : t("common.dash");
}

export function SynthesisSection({ summary, coreOnly, peerGroupId, weightProfileId, field }: Props) {
  const { data: counts } = useSWR<SynthesisCounts>(
    `/institution/synthesis?field=${encodeURIComponent(field)}&core_only=${coreOnly}`,
    (url: string) => api.get<SynthesisCounts>(url),
  );
  const { data: impact } = useSWR<ImpactIndicators>(
    peerGroupId
      ? `/indicators/impact-scientifique?peer_group_id=${peerGroupId}&field=${encodeURIComponent(field)}&core_only=${coreOnly}`
      : null,
    (url: string) => api.get<ImpactIndicators>(url),
  );

  const fromLeiden = counts?.source === "leiden";
  const sourceNote = fromLeiden ? " " + t("synthesis.leidenDomainSourceNote") : "";
  const headline = impact?.indicators.impact_normalise_leiden;
  const headlineLabel =
    headline?.leiden_column === "pp_10_cits" ? t("synthesis.headlinePp10Cits") : t("synthesis.headlinePpTop10");

  return (
    <section className="mb-10">
      <h2 className="text-base font-semibold text-gray-800 mb-2">{t("synthesis.title")}</h2>
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        <FilterChip label={coreOnly ? t("filters.core") : t("filters.allPublications")} variant="active" />
        {summary.period_start && summary.period_end && (
          <FilterChip label={`${summary.period_start}–${summary.period_end}`} />
        )}
        <FilterChip
          label={t(`leidenDomain.${LEIDEN_DOMAINS.find((d) => d.value === field)?.value ?? field}`)}
          variant={field !== "All sciences" ? "active" : "neutral"}
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label={t("synthesis.publications")}
          value={formatCount(counts?.publications)}
          icon={FileText}
          tooltip={
            (coreOnly
              ? t(fromLeiden ? "synthesis.publicationsTooltipCoreLeiden" : "synthesis.publicationsTooltipCore")
              : t(fromLeiden ? "synthesis.publicationsTooltipAllLeiden" : "synthesis.publicationsTooltipAll")) + sourceNote
          }
        />
        <StatCard
          label={t("synthesis.citations")}
          value={formatCount(counts?.citations)}
          icon={TrendingUp}
          tooltip={(coreOnly ? t("synthesis.citationsTooltipCore") : t("synthesis.citationsTooltipAll")) + sourceNote}
        />
        <StatCard
          label={headlineLabel}
          value={headline?.value != null ? `${headline.value}%` : t("common.dash")}
          icon={Award}
          tooltip={t("synthesis.headlineTooltip")}
        />
      </div>
      <ComparisonInstitutionsTable
        groupId={peerGroupId}
        weightProfileId={weightProfileId}
        coreOnly={coreOnly}
        field={field}
      />
    </section>
  );
}
