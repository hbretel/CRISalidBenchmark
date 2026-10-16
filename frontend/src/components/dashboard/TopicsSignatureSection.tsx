"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { Calculator } from "lucide-react";
import { api } from "@/lib/api";
import type { SignatureTopic, TopicsSignature } from "@/types/api";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { ScoreBreakdownModal } from "@/components/benchmark/ScoreBreakdownModal";
import { t } from "@/lib/i18n";

interface Props {
  peerGroupId: number;
  weightProfileId: number;
  profileName?: string;
}

const fmt = (v: number | null, digits = 1) =>
  v === null ? t("common.dash") : v.toLocaleString("fr-FR", { maximumFractionDigits: digits });

/** Topics where the reference institution ranks first of its group (backend services/topics_signature.py). */
export function TopicsSignatureSection({ peerGroupId, weightProfileId, profileName }: Props) {
  const [selected, setSelected] = useState<SignatureTopic | null>(null);
  const { data, isLoading, error } = useSWR<TopicsSignature>(
    `/indicators/topics-signature?peer_group_id=${peerGroupId}&weight_profile_id=${weightProfileId}`,
    (url: string) => api.get<TopicsSignature>(url),
  );

  const columns = useMemo<Column<SignatureTopic>[]>(
    () => [
      {
        key: "topic_name",
        label: t("signature.colTopic"),
        sortValue: (r) => r.topic_name,
        render: (r) => (
          <>
            {r.topic_name}
            {r.subfield_name && <span className="block text-xs text-gray-400">{r.subfield_name}</span>}
          </>
        ),
      },
      {
        key: "own_publications",
        label: t("signature.colPublications"),
        numeric: true,
        sortValue: (r) => r.own_publications,
        render: (r) => r.own_publications.toLocaleString("fr-FR"),
      },
      {
        key: "own_share_permille",
        label: t("signature.colShare"),
        numeric: true,
        sortValue: (r) => r.own_share_permille,
        render: (r) => fmt(r.own_share_permille, 2),
      },
      {
        key: "own_top10_pct",
        label: t("signature.colTop10"),
        numeric: true,
        sortValue: (r) => r.own_impact.pp_top_10 ?? null,
        render: (r) => `${fmt(r.own_impact.pp_top_10 ?? null)} %`,
      },
      {
        key: "own_p_top10",
        label: t("signature.colPTop10"),
        numeric: true,
        sortValue: (r) => r.own_volume.p_top_10 ?? null,
        render: (r) => r.own_volume.p_top_10?.toLocaleString("fr-FR") ?? t("common.dash"),
      },
      {
        key: "own_oa_pct",
        label: t("signature.colOa"),
        numeric: true,
        sortValue: (r) => r.own_impact.pp_oa ?? null,
        render: (r) => `${fmt(r.own_impact.pp_oa ?? null)} %`,
      },
      {
        key: "own_intl_pct",
        label: t("signature.colIntl"),
        numeric: true,
        sortValue: (r) => r.own_impact.pp_int_collab ?? null,
        render: (r) => `${fmt(r.own_impact.pp_int_collab ?? null)} %`,
      },
      {
        key: "own_quality",
        label: t("signature.colQuality"),
        numeric: true,
        sortValue: (r) => r.own_quality,
        render: (r) => (r.own_quality === null ? t("common.dash") : `×${fmt(r.own_quality, 2)}`),
      },
      {
        key: "own_score",
        label: t("signature.colScore"),
        numeric: true,
        sortValue: (r) => r.own_score,
        render: (r) => (
          <button
            type="button"
            onClick={() => setSelected(r)}
            className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline"
            aria-label={t("signature.scoreButtonLabel", { topic: r.topic_name })}
          >
            <Calculator size={12} className="opacity-60" />
            {fmt(r.own_score)}
          </button>
        ),
      },
      {
        key: "runner_up_score",
        label: t("signature.colRunnerUp"),
        numeric: true,
        sortValue: (r) => r.runner_up_score,
        render: (r) =>
          r.runner_up_score === null ? (
            <span className="text-xs text-gray-400">{t("signature.alone")}</span>
          ) : (
            <span>
              {fmt(r.runner_up_score)}
              <span className="block text-xs text-gray-400">{r.runner_up_name}</span>
            </span>
          ),
      },
      {
        key: "margin",
        label: t("signature.colMargin"),
        numeric: true,
        sortValue: (r) => r.margin,
        render: (r) => (r.margin === null ? t("common.dash") : `+${fmt(r.margin)}`),
      },
      {
        key: "n_compared",
        label: t("signature.colCompared"),
        numeric: true,
        sortValue: (r) => r.n_compared,
        render: (r) => r.n_compared,
      },
    ],
    [],
  );

  return (
    <section className="mb-10">
      <h2 className="text-base font-semibold text-gray-800 mb-1">{t("signature.title")}</h2>
      <p className="text-sm text-gray-500 mb-2">{t("signature.subtitle")}</p>

      <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800 leading-relaxed">
        <strong>{t("signature.methodLabel")}</strong>{" "}
        {t("signature.method", {
          min: data?.min_publications ?? 10,
          start: data?.period_start ?? "…",
          end: data?.period_end ?? "…",
        })}
      </div>

      {isLoading && <div className="text-gray-500 text-sm">{t("common.computing")}</div>}
      {error && <div className="text-red-600 text-sm">{t("signature.computeError")}</div>}

      {data && !(data.own_cache_populated && data.peer_cache_populated) && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800">
          {t("signature.cacheMissingBefore")} <em>{t("nav.settings")}</em>
          {t("signature.cacheMissingAfter")}
        </div>
      )}

      {data?.own_cache_populated && data.peer_cache_populated && (
        <>
          <p className="text-xs text-gray-400 mb-2">
            {t("signature.coverage", { n: data.institutions_with_data, total: data.group_size + 1 })}
          </p>
          {data.items.length === 0 ? (
            <p className="text-sm text-gray-500">{t("signature.none", { min: data.min_publications })}</p>
          ) : (
            <DataTable
              columns={columns}
              rows={data.items}
              rowKey={(r) => r.topic_id}
              initialSort={{ key: "margin", dir: "desc" }}
            />
          )}
        </>
      )}

      {selected && (
        <ScoreBreakdownModal
          open
          onClose={() => setSelected(null)}
          institutionName={selected.topic_name}
          compositeScore={selected.own_score}
          breakdown={selected.breakdown}
          profileName={profileName}
        />
      )}
    </section>
  );
}
