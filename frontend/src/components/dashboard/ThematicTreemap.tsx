"use client";

import { useMemo, useState } from "react";
import { Treemap, ResponsiveContainer } from "recharts";
import { ChevronRight } from "lucide-react";
import type { TopicTreeNode } from "@/types/api";
import { getCategoricalColor, getContrastTextColor, getShade } from "@/lib/topicColors";
import { t } from "@/lib/i18n";

interface Props {
  data: TopicTreeNode[]; // root: Domains
  totalWorks: number;
}

const LEVEL_HINT_KEYS = [
  "treemap.hintDomain",
  "treemap.hintField",
  "treemap.hintSubfield",
  "treemap.hintTopic",
] as const;

function truncate(name: string, maxWidthPx: number, fontSize: number): string {
  const approxCharWidth = fontSize * 0.56;
  const maxChars = Math.max(0, Math.floor((maxWidthPx - 10) / approxCharWidth));
  if (name.length <= maxChars) return name;
  if (maxChars <= 1) return "";
  return `${name.slice(0, maxChars - 1)}…`;
}

export function ThematicTreemap({ data, totalWorks }: Props) {
  const [path, setPath] = useState<string[]>([]);

  const rootSorted = useMemo(() => [...data].sort((a, b) => b.value - a.value), [data]);

  // Walk `data` along `path`. Field colors are assigned by rank within their
  // parent Domain (stable, since a Field belongs to exactly one Domain) —
  // once two or more levels deep, remember that color so Subfield/Topic
  // cells can render as shades of it.
  const { nodes, fieldColor } = useMemo(() => {
    let level = rootSorted;
    let activeFieldColor: string | null = null;
    for (let depth = 0; depth < path.length; depth++) {
      const idx = level.findIndex((n) => n.name === path[depth]);
      if (idx === -1) break;
      if (depth === 1) activeFieldColor = getCategoricalColor(idx);
      level = [...(level[idx].children ?? [])].sort((a, b) => b.value - a.value);
    }
    return { nodes: level, fieldColor: activeFieldColor };
  }, [rootSorted, path]);

  // Recharts recomputes the whole subtree under whatever `children` ride
  // along on each data item (see Treemap's getDerivedStateFromProps, which
  // always recurses into node.children regardless of the `type` prop) — so
  // the Treemap must only ever receive the current level's bare {id, name,
  // value}, with no nested `children`, or it silently tries to squarify
  // several levels of descendants at once and throws deep inside its own
  // layout code. Drilldown state (does this cell have children to explore?)
  // is instead read from the `nodes` closure by index, not from recharts.
  const flatNodes = useMemo(
    () => nodes.map((n) => ({ id: n.id, name: n.name, value: n.value })),
    [nodes],
  );

  function colorForIndex(index: number): string {
    if (path.length < 2) return getCategoricalColor(index);
    return getShade(fieldColor ?? getCategoricalColor(0), index, Math.max(nodes.length, 1));
  }

  function renderCell(nodeProps: { x: number; y: number; width: number; height: number; index: number }) {
    const { x, y, width, height, index } = nodeProps;
    const source = nodes[index];
    if (!source) return <g />;
    const { name, value, children } = source;
    const fill = colorForIndex(index);
    const textColor = getContrastTextColor(fill);
    const canDrill = Array.isArray(children) && children.length > 0;
    const showLabel = width > 44 && height > 24;
    const showCount = showLabel && height > 42;
    const nounPub = value > 1 ? t("treemap.publicationPlural") : t("treemap.publicationSingular");

    return (
      <g
        onClick={canDrill ? () => setPath((p) => [...p, name]) : undefined}
        style={{ cursor: canDrill ? "pointer" : "default" }}
      >
        <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#fff" strokeWidth={1.5} rx={2} />
        <title>{`${name} — ${value.toLocaleString("fr-FR")} ${nounPub}${canDrill ? t("treemap.clickToExplore") : ""}`}</title>
        {showLabel && (
          <text x={x + 6} y={y + 16} fontSize={11} fontWeight={600} fill={textColor} style={{ pointerEvents: "none" }}>
            {truncate(name, width, 11)}
          </text>
        )}
        {showCount && (
          <text x={x + 6} y={y + 32} fontSize={10} fill={textColor} opacity={0.85} style={{ pointerEvents: "none" }}>
            {`${value.toLocaleString("fr-FR")} ${nounPub}`}
          </text>
        )}
      </g>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-1 text-xs text-gray-500 mb-1 flex-wrap">
        <button
          onClick={() => setPath([])}
          className={path.length === 0 ? "font-semibold text-gray-800" : "hover:text-brand-600"}
        >
          {t("treemap.allDomains")}
        </button>
        {path.map((segment, i) => (
          <span key={segment} className="flex items-center gap-1">
            <ChevronRight size={12} />
            <button
              onClick={() => setPath(path.slice(0, i + 1))}
              className={i === path.length - 1 ? "font-semibold text-gray-800" : "hover:text-brand-600"}
            >
              {segment}
            </button>
          </span>
        ))}
      </div>
      <p className="text-xs text-gray-400 mb-2">{t(LEVEL_HINT_KEYS[Math.min(path.length, 3)])}</p>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Treemap data={flatNodes} dataKey="value" aspectRatio={4 / 3} content={renderCell as any} isAnimationActive={false} />
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-400 mt-2">
        {t("treemap.analysedFooter", { count: totalWorks.toLocaleString("fr-FR") })}
      </p>
    </div>
  );
}
