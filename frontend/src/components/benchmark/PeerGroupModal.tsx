"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { usePeerGroupMembers } from "@/hooks/usePeerGroups";
import type { PeerGroupSummary } from "@/types/api";
import { Modal } from "@/components/ui/Modal";
import { t } from "@/lib/i18n";

interface SearchResult {
  ror_id: string;
  university_name: string | null;
  country_code: string | null;
  p: number | null;
}

interface Props {
  open: boolean;
  onClose: () => void;
  editingGroup: PeerGroupSummary | null;
  onSaved: (group: PeerGroupSummary) => void;
}

/**
 * Create/edit modal for custom comparison groups — deliberately mirrors
 * WeightProfileModal's layout (header, body, Annuler/Sauvegarder) per the
 * spec's "reprend les mêmes codes" requirement, and reuses the same
 * search/select flow the inline builder used before it moved into a modal.
 */
export function PeerGroupModal({ open, onClose, editingGroup, onSaved }: Props) {
  const { data: existingMembers } = usePeerGroupMembers(editingGroup?.id ?? null);

  const [name, setName] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [selected, setSelected] = useState<Map<string, SearchResult>>(new Map());
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName(editingGroup?.name ?? "");
    setSearchQ("");
    setSearchResults([]);
    setHasSearched(false);
    setSaveError(null);
    setSelected(
      new Map(
        (existingMembers ?? []).map((m) => [
          m.ror_id,
          { ror_id: m.ror_id, university_name: m.university_name, country_code: m.country_code, p: m.p },
        ]),
      ),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, editingGroup, existingMembers]);

  async function handleSearch() {
    if (searchQ.trim().length < 2) return;
    setSearching(true);
    setSearchError(null);
    try {
      const res = await api.get<SearchResult[]>(
        `/peer-groups/leiden-institutions?q=${encodeURIComponent(searchQ.trim())}`,
      );
      setSearchResults(res);
      setHasSearched(true);
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.detail : t("peerGroupModal.searchError"));
    } finally {
      setSearching(false);
    }
  }

  function toggle(r: SearchResult) {
    const next = new Map(selected);
    if (next.has(r.ror_id)) next.delete(r.ror_id);
    else next.set(r.ror_id, r);
    setSelected(next);
  }

  async function handleSave() {
    if (!name.trim() || selected.size === 0) return;
    setSaving(true);
    setSaveError(null);
    try {
      const body = { name: name.trim(), ror_ids: Array.from(selected.keys()) };
      const group = editingGroup
        ? await api.put<PeerGroupSummary>(`/peer-groups/${editingGroup.id}`, body)
        : await api.post<PeerGroupSummary>("/peer-groups", body);
      onSaved(group);
      onClose();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.detail : t("peerGroupModal.saveError"));
    } finally {
      setSaving(false);
    }
  }

  const selectedList = Array.from(selected.values());

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editingGroup ? t("peerGroupModal.editTitle") : t("peerGroupModal.newTitle")}
      maxWidth="max-w-xl"
    >
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">{t("peerGroupModal.nameLabel")}</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("peerGroupModal.namePlaceholder")}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {selectedList.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-600 mb-1">
              {t("peerGroupModal.selectedCount", { count: selectedList.length })}
            </p>
            <div className="border rounded divide-y max-h-32 overflow-y-auto text-sm">
              {selectedList.map((r) => (
                <div key={r.ror_id} className="flex items-center justify-between px-3 py-1.5">
                  <span>{r.university_name ?? r.ror_id}</span>
                  <button
                    type="button"
                    onClick={() => toggle(r)}
                    className="text-xs text-gray-400 hover:text-red-600"
                  >
                    {t("common.remove")}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">{t("peerGroupModal.addLabel")}</label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder={t("peerGroupModal.searchPlaceholder")}
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1 border rounded px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={handleSearch}
              disabled={searching || searchQ.trim().length < 2}
              className="px-3 py-2 bg-gray-100 rounded text-sm border hover:bg-gray-200 disabled:opacity-50"
            >
              {searching ? t("peerGroupModal.searching") : t("peerGroupModal.search")}
            </button>
          </div>
          {searchError && <p className="text-xs text-red-600 mt-2">{searchError}</p>}
          {hasSearched && !searching && searchResults.length === 0 && !searchError && (
            <p className="text-xs text-gray-500 mt-2">
              {t("peerGroupModal.noResults", { query: searchQ })}
            </p>
          )}
          {searchResults.length > 0 && (
            <div className="border rounded divide-y max-h-48 overflow-y-auto text-sm mt-2">
              {searchResults.map((r) => (
                <label key={r.ror_id} className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selected.has(r.ror_id)}
                    onChange={() => toggle(r)}
                    className="accent-brand-600"
                  />
                  <span className="flex-1">{r.university_name ?? r.ror_id}</span>
                  <span className="text-gray-400 text-xs">{r.country_code}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {saveError && <p className="text-xs text-red-600">{saveError}</p>}

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded text-gray-600 hover:bg-gray-50"
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !name.trim() || selected.size === 0}
            className="flex-1 py-2 px-4 bg-brand-600 text-white rounded text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? t("common.saving") : t("peerGroupModal.saveButton")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
