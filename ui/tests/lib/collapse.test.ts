import { describe, it, expect } from "vitest";
import {
  collapseInteractions,
  countEdges,
  guidelinePairs,
} from "@/lib/interactions/collapse";
import type { InteractionsResponse } from "@/lib/api/client";

const MOCK_DATA: InteractionsResponse = {
  guidelines: [
    { id: "uspstf-statin-2022", domain: "USPSTF", title: "USPSTF" },
    { id: "acc-aha-cholesterol-2018", domain: "ACC/AHA", title: "ACC/AHA" },
    { id: "kdigo-ckd-2024", domain: "KDIGO", title: "KDIGO" },
  ],
  recommendations: [
    {
      id: "rec:statin-initiate-grade-b",
      title: "Grade B",
      domain: "USPSTF",
      evidence_grade: "B",
      has_preemption_in: false,
      has_preemption_out: true,
      modifier_count: 1,
    },
    {
      id: "rec:accaha-statin-diabetes",
      title: "Diabetes statin",
      domain: "ACC/AHA",
      evidence_grade: null,
      has_preemption_in: true,
      has_preemption_out: false,
      modifier_count: 1,
    },
    {
      id: "rec:kdigo-statin-for-ckd",
      title: "CKD statin",
      domain: "KDIGO",
      evidence_grade: null,
      has_preemption_in: false,
      has_preemption_out: false,
      modifier_count: 0,
    },
    {
      id: "rec:no-cross-edges",
      title: "No cross edges",
      domain: "USPSTF",
      evidence_grade: "C",
      has_preemption_in: false,
      has_preemption_out: false,
      modifier_count: 0,
    },
  ],
  shared_entities: [],
  edges: [
    {
      type: "PREEMPTED_BY",
      source: "rec:statin-initiate-grade-b",
      target: "rec:accaha-statin-diabetes",
      edge_priority: 200,
      reason: "ACC/AHA more specific",
    },
    {
      type: "MODIFIES",
      source: "rec:kdigo-statin-for-ckd",
      target: "rec:accaha-statin-diabetes",
      nature: "intensity_reduction",
      note: "Reduce to moderate intensity in CKD",
      suppressed_by_preemption: false,
    },
    {
      type: "MODIFIES",
      source: "rec:kdigo-statin-for-ckd",
      target: "rec:statin-initiate-grade-b",
      nature: "intensity_reduction",
      note: "CKD context for USPSTF Grade B",
      suppressed_by_preemption: true,
    },
  ],
};

describe("collapseInteractions", () => {
  it("includes only recs with cross-edges, excludes recs without", () => {
    const { elements } = collapseInteractions(MOCK_DATA);
    const nodeIds = elements
      .filter((el) => el.data.nodeType === "Recommendation")
      .map((el) => el.data.id);

    expect(nodeIds).toContain("rec:statin-initiate-grade-b");
    expect(nodeIds).toContain("rec:accaha-statin-diabetes");
    expect(nodeIds).toContain("rec:kdigo-statin-for-ckd");
    expect(nodeIds).not.toContain("rec:no-cross-edges");
  });

  it("renders compound parents for all guideline domains even if no recs match", () => {
    const emptyData: InteractionsResponse = {
      ...MOCK_DATA,
      edges: [],
      recommendations: [],
    };
    const { elements } = collapseInteractions(emptyData);
    const clusters = elements.filter(
      (el) => el.data.nodeType === "__interactions_cluster",
    );
    expect(clusters.length).toBe(3);
    expect(clusters.map((c) => c.data.domain).sort()).toEqual(
      ["ACC/AHA", "KDIGO", "USPSTF"],
    );
  });

  it("filters to preemption edges only", () => {
    const { elements } = collapseInteractions(MOCK_DATA, "preemption");
    const edges = elements.filter((el) => el.data.edgeType != null);
    expect(edges.every((e) => e.data.edgeType === "PREEMPTED_BY")).toBe(true);
    expect(edges.length).toBe(1);
  });

  it("filters to modifier edges only", () => {
    const { elements } = collapseInteractions(MOCK_DATA, "modifier");
    const edges = elements.filter((el) => el.data.edgeType != null);
    expect(edges.every((e) => e.data.edgeType === "MODIFIES")).toBe(true);
    expect(edges.length).toBe(2);
  });

  it("drops edges when target guideline is filtered out", () => {
    const visibleGuidelines = new Set(["USPSTF", "KDIGO"]);
    const { elements } = collapseInteractions(MOCK_DATA, "both", visibleGuidelines);
    const edges = elements.filter((el) => el.data.edgeType != null);
    // Only the MODIFIES edge from KDIGO → USPSTF should remain.
    // The PREEMPTED_BY and the MODIFIES to ACC/AHA should be dropped.
    expect(edges.length).toBe(1);
    expect(edges[0].data.edgeType).toBe("MODIFIES");
    expect(edges[0].data.source).toBe("rec:kdigo-statin-for-ckd");
    expect(edges[0].data.target).toBe("rec:statin-initiate-grade-b");
  });

  it("marks suppressed modifier edges", () => {
    const { elements } = collapseInteractions(MOCK_DATA);
    const suppressedEdge = elements.find(
      (el) =>
        el.data.edgeType === "MODIFIES" &&
        el.data.target === "rec:statin-initiate-grade-b",
    );
    expect(suppressedEdge?.data.suppressed).toBe("true");
  });
});

describe("countEdges", () => {
  it("counts preemptions and modifiers", () => {
    const counts = countEdges(MOCK_DATA);
    expect(counts.preemptions).toBe(1);
    expect(counts.modifiers).toBe(2);
    expect(counts.sharedEntities).toBe(0);
  });
});

describe("guidelinePairs", () => {
  it("returns unique guideline pairs", () => {
    const pairs = guidelinePairs(MOCK_DATA);
    // USPSTF↔ACC/AHA (preemption), KDIGO↔ACC/AHA (modifier), KDIGO↔USPSTF (modifier)
    expect(pairs.length).toBe(3);
    const labels = pairs.map((p) => p.label).sort();
    expect(labels).toContain("ACC/AHA ↔ USPSTF");
    expect(labels).toContain("ACC/AHA ↔ KDIGO");
    expect(labels).toContain("KDIGO ↔ USPSTF");
  });
});
