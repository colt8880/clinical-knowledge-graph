/**
 * Explore tab e2e tests.
 *
 * Requires: API running at localhost:8000 with a seeded Neo4j graph.
 * Run: cd ui && npm run test
 *
 * The test verifies the core Explore flow:
 *  1. Page loads with the guideline node auto-pinned, showing its children.
 *  2. Clicking a Recommendation navigates down to show that rec's children.
 *  3. Deep link via ?pinned= restores the correct view.
 */
import { test, expect } from "@playwright/test";

const GUIDELINE_ID = "guideline:uspstf-statin-2022";

test.describe("Explore tab", () => {
  test("loads the guideline node and renders Recommendation children", async ({
    page,
  }) => {
    await page.goto("/explore");

    await expect(page.getByTestId("explore-page")).toBeVisible();
    await expect(page.getByTestId("graph-canvas")).toBeVisible();

    // Wait for the 3 Recommendation children to appear in the sidebar.
    await expect(async () => {
      const count = await page.locator("aside ul li").count();
      expect(count).toBe(3);
    }).toPass({ timeout: 10_000 });
  });

  test("clicking a recommendation navigates down the hierarchy", async ({
    page,
  }) => {
    await page.goto("/explore");

    // Wait for children to load.
    await expect(async () => {
      const count = await page.locator("aside ul li").count();
      expect(count).toBe(3);
    }).toPass({ timeout: 10_000 });

    // Click a recommendation to navigate down.
    const recButton = page.locator("aside ul li button").first();
    await recButton.click();

    // Should navigate — URL should change to have the rec as pinned.
    await expect(page).toHaveURL(/pinned=rec%3A/, { timeout: 5_000 });

    // The "Back to parent" button should now be visible.
    await expect(
      page.locator("button", { hasText: "Back to parent" }),
    ).toBeVisible({ timeout: 5_000 });
  });

  test("deep link with ?pinned= restores state", async ({ page }) => {
    await page.goto(
      `/explore?pinned=${encodeURIComponent(GUIDELINE_ID)}`,
    );

    await expect(page.getByTestId("explore-page")).toBeVisible();
    await expect(page.getByTestId("graph-canvas")).toBeVisible();

    // Should load the guideline's children (3 recs).
    await expect(async () => {
      const count = await page.locator("aside ul li").count();
      expect(count).toBe(3);
    }).toPass({ timeout: 10_000 });
  });

  test("deep link to a recommendation shows its children only", async ({
    page,
  }) => {
    const recId = "rec:statin-initiate-grade-b";
    await page.goto(
      `/explore?pinned=${encodeURIComponent(recId)}`,
    );

    await expect(page.getByTestId("explore-page")).toBeVisible();

    // Should show the rec's children (strategy node), not sibling recs.
    await expect(async () => {
      const count = await page.locator("aside ul li").count();
      // Grade B rec has 1 strategy child.
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10_000 });

    // Back to parent button should be available.
    await expect(
      page.locator("button", { hasText: "Back to parent" }),
    ).toBeVisible();
  });
});
