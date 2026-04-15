#!/usr/bin/env python3
"""
Validate machine-readable contracts.

Checks:
  1. docs/contracts/predicate-catalog.yaml validates against
     docs/contracts/predicate-catalog.schema.json.
  2. docs/contracts/patient-context.schema.json is itself a valid JSON Schema
     (Draft 2020-12).
  3. Predicate names are unique across composites, value_filters, predicates.

Exits non-zero on any failure. Prints concrete diagnostics.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("pyyaml not installed. pip install pyyaml jsonschema\n")
    sys.exit(2)

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError:
    sys.stderr.write("jsonschema not installed. pip install pyyaml jsonschema\n")
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG = REPO_ROOT / "docs" / "contracts" / "predicate-catalog.yaml"
CATALOG_SCHEMA = REPO_ROOT / "docs" / "contracts" / "predicate-catalog.schema.json"
PATIENT_CTX_SCHEMA = REPO_ROOT / "docs" / "contracts" / "patient-context.schema.json"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"OK:   {msg}")


def validate_catalog() -> list[str]:
    errors: list[str] = []
    catalog = yaml.safe_load(CATALOG.read_text())
    schema = json.loads(CATALOG_SCHEMA.read_text())

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        errors.append(f"predicate-catalog.schema.json is not a valid JSON Schema: {e.message}")
        return errors

    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(catalog), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"predicate-catalog.yaml @ {path}: {err.message}")

    # Uniqueness across all named entries.
    seen: dict[str, str] = {}
    for section in ("composites", "value_filters", "predicates"):
        for item in catalog.get(section, []):
            name = item.get("name")
            if name is None:
                continue
            if name in seen:
                errors.append(
                    f"duplicate name '{name}' in {section} (also defined in {seen[name]})"
                )
            else:
                seen[name] = section
    return errors


def validate_patient_context_schema() -> list[str]:
    errors: list[str] = []
    schema = json.loads(PATIENT_CTX_SCHEMA.read_text())
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        errors.append(f"patient-context.schema.json is not a valid JSON Schema: {e.message}")
    return errors


def main() -> int:
    all_errors: list[str] = []

    cat_errors = validate_catalog()
    if cat_errors:
        for e in cat_errors:
            fail(e)
    else:
        ok("predicate-catalog.yaml conforms to predicate-catalog.schema.json")
    all_errors.extend(cat_errors)

    ctx_errors = validate_patient_context_schema()
    if ctx_errors:
        for e in ctx_errors:
            fail(e)
    else:
        ok("patient-context.schema.json is a valid Draft 2020-12 JSON Schema")
    all_errors.extend(ctx_errors)

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
