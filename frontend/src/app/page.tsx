"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { InstitutionSummary } from "@/types/api";
import { Clock } from "lucide-react";
import { usePeerGroups, getDefaultPeerGroupId } from "@/hooks/usePeerGroups";
import { useWeightProfiles, getDefaultWeightProfileId } from "@/hooks/useWeightProfiles";
import { useCurrentPeerGroupId, useCurrentWeightProfileId, useCoreOnly } from "@/hooks/useCurrentSelection";
import { StickyHeader } from "@/components/dashboard/StickyHeader";
import { SynthesisSection } from "@/components/dashboard/SynthesisSection";
import { ImpactCitationsSection } from "@/components/dashboard/ImpactCitationsSection";
import { SpecialtyDomainsSection } from "@/components/dashboard/SpecialtyDomainsSection";

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

  if (isLoading) {
    return <div className="text-gray-500 text-sm">Chargement…</div>;
  }

  if (error) {
    return (
      <div className="text-red-600 text-sm">
        Impossible de charger les données. Vérifiez que l&apos;instance est configurée.
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
            <strong>Aucune synchronisation effectuée.</strong> Les données ci-dessous sont vides.
            Une première synchronisation démarre automatiquement après la configuration initiale —
            si ce message persiste, relancez-la depuis <em>Configuration</em>.
          </div>
        )}

        <SynthesisSection summary={data} coreOnly={coreOnly} peerGroupId={currentGroupId} />

        {currentGroupId ? (
          <>
            <ImpactCitationsSection peerGroupId={currentGroupId} coreOnly={coreOnly} />
            <SpecialtyDomainsSection peerGroupId={currentGroupId} />
          </>
        ) : (
          <div className="mb-8 bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-500">
            Aucun groupe de comparaison disponible pour l&apos;instant — importez les données Leiden Ranking
            (page <em>Paramètres du benchmark</em>) pour voir votre positionnement.
          </div>
        )}

        {data.leiden_snapshot_year && (
          <div className="mt-6 text-xs text-gray-400 flex items-center gap-1.5">
            <Clock size={12} />
            Données Leiden : édition {data.leiden_snapshot_year} ·{" "}
            {data.last_openalex_sync
              ? `OpenAlex : ${new Intl.DateTimeFormat("fr-FR").format(new Date(data.last_openalex_sync))}`
              : "OpenAlex : jamais synchronisé"}
          </div>
        )}
      </div>
    </div>
  );
}
