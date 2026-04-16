"""Tests for 3.1c-05 Bridge Transformer.

Verifies:
- Round-trip: transform(real_plan02_hook_payload) -> EvaluationInput
- Null-safety: payload missing tool_use_id -> returns None with warning
- Batch transform filters out None results
- Structured output preserves traceability metadata
"""

from __future__ import annotations

import logging

import pytest

from alphaswarm_sol.testing.evaluation.bridge_transformer import BridgeTransformer
from alphaswarm_sol.testing.evaluation.models import EvaluationInput, RunMode


# ---------------------------------------------------------------------------
# Real Plan 02 hook payload fixtures
# ---------------------------------------------------------------------------

# This fixture represents a real Plan 02 PostToolUse observation payload
# as produced by the observation hooks (ObservationRecord schema).
REAL_PLAN02_HOOK_PAYLOAD = {
    "timestamp": "2026-02-26T18:30:00.000Z",
    "session_id": "investigation-eeb93c51",
    "event_type": "tool_use",
    "hook_name": "observe_tool_use.py",
    "hook_type": "PostToolUse",
    "tool_use_id": "toolu_01ABC123",
    "data": {
        "tool_use_id": "toolu_01ABC123",
        "tool_name": "Bash",
        "duration_ms": 1523.4,
        "raw_observation": "Running: alphaswarm build-kg contracts/ReentrancyVuln.sol\nGraph built: 42 nodes, 128 edges",
        "bskg_queries": [
            {
                "query_text": "functions without access control",
                "query_type": "natural_language",
            }
        ],
    },
}

# Minimal payload with tool_use_id at top level only
MINIMAL_PLAN02_PAYLOAD = {
    "timestamp": "2026-02-26T18:31:00.000Z",
    "session_id": "tool-run-453e6460",
    "event_type": "tool_result",
    "hook_name": "observe_tool_result.py",
    "tool_use_id": "toolu_02DEF456",
    "data": {
        "response_text": "Slither analysis complete: 3 findings",
    },
}

# Payload missing tool_use_id entirely (should return None)
PAYLOAD_MISSING_TOOL_USE_ID = {
    "timestamp": "2026-02-26T18:32:00.000Z",
    "session_id": "bad-session",
    "event_type": "message",
    "hook_name": "observe_message.py",
    "data": {
        "content": "Some agent message",
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBridgeTransformer:
    def setup_method(self):
        self.transformer = BridgeTransformer()

    def test_round_trip_real_payload(self):
        """transform(real Plan 02 hook payload) produces valid EvaluationInput."""
        result = self.transformer.transform(REAL_PLAN02_HOOK_PAYLOAD)

        assert result is not None
        assert isinstance(result, EvaluationInput)
        assert result.run_id == "investigation-eeb93c51:toolu_01ABC123"
        assert "Bash" in result.tool_sequence
        assert len(result.bskg_queries) == 1
        assert result.bskg_queries[0]["query_text"] == "functions without access control"
        assert result.duration_ms == 1523.4
        assert "alphaswarm build-kg" in result.response_text
        assert result.structured_output is not None
        assert result.structured_output["tool_use_id"] == "toolu_01ABC123"
        assert result.structured_output["hook_type"] == "PostToolUse"

    def test_round_trip_minimal_payload(self):
        """Minimal payload with top-level tool_use_id transforms correctly."""
        result = self.transformer.transform(MINIMAL_PLAN02_PAYLOAD)

        assert result is not None
        assert isinstance(result, EvaluationInput)
        assert "toolu_02DEF456" in result.run_id
        assert "Slither analysis complete" in result.response_text

    def test_none_on_missing_tool_use_id(self, caplog):
        """Payload missing tool_use_id returns None with warning."""
        with caplog.at_level(logging.WARNING):
            result = self.transformer.transform(PAYLOAD_MISSING_TOOL_USE_ID)

        assert result is None
        assert "missing tool_use_id" in caplog.text

    def test_none_on_non_dict(self, caplog):
        """Non-dict payload returns None with warning."""
        with caplog.at_level(logging.WARNING):
            result = self.transformer.transform("not a dict")  # type: ignore[arg-type]

        assert result is None
        assert "not a dict" in caplog.text

    def test_none_on_empty_tool_use_id(self, caplog):
        """Empty string tool_use_id returns None."""
        payload = {
            "tool_use_id": "",
            "session_id": "s",
            "data": {},
        }
        with caplog.at_level(logging.WARNING):
            result = self.transformer.transform(payload)

        assert result is None

    def test_custom_run_mode(self):
        """Custom run_mode is propagated to EvaluationInput."""
        transformer = BridgeTransformer(run_mode=RunMode.HEADLESS)
        result = transformer.transform(REAL_PLAN02_HOOK_PAYLOAD)

        assert result is not None
        assert result.run_mode == RunMode.HEADLESS

    def test_custom_scenario_name(self):
        """Custom default_scenario_name is used when payload lacks one."""
        transformer = BridgeTransformer(default_scenario_name="custom_scenario")
        result = transformer.transform(REAL_PLAN02_HOOK_PAYLOAD)

        assert result is not None
        assert result.scenario_name == "custom_scenario"

    def test_scenario_name_from_payload(self):
        """scenario_name in payload overrides default."""
        payload = {
            **REAL_PLAN02_HOOK_PAYLOAD,
            "data": {
                **REAL_PLAN02_HOOK_PAYLOAD["data"],
                "scenario_name": "from_payload",
            },
        }
        result = self.transformer.transform(payload)

        assert result is not None
        assert result.scenario_name == "from_payload"

    def test_batch_transform_filters_none(self):
        """transform_batch filters out None results."""
        payloads = [
            REAL_PLAN02_HOOK_PAYLOAD,
            PAYLOAD_MISSING_TOOL_USE_ID,
            MINIMAL_PLAN02_PAYLOAD,
        ]
        results = self.transformer.transform_batch(payloads)

        assert len(results) == 2
        assert all(isinstance(r, EvaluationInput) for r in results)

    def test_evaluation_input_validates_against_schema(self):
        """Transformed output validates as proper EvaluationInput Pydantic model."""
        result = self.transformer.transform(REAL_PLAN02_HOOK_PAYLOAD)

        assert result is not None
        # Pydantic model_dump should not raise
        dumped = result.model_dump()
        assert "scenario_name" in dumped
        assert "run_id" in dumped
        assert "tool_sequence" in dumped
        assert "bskg_queries" in dumped
        assert "run_mode" in dumped

    def test_response_text_truncation(self):
        """Very long response text is truncated."""
        payload = {
            "tool_use_id": "toolu_long",
            "session_id": "s",
            "data": {
                "raw_observation": "x" * 10000,
            },
        }
        result = self.transformer.transform(payload)

        assert result is not None
        assert len(result.response_text) <= 4000

    def test_tool_use_id_from_data_fallback(self):
        """tool_use_id in data dict is used when not at top level."""
        payload = {
            "session_id": "s",
            "event_type": "tool_use",
            "hook_name": "h",
            "data": {
                "tool_use_id": "toolu_from_data",
                "tool_name": "Read",
            },
        }
        result = self.transformer.transform(payload)

        assert result is not None
        assert "toolu_from_data" in result.run_id
        assert "Read" in result.tool_sequence
