"""
Import Remapping Resolution (Task 4.3)

Resolves Solidity import paths to actual file paths using project-specific
remappings for test scaffold generation.

Philosophy:
- Target 70% resolution of common patterns, not 100%
- Fail gracefully with helpful TODO comments
- Project-specific remappings take precedence over defaults
- Always return something usable for test generation

Known Limitations:
- Cannot verify OpenZeppelin version compatibility
- Cannot resolve transitive dependencies
- Cannot handle monorepo structures
- Relative imports passed through unchanged
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from alphaswarm_sol.testing.detection import ProjectConfig, ProjectType


class ImportResolver:
    """
    Resolve Solidity import paths to actual file paths.

    Uses project-specific remappings from detection, falling back to
    common patterns for standard dependencies.

    Example:
        >>> config = detect_project_structure(Path("./my-foundry-project"))
        >>> resolver = ImportResolver(config)
        >>> resolver.resolve("@openzeppelin/contracts/token/ERC20/ERC20.sol")
        'lib/openzeppelin-contracts/contracts/token/ERC20/ERC20.sol'
    """

    # Common remapping patterns with fallback candidates
    # Order matters - earlier candidates are tried first
    COMMON_REMAPPINGS: Dict[str, List[str]] = {
        # OpenZeppelin
        "@openzeppelin/contracts/": [
            "lib/openzeppelin-contracts/contracts/",
            "lib/@openzeppelin/contracts/",
            "node_modules/@openzeppelin/contracts/",
        ],
        "@openzeppelin/contracts-upgradeable/": [
            "lib/openzeppelin-contracts-upgradeable/contracts/",
            "lib/@openzeppelin/contracts-upgradeable/",
            "node_modules/@openzeppelin/contracts-upgradeable/",
        ],
        # Forge std
        "forge-std/": [
            "lib/forge-std/src/",
        ],
        # Solmate
        "solmate/": [
            "lib/solmate/src/",
        ],
        # Solady
        "solady/": [
            "lib/solady/src/",
        ],
        # Chainlink
        "@chainlink/contracts/": [
            "lib/chainlink/contracts/",
            "node_modules/@chainlink/contracts/",
        ],
        # Uniswap
        "@uniswap/v2-core/": [
            "lib/v2-core/",
            "node_modules/@uniswap/v2-core/",
        ],
        "@uniswap/v3-core/": [
            "lib/v3-core/",
            "node_modules/@uniswap/v3-core/",
        ],
    }

    def __init__(self, config: ProjectConfig):
        """
        Initialize resolver with project configuration.

        Args:
            config: Project configuration from detection module
        """
        self.config = config
        self.root = config.root
        self._resolution_cache: Dict[str, Optional[str]] = {}

    def resolve(self, import_path: str) -> Optional[str]:
        """
        Resolve import path to actual file path.

        Resolution order:
        1. Project-specific remappings from config
        2. Common library patterns
        3. node_modules for Hardhat projects
        4. Direct path check

        Args:
            import_path: The import path from Solidity
                (e.g., "@openzeppelin/contracts/token/ERC20/ERC20.sol")

        Returns:
            Resolved path relative to project root, or None if cannot resolve
        """
        # Check cache first
        if import_path in self._resolution_cache:
            return self._resolution_cache[import_path]

        result = self._resolve_uncached(import_path)
        self._resolution_cache[import_path] = result
        return result

    def _resolve_uncached(self, import_path: str) -> Optional[str]:
        """Internal resolution without caching."""
        # Handle relative imports - pass through unchanged
        if import_path.startswith("./") or import_path.startswith("../"):
            return import_path

        # 1. Try project-specific remappings first
        for prefix, replacement in self.config.remappings.items():
            if import_path.startswith(prefix):
                candidate = import_path.replace(prefix, replacement, 1)
                full_path = self.root / candidate
                if full_path.exists():
                    return candidate
                # Return anyway - project config is authoritative
                return candidate

        # 2. Try common patterns
        for prefix, candidates in self.COMMON_REMAPPINGS.items():
            if import_path.startswith(prefix):
                for candidate_base in candidates:
                    candidate = import_path.replace(prefix, candidate_base, 1)
                    full_path = self.root / candidate
                    if full_path.exists():
                        return candidate
                # Return first candidate even if not found
                # Better to have something than nothing
                return import_path.replace(prefix, candidates[0], 1)

        # 3. For Hardhat, try node_modules directly
        if self.config.project_type == ProjectType.HARDHAT:
            if import_path.startswith("@"):
                candidate = f"node_modules/{import_path}"
                full_path = self.root / candidate
                if full_path.exists():
                    return candidate
                # Return anyway for Hardhat
                return candidate

        # 4. Try direct path (might be relative to src)
        for base_dir in [self.config.src_dir, self.root]:
            candidate = import_path
            full_path = base_dir / candidate
            if full_path.exists():
                return candidate

        # Cannot resolve
        return None

    def resolve_for_test(self, import_path: str) -> str:
        """
        Resolve import path for test file, with fallback.

        Always returns a string suitable for an import statement.
        If cannot resolve, returns original with helpful TODO comment.

        Args:
            import_path: The import path

        Returns:
            Import statement string
        """
        resolved = self.resolve(import_path)
        if resolved:
            return f'import "{resolved}";'
        else:
            return (
                f"// TODO: Cannot resolve import, adjust manually\n"
                f'// import "{import_path}";'
            )

    def suggest_forge_std_import(self) -> str:
        """
        Suggest the correct forge-std import for this project.

        Returns:
            Import statement for Test.sol or TODO comment
        """
        if self.config.project_type == ProjectType.FOUNDRY:
            # Check explicit remapping
            if "forge-std/" in self.config.remappings:
                return 'import "forge-std/Test.sol";'

            # Check if forge-std exists in lib
            if (self.root / "lib/forge-std").exists():
                return 'import "forge-std/Test.sol";'

            # Check dependencies list
            if "forge-std" in self.config.dependencies:
                return 'import "forge-std/Test.sol";'

        # For non-Foundry or missing forge-std
        return (
            "// TODO: Install forge-std or use alternative test framework\n"
            "// forge install foundry-rs/forge-std\n"
            '// import "forge-std/Test.sol";'
        )

    def suggest_console_import(self) -> str:
        """
        Suggest console.log import for debugging.

        Returns:
            Console import statement or TODO
        """
        if self.config.project_type == ProjectType.FOUNDRY:
            return 'import "forge-std/console.sol";'
        elif self.config.project_type == ProjectType.HARDHAT:
            return 'import "hardhat/console.sol";'
        else:
            return (
                "// TODO: Console logging varies by framework\n"
                '// import "forge-std/console.sol";  // For Foundry\n'
                '// import "hardhat/console.sol";    // For Hardhat'
            )

    def resolve_contract_import(self, contract_path: Path) -> str:
        """
        Generate import statement for a contract file.

        Calculates relative or remapped path from test directory.

        Args:
            contract_path: Path to the contract file

        Returns:
            Import statement string
        """
        try:
            # Make path relative to project root
            if contract_path.is_absolute():
                rel_path = contract_path.relative_to(self.root)
            else:
                rel_path = contract_path

            # For Foundry, use src-relative path
            if self.config.project_type == ProjectType.FOUNDRY:
                # Check if path is within src_dir
                src_rel = self.config.src_dir.relative_to(self.root)
                if str(rel_path).startswith(str(src_rel)):
                    return f'import "{rel_path}";'

                # Otherwise, use relative from test dir
                return f'import "../{rel_path}";'

            # For other frameworks
            return f'import "{rel_path}";'

        except ValueError:
            # Path is not relative to root
            return f'// TODO: Adjust import path\n// import "{contract_path.name}";'

    def get_resolution_stats(self) -> Dict[str, int]:
        """
        Get statistics on resolution success.

        Returns:
            Dict with 'resolved', 'unresolved', 'total' counts
        """
        resolved = sum(1 for v in self._resolution_cache.values() if v is not None)
        unresolved = sum(1 for v in self._resolution_cache.values() if v is None)
        return {
            "resolved": resolved,
            "unresolved": unresolved,
            "total": resolved + unresolved,
        }


def extract_imports_from_source(source_code: str) -> List[str]:
    """
    Extract import paths from Solidity source code.

    Handles various import syntaxes:
    - import "path";
    - import {Foo} from "path";
    - import {Foo as Bar} from "path";
    - import * as Lib from "path";

    Args:
        source_code: Solidity source file content

    Returns:
        List of unique import paths (deduplicated, order preserved)
    """
    # Pattern matches all Solidity import variants
    # import "path";
    # import { X } from "path";
    # import { X, Y } from "path";
    # import * as X from "path";
    pattern = r'import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+)\s+from\s+)?["\']([^"\']+)["\']'
    matches = re.findall(pattern, source_code)

    # Deduplicate while preserving order
    seen = set()
    result = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            result.append(match)

    return result


def extract_pragma_from_source(source_code: str) -> Optional[str]:
    """
    Extract pragma version from Solidity source code.

    Args:
        source_code: Solidity source file content

    Returns:
        Pragma version string (e.g., "^0.8.20") or None
    """
    pattern = r'pragma\s+solidity\s+([^;]+);'
    match = re.search(pattern, source_code)
    if match:
        return match.group(1).strip()
    return None


def parse_import_statement(import_line: str) -> Tuple[Optional[str], List[str]]:
    """
    Parse a Solidity import statement.

    Args:
        import_line: A single import statement

    Returns:
        Tuple of (path, list of imported symbols)
        symbols list is empty for "import path" style
    """
    # Match import with symbols
    symbol_pattern = r'import\s+\{([^}]+)\}\s+from\s+["\']([^"\']+)["\']'
    match = re.search(symbol_pattern, import_line)
    if match:
        symbols_str = match.group(1)
        path = match.group(2)
        # Parse individual symbols (handles "Foo as Bar" syntax)
        symbols = [s.strip().split()[0] for s in symbols_str.split(",")]
        return path, symbols

    # Match wildcard import
    wildcard_pattern = r'import\s+\*\s+as\s+(\w+)\s+from\s+["\']([^"\']+)["\']'
    match = re.search(wildcard_pattern, import_line)
    if match:
        alias = match.group(1)
        path = match.group(2)
        return path, [f"* as {alias}"]

    # Match simple import
    simple_pattern = r'import\s+["\']([^"\']+)["\']'
    match = re.search(simple_pattern, import_line)
    if match:
        return match.group(1), []

    return None, []
