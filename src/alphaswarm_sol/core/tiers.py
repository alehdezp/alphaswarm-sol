"""
Dependency Tier System

Defines VKG's dependency hierarchy for graceful degradation.

Tier System:
- TIER 0 (CORE): Must always work - Python, Slither, Pattern Engine
- TIER 1 (ENHANCEMENT): Adds value but not required - Aderyn, LLM, Foundry
- TIER 2 (OPTIONAL): Nice-to-have features - MCP, Telemetry, Learning
"""

from enum import IntEnum
from dataclasses import dataclass, field
from typing import Set, Optional, Dict, List, Callable
import subprocess
import shutil
import os


class Tier(IntEnum):
    """
    Dependency tiers. Lower = more critical.

    CORE (0): VKG fails without these
    ENHANCEMENT (1): Adds capabilities, VKG continues without
    OPTIONAL (2): Nice-to-have features
    """

    CORE = 0
    ENHANCEMENT = 1
    OPTIONAL = 2


@dataclass
class Dependency:
    """
    A VKG dependency with tier classification and availability checking.

    Attributes:
        name: Unique identifier for the dependency
        tier: Criticality tier (CORE, ENHANCEMENT, OPTIONAL)
        description: Human-readable description
        check_cmd: Shell command to verify availability (e.g., "slither --version")
        check_fn: Alternative Python function for checking availability
        install_hint: User-friendly installation instructions
        env_var: Environment variable that indicates availability
    """

    name: str
    tier: Tier
    description: str
    check_cmd: Optional[str] = None
    check_fn: Optional[Callable[[], bool]] = None
    install_hint: Optional[str] = None
    env_var: Optional[str] = None
    _version_cache: Optional[str] = field(default=None, repr=False)

    def is_available(self) -> bool:
        """
        Check if dependency is available.

        Checks in order:
        1. Environment variable (if specified)
        2. Custom check function (if specified)
        3. Shell command (if specified)
        4. Returns True if no checks specified (assume available)
        """
        # Check environment variable
        if self.env_var:
            return bool(os.environ.get(self.env_var))

        # Check custom function
        if self.check_fn:
            try:
                return self.check_fn()
            except Exception:
                return False

        # Check shell command
        if self.check_cmd:
            return self._check_command()

        # No check specified, assume available
        return True

    def _check_command(self) -> bool:
        """Run shell command to check availability."""
        if not self.check_cmd:
            return True

        try:
            # First check if the binary exists
            cmd_parts = self.check_cmd.split()
            binary = cmd_parts[0]

            # Check if it's in PATH
            if not shutil.which(binary):
                return False

            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                timeout=10,
                text=True,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def get_version(self) -> Optional[str]:
        """
        Get dependency version if available.

        Returns first line of version command output.
        """
        if self._version_cache is not None:
            return self._version_cache

        if not self.check_cmd:
            return None

        try:
            result = subprocess.run(
                self.check_cmd.split(),
                capture_output=True,
                timeout=10,
                text=True,
            )
            if result.returncode == 0:
                output = result.stdout.strip() or result.stderr.strip()
                self._version_cache = output.split("\n")[0]
                return self._version_cache
        except Exception:
            pass

        return None

    def get_install_instructions(self) -> str:
        """Get installation instructions."""
        if self.install_hint:
            return self.install_hint
        return f"Install {self.name} to enable this feature"


# -----------------------------------------------------------------------------
# Dependency Registry
# -----------------------------------------------------------------------------


def _check_python_available() -> bool:
    """Python is always available if we're running."""
    return True


def _check_llm_available() -> bool:
    """Check if any LLM API key is available."""
    providers = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "DEEPSEEK_API_KEY",
        "OPENROUTER_API_KEY",
    ]
    return any(os.environ.get(key) for key in providers)


DEPENDENCIES: Dict[str, Dependency] = {
    # -------------------------------------------------------------------------
    # TIER 0: Core (Must Work)
    # -------------------------------------------------------------------------
    "python": Dependency(
        name="python",
        tier=Tier.CORE,
        description="Python runtime",
        check_fn=_check_python_available,
    ),
    "slither": Dependency(
        name="slither",
        tier=Tier.CORE,
        description="Solidity static analyzer (Slither)",
        check_cmd="slither --version",
        install_hint="pip install slither-analyzer",
    ),
    "pattern_engine": Dependency(
        name="pattern_engine",
        tier=Tier.CORE,
        description="VKG pattern matching engine",
        check_fn=lambda: True,  # Always available if VKG is installed
    ),
    # -------------------------------------------------------------------------
    # TIER 1: Enhancement (Adds Value)
    # -------------------------------------------------------------------------
    "aderyn": Dependency(
        name="aderyn",
        tier=Tier.ENHANCEMENT,
        description="Rust-based Solidity analyzer",
        check_cmd="aderyn --version",
        install_hint="cargo install aderyn",
    ),
    "foundry": Dependency(
        name="foundry",
        tier=Tier.ENHANCEMENT,
        description="Ethereum development toolkit (Foundry)",
        check_cmd="forge --version",
        install_hint="curl -L https://foundry.paradigm.xyz | bash && foundryup",
    ),
    "medusa": Dependency(
        name="medusa",
        tier=Tier.ENHANCEMENT,
        description="Smart contract fuzzer",
        check_cmd="medusa --version",
        install_hint="See https://github.com/crytic/medusa",
    ),
    "llm_provider": Dependency(
        name="llm_provider",
        tier=Tier.ENHANCEMENT,
        description="LLM API access (Tier B analysis)",
        check_fn=_check_llm_available,
        install_hint="Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or another LLM provider key",
    ),
    "solc_select": Dependency(
        name="solc_select",
        tier=Tier.ENHANCEMENT,
        description="Solidity compiler version manager",
        check_cmd="solc-select --version",
        install_hint="pip install solc-select",
    ),
    # -------------------------------------------------------------------------
    # TIER 2: Optional (Nice-to-Have)
    # -------------------------------------------------------------------------
    "mcp": Dependency(
        name="mcp",
        tier=Tier.OPTIONAL,
        description="Model Context Protocol support",
        check_fn=lambda: False,  # Not yet implemented
    ),
    "telemetry": Dependency(
        name="telemetry",
        tier=Tier.OPTIONAL,
        description="Usage telemetry collection",
        check_fn=lambda: True,  # Always available
    ),
    "learning": Dependency(
        name="learning",
        tier=Tier.OPTIONAL,
        description="Pattern learning system",
        check_fn=lambda: True,  # Always available
    ),
}


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------


def get_tier_dependencies(tier: Tier) -> List[Dependency]:
    """Get all dependencies for a specific tier."""
    return [d for d in DEPENDENCIES.values() if d.tier == tier]


def get_available_tiers() -> Set[Tier]:
    """
    Get set of tiers that are fully available.

    A tier is available if ALL of its CORE dependencies are available
    (for CORE tier) or if the tier would provide value (for higher tiers).
    """
    available = set()

    for tier in Tier:
        tier_deps = get_tier_dependencies(tier)

        # For CORE tier, all must be available
        if tier == Tier.CORE:
            if all(d.is_available() for d in tier_deps):
                available.add(tier)
        else:
            # For other tiers, tier is "available" if any dependency works
            if any(d.is_available() for d in tier_deps):
                available.add(tier)

    return available


def get_degradation_message(missing_tier: Tier) -> str:
    """
    Get user-friendly message for degraded operation.

    Args:
        missing_tier: The tier that is unavailable

    Returns:
        Human-readable message explaining the degradation
    """
    messages = {
        Tier.CORE: (
            "CRITICAL: Core dependencies missing. VKG cannot run.\n"
            "Run 'vkg doctor' to diagnose and fix issues."
        ),
        Tier.ENHANCEMENT: (
            "Running with core features only. Enhanced analysis unavailable.\n"
            "Missing: LLM analysis, external tools (Aderyn, Medusa).\n"
            "Run 'vkg tools status' for details."
        ),
        Tier.OPTIONAL: (
            "Running without optional features (telemetry, learning).\n"
            "Core analysis is fully functional."
        ),
    }
    return messages.get(missing_tier, "Unknown degradation level")


def get_missing_dependencies(tier: Tier) -> List[Dependency]:
    """Get list of missing dependencies for a tier."""
    tier_deps = get_tier_dependencies(tier)
    return [d for d in tier_deps if not d.is_available()]


def format_dependency_status(dep: Dependency) -> str:
    """Format dependency status for display."""
    available = dep.is_available()
    status = "[OK]" if available else "[MISSING]"
    version = dep.get_version() if available else None
    version_str = f" ({version})" if version else ""

    line = f"  {status} {dep.name}: {dep.description}{version_str}"

    if not available and dep.install_hint:
        line += f"\n         Install: {dep.install_hint}"

    return line
