"""Tests for ContextMergeBead and ContextBeadFactory.

Tests cover:
- ContextMergeBead dataclass creation and serialization
- ContextBeadFactory bead creation and storage
- Pool-based organization
- Status management and tracking
"""

import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from alphaswarm_sol.agents.context import (
    ContextBeadFactory,
    ContextBundle,
    ContextMerger,
    ContextVerifier,
    RiskCategory,
    RiskProfile,
)
from alphaswarm_sol.beads.context_merge import ContextBeadStatus, ContextMergeBead


@pytest.fixture
def sample_context_bundle():
    """Create sample context bundle for testing."""
    risk_profile = RiskProfile(
        oracle_risks=RiskCategory(present=True, notes="Uses Chainlink", confidence="certain"),
        access_risks=RiskCategory(present=True, notes="Admin multisig", confidence="inferred"),
    )

    return ContextBundle(
        vulnerability_class="reentrancy/classic",
        reasoning_template="1. Check CEI pattern\n2. Look for state changes after external calls",
        semantic_triggers=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        vql_queries=["FIND functions WHERE has_external_call AND writes_state"],
        graph_patterns=["R:bal->X:out->W:bal"],
        risk_profile=risk_profile,
        protocol_name="TestProtocol",
        target_scope=["contracts/Vault.sol"],
        token_estimate=3500,
    )


@pytest.fixture
def sample_bead(sample_context_bundle):
    """Create sample ContextMergeBead for testing."""
    timestamp = datetime(2026, 1, 22, 12, 0, 0)
    bead_id = ContextMergeBead.generate_id(
        "reentrancy/classic",
        "TestProtocol",
        timestamp,
    )

    return ContextMergeBead(
        id=bead_id,
        vulnerability_class="reentrancy/classic",
        protocol_name="TestProtocol",
        context_bundle=sample_context_bundle,
        target_scope=["contracts/Vault.sol"],
        verification_score=0.95,
        verification_warnings=["Minor: reasoning template could have more steps"],
        status=ContextBeadStatus.PENDING,
        created_at=timestamp,
        created_by="test-agent",
        pool_id="test-pool",
    )


# ============================================================================
# ContextMergeBead Tests
# ============================================================================


def test_bead_creation(sample_context_bundle):
    """Test basic bead creation with all fields."""
    timestamp = datetime.now()
    bead_id = ContextMergeBead.generate_id(
        "reentrancy/classic",
        "TestProtocol",
        timestamp,
    )

    bead = ContextMergeBead(
        id=bead_id,
        vulnerability_class="reentrancy/classic",
        protocol_name="TestProtocol",
        context_bundle=sample_context_bundle,
        target_scope=["contracts/Vault.sol"],
        verification_score=0.95,
        verification_warnings=[],
        status=ContextBeadStatus.PENDING,
        created_at=timestamp,
        created_by="test-agent",
        pool_id="test-pool",
    )

    assert bead.id == bead_id
    assert bead.vulnerability_class == "reentrancy/classic"
    assert bead.protocol_name == "TestProtocol"
    assert bead.verification_score == 0.95
    assert bead.status == ContextBeadStatus.PENDING
    assert bead.pool_id == "test-pool"
    assert len(bead.finding_bead_ids) == 0


def test_bead_id_generation():
    """Test that bead IDs are deterministic and unique."""
    timestamp = datetime(2026, 1, 22, 12, 0, 0)

    # Same inputs -> same ID
    id1 = ContextMergeBead.generate_id("reentrancy/classic", "Protocol1", timestamp)
    id2 = ContextMergeBead.generate_id("reentrancy/classic", "Protocol1", timestamp)
    assert id1 == id2

    # Different vuln class -> different ID
    id3 = ContextMergeBead.generate_id("access-control/weak", "Protocol1", timestamp)
    assert id1 != id3

    # Different protocol -> different ID
    id4 = ContextMergeBead.generate_id("reentrancy/classic", "Protocol2", timestamp)
    assert id1 != id4

    # Different timestamp -> different ID
    timestamp2 = datetime(2026, 1, 22, 13, 0, 0)
    id5 = ContextMergeBead.generate_id("reentrancy/classic", "Protocol1", timestamp2)
    assert id1 != id5

    # All IDs start with CTX-
    assert id1.startswith("CTX-")
    assert id3.startswith("CTX-")
    assert id5.startswith("CTX-")


def test_bead_serialization_roundtrip(sample_bead):
    """Test to_dict/from_dict preserves data."""
    data = sample_bead.to_dict()

    # Check type field
    assert data["type"] == "context_merge"

    # Reconstruct
    reconstructed = ContextMergeBead.from_dict(data)

    assert reconstructed.id == sample_bead.id
    assert reconstructed.vulnerability_class == sample_bead.vulnerability_class
    assert reconstructed.protocol_name == sample_bead.protocol_name
    assert reconstructed.verification_score == sample_bead.verification_score
    assert reconstructed.status == sample_bead.status
    assert reconstructed.pool_id == sample_bead.pool_id
    assert reconstructed.target_scope == sample_bead.target_scope


def test_bead_yaml_roundtrip(sample_bead):
    """Test to_yaml/from_yaml preserves data."""
    yaml_str = sample_bead.to_yaml()

    # Should be valid YAML
    parsed = yaml.safe_load(yaml_str)
    assert parsed["type"] == "context_merge"
    assert parsed["vulnerability_class"] == "reentrancy/classic"

    # Reconstruct
    reconstructed = ContextMergeBead.from_yaml(yaml_str)

    assert reconstructed.id == sample_bead.id
    assert reconstructed.vulnerability_class == sample_bead.vulnerability_class
    assert reconstructed.protocol_name == sample_bead.protocol_name
    assert reconstructed.verification_score == sample_bead.verification_score


def test_bead_json_roundtrip(sample_bead):
    """Test to_json/from_dict(json.loads) works."""
    json_str = sample_bead.to_json()

    # Should be valid JSON
    parsed = json.loads(json_str)
    assert parsed["type"] == "context_merge"
    assert parsed["vulnerability_class"] == "reentrancy/classic"

    # Reconstruct
    reconstructed = ContextMergeBead.from_dict(parsed)

    assert reconstructed.id == sample_bead.id
    assert reconstructed.vulnerability_class == sample_bead.vulnerability_class


def test_bead_status_transitions(sample_bead):
    """Test mark_complete/mark_failed work."""
    # Start as PENDING
    assert sample_bead.status == ContextBeadStatus.PENDING

    # Mark complete
    sample_bead.mark_complete()
    assert sample_bead.status == ContextBeadStatus.COMPLETE

    # Mark failed
    sample_bead.mark_failed("Test error")
    assert sample_bead.status == ContextBeadStatus.FAILED
    assert sample_bead.metadata["failure_reason"] == "Test error"


def test_bead_finding_tracking(sample_bead):
    """Test add_finding_bead tracks correctly."""
    assert len(sample_bead.finding_bead_ids) == 0

    # Add finding beads
    sample_bead.add_finding_bead("finding-001")
    assert len(sample_bead.finding_bead_ids) == 1
    assert "finding-001" in sample_bead.finding_bead_ids

    sample_bead.add_finding_bead("finding-002")
    assert len(sample_bead.finding_bead_ids) == 2

    # Don't add duplicates
    sample_bead.add_finding_bead("finding-001")
    assert len(sample_bead.finding_bead_ids) == 2


def test_bead_get_prompts(sample_bead):
    """Test get_system_prompt/get_user_context work."""
    system_prompt = sample_bead.get_system_prompt()
    assert "Vulnerability Analysis: reentrancy/classic" in system_prompt
    assert "Detection Methodology" in system_prompt
    assert "Check CEI pattern" in system_prompt

    user_context = sample_bead.get_user_context()
    assert "Protocol: TestProtocol" in user_context
    assert "Target Scope" in user_context
    assert "contracts/Vault.sol" in user_context
    assert "Risk Profile" in user_context


# ============================================================================
# ContextBeadFactory Tests
# ============================================================================


def test_create_from_verified_merge_success(tmp_path, sample_context_bundle):
    """Test creates bead from valid inputs."""
    from alphaswarm_sol.agents.context.merger import MergeResult
    from alphaswarm_sol.agents.context.verifier import VerificationResult

    # Create mock merge result
    merge_result = MergeResult(
        success=True,
        bundle=sample_context_bundle,
        errors=[],
        warnings=[],
        token_count=3500,
        trimmed=False,
        sources_used=["vulndoc", "protocol_pack"],
    )

    # Create mock verification result (passing)
    verification_result = VerificationResult(
        valid=True,
        errors=[],
        warnings=[],
        quality_score=0.95,
        feedback_for_retry=None,
    )

    # Create factory and bead
    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")
    bead = factory.create_from_verified_merge(
        merge_result=merge_result,
        verification_result=verification_result,
        pool_id="test-pool",
        created_by="test-agent",
    )

    assert bead.vulnerability_class == "reentrancy/classic"
    assert bead.protocol_name == "TestProtocol"
    assert bead.status == ContextBeadStatus.PENDING
    assert bead.pool_id == "test-pool"
    assert bead.created_by == "test-agent"
    assert bead.verification_score == 0.95


def test_create_from_failed_merge_raises(tmp_path):
    """Test raises ValueError for failed merge."""
    from alphaswarm_sol.agents.context.merger import MergeResult
    from alphaswarm_sol.agents.context.verifier import VerificationResult

    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")

    # Failed merge
    merge_result = MergeResult(
        success=False,
        bundle=None,
        errors=["Merge failed"],
        warnings=[],
        token_count=0,
        trimmed=False,
        sources_used=[],
    )

    verification_result = VerificationResult(
        valid=True,
        errors=[],
        warnings=[],
        quality_score=1.0,
        feedback_for_retry=None,
    )

    with pytest.raises(ValueError, match="Cannot create bead from failed merge"):
        factory.create_from_verified_merge(merge_result, verification_result)


def test_create_from_failed_verification_raises(tmp_path, sample_context_bundle):
    """Test raises ValueError for failed verification."""
    from alphaswarm_sol.agents.context.merger import MergeResult
    from alphaswarm_sol.agents.context.verifier import VerificationError, VerificationResult

    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")

    merge_result = MergeResult(
        success=True,
        bundle=sample_context_bundle,
        errors=[],
        warnings=[],
        token_count=3500,
        trimmed=False,
        sources_used=["vulndoc"],
    )

    # Failed verification
    verification_result = VerificationResult(
        valid=False,
        errors=[
            VerificationError(
                field="reasoning_template",
                error_type="too_short",
                message="Too short",
                severity="error",
            )
        ],
        warnings=[],
        quality_score=0.5,
        feedback_for_retry="Fix errors",
    )

    with pytest.raises(ValueError, match="Cannot create bead from failed verification"):
        factory.create_from_verified_merge(merge_result, verification_result)


def test_save_and_load_bead(tmp_path, sample_bead):
    """Test roundtrip to filesystem."""
    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")

    # Save
    bead_path = factory.save_bead(sample_bead)
    assert bead_path.exists()
    assert bead_path.name == f"{sample_bead.id}.yaml"

    # Load
    loaded_bead = factory.load_bead(sample_bead.id, pool_id="test-pool")
    assert loaded_bead.id == sample_bead.id
    assert loaded_bead.vulnerability_class == sample_bead.vulnerability_class
    assert loaded_bead.protocol_name == sample_bead.protocol_name


def test_save_bead_with_pool(tmp_path, sample_bead):
    """Test organized by pool directory."""
    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")

    bead_path = factory.save_bead(sample_bead)

    # Should be in pool directory
    assert bead_path.parent.name == "test-pool"
    assert bead_path.parent.parent == tmp_path / "beads"


def test_save_bead_unassigned(tmp_path, sample_bead):
    """Test goes to unassigned/ without pool."""
    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")

    # Remove pool ID
    sample_bead.pool_id = None

    bead_path = factory.save_bead(sample_bead)

    # Should be in unassigned directory
    assert bead_path.parent.name == "unassigned"
    assert bead_path.parent.parent == tmp_path / "beads"


def test_list_pending_beads(tmp_path, sample_context_bundle):
    """Test returns only PENDING status."""
    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")

    # Create multiple beads with different statuses
    timestamp = datetime.now()
    beads = []
    for i, status in enumerate(
        [ContextBeadStatus.PENDING, ContextBeadStatus.IN_PROGRESS, ContextBeadStatus.PENDING]
    ):
        bead = ContextMergeBead(
            id=ContextMergeBead.generate_id(
                f"vuln-{i}",
                "Protocol",
                datetime(2026, 1, 22, 12, i, 0),
            ),
            vulnerability_class=f"vuln-{i}",
            protocol_name="Protocol",
            context_bundle=sample_context_bundle,
            target_scope=[],
            verification_score=0.9,
            status=status,
            created_at=timestamp,
            pool_id="pool1",
        )
        factory.save_bead(bead)
        beads.append(bead)

    # List pending
    pending = factory.list_pending_beads(pool_id="pool1")
    assert len(pending) == 2  # Only PENDING beads
    assert all(b.status == ContextBeadStatus.PENDING for b in pending)


def test_list_pending_beads_filtered_by_pool(tmp_path, sample_context_bundle):
    """Test pool filter works."""
    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")

    # Create beads in different pools
    timestamp = datetime.now()
    for pool_id in ["pool1", "pool2"]:
        for i in range(2):
            bead = ContextMergeBead(
                id=ContextMergeBead.generate_id(
                    f"{pool_id}-vuln-{i}",
                    "Protocol",
                    datetime(2026, 1, 22, 12, i, 0),
                ),
                vulnerability_class=f"vuln-{i}",
                protocol_name="Protocol",
                context_bundle=sample_context_bundle,
                target_scope=[],
                verification_score=0.9,
                status=ContextBeadStatus.PENDING,
                created_at=timestamp,
                pool_id=pool_id,
            )
            factory.save_bead(bead)

    # Filter by pool1
    pool1_beads = factory.list_pending_beads(pool_id="pool1")
    assert len(pool1_beads) == 2
    assert all(b.pool_id == "pool1" for b in pool1_beads)

    # Filter by pool2
    pool2_beads = factory.list_pending_beads(pool_id="pool2")
    assert len(pool2_beads) == 2
    assert all(b.pool_id == "pool2" for b in pool2_beads)

    # No filter = all beads
    all_beads = factory.list_pending_beads()
    assert len(all_beads) == 4


def test_load_bead_not_found_raises(tmp_path):
    """Test FileNotFoundError for missing bead."""
    factory = ContextBeadFactory(beads_dir=tmp_path / "beads")

    with pytest.raises(FileNotFoundError, match="Bead not found"):
        factory.load_bead("CTX-nonexistent")
