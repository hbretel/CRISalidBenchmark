"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, LocateFixed } from "lucide-react";
import { InfoTooltip } from "./InfoTooltip";
import { t } from "@/lib/i18n";

export const PAGE_SIZE = 25;

export interface Column<R> {
  key: string;
  label: string;
  numeric?: boolean;
  /** Value used for sorting; omit to make the column non-sortable. */
  sortValue?: (row: R) => number | string | null;
  render: (row: R) => React.ReactNode;
  tooltip?: string;
}

interface Props<R> {
  columns: Column<R>[];
  rows: R[];
  rowKey: (row: R) => string;
  initialSort?: { key: string; dir: "asc" | "desc" };
  /** Row of the reference institution: highlighted, and reachable with a "go to" button. */
  isHighlighted?: (row: R) => boolean;
  pageSize?: number;
}

/**
 * Shared summary table: sortable columns, at most PAGE_SIZE rows per page,
 * and a header that stays visible while the table is scrolled through — it
 * sticks below the dashboard's sticky header (CSS variable --sticky-offset,
 * set by StickyHeader) and leaves with the table.
 *
 * No horizontal scroll container on large screens (it would break the sticky
 * header, and tables are laid out to fit the page width); below the lg
 * breakpoint the table scrolls horizontally instead of overflowing the page.
 */
export function DataTable<R>({ columns, rows, rowKey, initialSort, isHighlighted, pageSize = PAGE_SIZE }: Props<R>) {
  const [sort, setSort] = useState(initialSort);
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const column = columns.find((c) => c.key === sort?.key);
    if (!column?.sortValue || !sort) return rows;
    const value = column.sortValue;
    return [...rows].sort((a, b) => {
      const av = value(a);
      const bv = value(b);
      if (av === null && bv === null) return 0;
      if (av === null) return 1; // missing values always last
      if (bv === null) return -1;
      const cmp = typeof av === "string" ? av.localeCompare(String(bv), "fr") : av - (bv as number);
      return sort.dir === "asc" ? cmp : -cmp;
    });
  }, [rows, columns, sort]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  useEffect(() => {
    if (page >= pageCount) setPage(pageCount - 1);
  }, [page, pageCount]);

  const visible = sorted.slice(page * pageSize, (page + 1) * pageSize);
  const highlightedIndex = isHighlighted ? sorted.findIndex(isHighlighted) : -1;
  const highlightedPage = highlightedIndex >= 0 ? Math.floor(highlightedIndex / pageSize) : null;

  function toggleSort(column: Column<R>) {
    if (!column.sortValue) return;
    setSort((s) =>
      s?.key === column.key ? { key: column.key, dir: s.dir === "desc" ? "asc" : "desc" } : { key: column.key, dir: "desc" },
    );
    setPage(0);
  }

  return (
    <div>
      <div className="border rounded-lg max-lg:overflow-x-auto">
        <table className="w-full text-sm border-separate border-spacing-0">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  style={{ top: "var(--sticky-offset, 0px)" }}
                  className={`sticky z-20 bg-gray-50 border-b py-1.5 px-2 text-xs font-medium text-gray-500 align-bottom first:rounded-tl-lg last:rounded-tr-lg ${
                    col.numeric ? "text-right" : "text-left"
                  }`}
                >
                  <span className={`inline-flex items-center gap-1 ${col.numeric ? "flex-row-reverse" : ""}`}>
                    {col.sortValue ? (
                      <button
                        type="button"
                        onClick={() => toggleSort(col)}
                        className={`inline-flex items-center gap-1 hover:text-gray-800 ${col.numeric ? "flex-row-reverse text-right" : "text-left"}`}
                      >
                        {col.label}
                        {sort?.key === col.key ? (
                          sort.dir === "desc" ? <ArrowDown size={11} /> : <ArrowUp size={11} />
                        ) : (
                          <ArrowUpDown size={11} className="opacity-30 shrink-0" />
                        )}
                      </button>
                    ) : (
                      col.label
                    )}
                    {col.tooltip && <InfoTooltip text={col.tooltip} />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={rowKey(row)} className={isHighlighted?.(row) ? "bg-brand-50 font-medium" : undefined}>
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`py-2 px-2 border-b border-gray-100 ${
                      col.numeric ? "text-right tabular-nums text-gray-600" : "text-gray-800"
                    }`}
                  >
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pageCount > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-2 mt-2 text-xs text-gray-500">
          <span>
            {t("dataTable.rows", {
              from: page * pageSize + 1,
              to: Math.min((page + 1) * pageSize, sorted.length),
              total: sorted.length,
            })}
          </span>
          <div className="flex items-center gap-1">
            {highlightedPage !== null && highlightedPage !== page && (
              <button
                type="button"
                onClick={() => setPage(highlightedPage)}
                className="mr-2 inline-flex items-center gap-1 px-2 py-1 rounded border text-brand-700 hover:bg-brand-50"
              >
                <LocateFixed size={12} /> {t("dataTable.goToOwn")}
              </button>
            )}
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-1 rounded border hover:bg-gray-50 disabled:opacity-40"
              aria-label={t("dataTable.previous")}
            >
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: pageCount }, (_, i) => i)
              .filter((i) => i === 0 || i === pageCount - 1 || Math.abs(i - page) <= 2)
              .map((i, idx, shown) => (
                <span key={i} className="inline-flex items-center">
                  {idx > 0 && shown[idx - 1] !== i - 1 && <span className="px-1">…</span>}
                  <button
                    type="button"
                    onClick={() => setPage(i)}
                    aria-current={i === page ? "page" : undefined}
                    className={`min-w-[1.75rem] px-1.5 py-1 rounded border ${
                      i === page ? "bg-brand-600 border-brand-600 text-white" : "hover:bg-gray-50"
                    } ${i === highlightedPage && i !== page ? "border-brand-400 text-brand-700" : ""}`}
                  >
                    {i + 1}
                  </button>
                </span>
              ))}
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
              disabled={page >= pageCount - 1}
              className="p-1 rounded border hover:bg-gray-50 disabled:opacity-40"
              aria-label={t("dataTable.next")}
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
