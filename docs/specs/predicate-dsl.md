# Predicate DSL

**v0 scope banner (ADR 0013, 0014):** The active predicate surface for v0 is **the subset listed in `docs/contracts/predicate-catalog.yaml`**. That file is authoritative for which predicates the evaluator must implement. The prose below retains rationale and semantics for predicates used by the broader USPSTF corpus (pregnancy, immunizations, screening instruments, etc.); those predicates are **deferred**, not deleted — they re-enter the active catalog when a guideline that reads them is added.

**Status: v1.** A narrow, homegrown predicate language used in three places in the graph:

- `Recommendation.structured_eligibility` — who the rec applies to
- `Recommendation.trigger_criteria` — what event fires the rec (for non-default triggers; not used in v0)
- `PREEMPTED_BY.condition` — when preemption applies (not used in v0)

v1 design is general. v0 exercises only the statins subset: demographics (age, sex, ancestry), conditions (history/active), smoking status, most-recent observation value with threshold, medication active-status, and `risk_score_compares`. See the changelog at the bottom.

## Design posture

- **Clinician-reviewable over developer-convenient.** The DSL renders as English in the review tool with minimal transformation. A clinician skimming a Rec's JSON should be able to read off the eligibility rule without learning a language.
- **Single source of truth for codes.** Predicates reference graph clinical-entity nodes by id (e.g., `cond:crc`). They never carry ontology codes inline. Code-list updates happen in one place.
- **Three-valued logic for missing data.** True, false, unknown. Propagates cleanly through composition. Safer than silent false-coercion and more useful than hard errors.
- **No CQL / FHIRPath in v0.** Rejected for three reasons: (1) clinicians reviewing JSON shouldn't have to learn CQL; (2) our v0 predicate set is ~12 predicates, smaller than the cost of a CQL subset implementation; (3) CQL can be added later as an alternative serialization layer over this DSL if a downstream integration demands it. The DSL is deliberately not a general expression language.
- **Evaluator is deterministic.** Same `(graph version, evaluator version, PatientContext)` → same result. No wall-clock, no RNG, no external lookups at evaluation time.

## Tree shape

An expression is either a **predicate atom** or a **composite**.

### Predicate atom

```
{ predicate: <name>, <arg>: <value>, ... }
```

The `predicate` key is required and identifies which predicate from the catalog is being applied. Remaining keys are the predicate's named arguments.

### Composite

```
{
  all_of: [ <expression>, ... ]?,
  any_of: [ <expression>, ... ]?,
  none_of: [ <expression>, ... ]?,
  n_of: { n: <int>, of: [ <expression>, ... ] }?
}
```

All four keys are optional; at least one must be present. When multiple keys appear at the same level, they combine with AND:

```
{ all_of: [A, B], none_of: [C] }   ≡   A AND B AND NOT(C)
```

Expressions nest arbitrarily. Empty-list semantics:

- `all_of: []` → true
- `any_of: []` → false
- `none_of: []` → true
- `n_of: { n: 0, of: [] }` → true; `n_of: { n: N>0, of: [] }` → false

### `n_of` composite

`n_of: { n: N, of: [E1, E2, ...] }` is true iff at least `N` of the listed expressions evaluate to `true`. Three-valued behavior: if the count of `true` siblings is already `>= N`, result is `true`; if the count of `true` plus `unknown` siblings is `< N`, result is `false`; otherwise `unknown`. Added because several USPSTF recs are phrased as "persons with one or more of the following risk factors" (statin, osteoporosis under 65, falls prevention) and are more legible as `n_of: { n: 1, of: [...] }` than as `any_of`, and because others are phrased as "two or more" thresholds (family history patterns already use `min_count` inside `has_family_history_matching`; `n_of` handles the cross-predicate case).

Prefer `any_of` when `n == 1` unless the rec text explicitly frames it as a count; the review tool renders `n_of` as "at least N of the following" and `any_of` as "any of the following."

### Why this shape over explicit AND/OR/NOT operators

Named collections read better in JSON/YAML than operator trees, and they match how guideline documents phrase eligibility ("must meet all of... must not have any of..."). An operator-tree representation can be introduced later as an alternative serialization without changing semantics.

## Three-valued logic

Every expression evaluates to one of `true`, `false`, `unknown`.

- `unknown` is produced only by a `fail_closed` predicate encountering missing data. Every other evaluation path produces `true` or `false`.
- Propagation rules:

| Context | Presence of `unknown` |
|---|---|
| `all_of` | `unknown` unless some sibling is `false` (short-circuits to `false`) |
| `any_of` | `unknown` unless some sibling is `true` (short-circuits to `true`) |
| `none_of` | `unknown` unless some sibling is `true` (short-circuits to `false`) |

- At the top level, if the whole expression evaluates to `unknown`, the API returns a structured **cannot-evaluate** response identifying the specific predicate(s) that produced the unknown. It does not treat unknown as false.

### Interaction with `require`-policy predicates

A `require`-policy predicate with missing data raises a **hard evaluation error**, not `unknown`. Rationale: the predicate's own semantic is "this input is mandatory." `age_between` with no DOB isn't a data-gap the consumer might accept; it's an adapter/contract failure the consumer must fix. The error surfaces as a 4xx from the API layer, distinct from the cannot-evaluate response for fail_closed misses.

## Code references

Predicates that match against clinical entities reference them by **graph node id**, not by ontology code.

```
{ predicate: has_condition_history, codes: [cond:crc, cond:ibd] }
```

The evaluator expands each node id to that node's code list at evaluation time and matches against the patient context using the any-match rule defined in `patient-context.md`.

Inline ontology codes (e.g., `snomed:363346000`) are not allowed inside predicates. When a guideline references a code not yet represented as a graph node, the node is added first; the predicate then references the new node id. This is a hard rule, not a convention, so code-list edits never require predicate edits.

## Value labels

When a predicate compares an observation's result, the comparison uses the same **value label** mechanism as `INCLUDES_ACTION.expects`. Labels (`negative`, `positive`, `normal`) resolve to coded value-sets via the external registry keyed by `(clinical_entity_id, label)`. See `schema.md` → Result-conditional satisfaction.

Numeric comparisons use separate argument forms (`value_above`, `value_below`, `value_between`) that operate on `value_quantity` in the patient context. Labels and numeric comparisons are mutually exclusive on a single predicate invocation; don't mix.

`value_between: { min, max, unit, inclusive? }` matches records whose `value_quantity` falls within `[min, max]`. `inclusive` defaults to `true`; setting it to `false` makes both bounds strict. One-sided ranges should use `value_above` / `value_below`, not `value_between` with a synthetic bound.

## Time and windows

- All durations use ISO 8601: `P1Y`, `P30D`, `P6M`, `PT24H`.
- All windows are relative to `PatientContext.evaluation_time`: `[evaluation_time - window, evaluation_time]`.
- Predicates that take a window default to `window: P10Y` only when explicitly documented; otherwise `window` is required.
- Patient records with `effective_date` or `performed_date` after `evaluation_time` are ignored (see `patient-context.md`).

## Missing-data policy

Every predicate has a default policy: `require`, `fail_open`, or `fail_closed`.

- `require`: missing input → hard evaluation error.
- `fail_open`: missing input → predicate evaluates to `false`.
- `fail_closed`: missing input → predicate evaluates to `unknown`.

Defaults are overridable per-evaluation via `PatientContext.policy_overrides`. Overrides are scoped by predicate name; all invocations of that predicate in the expression tree share the override for that evaluation.

"Missing input" is predicate-specific but always grounded in the patient context. For example:

- `age_between` considers input missing if `patient.date_of_birth` is absent.
- `has_condition_history` considers input missing if `completeness.conditions = not_available`. An empty `conditions: []` with `completeness.conditions = populated` is **not** missing; the predicate cleanly evaluates to `false`.
- `has_family_history_matching` considers input missing if `completeness.family_history = not_available`.

The distinction between "not asked" (not_available) and "asked, none" (populated + empty) is the reason `completeness` exists in the patient context. Predicates that care about the distinction encode it in their missing-input check.

## Predicate catalog (v1)

All predicates committed for v1. Each entry gives signature, semantics, and default missing-data policy. Sections are organized by domain; the `Domain helpers` section holds reusable composites that cross domains.

### Demographics

**`age_between {min, max}`**
Age (years, floor of `(evaluation_time - date_of_birth) / P1Y`) is in `[min, max]` inclusive.
Default: `require`.

**`age_greater_than {value}`** / **`age_less_than {value}`**
Strict inequality against computed age.
Default: `require`.

**`administrative_sex_is {value}`**
`patient.administrative_sex == value`. Value ∈ `{male, female, other, unknown}`.
Default: `require`. Used for sex-specific screening where the rec is anchored to the registered sex in the record.

**`sex_assigned_at_birth_is {value}`**
`patient.sex_assigned_at_birth == value`. Value ∈ `{male, female, intersex, unknown}`.
Default: `fail_closed`. USPSTF cervical, breast, AAA, and osteoporosis recs are biologically anchored and must not misclassify transgender or nonbinary patients whose administrative sex differs from anatomy. If the adapter does not supply this field, the predicate abstains rather than silently falling back to administrative sex.

**`gender_identity_is {values: [...]}`**
`patient.gender_identity` is in the list. Used when rec text explicitly invokes gender (rare for USPSTF; included for downstream specialty-society recs that do).
Default: `fail_open`.

**`has_ancestry_matching {populations: [...]}`**
True if `patient.ancestry` intersects the listed population tokens. Tokens are a controlled vocabulary maintained alongside the value-set registry (e.g., `ashkenazi_jewish`, `eastern_european_jewish`, `norwegian`, `icelandic`). Used by the USPSTF BRCA risk-assessment rec, which names ancestry groups with elevated founder-mutation prevalence.
Default: `fail_open`. Ancestry data is frequently missing and its absence does not trigger the rec on its own; pair with family-history predicates.

**`menopausal_status_is {value}`**
Value ∈ `{premenopausal, perimenopausal, postmenopausal, surgical_menopause, unknown}`. Resolved from either an explicit status field in the patient context or, if absent, from a canonical derivation (age, LMP, oophorectomy status) performed by the adapter. The predicate does not derive; adapters must supply.
Default: `fail_closed`. Used by the osteoporosis-under-65 rec, which scopes to postmenopausal women with risk factors.

### Pregnancy and perinatal

USPSTF has a large perinatal block (HepB, HIV, syphilis, Rh(D), gestational diabetes, preeclampsia aspirin, asymptomatic bacteriuria, IPV, breastfeeding support, perinatal depression interventions, healthy weight, tobacco cessation in pregnancy). All of these need pregnancy state as a first-class predicate rather than a coded condition, because pregnancy drives both eligibility and gestational-age timing, and because the adapter typically already carries a pregnancy status field distinct from a SNOMED Condition.

**`is_pregnant`**
True iff `patient.pregnancy.status == pregnant` at `evaluation_time`.
Default: `fail_open` (absence means "not known to be pregnant", which is the common case and not a safety issue for most recs that layer on this).

**`gestational_age_between {min_weeks, max_weeks, inclusive?}`**
True iff the patient is pregnant and `gestational_age_at(evaluation_time)` in weeks is in the specified range. `inclusive` defaults to `true`. Fails (evaluates `false`) if not pregnant.
Default: `fail_closed` if pregnant but gestational age is missing; `fail_open` if not pregnant. This split is deliberate: "not pregnant" is a clean negative, but "pregnant with unknown GA" is a data gap that should not silently satisfy or miss a window-scoped rec (e.g., GDM screening at ≥24 weeks, aspirin for preeclampsia starting 12 weeks).

**`postpartum_within {window}`**
True iff `patient.pregnancy.end_date` is within `[evaluation_time - window, evaluation_time]`. Used for postpartum depression, breastfeeding support, IPV screening extending into the postpartum period.
Default: `fail_open`.

**`parity_greater_than_or_equal {value}` / `gravidity_greater_than_or_equal {value}`**
Counts from obstetric history. Used sparingly (not a major USPSTF axis) but included because perinatal depression risk assessment and some downstream ACOG recs use parity thresholds.
Default: `fail_open`.

**`lactation_status_is {value}`**
Value ∈ `{lactating, not_lactating, unknown}`. Used by breastfeeding-support and medication-safety recs.
Default: `fail_open`.

### Conditions

**`has_condition_history {codes: [<graph Condition node id>, ...]}`**
True if any `Condition` in the patient context meets all of:
- Its code list intersects the union of the referenced nodes' code lists
- `verification_status = confirmed`
- `clinical_status ∈ {active, recurrence, remission, resolved, inactive}` (any status except refuted/entered-in-error, which are already excluded by verification_status)

Default: `fail_open`.

**`has_active_condition {codes: [...]}`**
Same as `has_condition_history` but restricted to `clinical_status ∈ {active, recurrence}`.
Default: `fail_open`. Used for HTN screening exclusion (already has active HTN dx) and for preemption conditions.

### Tobacco exposure

Tobacco has its own section because three USPSTF recs (AAA, lung cancer screening, tobacco cessation) depend on quantitative smoking history that is awkward to encode as a generic observation predicate. Adapters normalize tobacco into a dedicated `patient.tobacco` sub-object (current status, pack-years, quit date); predicates read from there.

**`smoking_status_is {values: [...]}`**
True iff `patient.tobacco.status` is in the list. Values ∈ `{never, former, current_some_day, current_every_day, unknown}`. `ever_smoker` is a derived token expanding to `{former, current_some_day, current_every_day}`.
Default: `fail_closed`. The AAA rec scopes to "men aged 65–75 who have ever smoked"; unknown status must abstain rather than silently excluding the patient.

**`pack_years_greater_than_or_equal {value}`**
True iff `patient.tobacco.pack_years >= value`.
Default: `fail_closed`. Used by lung cancer screening (≥20 pack-years).

**`years_since_smoking_cessation_less_than {value}`**
True iff the patient is a former smoker and `(evaluation_time - patient.tobacco.quit_date)` in whole years is `< value`. False if the patient currently smokes (treat as "zero years since cessation" does not apply cleanly; callers should compose with `smoking_status_is` when distinguishing).
Default: `fail_closed`. Used by lung cancer screening (quit within 15 years).

### Observations

**`has_observation_in_window {code, window}`**
True if any `Observation` in the patient context has a code in the referenced node's code list, `status ∈ {final, amended, corrected}`, and `effective_date` in window. Presence only; ignores result value.
Default: `fail_open`.

**`observation_value_matches {code, window, value_label? | value_above? | value_below?, component?}`**
True if any matching Observation in the window has a result satisfying the value filter. Exactly one of `value_label`, `value_above`, `value_below` must be provided. `component` optionally selects a sub-component by code (for multi-part observations like BP; required when the observation has components and the filter targets a specific limb).
- `value_label: <label>`: matched record must carry `value_coded` or `interpretation` with a code in the resolved value-set for `(code, label)`.
- `value_above: {value, unit}`: matched record must carry `value_quantity` with matching `unit` and value `> value`.
- `value_below: {value, unit}`: as above with `<`.

Any-match semantics within the window. For most-recent semantics, use `most_recent_observation_value`.
Default: `fail_open`. Records with `status: final` but `value: null` fail the match (they are records-in-the-window, but not value-satisfying).

**`most_recent_observation_value {code, window, comparator, threshold, unit, component?}`**
Locates the most-recent matching Observation (by `effective_date`) in the window and applies the comparator. `comparator ∈ {eq, ne, gt, lt, gte, lte}`. If no matching Observation exists, the predicate is false. Provided for trend-sensitive HTN/lipid predicates.
Default: `fail_open`.

**`count_observations_matching {code, window, value_label? | value_above? | value_below? | value_between?, component?, min_count, distinct_dates?}`**
True iff at least `min_count` matching Observations exist in the window. Value filter is optional; when omitted, counts presence only. `distinct_dates` defaults to `false`; when `true`, only one record per calendar date counts toward `min_count` (needed for diagnostic criteria that require elevated readings on separate occasions, e.g., HTN diagnosis requiring two or more elevated office BPs on separate dates).
Default: `fail_open`. Records with `status: final` but `value: null` do not satisfy a value filter.

**`time_since_most_recent_observation {code, comparator, duration, value_filter?, component?}`**
Finds the most recent matching Observation (optionally filtered by value) across the full patient history (not windowed) and compares `(evaluation_time - effective_date)` to `duration` via `comparator ∈ {gt, lt, gte, lte}`. If no matching Observation exists, returns `true` for `gt`/`gte` comparators (interpreted as "more time has elapsed than any finite duration") and `false` for `lt`/`lte`. This convention makes "overdue for screening" queries compose cleanly: "last FIT > P1Y OR no FIT ever" collapses to a single predicate.
Default: `fail_open`. Callers who need the "never" case distinguished from "long ago" should compose with `has_observation_in_window` or `has_any_prior_screening`.

**`bmi_above {value}` / `bmi_below {value}` / `bmi_between {min, max, inclusive?}`**
Convenience predicates over the most-recent BMI Observation (LOINC 39156-5) within `P2Y` of `evaluation_time`. Implemented as sugar over `most_recent_observation_value`; kept as first-class predicates because several USPSTF recs (prediabetes/diabetes screening at BMI ≥25 or ≥23 for Asian Americans, weight-loss interventions at BMI ≥30, healthy-diet/activity at CV risk factors) use BMI thresholds and the terse form is more reviewable.
Default: `fail_closed`. Missing BMI on a rec that requires it is a data gap, not a negative.

**`bmi_percentile_above {value}`**
Pediatric BMI-for-age percentile threshold (>=95th for the high-BMI intervention rec in children ≥6). Reads from a pediatric-percentile Observation supplied by the adapter; the evaluator does not compute percentiles from raw BMI.
Default: `fail_closed`.

### Procedures

**`has_procedure_in_window {code, window}`**
True if any `Procedure` with `status = completed` has a code in the referenced node's code list and `performed_date` in window.
Default: `fail_open`.

**`has_procedure_history {codes}`**
Lifetime (no window) variant. True if any completed Procedure has a code in the union of the referenced nodes' code lists, regardless of date. Used for once-in-a-lifetime facts that change eligibility: total hysterectomy (removes cervical screening population), bilateral mastectomy, bilateral oophorectomy.
Default: `fail_open`.

**`time_since_most_recent_procedure {codes, comparator, duration}`**
Analogous to `time_since_most_recent_observation`: finds the most recent completed matching Procedure across full history and compares elapsed time to `duration`. Same "never performed → true for gt/gte" convention. Central to screening-cadence logic (e.g., overdue for colonoscopy when `time_since_most_recent_procedure > P10Y`).
Default: `fail_open`.

### Medications

**`has_medication_active {codes: [<graph Medication node id>, ...]}`**
True if any `Medication` in the patient context has `status = active` and a code in the union of the referenced nodes' code lists. Class-level matching flows through the node's code list (e.g., `med:ace-inhibitor` node carrying all RxNorm ingredient codes for the class).
Default: `fail_open`.

### Immunizations

**`has_immunization {codes, min_doses?, completed_series?, within_window?}`**
True if the patient has matching `Immunization` records with `status = completed`. `codes` references graph `Immunization` or vaccine-product nodes. `min_doses` (default 1) requires at least that many distinct-date administrations. `completed_series: true` requires the adapter-flagged series-complete indicator (preferred for HepB, HPV, MMR where dose count alone is insufficient). `within_window` scopes to recent doses when recency matters (e.g., influenza, COVID boosters).
Default: `fail_open`. Used by HepB screening (prior-vaccination status modulates interpretation) and downstream vaccine-aware recs.

### Risk scores

USPSTF recs increasingly reference computed risk scores: 10-year ASCVD risk (statin primary prevention, ≥10%), BRCA risk-assessment tools as a gate before testing, FRAX / OST as pre-screening aids for osteoporosis under 65, fall-risk multifactorial screen. The graph does not compute these scores; adapters supply them as typed records on the patient context.

**`risk_score_compares {name, comparator, threshold}`**
True iff `patient.risk_scores[name]` exists and its value compared to `threshold` via `comparator ∈ {gt, lt, gte, lte, eq}` is true. `name` is a controlled token (e.g., `ascvd_10yr`, `frax_major_osteoporotic_10yr`, `frax_hip_10yr`, `gail_5yr`, `tyrer_cuzick_lifetime`, `stop_bang`, `ost`). The controlled list lives in the reference registry alongside value-sets.
Default: `fail_closed`. A rec that gates on a risk score and can't read one should abstain, not silently exclude; the review tool surfaces the missing score as an actionable data gap.

### Family history

**`has_family_history_matching {relationship, conditions, onset_age_below?, min_count}`**
Matches against `FamilyMemberHistory` records. See full definition below.
Default: `fail_open`.

- `relationship`: list of tokens or SNOMED codes.
  - Tokens: `first_degree_relative`, `second_degree_relative`, `any_relative`. Expand in the evaluator to canonical FHIR/SNOMED code sets:
    - `first_degree_relative` → mother, father, brother, sister, son, daughter
    - `second_degree_relative` → grandparent, grandchild, aunt, uncle, niece, nephew, half-sibling
    - `any_relative` → union of above plus cousins and more-distant relatives
  - Specific SNOMED codes (e.g., `72705000` for son) may also appear in the list.
  - A FamilyMemberHistory record matches if its relationship code is in the expanded set.
- `conditions`: list of graph Condition node ids. A family member's condition matches if any of its codes appears in any referenced node's code list.
- `onset_age_below`: optional integer. When set, only family-member condition records with `onset_age < value` count toward `min_count`. Records with unknown `onset_age` do **not** satisfy this filter.
- `min_count`: integer ≥ 1; true iff at least this many **distinct** family members satisfy relationship and condition (and onset-age if provided) filters. Distinctness is by `FamilyMemberHistory.id`.

### Allergies

**`has_allergy_to {substance_codes: [<graph Medication or substance node id>, ...]}`**
True if any `AllergyIntolerance` with `clinical_status = active` and `verification_status ∈ {confirmed, unconfirmed}` references a substance in the resolved code list. Unconfirmed allergies are included because safety-critical contraindication checks should not require confirmation.
Default: `fail_closed`. Unlike most predicates, absence-of-data here is not safe to treat as false; a safety check's job is to abstain when it can't be answered.

### Behavioral and social history

USPSTF screens multiple behavioral and social domains: unhealthy alcohol use, unhealthy drug use, sexual behavior (STI risk, chlamydia/gonorrhea, PrEP eligibility), intimate partner violence exposure, skin phenotype for sun-safety counseling, fall-risk factors. These do not cleanly fit Observation (values are often tokens, not coded results) and are grouped here as a dedicated namespace.

**`screening_result_is {instrument, result}`**
True iff the patient has a recorded screening-instrument result whose `instrument` matches and `result` is in the allowed set. `instrument` is a controlled token (`audit_c`, `audit`, `single_item_alcohol`, `nida_quick_screen`, `dast_10`, `phq_2`, `phq_9`, `gad_7`, `edinburgh_postnatal`, `hits`, `wast`, `e_hits`, `stay_left_screen`, `cage_aid`). `result` ∈ `{positive, negative, unknown}` or an instrument-specific ordinal (`audit_c: {score_gte_4_men, score_gte_3_women}`, `phq_9: {mild, moderate, moderately_severe, severe}`). Allowed result tokens per instrument are defined in the reference registry.
Default: `fail_closed`. "Never asked" is not "negative" for behavioral screens.

**`unhealthy_alcohol_use_positive {window?}`**
Sugar over `screening_result_is` for any of the USPSTF-endorsed alcohol instruments (AUDIT, AUDIT-C, Single-Item Alcohol Screening Question) with a positive result in the window (default `P1Y`). Included as a first-class predicate because three separate recs (unhealthy alcohol screening itself, preconception/pregnancy counseling, and downstream behavioral counseling) key off it.
Default: `fail_closed`.

**`has_sexual_risk_factor {factors: [...]}`**
True iff `patient.sexual_history` intersects the listed factor tokens. Controlled tokens: `new_partner_last_year`, `multiple_partners_last_year`, `inconsistent_condom_use`, `msm`, `transactional_sex`, `partner_with_hiv`, `partner_with_sti`, `iv_drug_use_sharing`, `commercial_sex_work`, `incarceration_history`. Used by chlamydia/gonorrhea (women 25+ at increased risk), PrEP eligibility, STI behavioral counseling.
Default: `fail_closed`. Sexual history is frequently undocumented; silent exclusion would systematically under-screen, so the rec should surface the data gap.

**`has_ipv_exposure {window?}`**
True iff the patient context records intimate partner violence exposure within `window` (default lifetime). Sourced from either a positive IPV-screening-instrument result or a structured social-history flag. Note the intentional asymmetry: because IPV disclosures carry safety implications, the predicate is used to route supportive interventions, not to gate access to care.
Default: `fail_closed`.

**`has_skin_phenotype {values: [...]}`**
Values from Fitzpatrick scale or the USPSTF skin-cancer-prevention rec's "fair-skinned" construct (`fitzpatrick_i`, `fitzpatrick_ii`, `fair_skinned`). Used by the skin-cancer behavioral counseling rec.
Default: `fail_open`.

**`has_fall_risk_factor {factors: [...]}`**
True iff the patient has one or more fall-risk factors from the controlled list (`history_of_falls_last_year`, `gait_or_balance_abnormality`, `lower_extremity_weakness`, `fear_of_falling`, `cognitive_impairment`, `high_risk_medications`, `orthostatic_hypotension`). Used by the falls-prevention rec (community-dwelling adults 65+ at increased risk).
Default: `fail_closed`.

### Shared decision-making

Several USPSTF recs are explicitly shared-decision-making (SDM): prostate screening 55–69, aspirin for CVD primary prevention (where still applicable), breast cancer medication, mammography 40–49 (where individualized). SDM recs should not fire their "perform the action" Strategy unless a preference has been captured; otherwise the graph produces a recommendation to *have the conversation*, not to perform the test.

**`patient_preference_is {decision_id, values: [...]}`**
True iff `patient.preferences[decision_id]` is present and its value is in the list. Decision ids are strings rooted to a specific Rec (e.g., `psa_screening_55_69`, `aspirin_primary_prevention`). Values are decision-specific tokens (e.g., `opted_in`, `opted_out`, `undecided`).
Default: `fail_closed`. Missing preference data on an SDM-gated rec is a signal to recommend the conversation; silent `false` would make the rec invisible.

### Prognostic

**`life_expectancy_below {years}`**
True iff `patient.prognosis.estimated_life_expectancy_years < value`. Sourced from an explicit clinician-entered field on the patient context; the evaluator does not compute life expectancy. Used by USPSTF stop-screening thresholds framed as "less than 10-year life expectancy" (colorectal ≥76, breast ≥75 in some framings, certain cancer screening discontinuation logic). Controversial clinically; the predicate exists so the rec can encode the threshold honestly rather than hide it in an age cutoff.
Default: `fail_open`. Absent life-expectancy judgment should not, on its own, disqualify screening.

### Domain helpers

**`has_any_prior_screening {domain}`**
True if the patient context contains any Procedure or Observation whose code appears in the domain → screening-code reference map for the given domain. Domains are string tokens (e.g., `crc`, `breast`, `cervical`). The mapping is reference data, maintained alongside the value-set registry; it is not in the graph.
Default: `fail_open`. Used in the ACP "discontinue over 75" Rec where "never previously screened" is the complement case.

## What's not in v1

Not in the catalog because no current USPSTF Grade A/B rec forces them. Add when a domain requires them; the grammar doesn't need to change.

- **Trend primitives** beyond `most_recent_observation_value` and the count/time-since predicates: rate-of-change, average-of-last-n, slope. HTN and HFrEF treatment targets will need these.
- **Dosing predicates** on medications: `is_at_target_dose`, `dose_above`. Belong with HFrEF / diabetes treatment recs, not screening.
- **Encounter / visit context**: `seen_in_encounter_type`, `in_inpatient_setting`. Screening recs are visit-agnostic; treatment pathways are not.
- **Sequenced / ordered events**: "observation X followed by observation Y within Z days." Expressible via two count/time-since predicates for now; a dedicated sequencing predicate is warranted if LDCT-follow-up or colposcopy-follow-up logic lands.
- **Fraction/ratio composites**: `fraction_of`. No current screening rec requires it.
- **Absolute calendar windows**: "since 2020-01-01." All current recs are relative-to-evaluation-time. Add if a rec ever keys to a specific historical date.
- **Explicit AND/OR/NOT operator forms**: alternative serialization if consumers request it.

## Serialization

- YAML or JSON; interchangeable.
- Schema validation happens at ingestion; invalid predicates are rejected before reaching the graph.
- The evaluator does not parse predicates; it consumes them as already-validated structured objects.

## Determinism and versioning

- The predicate catalog is part of the **evaluator version**. Adding a predicate or changing a predicate's semantics or default policy bumps the evaluator version.
- The value-set registry is part of the **graph version** (see `schema.md`). Value-label semantic changes bump the graph version, not the evaluator version.
- The same `structured_eligibility` expression, evaluated against the same `PatientContext` (same `evaluation_time`) under the same evaluator version and graph version, always produces the same result.

## Worked examples

### CRC Grade A exclusion (from `crc-model.md`)

```yaml
structured_eligibility:
  all_of:
    - { predicate: age_between, min: 50, max: 75 }
  none_of:
    - { predicate: has_condition_history, codes: [cond:crc, cond:high-risk-adenoma, cond:ibd, cond:lynch-syndrome, cond:fap] }
    - { predicate: has_family_history_matching, relationship: [first_degree_relative], conditions: [cond:crc], onset_age_below: 60, min_count: 1 }
    - { predicate: has_family_history_matching, relationship: [first_degree_relative], conditions: [cond:crc], min_count: 2 }
    - { predicate: has_family_history_matching, relationship: [any_relative], conditions: [cond:lynch-syndrome, cond:fap], min_count: 1 }
```

Semantics: age 50-75 AND none of {personal CRC/HRA/IBD/Lynch/FAP, FDR with CRC <60, ≥2 FDRs with CRC, any relative with Lynch/FAP}.

### HTN diagnostic-confirmation trigger (illustrative; Rec not yet modeled)

```yaml
trigger_criteria:
  any_of:
    - predicate: observation_value_matches
      code: obs:blood-pressure-panel
      component: loinc:8480-6       # systolic
      value_above: { value: 130, unit: "mm[Hg]" }
      window: P30D
    - predicate: observation_value_matches
      code: obs:blood-pressure-panel
      component: loinc:8462-4       # diastolic
      value_above: { value: 80, unit: "mm[Hg]" }
      window: P30D
```

Semantics: an office BP in the past 30 days with SBP >130 OR DBP >80 fires the confirmation Rec.

### Lynch-syndrome preemption of CRC avg-risk (illustrative)

```yaml
PREEMPTED_BY:
  condition:
    any_of:
      - { predicate: has_condition_history, codes: [cond:lynch-syndrome, cond:fap] }
      - { predicate: has_family_history_matching, relationship: [any_relative], conditions: [cond:lynch-syndrome, cond:fap], min_count: 1 }
  priority: 100
  rationale: "Known or suspected hereditary CRC syndrome; USPSTF avg-risk does not apply."
```

### Lung cancer screening eligibility (USPSTF 2021)

```yaml
structured_eligibility:
  all_of:
    - { predicate: age_between, min: 50, max: 80 }
    - { predicate: pack_years_greater_than_or_equal, value: 20 }
    - any_of:
        - { predicate: smoking_status_is, values: [current_some_day, current_every_day] }
        - all_of:
            - { predicate: smoking_status_is, values: [former] }
            - { predicate: years_since_smoking_cessation_less_than, value: 15 }
  none_of:
    - { predicate: life_expectancy_below, years: 5 }
    - { predicate: has_condition_history, codes: [cond:lung-cancer] }
```

### Statin primary prevention (USPSTF 2022)

```yaml
structured_eligibility:
  all_of:
    - { predicate: age_between, min: 40, max: 75 }
    - { predicate: risk_score_compares, name: ascvd_10yr, comparator: gte, threshold: 10 }
    - n_of:
        n: 1
        of:
          - { predicate: has_active_condition, codes: [cond:dyslipidemia] }
          - { predicate: has_active_condition, codes: [cond:diabetes] }
          - { predicate: has_active_condition, codes: [cond:hypertension] }
          - { predicate: smoking_status_is, values: [current_some_day, current_every_day] }
  none_of:
    - { predicate: has_condition_history, codes: [cond:ascvd] }
    - { predicate: has_medication_active, codes: [med:statin] }
```

### Gestational diabetes screening (USPSTF 2021)

```yaml
structured_eligibility:
  all_of:
    - { predicate: is_pregnant }
    - { predicate: gestational_age_between, min_weeks: 24, max_weeks: 42 }
  none_of:
    - { predicate: has_active_condition, codes: [cond:diabetes, cond:gestational-diabetes-current-pregnancy] }
```

### Cervical cancer screening population (USPSTF 2018)

```yaml
structured_eligibility:
  all_of:
    - { predicate: sex_assigned_at_birth_is, value: female }
    - { predicate: age_between, min: 21, max: 65 }
  none_of:
    - { predicate: has_procedure_history, codes: [proc:total-hysterectomy-benign] }
```

Semantics: biologically anchored on sex assigned at birth so trans men with a cervix remain eligible; excluded after total hysterectomy for benign indications (hysterectomy for cervical cancer or precancer does NOT remove eligibility; that nuance lives in the `codes` code list, not the predicate).

### HTN diagnostic confirmation on separate occasions

```yaml
trigger_criteria:
  any_of:
    - predicate: count_observations_matching
      code: obs:blood-pressure-panel
      component: loinc:8480-6
      value_above: { value: 130, unit: "mm[Hg]" }
      window: P6M
      min_count: 2
      distinct_dates: true
    - predicate: count_observations_matching
      code: obs:blood-pressure-panel
      component: loinc:8462-4
      value_above: { value: 80, unit: "mm[Hg]" }
      window: P6M
      min_count: 2
      distinct_dates: true
```

Semantics: elevated SBP or DBP on at least two separate dates within 6 months fires the confirmation rec. `distinct_dates: true` prevents two sequential readings in the same office visit from satisfying the criterion.

### CRC screening overdue (time-since)

```yaml
trigger_criteria:
  all_of:
    - { predicate: age_between, min: 45, max: 75 }
    - any_of:
        - { predicate: time_since_most_recent_procedure, codes: [proc:colonoscopy], comparator: gt, duration: P10Y }
        - { predicate: time_since_most_recent_observation, code: obs:fit, comparator: gt, duration: P1Y }
```

The "never performed" case is covered implicitly by the time-since predicates' semantics (no record → elapsed time is treated as exceeding any finite duration).

### BRCA risk-assessment gate (USPSTF 2019)

```yaml
structured_eligibility:
  all_of:
    - { predicate: sex_assigned_at_birth_is, value: female }
    - { predicate: age_greater_than, value: 18 }
    - any_of:
        - { predicate: has_family_history_matching, relationship: [first_degree_relative, second_degree_relative], conditions: [cond:breast-cancer, cond:ovarian-cancer, cond:tubal-cancer, cond:peritoneal-cancer], min_count: 1 }
        - { predicate: has_condition_history, codes: [cond:breast-cancer, cond:ovarian-cancer, cond:tubal-cancer, cond:peritoneal-cancer] }
        - { predicate: has_ancestry_matching, populations: [ashkenazi_jewish] }
        - { predicate: risk_score_compares, name: tyrer_cuzick_lifetime, comparator: gte, threshold: 20 }
```

### PSA screening (SDM-gated)

```yaml
structured_eligibility:
  all_of:
    - { predicate: sex_assigned_at_birth_is, value: male }
    - { predicate: age_between, min: 55, max: 69 }
    - { predicate: patient_preference_is, decision_id: psa_screening_55_69, values: [opted_in] }
  none_of:
    - { predicate: has_condition_history, codes: [cond:prostate-cancer] }
```

Absence of a recorded preference produces `unknown` rather than `false`; the API layer surfaces this as a data gap and the graph emits a companion "conduct SDM conversation" Rec.

## Changelog

- **v1 (2026-04):** Added predicates for pregnancy/perinatal state, tobacco exposure, BMI (adult and pediatric), immunizations, risk scores, behavioral/substance-use screening, sexual risk, IPV, skin phenotype, fall risk, menopausal status, ancestry, shared-decision-making preference, life expectancy, lifetime procedure history, time-since-most-recent (observation and procedure), and distinct-date observation counting. Added `n_of` composite and `value_between` value filter. Motivated by coverage of the full USPSTF Grade A/B corpus; the CRC and HTN v0 set is a strict subset.
- **v0:** Initial DSL scoped to CRC and HTN screening/diagnosis.

## Open questions (resolve before first evaluator implementation)

- **Most-recent ordering tiebreaker.** When two matching observations share an `effective_date`, which wins? Proposed: deterministic tiebreak by `id` lexicographically. Pin this before writing the evaluator so goldens are stable.
- **Value-quantity unit coercion.** A predicate specifying `unit: "mm[Hg]"` against a record with `unit: "mmHg"` (no UCUM brackets). Evaluator should normalize UCUM at parse time. Adapter responsibility vs. evaluator responsibility TBD; lean evaluator so records from slightly noncompliant adapters still work.
- **Distinctness in `has_family_history_matching` when `id`s clash across sources.** Proposed: distinctness is by `id`; if the adapter fails to assign stable ids, duplicates count multiply. Document as an adapter-contract requirement, not an evaluator-side dedup.

## Related docs

- `patient-context.md` — input shape the DSL evaluates against.
- `schema.md` — graph schema; `structured_eligibility`, `trigger_criteria`, and `PREEMPTED_BY.condition` carry these expressions.
- `api-primitives.md` — evaluator lives here; surfaces evaluation errors, cannot-evaluate responses, and data-gap details.
- `docs/archive/crc-model.md` — worked guideline using this DSL (archived).
