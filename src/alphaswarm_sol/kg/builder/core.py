"""Core orchestration for VKG building.

This module provides the main entry point for building VKG knowledge graphs
from Solidity source code. It orchestrates the build process using modular
components with dependency injection via BuildContext.

The VKGBuilder class is the canonical entry point for all VKG construction.
It uses specialized processors:
- ContractProcessor: Contract nodes and properties
- StateVarProcessor: State variable nodes
- FunctionProcessor: Function nodes with 200+ emitted properties
- CallTracker: Call edges with confidence scoring
- ProxyResolver: Proxy pattern detection and resolution
- CompletenessReporter: Build quality metrics
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from alphaswarm_sol.kg.schema import KnowledgeGraph, Edge, Evidence, Node
from alphaswarm_sol.kg.builder.context import BuildContext
from alphaswarm_sol.kg.builder.contracts import ContractProcessor
from alphaswarm_sol.kg.builder.state_vars import StateVarProcessor
from alphaswarm_sol.kg.builder.functions import FunctionProcessor
from alphaswarm_sol.kg.builder.calls import CallTracker, CALLBACK_PATTERNS
from alphaswarm_sol.kg.builder.proxy import ProxyResolver
from alphaswarm_sol.kg.builder.completeness import CompletenessReporter, CompletenessReport
from alphaswarm_sol.kg.solc import select_solc_for_file
from alphaswarm_sol.kg.fingerprint import graph_fingerprint

# Slither import with graceful fallback
try:
    from slither import Slither
except Exception as exc:
    Slither = None  # type: ignore[assignment]
    _SLITHER_IMPORT_ERROR = exc
else:
    _SLITHER_IMPORT_ERROR = None


class VKGBuilder:
    """Construct a knowledge graph for a Solidity project.

    This modular builder orchestrates specialized processors for each
    aspect of the knowledge graph construction. All processors share
    state via BuildContext for dependency injection.

    Attributes:
        project_root: Root directory of the project being analyzed.
        exclude_dependencies: Whether to exclude external dependency contracts.
        generate_completeness_report: Whether to generate completeness report.
        logger: Structured logger for build events.

    Example:
        >>> from pathlib import Path
        >>> builder = VKGBuilder(Path("/path/to/project"))
        >>> graph = builder.build(Path("/path/to/project/contracts/Token.sol"))
        >>> print(f"Built graph with {len(graph.nodes)} nodes")
    """

    def __init__(
        self,
        project_root: Path,
        *,
        exclude_dependencies: bool = True,
        generate_completeness_report: bool = True,
    ) -> None:
        """Initialize the VKG builder.

        Args:
            project_root: Root directory of the project.
            exclude_dependencies: Whether to exclude external dependencies
                from the knowledge graph. Defaults to True.
            generate_completeness_report: Whether to generate completeness
                report after build. Defaults to True.
        """
        self.project_root = Path(project_root)
        self.exclude_dependencies = exclude_dependencies
        self.generate_completeness_report = generate_completeness_report
        self.logger = structlog.get_logger()
        self._last_report: CompletenessReport | None = None

    @property
    def last_completeness_report(self) -> CompletenessReport | None:
        """Get the completeness report from the last build."""
        return self._last_report

    def build(self, target: Path) -> KnowledgeGraph:
        """Build a knowledge graph from a Solidity target.

        This method orchestrates the complete build process:
        1. Initialize Slither analysis
        2. Create BuildContext for DI
        3. Process contracts, functions, state variables
        4. Generate edges (calls, reads, writes)
        5. Compute operations and behavioral signatures
        6. Generate rich edges and meta edges
        7. Classify nodes into semantic roles
        8. Generate completeness report

        Args:
            target: Path to Solidity file or directory to analyze.

        Returns:
            Complete KnowledgeGraph with all nodes, edges, and metadata.

        Raises:
            RuntimeError: If Slither is not available.
            Exception: If Slither analysis fails (compilation errors, etc.).
        """
        if Slither is None:
            raise RuntimeError(f"Slither is not available: {_SLITHER_IMPORT_ERROR}")

        self.logger.info(
            "vkg_build_start",
            target=str(target),
            project_root=str(self.project_root),
            exclude_dependencies=self.exclude_dependencies,
            builder="modular-2.0",
        )

        # Initialize Slither
        slither, selected_version = self._init_slither(target)

        # Initialize graph
        graph = self._init_graph(target, slither, selected_version)

        # Initialize build context
        ctx = BuildContext(
            project_root=self.project_root,
            graph=graph,
            slither=slither,
            exclude_dependencies=self.exclude_dependencies,
            logger=self.logger,
        )

        # Initialize processors
        contract_processor = ContractProcessor(ctx)
        state_var_processor = StateVarProcessor(ctx)
        function_processor = FunctionProcessor(ctx)
        call_tracker = CallTracker(ctx=ctx, graph=graph)
        proxy_resolver = ProxyResolver(ctx)

        # Process contracts in sorted order (determinism)
        contracts = sorted(
            getattr(slither, "contracts", []),
            key=lambda c: getattr(c, "name", "")
        )

        for contract in contracts:
            self._process_contract(
                ctx, graph, contract,
                contract_processor,
                state_var_processor,
                function_processor,
                call_tracker,
                proxy_resolver,
            )

        # Post-processing phases
        self._generate_rich_edges(graph)
        self._generate_meta_edges(graph)
        self._classify_nodes(graph)
        self._analyze_execution_paths(graph)

        # Generate completeness report
        if self.generate_completeness_report:
            reporter = CompletenessReporter(ctx)
            self._last_report = reporter.generate(graph)
            self.logger.info(
                "completeness_report",
                coverage=f"{self._last_report.coverage.function_coverage:.1%}",
                high_confidence=f"{self._last_report.confidence.high_percentage:.1f}%",
                warnings=len(self._last_report.warnings),
            )

        self.logger.info(
            "vkg_build_complete",
            nodes=len(graph.nodes),
            edges=len(graph.edges),
            rich_edges=len(graph.rich_edges),
            meta_edges=len(graph.meta_edges),
            fingerprint=graph_fingerprint(graph)[:16],
            builder="modular-2.0",
        )

        return graph

    def build_with_context(self, target: Path) -> tuple[KnowledgeGraph, BuildContext]:
        """Build a knowledge graph and return the build context.

        This method provides access to the BuildContext which contains
        additional information about the build process including warnings,
        unresolved targets, and caches.

        Args:
            target: Path to Solidity file or directory to analyze.

        Returns:
            Tuple of (KnowledgeGraph, BuildContext) with the graph and
            build metadata.

        Note:
            This method is intended for advanced use cases where access
            to build diagnostics is needed. For most uses, build() is
            sufficient.
        """
        if Slither is None:
            raise RuntimeError(f"Slither is not available: {_SLITHER_IMPORT_ERROR}")

        self.logger.info(
            "vkg_build_start",
            target=str(target),
            project_root=str(self.project_root),
            mode="with_context",
        )

        # Initialize Slither
        slither, selected_version = self._init_slither(target)

        # Initialize graph
        graph = self._init_graph(target, slither, selected_version)

        # Initialize build context
        ctx = BuildContext(
            project_root=self.project_root,
            graph=graph,
            slither=slither,
            exclude_dependencies=self.exclude_dependencies,
            logger=self.logger,
        )

        # Initialize processors
        contract_processor = ContractProcessor(ctx)
        state_var_processor = StateVarProcessor(ctx)
        function_processor = FunctionProcessor(ctx)
        call_tracker = CallTracker(ctx=ctx, graph=graph)
        proxy_resolver = ProxyResolver(ctx)

        # Process contracts in sorted order (determinism)
        contracts = sorted(
            getattr(slither, "contracts", []),
            key=lambda c: getattr(c, "name", "")
        )

        for contract in contracts:
            self._process_contract(
                ctx, graph, contract,
                contract_processor,
                state_var_processor,
                function_processor,
                call_tracker,
                proxy_resolver,
            )

        # Post-processing phases
        self._generate_rich_edges(graph)
        self._generate_meta_edges(graph)
        self._classify_nodes(graph)
        self._analyze_execution_paths(graph)

        # Generate completeness report
        if self.generate_completeness_report:
            reporter = CompletenessReporter(ctx)
            self._last_report = reporter.generate(graph)

        self.logger.info(
            "vkg_build_complete",
            nodes=len(graph.nodes),
            edges=len(graph.edges),
        )

        return graph, ctx

    def _init_slither(self, target: Path) -> tuple[Any, str | None]:
        """Initialize Slither with appropriate solc version.

        Args:
            target: Path to Solidity file or directory.

        Returns:
            Tuple of (Slither instance, selected solc version string or None).
        """
        slither_kwargs: dict[str, Any] = {"exclude_dependencies": self.exclude_dependencies}
        selected_version: str | None = None

        if target.is_file():
            solc_selection = select_solc_for_file(target)
            if solc_selection:
                solc_bin, selected_version = solc_selection
                slither_kwargs["solc"] = solc_bin
                self.logger.info(
                    "solc_selected",
                    target=str(target),
                    version=selected_version,
                )

        try:
            slither_instance = Slither(str(target), **slither_kwargs)
            return slither_instance, selected_version
        except Exception as exc:
            self.logger.error(
                "slither_init_failed",
                target=str(target),
                error=str(exc),
            )
            raise

    def _init_graph(
        self, target: Path, slither: Any, solc_version: str | None
    ) -> KnowledgeGraph:
        """Initialize empty knowledge graph with metadata.

        Args:
            target: Target path being analyzed.
            slither: Slither instance for version info.
            solc_version: Selected solc version.

        Returns:
            Fresh KnowledgeGraph with metadata populated.
        """
        return KnowledgeGraph(
            metadata={
                "root": str(self.project_root),
                "target": str(target),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "builder": "modular-2.0",
                "builder_version": "2.0.0",
                "slither_version": getattr(slither, "__version__", None),
                "solc_version_selected": solc_version,
                "exclude_dependencies": self.exclude_dependencies,
            }
        )

    def _process_contract(
        self,
        ctx: BuildContext,
        graph: KnowledgeGraph,
        contract: Any,
        contract_processor: ContractProcessor,
        state_var_processor: StateVarProcessor,
        function_processor: FunctionProcessor,
        call_tracker: CallTracker,
        proxy_resolver: ProxyResolver,
    ) -> None:
        """Process a single contract with all processors.

        Args:
            ctx: Build context.
            graph: Knowledge graph being built.
            contract: Slither contract object.
            contract_processor: Contract processor instance.
            state_var_processor: State variable processor instance.
            function_processor: Function processor instance.
            call_tracker: Call tracker instance.
            proxy_resolver: Proxy resolver instance.
        """
        # Skip interfaces if they snuck through
        if getattr(contract, "is_interface", False):
            return

        # Create contract node
        contract_node = contract_processor.process(contract)

        # Process inheritance
        contract_processor.process_inheritance(contract, contract_node)

        # Resolve proxy if applicable
        proxy_info = proxy_resolver.resolve(contract)
        if proxy_info.is_proxy:
            contract_node.properties["proxy_info"] = {
                "pattern": proxy_info.pattern.value if proxy_info.pattern else "unknown",
                "confidence": proxy_info.confidence,
                "implementation": proxy_info.implementation_contract,
                "evidence": proxy_info.evidence[:3] if proxy_info.evidence else [],  # Limit evidence
            }

        # Process state variables
        state_var_nodes = state_var_processor.process_all(contract, contract_node)

        # Add modifiers
        self._add_modifiers(graph, contract, contract_node)

        # Add events
        self._add_events(graph, contract, contract_node)

        # Process functions
        function_nodes = function_processor.process_all(contract, contract_node)

        # Add invariants
        invariants = self._add_invariants(graph, contract, contract_node)

        # Update functions with invariant info
        self._update_functions_for_invariants(graph, contract, invariants)

        # Annotate cross-function signals
        self._annotate_cross_function_signals(graph, contract)

        # Cache contract for later reference
        ctx.cache_contract(contract)

    def _add_modifiers(
        self, graph: KnowledgeGraph, contract: Any, contract_node: Node
    ) -> None:
        """Add modifier nodes and edges.

        Args:
            graph: Knowledge graph being built.
            contract: Slither contract object.
            contract_node: Contract node.
        """
        from alphaswarm_sol.kg.builder.helpers import source_location, evidence_from_location, relpath, node_id_hash, edge_id_hash

        for modifier in getattr(contract, "modifiers", []) or []:
            file_path, line_start, line_end = source_location(modifier)
            if file_path:
                file_path = relpath(file_path, self.project_root)

            name = getattr(modifier, "name", "modifier")
            node_id = node_id_hash("modifier", f"{contract.name}.{name}", file_path, line_start)

            node = Node(
                id=node_id,
                type="Modifier",
                label=name,
                properties={
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=evidence_from_location(file_path, line_start, line_end),
            )
            graph.add_node(node)

            edge = Edge(
                id=edge_id_hash("CONTAINS_MODIFIER", contract_node.id, node_id),
                type="CONTAINS_MODIFIER",
                source=contract_node.id,
                target=node_id,
            )
            graph.add_edge(edge)

    def _add_events(
        self, graph: KnowledgeGraph, contract: Any, contract_node: Node
    ) -> None:
        """Add event nodes and edges.

        Args:
            graph: Knowledge graph being built.
            contract: Slither contract object.
            contract_node: Contract node.
        """
        from alphaswarm_sol.kg.builder.helpers import source_location, evidence_from_location, relpath, node_id_hash, edge_id_hash

        for event in getattr(contract, "events", []) or []:
            file_path, line_start, line_end = source_location(event)
            if file_path:
                file_path = relpath(file_path, self.project_root)

            name = getattr(event, "name", "event")
            node_id = node_id_hash("event", f"{contract.name}.{name}", file_path, line_start)

            node = Node(
                id=node_id,
                type="Event",
                label=name,
                properties={
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                },
                evidence=evidence_from_location(file_path, line_start, line_end),
            )
            graph.add_node(node)

            edge = Edge(
                id=edge_id_hash("CONTAINS_EVENT", contract_node.id, node_id),
                type="CONTAINS_EVENT",
                source=contract_node.id,
                target=node_id,
            )
            graph.add_edge(edge)

    def _add_invariants(
        self, graph: KnowledgeGraph, contract: Any, contract_node: Node
    ) -> list[str]:
        """Add invariant nodes for supply tracking patterns.

        Args:
            graph: Knowledge graph.
            contract: Slither contract object.
            contract_node: Contract node.

        Returns:
            List of invariant IDs added.
        """
        from alphaswarm_sol.kg.builder.helpers import node_id_hash, edge_id_hash

        invariants = []

        # Check for totalSupply tracking pattern
        state_vars = getattr(contract, "state_variables", []) or []
        has_total_supply = any(
            "totalsupply" in getattr(var, "name", "").lower() or "supply" in getattr(var, "name", "").lower()
            for var in state_vars
        )
        has_balance = any(
            "balance" in getattr(var, "name", "").lower()
            for var in state_vars
        )

        if has_total_supply and has_balance:
            invariant_id = node_id_hash("invariant", contract.name, "total_supply_balance_sum", None)
            node = Node(
                id=invariant_id,
                type="Invariant",
                label="totalSupply == sum(balances)",
                properties={
                    "invariant_type": "sum_equality",
                    "description": "Total supply equals sum of all balances",
                },
            )
            graph.add_node(node)

            edge = Edge(
                id=edge_id_hash("HAS_INVARIANT", contract_node.id, invariant_id),
                type="HAS_INVARIANT",
                source=contract_node.id,
                target=invariant_id,
            )
            graph.add_edge(edge)

            invariants.append(invariant_id)

        return invariants

    def _update_functions_for_invariants(
        self, graph: KnowledgeGraph, contract: Any, invariants: list[str]
    ) -> None:
        """Update function nodes with invariant-breaking risk.

        Args:
            graph: Knowledge graph.
            contract: Slither contract object.
            invariants: List of invariant IDs.
        """
        if not invariants:
            return

        # Find function nodes for this contract
        contract_name = getattr(contract, "name", "")
        for node in graph.nodes.values():
            if node.type != "Function":
                continue
            # Check if function belongs to this contract
            file_path = node.properties.get("file", "")
            if not file_path:
                continue

            # Check if function modifies invariant-related state
            writes_balance = node.properties.get("writes_balance_state", False)
            writes_supply = node.properties.get("writes_supply_state", False)

            if writes_balance or writes_supply:
                node.properties["may_break_invariant"] = True
                node.properties["related_invariants"] = invariants

    def _annotate_cross_function_signals(
        self, graph: KnowledgeGraph, contract: Any
    ) -> None:
        """Annotate cross-function patterns (e.g., cross-function reentrancy).

        Args:
            graph: Knowledge graph.
            contract: Slither contract object.
        """
        # Find all functions that read balance state without writing
        # and all functions that write balance state
        # This detects cross-function reentrancy patterns

        contract_functions = []
        for node in graph.nodes.values():
            if node.type != "Function":
                continue
            contract_functions.append(node)

        readers = [n for n in contract_functions if n.properties.get("reads_balance_state")]
        writers = [n for n in contract_functions if n.properties.get("writes_balance_state")]

        for reader in readers:
            for writer in writers:
                if reader.id != writer.id:
                    # Mark both as having cross-function reentrancy surface
                    reader.properties["cross_function_reentrancy_read"] = True
                    writer.properties["cross_function_reentrancy_surface"] = True

    def _generate_rich_edges(self, graph: KnowledgeGraph) -> None:
        """Generate rich edges from function analysis.

        Rich edges contain additional intelligence metadata about
        function relationships (value flow, taint, risk scores).

        Args:
            graph: Knowledge graph to enhance.
        """
        from alphaswarm_sol.kg.rich_edge import create_rich_edge, EdgeType, TaintSource, ExecutionContext

        for node in graph.nodes.values():
            if node.type != "Function":
                continue

            props = node.properties
            visibility = props.get("visibility")
            if visibility not in ("public", "external"):
                continue

            # Create rich edges for external calls
            if props.get("has_external_calls"):
                try:
                    rich_edge = create_rich_edge(
                        source_node_id=node.id,
                        target_node_id=node.id,  # Self-reference for function analysis
                        edge_type=EdgeType.CALL,
                        label=f"{node.label} external_call",
                        taint_sources=[TaintSource.USER_PARAMETER] if props.get("has_user_input") else [],
                        execution_context=ExecutionContext.EXTERNAL_CALL if props.get("has_external_calls") else ExecutionContext.INTERNAL,
                        value_flow=props.get("has_call_with_value", False),
                    )
                    graph.add_rich_edge(rich_edge)
                except Exception:
                    pass  # Rich edge creation is optional enhancement

    def _generate_meta_edges(self, graph: KnowledgeGraph) -> None:
        """Generate meta edges (SIMILAR_TO, BUGGY_PATTERN_MATCH).

        Args:
            graph: Knowledge graph to enhance.
        """
        try:
            from alphaswarm_sol.kg.rich_edge import generate_meta_edges
            meta_edges = generate_meta_edges(graph)
            for meta_edge in meta_edges:
                graph.add_meta_edge(meta_edge)
        except Exception as exc:
            self.logger.warning("meta_edge_generation_failed", error=str(exc))

    def _classify_nodes(self, graph: KnowledgeGraph) -> None:
        """Classify nodes into semantic roles.

        Args:
            graph: Knowledge graph to classify.
        """
        try:
            from alphaswarm_sol.kg.classification import (
                NodeClassifier,
                classify_function_role,
                classify_state_variable_role,
            )

            classifier = NodeClassifier()
            for node in graph.nodes.values():
                if node.type == "Function":
                    role = classify_function_role(node)
                    if role:
                        # Handle both enum and string returns
                        node.properties["semantic_role"] = getattr(role, "value", role)
                elif node.type == "StateVariable":
                    role = classify_state_variable_role(node)
                    if role:
                        node.properties["semantic_role"] = getattr(role, "value", role)
        except Exception as exc:
            self.logger.warning("node_classification_failed", error=str(exc))

    def _analyze_execution_paths(self, graph: KnowledgeGraph) -> None:
        """Analyze execution paths for attack scenarios.

        Only runs for graphs with sufficient complexity.

        Args:
            graph: Knowledge graph to analyze.
        """
        # Only analyze if graph is large enough to be interesting
        if len(graph.nodes) < 10:
            return

        try:
            from alphaswarm_sol.kg.paths import PathEnumerator, generate_attack_scenarios

            enumerator = PathEnumerator(graph)
            scenarios = generate_attack_scenarios(graph)

            # Store summary in graph metadata
            graph.metadata["path_analysis"] = {
                "attack_scenarios_count": len(scenarios),
            }
        except Exception as exc:
            self.logger.debug("path_analysis_skipped", reason=str(exc))


def build_graph(
    target: Path,
    *,
    project_root: Path | None = None,
    exclude_dependencies: bool = True,
    generate_completeness_report: bool = True,
) -> KnowledgeGraph:
    """Convenience function to build a knowledge graph.

    This is the simplest way to build a VKG graph from a Solidity target.
    For more control, use VKGBuilder directly.

    Args:
        target: Path to Solidity file or directory to analyze.
        project_root: Root of the project. Defaults to target's parent
            directory if target is a file, or target itself if directory.
        exclude_dependencies: Whether to exclude external dependency
            contracts from the graph. Defaults to True.
        generate_completeness_report: Whether to generate completeness
            report after build. Defaults to True.

    Returns:
        Complete KnowledgeGraph with all nodes, edges, and metadata.

    Example:
        >>> from pathlib import Path
        >>> from alphaswarm_sol.kg.builder import build_graph
        >>> graph = build_graph(Path("contracts/Token.sol"))
        >>> print(f"Nodes: {len(graph.nodes)}, Edges: {len(graph.edges)}")
    """
    target = Path(target)

    if project_root is None:
        project_root = target.parent if target.is_file() else target
    else:
        project_root = Path(project_root)

    builder = VKGBuilder(
        project_root,
        exclude_dependencies=exclude_dependencies,
        generate_completeness_report=generate_completeness_report,
    )
    return builder.build(target)


def build_graph_with_context(
    target: Path,
    *,
    project_root: Path | None = None,
    exclude_dependencies: bool = True,
    generate_completeness_report: bool = True,
) -> tuple[KnowledgeGraph, BuildContext]:
    """Convenience function to build a graph with context.

    Similar to build_graph() but also returns the BuildContext for
    access to build diagnostics (warnings, unresolved targets, etc.).

    Args:
        target: Path to Solidity file or directory to analyze.
        project_root: Root of the project.
        exclude_dependencies: Whether to exclude dependencies.
        generate_completeness_report: Whether to generate report.

    Returns:
        Tuple of (KnowledgeGraph, BuildContext).

    Example:
        >>> graph, ctx = build_graph_with_context(Path("contracts/"))
        >>> if ctx.unresolved_targets:
        ...     print(f"Warning: {len(ctx.unresolved_targets)} unresolved calls")
    """
    target = Path(target)

    if project_root is None:
        project_root = target.parent if target.is_file() else target
    else:
        project_root = Path(project_root)

    builder = VKGBuilder(
        project_root,
        exclude_dependencies=exclude_dependencies,
        generate_completeness_report=generate_completeness_report,
    )
    return builder.build_with_context(target)
