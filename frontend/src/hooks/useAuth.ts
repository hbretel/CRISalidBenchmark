import useSWR from "swr";
import { api, ApiError } from "@/lib/api";

interface MeResponse {
  username: string;
}

export function useAuth() {
  const { data, error, isLoading, mutate } = useSWR<MeResponse>(
    "/auth/me",
    () => api.get<MeResponse>("/auth/me"),
    {
      // Don't retry on 401 (not logged in) — the login page / AuthGate handle that.
      shouldRetryOnError: (err) => !(err instanceof ApiError && err.status === 401),
      revalidateOnFocus: false,
    },
  );

  return {
    username: data?.username ?? null,
    isAuthenticated: !!data,
    isLoading,
    error,
    mutate,
  };
}
