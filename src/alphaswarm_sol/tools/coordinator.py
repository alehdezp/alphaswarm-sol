"""
Tool Coordinator

Analyzes Solidity projects and creates intelligent tool execution strategies.
The coordinator determines which tools to run based on project characteristics,
groups tools for parallel execution, and provides rationale for decisions.

Per PHILOSOPHY.md Pillar 6: coordinator decisions use sonnet-4.5 tier for
optimal strategy creation while tool execution uses haiku-4.5.

Usage:
    coordinator = ToolCoordinator()
    analysis = coordinator.analyze_project(Path("./contracts"))
    strategy = coordinator.create_strategy(analysis, available_tools)
    print(coordinator.explain_strategy(strategy))
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple

import structlog

from alphaswarm_sol.tools.config import ToolConfig, get_optimal_config
from alphaswarm_sol.tools.mapping import TOOL_DETECTOR_MAP, get_patterns_covered_by_tools
from alphaswarm_sol.tools.registry import ModelTier, ToolRegistry, ToolTier

logger = structlog.get_logger(__name__)


@dataclass
class ProjectAnalysis:
    """Analysis of a Solidity project for tool selection.

    Captures project characteristics that influence which tools to run:
    - Scale (contracts, lines of code)
    - Complexity indicators (proxies, math libraries)
    - Risk areas (value handling, external calls)
    - Build system (Foundry vs Hardhat)

    Attributes:
        contract_count: Number of .sol files in scope
        total_lines: Total lines of Solidity code
        has_proxy_pattern: Uses delegatecall or proxy patterns
        has_complex_math: Uses FullMath, FixedPoint, or similar
        has_value_transfers: Handles ETH transfers
        has_external_calls: Makes calls to external contracts
        has_oracles: Integrates price feeds or oracles
        libraries_used: Known libraries (OpenZeppelin, Solmate, etc.)
        solidity_version: Primary Solidity version detected
        is_foundry_project: Has foundry.toml
        is_hardhat_project: Has hardhat.config.js/ts
        contracts_in_scope: List of contract file paths
        detected_patterns: Specific patterns found during analysis
    """

    contract_count: int
    total_lines: int
    has_proxy_pattern: bool
    has_complex_math: bool
    has_value_transfers: bool
    has_external_calls: bool
    has_oracles: bool
    libraries_used: List[str]
    solidity_version: str
    is_foundry_project: bool
    is_hardhat_project: bool
    contracts_in_scope: List[str] = field(default_factory=list)
    detected_patterns: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "contract_count": self.contract_count,
            "total_lines": self.total_lines,
            "has_proxy_pattern": self.has_proxy_pattern,
            "has_complex_math": self.has_complex_math,
            "has_value_transfers": self.has_value_transfers,
            "has_external_calls": self.has_external_calls,
            "has_oracles": self.has_oracles,
            "libraries_used": self.libraries_used,
            "solidity_version": self.solidity_version,
            "is_foundry_project": self.is_foundry_project,
            "is_hardhat_project": self.is_hardhat_project,
            "contracts_in_scope": self.contracts_in_scope,
            "detected_patterns": self.detected_patterns,
        }

    @property
    def complexity_score(self) -> int:
        """Estimate project complexity (0-10 scale).

        Higher scores indicate more complex analysis needs.
        """
        score = 0
        if self.contract_count > 10:
            score += 2
        elif self.contract_count > 5:
            score += 1
        if self.total_lines > 2000:
            score += 2
        elif self.total_lines > 500:
            score += 1
        if self.has_proxy_pattern:
            score += 2
        if self.has_complex_math:
            score += 1
        if self.has_value_transfers:
            score += 1
        if self.has_external_calls:
            score += 1
        return min(score, 10)


@dataclass
class ToolStrategy:
    """Execution strategy for static analysis tools.

    Specifies which tools to run, how to group them for parallel
    execution, and the rationale for each decision.

    Attributes:
        tools_to_run: List of tool names to execute
        parallel_groups: Groups of tools that can run concurrently
        tool_configs: Configuration overrides per tool
        estimated_time_seconds: Rough time estimate for full analysis
        rationale: Human-readable explanation of strategy
        skip_reasons: Why each skipped tool was excluded
        patterns_to_skip: VKG patterns covered by tools (can skip in VKG)
        pattern_skip_rationale: Explanation for each pattern skip
    """

    tools_to_run: List[str]
    parallel_groups: List[List[str]]
    tool_configs: Dict[str, ToolConfig]
    estimated_time_seconds: int
    rationale: str
    skip_reasons: Dict[str, str] = field(default_factory=dict)
    patterns_to_skip: List[str] = field(default_factory=list)
    pattern_skip_rationale: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tools_to_run": self.tools_to_run,
            "parallel_groups": self.parallel_groups,
            "tool_configs": {
                name: config.to_dict() for name, config in self.tool_configs.items()
            },
            "estimated_time_seconds": self.estimated_time_seconds,
            "rationale": self.rationale,
            "skip_reasons": self.skip_reasons,
            "patterns_to_skip": self.patterns_to_skip,
            "pattern_skip_rationale": self.pattern_skip_rationale,
        }


class ToolCoordinator:
    """Coordinates tool selection and execution strategy.

    Analyzes Solidity projects to determine optimal tool selection based on:
    - Project characteristics (size, complexity, patterns)
    - Tool availability (what's installed)
    - Tool capabilities (what each tool is good at)

    Also determines which VKG patterns can be skipped based on tool coverage
    (TOOL-07 pattern skip logic).

    Model tier: sonnet-4.5 for coordination decisions.

    Example:
        coordinator = ToolCoordinator()

        # Analyze project
        analysis = coordinator.analyze_project(Path("./contracts"))
        print(f"Found {analysis.contract_count} contracts")

        # Create strategy based on available tools
        strategy = coordinator.create_strategy(analysis, ["slither", "aderyn"])

        # Get human-readable explanation
        print(coordinator.explain_strategy(strategy))

        # Get patterns VKG should run (complement of skip list)
        edge_cases = coordinator.get_edge_case_patterns()
    """

    # Model tier for coordination decisions
    MODEL_TIER: ClassVar[str] = ModelTier.COORDINATION

    # Coverage threshold: if tool precision >= this, skip VKG pattern
    SKIP_THRESHOLD: ClassVar[float] = 0.80

    # Patterns that should NEVER be skipped (edge cases, complex logic)
    # These require VKG's semantic analysis regardless of tool coverage
    NEVER_SKIP_PATTERNS: ClassVar[Set[str]] = {
        # Business logic - tools can't detect semantic issues
        "business-logic-violation",
        "economic-manipulation",
        "governance-attack",
        # Complex multi-step patterns
        "cross-function-reentrancy",
        "cross-contract-reentrancy",
        # Context-dependent issues
        "oracle-manipulation",
        "price-manipulation",
        "flash-loan-attack",
        # Access control edge cases
        "privilege-escalation",
        "role-confusion",
        # Protocol-specific patterns
        "slippage-manipulation",
        "sandwich-attack",
        "front-running",
    }

    # Patterns for detecting project characteristics
    PROXY_PATTERNS: ClassVar[List[str]] = [
        r"\bdelegatecall\b",
        r"\bERC1967\b",
        r"\bTransparentUpgradeableProxy\b",
        r"\bUUPS\b",
        r"\bBeaconProxy\b",
        r"Proxy\s*\(",
        r"_implementation\s*\(",
        r"_delegate\s*\(",
    ]

    COMPLEX_MATH_PATTERNS: ClassVar[List[str]] = [
        r"\bmulDiv\b",
        r"\bFullMath\b",
        r"\bFixedPoint\b",
        r"\bSafeMath\b",
        r"\bABDK\b",
        r"\bPRBMath\b",
        r"\bMath\.sqrt\b",
        r"\bwad\w*\b",
        r"\bray\w*\b",
        r"\bsqrt\s*\(",
    ]

    VALUE_TRANSFER_PATTERNS: ClassVar[List[str]] = [
        r"\.transfer\s*\(",
        r"\.send\s*\(",
        r"\.call\s*\{.*value:",
        r"\bpayable\b",
        r"msg\.value",
        r"\breceive\s*\(\s*\)",
        r"\bfallback\s*\(\s*\)",
    ]

    EXTERNAL_CALL_PATTERNS: ClassVar[List[str]] = [
        r"\.call\s*\(",
        r"\.staticcall\s*\(",
        r"\bIERC20\b",
        r"\bSafeERC20\b",
        r"\.safeTransfer",
        r"\.approve\s*\(",
        r"interface\s+\w+\s*\{",
    ]

    ORACLE_PATTERNS: ClassVar[List[str]] = [
        r"\bpriceFeed\b",
        r"\boracle\b",
        r"\bChainlink\b",
        r"\bgetPrice\b",
        r"\blatestRoundData\b",
        r"\bgetLatestPrice\b",
        r"\bAggregator",
        r"\bTWAP\b",
    ]

    # Known library imports
    KNOWN_LIBRARIES: ClassVar[Dict[str, List[str]]] = {
        "openzeppelin": [
            "@openzeppelin/",
            "openzeppelin-contracts",
        ],
        "solmate": [
            "solmate/",
            "@rari-capital/solmate",
        ],
        "solady": [
            "solady/",
        ],
        "prb-math": [
            "@prb/math",
            "prb-math",
        ],
        "uniswap": [
            "@uniswap/",
            "uniswap-v2",
            "uniswap-v3",
        ],
        "chainlink": [
            "@chainlink/",
            "chainlink",
        ],
    }

    # Default parallel execution groups
    DEFAULT_PARALLEL_GROUPS: ClassVar[List[List[str]]] = [
        ["slither", "aderyn", "semgrep"],  # Fast static analysis
        ["mythril", "halmos"],  # Symbolic execution
        ["echidna", "foundry", "medusa"],  # Fuzzing
    ]

    # Estimated time per tool (seconds) for 1000 lines of code
    TOOL_TIME_ESTIMATES: ClassVar[Dict[str, int]] = {
        "slither": 30,
        "aderyn": 20,
        "semgrep": 15,
        "mythril": 300,
        "halmos": 180,
        "echidna": 120,
        "foundry": 60,
        "medusa": 150,
    }

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """Initialize coordinator.

        Args:
            registry: Tool registry for checking availability.
                     Creates default if not provided.
        """
        self.registry = registry or ToolRegistry()

    def analyze_project(self, path: Path) -> ProjectAnalysis:
        """Analyze a Solidity project for tool selection.

        Scans the project to determine characteristics that influence
        tool selection and configuration.

        Args:
            path: Project root directory.

        Returns:
            ProjectAnalysis with detected characteristics.
        """
        logger.info("analyzing_project", path=str(path))

        # Find all .sol files
        sol_files = self._find_solidity_files(path)
        contracts_in_scope = [str(f.relative_to(path)) for f in sol_files]

        # Read and aggregate code content
        all_code = ""
        total_lines = 0
        for sol_file in sol_files:
            try:
                content = sol_file.read_text(encoding="utf-8")
                all_code += content + "\n"
                total_lines += len(content.splitlines())
            except (OSError, UnicodeDecodeError) as e:
                logger.warning("file_read_error", file=str(sol_file), error=str(e))

        # Detect patterns
        detected_patterns: Dict[str, List[str]] = {}

        has_proxy = self._detect_patterns(all_code, self.PROXY_PATTERNS, "proxy")
        if has_proxy:
            detected_patterns["proxy"] = has_proxy

        has_math = self._detect_patterns(
            all_code, self.COMPLEX_MATH_PATTERNS, "complex_math"
        )
        if has_math:
            detected_patterns["complex_math"] = has_math

        has_value = self._detect_patterns(
            all_code, self.VALUE_TRANSFER_PATTERNS, "value_transfer"
        )
        if has_value:
            detected_patterns["value_transfer"] = has_value

        has_external = self._detect_patterns(
            all_code, self.EXTERNAL_CALL_PATTERNS, "external_call"
        )
        if has_external:
            detected_patterns["external_call"] = has_external

        has_oracle = self._detect_patterns(all_code, self.ORACLE_PATTERNS, "oracle")
        if has_oracle:
            detected_patterns["oracle"] = has_oracle

        # Detect libraries
        libraries_used = self._detect_libraries(all_code)

        # Detect Solidity version
        solidity_version = self._detect_solidity_version(all_code)

        # Detect build system
        is_foundry = (path / "foundry.toml").exists()
        is_hardhat = (
            (path / "hardhat.config.js").exists()
            or (path / "hardhat.config.ts").exists()
        )

        analysis = ProjectAnalysis(
            contract_count=len(sol_files),
            total_lines=total_lines,
            has_proxy_pattern=bool(has_proxy),
            has_complex_math=bool(has_math),
            has_value_transfers=bool(has_value),
            has_external_calls=bool(has_external),
            has_oracles=bool(has_oracle),
            libraries_used=libraries_used,
            solidity_version=solidity_version,
            is_foundry_project=is_foundry,
            is_hardhat_project=is_hardhat,
            contracts_in_scope=contracts_in_scope,
            detected_patterns=detected_patterns,
        )

        logger.info(
            "project_analyzed",
            contracts=analysis.contract_count,
            lines=analysis.total_lines,
            complexity=analysis.complexity_score,
            patterns=list(detected_patterns.keys()),
        )

        return analysis

    def create_strategy(
        self,
        analysis: ProjectAnalysis,
        available_tools: Optional[List[str]] = None,
    ) -> ToolStrategy:
        """Create tool execution strategy based on project analysis.

        Selects tools based on:
        1. Project characteristics (what tools are most effective)
        2. Tool availability (what's installed)
        3. Parallel execution groups (minimize total time)

        Args:
            analysis: Project analysis from analyze_project().
            available_tools: List of available tool names.
                           If None, queries registry.

        Returns:
            ToolStrategy with execution plan.
        """
        # Get available tools
        if available_tools is None:
            available_tools = self.registry.get_available_tools()

        available_set = set(available_tools)
        tools_to_run: List[str] = []
        skip_reasons: Dict[str, str] = {}
        rationale_parts: List[str] = []

        # Always run baseline static analysis (Tier 0 and Tier 1 basics)
        baseline_tools = ["slither", "aderyn"]
        for tool in baseline_tools:
            if tool in available_set:
                tools_to_run.append(tool)
                rationale_parts.append(f"- {tool}: baseline static analysis")
            else:
                skip_reasons[tool] = "not installed"

        # Add semgrep for pattern matching
        if "semgrep" in available_set:
            tools_to_run.append("semgrep")
            rationale_parts.append("- semgrep: pattern-based vulnerability detection")
        else:
            skip_reasons["semgrep"] = "not installed"

        # Add symbolic execution for complex contracts
        if analysis.has_complex_math or analysis.has_proxy_pattern:
            symbolic_reason = []
            if analysis.has_complex_math:
                symbolic_reason.append("complex math")
            if analysis.has_proxy_pattern:
                symbolic_reason.append("proxy patterns")
            reason_str = " and ".join(symbolic_reason)

            if "mythril" in available_set:
                tools_to_run.append("mythril")
                rationale_parts.append(
                    f"- mythril: symbolic execution ({reason_str} detected)"
                )
            else:
                skip_reasons["mythril"] = "not installed (recommended for complex math)"

            if "halmos" in available_set:
                tools_to_run.append("halmos")
                rationale_parts.append(
                    f"- halmos: bounded model checking ({reason_str} detected)"
                )
            else:
                skip_reasons["halmos"] = "not installed (optional for verification)"
        else:
            skip_reasons["mythril"] = "no complex math or proxy patterns detected"
            skip_reasons["halmos"] = "no complex math or proxy patterns detected"

        # Add fuzzing for value handling
        if analysis.has_value_transfers or analysis.has_external_calls:
            fuzz_reason = []
            if analysis.has_value_transfers:
                fuzz_reason.append("value transfers")
            if analysis.has_external_calls:
                fuzz_reason.append("external calls")
            reason_str = " and ".join(fuzz_reason)

            # Prefer foundry if it's a foundry project
            if analysis.is_foundry_project and "foundry" in available_set:
                tools_to_run.append("foundry")
                rationale_parts.append(
                    f"- foundry: native fuzz testing ({reason_str}, foundry project)"
                )
            elif "foundry" in available_set:
                tools_to_run.append("foundry")
                rationale_parts.append(f"- foundry: fuzz testing ({reason_str})")
            else:
                skip_reasons["foundry"] = "not installed"

            if "echidna" in available_set:
                tools_to_run.append("echidna")
                rationale_parts.append(
                    f"- echidna: property-based fuzzing ({reason_str})"
                )
            else:
                skip_reasons["echidna"] = "not installed (recommended for fuzzing)"

            if "medusa" in available_set:
                tools_to_run.append("medusa")
                rationale_parts.append(f"- medusa: parallel fuzzing ({reason_str})")
            else:
                skip_reasons["medusa"] = "not installed (optional parallel fuzzer)"
        else:
            skip_reasons["echidna"] = "no value transfers or external calls detected"
            skip_reasons["foundry"] = "no value transfers or external calls detected"
            skip_reasons["medusa"] = "no value transfers or external calls detected"

        # Build parallel groups from selected tools
        parallel_groups = self._build_parallel_groups(tools_to_run)

        # Create tool configs
        tool_configs = self._create_tool_configs(tools_to_run, analysis)

        # Estimate execution time
        estimated_time = self._estimate_execution_time(
            tools_to_run, parallel_groups, analysis.total_lines
        )

        # Build rationale
        rationale = self._build_rationale(analysis, rationale_parts)

        # Calculate pattern skip list (TOOL-07)
        patterns_to_skip, pattern_skip_rationale = self._calculate_pattern_skips(
            tools_to_run, analysis
        )

        strategy = ToolStrategy(
            tools_to_run=tools_to_run,
            parallel_groups=parallel_groups,
            tool_configs=tool_configs,
            estimated_time_seconds=estimated_time,
            rationale=rationale,
            skip_reasons=skip_reasons,
            patterns_to_skip=patterns_to_skip,
            pattern_skip_rationale=pattern_skip_rationale,
        )

        logger.info(
            "strategy_created",
            tools=tools_to_run,
            groups=len(parallel_groups),
            estimated_time=estimated_time,
            patterns_skipped=len(patterns_to_skip),
        )

        return strategy

    def explain_strategy(self, strategy: ToolStrategy) -> str:
        """Generate human-readable explanation of strategy.

        Args:
            strategy: Strategy to explain.

        Returns:
            Formatted explanation string.
        """
        lines = [
            "Tool Execution Strategy",
            "=" * 50,
            "",
            f"Tools to run: {len(strategy.tools_to_run)}",
            f"Estimated time: {strategy.estimated_time_seconds // 60}m "
            f"{strategy.estimated_time_seconds % 60}s",
            "",
            "Execution Plan:",
        ]

        for i, group in enumerate(strategy.parallel_groups, 1):
            active = [t for t in group if t in strategy.tools_to_run]
            if active:
                lines.append(f"  Group {i} (parallel): {', '.join(active)}")

        lines.extend(["", "Rationale:", strategy.rationale, ""])

        if strategy.skip_reasons:
            lines.append("Skipped tools:")
            for tool, reason in strategy.skip_reasons.items():
                lines.append(f"  - {tool}: {reason}")

        # Add pattern skip information
        if strategy.patterns_to_skip:
            lines.extend([
                "",
                f"VKG patterns to skip ({len(strategy.patterns_to_skip)} covered by tools):",
            ])
            for pattern in sorted(strategy.patterns_to_skip)[:10]:
                rationale = strategy.pattern_skip_rationale.get(pattern, "")
                if rationale:
                    lines.append(f"  - {pattern}: {rationale}")
                else:
                    lines.append(f"  - {pattern}")
            if len(strategy.patterns_to_skip) > 10:
                lines.append(f"  ... and {len(strategy.patterns_to_skip) - 10} more")

            lines.extend([
                "",
                "Edge case patterns (always run VKG):",
                f"  {', '.join(sorted(self.NEVER_SKIP_PATTERNS)[:5])}...",
            ])

        return "\n".join(lines)

    def _find_solidity_files(self, path: Path) -> List[Path]:
        """Find all Solidity files in scope.

        Excludes common library paths (node_modules, lib, test).

        Args:
            path: Root directory to search.

        Returns:
            List of .sol file paths.
        """
        sol_files: List[Path] = []
        exclude_dirs = {"node_modules", "lib", ".git", "cache", "out", "artifacts"}

        for sol_file in path.rglob("*.sol"):
            # Check if any parent directory should be excluded
            parts = sol_file.relative_to(path).parts
            if not any(part in exclude_dirs for part in parts):
                sol_files.append(sol_file)

        return sorted(sol_files)

    def _detect_patterns(
        self,
        code: str,
        patterns: List[str],
        pattern_type: str,
    ) -> List[str]:
        """Detect patterns in code.

        Args:
            code: Source code to scan.
            patterns: Regex patterns to match.
            pattern_type: Type name for logging.

        Returns:
            List of matched pattern strings.
        """
        matches: Set[str] = set()
        for pattern in patterns:
            found = re.findall(pattern, code, re.IGNORECASE)
            matches.update(found)

        if matches:
            logger.debug(
                "patterns_detected",
                type=pattern_type,
                count=len(matches),
                examples=list(matches)[:3],
            )

        return list(matches)

    def _detect_libraries(self, code: str) -> List[str]:
        """Detect known libraries from imports.

        Args:
            code: Source code to scan.

        Returns:
            List of library names found.
        """
        libraries: List[str] = []

        for lib_name, markers in self.KNOWN_LIBRARIES.items():
            for marker in markers:
                if marker in code:
                    libraries.append(lib_name)
                    break

        return libraries

    def _detect_solidity_version(self, code: str) -> str:
        """Detect primary Solidity version from pragmas.

        Args:
            code: Source code to scan.

        Returns:
            Version string (e.g., "0.8.20") or "unknown".
        """
        # Match pragma solidity ^0.8.20; or pragma solidity >=0.8.0 <0.9.0;
        version_patterns = [
            r"pragma\s+solidity\s+[\^~]?(\d+\.\d+\.\d+)",
            r"pragma\s+solidity\s+>=?(\d+\.\d+\.\d+)",
        ]

        for pattern in version_patterns:
            match = re.search(pattern, code)
            if match:
                return match.group(1)

        return "unknown"

    def _build_parallel_groups(self, tools: List[str]) -> List[List[str]]:
        """Build parallel execution groups from selected tools.

        Args:
            tools: Tools to organize.

        Returns:
            List of tool groups that can run in parallel.
        """
        tool_set = set(tools)
        groups: List[List[str]] = []

        for default_group in self.DEFAULT_PARALLEL_GROUPS:
            group = [t for t in default_group if t in tool_set]
            if group:
                groups.append(group)

        # Add any tools not in default groups as a final group
        covered = {t for g in groups for t in g}
        uncovered = [t for t in tools if t not in covered]
        if uncovered:
            groups.append(uncovered)

        return groups

    def _create_tool_configs(
        self,
        tools: List[str],
        analysis: ProjectAnalysis,
    ) -> Dict[str, ToolConfig]:
        """Create optimized configs for selected tools.

        Adjusts configs based on project analysis.

        Args:
            tools: Tools to configure.
            analysis: Project analysis.

        Returns:
            Dict mapping tool name to config.
        """
        configs: Dict[str, ToolConfig] = {}

        for tool in tools:
            config = get_optimal_config(tool)

            # Adjust timeout for large projects
            if analysis.total_lines > 5000:
                config.timeout = int(config.timeout * 1.5)
            elif analysis.total_lines > 10000:
                config.timeout = int(config.timeout * 2)

            # Add contracts to scope
            if analysis.contracts_in_scope and tool in ["slither", "aderyn"]:
                # Don't override exclude_paths, let tool handle it
                pass

            configs[tool] = config

        return configs

    def _estimate_execution_time(
        self,
        tools: List[str],
        parallel_groups: List[List[str]],
        total_lines: int,
    ) -> int:
        """Estimate total execution time.

        Accounts for parallel execution - each group runs in parallel,
        groups run sequentially.

        Args:
            tools: All tools to run.
            parallel_groups: Parallel execution groups.
            total_lines: Lines of code.

        Returns:
            Estimated seconds.
        """
        # Scale factor based on code size (1000 lines = 1.0)
        scale = max(1.0, total_lines / 1000.0)

        total_time = 0
        for group in parallel_groups:
            # Time for group = slowest tool in group
            group_tools = [t for t in group if t in tools]
            if group_tools:
                max_time = max(
                    self.TOOL_TIME_ESTIMATES.get(t, 60) for t in group_tools
                )
                total_time += int(max_time * scale)

        return total_time

    def _calculate_pattern_skips(
        self,
        tools: List[str],
        analysis: ProjectAnalysis,
    ) -> Tuple[List[str], Dict[str, str]]:
        """Determine which VKG patterns to skip based on tool coverage.

        Per TOOL-07: VKG should not re-run patterns that tools cover well.
        Exception: edge case patterns (NEVER_SKIP_PATTERNS) always run.

        Args:
            tools: Tools that will be executed
            analysis: Project analysis (for context-specific skips)

        Returns:
            Tuple of (patterns_to_skip, skip_rationale)
        """
        coverage = get_patterns_covered_by_tools(tools)

        patterns_to_skip: List[str] = []
        skip_rationale: Dict[str, str] = {}

        for pattern, score in coverage.items():
            # Never skip edge-case patterns
            if pattern in self.NEVER_SKIP_PATTERNS:
                continue

            # Skip if tool coverage is high enough
            if score >= self.SKIP_THRESHOLD:
                patterns_to_skip.append(pattern)
                tools_covering = self._get_tools_for_pattern(pattern, tools)
                skip_rationale[pattern] = (
                    f"Covered by {', '.join(tools_covering)} "
                    f"(precision={score:.0%})"
                )

        logger.debug(
            "pattern_skips_calculated",
            total_patterns=len(coverage),
            skipped=len(patterns_to_skip),
            protected=len(self.NEVER_SKIP_PATTERNS),
        )

        return patterns_to_skip, skip_rationale

    def _get_tools_for_pattern(
        self,
        pattern: str,
        tools: List[str],
    ) -> List[str]:
        """Get which tools from the list cover a pattern.

        Args:
            pattern: VKG pattern ID
            tools: List of tool names to check

        Returns:
            List of tool names that cover this pattern
        """
        covering: List[str] = []
        for tool in tools:
            tool_map = TOOL_DETECTOR_MAP.get(tool.lower(), {})
            for detector, mapping in tool_map.items():
                if mapping.vkg_pattern == pattern:
                    covering.append(tool)
                    break
        return covering

    def get_edge_case_patterns(self) -> List[str]:
        """Return patterns that require VKG regardless of tools.

        These patterns detect issues that static tools cannot:
        - Business logic violations
        - Economic attacks
        - Multi-step exploits
        - Context-dependent vulnerabilities

        Returns:
            Sorted list of edge-case pattern IDs
        """
        return sorted(self.NEVER_SKIP_PATTERNS)

    def _build_rationale(
        self,
        analysis: ProjectAnalysis,
        tool_reasons: List[str],
    ) -> str:
        """Build human-readable rationale.

        Args:
            analysis: Project analysis.
            tool_reasons: Per-tool reasons.

        Returns:
            Formatted rationale string.
        """
        lines = [
            f"Project: {analysis.contract_count} contracts, "
            f"{analysis.total_lines} lines of code",
            f"Complexity score: {analysis.complexity_score}/10",
            "",
            "Tool selection:",
        ]
        lines.extend(tool_reasons)

        return "\n".join(lines)


# Convenience functions


def analyze_project(path: Path) -> ProjectAnalysis:
    """Analyze a project using default coordinator.

    Args:
        path: Project root directory.

    Returns:
        ProjectAnalysis.
    """
    return ToolCoordinator().analyze_project(path)


def create_strategy(
    analysis: ProjectAnalysis,
    available_tools: Optional[List[str]] = None,
) -> ToolStrategy:
    """Create strategy using default coordinator.

    Args:
        analysis: Project analysis.
        available_tools: Available tool names.

    Returns:
        ToolStrategy.
    """
    return ToolCoordinator().create_strategy(analysis, available_tools)


__all__ = [
    "ProjectAnalysis",
    "ToolStrategy",
    "ToolCoordinator",
    "analyze_project",
    "create_strategy",
]
