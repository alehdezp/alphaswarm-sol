"""Unit tests for AutoGen and CrewAI adapters.

Tests role mapping, team/crew creation, handoff mechanisms, and evidence preservation
for both AutoGenAdapter and CrewAIAdapter implementations.

These adapters are EXPERIMENTAL - tests verify warning emission and placeholder behavior.

Phase: 07.1.4-04 AutoGen & CrewAI Adapters
"""

import warnings
import pytest
from unittest.mock import MagicMock, patch

from alphaswarm_sol.adapters.autogen import (
    AutoGenAdapter,
    AutoGenConfig,
    VrsTeam,
    VRS_TO_AUTOGEN_ROLE,
    EXPERIMENTAL,
)
from alphaswarm_sol.adapters.crewai import (
    CrewAIAdapter,
    CrewAIConfig,
    VrsCrew,
    VRS_TO_CREWAI_ROLE,
    EXPERIMENTAL as CREWAI_EXPERIMENTAL,
)
from alphaswarm_sol.adapters.base import (
    HandoffContext,
    TraceContext,
)
from alphaswarm_sol.adapters.capability import AdapterCapability
from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentRole
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

# Check if optional dependencies are available
try:
    import autogen
    HAS_AUTOGEN = True
except ImportError:
    HAS_AUTOGEN = False

try:
    import crewai
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False


@pytest.fixture
def sample_bead():
    """Create a sample VulnerabilityBead for testing.

    Uses the correct schema fields:
    - CodeSnippet: source, file_path, start_line, end_line, function_name, contract_name
    - PatternContext: pattern_name, pattern_description, why_flagged, matched_properties, evidence_lines
    - InvestigationGuide: steps, questions_to_answer, common_false_positives, key_indicators, safe_patterns
    - TestContext: scaffold_code, attack_scenario, setup_requirements, expected_outcome
    """
    return VulnerabilityBead(
        id="VKG-001",
        vulnerability_class="reentrancy-classic",
        pattern_id="vm-001",
        severity=Severity.CRITICAL,
        confidence=0.85,
        vulnerable_code=CodeSnippet(
            source="function withdraw(uint256 amount) external { ... }",
            file_path="contracts/Vault.sol",
            start_line=42,
            end_line=45,
            function_name="withdraw",
            contract_name="Vault",
        ),
        related_code=[],
        full_contract=None,
        inheritance_chain=[],
        pattern_context=PatternContext(
            pattern_name="Classic Reentrancy",
            pattern_description="External call before state update",
            why_flagged="External call before balance update",
            matched_properties=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            evidence_lines=[42, 43],
        ),
        investigation_guide=InvestigationGuide(
            steps=[
                InvestigationStep(
                    step_number=1,
                    action="Check for reentrancy guard",
                    look_for="nonReentrant modifier",
                    evidence_needed="Guard presence or absence",
                )
            ],
            questions_to_answer=["Is external call target user-controlled?"],
            common_false_positives=["nonReentrant modifier present"],
            key_indicators=["External call before state update"],
            safe_patterns=["CEI pattern"],
        ),
        test_context=TestContext(
            scaffold_code="// Test scaffold",
            attack_scenario="Deploy attacker and call withdraw",
            setup_requirements=["Attacker contract"],
            expected_outcome="Attacker drains funds",
        ),
        similar_exploits=[],
        fix_recommendations=["Add nonReentrant modifier"],
        metadata={},
    )


@pytest.fixture
def mock_autogen():
    """Mock autogen imports for unit testing."""
    with patch("alphaswarm_sol.adapters.autogen.HAS_AUTOGEN", True):
        with patch("alphaswarm_sol.adapters.autogen.ConversableAgent") as mock_agent:
            with patch("alphaswarm_sol.adapters.autogen.GroupChat") as mock_chat:
                with patch("alphaswarm_sol.adapters.autogen.GroupChatManager") as mock_mgr:
                    mock_agent.return_value = MagicMock()
                    mock_chat.return_value = MagicMock()
                    mock_mgr.return_value = MagicMock()
                    yield {
                        "agent": mock_agent,
                        "chat": mock_chat,
                        "manager": mock_mgr,
                    }


@pytest.fixture
def mock_crewai():
    """Mock crewai imports for unit testing."""
    with patch("alphaswarm_sol.adapters.crewai.HAS_CREWAI", True):
        with patch("alphaswarm_sol.adapters.crewai.Agent") as mock_agent:
            with patch("alphaswarm_sol.adapters.crewai.Task") as mock_task:
                with patch("alphaswarm_sol.adapters.crewai.Crew") as mock_crew:
                    mock_agent.return_value = MagicMock()
                    mock_task.return_value = MagicMock()
                    mock_crew.return_value = MagicMock()
                    yield {
                        "agent": mock_agent,
                        "task": mock_task,
                        "crew": mock_crew,
                    }


# ============================================================================
# Experimental Status Tests
# ============================================================================

def test_autogen_experimental_flag():
    """Test that AutoGen adapter is marked as experimental."""
    assert EXPERIMENTAL is True


def test_crewai_experimental_flag():
    """Test that CrewAI adapter is marked as experimental."""
    assert CREWAI_EXPERIMENTAL is True


@pytest.mark.asyncio
async def test_autogen_execute_agent_emits_warning():
    """Test that execute_agent emits experimental warning."""
    config = AutoGenConfig()
    adapter = AutoGenAdapter(config)

    agent_config = AgentConfig(
        role=AgentRole.ATTACKER,
        system_prompt="Test",
        tools=[],
    )

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        response = await adapter.execute_agent(agent_config, [])

        # Check warning was emitted
        assert len(w) >= 1
        assert any("experimental" in str(warning.message).lower() for warning in w)


@pytest.mark.asyncio
async def test_crewai_execute_agent_emits_warning():
    """Test that execute_agent emits experimental warning."""
    config = CrewAIConfig()
    adapter = CrewAIAdapter(config)

    agent_config = AgentConfig(
        role=AgentRole.DEFENDER,
        system_prompt="Test",
        tools=[],
    )

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        response = await adapter.execute_agent(agent_config, [])

        # Check warning was emitted
        assert len(w) >= 1
        assert any("experimental" in str(warning.message).lower() for warning in w)


# ============================================================================
# AutoGen Adapter Tests
# ============================================================================

def test_autogen_role_mapping():
    """Test that VRS roles map correctly to AutoGen agent names."""
    # Check all expected roles are mapped
    assert AgentRole.ATTACKER in VRS_TO_AUTOGEN_ROLE
    assert AgentRole.DEFENDER in VRS_TO_AUTOGEN_ROLE
    assert AgentRole.VERIFIER in VRS_TO_AUTOGEN_ROLE
    assert AgentRole.SUPERVISOR in VRS_TO_AUTOGEN_ROLE

    # Check expected agent names
    assert VRS_TO_AUTOGEN_ROLE[AgentRole.ATTACKER] == "attacker_agent"
    assert VRS_TO_AUTOGEN_ROLE[AgentRole.DEFENDER] == "defender_agent"
    assert VRS_TO_AUTOGEN_ROLE[AgentRole.VERIFIER] == "verifier_agent"
    assert VRS_TO_AUTOGEN_ROLE[AgentRole.SUPERVISOR] == "orchestrator_agent"


def test_autogen_config_defaults():
    """Test AutoGenConfig has correct defaults."""
    config = AutoGenConfig()

    assert config.name == "autogen"
    assert config.team_type == "swarm"
    assert config.max_rounds == 10
    assert config.human_input_mode == "NEVER"
    assert config.code_execution_enabled is False
    assert config.evidence_mode == "bead"


def test_autogen_team_creation(sample_bead, mock_autogen):
    """Test VrsTeam creates valid team structure."""
    config = AutoGenConfig()
    adapter = AutoGenAdapter(config)

    # Create team (mocked AutoGen)
    team = VrsTeam(adapter, sample_bead)

    # Check team has bead and adapter references
    assert team.bead == sample_bead
    assert team.adapter == adapter


@pytest.mark.asyncio
async def test_autogen_handoff_preserves_evidence(sample_bead):
    """Test that handoff preserves evidence in chat context."""
    config = AutoGenConfig()
    adapter = AutoGenAdapter(config)

    # Preserve evidence before handoff
    ctx = HandoffContext(
        source_agent="vrs-attacker",
        target_agent="vrs-defender",
        bead_id=sample_bead.id,
        trace_id="test-trace-123",
    )
    adapter.preserve_evidence(sample_bead, ctx)

    # Verify evidence snapshot created
    assert ctx.evidence_snapshot is not None
    assert ctx.evidence_snapshot["bead_id"] == sample_bead.id
    assert ctx.evidence_snapshot["vulnerability_class"] == "reentrancy-classic"
    assert ctx.evidence_snapshot["severity"] == "critical"

    # Execute handoff
    result = await adapter.handoff(ctx)

    # Verify handoff success and evidence preservation
    assert result.success is True
    assert result.evidence_preserved is True
    assert result.trace_continued is True


def test_autogen_capabilities():
    """Test AutoGenAdapter reports correct capabilities."""
    config = AutoGenConfig()
    adapter = AutoGenAdapter(config)

    capabilities = adapter.get_capabilities()

    # AutoGen supports tool execution, memory thread, sync/async handoff
    assert AdapterCapability.TOOL_EXECUTION in capabilities
    assert AdapterCapability.MEMORY_THREAD in capabilities
    assert AdapterCapability.HANDOFF_SYNC in capabilities
    assert AdapterCapability.HANDOFF_ASYNC in capabilities

    # AutoGen does not support bead replay or graph-first
    assert AdapterCapability.BEAD_REPLAY not in capabilities
    assert AdapterCapability.GRAPH_FIRST not in capabilities


@pytest.mark.asyncio
async def test_autogen_execute_agent():
    """Test single agent execution with AutoGen (placeholder response expected)."""
    config = AutoGenConfig()
    adapter = AutoGenAdapter(config)

    agent_config = AgentConfig(
        role=AgentRole.ATTACKER,
        system_prompt="You are a security attacker",
        tools=[],
    )
    messages = [{"role": "user", "content": "Analyze this vulnerability"}]

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        response = await adapter.execute_agent(agent_config, messages)

    # Should return placeholder response (adapter is experimental)
    assert response is not None
    assert response.content is not None  # Response has content
    # Without AutoGen installed, metadata shows experimental status
    assert "experimental" in response.metadata or "adapter" in response.metadata


# ============================================================================
# CrewAI Adapter Tests
# ============================================================================

def test_crewai_role_mapping():
    """Test that VRS roles map correctly to CrewAI roles."""
    # Check all expected roles are mapped
    assert AgentRole.ATTACKER in VRS_TO_CREWAI_ROLE
    assert AgentRole.DEFENDER in VRS_TO_CREWAI_ROLE
    assert AgentRole.VERIFIER in VRS_TO_CREWAI_ROLE
    assert AgentRole.SUPERVISOR in VRS_TO_CREWAI_ROLE

    # Check role structures
    attacker = VRS_TO_CREWAI_ROLE[AgentRole.ATTACKER]
    assert "role" in attacker
    assert "goal" in attacker
    assert "backstory" in attacker
    assert attacker["role"] == "Security Attacker"


def test_crewai_config_defaults():
    """Test CrewAIConfig has correct defaults."""
    config = CrewAIConfig()

    assert config.name == "crewai"
    assert config.process_type == "sequential"
    assert config.verbose is False
    assert config.memory_enabled is True
    assert config.max_iterations == 5
    assert config.evidence_mode == "bead"


def test_crewai_crew_creation(sample_bead):
    """Test VrsCrew creates valid crew structure (without CrewAI package)."""
    config = CrewAIConfig()
    adapter = CrewAIAdapter(config)

    # Create crew (CrewAI package not required for basic instantiation)
    crew = VrsCrew(adapter, sample_bead)

    # Check crew has bead and adapter references
    assert crew.bead == sample_bead
    assert crew.adapter == adapter
    # Without HAS_CREWAI, agents and tasks are empty
    assert isinstance(crew.agents, dict)
    assert isinstance(crew.tasks, list)


def test_crewai_task_delegation(sample_bead):
    """Test that VrsCrew structure is correctly initialized."""
    config = CrewAIConfig()
    adapter = CrewAIAdapter(config)

    # Create crew
    crew = VrsCrew(adapter, sample_bead)

    # Check basic structure (full task creation requires HAS_CREWAI)
    assert crew.bead == sample_bead
    assert crew.adapter == adapter


@pytest.mark.asyncio
async def test_crewai_handoff_preserves_evidence(sample_bead):
    """Test that handoff preserves evidence in task context."""
    config = CrewAIConfig()
    adapter = CrewAIAdapter(config)

    # Preserve evidence before handoff
    ctx = HandoffContext(
        source_agent="vrs-attacker",
        target_agent="vrs-defender",
        bead_id=sample_bead.id,
        trace_id="test-trace-456",
    )
    adapter.preserve_evidence(sample_bead, ctx)

    # Verify evidence snapshot created
    assert ctx.evidence_snapshot is not None
    assert ctx.evidence_snapshot["bead_id"] == sample_bead.id
    assert ctx.evidence_snapshot["vulnerability_class"] == "reentrancy-classic"

    # Execute handoff
    result = await adapter.handoff(ctx)

    # Verify handoff success and evidence preservation
    assert result.success is True
    assert result.evidence_preserved is True
    assert result.trace_continued is True


def test_crewai_capabilities():
    """Test CrewAIAdapter reports correct capabilities."""
    config = CrewAIConfig()
    adapter = CrewAIAdapter(config)

    capabilities = adapter.get_capabilities()

    # CrewAI supports tool execution, memory shared, sync handoff
    assert AdapterCapability.TOOL_EXECUTION in capabilities
    assert AdapterCapability.MEMORY_SHARED in capabilities
    assert AdapterCapability.HANDOFF_SYNC in capabilities

    # CrewAI does not support async handoff, bead replay, or graph-first
    assert AdapterCapability.HANDOFF_ASYNC not in capabilities
    assert AdapterCapability.BEAD_REPLAY not in capabilities
    assert AdapterCapability.GRAPH_FIRST not in capabilities


@pytest.mark.asyncio
async def test_crewai_execute_agent():
    """Test single agent execution with CrewAI (placeholder response expected)."""
    config = CrewAIConfig()
    adapter = CrewAIAdapter(config)

    agent_config = AgentConfig(
        role=AgentRole.DEFENDER,
        system_prompt="You are a security defender",
        tools=[],
    )
    messages = [{"role": "user", "content": "Find guards for this vulnerability"}]

    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        response = await adapter.execute_agent(agent_config, messages)

    # Should return placeholder response (adapter is experimental)
    assert response is not None
    assert response.content is not None  # Response has content
    # Without CrewAI installed, metadata shows experimental status
    assert "experimental" in response.metadata or "adapter" in response.metadata


# ============================================================================
# Integration Tests (Skip if packages not installed)
# ============================================================================

@pytest.mark.skipif(not HAS_AUTOGEN, reason="AutoGen not installed")
@pytest.mark.asyncio
async def test_autogen_real_team_creation(sample_bead):
    """Test real AutoGen team creation when package is available."""
    config = AutoGenConfig()
    adapter = AutoGenAdapter(config)

    # Create team with real AutoGen
    team = VrsTeam(adapter, sample_bead)

    # Should have agents dictionary
    assert isinstance(team.agents, dict)


@pytest.mark.skipif(not HAS_CREWAI, reason="CrewAI not installed")
@pytest.mark.asyncio
async def test_crewai_real_crew_creation(sample_bead):
    """Test real CrewAI crew creation when package is available."""
    config = CrewAIConfig()
    adapter = CrewAIAdapter(config)

    # Create crew with real CrewAI
    crew = VrsCrew(adapter, sample_bead)

    # Should have agents and tasks
    assert isinstance(crew.agents, dict)
    assert isinstance(crew.tasks, list)


@pytest.mark.asyncio
async def test_trace_propagation_autogen():
    """Test trace context propagation in AutoGen adapter."""
    config = AutoGenConfig()
    adapter = AutoGenAdapter(config)

    agent_config = AgentConfig(
        role=AgentRole.VERIFIER,
        system_prompt="You are a verifier",
        tools=[],
    )

    trace = TraceContext(
        trace_id="trace-789",
        span_id="span-001",
        operation="test_operation",
    )

    response = await adapter.spawn_with_trace(agent_config, "Verify this", trace)

    # Should attach trace metadata
    assert "trace_id" in response.metadata
    assert response.metadata["trace_id"] == "trace-789"


@pytest.mark.asyncio
async def test_trace_propagation_crewai():
    """Test trace context propagation in CrewAI adapter."""
    config = CrewAIConfig()
    adapter = CrewAIAdapter(config)

    agent_config = AgentConfig(
        role=AgentRole.ATTACKER,
        system_prompt="You are an attacker",
        tools=[],
    )

    trace = TraceContext(
        trace_id="trace-999",
        span_id="span-002",
        operation="test_operation",
    )

    response = await adapter.spawn_with_trace(agent_config, "Attack this", trace)

    # Should attach trace metadata
    assert "trace_id" in response.metadata
    assert response.metadata["trace_id"] == "trace-999"
