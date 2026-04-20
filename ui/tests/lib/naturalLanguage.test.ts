import { describe, it, expect } from "vitest";
import { predicateToNaturalLanguage } from "@/lib/predicates/naturalLanguage";

describe("predicateToNaturalLanguage", () => {
  it("renders a single age_between predicate", () => {
    const result = predicateToNaturalLanguage({
      age_between: { min: 40, max: 75 },
    });
    expect(result).toBe("Patient is age 40–75");
  });

  it("renders a single risk_score_compares predicate", () => {
    const result = predicateToNaturalLanguage({
      risk_score_compares: { name: "ascvd_10yr", comparator: "gte", threshold: 10 },
    });
    expect(result).toBe("10-year ASCVD risk ≥ 10%");
  });

  it("renders all_of with AND", () => {
    const result = predicateToNaturalLanguage({
      all_of: [
        { age_between: { min: 40, max: 75 } },
        { risk_score_compares: { name: "ascvd_10yr", comparator: "gte", threshold: 10 } },
      ],
    });
    expect(result).toBe("Patient is age 40–75 AND 10-year ASCVD risk ≥ 10%");
  });

  it("renders any_of with OR", () => {
    const result = predicateToNaturalLanguage({
      any_of: [
        { has_active_condition: { codes: ["cond:dyslipidemia"] } },
        { has_active_condition: { codes: ["cond:diabetes"] } },
      ],
    });
    expect(result).toBe("Has active dyslipidemia OR Has active diabetes");
  });

  it("renders none_of as NOT", () => {
    const result = predicateToNaturalLanguage({
      none_of: [
        { has_condition_history: { codes: ["cond:ascvd-established"] } },
      ],
    });
    expect(result).toBe("NOT Has history of ascvd established");
  });

  it("renders none_of with multiple children as NOT (... OR ...)", () => {
    const result = predicateToNaturalLanguage({
      none_of: [
        { has_condition_history: { codes: ["cond:ascvd-established"] } },
        { has_condition_history: { codes: ["cond:familial-hypercholesterolemia"] } },
      ],
    });
    expect(result).toBe(
      "NOT (Has history of ascvd established OR Has history of familial hypercholesterolemia)",
    );
  });

  it("renders nested composites with parentheses", () => {
    const result = predicateToNaturalLanguage({
      all_of: [
        { age_between: { min: 40, max: 75 } },
        {
          any_of: [
            { has_active_condition: { codes: ["cond:dyslipidemia"] } },
            { has_active_condition: { codes: ["cond:diabetes"] } },
          ],
        },
      ],
    });
    expect(result).toBe(
      "Patient is age 40–75 AND (Has active dyslipidemia OR Has active diabetes)",
    );
  });

  it("renders observation comparison with human-readable comparator", () => {
    const result = predicateToNaturalLanguage({
      most_recent_observation_value: {
        code: "obs:ldl-cholesterol",
        window: "P2Y",
        comparator: "gte",
        threshold: 190,
        unit: "mg/dL",
      },
    });
    expect(result).toBe("Most recent ldl cholesterol ≥ 190 mg/dL (within P2Y)");
  });

  it("falls back to raw rendering for unknown predicates", () => {
    const result = predicateToNaturalLanguage({
      unknown_pred: { foo: "bar", baz: 42 },
    });
    expect(result).toBe('unknown_pred(foo: "bar", baz: 42)');
  });

  it("renders the full USPSTF Grade B eligibility tree", () => {
    const tree = {
      all_of: [
        { age_between: { min: 40, max: 75 } },
        {
          none_of: [
            { has_condition_history: { codes: ["cond:ascvd-established"] } },
            {
              most_recent_observation_value: {
                code: "obs:ldl-cholesterol",
                window: "P2Y",
                comparator: "gte",
                threshold: 190,
                unit: "mg/dL",
              },
            },
            { has_condition_history: { codes: ["cond:familial-hypercholesterolemia"] } },
          ],
        },
        {
          any_of: [
            { has_active_condition: { codes: ["cond:dyslipidemia"] } },
            { has_active_condition: { codes: ["cond:diabetes"] } },
            { has_active_condition: { codes: ["cond:hypertension"] } },
            { smoking_status_is: { values: ["current", "current_some_day", "current_every_day"] } },
          ],
        },
        { risk_score_compares: { name: "ascvd_10yr", comparator: "gte", threshold: 10 } },
      ],
    };
    const result = predicateToNaturalLanguage(tree);
    expect(result).toContain("Patient is age 40–75");
    expect(result).toContain("NOT (");
    expect(result).toContain("Has active dyslipidemia OR");
    expect(result).toContain("10-year ASCVD risk ≥ 10%");
  });
});
