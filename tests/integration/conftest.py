"""Integration test fixtures for Graph Interface Contract v2 compliance.

Provides shared fixtures for:
- Contract paths and sample graphs
- v2 JSON schema loading
- Omission ledger validation helpers
- Coverage score verification
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

# Project root paths
ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "tests" / "contracts"
SCHEMAS = ROOT / "schemas"


@pytest.fixture
def sample_contract_path() -> Path:
    """Path to test contract with known vulnerabilities (reentrancy)."""
    return CONTRACTS / "ReentrancyClassic.sol"


@pytest.fixture
def sample_safe_contract_path() -> Path:
    """Path to safe test contract (CEI pattern)."""
    return CONTRACTS / "ReentrancyCEI.sol"


@pytest.fixture
def sample_access_control_path() -> Path:
    """Path to contract with access control issues."""
    return CONTRACTS / "NoAccessGate.sol"


@pytest.fixture
def sample_graph(sample_contract_path):
    """Pre-built graph for integration tests.

    Uses ReentrancyClassic.sol which has a known reentrancy vulnerability.
    """
    from alphaswarm_sol.kg.builder import VKGBuilder

    builder = VKGBuilder(ROOT)
    return builder.build(sample_contract_path)


@pytest.fixture
def sample_safe_graph(sample_safe_contract_path):
    """Pre-built graph for safe contract.

    Uses ReentrancyCEI.sol which has proper CEI pattern.
    """
    from alphaswarm_sol.kg.builder import VKGBuilder

    builder = VKGBuilder(ROOT)
    return builder.build(sample_safe_contract_path)


@pytest.fixture
def v2_schema() -> Dict[str, Any]:
    """Load v2 JSON schema for validation."""
    schema_path = SCHEMAS / "graph_interface_v2.json"
    with open(schema_path) as f:
        return json.load(f)


@pytest.fixture
def graph_interface_validator():
    """Get Graph Interface Contract v2 validator."""
    from alphaswarm_sol.llm.interface_contract import GraphInterfaceValidator

    return GraphInterfaceValidator(strict=True)


@pytest.fixture
def graph_interface_validator_lenient():
    """Get lenient Graph Interface Contract v2 validator."""
    from alphaswarm_sol.llm.interface_contract import GraphInterfaceValidator

    return GraphInterfaceValidator(strict=False)


@pytest.fixture
def pattern_result_packager(sample_graph):
    """Get pattern result packager configured for test graph.

    Uses build hash derived from the test graph.
    """
    from alphaswarm_sol.llm.interface_contract import generate_build_hash
    from alphaswarm_sol.queries import PatternResultPackager

    # Generate build hash from source
    source_path = CONTRACTS / "ReentrancyClassic.sol"
    source_content = source_path.read_text() if source_path.exists() else ""
    build_hash = generate_build_hash(source_content)

    return PatternResultPackager(build_hash=build_hash, strict=True)


@pytest.fixture
def subgraph_extractor(sample_graph):
    """Get subgraph extractor for sample graph."""
    from alphaswarm_sol.kg.subgraph import SubgraphExtractor

    return SubgraphExtractor(sample_graph)


@pytest.fixture
def ppr_extractor(sample_graph):
    """Get PPR subgraph extractor for sample graph."""
    from alphaswarm_sol.kg.ppr_subgraph import PPRSubgraphExtractor

    return PPRSubgraphExtractor(sample_graph)


# ============================================================================
# Helper fixtures for validation
# ============================================================================


@pytest.fixture
def validate_v2_output(v2_schema):
    """Helper function to validate output against v2 schema."""

    def _validate(output: Dict[str, Any]) -> bool:
        try:
            import jsonschema

            jsonschema.validate(output, v2_schema)
            return True
        except jsonschema.ValidationError:
            return False

    return _validate


@pytest.fixture
def assert_omissions_present():
    """Helper to assert omission metadata is present in output."""

    def _assert(output: Dict[str, Any]) -> None:
        # Check global omissions
        assert "omissions" in output, "SILENT OMISSION: output missing omissions field"
        omissions = output["omissions"]
        assert "coverage_score" in omissions, "SILENT OMISSION: omissions missing coverage_score"
        assert "cut_set" in omissions, "SILENT OMISSION: omissions missing cut_set"
        assert "slice_mode" in omissions, "SILENT OMISSION: omissions missing slice_mode"

        # Check summary has coverage
        if "summary" in output:
            assert "coverage_score" in output["summary"], "summary missing coverage_score"
            assert "omissions_present" in output["summary"], "summary missing omissions_present"

        # Check per-finding omissions
        for i, finding in enumerate(output.get("findings", [])):
            assert "omissions" in finding, f"Finding[{i}] missing omissions field"
            finding_omissions = finding["omissions"]
            assert "coverage_score" in finding_omissions, f"Finding[{i}].omissions missing coverage_score"

    return _assert


@pytest.fixture
def assert_coverage_valid():
    """Helper to assert coverage score is in valid range."""

    def _assert(coverage_score: float) -> None:
        assert isinstance(coverage_score, (int, float)), f"coverage_score must be numeric, got {type(coverage_score)}"
        assert 0.0 <= coverage_score <= 1.0, f"coverage_score out of range: {coverage_score}"

    return _assert


@pytest.fixture
def get_function_node_ids(sample_graph):
    """Get function node IDs from sample graph."""

    def _get(visibility: str = None) -> list:
        node_ids = []
        for node_id, node in sample_graph.nodes.items():
            if node.type == "Function":
                if visibility is None or node.properties.get("visibility") == visibility:
                    node_ids.append(node_id)
        return node_ids

    return _get


# ============================================================================
# Mock fixtures for CLI testing
# ============================================================================


@pytest.fixture
def mock_cli_env(tmp_path):
    """Set up mock environment for CLI tests."""
    # Create a temporary directory with test contracts
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()

    # Copy a test contract
    src = CONTRACTS / "ReentrancyClassic.sol"
    if src.exists():
        (contracts_dir / "ReentrancyClassic.sol").write_text(src.read_text())

    return {
        "contracts_dir": contracts_dir,
        "tmp_path": tmp_path,
    }
