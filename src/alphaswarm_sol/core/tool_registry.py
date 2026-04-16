"""
Tool Registry

Extended tool detection with version parsing and health checks.
Provides detailed information about external tools used by VKG.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import subprocess
import shutil
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """
    Information about a detected tool.

    Attributes:
        name: Tool identifier
        available: Whether the tool is available
        version: Detected version string
        path: Path to the tool binary
        health: Health status (ok, degraded, error, unknown)
        details: Additional details or error information
    """

    name: str
    available: bool
    version: Optional[str] = None
    path: Optional[str] = None
    health: str = "unknown"
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "available": self.available,
            "version": self.version,
            "path": self.path,
            "health": self.health,
            "details": self.details,
        }


class ToolRegistry:
    """
    Registry for external tool detection.

    Provides version detection, health checks, and tool enumeration
    for all tools used by VKG.
    """

    # Version extraction patterns for different tools
    VERSION_PATTERNS = {
        "slither": r"(\d+\.\d+\.\d+)",
        "aderyn": r"(\d+\.\d+\.\d+)",
        "forge": r"(\d+\.\d+\.\d+)",
        "medusa": r"(\d+\.\d+\.\d+)",
        "solc": r"(\d+\.\d+\.\d+)",
        "python": r"Python (\d+\.\d+\.\d+)",
        "solc-select": r"solc-select (\d+\.\d+\.\d+)",
    }

    def __init__(self, timeout: int = 10):
        """
        Initialize tool registry.

        Args:
            timeout: Timeout for tool detection commands (seconds)
        """
        self.timeout = timeout
        self._cache: Dict[str, ToolInfo] = {}

    def detect_tool(
        self,
        name: str,
        check_cmd: str,
        force: bool = False,
    ) -> ToolInfo:
        """
        Detect a tool and gather information.

        Args:
            name: Tool name identifier
            check_cmd: Command to run for version check
            force: If True, bypass cache

        Returns:
            ToolInfo with detection results
        """
        # Check cache
        if not force and name in self._cache:
            return self._cache[name]

        try:
            # First check if binary exists
            cmd_parts = check_cmd.split()
            binary = cmd_parts[0]

            path = shutil.which(binary)
            if not path:
                info = ToolInfo(
                    name=name,
                    available=False,
                    health="error",
                    details={"error": "Binary not found in PATH"},
                )
                self._cache[name] = info
                return info

            # Run version command
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                timeout=self.timeout,
                text=True,
            )

            if result.returncode != 0:
                info = ToolInfo(
                    name=name,
                    available=False,
                    path=path,
                    health="error",
                    details={
                        "error": "Command failed",
                        "returncode": result.returncode,
                        "stderr": result.stderr[:500] if result.stderr else None,
                    },
                )
                self._cache[name] = info
                return info

            # Extract version
            output = result.stdout + result.stderr
            version = self._extract_version(name, output)

            info = ToolInfo(
                name=name,
                available=True,
                version=version,
                path=path,
                health="ok",
            )
            self._cache[name] = info
            return info

        except subprocess.TimeoutExpired:
            info = ToolInfo(
                name=name,
                available=False,
                health="error",
                details={"error": "Command timed out"},
            )
            self._cache[name] = info
            return info

        except FileNotFoundError:
            info = ToolInfo(
                name=name,
                available=False,
                health="error",
                details={"error": "Command not found"},
            )
            self._cache[name] = info
            return info

        except Exception as e:
            logger.warning(f"Tool detection failed for {name}: {e}")
            info = ToolInfo(
                name=name,
                available=False,
                health="error",
                details={"error": str(e)},
            )
            self._cache[name] = info
            return info

    def _extract_version(self, name: str, output: str) -> Optional[str]:
        """
        Extract version string from command output.

        Args:
            name: Tool name (used for pattern lookup)
            output: Combined stdout/stderr output

        Returns:
            Version string or None if not found
        """
        # Use tool-specific pattern if available
        pattern = self.VERSION_PATTERNS.get(name, r"(\d+\.\d+\.\d+)")

        match = re.search(pattern, output)
        if match:
            return match.group(1)

        # Fallback: try generic version pattern
        fallback_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", output)
        if fallback_match:
            return fallback_match.group(1)

        return None

    def detect_all(self, force: bool = False) -> Dict[str, ToolInfo]:
        """
        Detect all registered tools.

        Args:
            force: If True, bypass cache

        Returns:
            Dict mapping tool names to ToolInfo
        """
        from alphaswarm_sol.core.tiers import DEPENDENCIES

        results = {}

        for name, dep in DEPENDENCIES.items():
            if dep.check_cmd:
                results[name] = self.detect_tool(name, dep.check_cmd, force=force)
            elif dep.check_fn:
                # Custom check function
                try:
                    available = dep.check_fn()
                    results[name] = ToolInfo(
                        name=name,
                        available=available,
                        health="ok" if available else "unknown",
                    )
                except Exception as e:
                    results[name] = ToolInfo(
                        name=name,
                        available=False,
                        health="error",
                        details={"error": str(e)},
                    )
            else:
                # No check available = assume available
                results[name] = ToolInfo(name=name, available=True, health="ok")

        return results

    def get_healthy_tools(self) -> List[str]:
        """Get list of healthy tool names."""
        results = self.detect_all()
        return [name for name, info in results.items() if info.health == "ok"]

    def get_missing_tools(self) -> List[str]:
        """Get list of unavailable tools."""
        results = self.detect_all()
        return [name for name, info in results.items() if not info.available]

    def clear_cache(self) -> None:
        """Clear detection cache."""
        self._cache.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert all results to dictionary."""
        results = self.detect_all()
        return {name: info.to_dict() for name, info in results.items()}


# Convenience functions

_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def detect_tool(name: str, check_cmd: str) -> ToolInfo:
    """Detect a single tool."""
    return get_registry().detect_tool(name, check_cmd)


def detect_all_tools(force: bool = False) -> Dict[str, ToolInfo]:
    """Detect all registered tools."""
    return get_registry().detect_all(force=force)
