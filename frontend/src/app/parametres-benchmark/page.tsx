"use client";

import { useState } from "react";
import { Pencil, Plus, Trash2, Users } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { AXIS_LABELS } from "@/lib/constants";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { WeightProfileModal } from "@/components/benchmark/WeightProfileModal";
import { PeerGroupModal } from "@/components/benchmark/PeerGroupModal";
import { LeidenImportPanel } from "@/components/benchmark/LeidenImportPanel";
import { PeerTopicCachePanel } from "@/components/benchmark/PeerTopicCachePanel";
import { useWeightProfiles, getDefaultWeightProfileId } from "@/hooks/useWeightProfiles";
import { usePeerGroups, getDefaultPeerGroupId } from "@/hooks/usePeerGroups";
import { useCurrentPeerGroupId, useCurrentWeightProfileId } from "@/hooks/useCurrentSelection";
import { useSyncStatus } from "@/hooks/useSyncStatus";
import type { PeerGroupSummary, WeightProfileResponse } from "@/types/api";

const TYPE_LABELS: Record<string, string> = {
  geographic: "Géographique",
  size_bracket: "Tranche de taille",
  custom: "Personnalisé",
};

function pct(v: number) {
  return Math.round(v * 100);
}

/** Mini stacked bar showing the impact / specialisation split of a profile. */
function ProfileThumbnail({ profile }: { profile: WeightProfileResponse }) {
  const impact = pct(profile.axis_weights.impact_scientifique ?? 0);
  const specificite = 100 - impact;
  return (
    <div className="w-full h-2 rounded-full overflow-hidden flex bg-gray-100">
      <div className="bg-brand-500 h-full" style={{ width: `${impact}%` }} title={`${AXIS_LABELS.impact_scientifique} ${impact}%`} />
      <div className="bg-amber-400 h-full" style={{ width: `${specificite}%` }} title={`${AXIS_LABELS.specificite_disciplinaire} ${specificite}%`} />
    </div>
  );
}

export default function ParametresBenchmarkPage() {
  const { data: profiles, mutate: mutateProfiles } = useWeightProfiles();
  const { data: groups, mutate: mutateGroups } = usePeerGroups();
  const { jobs, lastLeidenSync } = useSyncStatus();
  const leidenImportRunning = jobs.some((j) => j.job_name === "leiden_annual" && j.status === "running");
  const noLeidenDataYet = !lastLeidenSync && (groups?.length ?? 0) === 0;

  const defaultProfileId = getDefaultWeightProfileId(profiles);
  const defaultGroupId = getDefaultPeerGroupId(groups);
  const [currentProfileId, setCurrentProfileId] = useCurrentWeightProfileId(
    defaultProfileId,
    profiles?.map((p) => p.id),
  );
  const [currentGroupId, setCurrentGroupId] = useCurrentPeerGroupId(defaultGroupId, groups?.map((g) => g.id));

  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<WeightProfileResponse | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  const [groupModalOpen, setGroupModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<PeerGroupSummary | null>(null);
  const [groupError, setGroupError] = useState<string | null>(null);

  const currentProfile = profiles?.find((p) => p.id === currentProfileId);
  const currentGroup = groups?.find((g) => g.id === currentGroupId);
  const customGroups = groups?.filter((g) => g.type === "custom") ?? [];
  const predefinedGroups = groups?.filter((g) => g.type !== "custom") ?? [];

  async function handleDeleteProfile(id: number) {
    if (!confirm("Supprimer ce profil de comparaison ?")) return;
    setProfileError(null);
    try {
      await api.delete(`/weight-profiles/${id}`);
      mutateProfiles();
    } catch (err) {
      setProfileError(err instanceof ApiError ? err.detail : "Erreur lors de la suppression.");
    }
  }

  async function handleDeleteGroup(id: number) {
    if (!confirm("Supprimer ce groupe de comparaison ?")) return;
    setGroupError(null);
    try {
      await api.delete(`/peer-groups/${id}`);
      mutateGroups();
    } catch (err) {
      setGroupError(err instanceof ApiError ? err.detail : "Erreur lors de la suppression.");
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-xl font-bold text-gray-900">Paramètres du benchmark</h1>
      </div>

      {/* ── Profils de comparaison ─────────────────────────────────────── */}
      <section className="mb-10">
        <h2 className="text-base font-semibold text-gray-800 mb-1">Profils de comparaison</h2>
        <p className="text-sm text-gray-500 mb-4">
          Définissez sous quels angles vous souhaitez comparer votre établissement. Choisissez ou
          créez des profils de comparaison en attribuant des poids aux indicateurs disponibles.
        </p>

        {currentProfile && (
          <div className="bg-white border rounded-lg p-4 mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">
                Profil actuel : <span className="text-brand-700">{currentProfile.name}</span>
              </span>
              <InfoTooltip text="Le profil de comparaison actuel pondère les indicateurs de l'axe impact en citations et de l'axe domaines de spécialité pour le score composite. Il peut aussi être changé depuis l'en-tête du tableau de bord." />
            </div>
            <ProfileThumbnail profile={currentProfile} />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>{AXIS_LABELS.impact_scientifique}</span>
              <span>{AXIS_LABELS.specificite_disciplinaire}</span>
            </div>
          </div>
        )}

        {profileError && <p className="text-xs text-red-600 mb-2">{profileError}</p>}

        <div className="bg-white border rounded-lg divide-y">
          {!profiles && <p className="text-xs text-gray-400 p-4">Chargement…</p>}
          {profiles?.map((p) => (
            <div key={p.id} className="flex items-center justify-between px-4 py-2.5">
              <label className="flex items-center gap-2 text-sm cursor-pointer flex-1">
                <input
                  type="radio"
                  name="current-profile"
                  checked={currentProfileId === p.id}
                  onChange={() => setCurrentProfileId(p.id)}
                  className="accent-brand-600"
                />
                <span className={currentProfileId === p.id ? "font-medium text-gray-900" : "text-gray-700"}>
                  {p.name}
                </span>
                {p.is_default && (
                  <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">par défaut</span>
                )}
              </label>
              <div className="flex items-center gap-1">
                {!p.is_default && (
                  <>
                    <button
                      onClick={() => { setEditingProfile(p); setProfileModalOpen(true); }}
                      title="Modifier"
                      className="p-1.5 text-gray-500 hover:text-brand-600 rounded"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => handleDeleteProfile(p.id)}
                      title="Supprimer"
                      className="p-1.5 text-gray-500 hover:text-red-600 rounded"
                    >
                      <Trash2 size={14} />
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>

        <button
          onClick={() => { setEditingProfile(null); setProfileModalOpen(true); }}
          className="mt-3 flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700 font-medium"
        >
          <Plus size={15} /> Nouveau profil de comparaison
        </button>
      </section>

      {/* ── Groupes de comparaison ─────────────────────────────────────── */}
      <section>
        <h2 className="text-base font-semibold text-gray-800 mb-1">Groupes de comparaison</h2>
        <p className="text-sm text-gray-500 mb-4">
          Définissez avec quel groupe vous souhaitez comparer votre établissement. Choisissez parmi
          les groupes disponibles ou créez vos propres groupes.
        </p>

        {currentGroup && (
          <div className="bg-white border rounded-lg p-4 mb-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-700">
                Groupe actuel : <span className="text-brand-700">{currentGroup.name}</span>
              </span>
              <InfoTooltip text="Le groupe de comparaison actuel sert de référence pour les percentiles affichés sur le tableau de bord. Il peut aussi être changé depuis l'en-tête du tableau de bord." />
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <Users size={13} />
              {currentGroup.member_count} établissements
            </div>
            <PeerTopicCachePanel groupId={currentGroup.id} />
          </div>
        )}

        {(noLeidenDataYet || leidenImportRunning) && (
          <LeidenImportPanel onImportStarted={() => mutateGroups()} />
        )}
        {leidenImportRunning && (
          <p className="text-xs text-gray-500 -mt-4 mb-4">
            Un import Leiden est en cours d&apos;exécution — les groupes de comparaison se rafraîchiront automatiquement.
          </p>
        )}

        {groupError && <p className="text-xs text-red-600 mb-2">{groupError}</p>}

        <div className="bg-white border rounded-lg divide-y mb-2">
          {!groups && <p className="text-xs text-gray-400 p-4">Chargement…</p>}
          {predefinedGroups.map((g) => (
            <GroupRow key={g.id} group={g} current={currentGroupId === g.id} onSelect={() => setCurrentGroupId(g.id)} />
          ))}
        </div>

        {customGroups.length > 0 && (
          <div className="bg-white border rounded-lg divide-y mb-2">
            {customGroups.map((g) => (
              <GroupRow
                key={g.id}
                group={g}
                current={currentGroupId === g.id}
                onSelect={() => setCurrentGroupId(g.id)}
                onEdit={() => { setEditingGroup(g); setGroupModalOpen(true); }}
                onDelete={() => handleDeleteGroup(g.id)}
              />
            ))}
          </div>
        )}

        <button
          onClick={() => { setEditingGroup(null); setGroupModalOpen(true); }}
          className="mt-1 flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700 font-medium"
        >
          <Plus size={15} /> Nouveau groupe de comparaison
        </button>
      </section>

      <WeightProfileModal
        open={profileModalOpen}
        onClose={() => setProfileModalOpen(false)}
        editingProfile={editingProfile}
        existingProfiles={profiles ?? []}
        onSaved={(p) => { mutateProfiles(); setCurrentProfileId(p.id); }}
      />
      <PeerGroupModal
        open={groupModalOpen}
        onClose={() => setGroupModalOpen(false)}
        editingGroup={editingGroup}
        onSaved={(g) => { mutateGroups(); setCurrentGroupId(g.id); }}
      />
    </div>
  );
}

function GroupRow({
  group,
  current,
  onSelect,
  onEdit,
  onDelete,
}: {
  group: PeerGroupSummary;
  current: boolean;
  onSelect: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5">
      <label className="flex items-center gap-2 text-sm cursor-pointer flex-1">
        <input type="radio" name="current-group" checked={current} onChange={onSelect} className="accent-brand-600" />
        <span className={current ? "font-medium text-gray-900" : "text-gray-700"}>{group.name}</span>
        <span className="text-xs text-gray-400">
          {TYPE_LABELS[group.type] ?? group.type} · {group.member_count}
        </span>
      </label>
      {(onEdit || onDelete) && (
        <div className="flex items-center gap-1">
          {onEdit && (
            <button onClick={onEdit} title="Modifier" className="p-1.5 text-gray-500 hover:text-brand-600 rounded">
              <Pencil size={14} />
            </button>
          )}
          {onDelete && (
            <button onClick={onDelete} title="Supprimer" className="p-1.5 text-gray-500 hover:text-red-600 rounded">
              <Trash2 size={14} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
