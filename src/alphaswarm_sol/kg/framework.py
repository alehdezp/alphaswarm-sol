"""
Framework Detection Module

Detects project framework (Hardhat, Foundry, Truffle, etc.) at build time
to enable framework-specific optimizations and remapping resolution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class Framework(Enum):
    """Supported development frameworks."""
    FOUNDRY = "foundry"
    HARDHAT = "hardhat"
    TRUFFLE = "truffle"
    BROWNIE = "brownie"
    APE = "ape"
    UNKNOWN = "unknown"


@dataclass
class FrameworkInfo:
    """Information about detected framework."""
    framework: Framework
    version: str | None = None
    config_path: Path | None = None
    remappings: dict[str, str] | None = None
    lib_paths: list[Path] | None = None
    src_paths: list[Path] | None = None
    test_paths: list[Path] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "framework": self.framework.value,
            "version": self.version,
            "config_path": str(self.config_path) if self.config_path else None,
            "remappings": self.remappings,
            "lib_paths": [str(p) for p in self.lib_paths] if self.lib_paths else None,
            "src_paths": [str(p) for p in self.src_paths] if self.src_paths else None,
            "test_paths": [str(p) for p in self.test_paths] if self.test_paths else None,
        }


def detect_framework(project_root: Path) -> FrameworkInfo:
    """
    Detect the development framework used in a project.

    Detection order (first match wins):
    1. Foundry (foundry.toml)
    2. Hardhat (hardhat.config.js/ts)
    3. Truffle (truffle-config.js)
    4. Brownie (brownie-config.yaml)
    5. Ape (ape-config.yaml)

    Args:
        project_root: Path to project root directory

    Returns:
        FrameworkInfo with detected framework details
    """
    # Check for Foundry
    foundry_config = project_root / "foundry.toml"
    if foundry_config.exists():
        return _parse_foundry(project_root, foundry_config)

    # Check for Hardhat
    for config_name in ["hardhat.config.ts", "hardhat.config.js"]:
        hardhat_config = project_root / config_name
        if hardhat_config.exists():
            return _parse_hardhat(project_root, hardhat_config)

    # Check for Truffle
    truffle_config = project_root / "truffle-config.js"
    if truffle_config.exists():
        return _parse_truffle(project_root, truffle_config)

    # Check for Brownie
    brownie_config = project_root / "brownie-config.yaml"
    if brownie_config.exists():
        return _parse_brownie(project_root, brownie_config)

    # Check for Ape
    ape_config = project_root / "ape-config.yaml"
    if ape_config.exists():
        return _parse_ape(project_root, ape_config)

    # Unknown framework - try to infer from directory structure
    return _infer_from_structure(project_root)


def _parse_foundry(project_root: Path, config_path: Path) -> FrameworkInfo:
    """Parse Foundry configuration."""
    remappings = {}
    lib_paths = []
    src_paths = []
    test_paths = []

    # Parse foundry.toml
    try:
        import tomllib
        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        profile = config.get("profile", {}).get("default", {})

        # Get paths
        src = profile.get("src", "src")
        test = profile.get("test", "test")
        libs = profile.get("libs", ["lib"])

        src_paths = [project_root / src]
        test_paths = [project_root / test]
        lib_paths = [project_root / lib for lib in libs]

    except Exception:
        # Default Foundry structure
        src_paths = [project_root / "src"]
        test_paths = [project_root / "test"]
        lib_paths = [project_root / "lib"]

    # Parse remappings.txt if exists
    remappings_file = project_root / "remappings.txt"
    if remappings_file.exists():
        try:
            with open(remappings_file) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line:
                        key, value = line.split("=", 1)
                        remappings[key] = value
        except Exception:
            pass

    return FrameworkInfo(
        framework=Framework.FOUNDRY,
        config_path=config_path,
        remappings=remappings if remappings else None,
        lib_paths=lib_paths,
        src_paths=src_paths,
        test_paths=test_paths,
    )


def _parse_hardhat(project_root: Path, config_path: Path) -> FrameworkInfo:
    """Parse Hardhat configuration."""
    # Default Hardhat structure
    src_paths = [project_root / "contracts"]
    test_paths = [project_root / "test"]
    lib_paths = [project_root / "node_modules"]

    # Try to parse package.json for dependencies
    package_json = project_root / "package.json"
    if package_json.exists():
        try:
            with open(package_json) as f:
                pkg = json.load(f)
            version = pkg.get("devDependencies", {}).get("hardhat")
            if not version:
                version = pkg.get("dependencies", {}).get("hardhat")
        except Exception:
            version = None
    else:
        version = None

    # Check for remappings in hardhat.config
    # (Would need to parse JS/TS which is complex - skip for now)

    return FrameworkInfo(
        framework=Framework.HARDHAT,
        version=version,
        config_path=config_path,
        lib_paths=lib_paths,
        src_paths=src_paths,
        test_paths=test_paths,
    )


def _parse_truffle(project_root: Path, config_path: Path) -> FrameworkInfo:
    """Parse Truffle configuration."""
    return FrameworkInfo(
        framework=Framework.TRUFFLE,
        config_path=config_path,
        src_paths=[project_root / "contracts"],
        test_paths=[project_root / "test"],
        lib_paths=[project_root / "node_modules"],
    )


def _parse_brownie(project_root: Path, config_path: Path) -> FrameworkInfo:
    """Parse Brownie configuration."""
    return FrameworkInfo(
        framework=Framework.BROWNIE,
        config_path=config_path,
        src_paths=[project_root / "contracts"],
        test_paths=[project_root / "tests"],
        lib_paths=[project_root / "interfaces"],
    )


def _parse_ape(project_root: Path, config_path: Path) -> FrameworkInfo:
    """Parse Ape configuration."""
    return FrameworkInfo(
        framework=Framework.APE,
        config_path=config_path,
        src_paths=[project_root / "contracts"],
        test_paths=[project_root / "tests"],
    )


def _infer_from_structure(project_root: Path) -> FrameworkInfo:
    """Infer framework from directory structure."""
    # Check for common patterns
    if (project_root / "src").exists() and (project_root / "lib").exists():
        # Likely Foundry without config
        return FrameworkInfo(
            framework=Framework.FOUNDRY,
            src_paths=[project_root / "src"],
            lib_paths=[project_root / "lib"],
        )

    if (project_root / "contracts").exists():
        if (project_root / "node_modules").exists():
            # Likely Hardhat/Truffle
            return FrameworkInfo(
                framework=Framework.HARDHAT,
                src_paths=[project_root / "contracts"],
                lib_paths=[project_root / "node_modules"],
            )
        else:
            # Generic contracts directory
            return FrameworkInfo(
                framework=Framework.UNKNOWN,
                src_paths=[project_root / "contracts"],
            )

    # Unknown - use project root as source
    return FrameworkInfo(
        framework=Framework.UNKNOWN,
        src_paths=[project_root],
    )


def resolve_import(import_path: str, framework_info: FrameworkInfo, project_root: Path) -> Path | None:
    """
    Resolve an import path using framework-specific remappings.

    Args:
        import_path: Import path from Solidity source
        framework_info: Detected framework info
        project_root: Project root directory

    Returns:
        Resolved path or None if not found
    """
    # Apply remappings first
    if framework_info.remappings:
        for prefix, target in sorted(framework_info.remappings.items(), key=lambda x: -len(x[0])):
            if import_path.startswith(prefix):
                resolved = import_path.replace(prefix, target, 1)
                full_path = project_root / resolved
                if full_path.exists():
                    return full_path

    # Check lib paths
    if framework_info.lib_paths:
        for lib_path in framework_info.lib_paths:
            # Try direct path
            full_path = lib_path / import_path
            if full_path.exists():
                return full_path

            # Try with common prefixes stripped
            for prefix in ["@", ""]:
                if import_path.startswith(prefix):
                    stripped = import_path[len(prefix):]
                    full_path = lib_path / stripped
                    if full_path.exists():
                        return full_path

    # Check src paths
    if framework_info.src_paths:
        for src_path in framework_info.src_paths:
            full_path = src_path / import_path
            if full_path.exists():
                return full_path

    return None
