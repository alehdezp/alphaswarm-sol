"""
Tool Configuration Manager

Manages per-tool configurations with VKG-optimized defaults and project-level
overrides. Configuration priority: project (.vrs/tools.yaml) > VRS defaults.

Usage:
    # Get VKG defaults for a tool
    config = get_optimal_config("slither")

    # Load project-specific config
    config = load_tool_config("slither", Path("."))

    # Merge configs
    merged = merge_configs(base_config, override_config)
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

import structlog
import yaml

logger = structlog.get_logger(__name__)


@dataclass
class ToolConfig:
    """Configuration for a single tool.

    Attributes:
        tool: Tool name (slither, aderyn, etc.).
        enabled: Whether to run this tool.
        timeout: Execution timeout in seconds.
        exclude_paths: Paths to exclude from analysis.
        exclude_detectors: Tool-specific detector IDs to skip.
        extra_args: Additional command-line arguments.
        custom: Tool-specific options (varies by tool).
    """

    tool: str
    enabled: bool = True
    timeout: int = 120
    exclude_paths: List[str] = field(default_factory=list)
    exclude_detectors: List[str] = field(default_factory=list)
    extra_args: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool": self.tool,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "exclude_paths": self.exclude_paths,
            "exclude_detectors": self.exclude_detectors,
            "extra_args": self.extra_args,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], tool_name: str) -> "ToolConfig":
        """Create from dictionary.

        Args:
            data: Configuration dictionary.
            tool_name: Tool this config is for.

        Returns:
            ToolConfig instance.
        """
        return cls(
            tool=tool_name,
            enabled=data.get("enabled", True),
            timeout=data.get("timeout", 120),
            exclude_paths=data.get("exclude_paths", []),
            exclude_detectors=data.get("exclude_detectors", []),
            extra_args=data.get("extra_args", []),
            custom={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "enabled",
                    "timeout",
                    "exclude_paths",
                    "exclude_detectors",
                    "extra_args",
                }
            },
        )


# VKG-optimized default configurations for each tool
# These defaults filter noise and focus on security-relevant findings
VKG_OPTIMAL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "slither": {
        "timeout": 120,
        "exclude_paths": ["lib/", "node_modules/", "test/", "script/"],
        "exclude_detectors": [
            # Style/naming (not security relevant)
            "naming-convention",
            "solc-version",
            "pragma",
            "external-function",
            # Low value for security audits
            "similar-names",
            "too-many-digits",
            "constable-states",
            "immutable-states",
        ],
        "exclude_severity": ["informational", "low"],
    },
    "aderyn": {
        "timeout": 60,
        "exclude_paths": ["lib/", "node_modules/", "test/"],
        "exclude_detectors": [],
    },
    "mythril": {
        "timeout": 300,
        "exclude_paths": ["lib/", "node_modules/"],
        "execution_timeout": 600,
        "max_depth": 24,
        "strategy": "bfs",
    },
    "echidna": {
        "timeout": 600,
        "exclude_paths": [],
        "test_limit": 50000,
        "seq_len": 100,
        "corpus_dir": ".echidna_corpus",
        "shrink_limit": 5000,
    },
    "foundry": {
        "timeout": 180,
        "exclude_paths": [],
        "verbosity": 3,
        "fuzz_runs": 256,
        "invariant_runs": 256,
    },
    "semgrep": {
        "timeout": 120,
        "exclude_paths": ["lib/", "node_modules/", "test/"],
        "config": ["p/smart-contracts", "p/solidity"],
        "severity": ["ERROR", "WARNING"],
    },
    "halmos": {
        "timeout": 300,
        "exclude_paths": [],
        "solver_timeout_assertion": 1000,
        "solver_timeout_branching": 1000,
        "loop": 2,
        "width": 1024,
    },
    "medusa": {
        "timeout": 600,
        "exclude_paths": [],
        "test_limit": 0,
        "seq_len": 100,
        "workers": 4,
    },
    "solc": {
        "timeout": 60,
        "exclude_paths": [],
        "optimize": True,
        "optimize_runs": 200,
    },
    "crytic-compile": {
        "timeout": 120,
        "exclude_paths": [],
        "compile_force_framework": None,
    },
}


def get_optimal_config(tool: str) -> ToolConfig:
    """Get VKG-optimized default configuration for a tool.

    These defaults are tuned for security auditing:
    - Exclude noisy/low-value findings
    - Reasonable timeouts
    - Focus on protocol code (not libraries)

    Args:
        tool: Tool name.

    Returns:
        ToolConfig with VKG optimal settings.
    """
    defaults = VKG_OPTIMAL_CONFIGS.get(tool, {})
    return ToolConfig.from_dict(defaults, tool)


def load_tool_config(
    tool: str,
    project_path: Path,
    config_file: str = ".vrs/tools.yaml",
) -> ToolConfig:
    """Load tool configuration with project overrides.

    Priority:
    1. Project config (.vrs/tools.yaml)
    2. VRS optimal defaults

    Args:
        tool: Tool name.
        project_path: Project root directory.
        config_file: Relative path to config file.

    Returns:
        ToolConfig with merged settings.
    """
    # Start with VKG defaults
    base = get_optimal_config(tool)

    # Look for project config
    config_path = project_path / config_file
    if not config_path.exists():
        logger.debug(
            "no_project_config",
            tool=tool,
            path=str(config_path),
            using="vkg_defaults",
        )
        return base

    # Load project config
    try:
        with open(config_path) as f:
            all_configs = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        logger.warning(
            "config_load_error",
            path=str(config_path),
            error=str(e),
            using="vkg_defaults",
        )
        return base

    # Get tool-specific override
    tool_override = all_configs.get(tool)
    if not tool_override:
        logger.debug(
            "no_tool_override",
            tool=tool,
            path=str(config_path),
            using="vkg_defaults",
        )
        return base

    # Merge project override with base
    override = ToolConfig.from_dict(tool_override, tool)
    return merge_configs(base, override)


def load_all_tool_configs(
    project_path: Path,
    config_file: str = ".vrs/tools.yaml",
) -> Dict[str, ToolConfig]:
    """Load configurations for all known tools.

    Args:
        project_path: Project root directory.
        config_file: Relative path to config file.

    Returns:
        Dict mapping tool name to config.
    """
    configs = {}
    for tool in VKG_OPTIMAL_CONFIGS:
        configs[tool] = load_tool_config(tool, project_path, config_file)
    return configs


def merge_configs(base: ToolConfig, override: ToolConfig) -> ToolConfig:
    """Merge two configurations with override taking precedence.

    Lists are replaced (not appended).
    Dicts are merged (override keys win).

    Args:
        base: Base configuration.
        override: Override configuration.

    Returns:
        New merged ToolConfig.
    """
    # Start with base values
    merged_data = base.to_dict()

    # Override with non-default values from override
    override_data = override.to_dict()

    # Simple fields - override wins
    for key in ["enabled", "timeout"]:
        if key in override_data:
            merged_data[key] = override_data[key]

    # List fields - override replaces entirely if present
    for key in ["exclude_paths", "exclude_detectors", "extra_args"]:
        if override_data.get(key):
            merged_data[key] = override_data[key]

    # Custom dict - merge with override winning
    if override_data.get("custom"):
        merged_data["custom"] = {**base.custom, **override_data["custom"]}

    return ToolConfig.from_dict(merged_data, base.tool)


def save_project_config(
    configs: Dict[str, ToolConfig],
    project_path: Path,
    config_file: str = ".vrs/tools.yaml",
) -> Path:
    """Save tool configurations to project config file.

    Args:
        configs: Dict mapping tool name to config.
        project_path: Project root directory.
        config_file: Relative path to config file.

    Returns:
        Path to saved config file.
    """
    config_path = project_path / config_file

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to serializable format
    data = {}
    for name, config in configs.items():
        tool_data = config.to_dict()
        # Remove 'tool' key since it's the dict key
        del tool_data["tool"]
        data[name] = tool_data

    # Add header comment
    header = """# VKG Tool Configuration
# Override per-project or use VKG defaults
# See: uv run alphaswarm tools config --show-defaults

"""

    with open(config_path, "w") as f:
        f.write(header)
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    logger.info("config_saved", path=str(config_path))
    return config_path


def create_default_config_file(project_path: Path) -> Path:
    """Create a tools.yaml with VKG defaults commented out.

    This provides a template for users to customize.

    Args:
        project_path: Project root directory.

    Returns:
        Path to created config file.
    """
    config_path = project_path / ".vrs" / "tools.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    content = '''# VKG Tool Configuration
# Override per-project or use defaults
# Run: uv run alphaswarm tools config --show-defaults

slither:
  timeout: 120
  exclude_paths: ["lib/", "node_modules/", "test/", "script/"]
  exclude_detectors:
    - naming-convention
    - solc-version
    - pragma
    - external-function
  exclude_severity: [informational, low]

aderyn:
  timeout: 60
  exclude_paths: ["lib/", "node_modules/", "test/"]

mythril:
  timeout: 300
  execution_timeout: 600
  max_depth: 24
  exclude_paths: ["lib/", "node_modules/"]

echidna:
  timeout: 600
  test_limit: 50000
  seq_len: 100

foundry:
  timeout: 180
  verbosity: 3

semgrep:
  timeout: 120
  config: ["p/smart-contracts", "p/solidity"]

halmos:
  timeout: 300
  solver_timeout_assertion: 1000
'''

    with open(config_path, "w") as f:
        f.write(content)

    logger.info("default_config_created", path=str(config_path))
    return config_path


def get_tool_command_args(config: ToolConfig) -> List[str]:
    """Generate command-line arguments from config.

    This is a helper to translate config to CLI args.
    Tool-specific logic should be in tool adapters.

    Args:
        config: Tool configuration.

    Returns:
        List of command-line arguments.
    """
    args = []

    # Add extra args first (user-specified)
    args.extend(config.extra_args)

    return args


def validate_config(config: ToolConfig) -> List[str]:
    """Validate a tool configuration.

    Args:
        config: Configuration to validate.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors = []

    if config.timeout < 1:
        errors.append(f"Timeout must be positive, got {config.timeout}")

    if config.timeout > 3600:
        errors.append(f"Timeout too large ({config.timeout}s), max is 3600s")

    # Check for invalid exclude patterns
    for path in config.exclude_paths:
        if ".." in path:
            errors.append(f"Invalid exclude path (no ..): {path}")

    return errors


class ConfigManager:
    """Manager for tool configurations.

    Provides a unified interface for loading, caching, and validating
    tool configurations across a project.
    """

    DEFAULT_CONFIG_FILE: ClassVar[str] = ".vrs/tools.yaml"

    def __init__(self, project_path: Path):
        """Initialize config manager.

        Args:
            project_path: Root directory of the project.
        """
        self.project_path = project_path
        self._cache: Dict[str, ToolConfig] = {}

    def get(self, tool: str, force_reload: bool = False) -> ToolConfig:
        """Get configuration for a tool.

        Args:
            tool: Tool name.
            force_reload: Skip cache and reload from disk.

        Returns:
            ToolConfig for the tool.
        """
        if not force_reload and tool in self._cache:
            return self._cache[tool]

        config = load_tool_config(tool, self.project_path)
        self._cache[tool] = config
        return config

    def get_all(self, force_reload: bool = False) -> Dict[str, ToolConfig]:
        """Get configurations for all tools.

        Args:
            force_reload: Skip cache and reload from disk.

        Returns:
            Dict mapping tool name to config.
        """
        if force_reload:
            self._cache.clear()

        for tool in VKG_OPTIMAL_CONFIGS:
            if tool not in self._cache:
                self._cache[tool] = load_tool_config(tool, self.project_path)

        return dict(self._cache)

    def save(self, configs: Optional[Dict[str, ToolConfig]] = None) -> Path:
        """Save configurations to project config file.

        Args:
            configs: Configs to save (uses cache if None).

        Returns:
            Path to saved config file.
        """
        to_save = configs or self._cache
        return save_project_config(to_save, self.project_path)

    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all cached configurations.

        Returns:
            Dict mapping tool name to list of errors (empty if valid).
        """
        errors = {}
        for tool, config in self._cache.items():
            tool_errors = validate_config(config)
            if tool_errors:
                errors[tool] = tool_errors
        return errors

    def config_file_exists(self) -> bool:
        """Check if project config file exists.

        Returns:
            True if .vrs/tools.yaml exists.
        """
        return (self.project_path / self.DEFAULT_CONFIG_FILE).exists()

    def create_config_file(self) -> Path:
        """Create default config file if not exists.

        Returns:
            Path to config file.
        """
        return create_default_config_file(self.project_path)
