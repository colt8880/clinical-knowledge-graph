import { describe, it, expect } from "vitest";
import { extractScopedSubgraph } from "@/lib/explore/scopedSubgraph";
import type { ForestSubgraph, ForestNode, GraphEdge } from "@/lib/api/client";

function makeNode(id: string, domain: string | null, labels: string[]): ForestNode {
  return {
    id,
    labels,
    properties: {},
    domain: domain as ForestNode["domain"],
  };
}

function makeEdge(id: string, start: string, end: string, type: string): GraphEdge {
  return { id, start, end, type, properties: {} };
}

describe("extractScopedSubgraph", () => {
  const forest: ForestSubgraph = {
    nodes: [
      makeNode("guideline:uspstf-statin-2022", "USPSTF", ["Guideline", "USPSTF"]),
      makeNode("rec:statin-initiate-grade-b", "USPSTF", ["Recommendation", "USPSTF"]),
      makeNode("strategy:statin-moderate-intensity", "USPSTF", ["Strategy", "USPSTF"]),
      makeNode("med:atorvastatin", null, ["Medication"]),
      makeNode("med:rosuvastatin", null, ["Medication"]),
      makeNode("guideline:acc-aha-cholesterol-2018", "ACC_AHA", ["Guideline", "ACC_AHA"]),
      makeNode("rec:accaha-statin-secondary-prevention", "ACC_AHA", ["Recommendation", "ACC_AHA"]),
      makeNode("med:simvastatin", null, ["Medication"]),
    ],
    edges: [
      makeEdge("e1", "rec:statin-initiate-grade-b", "guideline:uspstf-statin-2022", "FROM_GUIDELINE"),
      makeEdge("e2", "rec:statin-initiate-grade-b", "strategy:statin-moderate-intensity", "OFFERS_STRATEGY"),
      makeEdge("e3", "strategy:statin-moderate-intensity", "med:atorvastatin", "INCLUDES_ACTION"),
      makeEdge("e4", "strategy:statin-moderate-intensity", "med:rosuvastatin", "INCLUDES_ACTION"),
      makeEdge("e5", "rec:accaha-statin-secondary-prevention", "guideline:acc-aha-cholesterol-2018", "FROM_GUIDELINE"),
      makeEdge("e6", "rec:accaha-statin-secondary-prevention", "med:simvastatin", "INCLUDES_ACTION"),
      // Cross-guideline edge.
      makeEdge("e7", "rec:statin-initiate-grade-b", "rec:accaha-statin-secondary-prevention", "PREEMPTED_BY"),
    ],
  };

  it("includes only USPSTF nodes and their shared entities", () => {
    const result = extractScopedSubgraph(forest, "uspstf-statin-2022");
    const nodeIds = result.nodes.map((n) => n.id);

    expect(nodeIds).toContain("guideline:uspstf-statin-2022");
    expect(nodeIds).toContain("rec:statin-initiate-grade-b");
    expect(nodeIds).toContain("strategy:statin-moderate-intensity");
    expect(nodeIds).toContain("med:atorvastatin");
    expect(nodeIds).toContain("med:rosuvastatin");
    // ACC/AHA nodes excluded.
    expect(nodeIds).not.toContain("guideline:acc-aha-cholesterol-2018");
    expect(nodeIds).not.toContain("rec:accaha-statin-secondary-prevention");
  });

  it("excludes shared entities only referenced by other guidelines", () => {
    const result = extractScopedSubgraph(forest, "uspstf-statin-2022");
    const nodeIds = result.nodes.map((n) => n.id);
    // med:simvastatin is only connected to ACC/AHA via INCLUDES_ACTION.
    expect(nodeIds).not.toContain("med:simvastatin");
  });

  it("drops cross-guideline edges", () => {
    const result = extractScopedSubgraph(forest, "uspstf-statin-2022");
    const edgeTypes = result.edges.map((e) => e.type);
    expect(edgeTypes).not.toContain("PREEMPTED_BY");
  });

  it("includes intra-guideline edges", () => {
    const result = extractScopedSubgraph(forest, "uspstf-statin-2022");
    const edgeIds = result.edges.map((e) => e.id);
    expect(edgeIds).toContain("e1"); // FROM_GUIDELINE
    expect(edgeIds).toContain("e2"); // OFFERS_STRATEGY
    expect(edgeIds).toContain("e3"); // INCLUDES_ACTION to atorvastatin
  });

  it("identifies nodes with cross-guideline interactions", () => {
    const result = extractScopedSubgraph(forest, "uspstf-statin-2022");
    expect(result.crossGuidelineNodeIds.has("rec:statin-initiate-grade-b")).toBe(true);
  });

  it("returns empty for unknown slug", () => {
    const result = extractScopedSubgraph(forest, "nonexistent");
    expect(result.nodes).toHaveLength(0);
    expect(result.edges).toHaveLength(0);
  });
});
