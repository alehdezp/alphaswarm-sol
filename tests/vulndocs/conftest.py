"""Shared pytest fixtures for VulnDocs tests.

Provides reusable fixtures for:
- Temporary vulndocs directories with templates
- Sample vulnerabilities and patterns
- CLI test runner

Part of Plan 05.4-08: Integration Testing
"""

from pathlib import Path
import shutil
import yaml
import pytest
from typer.testing import CliRunner

from alphaswarm_sol.vulndocs.scaffold import scaffold_vulnerability


@pytest.fixture
def tmp_vulndocs(tmp_path):
    """Create temporary vulndocs folder with templates copied from project.

    This fixture ensures tests have access to the actual template files
    for scaffolding operations.

    Args:
        tmp_path: pytest's built-in tmp_path fixture

    Returns:
        Path to temporary vulndocs directory with .meta/ copied
    """
    vulndocs_root = tmp_path / "vulndocs"
    vulndocs_root.mkdir()

    # Copy templates from project to temp directory (new .meta/ structure)
    meta_src = Path("vulndocs") / ".meta"
    if meta_src.exists():
        meta_dst = vulndocs_root / ".meta"
        shutil.copytree(meta_src, meta_dst)

    return vulndocs_root


@pytest.fixture
def sample_vulnerability(tmp_vulndocs):
    """Create a sample vulnerability for testing.

    Uses scaffold to create a complete vulnerability structure,
    then fixes the template values to have valid data.

    Args:
        tmp_vulndocs: Fixture providing temporary vulndocs directory

    Returns:
        Path to created vulnerability folder
    """
    # Scaffold vulnerability
    vuln_path = scaffold_vulnerability(
        root=tmp_vulndocs,
        category="reentrancy",
        subcategory="classic",
        severity="critical",
    )

    # Fix template values to be valid
    index_path = vuln_path / "index.yaml"
    with open(index_path) as f:
        index_data = yaml.safe_load(f)

    # Replace template placeholders with valid values
    index_data["id"] = "reentrancy-classic"
    index_data["category"] = "reentrancy"
    index_data["subcategory"] = "classic"
    index_data["severity"] = "critical"
    index_data["vulndoc"] = "reentrancy/classic"
    index_data["semantic_triggers"] = ["TRANSFERS_ETH", "WRITES_BALANCE", "CALLS_EXTERNAL"]
    index_data["vql_queries"] = [
        "FIND functions WHERE has_operation:TRANSFERS_ETH AND has_operation:WRITES_BALANCE"
    ]
    index_data["graph_patterns"] = ["R:bal->X:out->W:bal"]
    index_data["reasoning_template"] = "1. Find external calls\n2. Check if balance written after call"

    with open(index_path, "w") as f:
        yaml.dump(index_data, f)

    return vuln_path


@pytest.fixture
def sample_pattern(sample_vulnerability):
    """Create a sample pattern for testing.

    Args:
        sample_vulnerability: Fixture providing vulnerability folder

    Returns:
        Path to created pattern file
    """
    patterns_dir = sample_vulnerability / "patterns"
    patterns_dir.mkdir(exist_ok=True)

    pattern_data = {
        "id": "vm-001-classic-reentrancy",
        "name": "Classic Reentrancy",
        "severity": "critical",
        "lens": ["Reentrancy"],
        "description": "Classic reentrancy via external call before state update",
    }

    pattern_path = patterns_dir / "vm-001-classic-reentrancy.yaml"
    with open(pattern_path, "w") as f:
        yaml.dump(pattern_data, f)

    # Update index.yaml to reference pattern
    index_path = sample_vulnerability / "index.yaml"
    with open(index_path) as f:
        index_data = yaml.safe_load(f)

    index_data["patterns"] = ["vm-001-classic-reentrancy"]

    with open(index_path, "w") as f:
        yaml.dump(index_data, f)

    return pattern_path


@pytest.fixture
def sample_framework(tmp_vulndocs):
    """Create a framework with multiple entries for testing.

    Creates 2-3 categories with vulnerabilities for aggregation tests.

    Args:
        tmp_vulndocs: Fixture providing temporary vulndocs directory

    Returns:
        Path to temporary vulndocs directory with multiple entries
    """
    # Create oracle category
    oracle_vuln = tmp_vulndocs / "oracle" / "price-manipulation"
    oracle_vuln.mkdir(parents=True)

    oracle_index = {
        "id": "oracle-price-manipulation",
        "category": "oracle",
        "subcategory": "price-manipulation",
        "severity": "critical",
        "vulndoc": "oracle/price-manipulation",
        "semantic_triggers": ["READS_ORACLE", "TRANSFERS_ETH"],
    }

    with open(oracle_vuln / "index.yaml", "w") as f:
        yaml.dump(oracle_index, f)

    # Create reentrancy category
    reentrancy_vuln = tmp_vulndocs / "reentrancy" / "classic"
    reentrancy_vuln.mkdir(parents=True)

    reentrancy_index = {
        "id": "reentrancy-classic",
        "category": "reentrancy",
        "subcategory": "classic",
        "severity": "high",
        "vulndoc": "reentrancy/classic",
        "semantic_triggers": ["TRANSFERS_ETH", "WRITES_BALANCE"],
    }

    with open(reentrancy_vuln / "index.yaml", "w") as f:
        yaml.dump(reentrancy_index, f)

    # Create access-control category
    access_vuln = tmp_vulndocs / "access-control" / "weak-auth"
    access_vuln.mkdir(parents=True)

    access_index = {
        "id": "access-control-weak-auth",
        "category": "access-control",
        "subcategory": "weak-auth",
        "severity": "medium",
        "vulndoc": "access-control/weak-auth",
        "semantic_triggers": ["WRITES_STATE", "CALLS_EXTERNAL"],
    }

    with open(access_vuln / "index.yaml", "w") as f:
        yaml.dump(access_index, f)

    return tmp_vulndocs


@pytest.fixture
def cli_runner():
    """Typer CLI test runner for testing CLI commands.

    Returns:
        CliRunner instance from typer.testing
    """
    return CliRunner()
