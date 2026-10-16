import useSWR from "swr";
import { api } from "@/lib/api";
import type { PeerGroupSummary, PeerMemberInfo, PeerComparisonTable } from "@/types/api";

export function usePeerGroups() {
  return useSWR<PeerGroupSummary[]>(
    "/peer-groups",
    () => api.get<PeerGroupSummary[]>("/peer-groups"),
  );
}

/**
 * Pick the sensible default peer group: the geographic one (same country as
 * the configured institution) when available, since "compare me to my
 * country's institutions" is the most broadly meaningful comparison without
 * any user action. Falls back to the first group otherwise (e.g. only
 * size-bracket or custom groups exist).
 *
 * Without this, pages previously defaulted to `groups[0]`, which — since the
 * API orders groups by `type, name` — actually put "custom" ahead of
 * "geographic" alphabetically, so any custom group silently became the
 * default the moment one existed. Not what "default to my country" means.
 */
export function getDefaultPeerGroupId(groups: PeerGroupSummary[] | undefined): number | null {
  if (!groups || groups.length === 0) return null;
  const geographic = groups.find((g) => g.type === "geographic");
  return (geographic ?? groups[0]).id;
}

export function usePeerGroupMembers(groupId: number | null) {
  return useSWR<PeerMemberInfo[]>(
    groupId ? `/peer-groups/${groupId}/members` : null,
    () => api.get<PeerMemberInfo[]>(`/peer-groups/${groupId}/members`),
  );
}

export function usePeerComparisonTable(
  groupId: number | null,
  weightProfileId: number | null,
  coreOnly: boolean,
  field: string,
) {
  const url =
    groupId && weightProfileId
      ? `/peer-groups/${groupId}/comparison-table?weight_profile_id=${weightProfileId}&core_only=${coreOnly}&field=${encodeURIComponent(field)}`
      : null;
  return useSWR<PeerComparisonTable>(url, (u: string) => api.get<PeerComparisonTable>(u));
}
