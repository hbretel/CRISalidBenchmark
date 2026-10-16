"use client";

import { useSyncStatus } from "@/hooks/useSyncStatus";
import { AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { t } from "@/lib/i18n";

function formatDate(iso: string | null): string {
  if (!iso) return t("freshnessBar.leidenNever");
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(iso));
}

function isStale(iso: string | null, maxHours = 48): boolean {
  if (!iso) return true;
  const diff = Date.now() - new Date(iso).getTime();
  return diff > maxHours * 3_600_000;
}

export function DataFreshnessBar() {
  const { lastOpenAlexSync, lastLeidenSync, leidenSummary, isLoading } = useSyncStatus();

  if (isLoading) return null;

  const openAlexStale = isStale(lastOpenAlexSync);
  const neverSynced = !lastOpenAlexSync;

  const bgColor = neverSynced
    ? "bg-red-50 border-red-200"
    : openAlexStale
      ? "bg-amber-50 border-amber-200"
      : "bg-green-50 border-green-200";

  const Icon = neverSynced || openAlexStale ? AlertTriangle : CheckCircle;
  const iconColor = neverSynced
    ? "text-red-500"
    : openAlexStale
      ? "text-amber-500"
      : "text-green-500";

  return (
    <div className={`border-b px-4 py-1.5 text-xs flex items-center gap-4 ${bgColor}`}>
      <Icon size={13} className={iconColor} />
      <span className="text-gray-600">
        <strong>{t("freshnessBar.openalexLabel")}</strong>{" "}
        {neverSynced ? (
          <span className="text-red-600 font-medium">{t("freshnessBar.neverSynced")}</span>
        ) : (
          <>
            {t("freshnessBar.syncedOnPrefix")}{" "}
            <span className={openAlexStale ? "text-amber-700 font-medium" : "text-gray-700"}>
              {formatDate(lastOpenAlexSync)}
            </span>
            {openAlexStale && t("freshnessBar.staleFlag")}
          </>
        )}
      </span>
      <span className="text-gray-400">|</span>
      <span className="text-gray-600">
        <strong>{t("freshnessBar.leidenLabel")}</strong>{" "}
        {lastLeidenSync && leidenSummary ? (
          <span className="text-gray-700">
            {t("freshnessBar.leidenImported", { date: formatDate(lastLeidenSync) })}
            {leidenSummary.period && t("freshnessBar.leidenPeriod", { period: leidenSummary.period })} ·{" "}
            {t("freshnessBar.leidenCounts", {
              rows: leidenSummary.row_count.toLocaleString("fr-FR"),
              institutions: leidenSummary.institution_count.toLocaleString("fr-FR"),
            })}
          </span>
        ) : (
          <span className="text-gray-500">{t("freshnessBar.leidenNever")}</span>
        )}
      </span>
      <span className="ml-auto flex items-center gap-1 text-gray-400">
        <Clock size={11} />
        {t("freshnessBar.refreshNote")}
      </span>
    </div>
  );
}
