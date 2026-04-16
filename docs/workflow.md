# Build workflow

The per-feature runbook. Read once; follow every time. The short version lives in root `CLAUDE.md`; this document is the full detail.

Each feature has a self-contained spec in `docs/build/`. In a fresh Claude Code session, prompt `/build NN` to run that feature through this workflow end to end. One feature per session. **One Claude Code session per repo at a time** — two sessions racing the same `.git` directory causes lock contention and lost work.

## Running the full stack

The simplest way to run everything:

```sh
docker compose up --build
```

This starts Neo4j, seeds the graph, starts the API, and starts the UI. All services are wired together and start in dependency order via healthchecks.

- UI: http://localhost:3000
- API: http://localhost:8000
- Neo4j Browser: http://localhost:7474 (neo4j / password123)

For component-level development (hot reload, faster iteration), run individual services locally per their READMEs (`api/README.md`, `ui/README.md`, `graph/README.md`).

## Per-feature loop

1. Start from a clean `main`:
   ```sh
   git checkout main
   git pull
   ```
2. Cut a branch with a typed prefix (see **Branch naming**):
   ```sh
   git checkout -b feat/<slug>
   ```
3. Do the work in logical chunks. Commit as you go — do not save one giant commit for the end.
   - **Contract alignment rule:** if your changes touch API routes, evaluator events, patient context handling, or predicates, the corresponding contract file (`api.openapi.yaml`, `eval-trace.schema.json`, `patient-context.schema.json`, `predicate-catalog.yaml`) must be updated in the same diff. If you're shipping a feature from `docs/build/`, the matching row in `docs/reference/build-status.md` must also move to `shipped` in the same diff. The `pr-reviewer` subagent will block if these are missing. See `.claude/agents/pr-reviewer.md` § Contract alignment for the full list.
4. Before opening a PR:
   - Run the test suite locally. It **must pass**. Do not open a PR on a red suite.
   - Run the manual test steps you plan to put in the PR body. Capture the real output.
5. Push the branch:
   ```sh
   git push -u origin feat/<slug>
   ```
6. Open the PR against `main` via `gh pr create` with a body matching the **PR template** below.
7. Invoke the `pr-reviewer` subagent on the PR. Post its output as a PR comment.
8. Address every blocking issue and every actionable non-blocking suggestion the subagent raises. Push fixes to the same branch. Re-run the subagent if you made substantive changes.
9. Only after the subagent's feedback is resolved, hand the PR to the human for review.
10. Human merges. You never merge your own PR. Never push to `main`.
11. After merge, clean up (see **Merging and cleanup**).

## Branch naming

- `feat/<slug>` — new user-visible behavior (new predicate, new endpoint, new UI tab, new evaluator primitive).
- `fix/<slug>` — bug fix for existing behavior. The slug names the bug, not the fix.
- `chore/<slug>` — refactors, docs, tooling, schema rewrites with no behavior change.

Slugs are lowercase, hyphen-separated, short. Examples: `feat/predicate-age-range`, `fix/trace-event-ordering`, `chore/stage-0-workflow`.

## Commit messages

- Each commit is one logical chunk: one file group, one concern. If you can't summarize it in one sentence, split it.
- Subject line ≤ 72 chars, imperative mood ("Add predicate_age_range", not "Added" or "Adds").
- Body explains the **why**. The diff shows the what. Cite the guideline or ADR when the commit encodes clinical content or a design decision.
- Reference the ADR when implementing one (`per ADR 0014`).

Example:
```
Add predicate_age_range to the v0 catalog

USPSTF statin rec uses age 40–75 as the Grade B eligibility floor.
Existing predicate_gte / predicate_lte chain worked but produced two
trace events for one concept, which made the Eval UI noisy. Collapsing
to a single predicate keeps the trace legible for reviewers.

Per ADR 0007 (predicate DSL). Contract updated in the same commit.
```

## Test layers

Four layers. Pick the lowest layer that exercises the behavior you added, and add higher-layer coverage when the behavior is user-visible.

- **Unit** — a single function, pure logic. Fast, no I/O. Use for: predicate evaluators, trace event construction, JSON Schema validation helpers, any utility. Required for new primitives.
- **Fixture** — the evaluator run against a synthetic `PatientContext` from `evals/fixtures/statins/`. Asserts the trace event stream and the derived recommendation list. Use for: new eligibility rules, new trace event types, changes to how strategies resolve. Required for any evaluator change.
- **Integration** — wire through the REST API, often with a live Neo4j instance. Asserts a full `/evaluate` call end-to-end. Use for: API shape changes, new endpoints, schema changes that affect traversal.
- **e2e** — the `/ui` talking to the `/api` talking to the graph. Reserved for UI flows — Explore traversal, Eval step-through. Keep these few and focused; they are slow and brittle.

Rule of thumb: no code path ships without at least one test that would catch it regressing. Pure data changes (a new fixture, a seed tweak) need at least one integration assertion. New logic needs unit + fixture.

## PR template

Open every PR with this body. Copy it verbatim and fill in. The outer fence here is four backticks so the nested triple-backtick blocks render correctly.

````markdown
## Scope

<One paragraph: what this PR does and why. Link the ADR or issue if applicable.>

## Changes

- <bullet per file group or concern>

## Test suite

```
<paste the output of the test runner — pytest, vitest, whatever — showing it passed>
```

## Manual test steps

1. <command or action>
2. <command or action>
3. <command or action>

## Manual test output

```
<paste the actual terminal output of running the steps above>
```

## Notes

<anything the reviewer should know: tradeoffs, deferred work, linked ISSUES.md entries>
````

## Subagent review

Every PR gets reviewed by the `pr-reviewer` subagent before a human looks at it.

Invoke pattern: use the `Task` tool with `subagent_type: "pr-reviewer"` and a prompt naming the PR number, e.g.:

```
Task(
  subagent_type: "pr-reviewer",
  description: "Review PR #<n>",
  prompt: "Review PR #<n> in this repo. Fetch the diff and body via gh,
           follow .claude/agents/pr-reviewer.md, check against the
           workflow in docs/workflow.md and the component DoDs, and
           post your review as a PR comment via gh pr comment."
)
```

The subagent posts its review as a PR comment via `gh pr comment`. It must:

- Name at least three substantive things it actually checked.
- Give a verdict: APPROVE, REQUEST CHANGES, or COMMENT.
- Flag any blocking issues explicitly.

If the subagent requests changes:

1. Read the comment carefully. Do not dismiss nits without reason.
2. Push fixes to the same branch. One commit per distinct fix.
3. If the changes are substantive (not just typo fixes), re-invoke the subagent so the new diff gets reviewed.
4. Only when the subagent's feedback is resolved do you hand the PR to the human.

The subagent spec lives at `.claude/agents/pr-reviewer.md`. Update it as the repo matures — new components get new DoD items to check.

## CI

GitHub Actions runs three jobs on every push to `main` and every pull request. All three must pass before merge (once branch protection is enabled).

| Job | What it does |
|---|---|
| `api-tests` | Loads the graph seed into a Neo4j 5 service container, runs `pytest api/tests/`. |
| `contract-lint` | Validates `api.openapi.yaml` (OpenAPI 3), `*.schema.json` (JSON Schema), and `predicate-catalog.yaml` (against its schema). |
| `graph-smoke` | Loads the seed and asserts expected node/edge counts (23 nodes, 14 edges for the statin model). |

Workflow file: `.github/workflows/ci.yml`. Local reproduction instructions: `.github/workflows/README.md`.

CI complements the `pr-reviewer` subagent — it catches mechanical breakage (tests fail, contracts don't parse, seed is incomplete), while the subagent catches semantic issues (missing contract updates, DoD compliance, test coverage gaps).

## Merging and cleanup

The human merges. Never merge your own PR. Never push directly to `main`.

After merge:
```sh
git checkout main
git pull
git branch -d <branch>
# optional: prune the remote-tracking ref
git fetch --prune
```

If the branch is deleted on the remote first and your local `git branch -d` fails because it "may not be fully merged" (it was squashed), use `git branch -D <branch>` — but only after confirming via `gh pr view <n>` that the PR was actually merged.

## Handling conflicts

**Text conflicts** (same file, different lines, mechanically resolvable): rebase onto `main` and fix.

```sh
git fetch origin
git rebase origin/main
# resolve conflicts, git add, git rebase --continue
git push --force-with-lease
```

Use `--force-with-lease`, never plain `--force` — it refuses the push if the remote branch moved under you, which protects against clobbering a teammate's commit on the same branch.

**Semantic conflicts** (both PRs edited different files but the meaning collides — e.g., your PR adds a predicate the other PR's evaluator no longer calls): stop. Do not silently resolve. Flag the conflict in a PR comment, tag the human, and wait. A mechanical merge here silently breaks behavior.

Conflicts in ADRs or contracts are almost always semantic. Escalate by default.

## Worked example: adding a new predicate to the v0 catalog

Concrete run-through. Task: add `predicate_age_range` to the v0 predicate catalog, because the statin model needs `age in [40, 75]` as one event instead of a `gte`+`lte` pair.

The commands below assume the Stage 1+ harness is in place (`api/`, `evals/fixtures/statins/tests/`, seed loaded into Neo4j). Until then, substitute whatever test runner exists at the time — and if nothing exists yet, the PR needs manual-test evidence only, per the carve-out in `.claude/agents/pr-reviewer.md`.

1. **Branch from main:**
   ```sh
   git checkout main && git pull
   git checkout -b feat/predicate-age-range
   ```
2. **Read the relevant spec and contract:**
   - `docs/specs/predicate-dsl.md` — semantics.
   - `docs/contracts/predicate-catalog.yaml` — shape.
3. **Edit spec and contract in one commit** (root CLAUDE.md rule: shape changes pair spec + contract):
   ```sh
   # add predicate_age_range section to docs/specs/predicate-dsl.md
   # add predicate_age_range entry to docs/contracts/predicate-catalog.yaml
   git add docs/specs/predicate-dsl.md docs/contracts/predicate-catalog.yaml
   git commit -m "Add predicate_age_range to spec and contract

   USPSTF 2022 statin Grade B floor is age 40–75. Collapsing the
   existing gte+lte pair into one predicate keeps the EvalTrace legible
   for clinician reviewers — one event per clinical concept.

   Per ADR 0007 (predicate DSL)."
   ```
4. **Implement the predicate in `/api`:**
   ```sh
   # add evaluator function + registry entry
   git add api/evaluator/predicates.py
   git commit -m "Implement predicate_age_range evaluator

   Reads patient.demographics.age, returns a single trace event with
   the resolved bounds and the matched flag. Deterministic — no wall
   clock, no RNG."
   ```
5. **Add unit tests:**
   ```sh
   git add api/tests/test_predicate_age_range.py
   git commit -m "Unit tests for predicate_age_range

   Covers in-range, below-range, above-range, and missing-age cases."
   ```
6. **Update the statin seed to use the new predicate and refresh the fixture-level test:**
   ```sh
   git add graph/seeds/statins.cypher evals/fixtures/statins/tests/test_grade_b.py
   git commit -m "Migrate statin Grade B eligibility to predicate_age_range

   Replaces the gte+lte pair in the Grade B Rec's structured_eligibility.
   Updates the Grade B fixture test to expect one age event instead of two.

   Per docs/reference/guidelines/statins.md."
   ```
7. **Run the suite locally:**
   ```sh
   cd api && pytest
   cd .. && pytest evals/
   ```
   Both must be green. If anything is red, fix before pushing.
8. **Run the manual test steps you'll put in the PR body.** Capture output.
9. **Push and open the PR:**
   ```sh
   git push -u origin feat/predicate-age-range
   gh pr create --base main --title "Add predicate_age_range for statin Grade B eligibility" \
     --body-file .pr-body.md
   ```
10. **Invoke the `pr-reviewer` subagent.** Post its output as a PR comment.
11. **Address the subagent's feedback** on the same branch. Re-run the subagent if the changes are non-trivial.
12. **Hand to the human.** Report the PR URL and the subagent's final verdict. Do not merge.
13. **After merge:**
    ```sh
    git checkout main && git pull && git branch -d feat/predicate-age-range
    ```
