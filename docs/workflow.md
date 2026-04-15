# Development Workflow Runbook

## Per-Feature Loop

Every feature follows this loop: branch → build → test → manual-test → PR → review → merge.

### 1. Create a worktree

```bash
# From the main repo directory
git fetch origin main
git worktree add ../ckg-<feature-slug> -b <type>/<feature-slug> origin/main
cd ../ckg-<feature-slug>
```

Types: `feat/`, `fix/`, `chore/`, `refactor/`, `docs/`.

### 2. Do the work

Build the feature. Follow the directory-level CLAUDE.md for DoD.

### 3. Run tests locally

```bash
# Unit tests
cd api && pytest tests/unit -v && cd ..
cd ui && npm test && cd ..

# Integration (requires Neo4j)
docker compose up neo4j -d --wait
cd api && pytest tests/integration -v && cd ..

# Eval fixtures
cd api && pytest tests/eval -v && cd ..

# E2E
docker compose up -d --build --wait
cd ui && npx playwright test && cd ..
docker compose down
```

### 4. Execute manual test steps

Follow `docs/manual-tests/<feature>.md`. Paste output.

### 5. Commit and push

```bash
git add <files>
git commit -m "<type>: <description>"
git push -u origin <type>/<feature-slug>
```

### 6. Open PR

```bash
gh pr create --title "<type>: <description>" --body "$(cat <<'EOF'
## Scope
...

## Test Plan
- [x] Unit tests pass
- [x] Integration tests pass
- [x] Eval fixtures pass
- [x] E2e tests pass

## Manual Test Steps
See docs/manual-tests/<feature>.md

## Manual Test Output
<paste>

## ADR References
...

## Contract Changes
...
EOF
)"
```

### 7. Run subagent reviews

After the PR is created, invoke both review agents:

- **PR Reviewer**: checks test coverage, DoD adherence, determinism.
- **ADR Guardian**: checks ADR compliance, schema drift, scope creep.

Post their output as PR comments.

### 8. Address feedback, then request human review

### 9. After merge, clean up the worktree

```bash
cd /path/to/main/repo
git worktree remove ../ckg-<feature-slug>
```

---

## Claude Session Prompt Template

When starting a new Claude session for a feature, use this prompt:

```
You are working on the Clinical Knowledge Graph project.
Branch: <type>/<feature-slug>
Worktree: ../ckg-<feature-slug>

Read CLAUDE.md and the relevant directory-level CLAUDE.md files.
Read the ADRs in docs/decisions/ that are relevant to this feature.

Task: <description of what to build>

Follow the workflow in docs/workflow.md. Run all test tiers before opening the PR.
Execute the manual test steps and paste output into the PR body.
Invoke both subagent reviews (pr-reviewer, adr-guardian) and post as PR comments.
```

---

## Manual Test Protocol

1. Every PR that changes behavior must have a manual test doc in `docs/manual-tests/`.
2. Claude executes the steps and pastes output into the PR's "Manual Test Output" section.
3. If any step fails, the PR is not ready for review.
4. Reviewer verifies the pasted output matches expected results.
