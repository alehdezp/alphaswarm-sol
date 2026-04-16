"""
VKG Error Handling

LLM-friendly error messages with recovery suggestions.

Philosophy: "Error messages should guide recovery, not just report failure"
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    """Categories of errors for targeted recovery suggestions."""

    BUILD = "build"          # Graph building errors
    ANALYSIS = "analysis"    # Pattern analysis errors
    QUERY = "query"          # Query execution errors
    FINDINGS = "findings"    # Findings management errors
    CONFIG = "config"        # Configuration errors
    IO = "io"                # File I/O errors


class VKGError(Exception):
    """
    Base exception for VKG with recovery suggestions.

    All VKG errors include:
    - What went wrong (message)
    - Where it happened (location)
    - Why it happened (details)
    - How to fix it (suggestions)

    Example:
        >>> raise VKGError(
        ...     message="Build failed: contracts not found",
        ...     category=ErrorCategory.BUILD,
        ...     location="contracts/",
        ...     details="No .sol files in target directory",
        ...     suggestions=[
        ...         "Check the path is correct",
        ...         "Ensure .sol files exist in the directory",
        ...         "Try: vkg build src/ (if contracts are in src/)"
        ...     ]
        ... )
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.BUILD,
        location: Optional[str] = None,
        details: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        recovery_commands: Optional[list[str]] = None,
    ) -> None:
        """
        Initialize VKG error.

        Args:
            message: What went wrong
            category: Error category for grouping
            location: Where the error occurred
            details: Why it happened
            suggestions: How to fix it (text suggestions)
            recovery_commands: Ready-to-run commands to fix the issue
        """
        self.category = category
        self.location = location
        self.details = details
        self.suggestions = suggestions or []
        self.recovery_commands = recovery_commands or []

        super().__init__(message)

    def format_cli(self) -> str:
        """Format error for CLI output (LLM-friendly)."""
        lines = []

        # Error header
        lines.append(f"Error: {self.args[0]}")
        lines.append("")

        # Location if available
        if self.location:
            lines.append(f"Location: {self.location}")

        # Details if available
        if self.details:
            lines.append(f"Details: {self.details}")

        if self.location or self.details:
            lines.append("")

        # Suggestions
        if self.suggestions:
            lines.append("To fix this:")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
            lines.append("")

        # Ready-to-run commands
        if self.recovery_commands:
            lines.append("Try running:")
            for cmd in self.recovery_commands:
                lines.append(f"  {cmd}")
            lines.append("")

        # Help reference
        lines.append("For more help: vkg --help")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "error": True,
            "message": str(self.args[0]),
            "category": self.category.value,
            "location": self.location,
            "details": self.details,
            "suggestions": self.suggestions,
            "recovery_commands": self.recovery_commands,
        }


class BuildError(VKGError):
    """Error during graph building."""

    def __init__(
        self,
        message: str,
        location: Optional[str] = None,
        details: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        recovery_commands: Optional[list[str]] = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.BUILD,
            location=location,
            details=details,
            suggestions=suggestions,
            recovery_commands=recovery_commands,
        )


class AnalysisError(VKGError):
    """Error during pattern analysis."""

    def __init__(
        self,
        message: str,
        location: Optional[str] = None,
        details: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        recovery_commands: Optional[list[str]] = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.ANALYSIS,
            location=location,
            details=details,
            suggestions=suggestions,
            recovery_commands=recovery_commands,
        )


class QueryError(VKGError):
    """Error during query execution."""

    def __init__(
        self,
        message: str,
        location: Optional[str] = None,
        details: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        recovery_commands: Optional[list[str]] = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.QUERY,
            location=location,
            details=details,
            suggestions=suggestions,
            recovery_commands=recovery_commands,
        )


class FindingsError(VKGError):
    """Error in findings management."""

    def __init__(
        self,
        message: str,
        location: Optional[str] = None,
        details: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        recovery_commands: Optional[list[str]] = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.FINDINGS,
            location=location,
            details=details,
            suggestions=suggestions,
            recovery_commands=recovery_commands,
        )


class ConfigError(VKGError):
    """Error in configuration."""

    def __init__(
        self,
        message: str,
        location: Optional[str] = None,
        details: Optional[str] = None,
        suggestions: Optional[list[str]] = None,
        recovery_commands: Optional[list[str]] = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIG,
            location=location,
            details=details,
            suggestions=suggestions,
            recovery_commands=recovery_commands,
        )


# Common error factory functions for consistent messaging


def graph_not_found_error(graph_path: str) -> BuildError:
    """Create error for missing graph file."""
    return BuildError(
        message="Knowledge graph not found",
        location=graph_path,
        details="VKG requires a built graph to analyze. The graph file does not exist.",
        suggestions=[
            "Build the graph first using 'vkg build'",
            "Check the graph path is correct",
            "Ensure you're in the project root directory",
        ],
        recovery_commands=[
            "vkg build contracts/",
            "vkg build src/",
        ],
    )


def no_contracts_error(path: str) -> BuildError:
    """Create error for no contracts found."""
    return BuildError(
        message="No Solidity contracts found",
        location=path,
        details="No .sol files were found in the target directory.",
        suggestions=[
            "Check the path points to your contracts directory",
            "Ensure the directory contains .sol files",
            "Try specifying a different path",
        ],
        recovery_commands=[
            f"ls {path}",
            "find . -name '*.sol'",
            "vkg build src/",
        ],
    )


def compilation_error(details: str) -> BuildError:
    """Create error for Solidity compilation failure."""
    return BuildError(
        message="Solidity compilation failed",
        details=details,
        suggestions=[
            "Check for syntax errors in your contracts",
            "Ensure all dependencies are installed",
            "Try specifying a compatible solc version",
        ],
        recovery_commands=[
            "forge build",
            "npm install",
            "vkg build --solc 0.8.19 contracts/",
        ],
    )


def finding_not_found_error(finding_id: str) -> FindingsError:
    """Create error for missing finding."""
    return FindingsError(
        message=f"Finding not found: {finding_id}",
        details="The specified finding ID does not exist in the findings store.",
        suggestions=[
            "Check the finding ID is correct (format: VKG-XXXXXXXX)",
            "List available findings to see valid IDs",
            "Run analysis if findings are empty",
        ],
        recovery_commands=[
            "vkg findings list",
            "vkg analyze",
        ],
    )


def invalid_status_error(status: str, valid_statuses: list[str]) -> FindingsError:
    """Create error for invalid finding status."""
    return FindingsError(
        message=f"Invalid status: {status}",
        details=f"Valid statuses are: {', '.join(valid_statuses)}",
        suggestions=[
            "Use one of the valid status values",
            "Check the command syntax",
        ],
        recovery_commands=[
            "vkg findings update <id> --status pending",
            "vkg findings update <id> --status confirmed",
        ],
    )


def no_findings_error() -> AnalysisError:
    """Create error/warning for no findings detected."""
    return AnalysisError(
        message="No vulnerabilities detected",
        details="Analysis completed but found no matching patterns.",
        suggestions=[
            "This could mean the contracts are secure",
            "Try running with different patterns",
            "Check if the graph was built correctly",
        ],
        recovery_commands=[
            "vkg query 'functions with external calls'",
            "vkg lens-report --lens Ordering",
        ],
    )


def query_syntax_error(query: str, details: str) -> QueryError:
    """Create error for invalid query syntax."""
    return QueryError(
        message="Invalid query syntax",
        location=query,
        details=details,
        suggestions=[
            "Check the query format",
            "Use natural language or VQL 2.0 syntax",
            "Refer to documentation for query examples",
        ],
        recovery_commands=[
            "vkg query 'public functions that write state'",
            "vkg query 'pattern:auth-001'",
            "vkg schema  # List available properties",
        ],
    )


# Build Failure Diagnostics (Task 3.12)


def slither_not_found_error() -> BuildError:
    """Create error when Slither is not installed."""
    return BuildError(
        message="Slither not found",
        details="VKG requires Slither for Solidity analysis. Slither is not installed or not in PATH.",
        suggestions=[
            "Install Slither via pip: pip install slither-analyzer",
            "Ensure Slither is in your PATH",
            "Check Python virtual environment is activated",
        ],
        recovery_commands=[
            "pip install slither-analyzer",
            "pipx install slither-analyzer",
            "which slither",
        ],
    )


def slither_version_error(current: str, required: str) -> BuildError:
    """Create error for incompatible Slither version."""
    return BuildError(
        message=f"Slither version incompatible: {current}",
        details=f"VKG requires Slither version {required} or higher.",
        suggestions=[
            f"Upgrade Slither to version {required} or higher",
            "Check for breaking changes in release notes",
        ],
        recovery_commands=[
            "pip install --upgrade slither-analyzer",
            "slither --version",
        ],
    )


def solc_not_found_error(required_version: Optional[str] = None) -> BuildError:
    """Create error when solc compiler is not available."""
    version_info = f" (version {required_version} required)" if required_version else ""
    return BuildError(
        message=f"Solidity compiler (solc) not found{version_info}",
        details="VKG needs solc to compile contracts. The compiler is missing or the required version is not installed.",
        suggestions=[
            "Install solc via solc-select: pip install solc-select",
            "Use a Solidity version manager to install the required version",
            "If using Foundry, ensure forge build works first",
        ],
        recovery_commands=[
            "pip install solc-select && solc-select install 0.8.20",
            "solc-select use 0.8.20",
            "forge build",
        ],
    )


def import_resolution_error(import_path: str, contract_file: str) -> BuildError:
    """Create error for unresolved imports."""
    return BuildError(
        message=f"Cannot resolve import: {import_path}",
        location=contract_file,
        details=f"The import '{import_path}' in '{contract_file}' could not be resolved.",
        suggestions=[
            "Install missing dependencies (npm install or forge install)",
            "Check the import path matches your project structure",
            "Use remappings in foundry.toml or .solhint.json",
            "Ensure node_modules or lib/ contains the dependency",
        ],
        recovery_commands=[
            "npm install",
            "forge install",
            "cat foundry.toml  # Check remappings",
            f"ls node_modules/{import_path.split('/')[0]}",
        ],
    )


def pragma_version_error(contract_file: str, pragma: str, available: list[str]) -> BuildError:
    """Create error for unsatisfied pragma requirements."""
    available_str = ", ".join(available[:5]) + ("..." if len(available) > 5 else "")
    return BuildError(
        message=f"Pragma version {pragma} not satisfied",
        location=contract_file,
        details=f"Contract requires {pragma} but no compatible solc version is installed. Available: {available_str}",
        suggestions=[
            "Install a compatible solc version",
            "Update the contract's pragma to match available versions",
            "Use solc-select to manage multiple versions",
        ],
        recovery_commands=[
            f"solc-select install {pragma.replace('^', '').replace('>=', '')}",
            "solc-select versions",
            "forge build --use 0.8.20",
        ],
    )


def circular_import_error(cycle: list[str]) -> BuildError:
    """Create error for circular import dependencies."""
    cycle_display = " → ".join(cycle)
    return BuildError(
        message="Circular import detected",
        details=f"Import cycle: {cycle_display}",
        suggestions=[
            "Break the circular dependency by extracting shared code",
            "Use interface contracts to decouple dependencies",
            "Consider restructuring your contract hierarchy",
        ],
        recovery_commands=[
            "# Review the import structure in these files:",
            *[f"head -20 {f}" for f in cycle[:3]],
        ],
    )


def parse_error(contract_file: str, line: int, message: str) -> BuildError:
    """Create error for Solidity parse failures."""
    return BuildError(
        message="Solidity parse error",
        location=f"{contract_file}:{line}",
        details=message,
        suggestions=[
            "Check for syntax errors at the specified location",
            "Ensure matching braces, parentheses, and semicolons",
            "Verify function and contract declarations",
        ],
        recovery_commands=[
            f"cat -n {contract_file} | head -{line + 5} | tail -10",
            "forge build 2>&1 | head -20",
        ],
    )


# Proxy Resolution Warnings (Task 3.13)


class ProxyWarning:
    """
    Warning for proxy-related analysis limitations.

    Philosophy: "Never silent about proxy contracts"
    VKG should always inform the user when proxy detection may be incomplete.
    """

    def __init__(
        self,
        message: str,
        contract: str,
        proxy_type: Optional[str] = None,
        impact: str = "",
        recommendations: Optional[list[str]] = None,
    ) -> None:
        self.message = message
        self.contract = contract
        self.proxy_type = proxy_type
        self.impact = impact
        self.recommendations = recommendations or []

    def format_cli(self) -> str:
        """Format warning for CLI output."""
        lines = [
            f"Warning: {self.message}",
            f"Contract: {self.contract}",
        ]
        if self.proxy_type:
            lines.append(f"Proxy Type: {self.proxy_type}")
        if self.impact:
            lines.append("")
            lines.append(f"Impact: {self.impact}")
        if self.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"  {i}. {rec}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "warning": True,
            "message": self.message,
            "contract": self.contract,
            "proxy_type": self.proxy_type,
            "impact": self.impact,
            "recommendations": self.recommendations,
        }


def proxy_detected_warning(
    contract: str,
    proxy_type: str,
    implementation_found: bool = False,
) -> ProxyWarning:
    """Create warning when a proxy contract is detected."""
    if implementation_found:
        return ProxyWarning(
            message=f"Proxy contract detected with implementation",
            contract=contract,
            proxy_type=proxy_type,
            impact="Analysis includes both proxy and implementation. "
                   "Some vulnerabilities may span both contracts.",
            recommendations=[
                "Review proxy-specific vulnerabilities (storage collision, initializer)",
                "Check implementation access controls",
                "Verify upgrade mechanism security",
            ],
        )
    else:
        return ProxyWarning(
            message=f"Proxy contract detected without implementation",
            contract=contract,
            proxy_type=proxy_type,
            impact="Implementation contract not available. "
                   "Analysis is INCOMPLETE - only proxy logic analyzed.",
            recommendations=[
                "Provide implementation contract source code",
                "If using etherscan, include implementation address",
                "Run `vkg build --follow-proxy <proxy_address>` to fetch implementation",
            ],
        )


def unresolved_implementation_warning(
    proxy_contract: str,
    impl_address: Optional[str] = None,
) -> ProxyWarning:
    """Create warning when proxy implementation cannot be resolved."""
    addr_info = f" at {impl_address}" if impl_address else ""
    return ProxyWarning(
        message=f"Cannot resolve proxy implementation{addr_info}",
        contract=proxy_contract,
        proxy_type="unknown",
        impact="Vulnerability detection is INCOMPLETE. "
               "Implementation functions are not analyzed.",
        recommendations=[
            "Provide implementation source code in the build path",
            "Check if implementation is verified on block explorer",
            "Use --impl-source flag to specify implementation source",
            "For local testing, deploy and verify implementation",
        ],
    )


def storage_collision_warning(
    proxy_contract: str,
    impl_contract: str,
    colliding_slots: list[str],
) -> ProxyWarning:
    """Create warning for potential storage collision between proxy and impl."""
    slots_display = ", ".join(colliding_slots[:5])
    if len(colliding_slots) > 5:
        slots_display += f" (+{len(colliding_slots) - 5} more)"
    return ProxyWarning(
        message="Potential storage collision detected",
        contract=proxy_contract,
        proxy_type="upgradeable",
        impact=f"Storage slots {slots_display} may conflict between "
               f"{proxy_contract} and {impl_contract}. "
               "This can cause data corruption on upgrade.",
        recommendations=[
            "Use OpenZeppelin storage gaps pattern",
            "Verify EIP-1967 storage slots are used",
            "Review storage layout of both contracts",
            "Consider using diamond storage pattern",
        ],
    )


def delegatecall_to_unknown_warning(
    contract: str,
    function: str,
    target_expression: str,
) -> ProxyWarning:
    """Create warning for delegatecall to dynamic/unknown target."""
    return ProxyWarning(
        message=f"Delegatecall to dynamic target in {function}",
        contract=contract,
        proxy_type="dynamic",
        impact=f"Target address computed from: {target_expression}. "
               "VKG cannot analyze the target contract. "
               "This may hide critical vulnerabilities.",
        recommendations=[
            "Ensure delegatecall target is trusted and verified",
            "Consider using a registry pattern with known implementations",
            "Add explicit target validation before delegatecall",
            "Provide list of possible targets via --known-impls flag",
        ],
    )


def initializer_not_found_warning(
    contract: str,
    expected_initializers: list[str],
) -> ProxyWarning:
    """Create warning when upgradeable contract lacks initializer."""
    expected = ", ".join(expected_initializers)
    return ProxyWarning(
        message="No initializer function found",
        contract=contract,
        proxy_type="upgradeable",
        impact=f"Expected initializer(s): {expected}. "
               "Upgradeable contracts should use initializers instead of constructors.",
        recommendations=[
            "Use OpenZeppelin Initializable pattern",
            "Add `initialize()` function with `initializer` modifier",
            "Ensure `_disableInitializers()` is called in constructor",
            "Review upgrade safety documentation",
        ],
    )


def multiple_implementations_warning(
    proxy_contract: str,
    implementations: list[str],
) -> ProxyWarning:
    """Create warning when proxy has multiple potential implementations."""
    impls = ", ".join(implementations)
    return ProxyWarning(
        message=f"Multiple implementations found for proxy",
        contract=proxy_contract,
        proxy_type="diamond/multi-facet",
        impact=f"Found implementations: {impls}. "
               "Analysis covers all implementations but may miss cross-facet interactions.",
        recommendations=[
            "Review function selector collisions across facets",
            "Check storage isolation between facets",
            "Verify facet upgrade permissions",
            "Consider diamond cut authorization logic",
        ],
    )
