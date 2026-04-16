/**
 * Eval tab e2e tests — fixture picker, trace stepper, recommendation strip.
 *
 * Requires: API running at localhost:8000 with a seeded Neo4j graph.
 * Run: cd ui && npm run test
 *
 * Tests verify the Eval tab workflow: select fixture → run → step through
 * trace events → verify terminal event and recommendation strip.
 */
import { test, expect } from "@playwright/test";

test.describe("Eval tab", () => {
  test("loads with fixture picker and run button", async ({ page }) => {
    await page.goto("/eval");

    await expect(page.getByTestId("eval-page")).toBeVisible();
    await expect(page.getByTestId("fixture-picker")).toBeVisible();
    await expect(page.getByTestId("run-button")).toBeVisible();
    await expect(page.getByTestId("run-button")).toBeDisabled();
  });

  test("fixture 01: run, step through, terminal event is Grade B due", async ({
    page,
  }) => {
    await page.goto("/eval");

    // Select fixture 01.
    await page.getByTestId("fixture-picker").selectOption("01-high-risk-55m-smoker");
    await expect(page.getByTestId("run-button")).toBeEnabled();

    // Run the evaluation.
    await page.getByTestId("run-button").click();

    // Wait for trace to load — stepper and event list appear.
    await expect(page.getByTestId("trace-stepper")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("trace-event-list")).toBeVisible();

    // The trace event list should contain the Grade B recommendation_emitted.
    const eventList = page.getByTestId("trace-event-list");
    await expect(eventList).toContainText("Recommendation Emitted", {
      timeout: 5_000,
    });
    await expect(eventList).toContainText("rec:statin-initiate-grade-b");

    // Click the recommendation_emitted event for Grade B in the list.
    const gradeB = eventList.getByText("rec:statin-initiate-grade-b → due");
    await gradeB.click();

    // The event detail panel should show the recommendation details.
    const detail = page.getByTestId("event-detail");
    await expect(detail).toBeVisible();
    await expect(detail).toContainText("Recommendation Emitted");
    await expect(detail).toContainText("rec:statin-initiate-grade-b");
    await expect(detail).toContainText("due");

    // Recommendation strip should show Grade B.
    const strip = page.getByTestId("recommendation-strip");
    await expect(strip).toBeVisible();
    await expect(strip).toContainText("B");
    await expect(strip).toContainText("due");

    // Verify keyboard navigation works: step forward and back.
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("ArrowLeft");
    await expect(detail).toContainText("Recommendation Emitted");
  });

  test("fixture 03: too-young exit, no recommendations", async ({ page }) => {
    await page.goto("/eval");

    await page.getByTestId("fixture-picker").selectOption("03-too-young-35m");
    await page.getByTestId("run-button").click();

    await expect(page.getByTestId("trace-stepper")).toBeVisible({
      timeout: 15_000,
    });

    // The trace should contain an exit_condition_triggered event.
    const eventList = page.getByTestId("trace-event-list");
    await expect(eventList).toContainText("Exit Condition Triggered", {
      timeout: 5_000,
    });
    await expect(eventList).toContainText("out_of_scope_age_below_range");
  });

  test("URL state round-trips case and seq", async ({ page }) => {
    await page.goto("/eval");

    // Select and run fixture 01.
    await page.getByTestId("fixture-picker").selectOption("01-high-risk-55m-smoker");
    await page.getByTestId("run-button").click();

    await expect(page.getByTestId("trace-stepper")).toBeVisible({
      timeout: 15_000,
    });

    // Step forward a couple times.
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("ArrowRight");

    // URL should contain case and seq params.
    await page.waitForURL(/case=01-high-risk-55m-smoker/);
    const url = page.url();
    expect(url).toContain("case=01-high-risk-55m-smoker");
    expect(url).toMatch(/seq=\d+/);
  });
});
