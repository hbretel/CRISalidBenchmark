"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

/**
 * UX-layer gating only — mirrors how /setup redirects client-side based on
 * useConfig().isConfigured. Real enforcement is the backend 401 (via
 * AuthGuardMiddleware) on every non-exempt API route; this just avoids
 * flashing dashboard content before the redirect to /login happens.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const isLoginPage = pathname === "/login";

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isLoginPage) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, isLoginPage, router]);

  if (isLoginPage) return <>{children}</>;
  if (isLoading || !isAuthenticated) return null;
  return <>{children}</>;
}
