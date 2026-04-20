import { test, expect } from "@playwright/test";

test.describe("Interactions view", () => {
  test("loads with empty canvas and guideline picker", async ({ page }) => {
    await page.goto("/interactions");
    await page.waitForSelector('[data-testid="interactions-page"]');

    // Legend should show guideline chips.
    const legend = page.locator('[data-testid="interactions-legend"]');
    await expect(legend).toBeVisible();
    await expect(page.locator('[data-testid="guideline-chip-USPSTF"]')).toBeVisible();
    await expect(page.locator('[data-testid="guideline-chip-ACC/AHA"]')).toBeVisible();
    await expect(page.locator('[data-testid="guideline-chip-KDIGO"]')).toBeVisible();

    // Canvas should show empty state prompt.
    await expect(page.locator("text=Select two or more guidelines")).toBeVisible();

    // Edge type filter should NOT be visible yet.
    await expect(page.locator('[data-testid="edge-type-both"]')).not.toBeVisible();
  });

  test("selecting two guidelines shows the canvas", async ({ page }) => {
    await page.goto("/interactions");
    await page.waitForSelector('[data-testid="interactions-page"]');

    // Select USPSTF and ACC/AHA.
    await page.click('[data-testid="guideline-chip-USPSTF"]');
    await page.click('[data-testid="guideline-chip-ACC/AHA"]');

    // Canvas should appear.
    await expect(page.locator('[data-testid="interactions-canvas"]')).toBeVisible();

    // Edge type filter should now be visible.
    await expect(page.locator('[data-testid="edge-type-both"]')).toBeVisible();

    // Summary should show counts.
    await expect(page.locator('[data-testid="interactions-summary"]')).toBeVisible();
  });

  test("edge-type filter restores from URL", async ({ page }) => {
    await page.goto("/interactions?type=preemption&guidelines=uspstf,acc-aha");
    await page.waitForSelector('[data-testid="interactions-page"]');

    await expect(page.locator('[data-testid="edge-type-preemption"]')).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  test("detail panel shows placeholder when nothing selected", async ({ page }) => {
    await page.goto("/interactions?guidelines=uspstf,acc-aha");
    await page.waitForSelector('[data-testid="interactions-page"]');

    const detail = page.locator('[data-testid="interaction-detail-panel"]');
    await expect(detail).toContainText("Click an edge or node to view details.");
  });

  test("nav header shows Interactions link", async ({ page }) => {
    await page.goto("/");
    const navLink = page.locator('nav a[href="/interactions"]');
    await expect(navLink).toBeVisible();
    await expect(navLink).toContainText("Interactions");
  });
});
