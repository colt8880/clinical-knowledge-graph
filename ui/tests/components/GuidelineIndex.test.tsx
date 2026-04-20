import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import GuidelineIndex from "@/components/GuidelineIndex";
import type { GuidelineMeta } from "@/lib/api/client";

// Mock Next.js Link.
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

afterEach(() => {
  cleanup();
});

const MOCK_GUIDELINES: GuidelineMeta[] = [
  {
    id: "uspstf-statin-2022",
    domain: "USPSTF",
    title: "Statin Use for Primary Prevention",
    version: "2022-08-23",
    publication_date: "2022-08-23",
    citation_url: "https://example.com",
    rec_count: 3,
    coverage: {
      modeled: [{ label: "Grade B", rec_id: "rec:b" }],
      deferred: ["pregnancy"],
      exit_only: ["age < 40"],
    },
    seed_hash: "abc123",
    last_updated_in_graph: "2026-04-18",
  },
  {
    id: "acc-aha-cholesterol-2018",
    domain: "ACC/AHA",
    title: "Management of Blood Cholesterol",
    version: "2018-11-10",
    publication_date: "2018-11-10",
    citation_url: "https://example.com",
    rec_count: 4,
    coverage: {
      modeled: [{ label: "Secondary prevention", rec_id: "rec:sp" }],
      deferred: [],
      exit_only: [],
    },
    seed_hash: "def456",
    last_updated_in_graph: "2026-04-18",
  },
  {
    id: "kdigo-ckd-2024",
    domain: "KDIGO",
    title: "Evaluation and Management of CKD",
    version: "2024-03-14",
    publication_date: "2024-03-14",
    citation_url: "https://example.com",
    rec_count: 4,
    coverage: {
      modeled: [{ label: "CKD monitoring", rec_id: "rec:mon" }],
      deferred: ["dialysis"],
      exit_only: [],
    },
    seed_hash: "ghi789",
    last_updated_in_graph: "2026-04-18",
  },
];

describe("GuidelineIndex", () => {
  it("renders three guideline cards plus one all-guidelines card", () => {
    render(<GuidelineIndex guidelines={MOCK_GUIDELINES} />);

    expect(screen.getByTestId("guideline-card-uspstf-statin-2022")).toBeDefined();
    expect(screen.getByTestId("guideline-card-acc-aha-cholesterol-2018")).toBeDefined();
    expect(screen.getByTestId("guideline-card-kdigo-ckd-2024")).toBeDefined();
    expect(screen.getByTestId("guideline-card-all")).toBeDefined();
  });

  it("renders the index container", () => {
    render(<GuidelineIndex guidelines={MOCK_GUIDELINES} />);
    expect(screen.getByTestId("guideline-index")).toBeDefined();
  });

  it("all-guidelines card links to /explore/all", () => {
    render(<GuidelineIndex guidelines={MOCK_GUIDELINES} />);
    const allCard = screen.getByTestId("guideline-card-all");
    expect(allCard.getAttribute("href")).toBe("/explore/all");
  });
});
