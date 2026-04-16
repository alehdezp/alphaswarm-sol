"""Pytest plugin for Use Case Scenario discovery and parametrization.

Auto-discovers all scenario YAML files from
.planning/testing/scenarios/use-cases/ and creates parametrized fixtures
that can be filtered with pytest's -k flag.

Each scenario becomes a test case identified by its scenario ID
(e.g., test_use_cases[UC-AUDIT-001]).

Usage:
    pytest tests/scenarios/ -v
    pytest tests/scenarios/ -k "UC-AUDIT-001"
    pytest tests/scenarios/ -k "core"
    pytest tests/scenarios/ -k "audit"
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCENARIOS_DIR = PROJECT_ROOT / ".planning" / "testing" / "scenarios" / "use-cases"

ID_PATTERN = re.compile(r"^UC-[A-Z]+-\d{3}$")

VALID_WORKFLOWS = {
    "vrs-audit", "vrs-investigate", "vrs-verify", "vrs-debate",
    "vrs-attacker", "vrs-defender", "vrs-health-check",
    "graph-build", "tool-run", "failure",
}

VALID_CATEGORIES = {
    "audit", "investigate", "verify", "debate", "agents",
    "tools", "graph", "failure", "cross-workflow",
}

VALID_TIERS = {"core", "important", "mechanical"}
VALID_STATUSES = {"draft", "ready", "validated", "broken"}


# ---------------------------------------------------------------------------
# Scenario discovery
# ---------------------------------------------------------------------------


def discover_scenario_files() -> list[Path]:
    """Find all scenario YAML files recursively."""
    if not SCENARIOS_DIR.exists():
        return []
    files = []
    for path in sorted(SCENARIOS_DIR.rglob("*.yaml")):
        if path.name.startswith("_") or path.name.startswith("."):
            continue
        files.append(path)
    return files


def load_scenario(filepath: Path) -> dict[str, Any]:
    """Load a single scenario YAML file."""
    with open(filepath) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data).__name__} in {filepath}")
    data["_filepath"] = str(filepath)
    return data


def collect_scenarios() -> list[dict[str, Any]]:
    """Discover and load all scenarios."""
    scenarios = []
    for filepath in discover_scenario_files():
        try:
            scenario = load_scenario(filepath)
            scenarios.append(scenario)
        except Exception as e:
            # Create a sentinel scenario that will fail with a clear message
            scenarios.append({
                "id": f"LOAD-ERROR-{filepath.stem}",
                "name": f"Failed to load: {e}",
                "_filepath": str(filepath),
                "_load_error": str(e),
            })
    return scenarios


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Collect scenarios at module level for parametrize
_ALL_SCENARIOS = collect_scenarios()


def _scenario_id(scenario: dict[str, Any]) -> str:
    """Generate a test ID from the scenario."""
    return scenario.get("id", "UNKNOWN")


def pytest_collection_modifyitems(config: Any, items: list[Any]) -> None:
    """Add markers based on scenario metadata for -k filtering."""
    for item in items:
        # Check if this is a scenario test
        if "scenario" not in getattr(item, "fixturenames", []):
            continue

        scenario = None
        if hasattr(item, "callspec") and "scenario" in item.callspec.params:
            scenario = item.callspec.params["scenario"]

        if scenario is None:
            continue

        # Add markers for filtering
        tier = scenario.get("tier", "")
        category = scenario.get("category", "")
        workflow = scenario.get("workflow", "")
        status = scenario.get("status", "")

        if tier:
            item.add_marker(getattr(pytest.mark, tier))
        if category:
            item.add_marker(getattr(pytest.mark, category))
        if workflow:
            safe_workflow = workflow.replace("-", "_")
            item.add_marker(getattr(pytest.mark, safe_workflow))
        if status:
            item.add_marker(getattr(pytest.mark, status))

        # Skip broken scenarios
        if status == "broken":
            item.add_marker(pytest.mark.skip(reason="Scenario status is 'broken'"))

        # Check if evaluation contract exists -- only skip model construction tests
        if "model_construction" in item.name:
            links = scenario.get("links", {})
            if links:
                eval_contract = links.get("evaluation_contract", "")
                if eval_contract:
                    contract_path = PROJECT_ROOT / eval_contract
                    if not contract_path.exists():
                        item.add_marker(
                            pytest.mark.skip(
                                reason=f"Evaluation contract not found: {eval_contract}"
                            )
                        )


@pytest.fixture(
    params=_ALL_SCENARIOS,
    ids=[_scenario_id(s) for s in _ALL_SCENARIOS],
)
def scenario(request: pytest.FixtureRequest) -> dict[str, Any]:
    """Parametrized fixture providing each scenario as a dict."""
    return request.param


@pytest.fixture
def scenario_filepath(scenario: dict[str, Any]) -> Path:
    """Return the Path to the scenario YAML file."""
    return Path(scenario["_filepath"])


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT
