"""BuildContext for dependency injection in VKG Builder.

This module provides the BuildContext dataclass that serves as a
dependency injection container for all builder modules, enabling
testability and shared state management.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.kg.builder.types import UnresolvedTarget
from alphaswarm_sol.kg.fingerprint import stable_node_id, stable_edge_id


@dataclass
class BuildContext:
    """Shared context for all builder modules.

    Provides dependency injection for testability and shared state
    across builder modules without tight coupling.

    Attributes:
        project_root: Root path of the project being analyzed.
        graph: The KnowledgeGraph being constructed.
        slither: Slither instance (Any to avoid import dependency).
        schema_version: Graph schema version for deterministic IDs.
        exclude_dependencies: Whether to exclude dependency contracts.
        include_internal_calls: Whether to include internal call edges.
        contract_cache: Cache mapping contract names to Slither objects.
        function_cache: Cache mapping function IDs to Slither objects.
        source_cache: Cache mapping file paths to source lines.
        unresolved_targets: List of call targets that couldn't be resolved.
        warnings: List of non-fatal warnings encountered during build.
        logger: Structlog logger instance.
    """

    project_root: Path
    graph: KnowledgeGraph
    slither: Any  # Slither instance (using Any to avoid import dependency)

    # Schema version for deterministic IDs
    schema_version: str = "2.0"

    # Configuration
    exclude_dependencies: bool = True
    include_internal_calls: bool = True

    # Caches for cross-module access (populated during build)
    contract_cache: dict[str, Any] = field(default_factory=dict)
    function_cache: dict[str, Any] = field(default_factory=dict)
    source_cache: dict[str, list[str]] = field(default_factory=dict)

    # Completeness tracking (populated during build)
    unresolved_targets: list[UnresolvedTarget] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Logger (injected)
    logger: Any = field(default=None)  # structlog logger

    def __post_init__(self) -> None:
        """Initialize logger if not provided."""
        if self.logger is None:
            import structlog
            self.logger = structlog.get_logger()

    def node_id(
        self,
        kind: str,
        contract: str,
        name: str,
        signature: str | None = None,
    ) -> str:
        """Generate a stable, deterministic node ID.

        Delegates to fingerprint.stable_node_id for consistent ID generation
        across all builder modules. IDs are based on semantic content, not
        file paths, ensuring the same entity always gets the same ID.

        Args:
            kind: Node kind (e.g., 'function', 'contract', 'state_var').
            contract: Contract name.
            name: Entity name.
            signature: Optional function signature for disambiguation.

        Returns:
            A stable hash-based node ID in format "{kind}:{hash12}".

        Example:
            >>> ctx.node_id('function', 'Token', 'transfer', 'transfer(address,uint256)')
            'function:a9b652f2a6a1'
        """
        return stable_node_id(
            kind, contract, name, signature,
            schema_version=self.schema_version,
        )

    def edge_id(
        self,
        edge_type: str,
        source: str,
        target: str,
        qualifier: str | None = None,
    ) -> str:
        """Generate a stable, deterministic edge ID.

        Delegates to fingerprint.stable_edge_id for consistent ID generation
        across all builder modules. IDs are based on edge relationship and
        endpoints, ensuring uniqueness for parallel edges via qualifier.

        Args:
            edge_type: Type of edge (e.g., 'CALLS', 'READS', 'WRITES').
            source: Source node ID.
            target: Target node ID.
            qualifier: Optional qualifier for multiple edges between same nodes.

        Returns:
            A stable hash-based edge ID in format "{edge_type}:{hash12}".

        Example:
            >>> ctx.edge_id('CALLS', 'function:abc123', 'function:def456')
            'CALLS:7890abcd1234'
        """
        return stable_edge_id(edge_type, source, target, qualifier=qualifier)

    def add_warning(self, msg: str) -> None:
        """Add a non-fatal warning to the build context.

        Args:
            msg: Warning message to record.
        """
        self.warnings.append(msg)
        self.logger.warning("build_warning", msg=msg)

    def add_unresolved(self, target: UnresolvedTarget) -> None:
        """Track an unresolved call target.

        Args:
            target: UnresolvedTarget instance with details.
        """
        self.unresolved_targets.append(target)
        self.logger.debug(
            "unresolved_target",
            source=target.source_function,
            target_expr=target.target_expression,
            reason=target.reason,
        )

    def get_source_lines(self, file_path: str) -> list[str]:
        """Get source lines for a file, with caching.

        Args:
            file_path: Path to the source file.

        Returns:
            List of source lines (empty list if file not found).
        """
        if file_path not in self.source_cache:
            try:
                path = Path(file_path)
                if path.exists():
                    self.source_cache[file_path] = path.read_text().splitlines()
                else:
                    self.source_cache[file_path] = []
            except (OSError, UnicodeDecodeError) as e:
                self.add_warning(f"Could not read source file {file_path}: {e}")
                self.source_cache[file_path] = []

        return self.source_cache[file_path]

    def get_source_snippet(
        self,
        file_path: str,
        line_start: int,
        line_end: int | None = None,
    ) -> str:
        """Get a snippet of source code.

        Args:
            file_path: Path to the source file.
            line_start: Starting line (1-indexed).
            line_end: Ending line (1-indexed, inclusive). Defaults to line_start.

        Returns:
            Source code snippet, or empty string if unavailable.
        """
        lines = self.get_source_lines(file_path)
        if not lines:
            return ""

        if line_end is None:
            line_end = line_start

        # Convert to 0-indexed
        start_idx = max(0, line_start - 1)
        end_idx = min(len(lines), line_end)

        return "\n".join(lines[start_idx:end_idx])

    def cache_contract(self, contract: Any) -> None:
        """Cache a contract object by name.

        Args:
            contract: Slither contract object.
        """
        name = getattr(contract, "name", str(contract))
        self.contract_cache[name] = contract

    def cache_function(self, func: Any, node_id: str) -> None:
        """Cache a function object by node ID.

        Args:
            func: Slither function object.
            node_id: The node ID for this function in the graph.
        """
        self.function_cache[node_id] = func

    def get_build_stats(self) -> dict[str, Any]:
        """Get statistics about the current build.

        Returns:
            Dictionary with build statistics.
        """
        return {
            "nodes": len(self.graph.nodes),
            "edges": len(self.graph.edges),
            "rich_edges": len(self.graph.rich_edges),
            "contracts_cached": len(self.contract_cache),
            "functions_cached": len(self.function_cache),
            "source_files_cached": len(self.source_cache),
            "unresolved_targets": len(self.unresolved_targets),
            "warnings": len(self.warnings),
        }
