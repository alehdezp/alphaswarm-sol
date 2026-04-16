"""Phase 20: Configuration Profiles.

This module provides configuration profiles for different analysis modes
(fast, standard, thorough) to balance speed and coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProfileLevel(str, Enum):
    """Analysis profile levels."""
    FAST = "fast"           # Quick scan, minimal depth
    STANDARD = "standard"   # Balanced analysis
    THOROUGH = "thorough"   # Deep analysis, all checks
    CUSTOM = "custom"       # User-defined


@dataclass
class PatternConfig:
    """Configuration for pattern matching.

    Attributes:
        enabled_categories: Which pattern categories to run
        max_patterns_per_category: Limit patterns per category
        tier_b_enabled: Whether to run Tier B (semantic) checks
        voting_threshold: Threshold for voting aggregation
    """
    enabled_categories: List[str] = field(default_factory=lambda: ["all"])
    max_patterns_per_category: int = 100
    tier_b_enabled: bool = True
    voting_threshold: int = 2


@dataclass
class AnalysisConfig:
    """Configuration for analysis depth.

    Attributes:
        max_path_depth: Maximum depth for path analysis
        max_functions: Maximum functions to analyze per contract
        enable_temporal: Whether to enable temporal analysis
        enable_supply_chain: Whether to enable supply chain analysis
        enable_attack_synthesis: Whether to synthesize attack paths
    """
    max_path_depth: int = 5
    max_functions: int = 100
    enable_temporal: bool = True
    enable_supply_chain: bool = True
    enable_attack_synthesis: bool = True


@dataclass
class PerformanceConfig:
    """Configuration for performance.

    Attributes:
        parallel_workers: Number of parallel workers
        use_cache: Whether to use caching
        incremental_build: Whether to use incremental builds
        batch_size: Batch size for operations
    """
    parallel_workers: int = 4
    use_cache: bool = True
    incremental_build: bool = True
    batch_size: int = 10


@dataclass
class OutputConfig:
    """Configuration for output.

    Attributes:
        verbose: Verbose output
        compact: Compact output format
        show_evidence: Include evidence in findings
        max_findings: Maximum findings to report
    """
    verbose: bool = False
    compact: bool = False
    show_evidence: bool = True
    max_findings: int = 100


@dataclass
class ConfigProfile:
    """Complete configuration profile.

    Attributes:
        name: Profile name
        level: Profile level
        description: Profile description
        patterns: Pattern configuration
        analysis: Analysis configuration
        performance: Performance configuration
        output: Output configuration
    """
    name: str
    level: ProfileLevel
    description: str = ""
    patterns: PatternConfig = field(default_factory=PatternConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "level": self.level.value,
            "description": self.description,
            "patterns": {
                "enabled_categories": self.patterns.enabled_categories,
                "max_patterns_per_category": self.patterns.max_patterns_per_category,
                "tier_b_enabled": self.patterns.tier_b_enabled,
                "voting_threshold": self.patterns.voting_threshold,
            },
            "analysis": {
                "max_path_depth": self.analysis.max_path_depth,
                "max_functions": self.analysis.max_functions,
                "enable_temporal": self.analysis.enable_temporal,
                "enable_supply_chain": self.analysis.enable_supply_chain,
                "enable_attack_synthesis": self.analysis.enable_attack_synthesis,
            },
            "performance": {
                "parallel_workers": self.performance.parallel_workers,
                "use_cache": self.performance.use_cache,
                "incremental_build": self.performance.incremental_build,
                "batch_size": self.performance.batch_size,
            },
            "output": {
                "verbose": self.output.verbose,
                "compact": self.output.compact,
                "show_evidence": self.output.show_evidence,
                "max_findings": self.output.max_findings,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigProfile":
        """Create from dictionary."""
        patterns_data = data.get("patterns", {})
        analysis_data = data.get("analysis", {})
        performance_data = data.get("performance", {})
        output_data = data.get("output", {})

        return cls(
            name=data.get("name", "custom"),
            level=ProfileLevel(data.get("level", "standard")),
            description=data.get("description", ""),
            patterns=PatternConfig(
                enabled_categories=patterns_data.get("enabled_categories", ["all"]),
                max_patterns_per_category=patterns_data.get("max_patterns_per_category", 100),
                tier_b_enabled=patterns_data.get("tier_b_enabled", True),
                voting_threshold=patterns_data.get("voting_threshold", 2),
            ),
            analysis=AnalysisConfig(
                max_path_depth=analysis_data.get("max_path_depth", 5),
                max_functions=analysis_data.get("max_functions", 100),
                enable_temporal=analysis_data.get("enable_temporal", True),
                enable_supply_chain=analysis_data.get("enable_supply_chain", True),
                enable_attack_synthesis=analysis_data.get("enable_attack_synthesis", True),
            ),
            performance=PerformanceConfig(
                parallel_workers=performance_data.get("parallel_workers", 4),
                use_cache=performance_data.get("use_cache", True),
                incremental_build=performance_data.get("incremental_build", True),
                batch_size=performance_data.get("batch_size", 10),
            ),
            output=OutputConfig(
                verbose=output_data.get("verbose", False),
                compact=output_data.get("compact", False),
                show_evidence=output_data.get("show_evidence", True),
                max_findings=output_data.get("max_findings", 100),
            ),
        )


# Pre-defined profiles
FAST_PROFILE = ConfigProfile(
    name="fast",
    level=ProfileLevel.FAST,
    description="Quick scan for critical vulnerabilities only",
    patterns=PatternConfig(
        enabled_categories=["critical", "high"],
        max_patterns_per_category=20,
        tier_b_enabled=False,
    ),
    analysis=AnalysisConfig(
        max_path_depth=2,
        max_functions=50,
        enable_temporal=False,
        enable_supply_chain=False,
        enable_attack_synthesis=False,
    ),
    performance=PerformanceConfig(
        parallel_workers=8,
        use_cache=True,
        incremental_build=True,
        batch_size=20,
    ),
    output=OutputConfig(
        compact=True,
        show_evidence=False,
        max_findings=20,
    ),
)

STANDARD_PROFILE = ConfigProfile(
    name="standard",
    level=ProfileLevel.STANDARD,
    description="Balanced analysis with good coverage",
    patterns=PatternConfig(
        enabled_categories=["all"],
        max_patterns_per_category=50,
        tier_b_enabled=True,
    ),
    analysis=AnalysisConfig(
        max_path_depth=4,
        max_functions=100,
        enable_temporal=True,
        enable_supply_chain=True,
        enable_attack_synthesis=True,
    ),
    performance=PerformanceConfig(
        parallel_workers=4,
        use_cache=True,
        incremental_build=True,
        batch_size=10,
    ),
    output=OutputConfig(
        show_evidence=True,
        max_findings=50,
    ),
)

THOROUGH_PROFILE = ConfigProfile(
    name="thorough",
    level=ProfileLevel.THOROUGH,
    description="Deep analysis with maximum coverage",
    patterns=PatternConfig(
        enabled_categories=["all"],
        max_patterns_per_category=100,
        tier_b_enabled=True,
        voting_threshold=3,
    ),
    analysis=AnalysisConfig(
        max_path_depth=6,
        max_functions=200,
        enable_temporal=True,
        enable_supply_chain=True,
        enable_attack_synthesis=True,
    ),
    performance=PerformanceConfig(
        parallel_workers=2,
        use_cache=True,
        incremental_build=False,  # Full rebuild for thorough
        batch_size=5,
    ),
    output=OutputConfig(
        verbose=True,
        show_evidence=True,
        max_findings=200,
    ),
)


class ProfileManager:
    """Manages configuration profiles.

    Provides access to built-in profiles and custom profile loading.
    """

    def __init__(self):
        """Initialize profile manager."""
        self._profiles: Dict[str, ConfigProfile] = {
            "fast": FAST_PROFILE,
            "standard": STANDARD_PROFILE,
            "thorough": THOROUGH_PROFILE,
        }
        self._active_profile: ConfigProfile = STANDARD_PROFILE

    def get_profile(self, name: str) -> Optional[ConfigProfile]:
        """Get profile by name.

        Args:
            name: Profile name

        Returns:
            ConfigProfile or None
        """
        return self._profiles.get(name)

    def set_active_profile(self, name: str) -> bool:
        """Set the active profile.

        Args:
            name: Profile name

        Returns:
            True if profile was set
        """
        profile = self._profiles.get(name)
        if profile:
            self._active_profile = profile
            return True
        return False

    @property
    def active_profile(self) -> ConfigProfile:
        """Get the active profile."""
        return self._active_profile

    def register_profile(self, profile: ConfigProfile) -> None:
        """Register a custom profile.

        Args:
            profile: Profile to register
        """
        self._profiles[profile.name] = profile

    def list_profiles(self) -> List[str]:
        """List available profile names.

        Returns:
            List of profile names
        """
        return list(self._profiles.keys())

    def load_from_file(self, path: str) -> Optional[ConfigProfile]:
        """Load profile from file.

        Args:
            path: Path to profile file (JSON or YAML)

        Returns:
            Loaded profile or None
        """
        import json
        from pathlib import Path

        filepath = Path(path)
        if not filepath.exists():
            return None

        try:
            with open(filepath) as f:
                if filepath.suffix in [".yaml", ".yml"]:
                    import yaml
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            profile = ConfigProfile.from_dict(data)
            self._profiles[profile.name] = profile
            return profile
        except Exception:
            return None


def get_profile(name: str) -> Optional[ConfigProfile]:
    """Get a configuration profile by name.

    Convenience function for quick profile access.

    Args:
        name: Profile name (fast, standard, thorough)

    Returns:
        ConfigProfile or None
    """
    profiles = {
        "fast": FAST_PROFILE,
        "standard": STANDARD_PROFILE,
        "thorough": THOROUGH_PROFILE,
    }
    return profiles.get(name)


__all__ = [
    "ProfileLevel",
    "PatternConfig",
    "AnalysisConfig",
    "PerformanceConfig",
    "OutputConfig",
    "ConfigProfile",
    "ProfileManager",
    "get_profile",
    "FAST_PROFILE",
    "STANDARD_PROFILE",
    "THOROUGH_PROFILE",
]
