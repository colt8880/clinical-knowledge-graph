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
SEED_PATH = REPO_ROOT / "graph" / "seed.cypher"
BUILD_README_PATH = REPO_ROOT / "docs" / "build" / "README.md"
BUILD_STATUS_PATH = REPO_ROOT / "docs" / "reference" / "build-status.md"


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


def _parse_build_readme_table() -> dict[str, str]:
    """Parse the backlog table in docs/build/README.md.

    Returns {feature_number: status} e.g. {"01": "shipped", "10": "pending"}.
    """
    text = BUILD_README_PATH.read_text()
    rows: dict[str, str] = {}

    # Table rows: | 01 | Graph seed ... | shipped | — |
    pattern = re.compile(
        r"^\|\s*(\d+)\s*\|[^|]+\|\s*(\w[\w-]*)\s*\|",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        num = match.group(1).zfill(2)
        status = match.group(2).strip()
        rows[num] = status

    return rows


def _parse_build_status_shipped_components() -> set[str]:
    """Extract component names that are in 'tested' or 'implemented' or later
    states from docs/reference/build-status.md.

    Returns set of component description strings (first column values)
    with states beyond spec-only.
    """
    text = BUILD_STATUS_PATH.read_text()
    active: set[str] = set()

    # Table rows: | Component name | state | Notes |
    pattern = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*(implemented|tested|scaffolded|live)\s*\|",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        component = match.group(1).strip()
        active.add(component)

    return active


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


# ── Test 3: Build tracking consistency ─────────────────────────────────


class TestBuildStatusConsistency:
    """Validate that docs/build/README.md and docs/reference/build-status.md
    are consistent — no feature marked shipped in one but not reflected
    in the other."""

    def test_shipped_features_have_build_status_updates(self):
        """Every feature marked 'shipped' in docs/build/README.md should
        have corresponding state beyond 'spec-only' in build-status.md
        for its component."""
        readme_statuses = _parse_build_readme_table()
        build_status_components = _parse_build_status_shipped_components()

        # Map feature numbers to their expected build-status component
        # keywords. A shipped feature should have moved its component
        # beyond spec-only. When adding a new feature, add its mapping here.
        feature_component_keywords: dict[str, list[str]] = {
            "01": ["seed", "statin seed"],
            "02": ["fastapi", "skeleton"],
            "10": ["contract alignment"],
            "11": ["github actions", "ci"],
        }

        shipped = {num for num, status in readme_statuses.items() if status == "shipped"}

        for num in shipped:
            keywords = feature_component_keywords.get(num)
            assert keywords is not None, (
                f"Feature {num} is 'shipped' in docs/build/README.md but has "
                f"no keyword mapping in test_contract_alignment.py. Add an "
                f"entry to feature_component_keywords."
            )

            # Check that at least one active component matches a keyword
            found = False
            for component in build_status_components:
                component_lower = component.lower()
                if any(kw in component_lower for kw in keywords):
                    found = True
                    break

            assert found, (
                f"Feature {num} is 'shipped' in docs/build/README.md but no "
                f"matching component (keywords: {keywords}) is beyond "
                f"'spec-only' in docs/reference/build-status.md."
            )

    def test_build_readme_has_features(self):
        """Sanity check: the build README has parseable feature rows."""
        rows = _parse_build_readme_table()
        assert len(rows) > 0, "No feature rows found in docs/build/README.md"

    def test_build_status_has_components(self):
        """Sanity check: build-status.md has parseable component rows."""
        components = _parse_build_status_shipped_components()
        assert len(components) > 0, "No active components in docs/reference/build-status.md"
