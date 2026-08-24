"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { SpecificityIndicators } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { Treemap, ResponsiveContainer } from "recharts";

const HERFINDAHL_COLORS: Record<string, string> = {
  "peu spécialisé": "bg-blue-100 text-blue-800 border-blue-200",
  "moyennement spécialisé": "bg-amber-100 text-amber-800 border-amber-200",
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
              Carte thématique (Topics OpenAlex)
              <InfoTooltip text="Répartition des publications par domaine et sous-champ selon la taxonomie Topics d'OpenAlex (Domain > Field > Subfield > Topic). La surface est proportionnelle au nombre de publications." />
            </h3>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <Treemap data={data.thematic_profile} dataKey="total" aspectRatio={4 / 3} stroke="#fff" fill="#3b82f6" />
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              {data.total_works_analysed.toLocaleString("fr-FR")} publications analysées (corpus complet)
            </p>
          </div>

          <div className="bg-white border rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              Indice de Herfindahl (spécialisation disciplinaire)
              <InfoTooltip text={data.herfindahl.description} />
            </h3>
            <div className="flex items-center gap-4">
              <span className="text-3xl font-bold text-gray-900">{data.herfindahl.value.toFixed(3)}</span>
              <span
                className={`text-sm font-medium px-2.5 py-1 rounded border ${
                  HERFINDAHL_COLORS[data.herfindahl.label] ?? "bg-gray-100 text-gray-700 border-gray-200"
                }`}
              >
                {data.herfindahl.label}
              </span>
            </div>
            <div className="mt-3 text-xs text-gray-500">
              Calculé au niveau <em>field</em> (2e niveau de la hiérarchie OpenAlex). H ∈ [0, 1] —
              H proche de 0 : diffus ; H proche de 1 : très concentré.
            </div>
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
              <div className="divide-y">
                {data.topics_signature.items.slice(0, 20).map((t) => (
                  <div key={t.topic_id} className="py-2 flex items-center justify-between text-sm">
                    <span className="font-mono text-xs text-gray-500">{t.topic_id}</span>
                    <div className="flex items-center gap-4 text-xs text-gray-600">
                      <span>Établ. {t.own_share.toFixed(1)}%</span>
                      <span>Pairs {t.peer_avg_share.toFixed(1)}%</span>
                      <span className="font-semibold text-green-700">×{t.ratio.toFixed(1)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
