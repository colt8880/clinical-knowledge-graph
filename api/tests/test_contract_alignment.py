"""Contract alignment tests.

Validate that implementation and committed contract files stay in sync.
These tests codify the pr-reviewer's § Contract alignment rules as fast,
automated checks that run in the test suite.

See docs/build/10-contract-alignment-tests.md for the feature spec.
"""

import json
import re
from pathlib import Path

import yaml

# ── Paths ──────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = REPO_ROOT / "docs" / "contracts"
OPENAPI_PATH = CONTRACTS / "api.openapi.yaml"
PREDICATE_CATALOG_PATH = CONTRACTS / "predicate-catalog.yaml"
SEED_PATH = REPO_ROOT / "graph" / "seeds" / "statins.cypher"
BACKLOG_PATH = REPO_ROOT / "docs" / "reference" / "build-status.md"


# ── Helpers ────────────────────────────────────────────────────────────


def _load_openapi_contract() -> dict:
    """Load the committed api.openapi.yaml."""
    return yaml.safe_load(OPENAPI_PATH.read_text())


def _implemented_paths_from_app() -> dict:
    """Extract the FastAPI-generated OpenAPI schema (paths only)."""
    from app.main import app

    schema = app.openapi()
    return schema["paths"]


def _extract_predicates_from_eligibility(tree: dict | list) -> set[str]:
    """Recursively extract predicate names from a structured_eligibility tree.

    Composites (all_of, any_of, none_of) contain lists of sub-expressions.
    Everything else is a leaf predicate keyed by its name.
    """
    composites = {"all_of", "any_of", "none_of"}
    predicates: set[str] = set()

    if isinstance(tree, list):
        for item in tree:
            predicates |= _extract_predicates_from_eligibility(item)
    elif isinstance(tree, dict):
        for key, value in tree.items():
            if key in composites:
                # value is a list of sub-expressions
                predicates |= _extract_predicates_from_eligibility(value)
            else:
                # leaf predicate
                predicates.add(key)

    return predicates


def _extract_all_seed_predicates() -> set[str]:
    """Parse seed.cypher for structured_eligibility JSON and return all
    predicate names referenced."""
    seed_text = SEED_PATH.read_text()
    predicates: set[str] = set()

    # structured_eligibility values are single-quoted JSON strings in Cypher
    pattern = re.compile(
        r"structured_eligibility\s*=\s*'(\{.*?\})'",
        re.DOTALL,
    )
    for match in pattern.finditer(seed_text):
        tree = json.loads(match.group(1))
        predicates |= _extract_predicates_from_eligibility(tree)

    return predicates


def _load_catalog_predicate_names() -> set[str]:
    """Load predicate names from predicate-catalog.yaml."""
    catalog = yaml.safe_load(PREDICATE_CATALOG_PATH.read_text())
    names: set[str] = set()

    for section_key in ("composites", "predicates", "value_filters"):
        for entry in catalog.get(section_key, []):
            names.add(entry["name"])

    return names


def _parse_backlog_rows() -> list[dict]:
    """Parse the backlog table in docs/reference/build-status.md.

    Returns list of dicts with keys: num, feature, components, status,
    depends_on, spec, pr.
    """
    text = BACKLOG_PATH.read_text()
    rows: list[dict] = []

    # Table rows: | 01 | Feature name | components | status | depends | spec | pr |
    pattern = re.compile(
        r"^\|\s*(\d+)\s*\|"       # #
        r"\s*([^|]+?)\s*\|"       # Feature
        r"\s*([^|]*?)\s*\|"       # Components
        r"\s*(\w[\w-]*)\s*\|"     # Status
        r"\s*([^|]*?)\s*\|"       # Depends on
        r"\s*([^|]*?)\s*\|"       # Spec
        r"\s*([^|]*?)\s*\|",      # PR
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        rows.append({
            "num": match.group(1).zfill(2),
            "feature": match.group(2).strip(),
            "components": match.group(3).strip(),
            "status": match.group(4).strip(),
            "depends_on": match.group(5).strip(),
            "spec": match.group(6).strip(),
            "pr": match.group(7).strip(),
        })

    return rows


# ── Test 1: OpenAPI contract alignment ─────────────────────────────────


class TestOpenAPIAlignment:
    """Compare FastAPI-generated OpenAPI against the committed contract
    for implemented endpoints."""

    def test_implemented_paths_exist_in_contract(self):
        """Every path in the running app must appear in the committed
        api.openapi.yaml (possibly with different parameter names)."""
        contract = _load_openapi_contract()
        contract_paths = set(contract["paths"].keys())
        app_paths = set(_implemented_paths_from_app().keys())

        # Normalize: FastAPI uses {node_id}, contract uses {id}.
        # We compare path structure, not parameter names.
        def _normalize_path(p: str) -> str:
            return re.sub(r"\{[^}]+\}", "{param}", p)

        contract_normalized = {_normalize_path(p) for p in contract_paths}
        app_normalized = {_normalize_path(p) for p in app_paths}

        missing = app_normalized - contract_normalized
        assert not missing, (
            f"App paths not in contract: {missing}. "
            f"Update docs/contracts/api.openapi.yaml."
        )

    def test_implemented_methods_match_contract(self):
        """For each implemented path, the HTTP methods must match the contract."""
        contract = _load_openapi_contract()
        app_paths = _implemented_paths_from_app()

        # Build normalized contract lookup: normalized_path -> {methods}
        def _normalize(p: str) -> str:
            return re.sub(r"\{[^}]+\}", "{param}", p)

        contract_by_norm: dict[str, set[str]] = {}
        for path, ops in contract["paths"].items():
            norm = _normalize(path)
            methods = {m.lower() for m in ops if m.lower() not in ("parameters", "summary", "description")}
            contract_by_norm[norm] = methods

        for path, ops in app_paths.items():
            norm = _normalize(path)
            if norm not in contract_by_norm:
                continue  # test_implemented_paths_exist_in_contract covers this

            app_methods = {m.lower() for m in ops if m.lower() not in ("parameters", "summary", "description")}
            contract_methods = contract_by_norm[norm]
            assert app_methods == contract_methods, (
                f"Method mismatch for {path}: app={app_methods}, contract={contract_methods}"
            )

    def test_contract_server_url_matches_default(self):
        """The contract's server URL should match the default dev server."""
        contract = _load_openapi_contract()
        servers = contract.get("servers", [])
        urls = [s["url"] for s in servers]
        assert "http://localhost:8000" in urls, (
            f"Contract server URLs {urls} do not include http://localhost:8000"
        )

    def test_implemented_response_codes_in_contract(self):
        """For each implemented endpoint, response status codes defined in the
        app must be present in the contract."""
        contract = _load_openapi_contract()
        app_paths = _implemented_paths_from_app()

        def _normalize(p: str) -> str:
            return re.sub(r"\{[^}]+\}", "{param}", p)

        # Build contract lookup
        contract_lookup: dict[tuple[str, str], set[str]] = {}
        for path, ops in contract["paths"].items():
            norm = _normalize(path)
            for method, details in ops.items():
                if method.lower() in ("parameters", "summary", "description"):
                    continue
                if isinstance(details, dict) and "responses" in details:
                    codes = set(details["responses"].keys())
                    contract_lookup[(norm, method.lower())] = codes

        for path, ops in app_paths.items():
            norm = _normalize(path)
            for method, details in ops.items():
                if method.lower() in ("parameters", "summary", "description"):
                    continue
                if not isinstance(details, dict) or "responses" not in details:
                    continue
                app_codes = set(details["responses"].keys())
                key = (norm, method.lower())
                if key not in contract_lookup:
                    continue
                contract_codes = contract_lookup[key]
                missing = app_codes - contract_codes
                # Filter out default validation error responses FastAPI adds
                missing = {c for c in missing if c != "422"}
                assert not missing, (
                    f"{method.upper()} {path}: response codes {missing} "
                    f"in app but not in contract"
                )


# ── Test 2: Predicate catalog alignment ────────────────────────────────


class TestPredicateCatalogAlignment:
    """Validate that every predicate referenced in seed.cypher
    structured_eligibility trees has an entry in predicate-catalog.yaml."""

    def test_seed_predicates_are_in_catalog(self):
        """Every predicate name used in structured_eligibility must appear
        in the predicate catalog."""
        seed_predicates = _extract_all_seed_predicates()
        catalog_names = _load_catalog_predicate_names()

        missing = seed_predicates - catalog_names
        assert not missing, (
            f"Predicates in seed.cypher but not in predicate-catalog.yaml: {missing}. "
            f"Update docs/contracts/predicate-catalog.yaml."
        )

    def test_seed_has_predicates(self):
        """Sanity check: seed.cypher contains at least one predicate."""
        seed_predicates = _extract_all_seed_predicates()
        assert len(seed_predicates) > 0, "No predicates found in seed.cypher"

    def test_catalog_has_predicates(self):
        """Sanity check: predicate catalog is non-empty."""
        catalog_names = _load_catalog_predicate_names()
        assert len(catalog_names) > 0, "Predicate catalog is empty"


# ── Test 3: Backlog consistency ───────────────────────────────────────


class TestBacklogConsistency:
    """Validate the backlog in docs/reference/build-status.md:
    valid status values, no dependency cycles, referenced spec files
    exist, and every shipped row has a PR link."""

    VALID_STATUSES = {"pending", "in-progress", "shipped", "blocked"}

    def test_backlog_has_rows(self):
        """Sanity check: the backlog has parseable feature rows."""
        rows = _parse_backlog_rows()
        assert len(rows) > 0, "No feature rows found in docs/reference/build-status.md"

    def test_valid_status_values(self):
        """Every row must use one of the allowed status values."""
        rows = _parse_backlog_rows()
        for row in rows:
            assert row["status"] in self.VALID_STATUSES, (
                f"Feature {row['num']} ({row['feature']}) has invalid status "
                f"'{row['status']}'. Allowed: {self.VALID_STATUSES}"
            )

    def test_no_dependency_cycles(self):
        """The dependency graph must be a DAG — no cycles."""
        rows = _parse_backlog_rows()
        deps: dict[str, set[str]] = {}
        for row in rows:
            dep_str = row["depends_on"]
            if dep_str in ("—", "-", ""):
                deps[row["num"]] = set()
            else:
                # Parse "03" or "04, 05"
                dep_nums = {d.strip().zfill(2) for d in dep_str.split(",")}
                deps[row["num"]] = dep_nums

        # Detect cycles via DFS
        visited: set[str] = set()
        in_stack: set[str] = set()

        def _has_cycle(node: str) -> bool:
            if node in in_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for dep in deps.get(node, set()):
                if _has_cycle(dep):
                    return True
            in_stack.discard(node)
            return False

        for num in deps:
            assert not _has_cycle(num), (
                f"Dependency cycle detected involving feature {num}"
            )

    def test_referenced_spec_files_exist(self):
        """Every spec link in the backlog must point to an existing file."""
        rows = _parse_backlog_rows()
        for row in rows:
            spec = row["spec"]
            if spec in ("—", "-", ""):
                continue
            # Extract path from markdown link [NN](path)
            link_match = re.search(r"\[.*?\]\((.*?)\)", spec)
            if link_match:
                rel_path = link_match.group(1)
                # Resolve relative to backlog file location
                abs_path = (BACKLOG_PATH.parent / rel_path).resolve()
                assert abs_path.exists(), (
                    f"Feature {row['num']}: spec link '{rel_path}' "
                    f"resolves to {abs_path} which does not exist."
                )

    def test_shipped_rows_have_pr_link(self):
        """Every feature marked 'shipped' must have a PR link."""
        rows = _parse_backlog_rows()
        for row in rows:
            if row["status"] != "shipped":
                continue
            pr = row["pr"]
            assert pr not in ("—", "-", ""), (
                f"Feature {row['num']} ({row['feature']}) is shipped "
                f"but has no PR link in the backlog."
            )
