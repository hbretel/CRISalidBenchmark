"use client";

import { useEffect, useState } from "react";
import { useConfig } from "@/hooks/useConfig";
import { api, ApiError } from "@/lib/api";
import type { ConfigResponse } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { QualityJobPanel } from "@/components/setup/QualityJobPanel";
import { AlertTriangle, Building2, CheckCircle, KeyRound, Mail } from "lucide-react";
import { t } from "@/lib/i18n";

/**
 * Post-setup configuration management — reachable via the "Configuration"
 * sidebar link once the instance is configured (the /setup wizard is only
 * ever shown once, for the very first configuration). Each of the three
 * settings (institution, API key, contact email) is changed independently,
 * matching how they're actually decoupled server-side (PATCH /config).
 */
export default function ConfigurationPage() {
  const { config, mutate } = useConfig();

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-xl font-bold text-gray-900">{t("configuration.title")}</h1>
        <p className="text-sm text-gray-500 mt-1">{t("configuration.subtitle")}</p>
      </div>

      {config && (
        <>
          <InstitutionSection config={config} onSaved={mutate} />
          <ApiKeySection onSaved={mutate} />
          <EmailSection config={config} onSaved={mutate} />
          <QualityJobPanel />
        </>
      )}
    </div>
  );
}

function InstitutionSection({ config, onSaved }: { config: ConfigResponse; onSaved: () => void }) {
  const [institutionId, setInstitutionId] = useState(config.openalex_institution_id);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setInstitutionId(config.openalex_institution_id);
  }, [config.openalex_institution_id]);

  const changed = institutionId.trim() !== config.openalex_institution_id;

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.patch<ConfigResponse>("/config", { openalex_institution_id: institutionId.trim() });
      setSaved(true);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("configuration.genericError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white border rounded-lg p-5 mb-4">
      <div className="flex items-center gap-2 mb-1">
        <Building2 size={16} className="text-brand-600" />
        <h2 className="text-sm font-semibold text-gray-700">{t("configuration.institutionTitle")}</h2>
      </div>
      <p className="text-xs text-gray-500 mb-3 flex items-center gap-1">
        {config.institution_name} · ROR {config.ror_id ?? t("common.dash")} ·{" "}
        {config.openalex_lineage_ids.length} {t("configuration.lineageCount")}
        <InfoTooltip text={t("configuration.lineageCountTooltip")} />
      </p>

      <label className="block text-xs font-medium text-gray-600 mb-1">{t("configuration.institutionIdLabel")}</label>
      <div className="flex gap-2">
        <input
          type="text"
          value={institutionId}
          onChange={(e) => { setInstitutionId(e.target.value); setSaved(false); }}
          className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          onClick={handleSave}
          disabled={saving || !changed || !institutionId.trim()}
          className="px-4 py-2 bg-brand-600 text-white text-sm rounded disabled:opacity-50"
        >
          {saving ? t("configuration.changing") : t("configuration.change")}
        </button>
      </div>

      {changed && (
        <div className="mt-2 flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
          <AlertTriangle size={13} className="mt-0.5 shrink-0" />
          <span>{t("configuration.changeWarning")}</span>
        </div>
      )}

      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      {saved && (
        <p className="text-xs text-green-700 mt-2 flex items-center gap-1">
          <CheckCircle size={13} /> {t("configuration.institutionUpdated")}
        </p>
      )}
    </section>
  );
}

function ApiKeySection({ onSaved }: { onSaved: () => void }) {
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    if (!apiKey) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.patch<ConfigResponse>("/config", { openalex_api_key: apiKey });
      setApiKey("");
      setSaved(true);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("configuration.genericError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white border rounded-lg p-5 mb-4">
      <div className="flex items-center gap-2 mb-1">
        <KeyRound size={16} className="text-brand-600" />
        <h2 className="text-sm font-semibold text-gray-700">{t("configuration.apiKeyTitle")}</h2>
        <InfoTooltip text={t("configuration.apiKeyTooltip")} />
      </div>
      <p className="text-xs text-gray-500 mb-3">{t("configuration.apiKeyCurrent")}</p>

      <label className="block text-xs font-medium text-gray-600 mb-1">{t("configuration.apiKeyLabel")}</label>
      <div className="flex gap-2">
        <input
          type="password"
          value={apiKey}
          onChange={(e) => { setApiKey(e.target.value); setSaved(false); }}
          placeholder={t("configuration.apiKeyPlaceholder")}
          autoComplete="off"
          className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          onClick={handleSave}
          disabled={saving || !apiKey}
          className="px-4 py-2 bg-brand-600 text-white text-sm rounded disabled:opacity-50"
        >
          {saving ? t("configuration.changing") : t("configuration.change")}
        </button>
      </div>

      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      {saved && (
        <p className="text-xs text-green-700 mt-2 flex items-center gap-1">
          <CheckCircle size={13} /> {t("configuration.apiKeyUpdated")}
        </p>
      )}
    </section>
  );
}

function EmailSection({ config, onSaved }: { config: ConfigResponse; onSaved: () => void }) {
  const [email, setEmail] = useState(config.contact_email);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => setEmail(config.contact_email), [config.contact_email]);
  const changed = email.trim() !== config.contact_email;

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.patch<ConfigResponse>("/config", { contact_email: email.trim() });
      setSaved(true);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("configuration.genericError"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white border rounded-lg p-5">
      <div className="flex items-center gap-2 mb-3">
        <Mail size={16} className="text-brand-600" />
        <h2 className="text-sm font-semibold text-gray-700">{t("configuration.emailTitle")}</h2>
      </div>

      <label className="block text-xs font-medium text-gray-600 mb-1">{t("configuration.emailLabel")}</label>
      <div className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => { setEmail(e.target.value); setSaved(false); }}
          className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button
          onClick={handleSave}
          disabled={saving || !changed || !email.trim()}
          className="px-4 py-2 bg-brand-600 text-white text-sm rounded disabled:opacity-50"
        >
          {saving ? t("configuration.changing") : t("configuration.change")}
        </button>
      </div>

      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      {saved && (
        <p className="text-xs text-green-700 mt-2 flex items-center gap-1">
          <CheckCircle size={13} /> {t("configuration.emailUpdated")}
        </p>
      )}
    </section>
  );
}
