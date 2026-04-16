"""
Tool Registry

Discovers installed static analysis tools, validates their health, and provides
installation guidance. Per PHILOSOPHY.md Pillar 6, tools are discovered but
never executed without proper health checks.

Usage:
    registry = ToolRegistry()
    health = registry.check_all_tools()
    if not registry.validate_all_before_analysis():
        print("Missing required tools")
"""

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class ToolTier(IntEnum):
    """Tool importance tiers.

    Tier 0: Core tools required for basic VKG operation.
    Tier 1: Recommended tools for comprehensive analysis.
    Tier 2: Optional tools for specialized analysis.
    """

    CORE = 0
    RECOMMENDED = 1
    OPTIONAL = 2


class ModelTier:
    """LLM model tiers for tool execution.

    Tools are executed by Claude models with appropriate capability:
    - haiku-4.5: Fast, cheap - used for tool running
    - sonnet-4.5: Balanced - used for coordination
    """

    RUNNING = "haiku-4.5"
    COORDINATION = "sonnet-4.5"


@dataclass
class ToolInfo:
    """Static information about a tool.

    Attributes:
        name: Tool identifier (e.g., 'slither', 'aderyn').
        tier: Importance tier (0=core, 1=recommended, 2=optional).
        binary: Executable name to search for.
        install_method: How to install (pip, cargo, curl, binary).
        install_hint: Human-readable installation command.
        version_cmd: Command to get version (e.g., ['slither', '--version']).
        health_cmd: Command to verify tool works (may differ from version_cmd).
        model_tier: Which LLM tier should run this tool.
        description: Brief description of tool purpose.
        homepage: URL for more information.
        output_format: Primary output format (json, sarif, text).
        timeout_default: Default timeout in seconds.
    """

    name: str
    tier: ToolTier
    binary: str
    install_method: str
    install_hint: str
    version_cmd: List[str]
    health_cmd: List[str]
    model_tier: str = ModelTier.RUNNING
    description: str = ""
    homepage: str = ""
    output_format: str = "json"
    timeout_default: int = 120


@dataclass
class ToolHealth:
    """Health status of a tool.

    Attributes:
        tool: Tool name.
        installed: Whether the binary was found.
        version: Detected version string (if available).
        healthy: Whether the tool responds correctly.
        error: Error message if unhealthy.
        last_checked: When this check was performed.
        binary_path: Full path to the binary (if found).
    """

    tool: str
    installed: bool
    version: Optional[str] = None
    healthy: bool = False
    error: Optional[str] = None
    last_checked: datetime = field(default_factory=datetime.utcnow)
    binary_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool": self.tool,
            "installed": self.installed,
            "version": self.version,
            "healthy": self.healthy,
            "error": self.error,
            "last_checked": self.last_checked.isoformat(),
            "binary_path": self.binary_path,
        }


class ToolRegistry:
    """Registry of external static analysis tools.

    Manages tool discovery, health checking, and installation guidance.
    Per PHILOSOPHY.md, tool failures are warnings, not errors - VKG
    continues with available tools.

    Example:
        registry = ToolRegistry()

        # Check all tools
        health = registry.check_all_tools()
        for name, status in health.items():
            print(f"{name}: {'OK' if status.healthy else 'MISSING'}")

        # Get install hints for missing
        for tool in registry.get_missing_tools():
            print(f"Install {tool}: {registry.get_install_hint(tool)}")
    """

    # Tool definitions - static configuration for all supported tools
    TOOL_DEFINITIONS: ClassVar[Dict[str, ToolInfo]] = {
        # Tier 0: Core tools (required for basic operation)
        "slither": ToolInfo(
            name="slither",
            tier=ToolTier.CORE,
            binary="slither",
            install_method="pip",
            install_hint="pip install slither-analyzer",
            version_cmd=["slither", "--version"],
            health_cmd=["slither", "--help"],
            description="Static analyzer for Solidity - primary VKG data source",
            homepage="https://github.com/crytic/slither",
            output_format="json",
            timeout_default=120,
        ),
        # Tier 1: Recommended tools (comprehensive analysis)
        "aderyn": ToolInfo(
            name="aderyn",
            tier=ToolTier.RECOMMENDED,
            binary="aderyn",
            install_method="cargo",
            install_hint="cargo install aderyn",
            version_cmd=["aderyn", "--version"],
            health_cmd=["aderyn", "--help"],
            description="Rust-based Solidity analyzer with custom detectors",
            homepage="https://github.com/Cyfrin/aderyn",
            output_format="json",
            timeout_default=60,
        ),
        "mythril": ToolInfo(
            name="mythril",
            tier=ToolTier.RECOMMENDED,
            binary="myth",
            install_method="pip",
            install_hint="pip install mythril",
            version_cmd=["myth", "version"],
            health_cmd=["myth", "--help"],
            description="Symbolic execution for vulnerability detection",
            homepage="https://github.com/Consensys/mythril",
            output_format="json",
            timeout_default=300,
        ),
        "echidna": ToolInfo(
            name="echidna",
            tier=ToolTier.RECOMMENDED,
            binary="echidna",
            install_method="binary",
            install_hint="Download from GitHub releases or: nix-env -iA nixpkgs.echidna",
            version_cmd=["echidna", "--version"],
            health_cmd=["echidna", "--help"],
            description="Property-based fuzzer for smart contracts",
            homepage="https://github.com/crytic/echidna",
            output_format="text",
            timeout_default=600,
        ),
        "foundry": ToolInfo(
            name="foundry",
            tier=ToolTier.RECOMMENDED,
            binary="forge",
            install_method="curl",
            install_hint="curl -L https://foundry.paradigm.xyz | bash && foundryup",
            version_cmd=["forge", "--version"],
            health_cmd=["forge", "--help"],
            description="Fast testing framework and toolkit",
            homepage="https://github.com/foundry-rs/foundry",
            output_format="json",
            timeout_default=180,
        ),
        "semgrep": ToolInfo(
            name="semgrep",
            tier=ToolTier.RECOMMENDED,
            binary="semgrep",
            install_method="pip",
            install_hint="pip install semgrep",
            version_cmd=["semgrep", "--version"],
            health_cmd=["semgrep", "--help"],
            description="Pattern-based code analysis",
            homepage="https://github.com/returntocorp/semgrep",
            output_format="json",
            timeout_default=120,
        ),
        # Tier 2: Optional tools (specialized analysis)
        "halmos": ToolInfo(
            name="halmos",
            tier=ToolTier.OPTIONAL,
            binary="halmos",
            install_method="uv",
            install_hint="uv tool install halmos",
            version_cmd=["halmos", "--version"],
            health_cmd=["halmos", "--help"],
            description="Symbolic bounded model checker",
            homepage="https://github.com/a16z/halmos",
            output_format="text",
            timeout_default=300,
        ),
        "medusa": ToolInfo(
            name="medusa",
            tier=ToolTier.OPTIONAL,
            binary="medusa",
            install_method="go",
            install_hint="go install github.com/crytic/medusa/cmd/medusa@latest",
            version_cmd=["medusa", "--version"],
            health_cmd=["medusa", "--help"],
            description="Parallel fuzzer based on go-ethereum",
            homepage="https://github.com/crytic/medusa",
            output_format="json",
            timeout_default=600,
        ),
        "solc": ToolInfo(
            name="solc",
            tier=ToolTier.OPTIONAL,
            binary="solc",
            install_method="pip",
            install_hint="pip install solc-select && solc-select install 0.8.20",
            version_cmd=["solc", "--version"],
            health_cmd=["solc", "--help"],
            description="Solidity compiler",
            homepage="https://github.com/ethereum/solidity",
            output_format="json",
            timeout_default=60,
        ),
        "crytic-compile": ToolInfo(
            name="crytic-compile",
            tier=ToolTier.OPTIONAL,
            binary="crytic-compile",
            install_method="pip",
            install_hint="pip install crytic-compile",
            version_cmd=["crytic-compile", "--version"],
            health_cmd=["crytic-compile", "--help"],
            description="Compilation framework supporting multiple build systems",
            homepage="https://github.com/crytic/crytic-compile",
            output_format="json",
            timeout_default=120,
        ),
    }

    def __init__(self, cache_duration_seconds: int = 300):
        """Initialize registry.

        Args:
            cache_duration_seconds: How long to cache health checks (5 min default).
        """
        self._cache_duration = cache_duration_seconds
        self._health_cache: Dict[str, ToolHealth] = {}

    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """Get static information about a tool.

        Args:
            name: Tool name.

        Returns:
            ToolInfo or None if unknown tool.
        """
        return self.TOOL_DEFINITIONS.get(name)

    def check_tool(self, name: str, force: bool = False) -> ToolHealth:
        """Check health of a single tool.

        Args:
            name: Tool name.
            force: Skip cache and re-check.

        Returns:
            ToolHealth with current status.
        """
        # Check cache
        if not force and name in self._health_cache:
            cached = self._health_cache[name]
            age = (datetime.utcnow() - cached.last_checked).total_seconds()
            if age < self._cache_duration:
                return cached

        tool_info = self.TOOL_DEFINITIONS.get(name)
        if not tool_info:
            health = ToolHealth(
                tool=name,
                installed=False,
                error=f"Unknown tool: {name}",
            )
            return health

        # Check if binary exists
        binary_path = shutil.which(tool_info.binary)
        if not binary_path:
            health = ToolHealth(
                tool=name,
                installed=False,
                error=f"Binary not found: {tool_info.binary}",
            )
            self._health_cache[name] = health
            logger.warning(
                "tool_not_found",
                tool=name,
                binary=tool_info.binary,
                install_hint=tool_info.install_hint,
            )
            return health

        # Get version
        version = self._get_version(tool_info)

        # Check health
        healthy, error = self._check_health(tool_info)

        health = ToolHealth(
            tool=name,
            installed=True,
            version=version,
            healthy=healthy,
            error=error,
            binary_path=binary_path,
        )
        self._health_cache[name] = health

        if healthy:
            logger.debug("tool_healthy", tool=name, version=version, path=binary_path)
        else:
            logger.warning("tool_unhealthy", tool=name, error=error)

        return health

    def check_all_tools(self, force: bool = False) -> Dict[str, ToolHealth]:
        """Check health of all known tools.

        Args:
            force: Skip cache and re-check all.

        Returns:
            Dict mapping tool name to health status.
        """
        results = {}
        for name in self.TOOL_DEFINITIONS:
            results[name] = self.check_tool(name, force=force)
        return results

    def get_available_tools(self) -> List[str]:
        """Get list of installed and healthy tools.

        Returns:
            List of tool names that are ready to use.
        """
        available = []
        for name in self.TOOL_DEFINITIONS:
            health = self.check_tool(name)
            if health.installed and health.healthy:
                available.append(name)
        return available

    def get_missing_tools(self, tier: Optional[ToolTier] = None) -> List[str]:
        """Get list of missing or unhealthy tools.

        Args:
            tier: Filter by tier (None = all tiers).

        Returns:
            List of tool names that are not available.
        """
        missing = []
        for name, info in self.TOOL_DEFINITIONS.items():
            if tier is not None and info.tier != tier:
                continue
            health = self.check_tool(name)
            if not health.installed or not health.healthy:
                missing.append(name)
        return missing

    def get_tools_by_tier(self, tier: ToolTier) -> List[str]:
        """Get tools in a specific tier.

        Args:
            tier: Tier to filter by.

        Returns:
            List of tool names in that tier.
        """
        return [
            name
            for name, info in self.TOOL_DEFINITIONS.items()
            if info.tier == tier
        ]

    def get_install_hint(self, name: str) -> str:
        """Get installation hint for a tool.

        Args:
            name: Tool name.

        Returns:
            Installation command or guidance.
        """
        tool_info = self.TOOL_DEFINITIONS.get(name)
        if tool_info:
            return tool_info.install_hint
        return f"Unknown tool: {name}. Check VKG documentation."

    def get_install_hints_batch(
        self, names: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """Get installation hints for multiple tools.

        Args:
            names: Tools to get hints for (None = all missing).

        Returns:
            Dict mapping tool name to install hint.
        """
        if names is None:
            names = self.get_missing_tools()
        return {name: self.get_install_hint(name) for name in names}

    def validate_all_before_analysis(self) -> bool:
        """Validate tool setup before starting analysis.

        Logs warnings for missing tools but never raises.
        Per PHILOSOPHY.md: tool failures are warnings, not blockers.

        Returns:
            True if at least Tier 0 tools are available.
        """
        health = self.check_all_tools()

        # Categorize by tier
        tier_status: Dict[ToolTier, List[str]] = {
            ToolTier.CORE: [],
            ToolTier.RECOMMENDED: [],
            ToolTier.OPTIONAL: [],
        }
        available_count = 0
        missing_count = 0

        for name, status in health.items():
            info = self.TOOL_DEFINITIONS[name]
            if status.healthy:
                available_count += 1
            else:
                tier_status[info.tier].append(name)
                missing_count += 1

        # Log summary
        logger.info(
            "tool_validation_complete",
            available=available_count,
            missing=missing_count,
            total=len(self.TOOL_DEFINITIONS),
        )

        # Warn about missing Tier 0 (core) tools
        if tier_status[ToolTier.CORE]:
            for tool in tier_status[ToolTier.CORE]:
                logger.warning(
                    "core_tool_missing",
                    tool=tool,
                    install=self.get_install_hint(tool),
                    impact="VKG functionality will be limited",
                )

        # Info about missing Tier 1 (recommended) tools
        if tier_status[ToolTier.RECOMMENDED]:
            logger.info(
                "recommended_tools_missing",
                tools=tier_status[ToolTier.RECOMMENDED],
                install_script=".vrs/install-tools.sh --tier-1",
            )

        # Return True if core tools available
        core_available = len(tier_status[ToolTier.CORE]) == 0
        return core_available

    def _get_version(self, tool_info: ToolInfo) -> Optional[str]:
        """Get version string from tool.

        Args:
            tool_info: Tool to check.

        Returns:
            Version string or None if unavailable.
        """
        try:
            result = subprocess.run(
                tool_info.version_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout or result.stderr
            if output:
                # Try to extract version number
                version = self._parse_version(output)
                return version or output.strip()[:50]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
            pass
        return None

    def _check_health(self, tool_info: ToolInfo) -> tuple[bool, Optional[str]]:
        """Check if tool responds correctly.

        Args:
            tool_info: Tool to check.

        Returns:
            Tuple of (healthy, error_message).
        """
        try:
            result = subprocess.run(
                tool_info.health_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            # Most tools return 0 on --help
            if result.returncode == 0:
                return True, None
            # Some tools return 1 on --help but still work
            if result.stdout or result.stderr:
                return True, None
            return False, f"Health check failed: exit code {result.returncode}"
        except subprocess.TimeoutExpired:
            return False, "Health check timed out"
        except subprocess.SubprocessError as e:
            return False, f"Health check error: {e}"
        except OSError as e:
            return False, f"OS error: {e}"

    def _parse_version(self, output: str) -> Optional[str]:
        """Extract version number from tool output.

        Args:
            output: Raw output from version command.

        Returns:
            Extracted version or None.
        """
        # Common patterns: "1.2.3", "v1.2.3", "version 1.2.3"
        patterns = [
            r"v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?)",
            r"version[:\s]+v?(\d+\.\d+\.\d+)",
            r"(\d+\.\d+\.\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def get_tools_for_context(
        self,
        max_tokens: int = 500,
        include_unavailable: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get compressed tool info for LLM context (Phase 7.1.3-05).

        Returns tool descriptions compressed for inclusion in LLM prompts.
        Applies compression strategies to reduce token usage.

        Args:
            max_tokens: Maximum tokens for tool context.
            include_unavailable: Include tools that aren't installed.

        Returns:
            List of compressed tool info dictionaries.

        Example:
            registry = ToolRegistry()
            tools = registry.get_tools_for_context(max_tokens=500)
            # Use in prompt context
        """
        from alphaswarm_sol.tools.description_compress import (
            compress_tool_descriptions,
        )

        # Get tool info as dicts
        tool_infos: List[Dict[str, Any]] = []
        for name, info in self.TOOL_DEFINITIONS.items():
            # Skip unavailable unless requested
            if not include_unavailable:
                health = self.check_tool(name)
                if not health.installed or not health.healthy:
                    continue

            tool_dict = {
                "name": info.name,
                "tier": info.tier.name.lower(),
                "binary": info.binary,
                "install_method": info.install_method,
                "install_hint": info.install_hint,
                "description": info.description,
                "output_format": info.output_format,
                "timeout_default": info.timeout_default,
            }
            tool_infos.append(tool_dict)

        # Compress for context
        return compress_tool_descriptions(
            tool_infos,
            max_tokens=max_tokens,
            aggressive=max_tokens < 300,  # Be aggressive for small budgets
        )

    def get_tools_context_string(
        self,
        max_chars: int = 1500,
        include_unavailable: bool = False,
    ) -> str:
        """Get compact context string for LLM prompts (Phase 7.1.3-05).

        Returns a minimal string representation of available tools
        suitable for LLM context.

        Args:
            max_chars: Maximum characters for output.
            include_unavailable: Include tools that aren't installed.

        Returns:
            Compact string like "Tools: slither(pip), aderyn(cargo), ..."

        Example:
            context = registry.get_tools_context_string(max_chars=500)
            prompt = f"Available {context}\\nAnalyze the code..."
        """
        from alphaswarm_sol.tools.description_compress import compress_for_context

        # Get tool info as dicts
        tool_infos: List[Dict[str, Any]] = []
        for name, info in self.TOOL_DEFINITIONS.items():
            # Skip unavailable unless requested
            if not include_unavailable:
                health = self.check_tool(name)
                if not health.installed or not health.healthy:
                    continue

            tool_dict = {
                "name": info.name,
                "install_method": info.install_method,
            }
            tool_infos.append(tool_dict)

        return compress_for_context(tool_infos, max_chars=max_chars)

    def summary(self) -> str:
        """Generate human-readable summary of tool status.

        Returns:
            Formatted summary string.
        """
        health = self.check_all_tools()
        lines = ["Tool Registry Status", "=" * 40]

        for tier in ToolTier:
            tier_name = ["Core (Tier 0)", "Recommended (Tier 1)", "Optional (Tier 2)"][
                tier
            ]
            lines.append(f"\n{tier_name}:")

            tools = self.get_tools_by_tier(tier)
            for name in tools:
                status = health[name]
                if status.healthy:
                    version = f" ({status.version})" if status.version else ""
                    lines.append(f"  [OK] {name}{version}")
                elif status.installed:
                    lines.append(f"  [!!] {name} (unhealthy: {status.error})")
                else:
                    lines.append(f"  [  ] {name} (not installed)")

        # Summary counts
        available = len([h for h in health.values() if h.healthy])
        total = len(health)
        lines.append(f"\nTotal: {available}/{total} tools available")

        return "\n".join(lines)


# Convenience function for quick checks
def check_all_tools() -> Dict[str, ToolHealth]:
    """Check health of all tools using default registry.

    Returns:
        Dict mapping tool name to health status.
    """
    return ToolRegistry().check_all_tools()


def get_available_tools() -> List[str]:
    """Get list of available tools using default registry.

    Returns:
        List of healthy tool names.
    """
    return ToolRegistry().get_available_tools()


def validate_tool_setup() -> bool:
    """Validate tool setup using default registry.

    Returns:
        True if core tools are available.
    """
    return ToolRegistry().validate_all_before_analysis()
