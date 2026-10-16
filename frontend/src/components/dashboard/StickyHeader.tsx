"use client";

import { useEffect, useRef } from "react";
import { Switch } from "@/components/ui/Switch";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { LEIDEN_DOMAINS, OPENALEX_DOMAINS } from "@/lib/constants";
import { t } from "@/lib/i18n";
import type { DashboardTab } from "@/hooks/useCurrentSelection";
import type { PeerGroupSummary, WeightProfileResponse } from "@/types/api";

interface Props {
  institutionName: string;
  openalexId: string;
  countryCode: string | null;
  periodStart: number | null;
  periodEnd: number | null;
  leidenDecileLabel: string | null;
  tab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
  coreOnly: boolean;
  onCoreOnlyChange: (v: boolean) => void;
  leidenField: string;
  onLeidenFieldChange: (field: string) => void;
  openalexDomain: string;
  onOpenalexDomainChange: (domain: string) => void;
  profiles: WeightProfileResponse[] | undefined;
  currentProfileId: number | null;
  onProfileChange: (id: number) => void;
  groups: PeerGroupSummary[] | undefined;
  currentGroupId: number | null;
  onGroupChange: (id: number) => void;
}

export function StickyHeader({
  institutionName,
  openalexId,
  countryCode,
  periodStart,
  periodEnd,
  leidenDecileLabel,
  tab,
  onTabChange,
  coreOnly,
  onCoreOnlyChange,
  leidenField,
  onLeidenFieldChange,
  openalexDomain,
  onOpenalexDomainChange,
  profiles,
  currentProfileId,
  onProfileChange,
  groups,
  currentGroupId,
  onGroupChange,
}: Props) {
  const period = periodStart && periodEnd ? `${periodStart}–${periodEnd}` : t("common.dash");
  const ref = useRef<HTMLDivElement>(null);

  // Table headers stick right below this header (DataTable reads
  // --sticky-offset), so it must track the header's actual height — it wraps
  // onto more lines on narrow windows.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const root = document.documentElement;
    const update = () => root.style.setProperty("--sticky-offset", `${el.offsetHeight}px`);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => {
      observer.disconnect();
      root.style.removeProperty("--sticky-offset");
    };
  }, []);

  return (
    <div ref={ref} className="sticky top-0 z-30 -mx-6 -mt-6 px-6 pt-4 pb-3 mb-6 bg-white/95 backdrop-blur border-b">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-3">
        <h1 className="text-lg font-bold text-gray-900">{institutionName}</h1>
        <div className="text-xs text-gray-500 flex items-center gap-2">
          <span>{openalexId}</span>
          {countryCode && (
            <>
              <span className="text-gray-300">·</span>
              <span>{countryCode}</span>
            </>
          )}
          <span className="text-gray-300">·</span>
          <span>{period}</span>
          {leidenDecileLabel && (
            <>
              <span className="text-gray-300">·</span>
              <span className="text-brand-600" title={t("header.decileTooltip")}>
                {leidenDecileLabel}
              </span>
            </>
          )}
        </div>
      </div>

      <div role="tablist" className="flex gap-1 mb-3 border-b -mx-1">
        {(["world", "groups"] as const).map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => onTabChange(key)}
            className={`px-3 py-1.5 text-sm font-medium -mb-px border-b-2 ${
              tab === key ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-800"
            }`}
          >
            {t(`header.tab_${key}`)}
          </button>
        ))}
      </div>

      {tab === "world" ? (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <div className="flex items-center gap-1.5">
            <Switch checked={coreOnly} onChange={onCoreOnlyChange} label={t("header.corePublicationsOnly")} />
            <InfoTooltip text={t("header.coreTooltip")} />
          </div>
          <div className="flex items-center gap-1.5">
            <label className="text-xs text-gray-500 flex items-center gap-1">
              {t("header.domainLabel")}
              <InfoTooltip text={t("header.domainTooltip")} />
            </label>
            <select
              className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={leidenField}
              onChange={(e) => onLeidenFieldChange(e.target.value)}
            >
              {LEIDEN_DOMAINS.map((d) => (
                <option key={d.value} value={d.value}>{t(`leidenDomain.${d.value}`)}</option>
              ))}
            </select>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <div className="flex items-center gap-1.5">
            <label className="text-xs text-gray-500 flex items-center gap-1">
              {t("header.openalexDomainLabel")}
              <InfoTooltip text={t("header.openalexDomainTooltip")} />
            </label>
            <select
              className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={openalexDomain}
              onChange={(e) => onOpenalexDomainChange(e.target.value)}
            >
              {OPENALEX_DOMAINS.map((d) => (
                <option key={d.value} value={d.value}>{t(`openalexDomain.${d.value}`)}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <label className="text-xs text-gray-500">{t("header.profileLabel")}</label>
            <select
              className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={currentProfileId ?? ""}
              onChange={(e) => onProfileChange(Number(e.target.value))}
            >
              {!profiles && <option>{t("common.loading")}</option>}
              {profiles?.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <label className="text-xs text-gray-500">{t("header.groupLabel")}</label>
            <select
              className="border rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              value={currentGroupId ?? ""}
              onChange={(e) => onGroupChange(Number(e.target.value))}
            >
              {!groups && <option>{t("common.loading")}</option>}
              {groups?.map((g) => (
                <option key={g.id} value={g.id}>{g.name} ({g.member_count})</option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
