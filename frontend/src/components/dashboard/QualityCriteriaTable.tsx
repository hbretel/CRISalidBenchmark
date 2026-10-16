"use client";

import { ChevronRight } from "lucide-react";
import type { QualityCriterion, QualitySummary } from "@/types/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { t } from "@/lib/i18n";

const ROLE_LABELS: Record<QualityCriterion["role"], { label: string; tooltip?: string }> = {
  coefficient: { label: "quality.roleCoefficient", tooltip: "quality.roleCoefficientTooltip" },
  points: { label: "quality.rolePoints", tooltip: "quality.rolePointsTooltip" },
  modulateur: { label: "quality.roleModulator", tooltip: "quality.roleModulatorTooltip" },
  aucun: { label: "quality.roleNone" },
};

function criterionSortKey(id: string): number[] {
  return id.split(".").map(Number);
}

function compareIds(a: string, b: string): number {
  const ka = criterionSortKey(a);
  const kb = criterionSortKey(b);
  for (let i = 0; i < Math.max(ka.length, kb.length); i++) {
    const d = (ka[i] ?? -1) - (kb[i] ?? -1);
    if (d) return d;
  }
  return 0;
}

// Header cells stick below the dashboard's sticky header (see DataTable).
const STICKY: React.CSSProperties = { top: "var(--sticky-offset, 0px)" };
const TH = "sticky z-10 bg-gray-50 shadow-[inset_0_-1px_0_#e5e7eb] py-1.5 px-2 font-medium";

export function QualityCriteriaTable({ categories }: { categories: NonNullable<QualitySummary["categories"]> }) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        {t("quality.criteriaTitle")}
        <InfoTooltip text={t("quality.criteriaTooltip")} />
      </h3>
      <div className="space-y-2">
        {categories.map((cat) => {
          const count = cat.subcategories.reduce((n, s) => n + s.criteria.length, 0);
          return (
            <details key={cat.name} className="group border rounded-md">
              <summary className="flex items-center gap-2 px-3 py-2 cursor-pointer select-none text-sm font-medium text-gray-800">
                <ChevronRight size={14} className="transition-transform group-open:rotate-90 text-gray-400" />
                {cat.name}
                <span className="text-xs font-normal text-gray-400">{t("quality.criteriaCount", { n: count })}</span>
              </summary>
              {/* No overflow container on large screens: it would stop the header from sticking. */}
              <div className="max-lg:overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500">
                      <th style={STICKY} className={`${TH} text-left`}>{t("quality.colCriterion")}</th>
                      <th style={STICKY} className={`${TH} text-left`}>{t("quality.colRole")}</th>
                      <th style={STICKY} className={`${TH} text-right`}>{t("quality.colShareYes")}</th>
                      <th style={STICKY} className={`${TH} text-right`}>{t("quality.colCoverage")}</th>
                      <th style={STICKY} className={`${TH} text-right whitespace-nowrap`}>{t("quality.colCounts")}</th>
                    </tr>
                  </thead>
                  {cat.subcategories.map((sub) => (
                    <tbody key={sub.name} className="divide-y">
                      <tr>
                        <td colSpan={5} className="pt-3 pb-1 px-2 text-xs font-semibold text-gray-500">
                          {sub.name}
                        </td>
                      </tr>
                      {[...sub.criteria].sort((a, b) => compareIds(a.id, b.id)).map((c) => (
                        <CriterionRow key={c.id} criterion={c} />
                      ))}
                    </tbody>
                  ))}
                </table>
              </div>
            </details>
          );
        })}
      </div>
    </div>
  );
}

function CriterionRow({ criterion: c }: { criterion: QualityCriterion }) {
  const role = ROLE_LABELS[c.role];
  return (
    <tr>
      <td className="py-1.5 px-2 text-gray-700">
        <span className="text-xs text-gray-400 tabular-nums mr-1.5">{c.id}</span>
        <span title={c.label}>{c.label.length > 110 ? `${c.label.slice(0, 110)}…` : c.label}</span>
      </td>
      <td className="py-1.5 px-2 text-xs text-gray-500 whitespace-nowrap" title={role.tooltip ? t(role.tooltip) : undefined}>
        {t(role.label)}
      </td>
      <td className="py-1.5 px-2 text-right whitespace-nowrap">
        {c.share_yes != null ? (
          <span className="inline-flex items-center gap-1.5">
            <span className="w-14 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <span className="block h-full bg-brand-500" style={{ width: `${c.share_yes}%` }} />
            </span>
            <span className="tabular-nums text-gray-700 w-10">{c.share_yes.toLocaleString("fr-FR")}%</span>
          </span>
        ) : (
          t("common.dash")
        )}
      </td>
      <td className="py-1.5 px-2 text-right tabular-nums text-gray-500">
        {c.coverage != null ? `${c.coverage.toLocaleString("fr-FR")}%` : t("common.dash")}
      </td>
      <td className="py-1.5 px-2 text-right tabular-nums text-xs text-gray-500 whitespace-nowrap">
        {c.yes.toLocaleString("fr-FR")} / {c.no.toLocaleString("fr-FR")} / {c.undetermined.toLocaleString("fr-FR")}
      </td>
    </tr>
  );
}
