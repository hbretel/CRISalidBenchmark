"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { QualityVerdict, QualityWorkDetail } from "@/types/api";
import { Modal } from "@/components/ui/Modal";
import { t } from "@/lib/i18n";

const VERDICT_STYLES: Record<QualityVerdict, { label: string; className: string }> = {
  Oui: { label: "quality.verdictYes", className: "bg-green-50 text-green-700 border-green-200" },
  Non: { label: "quality.verdictNo", className: "bg-gray-50 text-gray-600 border-gray-200" },
  Indéterminé: { label: "quality.verdictUndetermined", className: "bg-amber-50 text-amber-700 border-amber-200" },
};

export function QualityWorkModal({ workId, onClose }: { workId: string | null; onClose: () => void }) {
  const { data, error, isLoading } = useSWR<QualityWorkDetail>(
    workId ? `/quality/work?id=${encodeURIComponent(workId)}` : null,
    (url: string) => api.get<QualityWorkDetail>(url),
  );

  // Group by grid category, keeping the backend's criterion-id order.
  const groups = new Map<string, QualityWorkDetail["criteria"]>();
  data?.criteria.forEach((c) => {
    groups.set(c.category, [...(groups.get(c.category) ?? []), c]);
  });

  return (
    <Modal open={workId !== null} onClose={onClose} title={t("quality.detailTitle")} maxWidth="max-w-3xl">
      {isLoading && <p className="text-sm text-gray-500">{t("quality.detailLoading")}</p>}
      {error && <p className="text-sm text-red-600">{t("quality.detailError")}</p>}
      {data && (
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-gray-900">{data.title ?? data.id}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {[data.publication_year, data.type, data.source && t("quality.detailSource", { source: data.source })]
                .filter(Boolean)
                .join(" · ")}
              {data.doi && (
                <>
                  {" · "}
                  <a href={data.doi} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline">
                    {data.doi.replace("https://doi.org/", "")}
                  </a>
                </>
              )}
            </p>
            {data.score.coefficient != null && (
              <p className="text-sm font-semibold text-brand-700 mt-2">
                {t("quality.detailCoefficient", { value: data.score.coefficient.toLocaleString("fr-FR") })}
              </p>
            )}
          </div>
          <p className="text-xs text-gray-400">{t("quality.detailNote")}</p>
          {[...groups.entries()].map(([category, criteria]) => (
            <div key={category}>
              <h4 className="text-xs font-semibold text-gray-500 mb-1">{category}</h4>
              <ul className="divide-y border rounded-md">
                {criteria.map((c) => {
                  const style = VERDICT_STYLES[c.verdict];
                  return (
                    <li key={c.id} className="px-3 py-2">
                      <div className="flex items-start gap-2">
                        <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded border ${style.className}`}>
                          {t(style.label)}
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm text-gray-800">
                            <span className="text-xs text-gray-400 tabular-nums mr-1.5">{c.id}</span>
                            {c.label}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5 break-words">
                            {c.evidence}
                            {c.confidence === "heuristique" && (
                              <span className="ml-1.5 text-amber-600">({t("quality.confidenceHeuristic")})</span>
                            )}
                          </p>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}
