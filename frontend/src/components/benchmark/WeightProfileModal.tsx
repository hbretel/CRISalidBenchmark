"use client";

import { useEffect, useReducer, useState } from "react";
import { ChevronDown, ChevronRight, Lock, Unlock } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { DEFAULT_AXIS_WEIGHTS, DEFAULT_SUB_WEIGHTS } from "@/lib/constants";
import type { WeightProfileResponse } from "@/types/api";
import { Modal } from "@/components/ui/Modal";
import { t } from "@/lib/i18n";

interface WeightState {
  axis: Record<string, number>;
  sub: Record<string, Record<string, number>>;
  axisLocked: Record<string, boolean>;
  subLocked: Record<string, Record<string, boolean>>;
}

type Action =
  | { type: "SET_AXIS"; axis: string; value: number }
  | { type: "SET_SUB"; axis: string; indicator: string; value: number }
  | { type: "TOGGLE_AXIS_LOCK"; axis: string }
  | { type: "TOGGLE_SUB_LOCK"; axis: string; indicator: string }
  | { type: "LOAD"; axis: Record<string, number>; sub: Record<string, Record<string, number>> };

function defaultSubWeights(): Record<string, Record<string, number>> {
  return Object.fromEntries(Object.entries(DEFAULT_SUB_WEIGHTS).map(([axis, sub]) => [axis, { ...sub }]));
}

function defaultWeights(): WeightState {
  return {
    axis: { ...DEFAULT_AXIS_WEIGHTS },
    sub: defaultSubWeights(),
    axisLocked: {},
    subLocked: {},
  };
}

/**
 * Redistribute weight after a slider change, respecting locked keys — see
 * ponderation page history: without this, changing any one of 3+ weights
 * always perturbs every other one, making it impossible to pin a weight the
 * user already dialed in while adjusting the rest.
 */
function redistributeWithLocks(
  weights: Record<string, number>,
  locked: Record<string, boolean>,
  changedKey: string,
  requestedValue: number,
): Record<string, number> {
  const keys = Object.keys(weights);
  const lockedOthers = keys.filter((k) => k !== changedKey && locked[k]);
  const unlockedOthers = keys.filter((k) => k !== changedKey && !locked[k]);

  const sumLocked = lockedOthers.reduce((s, k) => s + weights[k], 0);
  const available = Math.max(0, 1 - sumLocked);

  const changedValue = Math.min(Math.max(requestedValue, 0), available);
  const result: Record<string, number> = { ...weights, [changedKey]: changedValue };

  if (unlockedOthers.length === 0) {
    result[changedKey] = available;
    return result;
  }

  const remaining = available - changedValue;
  const othersTotal = unlockedOthers.reduce((s, k) => s + weights[k], 0);
  if (othersTotal > 0) {
    for (const k of unlockedOthers) {
      result[k] = (weights[k] / othersTotal) * remaining;
    }
  } else {
    const share = remaining / unlockedOthers.length;
    for (const k of unlockedOthers) result[k] = share;
  }
  return result;
}

function reducer(state: WeightState, action: Action): WeightState {
  switch (action.type) {
    case "SET_AXIS":
      return { ...state, axis: redistributeWithLocks(state.axis, state.axisLocked, action.axis, action.value) };
    case "SET_SUB": {
      const locked = state.subLocked[action.axis] ?? {};
      const sub = redistributeWithLocks(state.sub[action.axis], locked, action.indicator, action.value);
      return { ...state, sub: { ...state.sub, [action.axis]: sub } };
    }
    case "TOGGLE_AXIS_LOCK":
      return { ...state, axisLocked: { ...state.axisLocked, [action.axis]: !state.axisLocked[action.axis] } };
    case "TOGGLE_SUB_LOCK": {
      const current = state.subLocked[action.axis] ?? {};
      return {
        ...state,
        subLocked: { ...state.subLocked, [action.axis]: { ...current, [action.indicator]: !current[action.indicator] } },
      };
    }
    case "LOAD":
      return { axis: action.axis, sub: action.sub, axisLocked: {}, subLocked: {} };
    default:
      return state;
  }
}

function pct(v: number) {
  return Math.round(v * 100);
}

function LockButton({ locked, onClick, title }: { locked: boolean; onClick: () => void; title: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`p-1 rounded ${locked ? "text-brand-600 bg-brand-50" : "text-gray-300 hover:text-gray-500"}`}
    >
      {locked ? <Lock size={13} /> : <Unlock size={13} />}
    </button>
  );
}

function nextDefaultName(existing: WeightProfileResponse[]): string {
  let n = 1;
  const names = new Set(existing.map((p) => p.name));
  while (names.has(t("weightProfileModal.defaultProfileName", { n }))) n++;
  return t("weightProfileModal.defaultProfileName", { n });
}

interface Props {
  open: boolean;
  onClose: () => void;
  editingProfile: WeightProfileResponse | null;
  existingProfiles: WeightProfileResponse[];
  onSaved: (profile: WeightProfileResponse) => void;
}

export function WeightProfileModal({ open, onClose, editingProfile, existingProfiles, onSaved }: Props) {
  const [weights, dispatch] = useReducer(reducer, undefined, defaultWeights);
  const [name, setName] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (editingProfile) {
      dispatch({ type: "LOAD", axis: editingProfile.axis_weights, sub: editingProfile.sub_indicator_weights });
      setName(editingProfile.name);
    } else {
      dispatch({ type: "LOAD", axis: { ...DEFAULT_AXIS_WEIGHTS }, sub: defaultSubWeights() });
      setName(nextDefaultName(existingProfiles));
    }
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, editingProfile]);

  async function handleSave() {
    if (!name.trim()) {
      setError(t("weightProfileModal.nameEmptyError"));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body = { name: name.trim(), axis_weights: weights.axis, sub_indicator_weights: weights.sub };
      const profile = editingProfile
        ? await api.put<WeightProfileResponse>(`/weight-profiles/${editingProfile.id}`, body)
        : await api.post<WeightProfileResponse>("/weight-profiles", body);
      onSaved(profile);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("weightProfileModal.saveError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={editingProfile ? t("weightProfileModal.editTitle") : t("weightProfileModal.newTitle")}>
      <div className="space-y-5">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">{t("weightProfileModal.nameLabel")}</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {Object.entries(weights.axis).map(([axis, value]) => (
          <div key={axis} className="border rounded-lg p-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium text-gray-700 flex items-center gap-1.5">
                <LockButton
                  locked={!!weights.axisLocked[axis]}
                  onClick={() => dispatch({ type: "TOGGLE_AXIS_LOCK", axis })}
                  title={weights.axisLocked[axis] ? t("weightProfileModal.unlock") : t("weightProfileModal.lock")}
                />
                {t(`axis.${axis}`)}
              </span>
              <span className="text-brand-700 font-bold">{pct(value)} %</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={pct(value)}
              disabled={weights.axisLocked[axis]}
              onChange={(e) => dispatch({ type: "SET_AXIS", axis, value: Number(e.target.value) / 100 })}
              className="w-full accent-brand-600 disabled:opacity-40"
            />

            <button
              type="button"
              onClick={() => setExpanded((v) => ({ ...v, [axis]: !v[axis] }))}
              className="mt-3 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
            >
              {expanded[axis] ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              {t("weightProfileModal.advancedIndicators")}
            </button>

            {expanded[axis] && (
              <div className="mt-3 pl-2 border-l-2 border-gray-100 space-y-3">
                {Object.entries(weights.sub[axis] ?? {}).map(([indicator, subValue]) => (
                  <div key={indicator}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-600 flex items-center gap-1.5">
                        <LockButton
                          locked={!!weights.subLocked[axis]?.[indicator]}
                          onClick={() => dispatch({ type: "TOGGLE_SUB_LOCK", axis, indicator })}
                          title={weights.subLocked[axis]?.[indicator] ? t("weightProfileModal.unlock") : t("weightProfileModal.lock")}
                        />
                        {t(`indicator.${indicator}`)}
                      </span>
                      <span className="text-brand-700 font-semibold">{pct(subValue)} %</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={pct(subValue)}
                      disabled={weights.subLocked[axis]?.[indicator]}
                      onChange={(e) =>
                        dispatch({ type: "SET_SUB", axis, indicator, value: Number(e.target.value) / 100 })
                      }
                      className="w-full accent-brand-600 disabled:opacity-40"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      {t(`indicatorDescription.${indicator}`)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {error && <p className="text-xs text-red-600">{error}</p>}

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
            disabled={saving}
            className="flex-1 py-2 px-4 bg-brand-600 text-white rounded text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? t("common.saving") : t("weightProfileModal.saveButton")}
          </button>
        </div>
      </div>
    </Modal>
  );
}
