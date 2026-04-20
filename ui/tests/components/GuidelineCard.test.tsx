import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import GuidelineCard from "@/components/GuidelineCard";
import type { GuidelineMeta } from "@/lib/api/client";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

afterEach(() => {
  cleanup();
});

const MOCK_GUIDELINE: GuidelineMeta = {
  id: "uspstf-statin-2022",
  domain: "USPSTF",
  title: "Statin Use for Primary Prevention of CVD",
  version: "2022-08-23",
  publication_date: "2022-08-23",
  citation_url: "https://example.com",
  rec_count: 3,
  coverage: {
    modeled: [
      { label: "Grade B", rec_id: "rec:b" },
      { label: "Grade C", rec_id: "rec:c" },
      { label: "Grade I", rec_id: "rec:i" },
    ],
    deferred: ["pregnancy", "secondary prevention"],
    exit_only: ["age < 40", "age > 75"],
  },
  seed_hash: "abc123",
  last_updated_in_graph: "2026-04-18",
};

describe("GuidelineCard", () => {
  it("renders guideline title and domain", () => {
    render(<GuidelineCard guideline={MOCK_GUIDELINE} />);
    expect(screen.getByText("Statin Use for Primary Prevention of CVD")).toBeDefined();
    expect(screen.getByText("USPSTF")).toBeDefined();
  });

  it("renders rec count", () => {
    render(<GuidelineCard guideline={MOCK_GUIDELINE} />);
    expect(screen.getByText(/3 recommendations/)).toBeDefined();
  });

  it("renders modeled count", () => {
    render(<GuidelineCard guideline={MOCK_GUIDELINE} />);
    expect(screen.getByText(/3 grades/)).toBeDefined();
  });

  it("renders deferred items", () => {
    render(<GuidelineCard guideline={MOCK_GUIDELINE} />);
    expect(screen.getByText(/pregnancy, secondary prevention/)).toBeDefined();
  });

  it("links to the guideline detail page", () => {
    render(<GuidelineCard guideline={MOCK_GUIDELINE} />);
    const card = screen.getByTestId("guideline-card-uspstf-statin-2022");
    expect(card.getAttribute("href")).toBe("/explore/uspstf-statin-2022");
  });
});
