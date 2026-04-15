#!/usr/bin/env python3
"""
Cross-check docs/contracts/predicate-catalog.yaml against docs/specs/predicate-dsl.md.

Rule: every predicate, composite, and value_filter declared in the catalog must
appear as a backticked identifier somewhere in the prose spec. Any catalog name
missing from the spec is a sync error.

Does not enforce the reverse (spec-only mentions are fine; the prose naturally
references non-catalog concepts like `value_quantity`, `effective_date`, etc.).

Exits non-zero on any mismatch.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("pyyaml not installed. pip install pyyaml\n")
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG = REPO_ROOT / "docs" / "contracts" / "predicate-catalog.yaml"
SPEC = REPO_ROOT / "docs" / "specs" / "predicate-dsl.md"

BACKTICK_IDENT = re.compile(r"`([a-z][a-z0-9_]*)\b")


def catalog_names(catalog: dict) -> list[tuple[str, str]]:
    """Return list of (section, name) for every named entry."""
    out: list[tuple[str, str]] = []
    for section in ("composites", "value_filters", "predicates"):
        for item in catalog.get(section, []):
            name = item.get("name")
            if name:
                out.append((section, name))
    return out


def spec_backtick_tokens(text: str) -> set[str]:
    return set(BACKTICK_IDENT.findall(text))


def main() -> int:
    catalog = yaml.safe_load(CATALOG.read_text())
    spec_text = SPEC.read_text()
    spec_tokens = spec_backtick_tokens(spec_text)

    missing: list[tuple[str, str]] = []
    for section, name in catalog_names(catalog):
        if name not in spec_tokens:
            missing.append((section, name))

    if missing:
        print("FAIL: catalog names not mentioned in predicate-dsl.md:", file=sys.stderr)
        for section, name in missing:
            print(f"  - {name} ({section})", file=sys.stderr)
        print(
            "\nEither add the name to the prose spec (wrapped in backticks) or "
            "remove it from predicate-catalog.yaml.",
            file=sys.stderr,
        )
        return 1

    print(f"OK:   all {sum(1 for _ in catalog_names(catalog))} catalog names appear in predicate-dsl.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
