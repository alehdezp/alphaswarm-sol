"""Tests for VulnDiscoveryAgent and FindingBeadFactory.

Tests cover:
- FindingBeadFactory creation and saving
- VulnDiscoveryAgent execution workflow
- Context bead status transitions
- Evidence chain preservation
- Confidence filtering
- Max findings limit
- Integration: ContextMergeBead -> VulnDiscoveryAgent -> FindingBeads
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from alphaswarm_sol.agents.context.types import ContextBundle, RiskProfile, RiskCategory
from alphaswarm_sol.agents.orchestration import (
    FindingBeadFactory,
    FindingInput,
    EvidenceChain,
    VulnDiscoveryAgent,
    VulnDiscoveryConfig,
    VulnDiscoveryResult,
)
from alphaswarm_sol.beads.context_merge import ContextMergeBead, ContextBeadStatus
from alphaswarm_sol.beads.types import Severity
from alphaswarm_sol.kg.schema import KnowledgeGraph, Node


@pytest.fixture
def temp_beads_dir(tmp_path):
    """Temporary directory for bead storage."""
    beads_dir = tmp_path / "beads"
    beads_dir.mkdir()
    return beads_dir


@pytest.fixture
def finding_factory(temp_beads_dir):
    """Create FindingBeadFactory with temp directory."""
    return FindingBeadFactory(beads_dir=temp_beads_dir)


@pytest.fixture
def sample_context_bead():
    """Create sample ContextMergeBead for testing."""
    risk_profile = RiskProfile(
        access_risks=RiskCategory(present=True, notes="Admin multisig"),
        timing_risks=RiskCategory(present=True, notes="MEV exposure"),
    )

    context_bundle = ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="1. Check CEI pattern\n2. Look for external calls before state updates",
        semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        vql_queries=["FIND functions WHERE visibility = external AND has_external_call"],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=risk_profile,
        protocol_name="TestProtocol",
        target_scope=["contracts/Vault.sol"],
        token_estimate=3500,
    )

    return ContextMergeBead(
        id="CTX-test123",
        vulnerability_class="reentrancy/classic",
        protocol_name="TestProtocol",
        context_bundle=context_bundle,
        target_scope=["contracts/Vault.sol"],
        verification_score=0.95,
        pool_id="POOL-001",
    )


@pytest.fixture
def sample_evidence_chain():
    """Create sample EvidenceChain for testing."""
    return EvidenceChain(
        code_locations=["Vault.sol:52-55", "Vault.sol:60"],
        vulndoc_reference="reentrancy/classic",
        reasoning_steps=[
            "1. External call found at line 52",
            "2. State update at line 55 after external call",
            "3. CEI pattern violated",
        ],
        vql_queries=["FIND functions WHERE visibility = external"],
        protocol_context_applied=[
            "Protocol: TestProtocol",
            "Access risks: admin multisig",
        ],
        confidence="confirmed",
        confidence_reason="CEI pattern clearly violated",
    )


@pytest.fixture
def sample_finding_input(sample_evidence_chain):
    """Create sample FindingInput for testing."""
    return FindingInput(
        vulnerability_class="reentrancy",
        severity=Severity.CRITICAL,
        summary="Classic reentrancy in withdraw()",
        evidence_chain=sample_evidence_chain,
        context_bead_id="CTX-test123",
        pool_id="POOL-001",
    )


@pytest.fixture
def mock_graph():
    """Create mock KnowledgeGraph for testing."""
    graph = KnowledgeGraph()

    # Add sample node
    node = Node(
        id="func_withdraw",
        type="function",
        label="Vault.withdraw",
        properties={
            "name": "withdraw",
            "visibility": "external",
            "has_external_call": True,
        },
    )
    graph.add_node(node)

    return graph


# =============================================================================
# FindingBeadFactory Tests
# =============================================================================


def test_create_finding_success(finding_factory, sample_finding_input, sample_context_bead):
    """Test creating a finding bead from valid input."""
    bead = finding_factory.create_finding(sample_finding_input, sample_context_bead)

    assert bead.id.startswith("VKG-")
    assert bead.vulnerability_class == "reentrancy"
    assert bead.severity == Severity.CRITICAL
    assert bead.confidence == 0.95  # "confirmed" maps to 0.95
    assert bead.pattern_id == "reentrancy/classic"
    assert bead.pool_id == "POOL-001"


def test_create_finding_maps_confidence(finding_factory, sample_finding_input, sample_context_bead):
    """Test that confidence levels map correctly to float values."""
    confidence_levels = {
        "confirmed": 0.95,
        "likely": 0.80,
        "uncertain": 0.60,
        "rejected": 0.20,
    }

    for level, expected_float in confidence_levels.items():
        # Update evidence chain confidence
        sample_finding_input.evidence_chain.confidence = level

        bead = finding_factory.create_finding(sample_finding_input, sample_context_bead)

        assert bead.confidence == expected_float, f"Confidence '{level}' should map to {expected_float}"


def test_create_finding_preserves_evidence(finding_factory, sample_finding_input, sample_context_bead):
    """Test that evidence chain is preserved in bead metadata."""
    bead = finding_factory.create_finding(sample_finding_input, sample_context_bead)

    # Check metadata contains evidence chain
    assert "evidence_chain" in bead.metadata
    evidence = bead.metadata["evidence_chain"]

    assert evidence["code_locations"] == sample_finding_input.evidence_chain.code_locations
    assert evidence["vulndoc_reference"] == sample_finding_input.evidence_chain.vulndoc_reference
    assert evidence["reasoning_steps"] == sample_finding_input.evidence_chain.reasoning_steps
    assert evidence["vql_queries"] == sample_finding_input.evidence_chain.vql_queries
    assert evidence["confidence"] == "confirmed"


def test_save_finding_with_pool(finding_factory, sample_finding_input, sample_context_bead, temp_beads_dir):
    """Test that finding is saved to pool-specific directory."""
    bead = finding_factory.create_finding(sample_finding_input, sample_context_bead)
    path = finding_factory.save_finding(bead)

    # Check path structure
    expected_path = temp_beads_dir / "POOL-001" / "findings" / f"{bead.id}.json"
    assert path == expected_path
    assert path.exists()

    # Verify content
    with open(path) as f:
        data = json.load(f)

    assert data["id"] == bead.id
    assert data["vulnerability_class"] == "reentrancy"
    assert data["pool_id"] == "POOL-001"


def test_link_to_context_bead(finding_factory, sample_finding_input, sample_context_bead, temp_beads_dir):
    """Test bidirectional linking between finding and context beads."""
    bead = finding_factory.create_finding(sample_finding_input, sample_context_bead)

    # Initially no findings linked
    assert len(sample_context_bead.finding_bead_ids) == 0

    # Link finding to context
    finding_factory.link_to_context_bead(bead, sample_context_bead)

    # Check context bead updated
    assert bead.id in sample_context_bead.finding_bead_ids

    # Check context bead saved
    context_path = temp_beads_dir / "POOL-001" / "context" / f"{sample_context_bead.id}.json"
    assert context_path.exists()

    # Verify saved context bead has finding ID
    with open(context_path) as f:
        data = json.load(f)
    assert bead.id in data["finding_bead_ids"]


# =============================================================================
# VulnDiscoveryAgent Tests
# =============================================================================


def test_execute_success(finding_factory, sample_context_bead, mock_graph):
    """Test successful execution of vuln-discovery agent."""
    config = VulnDiscoveryConfig(
        max_findings_per_context=10,
        min_confidence_to_report="uncertain",
    )
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Mock VQL execution to return sample match
    with patch.object(agent, '_execute_vql') as mock_vql:
        mock_vql.return_value = {
            "matches": [
                {
                    "node_id": "func_withdraw",
                    "file_path": "Vault.sol",
                    "line_number": 52,
                    "description": "External call before state update",
                    "confidence": "likely",
                    "why_matched": "CEI pattern violation",
                }
            ]
        }

        result = agent.execute(sample_context_bead, graph=mock_graph)

    assert result.success is True
    assert result.context_bead_id == "CTX-test123"
    assert result.findings_count == 1
    assert len(result.findings) == 1
    assert len(result.vql_queries_executed) == 1
    assert sample_context_bead.status == ContextBeadStatus.COMPLETE


def test_execute_no_matches(finding_factory, sample_context_bead, mock_graph):
    """Test execution when VQL returns no matches."""
    config = VulnDiscoveryConfig(
        max_findings_per_context=10,
        min_confidence_to_report="uncertain",
    )
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Mock VQL execution to return no matches
    with patch.object(agent, '_execute_vql') as mock_vql:
        mock_vql.return_value = {"matches": []}

        result = agent.execute(sample_context_bead, graph=mock_graph)

    assert result.success is True
    assert result.findings_count == 0
    assert len(result.findings) == 0
    assert sample_context_bead.status == ContextBeadStatus.COMPLETE


def test_execute_max_findings_limit(finding_factory, sample_context_bead, mock_graph):
    """Test that max_findings_per_context is respected."""
    config = VulnDiscoveryConfig(
        max_findings_per_context=2,  # Limit to 2 findings
        min_confidence_to_report="uncertain",
    )
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Mock VQL to return 5 matches
    with patch.object(agent, '_execute_vql') as mock_vql:
        mock_vql.return_value = {
            "matches": [
                {
                    "node_id": f"func_{i}",
                    "file_path": "Vault.sol",
                    "line_number": 50 + i,
                    "description": f"Finding {i}",
                    "confidence": "likely",
                    "why_matched": "Test match",
                }
                for i in range(5)
            ]
        }

        result = agent.execute(sample_context_bead, graph=mock_graph)

    assert result.success is True
    assert result.findings_count == 2  # Limited to max
    assert len(result.findings) == 2


def test_execute_confidence_threshold(finding_factory, sample_context_bead, mock_graph):
    """Test that confidence threshold filtering works."""
    config = VulnDiscoveryConfig(
        max_findings_per_context=10,
        min_confidence_to_report="likely",  # Filter out "uncertain"
    )
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Mock VQL to return matches with different confidence levels
    with patch.object(agent, '_execute_vql') as mock_vql:
        mock_vql.return_value = {
            "matches": [
                {
                    "node_id": "func_1",
                    "file_path": "Vault.sol",
                    "line_number": 50,
                    "confidence": "uncertain",  # Should be filtered
                    "why_matched": "Test",
                },
                {
                    "node_id": "func_2",
                    "file_path": "Vault.sol",
                    "line_number": 60,
                    "confidence": "likely",  # Should pass
                    "why_matched": "Test",
                },
                {
                    "node_id": "func_3",
                    "file_path": "Vault.sol",
                    "line_number": 70,
                    "confidence": "confirmed",  # Should pass
                    "why_matched": "Test",
                },
            ]
        }

        result = agent.execute(sample_context_bead, graph=mock_graph)

    assert result.success is True
    assert result.findings_count == 2  # Only "likely" and "confirmed"


def test_execute_marks_context_complete(finding_factory, sample_context_bead, mock_graph):
    """Test that context bead status is updated correctly on success."""
    config = VulnDiscoveryConfig()
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Initial status
    assert sample_context_bead.status == ContextBeadStatus.PENDING

    # Mock VQL execution
    with patch.object(agent, '_execute_vql') as mock_vql:
        mock_vql.return_value = {"matches": []}

        result = agent.execute(sample_context_bead, graph=mock_graph)

    # Status should be COMPLETE
    assert sample_context_bead.status == ContextBeadStatus.COMPLETE
    assert result.success is True


def test_execute_marks_context_failed(finding_factory, sample_context_bead, mock_graph):
    """Test that context bead is marked FAILED on error."""
    config = VulnDiscoveryConfig()
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Mock VQL execution to raise error
    with patch.object(agent, '_execute_vql') as mock_vql:
        mock_vql.side_effect = Exception("VQL execution failed")

        result = agent.execute(sample_context_bead, graph=mock_graph)

    # Status should be FAILED
    assert sample_context_bead.status == ContextBeadStatus.FAILED
    assert result.success is False
    assert len(result.errors) > 0
    assert "VQL execution failed" in sample_context_bead.metadata.get("failure_reason", "")


def test_severity_inference():
    """Test that severity is correctly inferred from vulnerability class."""
    factory = FindingBeadFactory(beads_dir="./temp")
    config = VulnDiscoveryConfig()
    agent = VulnDiscoveryAgent(factory, config)

    severity_tests = [
        ("reentrancy/classic", Severity.CRITICAL),
        ("access-control/missing", Severity.HIGH),
        ("oracle/price-manipulation", Severity.HIGH),
        ("flash-loan/attack", Severity.CRITICAL),
        ("arithmetic/overflow", Severity.MEDIUM),
        ("unknown-class", Severity.MEDIUM),  # Default
    ]

    for vuln_class, expected_severity in severity_tests:
        inferred = agent._infer_severity(vuln_class)
        assert inferred == expected_severity, f"Expected {expected_severity} for {vuln_class}, got {inferred}"


# =============================================================================
# Integration Tests
# =============================================================================


def test_full_discovery_pipeline(finding_factory, sample_context_bead, mock_graph, temp_beads_dir):
    """Test full pipeline: ContextMergeBead -> VulnDiscoveryAgent -> FindingBeads."""
    config = VulnDiscoveryConfig(
        max_findings_per_context=5,
        min_confidence_to_report="uncertain",
    )
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Mock VQL execution
    with patch.object(agent, '_execute_vql') as mock_vql:
        mock_vql.return_value = {
            "matches": [
                {
                    "node_id": "func_withdraw",
                    "file_path": "Vault.sol",
                    "line_number": 52,
                    "description": "Reentrancy vulnerability",
                    "confidence": "confirmed",
                    "why_matched": "CEI violation detected",
                }
            ]
        }

        result = agent.execute(sample_context_bead, graph=mock_graph)

    # Verify result
    assert result.success is True
    assert result.findings_count == 1

    # Verify finding bead was created
    finding_id = result.findings[0]
    finding_path = temp_beads_dir / "POOL-001" / "findings" / f"{finding_id}.json"
    assert finding_path.exists()

    # Verify finding content
    with open(finding_path) as f:
        finding_data = json.load(f)

    assert finding_data["id"] == finding_id
    assert finding_data["vulnerability_class"] == "reentrancy/classic"
    assert finding_data["severity"] == "critical"
    assert "evidence_chain" in finding_data["metadata"]


def test_findings_linked_to_context(finding_factory, sample_context_bead, mock_graph, temp_beads_dir):
    """Test bidirectional linking: findings -> context, context -> findings."""
    config = VulnDiscoveryConfig()
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Mock VQL execution to return 2 findings
    with patch.object(agent, '_execute_vql') as mock_vql:
        mock_vql.return_value = {
            "matches": [
                {
                    "node_id": "func_1",
                    "file_path": "Vault.sol",
                    "line_number": 50,
                    "confidence": "likely",
                    "why_matched": "Test 1",
                },
                {
                    "node_id": "func_2",
                    "file_path": "Vault.sol",
                    "line_number": 60,
                    "confidence": "likely",
                    "why_matched": "Test 2",
                },
            ]
        }

        result = agent.execute(sample_context_bead, graph=mock_graph)

    # Verify findings created
    assert result.findings_count == 2

    # Verify context bead tracks findings
    assert len(sample_context_bead.finding_bead_ids) == 2
    for finding_id in result.findings:
        assert finding_id in sample_context_bead.finding_bead_ids

    # Verify findings have context_bead_id in metadata
    for finding_id in result.findings:
        finding_path = temp_beads_dir / "POOL-001" / "findings" / f"{finding_id}.json"
        with open(finding_path) as f:
            finding_data = json.load(f)

        assert finding_data["metadata"]["context_bead_id"] == "CTX-test123"
