"""
Project Structure Detection (Task 4.2)

Detects Solidity project types (Foundry, Hardhat, Brownie, Unknown)
and extracts their configuration for test scaffold generation.

Philosophy:
- Detect project type reliably to generate appropriate test format
- Extract remappings for import resolution
- Fail gracefully to UNKNOWN if detection fails
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# Python 3.11+ has tomllib built-in
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore


class ProjectType(Enum):
    """
    Detected project type.

    Used to determine:
    - Test file format (Foundry .t.sol vs Hardhat .js/.ts)
    - Import resolution strategy
    - Test directory location
    """

    FOUNDRY = "foundry"    # Uses foundry.toml, lib/, forge-std
    HARDHAT = "hardhat"    # Uses hardhat.config.*, node_modules
    BROWNIE = "brownie"    # Uses brownie-config.yaml
    UNKNOWN = "unknown"    # Fallback for unrecognized projects


@dataclass
class ProjectConfig:
    """
    Detected project configuration.

    Contains all information needed to generate appropriate test scaffolds.

    Attributes:
        project_type: Detected project type
        root: Project root directory
        src_dir: Source directory (src/ or contracts/)
        test_dir: Test directory (test/ or tests/)
        remappings: Import remappings (prefix -> replacement)
        solc_version: Detected Solidity compiler version
        dependencies: List of detected dependencies
        config_file: Path to the config file that was detected
    """

    project_type: ProjectType
    root: Path
    src_dir: Path  # Usually src/ or contracts/
    test_dir: Path  # Usually test/ or tests/
    remappings: Dict[str, str] = field(default_factory=dict)
    solc_version: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    config_file: Optional[Path] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "project_type": self.project_type.value,
            "root": str(self.root),
            "src_dir": str(self.src_dir),
            "test_dir": str(self.test_dir),
            "remappings": self.remappings,
            "solc_version": self.solc_version,
            "dependencies": self.dependencies,
            "config_file": str(self.config_file) if self.config_file else None,
        }


def detect_project_structure(root: Path | str) -> ProjectConfig:
    """
    Detect project type and configuration.

    Priority order:
    1. foundry.toml -> FOUNDRY
    2. hardhat.config.* -> HARDHAT
    3. brownie-config.yaml -> BROWNIE
    4. package.json with hardhat dep -> HARDHAT
    5. UNKNOWN (fallback with best-effort defaults)

    Args:
        root: Project root directory

    Returns:
        ProjectConfig with detected settings
    """
    root = Path(root).resolve()

    # 1. Check for Foundry (highest priority - most specific)
    foundry_toml = root / "foundry.toml"
    if foundry_toml.exists():
        return _parse_foundry_config(root, foundry_toml)

    # 2. Check for Hardhat config files
    for config_name in ["hardhat.config.js", "hardhat.config.ts"]:
        config_path = root / config_name
        if config_path.exists():
            return _parse_hardhat_config(root, config_path)

    # 3. Check for Brownie
    brownie_config = root / "brownie-config.yaml"
    if brownie_config.exists():
        return _parse_brownie_config(root, brownie_config)

    # 4. Check package.json for hardhat dependency
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            all_deps = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
            }
            if "hardhat" in all_deps:
                return _parse_hardhat_config(root, pkg_json)
        except (json.JSONDecodeError, OSError):
            pass

    # 5. Unknown project - return best-effort defaults
    return _unknown_project(root)


def _parse_foundry_config(root: Path, config_path: Path) -> ProjectConfig:
    """
    Parse Foundry project configuration.

    Extracts:
    - Remappings from foundry.toml and remappings.txt
    - Source and test directories
    - Solidity compiler version
    - Dependencies from lib/
    """
    remappings: Dict[str, str] = {}
    src_dir = root / "src"
    test_dir = root / "test"
    solc_version: Optional[str] = None

    # Parse foundry.toml if tomllib is available
    if tomllib is not None:
        try:
            config = tomllib.loads(config_path.read_text())
            profile = config.get("profile", {}).get("default", {})

            # Get remappings from foundry.toml
            raw_remappings = profile.get("remappings", [])
            for mapping in raw_remappings:
                if "=" in mapping:
                    prefix, target = mapping.split("=", 1)
                    remappings[prefix] = target

            # Get source and test directories
            src_name = profile.get("src", "src")
            test_name = profile.get("test", "test")
            src_dir = root / src_name
            test_dir = root / test_name

            # Get solc version
            solc_version = profile.get("solc_version") or profile.get("solc")

        except Exception:
            # Fall back to defaults on parse error
            pass

    # Also check remappings.txt (can supplement foundry.toml)
    remappings_txt = root / "remappings.txt"
    if remappings_txt.exists():
        try:
            for line in remappings_txt.read_text().splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    prefix, target = line.split("=", 1)
                    # remappings.txt entries take precedence
                    remappings[prefix] = target
        except OSError:
            pass

    # Detect dependencies from lib/
    dependencies: List[str] = []
    lib_dir = root / "lib"
    if lib_dir.exists():
        try:
            dependencies = [d.name for d in lib_dir.iterdir() if d.is_dir()]
        except OSError:
            pass

    # Ensure directories exist, fallback to alternatives
    if not src_dir.exists():
        for alt in ["contracts", "."]:
            alt_dir = root / alt
            if alt_dir.exists():
                src_dir = alt_dir
                break

    if not test_dir.exists():
        for alt in ["tests"]:
            alt_dir = root / alt
            if alt_dir.exists():
                test_dir = alt_dir
                break

    return ProjectConfig(
        project_type=ProjectType.FOUNDRY,
        root=root,
        src_dir=src_dir,
        test_dir=test_dir,
        remappings=remappings,
        solc_version=solc_version,
        dependencies=dependencies,
        config_file=config_path,
    )


def _parse_hardhat_config(root: Path, config_path: Path) -> ProjectConfig:
    """
    Parse Hardhat project configuration.

    Hardhat uses node_modules for imports and typically has:
    - contracts/ directory
    - test/ directory
    """
    # Standard Hardhat remappings
    remappings = {
        "@openzeppelin/": "node_modules/@openzeppelin/",
        "@chainlink/": "node_modules/@chainlink/",
    }

    # Standard directories
    contracts_dir = root / "contracts"
    if not contracts_dir.exists():
        contracts_dir = root / "src"

    test_dir = root / "test"
    if not test_dir.exists():
        test_dir = root / "tests"

    # Try to detect dependencies from package.json
    dependencies: List[str] = []
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            all_deps = {
                **pkg.get("dependencies", {}),
                **pkg.get("devDependencies", {}),
            }
            # Look for common Solidity-related packages
            sol_prefixes = ["@openzeppelin", "@chainlink", "hardhat", "ethers"]
            dependencies = [
                name for name in all_deps
                if any(name.startswith(p) for p in sol_prefixes)
            ]
        except (json.JSONDecodeError, OSError):
            pass

    return ProjectConfig(
        project_type=ProjectType.HARDHAT,
        root=root,
        src_dir=contracts_dir,
        test_dir=test_dir,
        remappings=remappings,
        solc_version=None,  # Hardhat manages this via config
        dependencies=dependencies,
        config_file=config_path,
    )


def _parse_brownie_config(root: Path, config_path: Path) -> ProjectConfig:
    """
    Parse Brownie project configuration.

    Brownie uses a different structure:
    - contracts/ for source
    - tests/ for tests
    """
    return ProjectConfig(
        project_type=ProjectType.BROWNIE,
        root=root,
        src_dir=root / "contracts",
        test_dir=root / "tests",
        remappings={},
        solc_version=None,
        dependencies=[],
        config_file=config_path,
    )


def _unknown_project(root: Path) -> ProjectConfig:
    """
    Return best-effort config for unknown project type.

    Tries common directory names and returns sensible defaults.
    """
    # Try to find source directory
    src_dir = root
    for candidate in ["src", "contracts"]:
        candidate_dir = root / candidate
        if candidate_dir.exists():
            src_dir = candidate_dir
            break

    # Try to find test directory
    test_dir = root / "test"
    if not test_dir.exists():
        test_dir = root / "tests"
    if not test_dir.exists():
        test_dir = root / "test"  # Use this as default even if doesn't exist

    return ProjectConfig(
        project_type=ProjectType.UNKNOWN,
        root=root,
        src_dir=src_dir,
        test_dir=test_dir,
        remappings={},
        solc_version=None,
        dependencies=[],
        config_file=None,
    )


def is_foundry_project(root: Path | str) -> bool:
    """Quick check if a project is a Foundry project."""
    return (Path(root) / "foundry.toml").exists()


def is_hardhat_project(root: Path | str) -> bool:
    """Quick check if a project is a Hardhat project."""
    root = Path(root)
    return (root / "hardhat.config.js").exists() or (root / "hardhat.config.ts").exists()


def get_test_file_extension(project_type: ProjectType) -> str:
    """
    Get the appropriate test file extension for a project type.

    Args:
        project_type: The detected project type

    Returns:
        File extension including the dot
    """
    if project_type == ProjectType.FOUNDRY:
        return ".t.sol"
    elif project_type == ProjectType.HARDHAT:
        return ".ts"  # Modern Hardhat uses TypeScript
    elif project_type == ProjectType.BROWNIE:
        return ".py"  # Brownie uses Python
    else:
        return ".t.sol"  # Default to Foundry style
