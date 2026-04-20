/**
 * Guideline-first navigation e2e tests.
 *
 * Requires: API running at localhost:8000 with all three guideline seeds loaded.
 * Run: cd ui && npx playwright test tests/e2e/guideline-detail.spec.ts
 */
import { test, expect } from "@playwright/test";

test.describe("Guideline index", () => {
  test("renders three guideline cards plus one all-guidelines card", async ({ page }) => {
    await page.goto("/explore");

    await expect(page.getByTestId("guideline-index")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("guideline-card-uspstf-statin-2022")).toBeVisible();
    await expect(page.getByTestId("guideline-card-acc-aha-cholesterol-2018")).toBeVisible();
    await expect(page.getByTestId("guideline-card-kdigo-ckd-2024")).toBeVisible();
    await expect(page.getByTestId("guideline-card-all")).toBeVisible();
  });

  test("clicking USPSTF card navigates to detail page", async ({ page }) => {
    await page.goto("/explore");
    await expect(page.getByTestId("guideline-index")).toBeVisible({ timeout: 10_000 });

    await page.getByTestId("guideline-card-uspstf-statin-2022").click();
    await expect(page).toHaveURL(/\/explore\/uspstf-statin-2022/);
    await expect(page.getByTestId("guideline-detail-page")).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Guideline detail — USPSTF", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/explore/uspstf-statin-2022");
    await expect(page.getByTestId("guideline-detail-page")).toBeVisible({ timeout: 10_000 });
  });

  test("Logic tab renders by default with graph canvas", async ({ page }) => {
    await expect(page.getByTestId("tab-logic")).toHaveAttribute("aria-selected", "true");
    await expect(page.getByTestId("logic-view")).toBeVisible();
    await expect(page.getByTestId("graph-canvas")).toBeVisible({ timeout: 10_000 });
  });

  test("Coverage tab renders modeled and deferred lists", async ({ page }) => {
    await page.getByTestId("tab-coverage").click();
    await expect(page.getByTestId("coverage-view")).toBeVisible();
    await expect(page.getByTestId("modeled-table")).toBeVisible();
    await expect(page.getByTestId("deferred-list")).toBeVisible();
  });

  test("Provenance tab renders citation URL and version", async ({ page }) => {
    await page.getByTestId("tab-provenance").click();
    await expect(page.getByTestId("provenance-view")).toBeVisible();
    await expect(page.getByTestId("citation-url")).toBeVisible();
    await expect(page.getByTestId("seed-hash")).toBeVisible();
  });

  test("tab state is preserved in URL", async ({ page }) => {
    await page.getByTestId("tab-coverage").click();
    await expect(page).toHaveURL(/tab=coverage/);

    // Reload and verify tab state restored.
    await page.reload();
    await expect(page.getByTestId("coverage-view")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("tab-coverage")).toHaveAttribute("aria-selected", "true");
  });
});

test.describe("Whole-forest view preserved at /explore/all", () => {
  test("renders the whole-forest canvas with domain filter", async ({ page }) => {
    await page.goto("/explore/all");
    await expect(page.getByTestId("explore-all-page")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("graph-canvas")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("domain-filter")).toBeVisible();
  });

  test("domain filter params work on /explore/all", async ({ page }) => {
    await page.goto("/explore/all?domains=kdigo");
    await expect(page.getByTestId("explore-all-page")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("domain-chip-kdigo")).toHaveAttribute("aria-checked", "true");
  });
});

test.describe("Backward compatibility redirect", () => {
  test("old /explore?domains= redirects to /explore/all", async ({ page }) => {
    await page.goto("/explore?domains=kdigo");
    await page.waitForURL(/\/explore\/all/, { timeout: 5_000 });
    expect(page.url()).toContain("/explore/all");
  });
});
