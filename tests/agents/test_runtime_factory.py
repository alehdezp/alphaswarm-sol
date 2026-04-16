"""Tests for Runtime Factory.

Comprehensive tests for the runtime factory covering:
- RuntimeType enum values and conversions
- create_runtime() with each SDK type
- Deprecation warnings for legacy runtimes
- Configuration passing
- Error handling for invalid inputs
- Runtime availability checking
"""

from __future__ import annotations

import warnings
from unittest.mock import patch, MagicMock

import pytest

from alphaswarm_sol.agents.runtime.factory import (
    RuntimeType,
    create_runtime,
    get_available_runtimes,
    is_runtime_available,
)
from alphaswarm_sol.agents.runtime.opencode import OpenCodeRuntime, OpenCodeConfig
from alphaswarm_sol.agents.runtime.claude_code import ClaudeCodeRuntime, ClaudeCodeConfig
from alphaswarm_sol.agents.runtime.codex_cli import CodexCLIRuntime, CodexCLIConfig
from alphaswarm_sol.agents.runtime.anthropic import AnthropicRuntime
from alphaswarm_sol.agents.runtime.openai_agents import OpenAIAgentsRuntime
from alphaswarm_sol.agents.runtime.config import RuntimeConfig


# =============================================================================
# Test RuntimeType Enum
# =============================================================================

class TestRuntimeType:
    """Tests for RuntimeType enum."""

    def test_all_values_defined(self):
        """All expected RuntimeType values exist."""
        assert RuntimeType.OPENCODE.value == "opencode"
        assert RuntimeType.CLAUDE_CODE.value == "claude_code"
        assert RuntimeType.CODEX.value == "codex"
        assert RuntimeType.ANTHROPIC.value == "anthropic"
        assert RuntimeType.OPENAI.value == "openai"
        assert RuntimeType.AUTO.value == "auto"

    def test_string_conversion(self):
        """RuntimeType can be created from string."""
        assert RuntimeType("opencode") == RuntimeType.OPENCODE
        assert RuntimeType("claude_code") == RuntimeType.CLAUDE_CODE
        assert RuntimeType("codex") == RuntimeType.CODEX
        assert RuntimeType("anthropic") == RuntimeType.ANTHROPIC
        assert RuntimeType("openai") == RuntimeType.OPENAI
        assert RuntimeType("auto") == RuntimeType.AUTO

    def test_string_enum_comparison(self):
        """RuntimeType values are strings and compare with strings."""
        assert RuntimeType.OPENCODE == "opencode"
        assert RuntimeType.CLAUDE_CODE == "claude_code"
        assert RuntimeType.ANTHROPIC == "anthropic"

    def test_invalid_value_raises(self):
        """Invalid value raises ValueError."""
        with pytest.raises(ValueError):
            RuntimeType("invalid_sdk")


# =============================================================================
# Test create_runtime - OpenCode (Default)
# =============================================================================

class TestCreateRuntimeOpenCode:
    """Tests for create_runtime with OpenCode SDK."""

    def test_default_returns_opencode(self):
        """Default create_runtime() returns OpenCodeRuntime."""
        runtime = create_runtime()
        assert isinstance(runtime, OpenCodeRuntime)

    def test_explicit_opencode_string(self):
        """create_runtime('opencode') returns OpenCodeRuntime."""
        runtime = create_runtime("opencode")
        assert isinstance(runtime, OpenCodeRuntime)

    def test_explicit_opencode_enum(self):
        """create_runtime(RuntimeType.OPENCODE) returns OpenCodeRuntime."""
        runtime = create_runtime(RuntimeType.OPENCODE)
        assert isinstance(runtime, OpenCodeRuntime)

    def test_auto_returns_opencode(self):
        """'auto' defaults to OpenCode."""
        runtime = create_runtime("auto")
        assert isinstance(runtime, OpenCodeRuntime)

    def test_auto_enum_returns_opencode(self):
        """RuntimeType.AUTO defaults to OpenCode."""
        runtime = create_runtime(RuntimeType.AUTO)
        assert isinstance(runtime, OpenCodeRuntime)

    def test_opencode_with_config(self):
        """OpenCode runtime accepts OpenCodeConfig."""
        config = OpenCodeConfig(
            default_model="custom/model",
            timeout_seconds=60,
        )
        runtime = create_runtime("opencode", config=config)
        assert isinstance(runtime, OpenCodeRuntime)
        assert runtime.config.default_model == "custom/model"
        assert runtime.config.timeout_seconds == 60

    def test_opencode_with_kwargs(self):
        """OpenCode runtime accepts kwargs."""
        from pathlib import Path
        runtime = create_runtime("opencode", working_dir=Path("/tmp"))
        assert isinstance(runtime, OpenCodeRuntime)
        assert runtime.working_dir == Path("/tmp")


# =============================================================================
# Test create_runtime - Claude Code
# =============================================================================

class TestCreateRuntimeClaudeCode:
    """Tests for create_runtime with Claude Code CLI."""

    def test_claude_code_string(self):
        """create_runtime('claude_code') returns ClaudeCodeRuntime."""
        runtime = create_runtime("claude_code")
        assert isinstance(runtime, ClaudeCodeRuntime)

    def test_claude_code_enum(self):
        """create_runtime(RuntimeType.CLAUDE_CODE) returns ClaudeCodeRuntime."""
        runtime = create_runtime(RuntimeType.CLAUDE_CODE)
        assert isinstance(runtime, ClaudeCodeRuntime)

    def test_claude_code_with_config(self):
        """Claude Code runtime accepts ClaudeCodeConfig."""
        config = ClaudeCodeConfig(
            timeout_seconds=180,
            max_tokens=4096,
        )
        runtime = create_runtime("claude_code", config=config)
        assert isinstance(runtime, ClaudeCodeRuntime)
        assert runtime.config.timeout_seconds == 180
        assert runtime.config.max_tokens == 4096


# =============================================================================
# Test create_runtime - Codex CLI
# =============================================================================

class TestCreateRuntimeCodex:
    """Tests for create_runtime with Codex CLI."""

    def test_codex_string(self):
        """create_runtime('codex') returns CodexCLIRuntime."""
        runtime = create_runtime("codex")
        assert isinstance(runtime, CodexCLIRuntime)

    def test_codex_enum(self):
        """create_runtime(RuntimeType.CODEX) returns CodexCLIRuntime."""
        runtime = create_runtime(RuntimeType.CODEX)
        assert isinstance(runtime, CodexCLIRuntime)

    def test_codex_with_config(self):
        """Codex runtime accepts CodexCLIConfig."""
        config = CodexCLIConfig(
            timeout_seconds=240,
            approval_mode="suggest",
        )
        runtime = create_runtime("codex", config=config)
        assert isinstance(runtime, CodexCLIRuntime)
        assert runtime.config.timeout_seconds == 240
        assert runtime.config.approval_mode == "suggest"


# =============================================================================
# Test create_runtime - Legacy Runtimes with Deprecation Warnings
# =============================================================================

class TestCreateRuntimeLegacy:
    """Tests for create_runtime with legacy API runtimes."""

    def test_anthropic_emits_deprecation_warning(self):
        """'anthropic' SDK emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            runtime = create_runtime("anthropic")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "expensive" in str(w[0].message).lower()
            assert "deprecated" in str(w[0].message).lower()
            assert isinstance(runtime, AnthropicRuntime)

    def test_openai_emits_deprecation_warning(self):
        """'openai' SDK emits deprecation warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            runtime = create_runtime("openai")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "expensive" in str(w[0].message).lower()
            assert "deprecated" in str(w[0].message).lower()
            assert isinstance(runtime, OpenAIAgentsRuntime)

    def test_anthropic_with_config(self):
        """Anthropic runtime accepts RuntimeConfig."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            config = RuntimeConfig(
                preferred_sdk="anthropic",
                max_retries=5,
            )
            runtime = create_runtime("anthropic", config=config)
            assert isinstance(runtime, AnthropicRuntime)
            assert runtime.config.max_retries == 5


# =============================================================================
# Test create_runtime - Error Handling
# =============================================================================

class TestCreateRuntimeErrors:
    """Tests for create_runtime error handling."""

    def test_invalid_sdk_string_raises(self):
        """Invalid SDK string raises ValueError."""
        with pytest.raises(ValueError, match="Unknown SDK"):
            create_runtime("invalid_sdk")

    def test_wrong_config_type_uses_default(self):
        """Wrong config type logs warning and uses default."""
        # Passing RuntimeConfig to OpenCode should use default OpenCodeConfig
        wrong_config = RuntimeConfig(preferred_sdk="anthropic")
        runtime = create_runtime("opencode", config=wrong_config)

        # Should still work, using default config
        assert isinstance(runtime, OpenCodeRuntime)
        # Default model should be used
        assert runtime.config.default_model == "google/gemini-3-flash-preview"

    def test_case_insensitive_sdk_string(self):
        """SDK string matching is case-insensitive."""
        runtime = create_runtime("OpenCode")
        assert isinstance(runtime, OpenCodeRuntime)

        runtime = create_runtime("CLAUDE_CODE")
        assert isinstance(runtime, ClaudeCodeRuntime)


# =============================================================================
# Test is_runtime_available
# =============================================================================

class TestIsRuntimeAvailable:
    """Tests for is_runtime_available function."""

    @patch("shutil.which")
    def test_opencode_available_when_cli_exists(self, mock_which):
        """OpenCode available when CLI is installed."""
        mock_which.return_value = "/usr/local/bin/opencode"
        assert is_runtime_available("opencode") is True
        mock_which.assert_called_with("opencode")

    @patch("shutil.which")
    def test_opencode_unavailable_when_cli_missing(self, mock_which):
        """OpenCode unavailable when CLI not installed."""
        mock_which.return_value = None
        assert is_runtime_available("opencode") is False

    @patch("shutil.which")
    def test_claude_code_check_uses_claude_executable(self, mock_which):
        """Claude Code checks for 'claude' executable."""
        mock_which.return_value = "/usr/local/bin/claude"
        assert is_runtime_available("claude_code") is True
        mock_which.assert_called_with("claude")

    @patch("shutil.which")
    def test_codex_check_uses_codex_executable(self, mock_which):
        """Codex checks for 'codex' executable."""
        mock_which.return_value = "/usr/local/bin/codex"
        assert is_runtime_available(RuntimeType.CODEX) is True
        mock_which.assert_called_with("codex")

    def test_anthropic_available_when_package_installed(self):
        """Anthropic available when SDK installed."""
        # anthropic package should be installed in dev environment
        assert is_runtime_available("anthropic") is True

    def test_invalid_sdk_returns_false(self):
        """Invalid SDK returns False, not raises."""
        assert is_runtime_available("invalid_sdk") is False


# =============================================================================
# Test get_available_runtimes
# =============================================================================

class TestGetAvailableRuntimes:
    """Tests for get_available_runtimes function."""

    @patch("shutil.which")
    def test_returns_list(self, mock_which):
        """get_available_runtimes returns a list."""
        mock_which.return_value = None
        result = get_available_runtimes()
        assert isinstance(result, list)

    @patch("shutil.which")
    def test_includes_api_runtimes(self, mock_which):
        """API runtimes included when packages installed."""
        mock_which.return_value = None  # No CLI runtimes
        result = get_available_runtimes()

        # anthropic and openai should be installed in dev environment
        assert "anthropic" in result
        assert "openai" in result

    @patch("shutil.which")
    def test_includes_cli_runtimes_when_available(self, mock_which):
        """CLI runtimes included when executables exist."""
        def which_side_effect(name):
            if name == "opencode":
                return "/usr/local/bin/opencode"
            return None

        mock_which.side_effect = which_side_effect
        result = get_available_runtimes()

        assert "opencode" in result

    def test_auto_not_included(self):
        """'auto' type is not included in available runtimes."""
        result = get_available_runtimes()
        assert "auto" not in result


# =============================================================================
# Test Package Imports
# =============================================================================

class TestPackageImports:
    """Tests for package-level imports."""

    def test_all_runtimes_importable_from_package(self):
        """All runtime classes importable from runtime package."""
        from alphaswarm_sol.agents.runtime import (
            OpenCodeRuntime,
            ClaudeCodeRuntime,
            CodexCLIRuntime,
            AnthropicRuntime,
            OpenAIAgentsRuntime,
        )

        assert OpenCodeRuntime is not None
        assert ClaudeCodeRuntime is not None
        assert CodexCLIRuntime is not None
        assert AnthropicRuntime is not None
        assert OpenAIAgentsRuntime is not None

    def test_factory_importable_from_package(self):
        """Factory function and types importable from package."""
        from alphaswarm_sol.agents.runtime import (
            create_runtime,
            RuntimeType,
            get_available_runtimes,
            is_runtime_available,
        )

        assert callable(create_runtime)
        assert RuntimeType.OPENCODE is not None
        assert callable(get_available_runtimes)
        assert callable(is_runtime_available)

    def test_task_type_importable_from_package(self):
        """TaskType importable from package."""
        from alphaswarm_sol.agents.runtime import TaskType

        assert TaskType.VERIFY is not None
        assert TaskType.REASONING is not None
        assert TaskType.CODE is not None
