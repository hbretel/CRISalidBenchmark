"use client";

import { useState } from "react";
import { UploadCloud } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { t } from "@/lib/i18n";

export function LeidenImportPanel({ onImportStarted }: { onImportStarted: () => void }) {
  const currentYear = new Date().getFullYear();
  const [snapshotYear, setSnapshotYear] = useState(String(currentYear));
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("snapshot_year", snapshotYear);
      formData.append("file", file);
      const res = await api.postForm<{ message: string }>("/admin/sync/leiden", formData);
      setMessage(res.message);
      onImportStarted();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("leidenImport.error"));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mb-6 border border-amber-200 bg-amber-50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <UploadCloud size={16} className="text-amber-700" />
        <h2 className="text-sm font-semibold text-amber-800">{t("leidenImport.title")}</h2>
        <InfoTooltip text={t("leidenImport.tooltip")} />
      </div>
      <p className="text-xs text-amber-700 mb-3">{t("leidenImport.body")}</p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="number"
          value={snapshotYear}
          onChange={(e) => setSnapshotYear(e.target.value)}
          className="w-24 border rounded px-2 py-1.5 text-sm"
          placeholder={t("leidenImport.yearPlaceholder")}
        />
        <input
          type="file"
          accept=".xlsx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm flex-1 min-w-[200px]"
        />
        <button
          onClick={handleUpload}
          disabled={uploading || !file}
          className="px-3 py-1.5 bg-amber-700 text-white text-sm rounded hover:bg-amber-800 disabled:opacity-50"
        >
          {uploading ? t("leidenImport.uploading") : t("leidenImport.importButton")}
        </button>
      </div>
      {message && (
        <p className="text-xs text-green-700 mt-2">
          {message}{t("leidenImport.successSuffix")}
        </p>
      )}
      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
    </div>
  );
}
