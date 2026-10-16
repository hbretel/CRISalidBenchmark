"use client";

import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { t } from "@/lib/i18n";

interface TopicDistributionStatus {
  status: "complete" | "in_progress";
  progress: { done: number; total: number };
}

/**
 * Triggers (and polls) the peer topic-count cache fill for a peer group —
 * required for the dashboard's "Topics signature" section, which otherwise
 * shows a dead-end message pointing back here with no actual control to
 * launch the calculation. Backed by GET /peer-groups/{id}/topic-distribution,
 * which both starts the fill (idempotent — no-ops if already running/cached)
 * and reports progress.
 */
export function PeerTopicCachePanel({ groupId }: { groupId: number }) {
  const [state, setState] = useState<TopicDistributionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setState(null);
    setError(null);
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, [groupId]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function poll() {
    try {
      const res = await api.get<TopicDistributionStatus>(`/peer-groups/${groupId}/topic-distribution`);
      setState(res);
      if (res.status === "complete" && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return res;
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("peerTopicCache.error"));
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return null;
    }
  }

  async function handleTrigger() {
    setTriggering(true);
    setError(null);
    const res = await poll();
    setTriggering(false);
    if (res?.status === "in_progress" && !pollRef.current) {
      pollRef.current = setInterval(poll, 2000);
    }
  }

  const running = triggering || state?.status === "in_progress";

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
      <button
        onClick={handleTrigger}
        disabled={running}
        className="flex items-center gap-1.5 px-2.5 py-1.5 border rounded text-gray-700 hover:bg-gray-50 disabled:opacity-50"
      >
        <RefreshCw size={13} className={running ? "animate-spin" : ""} />
        {running ? t("peerTopicCache.computing") : t("peerTopicCache.trigger")}
      </button>
      <InfoTooltip text={t("peerTopicCache.tooltip")} />
      {state && (
        <span className="text-gray-400">
          {state.status === "complete"
            ? t("peerTopicCache.complete", { done: state.progress.done, total: state.progress.total })
            : t("peerTopicCache.inProgress", { done: state.progress.done, total: state.progress.total })}
        </span>
      )}
      {error && <span className="text-red-600">{error}</span>}
    </div>
  );
}
