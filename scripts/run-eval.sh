#!/usr/bin/env bash
# Convenience wrapper for the eval harness.
# Usage:
#   ./scripts/run-eval.sh                                    # all fixtures, all arms
#   ./scripts/run-eval.sh --arm a                            # all fixtures, arm A
#   ./scripts/run-eval.sh --fixture statins/01-high-risk-55m-smoker --arm c

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
EVALS_DIR="$REPO_ROOT/evals"

cd "$EVALS_DIR"

# Default to --all if no --fixture is specified
if [[ ! " $* " =~ " --fixture " ]]; then
    exec uv run python -m harness --all "$@"
else
    exec uv run python -m harness "$@"
fi
