"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { InstitutionSummary } from "@/types/api";
import { Clock } from "lucide-react";
import { t } from "@/lib/i18n";
import { usePeerGroups, getDefaultPeerGroupId } from "@/hooks/usePeerGroups";
import { useWeightProfiles, getDefaultWeightProfileId } from "@/hooks/useWeightProfiles";
import { useCurrentPeerGroupId, useCurrentWeightProfileId, useCoreOnly, useCurrentLeidenDomain } from "@/hooks/useCurrentSelection";
import { StickyHeader } from "@/components/dashboard/StickyHeader";
import { SynthesisSection } from "@/components/dashboard/SynthesisSection";
import { ImpactCitationsSection } from "@/components/dashboard/ImpactCitationsSection";
import { SpecialtyDomainsSection } from "@/components/dashboard/SpecialtyDomainsSection";
import { QualitySection } from "@/components/dashboard/QualitySection";

export default function DashboardPage() {
  const { data, error, isLoading } = useSWR<InstitutionSummary>(
    "/institution/summary",
    () => api.get<InstitutionSummary>("/institution/summary"),
  );

  const { data: peerGroups } = usePeerGroups();
  const { data: profiles } = useWeightProfiles();

  const defaultGroupId = getDefaultPeerGroupId(peerGroups);
  const defaultProfileId = getDefaultWeightProfileId(profiles);

  const [currentGroupId, setCurrentGroupId] = useCurrentPeerGroupId(defaultGroupId, peerGroups?.map((g) => g.id));
  const [currentProfileId, setCurrentProfileId] = useCurrentWeightProfileId(defaultProfileId, profiles?.map((p) => p.id));
  const [coreOnly, setCoreOnly] = useCoreOnly();
  const [domain, setDomain] = useCurrentLeidenDomain();

  if (isLoading) {
    return <div className="text-gray-500 text-sm">{t("common.loading")}</div>;
  }

  if (error) {
    return (
      <div className="text-red-600 text-sm">
        {t("header.loadError")}
      </div>
    );
  }

  if (!data) return null;

  const neverSynced = !data.last_openalex_sync;

  return (
    <div>
      <StickyHeader
        institutionName={data.institution_name}
        openalexId={data.openalex_institution_id}
        countryCode={data.country_code}
        periodStart={data.period_start}
        periodEnd={data.period_end}
        leidenDecileLabel={data.leiden_decile_label}
        coreOnly={coreOnly}
        onCoreOnlyChange={setCoreOnly}
        domain={domain}
        onDomainChange={setDomain}
        profiles={profiles}
        currentProfileId={currentProfileId}
        onProfileChange={setCurrentProfileId}
        groups={peerGroups}
        currentGroupId={currentGroupId}
        onGroupChange={setCurrentGroupId}
      />

      <div className="max-w-4xl">
        {neverSynced && (
          <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
            <strong>{t("header.neverSyncedTitle")}</strong> {t("header.neverSyncedBody")} <em>{t("nav.configuration")}</em>.
          </div>
        )}

        <SynthesisSection
          summary={data}
          coreOnly={coreOnly}
          peerGroupId={currentGroupId}
          weightProfileId={currentProfileId}
          field={domain}
        />

        {currentGroupId ? (
          <>
            <ImpactCitationsSection peerGroupId={currentGroupId} coreOnly={coreOnly} field={domain} />
            <SpecialtyDomainsSection peerGroupId={currentGroupId} />
          </>
        ) : (
          <div className="mb-8 bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-500">
            {t("header.noGroupAvailableBefore")} <em>{t("nav.settings")}</em>{t("header.noGroupAvailableAfter")}
          </div>
        )}

        <QualitySection
          coreOnly={coreOnly}
          peerGroupId={currentGroupId}
          periodStart={data.period_start}
          periodEnd={data.period_end}
        />

        {data.leiden_snapshot_year && (
          <div className="mt-6 text-xs text-gray-400 flex items-center gap-1.5">
            <Clock size={12} />
            {t("header.footerLeidenEdition", { year: data.leiden_snapshot_year })}
            {data.last_openalex_sync
              ? t("header.footerOpenalexSynced", {
                  date: new Intl.DateTimeFormat("fr-FR").format(new Date(data.last_openalex_sync)),
                })
              : t("header.footerOpenalexNever")}
          </div>
        )}
      </div>
    </div>
  );
}
