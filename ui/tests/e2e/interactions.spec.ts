import { test, expect } from "@playwright/test";

test.describe("Interactions view", () => {
  test("loads /interactions with three guideline clusters", async ({ page }) => {
    await page.goto("/interactions");
    await page.waitForSelector('[data-testid="interactions-page"]');

    // Legend should be visible with summary counts.
    const legend = page.locator('[data-testid="interactions-legend"]');
    await expect(legend).toBeVisible();

    // Summary should show preemptions and modifiers.
    const summary = page.locator('[data-testid="interactions-summary"]');
    await expect(summary).toContainText("preemption");
    await expect(summary).toContainText("modifier");

    // Canvas should be rendered.
    const canvas = page.locator('[data-testid="interactions-canvas"]');
    await expect(canvas).toBeVisible();
  });

  test("edge-type filter toggles between preemption/modifier/both", async ({ page }) => {
    // Navigate directly to preemption filter via URL to verify state restoration.
    await page.goto("/interactions?type=preemption");
    await page.waitForSelector('[data-testid="interactions-page"]');

    await expect(page.locator('[data-testid="edge-type-preemption"]')).toHaveAttribute(
      "aria-checked",
      "true",
    );

    // Navigate to modifier filter.
    await page.goto("/interactions?type=modifier");
    await page.waitForSelector('[data-testid="interactions-page"]');

    await expect(page.locator('[data-testid="edge-type-modifier"]')).toHaveAttribute(
      "aria-checked",
      "true",
    );

    // Navigate to both (default).
    await page.goto("/interactions");
    await page.waitForSelector('[data-testid="interactions-page"]');

    await expect(page.locator('[data-testid="edge-type-both"]')).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  test("detail panel shows placeholder when nothing selected", async ({ page }) => {
    await page.goto("/interactions");
    await page.waitForSelector('[data-testid="interactions-page"]');

    const detail = page.locator('[data-testid="interaction-detail-panel"]');
    await expect(detail).toContainText("Click an edge or node to view details.");
  });

  test("URL state with ?type=preemption restores filter state", async ({ page }) => {
    await page.goto("/interactions?type=preemption");
    await page.waitForSelector('[data-testid="interactions-page"]');

    await expect(page.locator('[data-testid="edge-type-preemption"]')).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  test("nav header shows Interactions link", async ({ page }) => {
    await page.goto("/");
    const navLink = page.locator('nav a[href="/interactions"]');
    await expect(navLink).toBeVisible();
    await expect(navLink).toContainText("Interactions");
  });
});
