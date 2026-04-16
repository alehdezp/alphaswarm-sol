"""Unit tests for LangGraph adapter and BeadCheckpointer.

Tests cover:
- State graph creation and node execution
- Handoff with checkpoint creation
- Replay from checkpoint
- Full workflow execution
- Replay chain reconstruction
- Evidence preservation
- Concurrent node execution

Phase: 07.1.4-03 LangGraph Adapter with Persistence
"""

import json
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse
from alphaswarm_sol.beads.schema import (
    VulnerabilityBead,
    PatternContext,
    InvestigationGuide,
    TestContext,
)
from alphaswarm_sol.beads.types import (
    CodeSnippet,
    InvestigationStep,
    BeadStatus,
    Severity,
)

# Check if langgraph is available
try:
    from langgraph.graph import StateGraph, END

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

from alphaswarm_sol.adapters.base import HandoffContext, TraceContext
from alphaswarm_sol.adapters.checkpointer import BeadCheckpointer, CheckpointState

# Only import langgraph components if available
if HAS_LANGGRAPH:
    from alphaswarm_sol.adapters.langgraph import (
        LangGraphAdapter,
        LangGraphConfig,
        VrsState,
        VrsStateGraph,
    )
else:
    # Provide dummy types for type hints when langgraph not available
    LangGraphAdapter = None  # type: ignore
    LangGraphConfig = None  # type: ignore
    VrsState = Dict[str, Any]  # type: ignore
    VrsStateGraph = None  # type: ignore


# Skip all tests if langgraph is not installed
pytestmark = pytest.mark.skipif(not HAS_LANGGRAPH, reason="langgraph not installed")


# Fixtures


@pytest.fixture
def temp_checkpoint_dir():
    """Create temporary directory for checkpoints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_bead() -> VulnerabilityBead:
    """Create sample VulnerabilityBead for testing.

    Uses the correct schema fields:
    - CodeSnippet: source, file_path, start_line, end_line, function_name, contract_name
    - PatternContext: pattern_name, pattern_description, why_flagged, matched_properties, evidence_lines
    - InvestigationGuide: steps, questions_to_answer, common_false_positives, key_indicators, safe_patterns
    """
    pattern_context = PatternContext(
        pattern_name="Classic Reentrancy",
        pattern_description="External call before state update",
        why_flagged="External call on line 46 before balance update",
        matched_properties=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
        evidence_lines=[46, 47],
    )

    vulnerable_code = CodeSnippet(
        source="function withdraw() public { ... }",
        file_path="contracts/Vault.sol",
        start_line=45,
        end_line=50,
        function_name="withdraw",
        contract_name="Vault",
    )

    investigation_guide = InvestigationGuide(
        steps=[
            InvestigationStep(
                step_number=1,
                action="Identify external call location",
                look_for="External call operations, Target address",
                evidence_needed="External call can trigger reentrancy",
            )
        ],
        questions_to_answer=["Is the external call target user-controlled?"],
        common_false_positives=["nonReentrant modifier present"],
        key_indicators=["External call before state update"],
        safe_patterns=["CEI pattern", "nonReentrant modifier"],
    )

    test_context = TestContext(
        scaffold_code="// Test scaffold",
        attack_scenario="1. Deploy attacker contract\n2. Call withdraw",
        setup_requirements=["Attacker contract with fallback"],
        expected_outcome="Attacker extracts more than their balance",
    )

    return VulnerabilityBead(
        id="VKG-TEST-001",
        vulnerability_class="reentrancy",
        pattern_id="reentrancy-classic",
        severity=Severity.CRITICAL,
        confidence=0.95,
        vulnerable_code=vulnerable_code,
        related_code=[],
        full_contract=None,
        inheritance_chain=[],
        pattern_context=pattern_context,
        investigation_guide=investigation_guide,
        test_context=test_context,
        similar_exploits=[],
        fix_recommendations=[],
        status=BeadStatus.PENDING,
    )


@pytest.fixture
def sample_vrs_state(sample_bead: VulnerabilityBead) -> VrsState:
    """Create sample VrsState for testing."""
    return {
        "bead": sample_bead.to_dict(),
        "messages": [],
        "current_agent": "",
        "evidence": {},
        "trace_context": {"trace_id": str(uuid.uuid4()), "operation": "test"},
        "checkpoint_id": "",
        "verdict_reached": False,
        "next_agent": "attacker",
    }


@pytest.fixture
def mock_agent_executor():
    """Mock AgentExecutor for testing."""
    with patch("alphaswarm_sol.adapters.langgraph.AgentExecutor") as mock:
        instance = mock.return_value
        instance.execute = AsyncMock(
            return_value=AgentResponse(
                content="Test response",
                role="assistant",
                model="claude-sonnet-4",
                tokens_used=100,
                cost=0.001,
                metadata={"test": "data"},
            )
        )
        yield mock


# Tests


def test_checkpoint_state_serialization():
    """Test CheckpointState serialization and deserialization."""
    state = CheckpointState(
        checkpoint_id="ckpt-abc123",
        bead_id="VKG-001",
        graph_state={"test": "data"},
        timestamp="2024-01-29T14:00:00Z",
        node_executed="attacker",
        parent_checkpoint_id="ckpt-parent",
        bead_hash="abc123",
    )

    # Test to_dict
    data = state.to_dict()
    assert data["checkpoint_id"] == "ckpt-abc123"
    assert data["bead_id"] == "VKG-001"
    assert data["node_executed"] == "attacker"

    # Test from_dict
    restored = CheckpointState.from_dict(data)
    assert restored.checkpoint_id == state.checkpoint_id
    assert restored.bead_id == state.bead_id
    assert restored.parent_checkpoint_id == state.parent_checkpoint_id

    # Test JSONL format
    jsonl = state.to_jsonl()
    assert isinstance(jsonl, str)
    assert "\n" not in jsonl  # Single line
    parsed = json.loads(jsonl)
    assert parsed["checkpoint_id"] == "ckpt-abc123"


def test_bead_checkpointer_save_load(temp_checkpoint_dir: Path, sample_vrs_state: VrsState):
    """Test saving and loading checkpoints."""
    checkpointer = BeadCheckpointer(temp_checkpoint_dir)

    # Save checkpoint
    checkpoint_id = checkpointer.save(sample_vrs_state, "attacker")
    assert checkpoint_id.startswith("ckpt-")

    # Load checkpoint
    loaded = checkpointer.load(checkpoint_id)
    assert loaded.checkpoint_id == checkpoint_id
    assert loaded.bead_id == sample_vrs_state["bead"]["id"]
    assert loaded.node_executed == "attacker"
    assert loaded.graph_state == sample_vrs_state


def test_bead_checkpointer_list_checkpoints(temp_checkpoint_dir: Path, sample_vrs_state: VrsState):
    """Test listing checkpoints for a bead."""
    checkpointer = BeadCheckpointer(temp_checkpoint_dir)

    # Save multiple checkpoints
    checkpoint_ids = []
    for node in ["attacker", "defender", "verifier"]:
        checkpoint_id = checkpointer.save(sample_vrs_state, node)
        checkpoint_ids.append(checkpoint_id)

    # List checkpoints
    checkpoints = checkpointer.list_checkpoints(sample_vrs_state["bead"]["id"])
    assert len(checkpoints) == 3
    assert checkpoints[0].node_executed == "verifier"  # Newest first
    assert checkpoints[2].node_executed == "attacker"  # Oldest last


def test_bead_checkpointer_replay_chain(temp_checkpoint_dir: Path, sample_vrs_state: VrsState):
    """Test building replay chain from checkpoints."""
    checkpointer = BeadCheckpointer(temp_checkpoint_dir)

    # Save checkpoints with parent chain
    checkpoint1 = checkpointer.save(sample_vrs_state, "attacker")
    checkpoint2 = checkpointer.save(sample_vrs_state, "defender")
    checkpoint3 = checkpointer.save(sample_vrs_state, "verifier")

    # Get replay chain
    chain = checkpointer.get_replay_chain(checkpoint3)
    assert len(chain) == 3
    assert chain[0].node_executed == "attacker"
    assert chain[1].node_executed == "defender"
    assert chain[2].node_executed == "verifier"

    # Verify parent links
    assert chain[0].parent_checkpoint_id is None
    assert chain[1].parent_checkpoint_id == checkpoint1
    assert chain[2].parent_checkpoint_id == checkpoint2


def test_bead_checkpointer_cleanup_old_checkpoints(temp_checkpoint_dir: Path, sample_vrs_state: VrsState):
    """Test cleanup of old checkpoints."""
    checkpointer = BeadCheckpointer(temp_checkpoint_dir)

    # Save checkpoints
    for i in range(5):
        checkpointer.save(sample_vrs_state, f"node-{i}")

    # Cleanup old checkpoints (max_age=0 removes all)
    removed = checkpointer.cleanup_old_checkpoints(max_age_hours=0)
    assert removed == 5

    # Verify checkpoints removed
    checkpoints = checkpointer.list_checkpoints(sample_vrs_state["bead"]["id"])
    assert len(checkpoints) == 0


def test_bead_checkpointer_validation(temp_checkpoint_dir: Path, sample_vrs_state: VrsState):
    """Test checkpoint validation."""
    checkpointer = BeadCheckpointer(temp_checkpoint_dir)

    # Valid checkpoint
    valid_state = CheckpointState(
        checkpoint_id="ckpt-valid",
        bead_id="VKG-001",
        graph_state=sample_vrs_state,
        timestamp="2024-01-29T14:00:00Z",
        node_executed="attacker",
    )
    assert checkpointer.validate_checkpoint(valid_state) is True

    # Invalid checkpoint - missing required fields
    invalid_state = CheckpointState(
        checkpoint_id="",
        bead_id="",
        graph_state={},
        timestamp="2024-01-29T14:00:00Z",
        node_executed="attacker",
    )
    assert checkpointer.validate_checkpoint(invalid_state) is False


def test_langgraph_config_initialization():
    """Test LangGraphConfig initialization with defaults."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
    )

    assert config.persistence_path == ".langgraph_checkpoints"
    assert config.enable_replay is True
    assert config.max_concurrent_nodes == 4
    assert config.state_schema is None


def test_state_graph_creation(mock_agent_executor, temp_checkpoint_dir: Path):
    """Test VrsStateGraph creates valid graph."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
        enable_replay=False,  # Disable for simpler test
    )
    adapter = LangGraphAdapter(config)

    # Verify state graph created
    assert adapter.state_graph is not None
    assert adapter.state_graph.graph is not None

    # Verify nodes added
    graph = adapter.state_graph.graph
    # Note: LangGraph doesn't expose nodes directly, so we verify compilation works
    compiled = adapter.state_graph.compile()
    assert compiled is not None


@pytest.mark.asyncio
async def test_node_execution_updates_state(mock_agent_executor, temp_checkpoint_dir: Path, sample_vrs_state: VrsState):
    """Test that state is updated after node execution."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
        enable_replay=False,
    )
    adapter = LangGraphAdapter(config)

    # Create agent node
    node_func = adapter.state_graph._create_agent_node("vrs-attacker")

    # Execute node
    updated_state = await node_func(sample_vrs_state)

    # Verify state updated
    assert updated_state["current_agent"] == "vrs-attacker"
    assert len(updated_state["messages"]) > len(sample_vrs_state["messages"])
    assert "vrs-attacker_evidence" in updated_state["evidence"]
    assert updated_state["trace_context"]["last_agent"] == "vrs-attacker"


@pytest.mark.asyncio
async def test_handoff_checkpoints_state(mock_agent_executor, temp_checkpoint_dir: Path, sample_bead: VulnerabilityBead):
    """Test that handoff creates checkpoint."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
        enable_replay=True,
    )
    adapter = LangGraphAdapter(config)

    # Create handoff context
    ctx = HandoffContext(
        source_agent="vrs-attacker",
        target_agent="vrs-defender",
        bead_id=sample_bead.id,
        evidence_snapshot={"test": "evidence"},
        trace_id=str(uuid.uuid4()),
    )

    # Perform handoff
    result = await adapter.handoff(ctx)

    # Verify checkpoint created
    assert result.success is True
    assert "checkpoint_id" in result.metadata
    checkpoint_id = result.metadata["checkpoint_id"]
    assert checkpoint_id is not None


@pytest.mark.asyncio
async def test_replay_from_checkpoint(mock_agent_executor, temp_checkpoint_dir: Path, sample_vrs_state: VrsState):
    """Test replaying from checkpoint."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
        enable_replay=True,
    )
    adapter = LangGraphAdapter(config)

    # Save checkpoint
    checkpoint_id = adapter.checkpointer.save(sample_vrs_state, "attacker")

    # Replay from checkpoint
    replayed_state = await adapter.replay_from_checkpoint(checkpoint_id)

    # Verify state restored
    assert replayed_state is not None
    # Note: Full state verification depends on graph execution


@pytest.mark.asyncio
async def test_full_workflow_execution(mock_agent_executor, temp_checkpoint_dir: Path, sample_bead: VulnerabilityBead):
    """Test full attacker->defender->verifier workflow."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
        enable_replay=False,
    )
    adapter = LangGraphAdapter(config)

    # Execute workflow
    result_bead = await adapter.execute_workflow(sample_bead, {})

    # Verify workflow completed
    assert result_bead.status == BeadStatus.VERIFIED
    assert result_bead.work_state is not None
    assert "final_state" in result_bead.work_state
    assert "messages" in result_bead.work_state
    assert "evidence" in result_bead.work_state


def test_evidence_preservation_across_nodes(temp_checkpoint_dir: Path, sample_bead: VulnerabilityBead):
    """Test that evidence is preserved across graph nodes."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
    )
    adapter = LangGraphAdapter(config)

    # Create handoff context
    ctx = HandoffContext(
        source_agent="vrs-attacker",
        target_agent="vrs-defender",
        bead_id=sample_bead.id,
        evidence_snapshot={"vulnerable_function": "withdraw"},
    )

    # Preserve evidence
    preserved_bead = adapter.preserve_evidence(sample_bead, ctx)

    # Verify evidence snapshot in work_state
    assert preserved_bead.work_state is not None
    assert "handoff_snapshot" in preserved_bead.work_state
    assert preserved_bead.work_state["handoff_snapshot"]["source_agent"] == "vrs-attacker"
    assert preserved_bead.work_state["handoff_snapshot"]["evidence"] == {"vulnerable_function": "withdraw"}


def test_adapter_capabilities(temp_checkpoint_dir: Path):
    """Test adapter reports correct capabilities."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
    )
    adapter = LangGraphAdapter(config)

    capabilities = adapter.get_capabilities()

    # Verify expected capabilities
    from alphaswarm_sol.adapters.capability import AdapterCapability

    assert AdapterCapability.TOOL_EXECUTION in capabilities
    assert AdapterCapability.MEMORY_PERSISTENT in capabilities
    assert AdapterCapability.TRACE_PROPAGATION in capabilities
    assert AdapterCapability.HANDOFF_ASYNC in capabilities
    assert AdapterCapability.BEAD_REPLAY in capabilities


def test_trace_export_import(temp_checkpoint_dir: Path):
    """Test trace context export and import."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
    )
    adapter = LangGraphAdapter(config)

    # Create trace context
    trace = TraceContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        operation="vrs.investigate",
        attributes={"bead_id": "VKG-001"},
    )

    # Export to OpenTelemetry format
    exported = adapter.export_trace(trace)
    assert "traceparent" in exported
    assert trace.trace_id in exported["traceparent"]
    assert trace.span_id in exported["traceparent"]

    # Import back
    imported = adapter.import_trace(exported)
    assert imported.trace_id == trace.trace_id
    assert imported.span_id == trace.span_id


@pytest.mark.asyncio
async def test_concurrent_node_execution(mock_agent_executor, temp_checkpoint_dir: Path, sample_vrs_state: VrsState):
    """Test concurrent node execution respects max_concurrent_nodes."""
    config = LangGraphConfig(
        name="langgraph",
        capabilities=set(),
        persistence_path=str(temp_checkpoint_dir),
        max_concurrent_nodes=2,
    )
    adapter = LangGraphAdapter(config)

    # Verify config applied
    assert adapter.config.max_concurrent_nodes == 2

    # Note: Testing actual concurrent execution requires more complex graph setup
    # This test verifies the configuration is properly stored
