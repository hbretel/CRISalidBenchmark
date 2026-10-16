"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn, Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { t } from "@/lib/i18n";

export default function LoginPage() {
  const router = useRouter();
  const { mutate } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/auth/login", { username, password });
      await mutate();
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("login.genericError"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-16">
      <div className="mb-6 text-center">
        <h1 className="text-xl font-bold text-gray-900">{t("login.appName")}</h1>
        <p className="text-sm text-gray-500 mt-1">{t("login.title")}</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border rounded-lg p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">{t("login.usernameLabel")}</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">{t("login.passwordLabel")}</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {error && <p className="text-xs text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting || !username || !password}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm rounded disabled:opacity-50"
        >
          {submitting ? <Loader2 size={14} className="animate-spin" /> : <LogIn size={14} />}
          {t("login.submit")}
        </button>
      </form>
    </div>
  );
}
