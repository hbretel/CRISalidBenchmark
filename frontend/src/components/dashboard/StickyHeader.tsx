"use client";

import { Switch } from "@/components/ui/Switch";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import type { PeerGroupSummary, WeightProfileResponse } from "@/types/api";

interface Props {
  institutionName: string;
  openalexId: string;
  countryCode: string | null;
  periodStart: number | null;
  periodEnd: number | null;
  leidenDecileLabel: string | null;
  coreOnly: boolean;
  onCoreOnlyChange: (v: boolean) => void;
  profiles: WeightProfileResponse[] | undefined;
  currentProfileId: number | null;
  onProfileChange: (id: number) => void;
  groups: PeerGroupSummary[] | undefined;
  currentGroupId: number | null;
  onGroupChange: (id: number) => void;
}

const CORE_TOOLTIP =
  "Les « publications core » approximent la définition Leiden : source dans la liste CWTS Core " +
  "(~36 000 revues), type article/revue/chapitre d'ouvrage, langue anglaise, non rétracté. " +
  "Activé par défaut pour rester cohérent avec les indicateurs Leiden calculés sur ce sous-ensemble. " +
  "Désactivé, l'indicateur de citation vedette change de nature : il devient le pourcentage de " +
  "publications ayant reçu au moins 10 citations (seuil absolu, non normalisé par domaine), et non " +
  "plus un simple élargissement du même chiffre.";

export function StickyHeader({
  institutionName,
  openalexId,
  countryCode,
  periodStart,
  periodEnd,
  leidenDecileLabel,
  coreOnly,
  onCoreOnlyChange,
  profiles,
  currentProfileId,
  onProfileChange,
  groups,
  currentGroupId,
  onGroupChange,
}: Props) {
  const period = periodStart && periodEnd ? `${periodStart}–${periodEnd}` : "—";

  return (
    <div className="sticky top-0 z-30 -mx-6 -mt-6 px-6 pt-4 pb-3 mb-6 bg-white/95 backdrop-blur border-b">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-3">
        <h1 className="text-lg font-bold text-gray-900">{institutionName}</h1>
        <div className="text-xs text-gray-500 flex items-center gap-2">
          <span>{openalexId}</span>
          {countryCode && (
            <>
              <span className="text-gray-300">·</span>
              <span>{countryCode}</span>
            </>
          )}
          <span className="text-gray-300">·</span>
          <span>{period}</span>
          {leidenDecileLabel && (
            <>
              <span className="text-gray-300">·</span>
              <span className="text-brand-600" title="Décile Leiden (nombre de publications) d'appartenance">
                {leidenDecileLabel}
              </span>
            </>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <div className="flex items-center gap-1.5">
          <Switch checked={coreOnly} onChange={onCoreOnlyChange} label="Publications core uniquement" />
          <InfoTooltip text={CORE_TOOLTIP} />
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs text-gray-500">Profil de comparaison</label>
          <select
            className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            value={currentProfileId ?? ""}
            onChange={(e) => onProfileChange(Number(e.target.value))}
          >
            {!profiles && <option>Chargement…</option>}
            {profiles?.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          <label className="text-xs text-gray-500">Groupe de comparaison</label>
          <select
            className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            value={currentGroupId ?? ""}
            onChange={(e) => onGroupChange(Number(e.target.value))}
          >
            {!groups && <option>Chargement…</option>}
            {groups?.map((g) => (
              <option key={g.id} value={g.id}>{g.name} ({g.member_count})</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
