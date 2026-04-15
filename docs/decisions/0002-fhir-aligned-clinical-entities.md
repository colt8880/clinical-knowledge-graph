# 0002. FHIR-aligned clinical entity layer

Status: Accepted
Date: 2026-04-14

## Context

Clinical entities in the graph (Condition, Observation, Medication, Procedure, etc.) need to match the shape of data the consuming agent will receive from an EHR at runtime. EHRs standardize on FHIR R4. Choosing a non-FHIR shape forces the adapter to do structural gymnastics and creates drift between the graph's notion of an "observation" and the source-system record.

## Decision

Clinical entity nodes use FHIR R4 resource structures wherever possible. Ontology codes (SNOMED CT, RxNorm, LOINC, ICD-10-CM) are carried as code lists on the nodes. The patient-context contract mirrors the same subsetted FHIR shape.

## Alternatives considered

- **OpenEHR archetypes.** Rejected: richer clinical semantics but adapter cost from major EHRs is high; FHIR wins on ubiquity.
- **A custom entity model keyed only on ontology codes.** Rejected: loses the reference structure (verification status, effective dates, components) that predicates depend on.

## Consequences

- The patient-context spec (`patient-context.md`) explicitly subsets FHIR rather than inventing shapes.
- When a FHIR convention is awkward for a use case, we document the departure (e.g., pregnancy as a top-level record, ADR 0008).
- Adapter work is bounded to "project subset of FHIR Bundle onto our contract" rather than full translation.

## Related

- `docs/specs/patient-context.md`
- `docs/specs/schema.md`
- ADR 0008 (pregnancy departure from FHIR Observation convention)
