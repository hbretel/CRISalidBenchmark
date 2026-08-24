import useSWR from "swr";
import { api } from "@/lib/api";
import type { SyncJob } from "@/types/api";

export function useSyncStatus() {
  const { data, error, isLoading } = useSWR<{ recent_jobs: SyncJob[] }>(
    "/admin/sync/status",
    () => api.get<{ recent_jobs: SyncJob[] }>("/admin/sync/status"),
    { refreshInterval: 30_000 }, // poll every 30s
  );

  const lastOpenAlex = data?.recent_jobs.find(
    (j) => j.job_name === "openalex_nightly" && j.status === "success",
  );
  const lastLeiden = data?.recent_jobs.find(
    (j) => j.job_name === "leiden_annual" && j.status === "success",
  );

  return {
    jobs: data?.recent_jobs ?? [],
    lastOpenAlexSync: lastOpenAlex?.finished_at ?? null,
    lastLeidenSync: lastLeiden?.finished_at ?? null,
    isLoading,
    error,
  };
}
