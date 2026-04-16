"""State variable processing for VKG builder.

This module handles state variable node creation and property computation,
extracting logic from the legacy builder into a modular, testable form.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alphaswarm_sol.kg.heuristics import classify_state_var_name, is_privileged_state
from alphaswarm_sol.kg.schema import Edge, Evidence, Node
from alphaswarm_sol.kg.builder.context import BuildContext


@dataclass
class StateVarProperties:
    """Computed properties for a state variable node.

    All security-relevant properties derived from static analysis
    of a Solidity state variable.
    """

    name: str
    var_type: str | None
    visibility: str | None
    is_constant: bool = False
    is_immutable: bool = False
    is_mapping: bool = False
    is_array: bool = False
    security_tags: list[str] = field(default_factory=list)
    is_privileged: bool = False
    has_initializer: bool = False


class StateVarProcessor:
    """Process state variables and create their nodes.

    This class extracts state variable analysis from the legacy builder,
    using BuildContext for dependency injection and shared state.
    """

    def __init__(self, ctx: BuildContext) -> None:
        """Initialize processor with build context.

        Args:
            ctx: BuildContext for shared state and utilities.
        """
        self.ctx = ctx

    def process_all(self, contract: Any, contract_node: Node) -> list[Node]:
        """Process all state variables for a contract.

        Args:
            contract: Slither contract object.
            contract_node: Node representing the contract.

        Returns:
            List of nodes created for state variables.
        """
        nodes = []
        for var in getattr(contract, "state_variables", []) or []:
            node = self._process_var(var, contract, contract_node)
            nodes.append(node)
        return nodes

    def _process_var(self, var: Any, contract: Any, contract_node: Node) -> Node:
        """Process a single state variable.

        Args:
            var: Slither state variable object.
            contract: Slither contract object.
            contract_node: Node representing the contract.

        Returns:
            Node representing the state variable.
        """
        file_path, line_start, line_end = self._source_location(var)
        props = self._compute_properties(var)

        node_id = self._node_id(
            "state", f"{contract.name}.{var.name}", file_path, line_start
        )

        node = Node(
            id=node_id,
            type="StateVariable",
            label=var.name,
            properties={
                "type": props.var_type,
                "visibility": props.visibility,
                "is_constant": props.is_constant,
                "is_immutable": props.is_immutable,
                "is_mapping": props.is_mapping,
                "is_array": props.is_array,
                "security_tags": props.security_tags,
                "is_privileged": props.is_privileged,
                "has_initializer": props.has_initializer,
                "file": file_path,
                "line_start": line_start,
                "line_end": line_end,
            },
            evidence=self._evidence(file_path, line_start, line_end),
        )
        self.ctx.graph.add_node(node)

        # Add edge from contract to state variable
        self.ctx.graph.add_edge(
            Edge(
                id=self._edge_id("CONTAINS_STATE_VAR", contract_node.id, node_id),
                type="CONTAINS_STATE_VAR",
                source=contract_node.id,
                target=node_id,
                evidence=self._evidence(file_path, line_start, line_end),
            )
        )

        return node

    def _compute_properties(self, var: Any) -> StateVarProperties:
        """Compute properties for a state variable.

        Args:
            var: Slither state variable object.

        Returns:
            StateVarProperties with all computed values.
        """
        name = getattr(var, "name", "") or ""
        var_type = getattr(var, "type", None)
        type_str = str(var_type) if var_type is not None else None
        type_lower = (type_str or "").lower()

        visibility = getattr(var, "visibility", None)
        is_constant = getattr(var, "is_constant", False)
        is_immutable = getattr(var, "is_immutable", False)
        is_mapping = "mapping" in type_lower
        is_array = "[" in type_lower and not is_mapping

        security_tags = classify_state_var_name(name)
        is_privileged = is_privileged_state(security_tags)

        # Check if variable has an initializer expression
        expression = getattr(var, "expression", None) or getattr(var, "value", None)
        has_initializer = expression is not None

        return StateVarProperties(
            name=name,
            var_type=type_str,
            visibility=visibility,
            is_constant=is_constant,
            is_immutable=is_immutable,
            is_mapping=is_mapping,
            is_array=is_array,
            security_tags=security_tags,
            is_privileged=is_privileged,
            has_initializer=has_initializer,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _source_location(self, obj: Any) -> tuple[str, int | None, int | None]:
        """Extract source location from Slither object.

        Args:
            obj: Slither object with source_mapping.

        Returns:
            Tuple of (file_path, line_start, line_end).
        """
        source_mapping = getattr(obj, "source_mapping", None)
        if not source_mapping:
            return "unknown", None, None
        filename = (
            getattr(source_mapping, "filename_absolute", None)
            or getattr(source_mapping, "filename", None)
            or "unknown"
        )
        if hasattr(filename, "absolute"):
            filename = getattr(filename, "absolute")
        elif hasattr(filename, "used"):
            filename = getattr(filename, "used")
        file_path = self._relpath(str(filename))
        lines = getattr(source_mapping, "lines", None)
        if not lines:
            return file_path, None, None
        return file_path, min(lines), max(lines)

    def _relpath(self, filename: str) -> str:
        """Convert to relative path.

        Args:
            filename: Absolute filename.

        Returns:
            Relative path from project root.
        """
        try:
            return str(
                Path(filename).resolve().relative_to(self.ctx.project_root.resolve())
            )
        except Exception:
            return str(filename)

    def _node_id(
        self, kind: str, name: str, file_path: str | None, line_start: int | None
    ) -> str:
        """Generate a node ID using same hashing as legacy builder.

        Args:
            kind: Node kind.
            name: Entity name.
            file_path: Source file path.
            line_start: Start line.

        Returns:
            Generated node ID.
        """
        raw = f"{kind}:{name}:{file_path}:{line_start}"
        return f"{kind}:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"

    def _edge_id(self, edge_type: str, source: str, target: str) -> str:
        """Generate an edge ID.

        Args:
            edge_type: Type of edge.
            source: Source node ID.
            target: Target node ID.

        Returns:
            Generated edge ID.
        """
        raw = f"{edge_type}:{source}:{target}"
        return f"edge:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"

    def _evidence(
        self, file_path: str | None, line_start: int | None, line_end: int | None
    ) -> list[Evidence]:
        """Create evidence list for a location.

        Args:
            file_path: Source file path.
            line_start: Start line.
            line_end: End line.

        Returns:
            List of Evidence objects.
        """
        if not file_path or file_path == "unknown":
            return []
        return [Evidence(file=file_path, line_start=line_start, line_end=line_end)]


def process_state_variables(
    ctx: BuildContext, contract: Any, contract_node: Node
) -> list[Node]:
    """Convenience function to process state variables.

    Args:
        ctx: BuildContext for shared state.
        contract: Slither contract object.
        contract_node: Node representing the contract.

    Returns:
        List of nodes created for state variables.
    """
    processor = StateVarProcessor(ctx)
    return processor.process_all(contract, contract_node)


def classify_state_variables(state_vars: list[Any]) -> dict[str, list[str]]:
    """Classify state variables by their security tags.

    This is a utility function that can be used standalone without
    needing a full BuildContext.

    Args:
        state_vars: List of Slither state variable objects.

    Returns:
        Dictionary mapping variable names to security tags.
    """
    result: dict[str, list[str]] = {}
    for var in state_vars:
        name = getattr(var, "name", None) or ""
        if not name:
            continue
        tags = classify_state_var_name(name)
        result[name] = tags
    return result


def get_privileged_state_vars(state_vars: list[Any]) -> list[str]:
    """Get names of privileged state variables.

    Privileged state variables are those that control access,
    ownership, or critical protocol settings.

    Args:
        state_vars: List of Slither state variable objects.

    Returns:
        List of variable names that are privileged.
    """
    privileged = []
    for var in state_vars:
        name = getattr(var, "name", None) or ""
        if not name:
            continue
        tags = classify_state_var_name(name)
        if is_privileged_state(tags):
            privileged.append(name)
    return privileged
