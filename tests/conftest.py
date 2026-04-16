"""Pytest Configuration and Shared Fixtures.

This module provides shared fixtures for runtime testing across all agent tests.

Fixtures:
    mock_opencode_cli: Mocks OpenCode CLI subprocess
    mock_claude_code_cli: Mocks Claude Code CLI subprocess
    mock_codex_cli: Mocks Codex CLI subprocess
    temp_rankings_store: Temporary rankings YAML store
    mock_all_runtimes: Combined mock for all CLI runtimes
    sample_agent_config: Sample AgentConfig for testing
    sample_messages: Sample conversation messages
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alphaswarm_sol.agents.runtime.base import AgentConfig, AgentResponse, AgentRole


# =============================================================================
# Mock Response Factories
# =============================================================================


def create_mock_response(
    content: str = "Mock response content",
    input_tokens: int = 100,
    output_tokens: int = 50,
    model: str = "test/model",
    cost_usd: float = 0.001,
    latency_ms: int = 500,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentResponse:
    """Create a mock AgentResponse with customizable values.

    Args:
        content: Response content
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model identifier
        cost_usd: Cost in USD
        latency_ms: Latency in milliseconds
        tool_calls: Optional list of tool calls
        metadata: Optional metadata dict

    Returns:
        AgentResponse with specified values
    """
    return AgentResponse(
        content=content,
        tool_calls=tool_calls or [],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model=model,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        metadata=metadata or {},
    )


def create_json_cli_response(
    content: str = "CLI response",
    input_tokens: int = 100,
    output_tokens: int = 50,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Create JSON response dict as returned by CLI tools.

    Args:
        content: Response content
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        tool_calls: Optional list of tool calls

    Returns:
        Dict matching CLI JSON output format
    """
    response = {
        "content": content,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }
    if tool_calls:
        response["tool_calls"] = tool_calls
    return response


# =============================================================================
# OpenCode CLI Mock Fixture
# =============================================================================


@pytest.fixture
def mock_opencode_cli():
    """Mock fixture for OpenCode CLI subprocess.

    Returns a context manager that patches asyncio.create_subprocess_exec
    to return mock JSON responses.

    The mock tracks all calls for verification.

    Usage:
        def test_something(mock_opencode_cli):
            with mock_opencode_cli() as mock:
                # Run test
                assert mock.call_count == 1
                assert "opencode" in mock.last_command

    Yields:
        Mock object with call tracking
    """
    class OpenCodeMock:
        def __init__(self):
            self.calls: List[List[str]] = []
            self.responses: List[Dict[str, Any]] = []
            self._next_response: Optional[Dict[str, Any]] = None
            self._patcher = None

        def set_response(self, response: Dict[str, Any]) -> None:
            """Set the next response to return."""
            self._next_response = response

        def add_response(self, response: Dict[str, Any]) -> None:
            """Add a response to the queue."""
            self.responses.append(response)

        @property
        def call_count(self) -> int:
            """Number of calls made."""
            return len(self.calls)

        @property
        def last_command(self) -> List[str]:
            """Last command executed."""
            return self.calls[-1] if self.calls else []

        def __enter__(self):
            async def mock_create_subprocess(*args, **kwargs):
                # Track the call
                cmd = list(args)
                self.calls.append(cmd)

                # Determine response
                if self._next_response:
                    response = self._next_response
                    self._next_response = None
                elif self.responses:
                    response = self.responses.pop(0)
                else:
                    response = create_json_cli_response(
                        content="OpenCode mock response",
                        input_tokens=100,
                        output_tokens=50,
                    )

                # Create mock process
                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(
                    return_value=(json.dumps(response).encode(), b"")
                )
                return mock_process

            self._patcher = patch(
                "asyncio.create_subprocess_exec",
                side_effect=mock_create_subprocess,
            )
            self._patcher.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self._patcher:
                self._patcher.stop()

    return OpenCodeMock


# =============================================================================
# Claude Code CLI Mock Fixture
# =============================================================================


@pytest.fixture
def mock_claude_code_cli():
    """Mock fixture for Claude Code CLI subprocess.

    Similar to mock_opencode_cli but returns subscription-based responses
    (cost_usd = 0.0).

    Usage:
        def test_claude(mock_claude_code_cli):
            with mock_claude_code_cli() as mock:
                # Run test
                assert mock.call_count == 1
                assert "claude" in mock.last_command

    Yields:
        Mock object with call tracking
    """
    class ClaudeCodeMock:
        def __init__(self):
            self.calls: List[List[str]] = []
            self.responses: List[Dict[str, Any]] = []
            self._next_response: Optional[Dict[str, Any]] = None
            self._patcher = None
            self.session_used: bool = False

        def set_response(self, response: Dict[str, Any]) -> None:
            """Set the next response to return."""
            self._next_response = response

        def add_response(self, response: Dict[str, Any]) -> None:
            """Add a response to the queue."""
            self.responses.append(response)

        @property
        def call_count(self) -> int:
            return len(self.calls)

        @property
        def last_command(self) -> List[str]:
            return self.calls[-1] if self.calls else []

        def __enter__(self):
            async def mock_create_subprocess(*args, **kwargs):
                cmd = list(args)
                self.calls.append(cmd)

                # Track session usage
                if "--resume" in cmd:
                    self.session_used = True

                # Determine response
                if self._next_response:
                    response = self._next_response
                    self._next_response = None
                elif self.responses:
                    response = self.responses.pop(0)
                else:
                    response = create_json_cli_response(
                        content="Claude Code mock response",
                        input_tokens=100,
                        output_tokens=50,
                    )

                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(
                    return_value=(json.dumps(response).encode(), b"")
                )
                return mock_process

            self._patcher = patch(
                "asyncio.create_subprocess_exec",
                side_effect=mock_create_subprocess,
            )
            self._patcher.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self._patcher:
                self._patcher.stop()

    return ClaudeCodeMock


# =============================================================================
# Codex CLI Mock Fixture
# =============================================================================


@pytest.fixture
def mock_codex_cli():
    """Mock fixture for Codex CLI subprocess.

    Returns GPT-4 style responses with subscription pricing.

    Usage:
        def test_codex(mock_codex_cli):
            with mock_codex_cli() as mock:
                # Run test
                assert mock.call_count == 1
                assert "codex" in mock.last_command

    Yields:
        Mock object with call tracking
    """
    class CodexMock:
        def __init__(self):
            self.calls: List[List[str]] = []
            self.responses: List[Dict[str, Any]] = []
            self._next_response: Optional[Dict[str, Any]] = None
            self._patcher = None

        def set_response(self, response: Dict[str, Any]) -> None:
            self._next_response = response

        def add_response(self, response: Dict[str, Any]) -> None:
            self.responses.append(response)

        @property
        def call_count(self) -> int:
            return len(self.calls)

        @property
        def last_command(self) -> List[str]:
            return self.calls[-1] if self.calls else []

        def __enter__(self):
            async def mock_create_subprocess(*args, **kwargs):
                cmd = list(args)
                self.calls.append(cmd)

                if self._next_response:
                    response = self._next_response
                    self._next_response = None
                elif self.responses:
                    response = self.responses.pop(0)
                else:
                    response = {
                        "content": "Codex mock response",
                        "output": "Codex mock response",  # Alternative key
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 50,
                        },
                    }

                mock_process = MagicMock()
                mock_process.returncode = 0
                mock_process.communicate = AsyncMock(
                    return_value=(json.dumps(response).encode(), b"")
                )
                return mock_process

            self._patcher = patch(
                "asyncio.create_subprocess_exec",
                side_effect=mock_create_subprocess,
            )
            self._patcher.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self._patcher:
                self._patcher.stop()

    return CodexMock


# =============================================================================
# Temporary Rankings Store Fixture
# =============================================================================


@pytest.fixture
def temp_rankings_store(tmp_path):
    """Create a temporary rankings YAML store.

    Creates a temporary directory with a rankings.yaml file.
    Cleans up automatically after test.

    Args:
        tmp_path: pytest tmp_path fixture

    Yields:
        Path to temporary rankings.yaml file

    Usage:
        def test_rankings(temp_rankings_store):
            store = RankingsStore(temp_rankings_store)
            store.update_ranking(...)
    """
    rankings_path = tmp_path / "rankings.yaml"
    yield rankings_path
    # Cleanup handled by tmp_path fixture


# =============================================================================
# Combined Mock Fixture
# =============================================================================


@pytest.fixture
def mock_all_runtimes(mock_opencode_cli, mock_claude_code_cli, mock_codex_cli):
    """Combined mock for all CLI runtimes.

    Provides a context manager that mocks all CLI runtimes simultaneously.
    Useful for integration tests that may route to different runtimes.

    Usage:
        def test_routing(mock_all_runtimes):
            with mock_all_runtimes() as mocks:
                # Run test that may use any runtime
                total_calls = (
                    mocks['opencode'].call_count +
                    mocks['claude_code'].call_count +
                    mocks['codex'].call_count
                )
                assert total_calls == 1

    Yields:
        Dict with all mock objects
    """
    class CombinedMock:
        def __init__(self):
            self.opencode = mock_opencode_cli()
            self.claude_code = mock_claude_code_cli()
            self.codex = mock_codex_cli()

        def __enter__(self):
            self.opencode.__enter__()
            self.claude_code.__enter__()
            self.codex.__enter__()
            return {
                "opencode": self.opencode,
                "claude_code": self.claude_code,
                "codex": self.codex,
            }

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.opencode.__exit__(exc_type, exc_val, exc_tb)
            self.claude_code.__exit__(exc_type, exc_val, exc_tb)
            self.codex.__exit__(exc_type, exc_val, exc_tb)

    return CombinedMock


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_agent_config():
    """Sample AgentConfig for testing.

    Returns a factory function that creates AgentConfig objects
    with customizable role and system prompt.

    Usage:
        def test_agent(sample_agent_config):
            config = sample_agent_config(AgentRole.ATTACKER)
            # or with custom prompt
            config = sample_agent_config(
                AgentRole.VERIFIER,
                system_prompt="Custom prompt"
            )

    Returns:
        Factory function that creates AgentConfig
    """
    def _create(
        role: AgentRole = AgentRole.VERIFIER,
        system_prompt: str = "You are a security expert.",
        tools: Optional[List[Any]] = None,
    ) -> AgentConfig:
        return AgentConfig(
            role=role,
            system_prompt=system_prompt,
            tools=tools or [],
        )

    return _create


@pytest.fixture
def sample_messages():
    """Sample conversation messages for testing.

    Returns a factory function that creates message lists
    in the expected format.

    Usage:
        def test_conversation(sample_messages):
            messages = sample_messages("Analyze this code")
            # or multi-turn
            messages = sample_messages(
                "Analyze this code",
                "Sure, I'll analyze it",
                "What vulnerabilities did you find?",
            )

    Returns:
        Factory function that creates message lists
    """
    def _create(*messages: str) -> List[Dict[str, str]]:
        result = []
        for i, content in enumerate(messages):
            role = "user" if i % 2 == 0 else "assistant"
            result.append({"role": role, "content": content})
        return result

    return _create


# =============================================================================
# Mock Runtime Fixture (for propulsion tests)
# =============================================================================


@pytest.fixture
def mock_runtime():
    """Mock runtime for propulsion engine tests.

    Returns a mock AgentRuntime that can be configured with
    custom responses and behavior.

    Usage:
        def test_engine(mock_runtime):
            runtime = mock_runtime(model="test/model", cost_usd=0.001)
            engine = PropulsionEngine(runtime, inboxes)
    """
    class MockAgentRuntime:
        def __init__(
            self,
            model: str = "test/model",
            cost_usd: float = 0.001,
            should_fail: bool = False,
            fail_message: str = "Mock failure",
        ):
            self.model = model
            self.cost_usd = cost_usd
            self.should_fail = should_fail
            self.fail_message = fail_message
            self.execute_calls: List[Dict[str, Any]] = []
            self.spawn_calls: List[Dict[str, Any]] = []

        async def execute(
            self,
            config: AgentConfig,
            messages: List[Dict[str, Any]],
        ) -> AgentResponse:
            self.execute_calls.append({
                "config": config,
                "messages": messages,
            })
            if self.should_fail:
                raise RuntimeError(self.fail_message)
            return create_mock_response(
                model=self.model,
                cost_usd=self.cost_usd,
            )

        async def spawn_agent(
            self,
            config: AgentConfig,
            task: str,
        ) -> AgentResponse:
            self.spawn_calls.append({
                "config": config,
                "task": task,
            })
            if self.should_fail:
                raise RuntimeError(self.fail_message)
            return create_mock_response(
                model=self.model,
                cost_usd=self.cost_usd,
            )

        def get_model_for_role(self, role: AgentRole) -> str:
            return self.model

        def get_usage(self) -> Dict[str, Any]:
            total_calls = len(self.execute_calls) + len(self.spawn_calls)
            return {"total_cost_usd": self.cost_usd * total_calls}

    def _create(**kwargs) -> MockAgentRuntime:
        return MockAgentRuntime(**kwargs)

    return _create


# =============================================================================
# Mock Bead Fixture
# =============================================================================


@pytest.fixture
def mock_bead():
    """Mock VulnerabilityBead for testing.

    Returns a factory function that creates mock beads
    with customizable properties.

    Usage:
        def test_bead_processing(mock_bead):
            bead = mock_bead("VKG-001", hypothesis="Reentrancy in withdraw")
    """
    class MockBead:
        def __init__(
            self,
            id: str = "VKG-001",
            hypothesis: str = "Test vulnerability hypothesis",
            work_state: Optional[Dict[str, Any]] = None,
            last_agent: Optional[str] = None,
            last_updated: Optional[datetime] = None,
        ):
            self.id = id
            self.hypothesis = hypothesis
            self.work_state = work_state
            self.last_agent = last_agent
            self.last_updated = last_updated

        def get_llm_prompt(self) -> str:
            return f"Analyze bead {self.id}: {self.hypothesis}"

    def _create(**kwargs) -> MockBead:
        return MockBead(**kwargs)

    return _create


# =============================================================================
# Mock Inbox Fixture
# =============================================================================


@pytest.fixture
def mock_inbox(mock_bead):
    """Mock AgentInbox for testing.

    Returns a factory function that creates mock inboxes
    with a queue of beads.

    Usage:
        def test_inbox(mock_inbox):
            inbox = mock_inbox([mock_bead("VKG-001"), mock_bead("VKG-002")])
            claim = inbox.claim_work()
            assert claim is not None
    """
    class MockInbox:
        def __init__(self, beads: List[Any]):
            self._beads = list(beads)
            self._claimed: Dict[str, Any] = {}
            self._completed: set = set()
            self._failed: set = set()

        @property
        def pending_count(self) -> int:
            return len(self._beads)

        def claim_work(self):
            if not self._beads:
                return None
            bead = self._beads.pop(0)
            self._claimed[bead.id] = bead
            claim = MagicMock()
            claim.bead = bead
            return claim

        def complete_work(self, bead_id: str) -> None:
            self._completed.add(bead_id)

        def fail_work(self, bead_id: str) -> None:
            self._failed.add(bead_id)

    def _create(beads: Optional[List[Any]] = None) -> MockInbox:
        if beads is None:
            beads = [mock_bead()]
        return MockInbox(beads)

    return _create
