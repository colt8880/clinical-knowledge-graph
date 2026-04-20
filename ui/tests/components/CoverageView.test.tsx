import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import CoverageView from "@/components/CoverageView";
import type { GuidelineMeta } from "@/lib/api/client";

afterEach(() => {
  cleanup();
});

const MOCK_GUIDELINE: GuidelineMeta = {
  id: "uspstf-statin-2022",
  domain: "USPSTF",
  title: "Statin Use for Primary Prevention",
  version: "2022-08-23",
  publication_date: "2022-08-23",
  citation_url: "https://example.com",
  rec_count: 3,
  coverage: {
    modeled: [
      { label: "Grade B", rec_id: "rec:b" },
      { label: "Grade C", rec_id: "rec:c" },
    ],
    deferred: ["pregnancy", "secondary prevention"],
    exit_only: ["age < 40", "age > 75"],
  },
  seed_hash: "abc",
  last_updated_in_graph: "2026-04-18",
};

describe("CoverageView", () => {
  it("renders the modeled recommendations table", () => {
    render(<CoverageView guideline={MOCK_GUIDELINE} />);
    expect(screen.getByTestId("modeled-table")).toBeDefined();
    expect(screen.getByText("Grade B")).toBeDefined();
    expect(screen.getByText("Grade C")).toBeDefined();
  });

  it("renders deferred areas", () => {
    render(<CoverageView guideline={MOCK_GUIDELINE} />);
    expect(screen.getByTestId("deferred-list")).toBeDefined();
    expect(screen.getByText("pregnancy")).toBeDefined();
    expect(screen.getByText("secondary prevention")).toBeDefined();
  });

  it("renders exit-only areas", () => {
    render(<CoverageView guideline={MOCK_GUIDELINE} />);
    expect(screen.getByTestId("exit-only-list")).toBeDefined();
    expect(screen.getByText("age < 40")).toBeDefined();
  });

  it("handles null coverage gracefully", () => {
    const noCoverage = { ...MOCK_GUIDELINE, coverage: null };
    render(<CoverageView guideline={noCoverage} />);
    expect(screen.getByText(/No coverage data/)).toBeDefined();
  });
});
