"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import type { SignatureTopic } from "@/types/api";

type SortKey = "topic_name" | "own_publication_count" | "own_share_permille" | "peer_avg_share_permille" | "ratio";

const COLUMNS: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: "topic_name", label: "Nom du Topic" },
  { key: "own_publication_count", label: "Nb. publications établissement", numeric: true },
  { key: "own_share_permille", label: "Part établissement (‰)", numeric: true },
  { key: "peer_avg_share_permille", label: "Moyenne groupe de comparaison (‰)", numeric: true },
  { key: "ratio", label: "Taux de spécialisation", numeric: true },
];

export function TopicsSignatureTable({ items }: { items: SignatureTopic[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("ratio");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const sorted = [...items].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    const cmp = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number);
    return sortDir === "asc" ? cmp : -cmp;
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
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
          {sorted.map((t) => (
            <tr key={t.topic_id}>
              <td className="py-2 px-2 text-gray-800">{t.topic_name}</td>
              <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
                {t.own_publication_count.toLocaleString("fr-FR")}
              </td>
              <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
                {t.own_share_permille.toLocaleString("fr-FR")}
              </td>
              <td className="py-2 px-2 text-right text-gray-600 tabular-nums">
                {t.peer_avg_share_permille.toLocaleString("fr-FR")}
              </td>
              <td className="py-2 px-2 text-right font-semibold text-green-700 tabular-nums">
                ×{t.ratio.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
