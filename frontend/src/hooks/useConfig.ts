import useSWR from "swr";
import { api, ApiError } from "@/lib/api";
import type { ConfigResponse } from "@/types/api";

export function useConfig() {
  const { data, error, isLoading, mutate } = useSWR<ConfigResponse>(
    "/config",
    () => api.get<ConfigResponse>("/config"),
    {
      // Don't retry on 404 (not configured yet) — the setup page handles that
      shouldRetryOnError: (err) => !(err instanceof ApiError && err.status === 404),
      revalidateOnFocus: false,
    },
  );

  return {
    config: data,
    isConfigured: !!data && data.api_key_set,
    isLoading,
    error,
    mutate,
  };
}
