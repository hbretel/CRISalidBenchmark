import useSWR from "swr";
import { api } from "@/lib/api";
import type { WeightProfileResponse } from "@/types/api";

export function useWeightProfiles() {
  return useSWR<WeightProfileResponse[]>(
    "/weight-profiles",
    () => api.get<WeightProfileResponse[]>("/weight-profiles"),
  );
}

/** The seeded "Équilibré" profile — always present, never deletable/editable. */
export function getDefaultWeightProfile(
  profiles: WeightProfileResponse[] | undefined,
): WeightProfileResponse | undefined {
  return profiles?.find((p) => p.is_default);
}

export function getDefaultWeightProfileId(
  profiles: WeightProfileResponse[] | undefined,
): number | null {
  if (!profiles || profiles.length === 0) return null;
  return (getDefaultWeightProfile(profiles) ?? profiles[0]).id;
}
