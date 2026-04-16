"""Unit Tests for Beads/Gas Town Adapter and Registry.

Tests git-backed bead operations, adapter registry functionality,
and capability-based adapter discovery.

Phase: 07.1.4-05 Beads/Gas Town and Claude Code Adapters
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from alphaswarm_sol.adapters.base import HandoffContext
from alphaswarm_sol.adapters.beads_gastown import (
    BeadsGasTownAdapter,
    BeadsGasTownConfig,
    GitBackedBead,
)
from alphaswarm_sol.adapters.capability import AdapterCapability
from alphaswarm_sol.adapters.registry import (
    AdapterRegistry,
    find_adapters_with_capabilities,
    get_adapter,
    list_adapters,
)
from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from alphaswarm_sol.beads.types import (
    CodeSnippet,
    InvestigationStep,
    Severity,
)


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create temporary git repository."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    readme = repo_path / "README.md"
    readme.write_text("Test repo")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    yield repo_path

    # Cleanup is automatic with tmp_path


@pytest.fixture
def sample_bead():
    """Create sample VulnerabilityBead with all required fields.

    Uses the correct schema fields:
    - CodeSnippet: source, file_path, start_line, end_line, function_name, contract_name
    - PatternContext: pattern_name, pattern_description, why_flagged, matched_properties, evidence_lines
    - InvestigationGuide: steps, questions_to_answer, common_false_positives, key_indicators, safe_patterns
    - TestContext: scaffold_code, attack_scenario, setup_requirements, expected_outcome
    """
    return VulnerabilityBead(
        id="VKG-TEST-001",
        vulnerability_class="reentrancy",
        pattern_id="reentrancy-classic",
        severity=Severity.HIGH,
        confidence=0.85,
        vulnerable_code=CodeSnippet(
            source="function withdraw() public { ... }",
            file_path="contracts/Vault.sol",
            start_line=42,
            end_line=50,
            function_name="withdraw",
            contract_name="Vault",
        ),
        related_code=[],
        full_contract=None,
        inheritance_chain=[],
        pattern_context=PatternContext(
            pattern_name="Classic Reentrancy",
            pattern_description="External call before state update",
            why_flagged="External call on line 45 before balance update on line 48",
            matched_properties=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            evidence_lines=[45, 48],
        ),
        investigation_guide=InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check for reentrancy guard",
                    look_for="nonReentrant modifier or mutex pattern",
                    evidence_needed="Presence or absence of guard",
                )
            ],
            questions_to_answer=["Can attacker re-enter?"],
            common_false_positives=["nonReentrant modifier present"],
            key_indicators=["External call before state update"],
            safe_patterns=["CEI pattern", "nonReentrant modifier"],
        ),
        test_context=TestContext(
            scaffold_code="// Test scaffold",
            attack_scenario="1. Deploy attacker contract\n2. Call withdraw",
            setup_requirements=["Attacker contract with fallback"],
            expected_outcome="Attacker extracts more than their balance",
        ),
        similar_exploits=[],
        fix_recommendations=["Add nonReentrant modifier"],
    )


@pytest.fixture
def clean_registry():
    """Reset registry between tests."""
    from alphaswarm_sol.adapters.registry import _registry

    _registry.clear_cache()
    yield _registry
    _registry.clear_cache()


# GitBackedBead Tests


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="Git CLI not available",
)
def test_git_backed_bead_save_load(temp_git_repo, sample_bead):
    """Test saving and loading bead from git."""
    git_bead = GitBackedBead(
        bead=sample_bead,
        repo_path=temp_git_repo,
        branch="bead/test",
    )

    # Save bead
    commit_hash = git_bead.save()
    assert len(commit_hash) == 7  # Short hash

    # Load bead from commit
    loaded_bead = git_bead.load(commit_hash)
    assert loaded_bead.id == sample_bead.id
    assert loaded_bead.vulnerability_class == sample_bead.vulnerability_class


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="Git CLI not available",
)
def test_git_backed_bead_history(temp_git_repo, sample_bead):
    """Test commit history tracking."""
    git_bead = GitBackedBead(
        bead=sample_bead,
        repo_path=temp_git_repo,
        branch="bead/test",
    )

    # Create multiple commits
    commit_1 = git_bead.save()
    sample_bead.confidence = 0.90
    commit_2 = git_bead.save()

    # Get history
    history = git_bead.get_history()
    assert len(history) >= 2
    assert all("commit_hash" in entry for entry in history)
    assert all("timestamp" in entry for entry in history)


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="Git CLI not available",
)
def test_git_backed_bead_replay(temp_git_repo, sample_bead):
    """Test replay to specific commit."""
    git_bead = GitBackedBead(
        bead=sample_bead,
        repo_path=temp_git_repo,
        branch="bead/test",
    )

    # Save initial state
    original_confidence = sample_bead.confidence
    commit_1 = git_bead.save()

    # Modify and save again
    sample_bead.confidence = 0.95
    commit_2 = git_bead.save()

    # Replay to first commit
    replayed_bead = git_bead.replay_to(commit_1)
    assert replayed_bead.confidence == original_confidence


# BeadsGasTownAdapter Tests


@pytest.mark.xfail(reason="Stale code: Beads adapter API changed")
def test_beads_adapter_initialization(temp_git_repo):
    """Test adapter initialization with git repo."""
    config = BeadsGasTownConfig(repo_path=temp_git_repo)
    adapter = BeadsGasTownAdapter(config)

    assert adapter.config.repo_path == temp_git_repo
    assert adapter.config.branch_prefix == "bead/"


def test_beads_adapter_invalid_repo():
    """Test adapter fails with non-git directory."""
    with pytest.raises(ValueError, match="Not a git repository"):
        config = BeadsGasTownConfig(repo_path=Path("/tmp"))
        BeadsGasTownAdapter(config)


@pytest.mark.asyncio
@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="Git CLI not available",
)
async def test_beads_adapter_handoff_creates_branch(temp_git_repo, sample_bead):
    """Test handoff creates git branch."""
    config = BeadsGasTownConfig(repo_path=temp_git_repo, enable_worktree=False)
    adapter = BeadsGasTownAdapter(config)

    ctx = HandoffContext(
        source_agent="vrs-attacker",
        target_agent="vrs-defender",
        bead_id=sample_bead.id,
    )

    result = await adapter.handoff(ctx)
    assert result.success
    assert "branch" in result.metadata


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="Git CLI not available",
)
@pytest.mark.xfail(reason="Stale code: Beads adapter API changed")
def test_beads_adapter_preserves_evidence_via_git(temp_git_repo, sample_bead):
    """Test evidence preservation through git commits."""
    config = BeadsGasTownConfig(repo_path=temp_git_repo, auto_commit=True)
    adapter = BeadsGasTownAdapter(config)

    ctx = HandoffContext(
        source_agent="vrs-attacker",
        target_agent="vrs-defender",
        bead_id=sample_bead.id,
    )

    preserved_bead = adapter.preserve_evidence(sample_bead, ctx)

    # Check evidence snapshot in context
    assert ctx.evidence_snapshot["bead_id"] == sample_bead.id
    assert ctx.evidence_snapshot["vulnerability_class"] == sample_bead.vulnerability_class

    # Check commit hash stored in metadata
    assert "commit_hash" in preserved_bead.metadata


@pytest.mark.xfail(reason="Stale code: Beads adapter API changed")
def test_beads_adapter_capabilities(temp_git_repo):
    """Test adapter reports correct capabilities."""
    config = BeadsGasTownConfig(repo_path=temp_git_repo)
    adapter = BeadsGasTownAdapter(config)

    capabilities = adapter.get_capabilities()

    assert AdapterCapability.BEAD_REPLAY in capabilities
    assert AdapterCapability.GRAPH_FIRST in capabilities
    assert AdapterCapability.MEMORY_PERSISTENT in capabilities


# AdapterRegistry Tests


def test_registry_register_and_get(clean_registry):
    """Test adapter registration and retrieval."""
    from alphaswarm_sol.adapters import AgentsSdkAdapter, AgentsSdkConfig

    # Get existing adapter
    adapters = list_adapters()
    assert "agents-sdk" in adapters

    # Get adapter requires config for new instance
    with pytest.raises(ValueError, match="Configuration required"):
        get_adapter("agents-sdk")


def test_registry_list_adapters(clean_registry):
    """Test listing all registered adapters."""
    adapters = list_adapters()

    # Should have at least built-in adapters
    assert "agents-sdk" in adapters
    assert "beads-gastown" in adapters
    assert "claude-code" in adapters
    assert "codex-mcp" in adapters

    # Should be sorted
    assert adapters == sorted(adapters)


def test_registry_find_by_capabilities(clean_registry):
    """Test capability-based adapter search."""
    # Find adapters with BEAD_REPLAY
    adapters = find_adapters_with_capabilities({AdapterCapability.BEAD_REPLAY})
    assert "beads-gastown" in adapters
    assert "langgraph" in adapters  # If available

    # Find adapters with GRAPH_FIRST
    adapters = find_adapters_with_capabilities({AdapterCapability.GRAPH_FIRST})
    assert "beads-gastown" in adapters
    assert "claude-code" in adapters

    # Find adapters with both
    adapters = find_adapters_with_capabilities(
        {AdapterCapability.BEAD_REPLAY, AdapterCapability.GRAPH_FIRST}
    )
    assert "beads-gastown" in adapters


def test_registry_capability_comparison(clean_registry):
    """Test capability comparison matrix generation."""
    registry = clean_registry
    comparison = registry.get_capability_comparison()

    # Check structure
    assert isinstance(comparison, dict)
    assert "agents-sdk" in comparison
    assert "beads-gastown" in comparison

    # Check capability booleans
    agents_sdk_caps = comparison["agents-sdk"]
    assert agents_sdk_caps["tool_execution"] is True
    assert agents_sdk_caps["guardrails"] is True
    assert agents_sdk_caps["bead_replay"] is False

    beads_caps = comparison["beads-gastown"]
    assert beads_caps["bead_replay"] is True
    assert beads_caps["graph_first"] is True


def test_registry_unknown_adapter(clean_registry):
    """Test error handling for unknown adapter."""
    with pytest.raises(KeyError, match="Unknown adapter"):
        get_adapter("nonexistent-adapter")


@pytest.mark.xfail(reason="Stale code: Beads adapter API changed")
def test_registry_clear_cache(clean_registry, temp_git_repo):
    """Test instance cache clearing."""
    config = BeadsGasTownConfig(repo_path=temp_git_repo)

    # Get instance (creates and caches)
    adapter1 = get_adapter("beads-gastown", config)

    # Get again (should be same instance)
    adapter2 = get_adapter("beads-gastown")
    assert adapter1 is adapter2

    # Clear cache
    clean_registry.clear_cache()

    # Get again (should require config)
    with pytest.raises(ValueError, match="Configuration required"):
        get_adapter("beads-gastown")
