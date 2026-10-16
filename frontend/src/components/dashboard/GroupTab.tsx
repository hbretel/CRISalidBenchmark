"use client";

import { useGroupBenchmark } from "@/hooks/usePeerGroups";
import { FilterChip } from "@/components/ui/FilterChip";
import { ComparisonInstitutionsTable } from "@/components/benchmark/ComparisonInstitutionsTable";
import { GroupOverview } from "./GroupOverview";
import { SpecializationSection } from "./SpecializationSection";
import { TopicsSignatureSection } from "./TopicsSignatureSection";
import { QualitySection } from "./QualitySection";
import { t } from "@/lib/i18n";

interface Props {
  groupId: number;
  profileId: number;
  profileName?: string;
  domain: string;
}

/** "Groupes de comparaison": OpenAlex-only benchmark of the group, by OpenAlex domain. */
export function GroupTab({ groupId, profileId, profileName, domain }: Props) {
  const { data, isLoading, error } = useGroupBenchmark(groupId, profileId, domain);
  const own = data?.rows.find((r) => r.is_own);
  const cacheMissing = data && (!own?.has_data || data.institutions_with_data <= 1);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5 mb-4">
        <FilterChip label={t("filters.allPublications")} variant="active" />
        {data?.period_start && data.period_end && <FilterChip label={`${data.period_start}–${data.period_end}`} />}
        <FilterChip label={t(`openalexDomain.${domain}`)} variant={domain !== "all" ? "active" : "neutral"} />
        {data && <FilterChip label={t("groupTab.threshold", { min: data.min_publications })} />}
      </div>

      <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-900 leading-relaxed">
        <strong>{t("groupTab.methodLabel")}</strong> {t("groupTab.method")}
      </div>

      {isLoading && <div className="text-gray-500 text-sm">{t("common.computing")}</div>}
      {error && <div className="text-red-600 text-sm">{t("groupTab.loadError")}</div>}
      {cacheMissing && (
        <div className="mb-6 bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800">
          {t("groupTab.cacheMissingBefore", { n: data.institutions_with_data, total: data.group_size + 1 })}{" "}
          <em>{t("nav.settings")}</em>
          {t("groupTab.cacheMissingAfter")}
        </div>
      )}

      {data && (
        <>
          <GroupOverview benchmark={data} profileName={profileName} />
          <ComparisonInstitutionsTable benchmark={data} profileName={profileName} domain={domain} />
          <SpecializationSection benchmark={data} domain={domain} />
          <TopicsSignatureSection peerGroupId={groupId} weightProfileId={profileId} />
          <QualitySection benchmark={data} periodStart={data.period_start} periodEnd={data.period_end} />
        </>
      )}
    </div>
  );
}
