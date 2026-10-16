"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { SpecificityIndicators } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { FilterChip } from "@/components/ui/FilterChip";
import { ThematicTreemap } from "./ThematicTreemap";
import { TopicsSignatureTable } from "./TopicsSignatureTable";
import { t } from "@/lib/i18n";

// data.herfindahl.label/description/explanation and topics_signature.description
// are server-generated French sentences (backend/app/services/indicators_specificity.py) —
// dynamic content, not a static UI wording, so out of scope for the frontend
// dictionary (see lib/i18n/fr.ts). This map just needs to match the backend's
// literal label strings.
const HERFINDAHL_COLORS: Record<string, string> = {
  "généraliste": "bg-blue-100 text-blue-800 border-blue-200",
  "modérément spécialisé": "bg-amber-100 text-amber-800 border-amber-200",
  "très spécialisé": "bg-green-100 text-green-800 border-green-200",
};

interface Props {
  peerGroupId: number | null;
}

export function SpecialtyDomainsSection({ peerGroupId }: Props) {
  const { data, isLoading, error } = useSWR<SpecificityIndicators>(
    peerGroupId ? `/indicators/specificite-disciplinaire?peer_group_id=${peerGroupId}` : null,
    (url: string) => api.get<SpecificityIndicators>(url),
  );

  return (
    <section>
      <h2 className="text-base font-semibold text-gray-800 mb-1">{t("specialty.title")}</h2>
      <p className="text-sm text-gray-500 mb-2">{t("specialty.subtitle")}</p>
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        <FilterChip label={t("filters.fullCorpus")} />
        <FilterChip label={t("filters.allDomainsOpenAlex")} />
        <InfoTooltip text={t("filters.specialtyIndependentNote")} />
      </div>

      <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
        <strong>{t("specialty.fullCorpusNoteLabel")}</strong> {t("specialty.fullCorpusNote")}
      </div>

      {isLoading && <div className="text-gray-500 text-sm">{t("common.computing")}</div>}
      {error && <div className="text-red-600 text-sm">{t("specialty.computeError")}</div>}

      {data && (
        <div className="space-y-6">
          <div className="bg-white border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              {t("specialty.herfindahlTitle")}
              <InfoTooltip text={data.herfindahl.description} />
            </h3>
            <div className="flex items-center gap-4 mb-2">
              <span className="text-3xl font-bold text-gray-900">{data.herfindahl.value.toFixed(3)}</span>
              <span
                className={`text-sm font-medium px-2.5 py-1 rounded border ${
                  HERFINDAHL_COLORS[data.herfindahl.label] ?? "bg-gray-100 text-gray-700 border-gray-200"
                }`}
              >
                {data.herfindahl.label}
              </span>
            </div>
            <p className="text-sm text-gray-700">{data.herfindahl.explanation}</p>
            <div className="mt-3 text-xs text-gray-500">{t("specialty.herfindahlFooter")}</div>
          </div>

          <div className="bg-white border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              {t("specialty.treemapTitle")}
              <InfoTooltip text={t("specialty.treemapTooltip")} />
            </h3>
            <ThematicTreemap data={data.thematic_profile} totalWorks={data.total_works_analysed} />
          </div>

          <div className="bg-white border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-1 flex items-center gap-2">
              {t("specialty.signatureTitle")}
              <InfoTooltip text={data.topics_signature.description} />
            </h3>
            {!data.topics_signature.peer_cache_populated && (
              <div className="mb-3 bg-amber-50 border border-amber-200 rounded p-2 text-xs text-amber-700">
                {t("specialty.signatureCacheNotPopulatedBefore")} <em>{t("nav.settings")}</em>
                {t("specialty.signatureCacheNotPopulatedAfter")}
              </div>
            )}
            {data.topics_signature.items.length === 0 ? (
              <p className="text-sm text-gray-500">
                {t("specialty.signatureNoneAboveThreshold", { threshold: data.topics_signature.threshold })}
              </p>
            ) : (
              <TopicsSignatureTable items={data.topics_signature.items} />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
