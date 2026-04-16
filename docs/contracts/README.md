# Contracts

Machine-readable shapes (JSON Schema, OpenAPI, YAML catalogs). Source of truth for shape.

Machine-readable artifacts that pair with the prose specs in `docs/specs/`. When prose and a contract diverge, **the prose spec is the source of truth for rationale and semantics; the contract is the source of truth for shape**. If they disagree, file an ADR and update both.

| Contract | Paired spec | Purpose |
|---|---|---|
| `predicate-catalog.yaml` | `specs/predicate-dsl.md` | Enumerates every predicate with args, types, default missing-data policy. Consumed by the evaluator, the ingestion validator, and the review-tool renderer. |
| `predicate-catalog.schema.json` | (meta-schema for the catalog) | JSON Schema that defines the shape of `predicate-catalog.yaml` itself. |
| `patient-context.schema.json` | `specs/patient-context.md` | JSON Schema for `PatientContext`. Consumed by the adapter validator and by eval fixture validation. |

## How contracts version

Contracts do not carry inline version strings. Their version is the git tag of the repo at the point of use (see `docs/VERSIONS.md`). A change to a contract without a spec tag bump is an "unreleased" edit; `VERSIONS.md` is the pin of which tag the current implementation targets.

## When to edit a contract vs. the spec

- Editing the shape of a field or a predicate signature: edit both. Prose first (so the rationale is clear), then the contract to match. One commit.
- Editing rationale, open questions, or examples that don't change shape: edit the prose spec only. No contract change.
- Adding a new predicate or field: edit both. Update the backlog in `docs/reference/build-status.md` if this opens new implementation work.

## Validation

Validation runs in CI via `.github/workflows/validate.yml`:
- `scripts/validate_contracts.py` validates `predicate-catalog.yaml` against `predicate-catalog.schema.json` and confirms `patient-context.schema.json` is a well-formed Draft 2020-12 JSON Schema.
- `scripts/check_spec_contract_sync.py` asserts every name in the catalog (composites, value_filters, predicates) appears as a backticked identifier in `specs/predicate-dsl.md`.
- `patient-context.schema.json` will also be used to validate eval fixture `patient` blocks once `/evals` lands.

Run locally: `pip install pyyaml jsonschema && python3 scripts/validate_contracts.py && python3 scripts/check_spec_contract_sync.py`.
