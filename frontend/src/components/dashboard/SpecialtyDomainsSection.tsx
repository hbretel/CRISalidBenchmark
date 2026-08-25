"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { SpecificityIndicators } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { ThematicTreemap } from "./ThematicTreemap";
import { TopicsSignatureTable } from "./TopicsSignatureTable";

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
      <h2 className="text-base font-semibold text-gray-800 mb-1">Domaines de spécialité</h2>
      <p className="text-sm text-gray-500 mb-4">
        Profil thématique de l&apos;établissement (corpus complet, pas de filtre core).
      </p>

      <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
        <strong>Note :</strong> cet axe utilise le corpus complet (sans filtre core), car la définition
        core Leiden favorise les revues anglophones et exclurait une partie du profil SHS ou recherche
        appliquée. La comparaison aux pairs est basée sur le <strong>volume</strong> de publications
        par topic (pas l&apos;impact).
      </div>

      {isLoading && <div className="text-gray-500 text-sm">Calcul en cours…</div>}
      {error && <div className="text-red-600 text-sm">Erreur lors du calcul.</div>}

      {data && (
        <div className="space-y-6">
          <div className="bg-white border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              Indice de Herfindahl (spécialisation disciplinaire)
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
            <div className="mt-3 text-xs text-gray-500">
              Calculé au niveau <em>field</em> (2e niveau de la hiérarchie OpenAlex). H ∈ [0, 1] —
              H proche de 0 : diffus ; H proche de 1 : très concentré.
            </div>
          </div>

          <div className="bg-white border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              Carte thématique (Topics OpenAlex)
              <InfoTooltip text="Répartition des publications selon la taxonomie Topics d'OpenAlex (Domain > Field > Subfield > Topic). La surface est proportionnelle au nombre de publications. Cliquez sur une case pour explorer le niveau suivant." />
            </h3>
            <ThematicTreemap data={data.thematic_profile} totalWorks={data.total_works_analysed} />
          </div>

          <div className="bg-white border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-1 flex items-center gap-2">
              Topics signature
              <InfoTooltip text={data.topics_signature.description} />
            </h3>
            {!data.topics_signature.peer_cache_populated && (
              <div className="mb-3 bg-amber-50 border border-amber-200 rounded p-2 text-xs text-amber-700">
                Le cache de distribution par topic des pairs n&apos;est pas encore peuplé.
                Rendez-vous sur <em>Paramètres du benchmark</em> pour déclencher le calcul.
              </div>
            )}
            {data.topics_signature.items.length === 0 ? (
              <p className="text-sm text-gray-500">
                Aucun topic ne dépasse le seuil (×{data.topics_signature.threshold}) par rapport aux pairs.
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
