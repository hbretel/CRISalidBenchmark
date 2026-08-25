"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { ImpactIndicators } from "@/types/api";
import { SubIndicatorCard } from "@/components/indicators/SubIndicatorCard";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { LEIDEN_DOMAINS } from "@/lib/constants";

interface Props {
  peerGroupId: number | null;
  coreOnly: boolean;
}

export function ImpactCitationsSection({ peerGroupId, coreOnly }: Props) {
  const [field, setField] = useState("All sciences");

  const { data, isLoading, error } = useSWR<ImpactIndicators>(
    peerGroupId
      ? `/indicators/impact-scientifique?peer_group_id=${peerGroupId}&field=${encodeURIComponent(field)}&core_only=${coreOnly}`
      : null,
    (url: string) => api.get<ImpactIndicators>(url),
  );

  const headline = data?.indicators.impact_normalise_leiden;
  const headlineLabel =
    headline?.leiden_column === "pp_10_cits"
      ? "% avec ≥ 10 citations (pp_10_cits)"
      : "% top 10% cités (pp_top_10)";
  const hIndexLabel =
    data?.period_start && data?.period_end
      ? `Indice h (publications core, ${data.period_start}–${data.period_end})`
      : "Indice h (publications core)";

  return (
    <section className="mb-10">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h2 className="text-base font-semibold text-gray-800">Impact en citations</h2>
        <div className="flex items-center gap-1.5">
          <label className="text-xs text-gray-500 flex items-center gap-1">
            Grand domaine Leiden
            <InfoTooltip text="Le Leiden Ranking publie ses indicateurs au niveau de l'établissement entier ('Tous les domaines') et sur 5 grands domaines. Cette granularité est plus grossière que les Topics OpenAlex (~4 500 topics)." />
          </label>
          <select
            className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            value={field}
            onChange={(e) => setField(e.target.value)}
          >
            {LEIDEN_DOMAINS.map((d) => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
        <strong>Note méthodologique :</strong> les indicateurs Leiden (pp_top_10/pp_10_cits, pp_int_collab, pp_oa)
        proviennent directement du Leiden Ranking Open Edition (comptage complet uniquement, édition{" "}
        {data?.snapshot_year ?? "…"}), normalisés par domaine par CWTS. Les indicateurs OpenAlex
        (citations, h-index) sont recalculés nocturnement et non normalisés.
        {headline?.leiden_column === "pp_10_cits" && (
          <>
            {" "}En mode « toutes les publications », l&apos;indicateur vedette change de nature :
            il mesure la part de publications ayant reçu au moins 10 citations, sans normalisation
            par discipline — ce n&apos;est pas la même chose que pp_top_10 (mode « publications core »).
          </>
        )}
      </div>

      {isLoading && <div className="text-gray-500 text-sm">Calcul en cours…</div>}
      {error && <div className="text-red-600 text-sm">Erreur lors du calcul des indicateurs.</div>}

      {data && (
        <>
          <div className="text-xs text-gray-400 mb-4">
            Percentiles calculés parmi {data.peer_group_size} établissements pairs (univers Leiden Ranking).
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SubIndicatorCard label={headlineLabel} indicator={data.indicators.impact_normalise_leiden} unit="%" />
            <SubIndicatorCard label="MNCS (citations normalisées, mode core uniquement)" indicator={data.indicators.mncs} />
            <SubIndicatorCard
              label="Citations moyennes par publication"
              indicator={data.indicators.citations_brutes_moyennes}
              formatValue={(v) => v.toFixed(1)}
            />
            <SubIndicatorCard label={hIndexLabel} indicator={data.indicators.h_index_core} />
            <SubIndicatorCard label="% accès ouvert" indicator={data.indicators.oa_pct} unit="%" />
            <SubIndicatorCard label="% collaboration internationale" indicator={data.indicators.collab_intl_pct} unit="%" />
          </div>
        </>
      )}
    </section>
  );
}
