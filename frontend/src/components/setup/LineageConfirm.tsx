"use client";

import type { LineageInfo, ValidateResponse } from "@/types/api";
import { CheckCircle, AlertTriangle, Building2 } from "lucide-react";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface Props {
  data: ValidateResponse;
  institutionName: string;
  onNameChange: (name: string) => void;
  onConfirm: () => void;
  onBack: () => void;
}

/**
 * Lineage confirmation step of the setup wizard.
 *
 * Shows the full list of ROR child institutions included in the ingestion
 * perimeter. This is critical for federated/merged universities whose
 * publications are distributed across multiple OpenAlex institution nodes.
 *
 * The user cannot exclude members from the lineage in MVP v1 — this step
 * is a guard to catch obvious errors (e.g. unexpected children, or missing
 * known components due to incomplete ROR data for French institutions).
 */
export function LineageConfirm({
  data,
  institutionName,
  onNameChange,
  onConfirm,
  onBack,
}: Props) {
  const hasChildren = data.lineage.length > 1;

  return (
    <div className="space-y-5">
      {/* Institution name field */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Nom d'affichage de l'établissement
        </label>
        <input
          type="text"
          value={institutionName}
          onChange={(e) => onNameChange(e.target.value)}
          className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <p className="text-xs text-gray-500 mt-1">
          Pré-rempli depuis OpenAlex — modifiable.
        </p>
      </div>

      {/* Lineage section */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm font-medium text-gray-700">
            Périmètre institutionnel (lineage ROR){" "}
          </span>
          <InfoTooltip text="Le périmètre d'ingestion inclut l'établissement configuré et ses structures 'enfants' (ex. composantes d'une université fédérale). Ces structures sont détectées à partir du champ associated_institutions d'OpenAlex (relation 'child'), pas du seul champ lineage — pour de nombreux établissements français, lineage revient vide au-delà de l'établissement lui-même alors que associated_institutions liste bien les composantes réelles. Note méthodologique : ce périmètre reste une curation OpenAlex, pas une hiérarchie ROR officielle, et peut différer de celui retenu par le Leiden Ranking (voir §4.1 de la spécification)." />
        </div>

        {hasChildren ? (
          <div className="bg-amber-50 border border-amber-200 rounded p-3 mb-3 text-xs text-amber-800">
            <div className="flex items-start gap-2">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <span>
                <strong>Établissement fédéral/fusionné détecté :</strong> l'ingestion couvrira{" "}
                {data.lineage.length} structures. Vérifiez que la liste ci-dessous est correcte
                avant de continuer. Les données ROR pour le système français peuvent être
                incomplètes (certaines composantes manquantes ou incluses par erreur).
              </span>
            </div>
          </div>
        ) : (
          <div className="bg-green-50 border border-green-200 rounded p-3 mb-3 text-xs text-green-800">
            <div className="flex items-start gap-2">
              <CheckCircle size={14} className="mt-0.5 shrink-0" />
              <span>
                Aucune structure enfant détectée (ni via lineage, ni via associated_institutions).
                L'ingestion couvrira l'établissement seul.
              </span>
            </div>
          </div>
        )}

        <div className="border rounded divide-y max-h-64 overflow-y-auto">
          {data.lineage.map((item: LineageInfo, i: number) => (
            <div key={item.openalex_id} className="flex items-center gap-3 px-3 py-2 text-sm">
              <Building2
                size={15}
                className={i === 0 ? "text-brand-600" : "text-gray-400"}
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">
                  {item.display_name}
                  {i === 0 && (
                    <span className="ml-2 text-xs bg-brand-100 text-brand-700 px-1.5 py-0.5 rounded">
                      établissement principal
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-400">
                  OpenAlex: {item.openalex_id}
                  {item.ror_id && ` · ROR: ${item.ror_id}`}
                </div>
              </div>
            </div>
          ))}
        </div>

        <p className="text-xs text-gray-500 mt-2">
          En v1, le périmètre ne peut pas être modifié manuellement. Si une structure est
          manquante ou incorrecte, signalez-le à l'équipe OpenAlex/ROR ou documentez l'écart.
        </p>
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 text-sm border rounded text-gray-600 hover:bg-gray-50"
        >
          Retour
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="flex-1 py-2 px-4 bg-brand-600 text-white rounded text-sm font-medium hover:bg-brand-700"
        >
          Confirmer et enregistrer
        </button>
      </div>
    </div>
  );
}
