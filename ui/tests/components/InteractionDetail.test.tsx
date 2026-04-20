import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import InteractionDetail from "@/components/InteractionDetail";
import type { InteractionsResponse } from "@/lib/api/client";

// Mock next/link.
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

afterEach(() => {
  cleanup();
});

const MOCK_DATA: InteractionsResponse = {
  guidelines: [
    { id: "uspstf-statin-2022", domain: "USPSTF", title: "USPSTF" },
    { id: "acc-aha-cholesterol-2018", domain: "ACC/AHA", title: "ACC/AHA" },
    { id: "kdigo-ckd-2024", domain: "KDIGO", title: "KDIGO" },
  ],
  recommendations: [
    {
      id: "rec:statin-initiate-grade-b",
      title: "Grade B Initiation",
      domain: "USPSTF",
      evidence_grade: "B",
      has_preemption_in: false,
      has_preemption_out: true,
      modifier_count: 1,
    },
    {
      id: "rec:accaha-statin-diabetes",
      title: "Diabetes Statin",
      domain: "ACC/AHA",
      evidence_grade: null,
      has_preemption_in: true,
      has_preemption_out: false,
      modifier_count: 0,
    },
    {
      id: "rec:kdigo-statin-for-ckd",
      title: "CKD Statin",
      domain: "KDIGO",
      evidence_grade: null,
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
      target: "rec:statin-initiate-grade-b",
      nature: "intensity_reduction",
      note: "CKD context",
      suppressed_by_preemption: true,
    },
  ],
};

describe("InteractionDetail", () => {
  it("shows placeholder when nothing selected", () => {
    render(
      <InteractionDetail
        data={MOCK_DATA}
        selectedEdgeId={null}
        selectedNodeId={null}
      />,
    );

    expect(screen.getByText("Click an edge or node to view details.")).toBeDefined();
  });

  it("shows preemption detail when a PREEMPTED_BY edge is selected", () => {
    render(
      <InteractionDetail
        data={MOCK_DATA}
        selectedEdgeId="PREEMPTED_BY__rec:statin-initiate-grade-b__rec:accaha-statin-diabetes"
        selectedNodeId={null}
      />,
    );

    expect(screen.getByTestId("preemption-detail")).toBeDefined();
    expect(screen.getByText("Grade B Initiation")).toBeDefined();
    expect(screen.getByText("Diabetes Statin")).toBeDefined();
    expect(screen.getByTestId("edge-priority").textContent).toBe("200");
    expect(screen.getByText("ACC/AHA more specific")).toBeDefined();
  });

  it("shows modifier detail with suppression notice when selected", () => {
    render(
      <InteractionDetail
        data={MOCK_DATA}
        selectedEdgeId="MODIFIES__rec:kdigo-statin-for-ckd__rec:statin-initiate-grade-b"
        selectedNodeId={null}
      />,
    );

    expect(screen.getByTestId("modifier-detail")).toBeDefined();
    expect(screen.getByText("intensity_reduction")).toBeDefined();
    expect(screen.getByTestId("suppression-notice")).toBeDefined();
  });

  it("shows cluster detail when a cluster node is selected", () => {
    render(
      <InteractionDetail
        data={MOCK_DATA}
        selectedEdgeId={null}
        selectedNodeId="__interactions_cluster_uspstf"
      />,
    );

    expect(screen.getByTestId("cluster-detail")).toBeDefined();
  });

  it("shows rec detail with Open in Explore link when a rec is selected", () => {
    render(
      <InteractionDetail
        data={MOCK_DATA}
        selectedEdgeId={null}
        selectedNodeId="rec:statin-initiate-grade-b"
      />,
    );

    expect(screen.getByTestId("rec-detail")).toBeDefined();
    const exploreLinks = screen.getAllByTestId("explore-link");
    expect(exploreLinks.length).toBeGreaterThan(0);
    expect(exploreLinks[0].getAttribute("href")).toContain("/explore/uspstf-statin-2022");
  });
});
