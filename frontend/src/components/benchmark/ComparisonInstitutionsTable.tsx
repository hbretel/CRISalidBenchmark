"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { usePeerComparisonTable } from "@/hooks/usePeerGroups";
import type { PeerComparisonRow } from "@/types/api";
import { t } from "@/lib/i18n";

type SortKey =
  | "name"
  | "p_total"
  | "headline_value"
  | "oa_pct"
  | "collab_pct"
  | "herfindahl_simplified"
  | "quality_coefficient"
  | "composite_score";

const COLUMNS: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: "name", label: t("comparisonTable.colInstitution") },
  { key: "p_total", label: t("comparisonTable.colPublications"), numeric: true },
  { key: "headline_value", label: t("comparisonTable.colHeadline"), numeric: true },
  { key: "oa_pct", label: t("comparisonTable.colOa"), numeric: true },
  { key: "collab_pct", label: t("comparisonTable.colCollab"), numeric: true },
  { key: "herfindahl_simplified", label: t("comparisonTable.colSpecificity"), numeric: true },
  { key: "quality_coefficient", label: t("comparisonTable.colQuality"), numeric: true },
  { key: "composite_score", label: t("comparisonTable.colScore"), numeric: true },
];

interface Props {
  groupId: number | null;
  weightProfileId: number | null;
  coreOnly: boolean;
  field: string;
}

export function ComparisonInstitutionsTable({ groupId, weightProfileId, coreOnly, field }: Props) {
  const { data, isLoading, error } = usePeerComparisonTable(groupId, weightProfileId, coreOnly, field);
  const [sortKey, setSortKey] = useState<SortKey>("composite_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  if (!groupId || !weightProfileId) return null;
  if (isLoading) return <div className="mt-3 text-xs text-gray-400">{t("common.computing")}</div>;
  if (error) return <div className="mt-3 text-xs text-red-600">{t("comparisonTable.computeError")}</div>;
  if (!data || data.rows.length === 0) return null;

  const sorted = [...data.rows].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (av === null && bv === null) return 0;
    if (av === null) return 1;
    if (bv === null) return -1;
    const cmp = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number);
    return sortDir === "asc" ? cmp : -cmp;
  });

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-sm font-semibold text-gray-700">{t("comparisonTable.title")}</h3>
        <InfoTooltip
          text={
            data.specificity_note +
            (data.field !== "All sciences" ? t("comparisonTable.tooltipDomain") : "") +
            t("comparisonTable.tooltipQuality") +
            t("comparisonTable.tooltipEdition", {
              headline:
                data.headline_column === "pp_top_10"
                  ? t("comparisonTable.tooltipHeadlinePpTop10")
                  : t("comparisonTable.tooltipHeadlinePp10Cits"),
              year: data.snapshot_year ?? "…",
            })
          }
        />
      </div>
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => toggleSort(col.key)}
                  className={`py-1.5 px-2 text-xs font-medium text-gray-500 select-none cursor-pointer hover:text-gray-800 whitespace-nowrap ${
                    col.numeric ? "text-right" : "text-left"
                  }`}
                >
                  <span className={`inline-flex items-center gap-1 ${col.numeric ? "flex-row-reverse" : ""}`}>
                    {col.label}
                    {sortKey === col.key ? (
                      sortDir === "desc" ? <ArrowDown size={11} /> : <ArrowUp size={11} />
                    ) : (
                      <ArrowUpDown size={11} className="opacity-30" />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {sorted.map((row) => (
              <Row key={row.ror_id} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Row({ row }: { row: PeerComparisonRow }) {
  return (
    <tr className={row.is_own ? "bg-brand-50 font-medium" : undefined}>
      <td className="py-2 px-2 text-gray-800">
        {row.name ?? row.ror_id}
        {row.is_own && <span className="ml-1.5 text-xs text-brand-600">{t("comparisonTable.ownTag")}</span>}
        {row.country_code && <span className="ml-1.5 text-xs text-gray-400">{row.country_code}</span>}
      </td>
      <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
        {row.p_total != null ? Math.round(row.p_total).toLocaleString("fr-FR") : t("common.dash")}
      </td>
      <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
        {row.headline_value != null ? `${row.headline_value}%` : t("common.dash")}
      </td>
      <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
        {row.oa_pct != null ? `${row.oa_pct}%` : t("common.dash")}
      </td>
      <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
        {row.collab_pct != null ? `${row.collab_pct}%` : t("common.dash")}
      </td>
      <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
        {row.herfindahl_simplified != null ? row.herfindahl_simplified.toFixed(3) : t("common.dash")}
      </td>
      <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
        {row.quality_coefficient != null ? `×${row.quality_coefficient.toLocaleString("fr-FR")}` : t("common.dash")}
      </td>
      <td className="py-2 px-2 text-right font-semibold text-brand-700 tabular-nums">
        {row.composite_score}
      </td>
    </tr>
  );
}
