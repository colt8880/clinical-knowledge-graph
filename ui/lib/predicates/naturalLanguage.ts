/**
 * Predicate tree → natural-language string.
 *
 * Catalog-driven: reads nl_template from the predicate catalog.
 * Falls back to raw predicate_name(args) for unknown predicates.
 */

/** NL templates keyed by predicate name. Sourced from predicate-catalog.yaml. */
const NL_TEMPLATES: Record<string, string> = {
  age_between: "Patient is age {min}–{max}",
  age_greater_than_or_equal: "Patient is age ≥ {value}",
  age_less_than: "Patient is age < {value}",
  administrative_sex_is: "Administrative sex is {value}",
  has_ancestry_matching: "Has ancestry matching {populations}",
  has_condition_history: "Has history of {codes}",
  has_active_condition: "Has active {codes}",
  smoking_status_is: "Smoking status is {values}",
  most_recent_observation_value:
    "Most recent {code} {comparator} {threshold} {unit} (within {window})",
  has_medication_active: "Has active medication {codes}",
  risk_score_compares: "10-year ASCVD risk {comparator} {threshold}%",
};

/** Comparator display mapping. */
const COMPARATOR_DISPLAY: Record<string, string> = {
  eq: "=",
  ne: "≠",
  gt: ">",
  lt: "<",
  gte: "≥",
  lte: "≤",
};

/** Format a code ID for display (strip prefix, humanize). */
function formatCode(code: string): string {
  // "cond:ascvd-established" → "ascvd-established"
  // "med:atorvastatin" → "atorvastatin"
  // "obs:ldl-cholesterol" → "ldl-cholesterol"
  const stripped = code.replace(/^(cond|med|obs|proc):/, "");
  return stripped.replace(/-/g, " ");
}

function formatValue(key: string, value: unknown): string {
  if (key === "comparator" && typeof value === "string") {
    return COMPARATOR_DISPLAY[value] ?? value;
  }
  if (key === "codes" && Array.isArray(value)) {
    return value.map((c) => formatCode(String(c))).join(", ");
  }
  if (key === "values" && Array.isArray(value)) {
    return value.map(String).join(", ");
  }
  if (key === "populations" && Array.isArray(value)) {
    return value.map(String).join(", ");
  }
  if (key === "code" && typeof value === "string") {
    return formatCode(value);
  }
  if (typeof value === "number") {
    return String(value);
  }
  return String(value);
}

function renderTemplate(template: string, args: Record<string, unknown>): string {
  return template.replace(/\{(\w+)\}/g, (_, key) => {
    if (key in args) {
      return formatValue(key, args[key]);
    }
    return `{${key}}`;
  });
}

interface PredicateNode {
  [key: string]: unknown;
}

const COMPOSITE_LABELS: Record<string, string> = {
  all_of: "AND",
  any_of: "OR",
  none_of: "NOT",
};

/**
 * Convert a predicate tree to a natural-language string.
 *
 * Composite operators (all_of, any_of, none_of) join children with
 * AND / OR / NOT. Leaf predicates use nl_template from the catalog.
 * Unknown predicates fall back to name(args) and log a warning.
 */
export function predicateToNaturalLanguage(
  node: PredicateNode,
  depth: number = 0,
): string {
  const parts: string[] = [];

  for (const [key, value] of Object.entries(node)) {
    // Composite operator.
    if (key in COMPOSITE_LABELS && Array.isArray(value)) {
      const label = COMPOSITE_LABELS[key];
      const children = (value as PredicateNode[]).map((child) =>
        predicateToNaturalLanguage(child, depth + 1),
      );

      if (key === "none_of") {
        // "NOT (child1 OR child2)"
        if (children.length === 1) {
          parts.push(`NOT ${children[0]}`);
        } else {
          parts.push(`NOT (${children.join(" OR ")})`);
        }
      } else {
        const joiner = ` ${label} `;
        const joined = children.join(joiner);
        // Parenthesize nested composites.
        if (depth > 0 && children.length > 1) {
          parts.push(`(${joined})`);
        } else {
          parts.push(joined);
        }
      }
      continue;
    }

    // Leaf predicate: key is the predicate name, value is its args object.
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      const template = NL_TEMPLATES[key];
      if (template) {
        parts.push(renderTemplate(template, value as Record<string, unknown>));
      } else {
        // Fallback: raw predicate name + args.
        if (typeof console !== "undefined") {
          console.warn(
            `[NL] No template for predicate "${key}", falling back to raw rendering`,
          );
        }
        const args = Object.entries(value as Record<string, unknown>)
          .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
          .join(", ");
        parts.push(`${key}(${args})`);
      }
    }
  }

  return parts.join(" AND ");
}
