"use client";

import { useEffect, useState } from "react";

/**
 * Persists the "current" peer group / weight profile choice across the whole
 * app (sticky dashboard header + Paramètres du benchmark page) via
 * localStorage — there's no server-side notion of a logged-in user's current
 * selection in this single-tenant app, so the browser is the source of truth.
 *
 * Falls back to `fallback` (the computed default: geographic group / the
 * "Équilibré" profile) whenever nothing is stored yet, or the stored id no
 * longer resolves to a real item (e.g. a custom group/profile was deleted).
 */
function usePersistedSelection(
  storageKey: string,
  fallback: number | null,
  validIds: number[] | undefined,
): [number | null, (id: number) => void] {
  const [stored, setStored] = useState<number | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem(storageKey);
    setStored(raw ? Number(raw) : null);
    setHydrated(true);
  }, [storageKey]);

  function set(id: number) {
    setStored(id);
    window.localStorage.setItem(storageKey, String(id));
  }

  if (!hydrated) return [null, set];

  const isValid = stored !== null && (!validIds || validIds.includes(stored));
  return [isValid ? stored : fallback, set];
}

export function useCurrentPeerGroupId(
  defaultId: number | null,
  validIds: number[] | undefined,
): [number | null, (id: number) => void] {
  return usePersistedSelection("crisalid.currentPeerGroupId", defaultId, validIds);
}

export function useCurrentWeightProfileId(
  defaultId: number | null,
  validIds: number[] | undefined,
): [number | null, (id: number) => void] {
  return usePersistedSelection("crisalid.currentWeightProfileId", defaultId, validIds);
}

export function useCurrentLeidenDomain(): [string, (field: string) => void] {
  const [value, setValue] = useState("All sciences");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem("crisalid.currentLeidenDomain");
    if (raw) setValue(raw);
    setHydrated(true);
  }, []);

  function set(field: string) {
    setValue(field);
    window.localStorage.setItem("crisalid.currentLeidenDomain", field);
  }

  return [hydrated ? value : "All sciences", set];
}

export function useCoreOnly(): [boolean, (v: boolean) => void] {
  const [value, setValue] = useState(true);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem("crisalid.coreOnly");
    if (raw !== null) setValue(raw === "true");
    setHydrated(true);
  }, []);

  function set(v: boolean) {
    setValue(v);
    window.localStorage.setItem("crisalid.coreOnly", String(v));
  }

  return [hydrated ? value : true, set];
}

function usePersistedString<T extends string>(storageKey: string, fallback: T, valid: readonly T[]): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(fallback);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem(storageKey);
    if (raw && (valid as readonly string[]).includes(raw)) setValue(raw as T);
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey]);

  function set(v: T) {
    setValue(v);
    window.localStorage.setItem(storageKey, v);
  }

  return [hydrated ? value : fallback, set];
}

export type DashboardTab = "world" | "groups";

/** Active dashboard tab: "Monde entier" (Leiden) or "Groupes de comparaison" (OpenAlex). */
export function useDashboardTab(): [DashboardTab, (tab: DashboardTab) => void] {
  return usePersistedString<DashboardTab>("crisalid.dashboardTab", "groups", ["world", "groups"]);
}

/** OpenAlex domain of the "Groupes de comparaison" tab ("all" or a domain id). */
export function useCurrentOpenAlexDomain(): [string, (domain: string) => void] {
  return usePersistedString("crisalid.currentOpenAlexDomain", "all", ["all", "1", "2", "3", "4"]);
}
