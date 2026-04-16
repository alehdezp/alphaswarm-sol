"""CLI Tool Detection and Management.

This module provides detection and management of AI coding CLI tools
(Claude Code, Codex CLI, OpenCode CLI) that can spawn micro-agents
for parallel verification and test generation.

Key features:
- CLI tool availability detection
- Version checking
- Configuration validation
- Graceful fallback handling

The CLI tools are OPTIONAL - VKG works without them but gains:
- Parallel verification of multiple findings
- Iterative test generation with self-correction
- Isolated context for each micro-agent

Usage:
    from alphaswarm_sol.agents.sdk import (
        SDKManager,
        SDKType,
        sdk_available,
        get_available_sdks,
    )

    # Check if any CLI tool is available
    if sdk_available():
        manager = SDKManager()
        print(f"Available: {manager.available_sdks}")

    # Check specific CLI tool
    if sdk_available(SDKType.CLAUDE):
        print("Claude Code CLI is available")
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, TypeVar
import logging


logger = logging.getLogger(__name__)


class SDKType(str, Enum):
    """Types of CLI tools supported.

    VKG can work with multiple CLI tools:
    - CLAUDE: Claude Code (via claude CLI)
    - CODEX: Codex CLI (via codex CLI)
    - OPENCODE: OpenCode CLI (via opencode CLI)
    - MOCK: Mock for testing
    """
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"
    MOCK = "mock"


class SDKStatus(str, Enum):
    """Status of an SDK."""
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"
    NOT_CONFIGURED = "not_configured"
    VERSION_MISMATCH = "version_mismatch"
    ERROR = "error"


@dataclass
class SDKInfo:
    """Information about an SDK installation.

    Attributes:
        sdk_type: Type of SDK
        status: Current status
        version: Version string if available
        path: Path to the SDK executable
        capabilities: What the SDK can do
        error: Error message if status is ERROR
    """
    sdk_type: SDKType
    status: SDKStatus
    version: Optional[str] = None
    path: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sdk_type": self.sdk_type.value,
            "status": self.status.value,
            "version": self.version,
            "path": self.path,
            "capabilities": self.capabilities,
            "error": self.error,
        }

    @property
    def is_available(self) -> bool:
        """Whether SDK is available for use."""
        return self.status == SDKStatus.AVAILABLE


@dataclass
class SDKConfig:
    """Configuration for SDK usage.

    Attributes:
        enabled_sdks: Which SDKs to use (in preference order)
        timeout_seconds: Timeout for SDK operations
        max_parallel: Maximum parallel micro-agents
        default_budget_usd: Default budget per micro-agent
        allowed_tools: Tools micro-agents can use
    """
    enabled_sdks: List[SDKType] = field(default_factory=lambda: [
        SDKType.CLAUDE,
        SDKType.CODEX,
        SDKType.OPENCODE,
    ])
    timeout_seconds: int = 120
    max_parallel: int = 5
    default_budget_usd: float = 0.50
    allowed_tools: List[str] = field(default_factory=lambda: [
        "Read",
        "Bash",
    ])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled_sdks": [sdk.value for sdk in self.enabled_sdks],
            "timeout_seconds": self.timeout_seconds,
            "max_parallel": self.max_parallel,
            "default_budget_usd": self.default_budget_usd,
            "allowed_tools": self.allowed_tools,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SDKConfig":
        """Create from dictionary."""
        enabled = [SDKType(s) for s in data.get("enabled_sdks", [])]
        return cls(
            enabled_sdks=enabled or [SDKType.CLAUDE, SDKType.CODEX, SDKType.OPENCODE],
            timeout_seconds=data.get("timeout_seconds", 120),
            max_parallel=data.get("max_parallel", 5),
            default_budget_usd=data.get("default_budget_usd", 0.50),
            allowed_tools=data.get("allowed_tools", ["Read", "Bash"]),
        )


# SDK detection functions for each type

def _detect_claude_sdk() -> SDKInfo:
    """Detect Claude Code CLI."""
    try:
        # Check if claude is in PATH
        claude_path = shutil.which("claude")
        if not claude_path:
            return SDKInfo(
                sdk_type=SDKType.CLAUDE,
                status=SDKStatus.NOT_INSTALLED,
                error="claude CLI not found in PATH"
            )

        # Get version
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return SDKInfo(
                sdk_type=SDKType.CLAUDE,
                status=SDKStatus.ERROR,
                path=claude_path,
                error=f"Version check failed: {result.stderr}"
            )

        version = result.stdout.strip()
        if "claude" in version.lower() or version:
            return SDKInfo(
                sdk_type=SDKType.CLAUDE,
                status=SDKStatus.AVAILABLE,
                version=version,
                path=claude_path,
                capabilities=[
                    "spawn_agent",
                    "read_files",
                    "bash_execution",
                    "structured_output",
                    "budget_control",
                ]
            )

        return SDKInfo(
            sdk_type=SDKType.CLAUDE,
            status=SDKStatus.ERROR,
            path=claude_path,
            error=f"Unexpected version output: {version}"
        )

    except subprocess.TimeoutExpired:
        return SDKInfo(
            sdk_type=SDKType.CLAUDE,
            status=SDKStatus.ERROR,
            error="claude --version timed out"
        )
    except FileNotFoundError:
        return SDKInfo(
            sdk_type=SDKType.CLAUDE,
            status=SDKStatus.NOT_INSTALLED,
            error="claude executable not found"
        )
    except Exception as e:
        return SDKInfo(
            sdk_type=SDKType.CLAUDE,
            status=SDKStatus.ERROR,
            error=str(e)
        )


def _detect_codex_sdk() -> SDKInfo:
    """Detect Codex CLI."""
    try:
        codex_path = shutil.which("codex")
        if not codex_path:
            return SDKInfo(
                sdk_type=SDKType.CODEX,
                status=SDKStatus.NOT_INSTALLED,
                error="codex CLI not found in PATH"
            )

        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return SDKInfo(
                sdk_type=SDKType.CODEX,
                status=SDKStatus.ERROR,
                path=codex_path,
                error=f"Version check failed: {result.stderr}"
            )

        version = result.stdout.strip()
        return SDKInfo(
            sdk_type=SDKType.CODEX,
            status=SDKStatus.AVAILABLE,
            version=version,
            path=codex_path,
            capabilities=[
                "spawn_thread",
                "exec_noninteractive",
                "resume_thread",
                "structured_output",
            ]
        )

    except subprocess.TimeoutExpired:
        return SDKInfo(
            sdk_type=SDKType.CODEX,
            status=SDKStatus.ERROR,
            error="codex --version timed out"
        )
    except FileNotFoundError:
        return SDKInfo(
            sdk_type=SDKType.CODEX,
            status=SDKStatus.NOT_INSTALLED,
            error="codex executable not found"
        )
    except Exception as e:
        return SDKInfo(
            sdk_type=SDKType.CODEX,
            status=SDKStatus.ERROR,
            error=str(e)
        )


def _detect_opencode_sdk() -> SDKInfo:
    """Detect OpenCode CLI."""
    try:
        opencode_path = shutil.which("opencode")
        if not opencode_path:
            return SDKInfo(
                sdk_type=SDKType.OPENCODE,
                status=SDKStatus.NOT_INSTALLED,
                error="opencode CLI not found in PATH"
            )

        result = subprocess.run(
            ["opencode", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return SDKInfo(
                sdk_type=SDKType.OPENCODE,
                status=SDKStatus.ERROR,
                path=opencode_path,
                error=f"Version check failed: {result.stderr}"
            )

        version = result.stdout.strip()
        return SDKInfo(
            sdk_type=SDKType.OPENCODE,
            status=SDKStatus.AVAILABLE,
            version=version,
            path=opencode_path,
            capabilities=[
                "spawn_session",
                "multi_provider",
                "structured_output",
            ]
        )

    except subprocess.TimeoutExpired:
        return SDKInfo(
            sdk_type=SDKType.OPENCODE,
            status=SDKStatus.ERROR,
            error="opencode --version timed out"
        )
    except FileNotFoundError:
        return SDKInfo(
            sdk_type=SDKType.OPENCODE,
            status=SDKStatus.NOT_INSTALLED,
            error="opencode executable not found"
        )
    except Exception as e:
        return SDKInfo(
            sdk_type=SDKType.OPENCODE,
            status=SDKStatus.ERROR,
            error=str(e)
        )


def _detect_mock_sdk() -> SDKInfo:
    """Mock SDK for testing - always available."""
    return SDKInfo(
        sdk_type=SDKType.MOCK,
        status=SDKStatus.AVAILABLE,
        version="1.0.0-mock",
        path="mock://sdk",
        capabilities=[
            "spawn_agent",
            "mock_responses",
            "testing",
        ]
    )


# Detection registry
_SDK_DETECTORS: Dict[SDKType, Callable[[], SDKInfo]] = {
    SDKType.CLAUDE: _detect_claude_sdk,
    SDKType.CODEX: _detect_codex_sdk,
    SDKType.OPENCODE: _detect_opencode_sdk,
    SDKType.MOCK: _detect_mock_sdk,
}


class SDKManager:
    """Manager for CLI tool detection and selection.

    The SDKManager detects available CLI tools and provides a unified
    interface for spawning micro-agents regardless of which tool
    is being used.

    Example:
        manager = SDKManager()
        if manager.any_available():
            sdk = manager.get_best_available()
            print(f"Using {sdk.sdk_type.value} for micro-agents")
    """

    def __init__(self, config: Optional[SDKConfig] = None):
        """Initialize SDK manager.

        Args:
            config: Optional SDK configuration
        """
        self.config = config or SDKConfig()
        self._sdk_info: Dict[SDKType, SDKInfo] = {}
        self._detected = False

    def detect_all(self, force: bool = False) -> Dict[SDKType, SDKInfo]:
        """Detect all configured SDKs.

        Args:
            force: Force re-detection even if already done

        Returns:
            Dictionary of SDK type to info
        """
        if self._detected and not force:
            return self._sdk_info

        for sdk_type in self.config.enabled_sdks:
            detector = _SDK_DETECTORS.get(sdk_type)
            if detector:
                self._sdk_info[sdk_type] = detector()
            else:
                self._sdk_info[sdk_type] = SDKInfo(
                    sdk_type=sdk_type,
                    status=SDKStatus.ERROR,
                    error=f"No detector for {sdk_type.value}"
                )

        self._detected = True
        return self._sdk_info

    def detect_one(self, sdk_type: SDKType) -> SDKInfo:
        """Detect a specific SDK.

        Args:
            sdk_type: SDK type to detect

        Returns:
            SDK info
        """
        detector = _SDK_DETECTORS.get(sdk_type)
        if not detector:
            return SDKInfo(
                sdk_type=sdk_type,
                status=SDKStatus.ERROR,
                error=f"No detector for {sdk_type.value}"
            )

        info = detector()
        self._sdk_info[sdk_type] = info
        return info

    def any_available(self) -> bool:
        """Check if any SDK is available.

        Returns:
            True if at least one SDK is available
        """
        self.detect_all()
        return any(info.is_available for info in self._sdk_info.values())

    def get_best_available(self) -> Optional[SDKInfo]:
        """Get the best available SDK based on preference order.

        Returns first available SDK from enabled_sdks list.

        Returns:
            SDKInfo for best available SDK, or None
        """
        self.detect_all()

        for sdk_type in self.config.enabled_sdks:
            info = self._sdk_info.get(sdk_type)
            if info and info.is_available:
                return info

        return None

    @property
    def available_sdks(self) -> List[SDKType]:
        """List of available SDK types."""
        self.detect_all()
        return [
            sdk_type for sdk_type, info in self._sdk_info.items()
            if info.is_available
        ]

    @property
    def all_info(self) -> Dict[SDKType, SDKInfo]:
        """Get all SDK info (triggers detection if not done)."""
        self.detect_all()
        return self._sdk_info

    def get_status_report(self) -> Dict[str, Any]:
        """Get a status report of all SDKs.

        Returns:
            Status report as dictionary
        """
        self.detect_all()
        return {
            "any_available": self.any_available(),
            "available_sdks": [s.value for s in self.available_sdks],
            "best_sdk": (
                self.get_best_available().sdk_type.value
                if self.get_best_available()
                else None
            ),
            "details": {
                sdk_type.value: info.to_dict()
                for sdk_type, info in self._sdk_info.items()
            },
            "config": self.config.to_dict(),
        }


# Convenience functions for quick checks

def sdk_available(sdk_type: Optional[SDKType] = None) -> bool:
    """Check if an SDK is available.

    Args:
        sdk_type: Specific SDK to check, or None for any

    Returns:
        True if SDK is available
    """
    manager = SDKManager()

    if sdk_type is None:
        return manager.any_available()

    info = manager.detect_one(sdk_type)
    return info.is_available


def get_available_sdks() -> List[SDKType]:
    """Get list of available SDK types.

    Returns:
        List of available SDK types
    """
    manager = SDKManager()
    return manager.available_sdks


def get_sdk_manager(config: Optional[SDKConfig] = None) -> SDKManager:
    """Get an SDK manager instance.

    Args:
        config: Optional configuration

    Returns:
        Configured SDKManager
    """
    return SDKManager(config)


# Installation guidance

INSTALLATION_GUIDES: Dict[SDKType, str] = {
    SDKType.CLAUDE: """
Claude Code Installation:
  npm install -g @anthropic-ai/claude-code

Or with Homebrew:
  brew install claude-code

Requires Anthropic account with Claude Code access.
""",
    SDKType.CODEX: """
Codex CLI Installation:
  npm install -g @openai/codex-cli

Or use the Python SDK:
  pip install openai-codex

Requires OpenAI account with Codex access.
""",
    SDKType.OPENCODE: """
OpenCode CLI Installation:
  go install github.com/opencode-ai/opencode@latest

Or with npm:
  npm install -g opencode

Works with 75+ LLM providers.
""",
}


def get_installation_guide(sdk_type: SDKType) -> str:
    """Get installation guide for an SDK.

    Args:
        sdk_type: SDK to get guide for

    Returns:
        Installation instructions
    """
    return INSTALLATION_GUIDES.get(sdk_type, f"No installation guide for {sdk_type.value}")


def get_fallback_message(sdk_type: Optional[SDKType] = None) -> str:
    """Get a user-friendly fallback message when SDK unavailable.

    Args:
        sdk_type: Specific SDK that was needed

    Returns:
        Fallback message with guidance
    """
    manager = SDKManager()

    if manager.any_available():
        best = manager.get_best_available()
        if best:
            return f"Using {best.sdk_type.value} SDK as fallback."

    if sdk_type:
        guide = get_installation_guide(sdk_type)
        return f"""
CLI tool not available.

{guide}

Falling back to scaffold generation mode.
Test scaffold will be saved for manual execution.
"""

    return """
No CLI tool available.

For parallel verification and iterative test generation, install one of:
- Claude Code: npm install -g @anthropic-ai/claude-code
- Codex CLI: npm install -g @openai/codex-cli
- OpenCode CLI: go install github.com/opencode-ai/opencode@latest

VKG will continue with scaffold generation mode.
"""
