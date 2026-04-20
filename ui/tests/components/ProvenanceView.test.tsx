import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import ProvenanceView from "@/components/ProvenanceView";
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
  citation_url: "https://www.example.com/guideline",
  rec_count: 3,
  coverage: null,
  seed_hash: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  last_updated_in_graph: "2026-04-18",
};

describe("ProvenanceView", () => {
  it("renders the provenance panel", () => {
    render(<ProvenanceView guideline={MOCK_GUIDELINE} />);
    expect(screen.getByTestId("provenance-view")).toBeDefined();
  });

  it("displays the citation URL as a link", () => {
    render(<ProvenanceView guideline={MOCK_GUIDELINE} />);
    const link = screen.getByTestId("citation-url");
    expect(link.getAttribute("href")).toBe("https://www.example.com/guideline");
  });

  it("displays the seed hash", () => {
    render(<ProvenanceView guideline={MOCK_GUIDELINE} />);
    const hash = screen.getByTestId("seed-hash");
    expect(hash.textContent).toContain("a1b2c3d4");
  });

  it("displays version and publication date", () => {
    render(<ProvenanceView guideline={MOCK_GUIDELINE} />);
    const cells = screen.getAllByText("2022-08-23");
    // Version and publication_date both show "2022-08-23".
    expect(cells.length).toBeGreaterThanOrEqual(2);
  });
});
