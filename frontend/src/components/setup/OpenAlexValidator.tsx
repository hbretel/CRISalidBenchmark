"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { ValidateResponse } from "@/types/api";
import { CheckCircle, Loader2, AlertCircle } from "lucide-react";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

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
      setError(
        err instanceof ApiError
          ? err.detail
          : "Erreur de connexion à l'API OpenAlex. Vérifiez l'ID et la clé API.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleValidate} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          ID OpenAlex de l'établissement{" "}
          <InfoTooltip text="L'identifiant OpenAlex commence par 'I' suivi de chiffres (ex. I4210140050). Vous pouvez coller l'URL complète (https://openalex.org/I...) — elle sera normalisée automatiquement. Trouvez votre établissement sur openalex.org." />
        </label>
        <input
          type="text"
          value={openalexId}
          onChange={(e) => setOpenalexId(e.target.value)}
          placeholder="I4210140050 ou https://openalex.org/I..."
          className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Clé API OpenAlex{" "}
          <InfoTooltip text="Depuis début 2026, OpenAlex requiert une clé API pour les usages en production. Obtenez-la gratuitement via votre compte sur openalex.org (paramètres du compte). La clé est stockée en base de données et ne sera plus affichée après validation." />
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Votre clé API OpenAlex"
          className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          required
          autoComplete="off"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Email de contact technique{" "}
          <InfoTooltip text="Utilisé comme paramètre mailto= dans les appels OpenAlex, en complément de la clé API. Recommandé par OpenAlex pour une meilleure identification des flux." />
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="contact@votre-etablissement.fr"
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
        Valider et continuer
      </button>
    </form>
  );
}
