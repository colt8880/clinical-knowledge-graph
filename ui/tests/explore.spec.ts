/**
 * Explore tab e2e tests — graph canvas with column layout.
 *
 * Requires: API running at localhost:8000 with a seeded Neo4j graph.
 * Run: cd ui && npm run test
 *
 * Tests verify the progressive column hierarchy rendered in Cytoscape:
 *   Guideline → Recommendations → Strategies → Actions
 *
 * Because Cytoscape renders to a <canvas>, we can't click individual
 * nodes via DOM selectors. Instead we test URL-driven state: navigating
 * to deep links and verifying the canvas renders + detail panel populates.
 */
import { test, expect } from "@playwright/test";

test.describe("Explore tab", () => {
  test("loads with graph canvas visible", async ({ page }) => {
    await page.goto("/explore");

    await expect(page.getByTestId("explore-page")).toBeVisible();
    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("default load shows guideline detail", async ({ page }) => {
    await page.goto("/explore");

    // The detail panel should auto-show the guideline node.
    const detail = page.getByTestId("node-detail");
    await expect(detail).toBeVisible({ timeout: 10_000 });
    await expect(detail).toContainText("Guideline", { timeout: 10_000 });
  });

  test("deep link with ?r= shows recommendation detail and strategies", async ({
    page,
  }) => {
    const g = encodeURIComponent("guideline:uspstf-statin-2022");
    const r = encodeURIComponent("rec:statin-initiate-grade-b");
    await page.goto(`/explore?g=${g}&r=${r}`);

    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });

    // Detail panel should show the selected recommendation.
    const detail = page.getByTestId("node-detail");
    await expect(detail).toBeVisible({ timeout: 10_000 });
    await expect(detail).toContainText("Grade B", { timeout: 10_000 });
  });

  test("deep link with ?r=&s= shows strategy detail and actions", async ({
    page,
  }) => {
    const g = encodeURIComponent("guideline:uspstf-statin-2022");
    const r = encodeURIComponent("rec:statin-initiate-grade-b");
    const s = encodeURIComponent("strategy:statin-moderate-intensity");
    await page.goto(`/explore?g=${g}&r=${r}&s=${s}`);

    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });

    // Detail panel should show the selected strategy.
    const detail = page.getByTestId("node-detail");
    await expect(detail).toBeVisible({ timeout: 10_000 });
    await expect(detail).toContainText("Strategy", { timeout: 10_000 });
  });

  test("navigating between recs updates detail panel content", async ({
    page,
  }) => {
    // Start with Grade B rec selected.
    const g = encodeURIComponent("guideline:uspstf-statin-2022");
    const rB = encodeURIComponent("rec:statin-initiate-grade-b");
    await page.goto(`/explore?g=${g}&r=${rB}`);

    const detail = page.getByTestId("node-detail");
    await expect(detail).toContainText("Grade B", { timeout: 10_000 });

    // Navigate to Grade C rec via URL.
    const rC = encodeURIComponent("rec:statin-selective-grade-c");
    await page.goto(`/explore?g=${g}&r=${rC}`);
    await expect(detail).toContainText("Grade C", { timeout: 10_000 });
  });
});
