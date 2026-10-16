"use client";

import { Modal } from "@/components/ui/Modal";
import type { ScoreAxis, ScoreComponent } from "@/types/api";
import { t } from "@/lib/i18n";

interface Props {
  open: boolean;
  onClose: () => void;
  institutionName: string;
  compositeScore: number;
  breakdown: ScoreAxis[];
  profileName?: string;
}

function pct(w: number | null): string {
  return w === null ? t("common.dash") : `${Math.round(w * 1000) / 10} %`;
}

function formatValue(c: ScoreComponent): string {
  if (c.value === null) return t("common.dash");
  if (c.unit === "×") return `×${c.value.toLocaleString("fr-FR", { maximumFractionDigits: 3 })}`;
  return `${c.value.toLocaleString("fr-FR", { maximumFractionDigits: 2 })}${c.unit ? ` ${c.unit}` : ""}`;
}

/** "How is this global score computed": every axis, sub-indicator, weight and contribution. */
export function ScoreBreakdownModal({ open, onClose, institutionName, compositeScore, breakdown, profileName }: Props) {
  const scored = breakdown.filter((a) => a.contribution !== null);
  const formula = scored.map((a) => `${a.score} × ${pct(a.applied_weight)}`).join(" + ");

  return (
    <Modal open={open} onClose={onClose} title={t("scoreBreakdown.title", { name: institutionName })} maxWidth="max-w-3xl">
      <div className="space-y-4 text-sm">
        <p className="text-xs text-gray-600 leading-relaxed">
          {t("scoreBreakdown.intro")}
          {profileName && ` ${t("scoreBreakdown.profile", { profile: profileName })}`}
        </p>

        {breakdown.map((axis) => (
          <div key={axis.axis} className="border rounded-lg">
            <div className="flex flex-wrap items-baseline justify-between gap-2 px-3 py-2 bg-gray-50 border-b rounded-t-lg">
              <span className="font-semibold text-gray-800">{t(`axis.${axis.axis}`)}</span>
              <span className="text-xs text-gray-600">
                {!axis.applicable
                  ? t("scoreBreakdown.notApplicable")
                  : axis.score === null
                    ? t("scoreBreakdown.noData")
                    : axis.contribution === null
                      ? t("scoreBreakdown.zeroWeight", { score: axis.score })
                      : t("scoreBreakdown.axisLine", {
                          score: axis.score,
                          weight: pct(axis.weight),
                          applied: pct(axis.applied_weight),
                          contribution: axis.contribution,
                        })}
              </span>
            </div>
            {axis.components.length > 0 && (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500">
                    <th className="text-left font-medium px-3 py-1.5">{t("scoreBreakdown.colIndicator")}</th>
                    <th className="text-right font-medium px-3 py-1.5">{t("scoreBreakdown.colValue")}</th>
                    <th className="text-right font-medium px-3 py-1.5">{t("scoreBreakdown.colPercentile")}</th>
                    <th className="text-right font-medium px-3 py-1.5">{t("scoreBreakdown.colWeight")}</th>
                    <th className="text-right font-medium px-3 py-1.5">{t("scoreBreakdown.colApplied")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {axis.components.map((c) => (
                    <tr key={c.key} className={c.applied_weight === null ? "text-gray-400" : "text-gray-700"}>
                      <td className="px-3 py-1.5">{t(`indicator.${c.key}`)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{formatValue(c)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{c.percentile ?? t("common.dash")}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{pct(c.weight)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{pct(c.applied_weight)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {axis.axis === "qualite" && (
              <p className="px-3 py-1.5 text-[11px] text-gray-400 border-t">{t("scoreBreakdown.qualityWeightsNote")}</p>
            )}
          </div>
        ))}

        <div className="bg-brand-50 border border-brand-200 rounded-lg px-3 py-2 text-brand-800">
          <span className="font-semibold">{t("scoreBreakdown.total")}</span>{" "}
          {formula ? `${formula} = ${compositeScore}` : compositeScore}
        </div>
        <p className="text-[11px] text-gray-400">{t("scoreBreakdown.footer")}</p>
      </div>
    </Modal>
  );
}
