/**
 * Pure function: takes the /interactions response and produces
 * Cytoscape-ready nodes and edges for the collapsed interactions view.
 *
 * Logic: for each PREEMPTED_BY or MODIFIES edge, include both endpoints
 * as nodes; group Recs under their guideline's compound parent. Only
 * cross-guideline edges are rendered — no within-guideline edges.
 */

import type { ElementDefinition } from "cytoscape";
import type {
  InteractionsResponse,
  InteractionEdge,
} from "@/lib/api/client";

/** Domain → compound parent node id. */
const GUIDELINE_PARENTS: Record<string, string> = {
  USPSTF: "__interactions_cluster_uspstf",
  "ACC/AHA": "__interactions_cluster_acc_aha",
  KDIGO: "__interactions_cluster_kdigo",
};

/** Domain → display label for the compound parent. */
const GUIDELINE_DISPLAY: Record<string, string> = {
  USPSTF: "USPSTF",
  "ACC/AHA": "ACC/AHA",
  KDIGO: "KDIGO",
};

/** Domain-specific colors matching the main GraphCanvas palette. */
const DOMAIN_COLORS: Record<string, { bg: string; border: string }> = {
  USPSTF: { bg: "#dbeafe", border: "#2563eb" },
  "ACC/AHA": { bg: "#ede9fe", border: "#7c3aed" },
  KDIGO: { bg: "#d1fae5", border: "#059669" },
};

export interface CollapsedGraph {
  elements: ElementDefinition[];
  /** Map from guideline domain → list of rec IDs in that cluster. */
  clusterRecs: Map<string, string[]>;
}

export type EdgeTypeFilter = "preemption" | "modifier" | "both";

export function collapseInteractions(
  data: InteractionsResponse,
  edgeTypeFilter: EdgeTypeFilter = "both",
  visibleGuidelines?: Set<string>,
): CollapsedGraph {
  const elements: ElementDefinition[] = [];
  const clusterRecs = new Map<string, string[]>();

  // Determine which guidelines to show.
  const allDomains = new Set(data.guidelines.map((g) => g.domain));
  const activeDomains = visibleGuidelines
    ? new Set([...allDomains].filter((d) => visibleGuidelines.has(d)))
    : allDomains;

  // Filter edges by type and guideline visibility.
  const filteredEdges = data.edges.filter((edge) => {
    if (edgeTypeFilter === "preemption" && edge.type !== "PREEMPTED_BY") return false;
    if (edgeTypeFilter === "modifier" && edge.type !== "MODIFIES") return false;

    // Both endpoints' domains must be in activeDomains.
    const sourceRec = data.recommendations.find((r) => r.id === edge.source);
    const targetRec = data.recommendations.find((r) => r.id === edge.target);
    if (!sourceRec?.domain || !targetRec?.domain) return false;
    if (!activeDomains.has(sourceRec.domain) || !activeDomains.has(targetRec.domain)) return false;

    return true;
  });

  // Collect rec IDs that participate in at least one visible edge.
  const participatingRecIds = new Set<string>();
  for (const edge of filteredEdges) {
    participatingRecIds.add(edge.source);
    participatingRecIds.add(edge.target);
  }

  // Always render compound parents for all active domains (even if empty).
  for (const domain of activeDomains) {
    const parentId = GUIDELINE_PARENTS[domain];
    if (!parentId) continue;
    const colors = DOMAIN_COLORS[domain] ?? { bg: "#f1f5f9", border: "#94a3b8" };

    // Count edges for badge.
    const preemptionOut = data.edges.filter(
      (e) => e.type === "PREEMPTED_BY" && data.recommendations.find((r) => r.id === e.source)?.domain === domain,
    ).length;
    const preemptionIn = data.edges.filter(
      (e) => e.type === "PREEMPTED_BY" && data.recommendations.find((r) => r.id === e.target)?.domain === domain,
    ).length;
    const modifierCount = data.edges.filter(
      (e) => e.type === "MODIFIES" && data.recommendations.find((r) => r.id === e.source)?.domain === domain,
    ).length;

    elements.push({
      data: {
        id: parentId,
        label: GUIDELINE_DISPLAY[domain] ?? domain,
        nodeType: "__interactions_cluster",
        bgColor: `${colors.bg}80`,
        borderColor: colors.border,
        domain,
        preemptionOut,
        preemptionIn,
        modifierCount,
      },
    });

    clusterRecs.set(domain, []);
  }

  // Add rec nodes grouped under their guideline's compound parent.
  for (const rec of data.recommendations) {
    if (!participatingRecIds.has(rec.id)) continue;
    if (!rec.domain || !activeDomains.has(rec.domain)) continue;

    const parentId = GUIDELINE_PARENTS[rec.domain];
    const colors = DOMAIN_COLORS[rec.domain] ?? { bg: "#e2e8f0", border: "#64748b" };
    const isPreempted = rec.has_preemption_out;

    elements.push({
      data: {
        id: rec.id,
        label: rec.title,
        nodeType: "Recommendation",
        bgColor: colors.bg,
        borderColor: colors.border,
        domain: rec.domain,
        evidenceGrade: rec.evidence_grade,
        parent: parentId,
        isPreempted: isPreempted ? "true" : "false",
        hasModifiers: (rec.modifier_count > 0) ? "true" : "false",
        modifierCount: rec.modifier_count,
        nodeWidth: 180,
        nodeHeight: 60,
        fontSize: 10,
      },
    });

    clusterRecs.get(rec.domain)?.push(rec.id);
  }

  // Add edges.
  for (const edge of filteredEdges) {
    const edgeId = `${edge.type}__${edge.source}__${edge.target}`;
    const isSuppressed = edge.type === "MODIFIES" && edge.suppressed_by_preemption;

    elements.push({
      data: {
        id: edgeId,
        source: edge.source,
        target: edge.target,
        edgeType: edge.type,
        lineColor: edge.type === "PREEMPTED_BY" ? "#991b1b" : "#d97706",
        edgePriority: edge.edge_priority,
        reason: edge.reason,
        nature: edge.nature,
        note: edge.note,
        suppressed: isSuppressed ? "true" : "false",
      },
    });
  }

  return { elements, clusterRecs };
}

/** Count edges by type from the full (unfiltered) response. */
export function countEdges(data: InteractionsResponse): {
  preemptions: number;
  modifiers: number;
  sharedEntities: number;
} {
  return {
    preemptions: data.edges.filter((e) => e.type === "PREEMPTED_BY").length,
    modifiers: data.edges.filter((e) => e.type === "MODIFIES").length,
    sharedEntities: data.shared_entities.length,
  };
}

/** Get the guideline-pair display string for an edge. */
export function edgePairLabel(
  edge: InteractionEdge,
  recs: InteractionsResponse["recommendations"],
): string {
  const sourceRec = recs.find((r) => r.id === edge.source);
  const targetRec = recs.find((r) => r.id === edge.target);
  const sourceDomain = sourceRec?.domain ?? "?";
  const targetDomain = targetRec?.domain ?? "?";
  return `${sourceDomain} → ${targetDomain}`;
}

/** Get unique guideline pairs from the edge set. */
export function guidelinePairs(
  data: InteractionsResponse,
): { label: string; domains: [string, string] }[] {
  const seen = new Set<string>();
  const pairs: { label: string; domains: [string, string] }[] = [];

  for (const edge of data.edges) {
    const sourceRec = data.recommendations.find((r) => r.id === edge.source);
    const targetRec = data.recommendations.find((r) => r.id === edge.target);
    if (!sourceRec?.domain || !targetRec?.domain) continue;

    const key = [sourceRec.domain, targetRec.domain].sort().join(":");
    if (seen.has(key)) continue;
    seen.add(key);

    const sorted = [sourceRec.domain, targetRec.domain].sort();
    pairs.push({
      label: `${sorted[0]} ↔ ${sorted[1]}`,
      domains: [sorted[0], sorted[1]],
    });
  }

  return pairs;
}
