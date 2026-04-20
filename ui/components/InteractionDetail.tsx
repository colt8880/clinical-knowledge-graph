"use client";

import Link from "next/link";
import type { InteractionsResponse, InteractionEdge, InteractionRec } from "@/lib/api/client";

/** Map API domain labels to guideline slugs for deep-links. */
const DOMAIN_TO_SLUG: Record<string, string> = {
  USPSTF: "uspstf-statin-2022",
  "ACC/AHA": "acc-aha-cholesterol-2018",
  KDIGO: "kdigo-ckd-2024",
};

const DOMAIN_BADGE_COLORS: Record<string, string> = {
  USPSTF: "bg-blue-100 text-blue-800",
  "ACC/AHA": "bg-purple-100 text-purple-800",
  KDIGO: "bg-emerald-100 text-emerald-800",
};

interface InteractionDetailProps {
  data: InteractionsResponse;
  selectedEdgeId: string | null;
  selectedNodeId: string | null;
}

function DomainBadge({ domain }: { domain: string | null }) {
  if (!domain) return null;
  const colors = DOMAIN_BADGE_COLORS[domain] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block px-2 py-0.5 text-[10px] font-semibold uppercase rounded ${colors}`}>
      {domain}
    </span>
  );
}

function ExploreLink({ rec }: { rec: InteractionRec }) {
  const slug = rec.domain ? DOMAIN_TO_SLUG[rec.domain] : null;
  if (!slug) return null;
  return (
    <Link
      href={`/explore/${slug}?focus=${encodeURIComponent(rec.id)}`}
      className="text-xs text-blue-600 hover:underline"
      data-testid="explore-link"
    >
      Open in Explore
    </Link>
  );
}

function EdgeDetail({ edge, data }: { edge: InteractionEdge; data: InteractionsResponse }) {
  const sourceRec = data.recommendations.find((r) => r.id === edge.source);
  const targetRec = data.recommendations.find((r) => r.id === edge.target);

  if (edge.type === "PREEMPTED_BY") {
    return (
      <div className="flex flex-col gap-3" data-testid="preemption-detail">
        <h3 className="text-sm font-semibold text-slate-900">Preemption</h3>

        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Preempted Rec</p>
          <div className="flex items-center gap-2">
            <DomainBadge domain={sourceRec?.domain ?? null} />
            <span className="text-xs text-slate-900 font-medium">{sourceRec?.title ?? edge.source}</span>
          </div>
          {sourceRec && <ExploreLink rec={sourceRec} />}
        </div>

        <div className="space-y-1">
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Winner Rec</p>
          <div className="flex items-center gap-2">
            <DomainBadge domain={targetRec?.domain ?? null} />
            <span className="text-xs text-slate-900 font-medium">{targetRec?.title ?? edge.target}</span>
          </div>
          {targetRec && <ExploreLink rec={targetRec} />}
        </div>

        {edge.edge_priority != null && (
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">Priority</p>
            <p className="text-xs text-slate-900" data-testid="edge-priority">{edge.edge_priority}</p>
          </div>
        )}

        {edge.reason && (
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">Reason</p>
            <p className="text-xs text-slate-700">{edge.reason}</p>
          </div>
        )}
      </div>
    );
  }

  // MODIFIES edge.
  return (
    <div className="flex flex-col gap-3" data-testid="modifier-detail">
      <h3 className="text-sm font-semibold text-slate-900">Modifier</h3>

      <div className="space-y-1">
        <p className="text-[11px] uppercase tracking-wide text-slate-500">Source Rec (modifier)</p>
        <div className="flex items-center gap-2">
          <DomainBadge domain={sourceRec?.domain ?? null} />
          <span className="text-xs text-slate-900 font-medium">{sourceRec?.title ?? edge.source}</span>
        </div>
        {sourceRec && <ExploreLink rec={sourceRec} />}
      </div>

      <div className="space-y-1">
        <p className="text-[11px] uppercase tracking-wide text-slate-500">Target Rec (modified)</p>
        <div className="flex items-center gap-2">
          <DomainBadge domain={targetRec?.domain ?? null} />
          <span className="text-xs text-slate-900 font-medium">{targetRec?.title ?? edge.target}</span>
        </div>
        {targetRec && <ExploreLink rec={targetRec} />}
      </div>

      {edge.nature && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Nature</p>
          <p className="text-xs text-slate-900">{edge.nature}</p>
        </div>
      )}

      {edge.note && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Note</p>
          <p className="text-xs text-slate-700">{edge.note}</p>
        </div>
      )}

      {edge.suppressed_by_preemption && (
        <div className="rounded bg-amber-50 border border-amber-200 p-2" data-testid="suppression-notice">
          <p className="text-xs text-amber-800 font-medium">
            This modifier is suppressed by a preemption on the target Rec.
          </p>
        </div>
      )}
    </div>
  );
}

function ClusterDetail({ domain, data }: { domain: string; data: InteractionsResponse }) {
  const recs = data.recommendations.filter((r) => r.domain === domain);
  const preemptionOut = data.edges.filter(
    (e) => e.type === "PREEMPTED_BY" && recs.some((r) => r.id === e.source),
  ).length;
  const preemptionIn = data.edges.filter(
    (e) => e.type === "PREEMPTED_BY" && recs.some((r) => r.id === e.target),
  ).length;
  const modifiersAuthored = data.edges.filter(
    (e) => e.type === "MODIFIES" && recs.some((r) => r.id === e.source),
  ).length;
  const modifiersReceived = data.edges.filter(
    (e) => e.type === "MODIFIES" && recs.some((r) => r.id === e.target),
  ).length;

  return (
    <div className="flex flex-col gap-3" data-testid="cluster-detail">
      <h3 className="text-sm font-semibold text-slate-900">
        <DomainBadge domain={domain} /> Cluster
      </h3>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-slate-100 rounded p-2">
          <p className="text-slate-500 text-[10px] uppercase">Preemptions out</p>
          <p className="text-slate-900 font-semibold">{preemptionOut}</p>
        </div>
        <div className="bg-slate-100 rounded p-2">
          <p className="text-slate-500 text-[10px] uppercase">Preemptions in</p>
          <p className="text-slate-900 font-semibold">{preemptionIn}</p>
        </div>
        <div className="bg-slate-100 rounded p-2">
          <p className="text-slate-500 text-[10px] uppercase">Modifiers authored</p>
          <p className="text-slate-900 font-semibold">{modifiersAuthored}</p>
        </div>
        <div className="bg-slate-100 rounded p-2">
          <p className="text-slate-500 text-[10px] uppercase">Modifiers received</p>
          <p className="text-slate-900 font-semibold">{modifiersReceived}</p>
        </div>
      </div>
    </div>
  );
}

function RecDetail({ rec, data }: { rec: InteractionRec; data: InteractionsResponse }) {
  const incomingPreemptions = data.edges.filter(
    (e) => e.type === "PREEMPTED_BY" && e.target === rec.id,
  );
  const outgoingPreemptions = data.edges.filter(
    (e) => e.type === "PREEMPTED_BY" && e.source === rec.id,
  );
  const modifiers = data.edges.filter(
    (e) => e.type === "MODIFIES" && e.target === rec.id,
  );

  return (
    <div className="flex flex-col gap-3" data-testid="rec-detail">
      <div className="flex items-center gap-2">
        <DomainBadge domain={rec.domain} />
        <h3 className="text-sm font-semibold text-slate-900">{rec.title}</h3>
      </div>

      {rec.evidence_grade && (
        <p className="text-xs text-slate-600">Grade: {rec.evidence_grade}</p>
      )}

      <ExploreLink rec={rec} />

      {outgoingPreemptions.length > 0 && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Preempted by</p>
          <ul className="text-xs text-slate-700 space-y-0.5">
            {outgoingPreemptions.map((e) => (
              <li key={e.target}>
                {data.recommendations.find((r) => r.id === e.target)?.title ?? e.target}
              </li>
            ))}
          </ul>
        </div>
      )}

      {incomingPreemptions.length > 0 && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Preempts</p>
          <ul className="text-xs text-slate-700 space-y-0.5">
            {incomingPreemptions.map((e) => (
              <li key={e.source}>
                {data.recommendations.find((r) => r.id === e.source)?.title ?? e.source}
              </li>
            ))}
          </ul>
        </div>
      )}

      {modifiers.length > 0 && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">Modifiers</p>
          <ul className="text-xs text-slate-700 space-y-0.5">
            {modifiers.map((e) => (
              <li key={e.source}>
                {data.recommendations.find((r) => r.id === e.source)?.title ?? e.source}
                {e.suppressed_by_preemption && " (suppressed)"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Cluster node ID → domain label reverse mapping. */
const CLUSTER_TO_DOMAIN: Record<string, string> = {
  __interactions_cluster_uspstf: "USPSTF",
  __interactions_cluster_acc_aha: "ACC/AHA",
  __interactions_cluster_kdigo: "KDIGO",
};

export default function InteractionDetail({
  data,
  selectedEdgeId,
  selectedNodeId,
}: InteractionDetailProps) {
  // Edge selected — show edge detail.
  if (selectedEdgeId) {
    const [edgeType, source, target] = selectedEdgeId.split("__");
    const edge = data.edges.find(
      (e) => e.type === edgeType && e.source === source && e.target === target,
    );
    if (edge) {
      return (
        <div className="w-72 border-l border-slate-200 p-4 overflow-y-auto bg-white" data-testid="interaction-detail-panel">
          <EdgeDetail edge={edge} data={data} />
        </div>
      );
    }
  }

  // Node selected — could be a cluster or a rec.
  if (selectedNodeId) {
    // Check if it's a cluster parent.
    const clusterDomain = CLUSTER_TO_DOMAIN[selectedNodeId];
    if (clusterDomain) {
      return (
        <div className="w-72 border-l border-slate-200 p-4 overflow-y-auto bg-white" data-testid="interaction-detail-panel">
          <ClusterDetail domain={clusterDomain} data={data} />
        </div>
      );
    }

    // Otherwise it's a rec node.
    const rec = data.recommendations.find((r) => r.id === selectedNodeId);
    if (rec) {
      return (
        <div className="w-72 border-l border-slate-200 p-4 overflow-y-auto bg-white" data-testid="interaction-detail-panel">
          <RecDetail rec={rec} data={data} />
        </div>
      );
    }
  }

  // Nothing selected.
  return (
    <div className="w-72 border-l border-slate-200 p-4 bg-white text-xs text-slate-500" data-testid="interaction-detail-panel">
      Click an edge or node to view details.
    </div>
  );
}
