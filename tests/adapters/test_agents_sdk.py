"""Unit tests for AgentsSdkAdapter.

Tests handoff semantics, guardrail enforcement, and trace propagation
for the OpenAI Agents SDK adapter.

Phase: 07.1.4-02 Agents SDK + Codex MCP Integration
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from alphaswarm_sol.adapters.agents_sdk import AgentsSdkAdapter, AgentsSdkConfig
from alphaswarm_sol.adapters.base import HandoffContext, TraceContext
from alphaswarm_sol.adapters.capability import AdapterCapability
from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse, AgentRole
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
    BeadStatus,
)


# ===============================================================================
# FIXTURES
# ===============================================================================


@pytest.fixture
def sample_guardrail_policy(tmp_path: Path) -> Path:
    """Create a sample guardrail policy YAML file."""
    policy_path = tmp_path / "skill_tool_policies.yaml"
    policy = {
        "version": "1.0",
        "roles": {
            "attacker": {
                "description": "Constructs exploit paths",
                "model_tier": "opus",
                "allowed_tools": [
                    "Read",
                    "Glob",
                    "Grep",
                    "Bash(uv run alphaswarm query*)",
                ],
                "constraints": {
                    "max_file_reads": 50,
                    "require_graph_first": True,
                    "evidence_required": True,
                    "token_budget": 8000,
                },
            },
            "defender": {
                "description": "Finds guards",
                "model_tier": "sonnet",
                "allowed_tools": ["Read", "Grep"],
                "constraints": {
                    "max_file_reads": 40,
                    "require_graph_first": True,
                    "evidence_required": True,
                    "token_budget": 6000,
                },
            },
        },
    }

    with open(policy_path, "w") as f:
        yaml.dump(policy, f)

    return policy_path


@pytest.fixture
def sample_bead() -> VulnerabilityBead:
    """Create a sample VulnerabilityBead for testing.

    Uses the correct schema fields:
    - CodeSnippet: source, file_path, start_line, end_line, function_name, contract_name
    - PatternContext: pattern_name, pattern_description, why_flagged, matched_properties, evidence_lines
    - InvestigationGuide: steps, questions_to_answer, common_false_positives, key_indicators, safe_patterns
    - TestContext: scaffold_code, attack_scenario, setup_requirements, expected_outcome
    """
    return VulnerabilityBead(
        id="VKG-001",
        vulnerability_class="reentrancy",
        pattern_id="vm-001",
        severity=Severity.CRITICAL,
        confidence=0.95,
        status=BeadStatus.PENDING,
        vulnerable_code=CodeSnippet(
            source="function withdraw() public { ... }",
            file_path="VulnerableBank.sol",
            start_line=10,
            end_line=20,
            function_name="withdraw",
            contract_name="VulnerableBank",
        ),
        related_code=[],
        full_contract=None,
        inheritance_chain=[],
        pattern_context=PatternContext(
            pattern_name="Classic Reentrancy",
            pattern_description="External call before state update",
            why_flagged="External call on line 15 before balance update on line 18",
            matched_properties=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            evidence_lines=[15, 18],
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
        fix_recommendations=["Use nonReentrant modifier"],
    )


@pytest.fixture
def mock_openai_runtime():
    """Mock OpenAIAgentsRuntime for unit testing."""
    mock = Mock()
    mock.execute = Mock(
        return_value=AgentResponse(
            content="Mock response",
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
            model="gpt-4-turbo",
        )
    )
    return mock


# ===============================================================================
# TESTS
# ===============================================================================


def test_adapter_capabilities(sample_guardrail_policy: Path):
    """Test that adapter reports correct capabilities."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrail_policy_path=str(sample_guardrail_policy),
    )
    adapter = AgentsSdkAdapter(config)

    capabilities = adapter.get_capabilities()

    # Check expected capabilities from ADAPTER_CAPABILITIES
    expected = {
        AdapterCapability.TOOL_EXECUTION,
        AdapterCapability.TOOL_CONVERSION,
        AdapterCapability.TRACE_PROPAGATION,
        AdapterCapability.HANDOFF_SYNC,
        AdapterCapability.GUARDRAILS,
        AdapterCapability.COST_TRACKING,
    }

    assert capabilities == expected


def test_guardrail_tool_filtering(sample_guardrail_policy: Path):
    """Test that tools are filtered by role policy."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrail_policy_path=str(sample_guardrail_policy),
    )
    adapter = AgentsSdkAdapter(config)

    # Tools provided to attacker
    tools = [
        {"name": "Read", "description": "Read files"},
        {"name": "Write", "description": "Write files"},
        {"name": "Grep", "description": "Search files"},
        {"name": "Bash", "description": "Run commands"},
    ]

    # Filter for attacker role
    filtered = adapter._apply_input_guardrails("attacker", tools)

    # Attacker should have Read, Grep, Bash but NOT Write
    filtered_names = {t["name"] for t in filtered}
    assert "Read" in filtered_names
    assert "Grep" in filtered_names
    assert "Bash" in filtered_names
    assert "Write" not in filtered_names


def test_handoff_preserves_evidence(
    sample_guardrail_policy: Path, sample_bead: VulnerabilityBead
):
    """Test that bead evidence is unchanged after handoff."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrail_policy_path=str(sample_guardrail_policy),
    )
    adapter = AgentsSdkAdapter(config)

    # Create handoff context
    ctx = HandoffContext(
        source_agent="vrs-attacker",
        target_agent="vrs-defender",
        bead_id=sample_bead.id,
    )

    # Preserve evidence
    original_id = sample_bead.id
    original_class = sample_bead.vulnerability_class
    original_severity = sample_bead.severity
    original_confidence = sample_bead.confidence

    preserved_bead = adapter.preserve_evidence(sample_bead, ctx)

    # Evidence should be unchanged
    assert preserved_bead.id == original_id
    assert preserved_bead.vulnerability_class == original_class
    assert preserved_bead.severity == original_severity
    assert preserved_bead.confidence == original_confidence

    # Evidence snapshot should be in context
    assert "bead_id" in ctx.evidence_snapshot
    assert ctx.evidence_snapshot["bead_id"] == sample_bead.id
    assert ctx.evidence_snapshot["vulnerability_class"] == sample_bead.vulnerability_class


@pytest.mark.asyncio
async def test_handoff_trace_continuity(sample_guardrail_policy: Path):
    """Test that trace_id is preserved and span_id is updated during handoff."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrail_policy_path=str(sample_guardrail_policy),
    )
    adapter = AgentsSdkAdapter(config)

    # Mock the runtime to avoid real API calls
    with patch.object(adapter, "_runtime") as mock_runtime:
        mock_runtime.execute = AsyncMock(
            return_value=AgentResponse(
                content="Mock response",
                tool_calls=[],
                input_tokens=100,
                output_tokens=50,
                model="gpt-4-turbo",
                metadata={},
            )
        )

        # Create handoff context with trace
        original_trace_id = "test-trace-123"
        original_span_id = "span-001"

        ctx = HandoffContext(
            source_agent="vrs-attacker",
            target_agent="vrs-defender",
            bead_id="VKG-001",
            trace_id=original_trace_id,
            parent_span_id=original_span_id,
        )

        # Execute handoff
        result = await adapter.handoff(ctx)

        # Check success
        assert result.success
        assert result.trace_continued

        # Check trace_id preserved
        assert result.metadata["trace_id"] == original_trace_id

        # Check span_id updated (new span created)
        new_span_id = result.metadata["span_id"]
        assert new_span_id != original_span_id


@pytest.mark.asyncio
async def test_spawn_with_trace(sample_guardrail_policy: Path):
    """Test that trace context is propagated to spawned agent."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrail_policy_path=str(sample_guardrail_policy),
    )
    adapter = AgentsSdkAdapter(config)

    # Mock the runtime and output guardrails to avoid real API calls
    with patch.object(adapter, "_runtime") as mock_runtime, \
         patch.object(adapter, "_validate_output_guardrails", return_value=True):
        mock_runtime.execute = AsyncMock(
            return_value=AgentResponse(
                content="Mock response",
                tool_calls=[],
                input_tokens=100,
                output_tokens=50,
                model="gpt-4-turbo",
                metadata={},
            )
        )

        # Create trace context
        trace = TraceContext(
            trace_id="test-trace-456",
            span_id="span-parent",
            operation="test.spawn",
        )

        # Spawn agent with trace
        agent_config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="Test prompt",
            tools=[],
        )

        response = await adapter.spawn_with_trace(agent_config, "Test task", trace)

        # Check trace metadata in response
        assert "trace_id" in response.metadata
        assert response.metadata["trace_id"] == trace.trace_id

        # Check new span created
        assert "span_id" in response.metadata
        assert response.metadata["span_id"] != trace.span_id

        # Check parent span preserved
        assert "parent_span_id" in response.metadata
        assert response.metadata["parent_span_id"] == trace.span_id


def test_export_import_trace(sample_guardrail_policy: Path):
    """Test that trace roundtrip serialization works."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrail_policy_path=str(sample_guardrail_policy),
    )
    adapter = AgentsSdkAdapter(config)

    # Create trace
    original_trace = TraceContext(
        trace_id="trace-789",
        span_id="span-001",
        parent_span_id="span-000",
        operation="test.operation",
        attributes={"key": "value"},
    )

    # Export
    exported = adapter.export_trace(original_trace)

    # Check OpenTelemetry format
    assert "traceId" in exported
    assert "spanId" in exported
    assert "parentSpanId" in exported
    assert exported["traceId"] == original_trace.trace_id
    assert exported["spanId"] == original_trace.span_id

    # Import back
    imported_trace = adapter.import_trace(exported)

    # Check roundtrip
    assert imported_trace.trace_id == original_trace.trace_id
    assert imported_trace.span_id == original_trace.span_id
    assert imported_trace.parent_span_id == original_trace.parent_span_id
    assert imported_trace.operation == original_trace.operation


def test_evidence_validation_fails_on_change(
    sample_guardrail_policy: Path, sample_bead: VulnerabilityBead
):
    """Test that evidence validation fails if bead is modified."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrail_policy_path=str(sample_guardrail_policy),
    )
    adapter = AgentsSdkAdapter(config)

    # Create handoff context
    ctx = HandoffContext(
        source_agent="vrs-attacker",
        target_agent="vrs-defender",
        bead_id=sample_bead.id,
    )

    # Preserve evidence
    adapter.preserve_evidence(sample_bead, ctx)

    # Create modified bead (changed confidence) - with correct schema fields
    modified_bead = VulnerabilityBead(
        id=sample_bead.id,
        vulnerability_class=sample_bead.vulnerability_class,
        pattern_id=sample_bead.pattern_id,
        severity=sample_bead.severity,
        confidence=0.5,  # Changed from 0.95
        status=sample_bead.status,
        vulnerable_code=sample_bead.vulnerable_code,
        related_code=sample_bead.related_code,
        full_contract=sample_bead.full_contract,
        inheritance_chain=sample_bead.inheritance_chain,
        pattern_context=sample_bead.pattern_context,
        investigation_guide=sample_bead.investigation_guide,
        test_context=sample_bead.test_context,
        similar_exploits=sample_bead.similar_exploits,
        fix_recommendations=sample_bead.fix_recommendations,
    )

    # Validate - should fail
    is_preserved = adapter.validate_evidence_preserved(
        sample_bead, modified_bead, ctx
    )

    assert not is_preserved


def test_guardrails_disabled(tmp_path: Path):
    """Test adapter works with guardrails disabled."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrails_enabled=False,
    )
    adapter = AgentsSdkAdapter(config)

    # Should not load policies
    assert adapter.guardrail_policies == {}

    # Tool filtering should be no-op
    tools = [
        {"name": "Read"},
        {"name": "Write"},
    ]
    filtered = adapter._apply_input_guardrails("attacker", tools)

    # All tools should pass through
    assert len(filtered) == len(tools)


@pytest.mark.asyncio
async def test_execute_agent_basic(sample_guardrail_policy: Path):
    """Test basic agent execution."""
    config = AgentsSdkConfig(
        name="agents-sdk",
        api_key="sk-test",
        guardrail_policy_path=str(sample_guardrail_policy),
    )
    adapter = AgentsSdkAdapter(config)

    # Mock the runtime and output guardrails to avoid real API calls
    with patch.object(adapter, "_runtime") as mock_runtime, \
         patch.object(adapter, "_validate_output_guardrails", return_value=True):
        mock_runtime.execute = AsyncMock(
            return_value=AgentResponse(
                content="Mock response",
                tool_calls=[],
                input_tokens=100,
                output_tokens=50,
                model="gpt-4-turbo",
                metadata={},
            )
        )

        agent_config = AgentConfig(
            role=AgentRole.ATTACKER,
            system_prompt="Test prompt",
            tools=[{"name": "Read"}],
        )

        messages = [{"role": "user", "content": "Test message"}]

        response = await adapter.execute_agent(agent_config, messages)

        # Check response structure
        assert isinstance(response, AgentResponse)
        assert response.content is not None
        assert response.input_tokens >= 0
        assert response.output_tokens >= 0
        assert "adapter" in response.metadata
        assert response.metadata["adapter"] == "agents-sdk"
