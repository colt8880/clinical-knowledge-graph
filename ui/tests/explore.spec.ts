/**
 * Explore tab e2e tests — column browser navigation.
 *
 * Requires: API running at localhost:8000 with a seeded Neo4j graph.
 * Run: cd ui && npm run test
 *
 * Tests verify the Miller-column hierarchy:
 *   Guideline → Recommendations → Strategies → Actions
 */
import { test, expect } from "@playwright/test";

test.describe("Explore tab", () => {
  test("loads with Guidelines and Recommendations columns", async ({
    page,
  }) => {
    await page.goto("/explore");

    await expect(page.getByTestId("explore-page")).toBeVisible();
    await expect(page.getByTestId("column-browser")).toBeVisible();

    // Should have 2 columns initially: Guidelines and Recommendations.
    const columns = page.locator("[data-testid='column-browser'] > div");
    await expect(columns).toHaveCount(2, { timeout: 10_000 });

    // The Recommendations column should have 3 items (the 3 statin recs).
    const recItems = columns.nth(1).locator("ul li button");
    await expect(recItems).toHaveCount(3, { timeout: 10_000 });
  });

  test("clicking a recommendation adds a Strategies column", async ({
    page,
  }) => {
    await page.goto("/explore");

    // Wait for Recommendations to load.
    const columns = page.locator("[data-testid='column-browser'] > div");
    await expect(columns).toHaveCount(2, { timeout: 10_000 });

    // Click the first recommendation.
    const recButtons = columns.nth(1).locator("ul li button");
    await recButtons.first().click();

    // A third column (Strategies) should appear.
    await expect(columns).toHaveCount(3, { timeout: 10_000 });

    // URL should have ?g= and ?r= params.
    await expect(page).toHaveURL(/[?&]r=/, { timeout: 5_000 });
  });

  test("clicking a strategy adds an Actions column", async ({ page }) => {
    await page.goto("/explore");

    const columns = page.locator("[data-testid='column-browser'] > div");
    await expect(columns).toHaveCount(2, { timeout: 10_000 });

    // Click first rec.
    await columns.nth(1).locator("ul li button").first().click();
    await expect(columns).toHaveCount(3, { timeout: 10_000 });

    // Click the strategy.
    await columns.nth(2).locator("ul li button").first().click();

    // A fourth column (Actions) should appear with medications.
    await expect(columns).toHaveCount(4, { timeout: 10_000 });

    // URL should have ?g=, ?r=, and ?s= params.
    await expect(page).toHaveURL(/[?&]s=/, { timeout: 5_000 });
  });

  test("clicking a different rec resets deeper columns", async ({ page }) => {
    await page.goto("/explore");

    const columns = page.locator("[data-testid='column-browser'] > div");
    await expect(columns).toHaveCount(2, { timeout: 10_000 });

    // Select first rec → strategies column appears.
    const recButtons = columns.nth(1).locator("ul li button");
    await recButtons.first().click();
    await expect(columns).toHaveCount(3, { timeout: 10_000 });

    // Select strategy → actions column appears.
    await columns.nth(2).locator("ul li button").first().click();
    await expect(columns).toHaveCount(4, { timeout: 10_000 });

    // Now click a different rec — should reset to 3 columns.
    await recButtons.nth(1).click();
    await expect(columns).toHaveCount(3, { timeout: 10_000 });
  });

  test("deep link restores column state", async ({ page }) => {
    const g = encodeURIComponent("guideline:uspstf-statin-2022");
    const r = encodeURIComponent("rec:statin-initiate-grade-b");
    await page.goto(`/explore?g=${g}&r=${r}`);

    await expect(page.getByTestId("explore-page")).toBeVisible();

    // Should show 3 columns (Guideline, Recommendations, Strategies).
    const columns = page.locator("[data-testid='column-browser'] > div");
    await expect(columns).toHaveCount(3, { timeout: 10_000 });

    // The detail panel should be visible.
    await expect(page.getByTestId("node-detail")).toBeVisible();
  });

  test("clicking a node shows its details in the panel", async ({ page }) => {
    await page.goto("/explore");

    const columns = page.locator("[data-testid='column-browser'] > div");
    await expect(columns).toHaveCount(2, { timeout: 10_000 });

    // Click a recommendation.
    await columns.nth(1).locator("ul li button").first().click();

    // Detail panel should show node info.
    const detail = page.getByTestId("node-detail");
    await expect(detail).toBeVisible({ timeout: 5_000 });
    await expect(detail).toContainText("Recommendation", { timeout: 5_000 });
  });
});
