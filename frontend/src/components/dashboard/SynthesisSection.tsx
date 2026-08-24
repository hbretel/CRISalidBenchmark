"use client";

import useSWR from "swr";
import { FileText, TrendingUp, Award } from "lucide-react";
import { api } from "@/lib/api";
import type { ImpactIndicators, InstitutionSummary } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface Props {
  summary: InstitutionSummary;
  coreOnly: boolean;
  peerGroupId: number | null;
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

export function SynthesisSection({ summary, coreOnly, peerGroupId }: Props) {
  const { data: impact } = useSWR<ImpactIndicators>(
    peerGroupId
      ? `/indicators/impact-scientifique?peer_group_id=${peerGroupId}&field=${encodeURIComponent("All sciences")}&core_only=${coreOnly}`
      : null,
    (url: string) => api.get<ImpactIndicators>(url),
  );

  const publications = coreOnly ? summary.core_works : summary.total_works;
  const citations = coreOnly ? summary.core_citations : summary.total_citations;
  const headline = impact?.indicators.impact_normalise_leiden;
  const headlineLabel =
    headline?.leiden_column === "pp_10_cits"
      ? "% avec au moins 10 citations"
      : "% dans le top 10% le plus cité";

  return (
    <section className="mb-10">
      <h2 className="text-base font-semibold text-gray-800 mb-4">Synthèse</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          label="Nombre de publications"
          value={publications.toLocaleString("fr-FR")}
          icon={FileText}
          tooltip={
            coreOnly
              ? "Publications « core » : approximation de la définition Leiden (source CWTS Core, type article/revue/chapitre, anglais, non rétracté)."
              : "Ensemble des publications synchronisées depuis OpenAlex, sans filtre core."
          }
        />
        <StatCard
          label="Somme des citations"
          value={citations.toLocaleString("fr-FR")}
          icon={TrendingUp}
          tooltip={coreOnly ? "Somme des citations reçues par les publications core." : "Somme des citations reçues par l'ensemble des publications."}
        />
        <StatCard
          label={headlineLabel}
          value={headline?.value != null ? `${headline.value}%` : "—"}
          icon={Award}
          tooltip="Indicateur d'impact par défaut du Leiden Ranking : en mode publications core, la part de publications dans le top 10% le plus cité (normalisée par domaine) ; en mode toutes les publications, la part de publications ayant reçu au moins 10 citations (seuil absolu, non normalisé — ce n'est pas le même indicateur)."
        />
      </div>
    </section>
  );
}
