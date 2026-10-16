"use client";

import { useEffect, useState } from "react";
import useSWR, { mutate as globalMutate } from "swr";
import { CheckCircle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { QualityCategoryWeights, QualityCategoryWeightsResponse } from "@/types/api";
import { t } from "@/lib/i18n";

const KEYS = ["qualite_ex_ante", "qualite_intrinseque", "qualite_ex_post"] as const;

function toPercent(w: QualityCategoryWeights): Record<(typeof KEYS)[number], number> {
  return Object.fromEntries(KEYS.map((k) => [k, Math.round(w[k] * 1000) / 10])) as Record<(typeof KEYS)[number], number>;
}

/**
 * Instance-wide weighting between the evaluation-grid categories (ex-ante /
 * intrinsic / ex-post) in the benchmark's quality axis — moved here from the
 * comparison profiles. Applied at request time (no re-evaluation needed).
 */
export function CategoryWeightsPanel() {
  const { data, mutate } = useSWR<QualityCategoryWeightsResponse>("/quality/category-weights", (url: string) =>
    api.get<QualityCategoryWeightsResponse>(url),
  );
  const [draft, setDraft] = useState<Record<(typeof KEYS)[number], number> | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (data) setDraft(toPercent(data.weights));
  }, [data]);

  if (!data || !draft) return null;
  // Categories without any valid (non-neutral, non-impact) criterion: weight locked at 0.
  const inactive = new Set(data.inactive);
  const total = Math.round(KEYS.reduce((s, k) => s + draft[k], 0) * 10) / 10;
  const saved = toPercent(data.weights);
  const dirty = KEYS.some((k) => Math.abs(draft[k] - saved[k]) > 0.05);
  const valid = Math.abs(total - 100) <= 0.1 && KEYS.every((k) => draft[k] >= 0);

  async function handleSave() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const body = Object.fromEntries(KEYS.map((k) => [k, draft[k] / total]));
      const updated = await api.put<QualityCategoryWeightsResponse>("/quality/category-weights", body);
      await mutate(updated, { revalidate: false });
      // Dashboard data computed with the previous weights.
      await globalMutate((key) => typeof key === "string" && key.includes("/benchmark"));
      setMessage(t("qualitySettings.categoryWeightsSaved"));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("qualitySettings.saveError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white border rounded-lg p-4 mb-6">
      <h2 className="text-sm font-semibold text-gray-800">{t("qualitySettings.categoryWeightsTitle")}</h2>
      <p className="text-xs text-gray-500 mt-1 mb-3 leading-relaxed">{t("qualitySettings.categoryWeightsIntro")}</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {KEYS.map((key) => (
          <label key={key} className="block">
            <span className="flex justify-between text-xs text-gray-600 mb-1">
              {t(`qualitySettings.category_${key}`)}
              {inactive.has(key) && <span className="text-gray-400">{t("qualitySettings.categoryInactive")}</span>}
              <span className="font-semibold text-brand-700 tabular-nums">{draft[key].toLocaleString("fr-FR")} %</span>
            </span>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={draft[key]}
              disabled={inactive.has(key)}
              onChange={(e) => {
                setDraft({ ...draft, [key]: Number(e.target.value) });
                setMessage(null);
              }}
              className="w-full accent-brand-600 disabled:opacity-40"
            />
          </label>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2 mt-3">
        <span className={`text-xs tabular-nums ${valid ? "text-gray-500" : "text-red-600"}`}>
          {t("qualitySettings.categoryWeightsTotal", { total: total.toLocaleString("fr-FR") })}
        </span>
        <button
          onClick={handleSave}
          disabled={saving || !dirty || total <= 0}
          className="ml-auto px-3 py-1.5 bg-brand-600 text-white text-sm rounded disabled:opacity-50"
          title={!valid ? t("qualitySettings.categoryWeightsNormalizeHint") : undefined}
        >
          {saving ? t("qualitySettings.saving") : valid ? t("common.save") : t("qualitySettings.categoryWeightsNormalize")}
        </button>
        <button
          onClick={() => {
            const active = KEYS.filter((k) => !inactive.has(k));
            setDraft(
              Object.fromEntries(
                KEYS.map((k) => [k, inactive.has(k) ? 0 : Math.round(1000 / active.length) / 10]),
              ) as Record<(typeof KEYS)[number], number>,
            );
          }}
          disabled={saving}
          className="px-3 py-1.5 text-sm border rounded text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          {t("qualitySettings.categoryWeightsEqual")}
        </button>
      </div>
      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      {message && (
        <p className="text-xs text-green-700 mt-2 flex items-center gap-1">
          <CheckCircle size={13} /> {message}
        </p>
      )}
    </div>
  );
}
