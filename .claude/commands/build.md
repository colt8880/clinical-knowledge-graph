---
description: Build a feature from docs/build/ end to end
---

You are building a feature specified in `docs/build/`.

The feature number is: $ARGUMENTS

## Steps

1. **Locate the spec.** Find the file in `docs/build/` whose name starts with the number provided (e.g., `02` → `docs/build/02-api-skeleton.md`). If the number is ambiguous or missing, stop and ask.

2. **Read the spec in full.** Do not skim. Every section (Context, Required reading, Scope, Constraints, Verification targets, DoD, Out of scope) is load-bearing.

3. **Read the required reading.** Every file listed under "Required reading" in the spec. Also read the root `CLAUDE.md` and `docs/workflow.md` if you haven't already this session.

4. **Check dependencies.** If the spec's "Depends on" lists features that are not `shipped` in `docs/build/README.md`, stop and surface the gap. Do not build on unfinished dependencies.

5. **Check for blockers.** Open questions in `docs/ISSUES.md` that the spec touches: resolve them in the spec before coding, or note the assumption you're making in the PR body.

6. **Branch.** Create the branch named in the spec (`feat/<slug>`, `chore/<slug>`, or `fix/<slug>`) off the latest `main`.

7. **Mark in-progress.** Update the row in `docs/build/README.md` from `pending` to `in-progress`.

8. **Implement.** Touch only files in the spec's Scope. If you need to edit a file outside Scope, stop and amend the spec first on its own branch.

9. **Test.** Hit every verification target. Tests must pass locally before opening the PR. Paste the output into the PR body.

10. **Update `docs/reference/build-status.md`.** Mark the backlog row as `shipped` (or `in-progress`) per the spec's DoD.

11. **Commit in logical chunks.** Each commit message explains the *why*.

12. **Push and open PR.** PR body: **Scope**, **Manual Test Steps**, **Manual Test Output**. Reference the spec file.

13. **Run `pr-reviewer` subagent.** Post output as a PR comment. Address blocking feedback on the same branch. Do not hand off to the human until the subagent is clean.

14. **Mark shipped after merge.** In a follow-up commit on `main` (or bundled with the next feature), flip the row in `docs/build/README.md` from `in-progress` to `shipped`.

## Rules

- One feature per session. Don't batch.
- If the spec is wrong or incomplete, stop and fix the spec on its own branch before building.
- Don't expand scope. The "Out of scope" list is binding.
- Never merge your own PR. The human merges.
