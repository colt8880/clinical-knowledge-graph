/**
 * Explore tab e2e tests — whole-forest Cytoscape canvas with domain filter.
 *
 * Requires: API running at localhost:8000 with all three guideline seeds loaded.
 * Run: cd ui && npm run test
 *
 * Because Cytoscape renders to a <canvas>, we can't click individual
 * nodes via DOM selectors. Instead we test URL-driven state, domain filter
 * interaction, and verify the canvas renders.
 */
import { test, expect } from "@playwright/test";

test.describe("Explore tab — whole-forest view", () => {
  test("loads with graph canvas and domain filter visible", async ({ page }) => {
    await page.goto("/explore");

    await expect(page.getByTestId("explore-page")).toBeVisible();
    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByTestId("domain-filter")).toBeVisible();
  });

  test("all three domain chips default to active", async ({ page }) => {
    await page.goto("/explore");

    await expect(page.getByTestId("domain-chip-uspstf")).toHaveAttribute(
      "aria-checked",
      "true",
      { timeout: 5_000 },
    );
    await expect(page.getByTestId("domain-chip-acc-aha")).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await expect(page.getByTestId("domain-chip-kdigo")).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  test("toggling a domain off updates URL", async ({ page }) => {
    await page.goto("/explore");

    // Wait for canvas to load.
    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });

    // Toggle KDIGO off.
    await page.getByTestId("domain-chip-kdigo").click();

    // URL should reflect the change.
    await expect(page).toHaveURL(/domains=/, { timeout: 5_000 });
    const url = new URL(page.url());
    const domains = url.searchParams.get("domains");
    expect(domains).not.toContain("kdigo");
    expect(domains).toContain("uspstf");
  });

  test("URL with single domain loads correctly", async ({ page }) => {
    await page.goto("/explore?domains=kdigo");

    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });

    // KDIGO chip should be active; others inactive.
    await expect(page.getByTestId("domain-chip-kdigo")).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await expect(page.getByTestId("domain-chip-uspstf")).toHaveAttribute(
      "aria-checked",
      "false",
    );
    await expect(page.getByTestId("domain-chip-acc-aha")).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  test("empty domains param still renders canvas (shared entities)", async ({
    page,
  }) => {
    await page.goto("/explore?domains=");

    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("legacy v0 URL loads without crash", async ({ page }) => {
    const g = encodeURIComponent("guideline:uspstf-statin-2022");
    const r = encodeURIComponent("rec:statin-initiate-grade-b");
    await page.goto(`/explore?g=${g}&r=${r}`);

    // Should load the full forest view (legacy params ignored).
    await expect(page.getByTestId("explore-page")).toBeVisible();
    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });

    // All domain chips should be active (default).
    await expect(page.getByTestId("domain-chip-uspstf")).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  test("focus param in URL shows detail panel", async ({ page }) => {
    await page.goto(
      "/explore?focus=" +
        encodeURIComponent("rec:statin-initiate-grade-b"),
    );

    await expect(page.getByTestId("graph-canvas")).toBeVisible({
      timeout: 10_000,
    });

    // Detail panel should show the focused node.
    const detail = page.getByTestId("node-detail");
    await expect(detail).toBeVisible({ timeout: 10_000 });
    await expect(detail).toContainText("Grade B", { timeout: 10_000 });
  });
});
