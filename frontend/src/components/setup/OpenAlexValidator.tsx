"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ValidateResponse } from "@/types/api";
import { CheckCircle, Loader2, AlertCircle } from "lucide-react";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { t } from "@/lib/i18n";

interface Props {
  onValidated: (data: ValidateResponse, apiKey: string, email: string) => void;
}

export function OpenAlexValidator({ onValidated }: Props) {
  const [openalexId, setOpenalexId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleValidate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Normalise ID: strip full URL if user pasted https://openalex.org/I...
    const id = openalexId.trim().replace(/^https?:\/\/openalex\.org\//, "");

    try {
      const data = await api.get<ValidateResponse>(
        `/config/validate?openalex_id=${encodeURIComponent(id)}&api_key=${encodeURIComponent(apiKey)}&contact_email=${encodeURIComponent(email)}`,
      );
      onValidated(data, apiKey, email);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("openAlexValidator.genericError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleValidate} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("openAlexValidator.idLabel")}{" "}
          <InfoTooltip text={t("openAlexValidator.idTooltip")} />
        </label>
        <input
          type="text"
          value={openalexId}
          onChange={(e) => setOpenalexId(e.target.value)}
          placeholder={t("openAlexValidator.idPlaceholder")}
          className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("openAlexValidator.apiKeyLabel")}{" "}
          <InfoTooltip text={t("openAlexValidator.apiKeyTooltip")} />
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder={t("openAlexValidator.apiKeyPlaceholder")}
          className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          required
          autoComplete="off"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("openAlexValidator.emailLabel")}{" "}
          <InfoTooltip text={t("openAlexValidator.emailTooltip")} />
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("openAlexValidator.emailPlaceholder")}
          className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          required
        />
      </div>

      {error && (
        <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 p-3 rounded">
          <AlertCircle size={15} className="mt-0.5 shrink-0" />
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || !openalexId || !apiKey || !email}
        className="w-full py-2 px-4 bg-brand-600 text-white rounded text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading && <Loader2 size={15} className="animate-spin" />}
        {t("openAlexValidator.submit")}
      </button>
    </form>
  );
}
