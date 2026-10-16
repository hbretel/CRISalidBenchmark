"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { CheckCircle, ChevronRight, RotateCcw, Search } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { GridCalibration, GridCriterion } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { t } from "@/lib/i18n";

type Filter = "all" | "automated" | "comparable" | "modified";

/** Draft values per criterion: weight and threshold parameters (N/M). */
type Draft = Record<string, { weight: number | null; parameters: Record<string, number> }>;

function draftFrom(criteria: GridCriterion[]): Draft {
  return Object.fromEntries(
    criteria.map((c) => [c.id, { weight: c.weight, parameters: Object.fromEntries(c.parameters.map((p) => [p.name, p.value])) }]),
  );
}

function differsFromDefault(c: GridCriterion, d: Draft[string]): boolean {
  if (c.default_weight !== null && d.weight !== null && Math.abs(d.weight - c.default_weight) > 1e-9) return true;
  return c.parameters.some((p) => Math.abs((d.parameters[p.name] ?? p.default) - p.default) > 1e-9);
}

function differsFromSaved(c: GridCriterion, d: Draft[string]): boolean {
  if (c.weight !== null && d.weight !== null && Math.abs(d.weight - c.weight) > 1e-9) return true;
  return c.parameters.some((p) => Math.abs((d.parameters[p.name] ?? p.value) - p.value) > 1e-9);
}

function compareIds(a: string, b: string): number {
  const ka = a.split(".").map(Number);
  const kb = b.split(".").map(Number);
  for (let i = 0; i < Math.max(ka.length, kb.length); i++) {
    const d = (ka[i] ?? -1) - (kb[i] ?? -1);
    if (d) return d;
  }
  return 0;
}

export default function QualitySettingsPage() {
  const { data, mutate } = useSWR<GridCalibration>("/quality/grid", () => api.get<GridCalibration>("/quality/grid"), {
    refreshInterval: (latest) => (latest?.running ? 15_000 : 0),
  });
  const [draft, setDraft] = useState<Draft>({});
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (data) setDraft(draftFrom(data.criteria));
  }, [data]);

  const criteria = useMemo(() => data?.criteria ?? [], [data]);
  const dirty = criteria.filter((c) => draft[c.id] && differsFromSaved(c, draft[c.id]));

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return criteria.filter((c) => {
      if (q && !c.id.startsWith(q) && !c.label.toLowerCase().includes(q)) return false;
      if (filter === "automated") return c.automated;
      if (filter === "comparable") return c.comparable;
      if (filter === "modified") return draft[c.id] && differsFromDefault(c, draft[c.id]);
      return true;
    });
  }, [criteria, query, filter, draft]);

  const groups = useMemo(() => {
    const out = new Map<string, Map<string, GridCriterion[]>>();
    for (const c of visible) {
      const cat = out.get(c.category) ?? new Map<string, GridCriterion[]>();
      cat.set(c.subcategory, [...(cat.get(c.subcategory) ?? []), c]);
      out.set(c.category, cat);
    }
    return out;
  }, [visible]);

  function setWeight(id: string, value: number | null) {
    setDraft((d) => ({ ...d, [id]: { ...d[id], weight: value } }));
    setMessage(null);
  }

  function setParameter(id: string, name: string, value: number) {
    setDraft((d) => ({ ...d, [id]: { ...d[id], parameters: { ...d[id].parameters, [name]: value } } }));
    setMessage(null);
  }

  async function handleSave() {
    if (!data) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      // Full replacement: send every criterion that differs from the default grid.
      const overrides = Object.fromEntries(
        data.criteria
          .filter((c) => differsFromDefault(c, draft[c.id]))
          .map((c) => [c.id, { weight: draft[c.id].weight, parameters: draft[c.id].parameters }]),
      );
      const updated = await api.put<GridCalibration>("/quality/grid", { overrides });
      await mutate({ ...updated, running: true }, { revalidate: false });
      setMessage(t("qualitySettings.saved"));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("qualitySettings.saveError"));
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!data || !confirm(t("qualitySettings.resetConfirm", { file: data.default_grid_file }))) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.delete<GridCalibration>("/quality/grid");
      await mutate({ ...updated, running: true }, { revalidate: false });
      setMessage(t("qualitySettings.saved"));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("qualitySettings.saveError"));
    } finally {
      setSaving(false);
    }
  }

  const FILTERS: { key: Filter; label: string }[] = [
    { key: "all", label: t("qualitySettings.filterAll") },
    { key: "automated", label: t("qualitySettings.filterAutomated") },
    { key: "comparable", label: t("qualitySettings.filterComparable") },
    { key: "modified", label: t("qualitySettings.filterModified") },
  ];

  return (
    <div className="max-w-5xl">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">{t("qualitySettings.title")}</h1>
        <p className="text-sm text-gray-500 mt-1">{t("qualitySettings.intro")}</p>
        <p className="text-xs text-gray-400 mt-2">{t("qualitySettings.roleHelp")}</p>
        {data && (
          <p className="text-xs text-gray-500 mt-2">
            {data.has_overrides && data.updated_at
              ? t("qualitySettings.statusModified", {
                  date: new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" }).format(
                    new Date(data.updated_at),
                  ),
                })
              : t("qualitySettings.statusDefault", { file: data.default_grid_file })}
          </p>
        )}
      </div>

      <div className="sticky top-0 z-10 bg-gray-50 py-3 mb-4 border-b space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[240px]">
            <Search size={14} className="absolute left-2.5 top-2.5 text-gray-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t("qualitySettings.searchPlaceholder")}
              className="w-full border rounded pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div className="flex text-xs border rounded-md overflow-hidden bg-white">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`px-2.5 py-1.5 ${filter === f.key ? "bg-brand-600 text-white" : "text-gray-600 hover:bg-gray-50"}`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saving || dirty.length === 0 || data?.running}
            className="px-4 py-1.5 bg-brand-600 text-white text-sm rounded disabled:opacity-50"
          >
            {saving ? t("qualitySettings.saving") : t("qualitySettings.save", { n: dirty.length })}
          </button>
          <button
            onClick={() => data && setDraft(draftFrom(data.criteria))}
            disabled={saving || dirty.length === 0}
            className="px-3 py-1.5 text-sm border rounded text-gray-600 hover:bg-white disabled:opacity-50"
          >
            {t("qualitySettings.discard")}
          </button>
          <button
            onClick={handleReset}
            disabled={saving || !data?.has_overrides || data?.running}
            className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-red-600 disabled:opacity-40"
          >
            <RotateCcw size={13} /> {t("qualitySettings.reset")}
          </button>
        </div>
        {data?.running && <p className="text-xs text-amber-700">{t("qualitySettings.running")}</p>}
        {error && <p className="text-xs text-red-600">{error}</p>}
        {message && (
          <p className="text-xs text-green-700 flex items-center gap-1">
            <CheckCircle size={13} /> {message}
          </p>
        )}
      </div>

      {!data && <p className="text-sm text-gray-500">{t("common.loading")}</p>}
      {data && visible.length === 0 && <p className="text-sm text-gray-500">{t("qualitySettings.noResult")}</p>}
      {data && visible.length > 0 && (
        <p className="text-xs text-gray-400 mb-2">{t("qualitySettings.criteriaShown", { n: visible.length })}</p>
      )}

      <div className="space-y-3">
        {[...groups.entries()].map(([category, subs]) => (
          <details key={category} open className="group bg-white border rounded-lg">
            <summary className="flex items-center gap-2 px-4 py-2.5 cursor-pointer select-none text-sm font-semibold text-gray-800">
              <ChevronRight size={14} className="transition-transform group-open:rotate-90 text-gray-400" />
              {category}
            </summary>
            <div className="divide-y">
              {[...subs.entries()].map(([sub, rows]) => (
                <div key={sub} className="px-4 py-2">
                  <h3 className="text-xs font-semibold text-gray-500 mb-1">{sub}</h3>
                  <ul className="divide-y">
                    {[...rows].sort((a, b) => compareIds(a.id, b.id)).map((c) => (
                      <CriterionRow
                        key={c.id}
                        criterion={c}
                        draft={draft[c.id]}
                        disabled={!!data?.running}
                        onWeight={(v) => setWeight(c.id, v)}
                        onParameter={(name, v) => setParameter(c.id, name, v)}
                      />
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function NumberField({
  value,
  defaultValue,
  disabled,
  onChange,
  step,
  suffix,
}: {
  value: number | null;
  defaultValue: number | null;
  disabled: boolean;
  onChange: (v: number) => void;
  step: number;
  suffix?: string;
}) {
  const changed = value !== null && defaultValue !== null && Math.abs(value - defaultValue) > 1e-9;
  return (
    <span className="inline-flex flex-col items-end">
      <span className="inline-flex items-center gap-1">
        <input
          type="number"
          min={0}
          step={step}
          value={value ?? ""}
          disabled={disabled}
          onChange={(e) => e.target.value !== "" && onChange(Number(e.target.value))}
          className={`w-20 border rounded px-2 py-1 text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-500 ${
            changed ? "border-brand-400 bg-brand-50" : ""
          }`}
        />
        {suffix && <span className="text-xs text-gray-400">{suffix}</span>}
      </span>
      {changed && defaultValue !== null && (
        <button
          type="button"
          onClick={() => onChange(defaultValue)}
          disabled={disabled}
          className="text-[11px] text-gray-400 hover:text-brand-600"
        >
          {t("qualitySettings.defaultValue", { value: defaultValue.toLocaleString("fr-FR") })}
        </button>
      )}
    </span>
  );
}

function CriterionRow({
  criterion: c,
  draft,
  disabled,
  onWeight,
  onParameter,
}: {
  criterion: GridCriterion;
  draft: Draft[string] | undefined;
  disabled: boolean;
  onWeight: (v: number) => void;
  onParameter: (name: string, v: number) => void;
}) {
  const roleLabel =
    c.role === "coefficient"
      ? t("qualitySettings.roleCoefficient")
      : c.role === "points"
        ? t("qualitySettings.rolePoints")
        : c.role === "modulateur"
          ? t("qualitySettings.roleModulator", { target: c.modulates ?? "?" })
          : t("qualitySettings.roleNone");

  return (
    <li className="py-2 flex items-start gap-3">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800">
          <span className="text-xs text-gray-400 tabular-nums mr-1.5">{c.id}</span>
          {c.label}
        </p>
        <div className="flex items-center gap-1.5 mt-1">
          {c.automated && (
            <span
              title={t("qualitySettings.badgeAutomatedTooltip")}
              className="text-[11px] px-1.5 py-0.5 rounded border bg-blue-50 text-blue-700 border-blue-200"
            >
              {t("qualitySettings.badgeAutomated")}
            </span>
          )}
          {c.comparable && (
            <span
              title={t("qualitySettings.badgeComparableTooltip")}
              className="text-[11px] px-1.5 py-0.5 rounded border bg-emerald-50 text-emerald-700 border-emerald-200"
            >
              {t("qualitySettings.badgeComparable")}
            </span>
          )}
          {c.parameters.length > 0 && (
            <span className="flex items-center gap-2 ml-1">
              {c.parameters.map((p) => (
                <span key={p.name} className="flex items-center gap-1 text-xs text-gray-500">
                  {p.name} =
                  <NumberField
                    value={draft?.parameters[p.name] ?? p.value}
                    defaultValue={p.default}
                    disabled={disabled}
                    step={1}
                    suffix={p.unit}
                    onChange={(v) => onParameter(p.name, v)}
                  />
                </span>
              ))}
            </span>
          )}
        </div>
      </div>
      <div className="shrink-0 flex items-start gap-2 pt-0.5">
        <span className="text-xs text-gray-400 pt-1.5 whitespace-nowrap">{roleLabel}</span>
        {c.weight !== null && (
          <NumberField
            value={draft?.weight ?? c.weight}
            defaultValue={c.default_weight}
            disabled={disabled}
            step={c.role === "points" ? 0.5 : 0.05}
            onChange={onWeight}
          />
        )}
        {c.weight === null && <InfoTooltip text={t("qualitySettings.roleHelp")} />}
      </div>
    </li>
  );
}
