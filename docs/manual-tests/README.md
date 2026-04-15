# Manual Test Documentation

Each feature that ships with a PR must have a corresponding manual test document in this directory.

## Template

Create a file named `<feature>.md` with this structure:

```markdown
# Manual Test: <Feature Name>

## Prerequisites
- Services running: `docker compose up -d`
- Seed data loaded (if applicable)

## Steps

1. Step description
   - **Action**: What to do (curl command, browser action, etc.)
   - **Expected**: What should happen
   - **Actual**: _paste output here_

2. ...

## Result
- [ ] All steps passed
```

## Rule

**Claude must execute every step in the manual test doc and paste the actual output into the PR body before requesting review.** This is non-negotiable. The PR template has a "Manual Test Output" section for this purpose.

If a step fails, the PR is not ready for review. Fix the issue first.
