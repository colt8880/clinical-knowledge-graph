# 0007. Homegrown predicate DSL over CQL/FHIRPath

Status: Accepted
Date: 2026-04-14

## Context

`Recommendation.structured_eligibility`, `Recommendation.trigger_criteria`, and `PREEMPTED_BY.condition` need a language. The obvious candidates are CQL (HL7 Clinical Quality Language) and FHIRPath. Both are standards; both have implementations available. The alternative is a homegrown predicate DSL.

## Decision

A homegrown predicate DSL (`docs/specs/predicate-dsl.md`). Tree-shaped JSON/YAML with a small predicate catalog, three-valued logic, and explicit missing-data policy per predicate.

## Alternatives considered

- **CQL.** Rejected because (a) clinicians reviewing JSON in the review tool shouldn't have to learn CQL; (b) our v1 predicate set is ~35 predicates, smaller than the cost of a CQL subset implementation; (c) CQL can be added later as an alternative serialization over this DSL if a downstream integration demands it.
- **FHIRPath.** Rejected: strong for traversing FHIR resources but weak for composing eligibility logic across resource types with explicit missing-data semantics.
- **Raw Python / JavaScript.** Rejected: executable predicates mean untrusted-code execution paths and destroy reviewability.

## Consequences

- The evaluator is a bounded project: implement each predicate in the catalog, apply three-valued logic, return structured results.
- The predicate catalog is part of the evaluator version. Adding a predicate bumps the evaluator version.
- If a downstream partner requires CQL, we serialize to CQL from this DSL rather than migrating the DSL.

## Related

- `docs/specs/predicate-dsl.md`
- `docs/contracts/predicate-catalog.yaml`
