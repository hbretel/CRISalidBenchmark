"use client";

import { useState } from "react";
import useSWR from "swr";
import { Bot, CheckCircle, ClipboardCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { LlmStatus } from "@/types/api";
import { useSyncStatus } from "@/hooks/useSyncStatus";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { t } from "@/lib/i18n";

/** Configuration page card: qualitative-indicators job status/trigger + vLLM status. */
export function QualityJobPanel() {
  const { jobs } = useSyncStatus();
  const { data: llm } = useSWR<LlmStatus>("/quality/llm-status", () => api.get<LlmStatus>("/quality/llm-status"));
  const [starting, setStarting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const lastJob = jobs.find((j) => j.job_name === "quality_nightly");
  const running = lastJob?.status === "running";

  async function handleRun() {
    setStarting(true);
    setMessage(null);
    setError(null);
    try {
      await api.post("/admin/sync/quality", {});
      setMessage(t("configuration.qualityStarted"));
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? t("configuration.qualityAlreadyRunning")
          : err instanceof ApiError ? err.detail : t("configuration.genericError"),
      );
    } finally {
      setStarting(false);
    }
  }

  let status = t("configuration.qualityNever");
  if (lastJob && running) {
    status = t("configuration.qualityRunning", { n: lastJob.records_processed.toLocaleString("fr-FR") });
  } else if (lastJob) {
    status = t("configuration.qualityLastRun", {
      status: lastJob.status === "success" ? t("configuration.qualitySuccess") : t("configuration.qualityFailed"),
      date: new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" }).format(
        new Date(lastJob.finished_at ?? lastJob.started_at),
      ),
      n: lastJob.records_processed.toLocaleString("fr-FR"),
    });
  }

  let llmLine = t("common.loading");
  if (llm && !llm.enabled) llmLine = t("configuration.llmDisabled");
  else if (llm && !llm.reachable) llmLine = t("configuration.llmUnreachable", { error: llm.error ?? "?" });
  else if (llm && llm.model_available === false)
    llmLine = t("configuration.llmModelMissing", { model: llm.model ?? "?", models: llm.models.join(", ") });
  else if (llm) llmLine = t("configuration.llmReachable", { model: llm.model ?? "?" });

  return (
    <section className="bg-white border rounded-lg p-5 mt-4">
      <div className="flex items-center gap-2 mb-3">
        <ClipboardCheck size={16} className="text-brand-600" />
        <h2 className="text-sm font-semibold text-gray-700">{t("configuration.qualityTitle")}</h2>
      </div>
      <p className="text-xs text-gray-500 mb-3">{t("configuration.qualityIntro")}</p>
      <div className="flex items-center justify-between gap-3">
        <p className={`text-sm ${lastJob?.status === "failed" ? "text-red-600" : "text-gray-700"}`}>{status}</p>
        <button
          onClick={handleRun}
          disabled={starting || running}
          className="px-4 py-2 bg-brand-600 text-white text-sm rounded disabled:opacity-50 shrink-0"
        >
          {t("configuration.qualityRun")}
        </button>
      </div>
      {lastJob?.status === "failed" && lastJob.error_message && (
        <p className="text-xs text-red-600 mt-1 break-words">{lastJob.error_message}</p>
      )}
      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      {message && (
        <p className="text-xs text-green-700 mt-2 flex items-center gap-1">
          <CheckCircle size={13} /> {message}
        </p>
      )}

      <div className="mt-4 pt-3 border-t flex items-start gap-2 text-sm">
        <Bot size={15} className="text-gray-400 mt-0.5 shrink-0" />
        <div className="flex-1">
          <span className="font-medium text-gray-700">{t("configuration.llmTitle")}</span>
          <p className="text-xs text-gray-500 mt-0.5">{llmLine}</p>
        </div>
        <InfoTooltip text={t("configuration.llmTooltip")} />
      </div>
    </section>
  );
}
