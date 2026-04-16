# PatientContext

**v0 scope (ADR 0013, 0014): USPSTF statin primary prevention.** Only fields exercised by the statin model and the 5 v0 patient fixtures are included. Historical fields (pregnancy, family history, genetic findings, screening instruments, etc.) that were previously specified for broader domains are retained in the schema pattern and can re-enter scope when new guidelines land. Contract source of truth: `docs/contracts/patient-context.schema.json`.

## Purpose

`PatientContext` is the single input shape the evaluator consumes. It is:
- **Patient-scoped**: one patient per request. No multi-patient batching in v0.
- **Deterministic-friendly**: every field has an explicit `effective_date` or `as_of` so recomputing with the same context produces the same trace.
- **Adapter-owned**: the EHR adapter (outside this repo) is responsible for normalizing EHR data into this shape. The evaluator never calls back into an EHR.

## Top-level shape

```
{
  evaluation_time: ISO 8601 date-time     // REQUIRED. Anchors all time-relative predicates.
  patient: Demographics                    // REQUIRED.
  conditions: Condition[]                  // default []
  observations: Observation[]              // default []
  medications: Medication[]                // default []
  social_history: SocialHistory            // optional
  risk_scores: { [name: string]: RiskScore } // optional; pre-computed scores
  completeness: Completeness               // optional; declares adapter data coverage
  policy_overrides: PolicyOverrides        // optional; per-predicate missing-data policy
}
```

## Demographics

| Field | Type | Notes |
|---|---|---|
| `date_of_birth` | date | REQUIRED. Age derived at `evaluation_time`. |
| `administrative_sex` | enum(male,female,other,unknown) | REQUIRED. |
| `sex_assigned_at_birth` | enum(male,female,intersex,unknown) | Optional. Not used by statin guideline. |
| `ancestry` | string[] | Tokens from the ancestry-population registry. **Required for Pooled Cohort ASCVD: `black` vs. non-`black` materially changes the risk estimate.** Absent ancestry → evaluator treats as non-Black (ASCVD calculator default) and emits a trace event noting the imputation. |

## Condition

```
{
  id: string                               // stable identifier from the source record
  codes: CodeReference[]                   // at least one
  clinical_status: enum(active, recurrence, remission, resolved, inactive)
  verification_status: enum(confirmed, unconfirmed, refuted, entered-in-error)
  onset_date: date                         // optional
  abatement_date: date                     // optional
}
```

Statin-relevant conditions the v0 model reads:
- Atherosclerotic cardiovascular disease (prior MI, stroke, PAD, established CAD) — exclusion (secondary prevention).
- Diabetes mellitus (type 1 or type 2) — counts as a CVD risk factor AND a required ASCVD input.
- Essential hypertension — counts as a CVD risk factor (regardless of treatment status).
- Hyperlipidemia / dyslipidemia (as a diagnosed condition) — counts as a CVD risk factor.
- Familial hypercholesterolemia — exclusion (separate pathway).

## Observation

```
{
  id: string
  codes: CodeReference[]                   // at least one
  status: enum(registered, preliminary, final, amended, corrected, cancelled, entered-in-error)
  effective_date: ISO 8601 date-time
  value: Value                             // value_quantity | value_coded | value_string | value_boolean
  interpretation: CodeReference            // optional
  components: ObservationComponent[]       // for composite observations like BP (SBP + DBP components)
}
```

Statin-relevant observations:
- Total cholesterol (LOINC 2093-3), mg/dL
- HDL cholesterol (LOINC 2085-9), mg/dL
- LDL cholesterol (LOINC 2089-1 or calculated 13457-7), mg/dL — used for FH exclusion threshold
- Blood pressure panel (LOINC 85354-9) with components SBP (8480-6) and DBP (8462-4), mm[Hg]

Only observations with `status in {final, amended, corrected}` count toward eligibility. Use `most_recent_observation_value` to read the latest value within a window for ASCVD inputs.

## Medication

```
{
  id: string
  codes: CodeReference[]                   // RxNorm; class-level matching via graph node code list
  status: enum(active, on-hold, stopped, completed, entered-in-error)
  intent: enum(order, plan, proposal, instance-order)  // optional
  start_date: date                         // optional
  end_date: date                           // optional
}
```

Statin-relevant medication uses:
- Antihypertensive on-treatment flag for ASCVD Pooled Cohort input. An active medication matching any of the antihypertensive classes (ACE-I, ARB, beta-blocker, CCB, thiazide, etc.) resolves the `on_bp_treatment` input to `true`.
- Current statin therapy (any agent in the statin class) resolves the "already on statin" check which determines whether the Rec is `due` (initiate) vs. `up to date` (continue).

No `Dosage` or `CumulativeExposure` fields in v0. Statin intensity classification (moderate vs. high) is not read from patient dosage in v0 — the graph models moderate-intensity as a class-level strategy; any active statin satisfies it.

## SocialHistory

```
{
  tobacco: TobaccoUse
}
```

v0 reads `tobacco.status` only. Current smokers (`current`, `current_some_day`, `current_every_day`) contribute to both the CVD risk-factor check and the ASCVD Pooled Cohort input. Former and never smokers do not. Pack-years is not required for statins.

```
TobaccoUse {
  status: enum(never, former, current_some_day, current_every_day, current, unknown)
  as_of: date
}
```

## RiskScore

Pre-computed scores can be supplied by the adapter. For v0 the evaluator will compute `ascvd_10yr` itself when inputs are present, but a supplied score takes precedence (allows adapters to use an official EHR-side calculator). When supplied:

```
{
  name: "ascvd_10yr"
  value: number                            // percent, e.g., 12.4
  computed_date: date
  inputs_as_of: date                       // optional
  method_version: string                   // optional; tracks which PCE variant was used
}
```

If both a supplied score and all inputs are present, the evaluator uses the supplied score and emits a trace event noting that it did not recompute. If the supplied score is older than 1 year at `evaluation_time`, the evaluator recomputes from current inputs when available and flags the discrepancy.

## Completeness (optional)

```
{
  medications: enum(populated, sparse, not_available)
  social_history: enum(populated, sparse, not_available)
}
```

Drives the `fail_closed` vs. `fail_open` behavior of predicates whose input could be silently missing. Default when `completeness` is absent: treat all sections as `populated` (missing data means the patient genuinely has none).

## PolicyOverrides (optional)

Per-predicate override of the default missing-data policy defined in `predicate-catalog.yaml`:

```
{
  "smoking_status_is": { "on_missing": "fail_open" }
}
```

Used for adapter environments where a specific data stream is known to be unreliable. Overrides are echoed back in the response envelope for audit.

## Missing-data semantics (summary)

See `predicate-dsl.md` § Three-valued logic for the full treatment. For statins v0:
- Demographics required fields missing → request rejected by adapter validation, not evaluator.
- `ancestry` missing → evaluator treats as non-Black for ASCVD, emits trace note.
- `observations` missing values for ASCVD inputs → evaluator cannot compute the score; emits a `risk_score_unavailable` trace event and treats the risk-threshold predicate as fail_closed (no positive rec without a score).
- `medications` marked `not_available` in `completeness` → `has_medication_active` fails open (cannot confirm absence).

## Related docs

- Contract: `docs/contracts/patient-context.schema.json`
- Predicate DSL: `docs/specs/predicate-dsl.md`
- Predicate catalog: `docs/contracts/predicate-catalog.yaml`
- Statin model: `docs/reference/guidelines/statins.md`
