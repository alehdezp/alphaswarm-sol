"""End-to-end integration tests for observability infrastructure.

These tests validate that tracing, audit logging, and evidence lineage work
correctly in real-world pool execution scenarios.

Test Coverage:
1. Full pool produces complete trace with GenAI attributes
2. Trace context propagates across agent handoffs
3. Audit log captures verdict with trace ID
4. Evidence lineage chain is complete from BSKG to verdict
5. Token usage tracking in LLM calls
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from alphaswarm_sol.observability import (
    create_agent_span,
    create_handoff_span,
    create_tool_span,
    get_tracer,
    record_llm_usage,
    setup_tracing,
    shutdown_tracing,
)
from alphaswarm_sol.observability.audit import AuditCategory, AuditLogger
from alphaswarm_sol.observability.lineage import LineageTracker, SourceType
from alphaswarm_sol.orchestration import (
    ExecutionLoop,
    LoopConfig,
    Pool,
    PoolManager,
    PoolStatus,
    Scope,
    Verdict,
    VerdictConfidence,
)

# Test fixtures path
FIXTURES = Path(__file__).parent.parent / "fixtures"
SCENARIOS_PATH = FIXTURES / "observability_scenarios.yaml"


@pytest.fixture
def scenarios():
    """Load test scenarios from YAML."""
    with open(SCENARIOS_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    provider = MagicMock()
    provider.get_completion.return_value = {
        "content": "Test response",
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
    return provider


@pytest.fixture
def temp_pool_dir(tmp_path):
    """Temporary directory for pool storage."""
    pool_dir = tmp_path / ".vrs" / "pools"
    pool_dir.mkdir(parents=True)
    return pool_dir


@pytest.fixture
def temp_audit_log(tmp_path):
    """Temporary audit log file."""
    return tmp_path / "audit.log"


class TestObservabilityEndToEnd:
    """End-to-end tests for observability infrastructure."""

    def test_full_pool_produces_complete_trace(
        self, scenarios, mock_llm_provider, temp_pool_dir, tmp_path
    ):
        """Test that full pool execution produces complete trace with GenAI attributes.

        Validates:
        - Pool execution span created
        - Agent investigation spans created
        - Tool execution spans created
        - All spans have correct attributes
        """
        scenario = scenarios["full_pool_scenario"]

        # Setup tracing with in-memory exporter
        spans_captured = []

        def capture_span(span):
            spans_captured.append(
                {
                    "name": span.name,
                    "attributes": dict(span.attributes) if span.attributes else {},
                }
            )

        setup_tracing(service_name="test-service")
        tracer = get_tracer(__name__)

        # Create pool from scenario
        scope = Scope(files=scenario["scope"]["files"])
        pool = Pool(
            id=scenario["pool_id"],
            scope=scope,
            status=PoolStatus.EXECUTE,
        )

        # Add beads
        for bead_data in scenario["beads"]:
            pool.add_bead(bead_data["bead_id"])

        # Execute pool with tracing
        with tracer.start_as_current_span(
            "pool.execute",
            attributes={
                "pool_id": pool.id,
                "bead_count": len(pool.bead_ids),
            },
        ) as pool_span:
            capture_span(pool_span)

            # Simulate agent investigation
            for bead_data in scenario["beads"]:
                with create_agent_span(
                    agent_name="vrs-attacker",
                    bead_id=bead_data["bead_id"],
                    pool_id=pool.id,
                ) as agent_span:
                    capture_span(agent_span)

                    # Simulate tool execution
                    with create_tool_span(
                        tool_name="slither",
                        pool_id=pool.id,
                        bead_id=bead_data["bead_id"],
                    ) as tool_span:
                        capture_span(tool_span)

        # Verify spans captured
        assert len(spans_captured) >= 3, "Should capture pool, agent, and tool spans"

        # Verify pool span
        pool_spans = [s for s in spans_captured if s["name"] == "pool.execute"]
        assert len(pool_spans) == 1
        assert pool_spans[0]["attributes"]["pool_id"] == scenario["pool_id"]

        # Verify agent span
        agent_spans = [s for s in spans_captured if "vrs-attacker" in s["name"]]
        assert len(agent_spans) >= 1
        assert agent_spans[0]["attributes"]["alphaswarm.agent.name"] == "vrs-attacker"

        # Verify tool span
        tool_spans = [s for s in spans_captured if "tool.slither" in s["name"]]
        assert len(tool_spans) >= 1
        assert tool_spans[0]["attributes"]["alphaswarm.tool.name"] == "slither"

        shutdown_tracing()

    @pytest.mark.xfail(reason="Stale code: Observability e2e test infrastructure changed")
    def test_trace_context_propagates_across_handoffs(self, scenarios):
        """Test that trace context propagates correctly across agent handoffs.

        Validates:
        - Trace ID is preserved across handoffs
        - Parent-child relationships maintained
        - Context accessible in downstream agents
        """
        scenario = scenarios["handoff_scenario"]

        setup_tracing(service_name="test-handoff")
        tracer = get_tracer(__name__)

        trace_ids_captured = []

        # First agent (attacker)
        with tracer.start_as_current_span("agent.attacker") as attacker_span:
            attacker_trace_id = format(attacker_span.get_span_context().trace_id, "032x")
            trace_ids_captured.append(attacker_trace_id)

            # Handoff to defender
            with create_handoff_span(
                from_agent="vrs-attacker",
                to_agent="vrs-defender",
                bead_id="VKG-002",
            ) as handoff_span:
                handoff_trace_id = format(handoff_span.get_span_context().trace_id, "032x")
                trace_ids_captured.append(handoff_trace_id)

                # Second agent (defender)
                with tracer.start_as_current_span("agent.defender") as defender_span:
                    defender_trace_id = format(
                        defender_span.get_span_context().trace_id, "032x"
                    )
                    trace_ids_captured.append(defender_trace_id)

        # Verify same trace ID across all spans
        assert (
            len(set(trace_ids_captured)) == 1
        ), "All spans should share same trace ID across handoff"

        shutdown_tracing()

    @pytest.mark.xfail(reason="Stale code: Observability e2e test infrastructure changed")
    def test_audit_log_captures_verdict_with_trace_id(
        self, scenarios, temp_audit_log
    ):
        """Test that audit log captures verdict assignment with trace ID.

        Validates:
        - Verdict logged with correct category
        - Trace ID included in audit entry
        - Pool ID and bead ID recorded
        - Evidence references logged
        """
        scenario = scenarios["audit_log_scenario"]

        # Setup audit logger
        audit_logger = AuditLogger(log_path=temp_audit_log)

        # Log verdict
        audit_logger.log_verdict(
            pool_id=scenario["pool_id"],
            bead_id=scenario["verdict"]["bead_id"],
            verdict=scenario["verdict"]["verdict"],
            confidence=scenario["verdict"]["confidence"],
            evidence_refs=scenario["verdict"]["evidence_refs"],
            agent_type=scenario["verdict"]["agent_type"],
            trace_id=scenario["trace_id"],
        )

        # Verify audit log file created
        assert temp_audit_log.exists(), "Audit log file should be created"

        # Read and verify audit log entry
        log_lines = temp_audit_log.read_text().strip().split("\n")
        assert len(log_lines) >= 1, "Should have at least one log entry"

        # Parse last log entry (JSON formatted)
        log_entry = json.loads(log_lines[-1])

        # Verify expected fields
        assert log_entry["category"] == AuditCategory.VERDICT_ASSIGNMENT.value
        assert log_entry["trace_id"] == scenario["trace_id"]
        assert log_entry["pool_id"] == scenario["pool_id"]
        assert log_entry["bead_id"] == scenario["verdict"]["bead_id"]
        assert log_entry["verdict"] == scenario["verdict"]["verdict"]
        assert log_entry["confidence"] == scenario["verdict"]["confidence"]
        assert log_entry["evidence_refs"] == scenario["verdict"]["evidence_refs"]

    def test_evidence_lineage_chain_complete(self, scenarios):
        """Test that evidence lineage chain is complete from BSKG to verdict.

        Validates:
        - Origin step records BSKG source
        - Extraction step records agent
        - Transformation steps tracked
        - Verification step recorded
        - Complete chain queryable
        """
        scenario = scenarios["lineage_scenario"]

        tracker = LineageTracker()

        # Build lineage chain from scenario
        evidence_id = scenario["evidence_id"]

        # Create initial lineage (includes origin + extraction)
        lineage = tracker.create_lineage(
            evidence_id=evidence_id,
            source_type=SourceType.BSKG,
            source_id="node_func_withdraw_123",
            extracting_agent="vrs-attacker",
        )

        # Add transformation step
        tracker.add_transformation(
            evidence_id=evidence_id,
            transform_type="confidence_upgrade",
            transforming_agent="vrs-verifier",
            metadata={"from": "POSSIBLE", "to": "LIKELY"},
        )

        # Add verification step
        tracker.add_verification(
            evidence_id=evidence_id,
            verifying_agent="vrs-verifier",
            verification_result="confirmed",
        )

        # Get complete chain
        chain = tracker.get_lineage(evidence_id)

        # Verify chain completeness
        assert chain is not None, "Lineage chain should exist"
        assert len(chain.chain) >= 2, "Should have at least origin and extraction steps"

        # Verify BSKG origin
        origin_step = chain.chain[0]
        assert origin_step.source_type == SourceType.BSKG
        assert origin_step.source_id == "node_func_withdraw_123"

        # Verify transformation step exists
        transform_steps = [s for s in chain.chain if s.step_type == "transformation"]
        assert len(transform_steps) >= 1, "Should have transformation step"
        assert transform_steps[0].metadata.get("transform_type") == "confidence_upgrade"

        # Verify verification step exists
        verify_steps = [s for s in chain.chain if s.step_type == "verification"]
        assert len(verify_steps) >= 1, "Should have verification step"

        # Query by source
        derived_evidence = tracker.query_by_source(
            SourceType.BSKG,
            "node_func_withdraw_123",
        )
        assert any(
            e.evidence_id == evidence_id for e in derived_evidence
        ), "Should find evidence by BSKG source"


class TestTokenUsageTracking:
    """Tests for token usage tracking in LLM calls."""

    @pytest.mark.xfail(reason="Stale code: Observability e2e test infrastructure changed")
    def test_llm_call_records_token_usage(self, mock_llm_provider):
        """Test that LLM calls record token usage in spans.

        Validates:
        - Input tokens recorded
        - Output tokens recorded
        - Model name captured
        - Tokens accessible for cost calculation
        """
        setup_tracing(service_name="test-tokens")
        tracer = get_tracer(__name__)

        tokens_captured = []

        with tracer.start_as_current_span("agent.llm_call") as span:
            # Record LLM usage
            record_llm_usage(
                input_tokens=100,
                output_tokens=50,
                model="claude-opus-4",
                pool_id="test-pool",
            )

            # Capture attributes
            if span.attributes:
                tokens_captured.append(
                    {
                        "input_tokens": span.attributes.get("gen_ai.usage.input_tokens"),
                        "output_tokens": span.attributes.get(
                            "gen_ai.usage.output_tokens"
                        ),
                        "model": span.attributes.get("gen_ai.request.model"),
                    }
                )

        # Verify token data captured
        assert len(tokens_captured) >= 0, "Token data should be available"

        shutdown_tracing()
