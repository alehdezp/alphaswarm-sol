"""Phase 20: Multi-Project Support.

This module provides functionality for managing multiple projects
and performing cross-project queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node


@dataclass
class ProjectInfo:
    """Information about a project.

    Attributes:
        id: Unique project identifier
        name: Project name
        path: Path to project
        graph: Knowledge graph for this project
        contracts: List of contract names
        metadata: Additional metadata
    """
    id: str
    name: str
    path: str = ""
    graph: Optional[KnowledgeGraph] = None
    contracts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_loaded(self) -> bool:
        """Check if project graph is loaded."""
        return self.graph is not None

    @property
    def contract_count(self) -> int:
        """Get number of contracts."""
        return len(self.contracts)

    @property
    def function_count(self) -> int:
        """Get number of functions."""
        if not self.graph:
            return 0
        return sum(1 for n in self.graph.nodes.values() if n.type == "Function")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "is_loaded": self.is_loaded,
            "contracts": self.contracts,
            "contract_count": self.contract_count,
            "function_count": self.function_count,
            "metadata": self.metadata,
        }


@dataclass
class CrossProjectQueryResult:
    """Result of a cross-project query.

    Attributes:
        query: The query that was executed
        results: Results by project ID
        total_matches: Total matches across all projects
    """
    query: str
    results: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    total_matches: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": self.results,
            "total_matches": self.total_matches,
            "project_count": len(self.results),
        }


class CrossProjectQuery:
    """Executes queries across multiple projects.

    Provides functionality to search for patterns and vulnerabilities
    across multiple project graphs.
    """

    def __init__(self, projects: List[ProjectInfo]):
        """Initialize with projects.

        Args:
            projects: List of projects to query
        """
        self.projects = {p.id: p for p in projects if p.is_loaded}

    def find_similar_functions(
        self,
        function_name: str,
    ) -> CrossProjectQueryResult:
        """Find functions with similar names across projects.

        Args:
            function_name: Function name to search for

        Returns:
            CrossProjectQueryResult with matches
        """
        result = CrossProjectQueryResult(query=f"similar:{function_name}")
        search_lower = function_name.lower()

        for project_id, project in self.projects.items():
            if not project.graph:
                continue

            matches: List[Dict[str, Any]] = []
            for node in project.graph.nodes.values():
                if node.type != "Function":
                    continue

                if search_lower in node.label.lower():
                    matches.append({
                        "function": node.label,
                        "contract": node.properties.get("contract_name", ""),
                        "visibility": node.properties.get("visibility", ""),
                        "properties": {
                            k: v for k, v in node.properties.items()
                            if isinstance(v, (bool, str, int, float))
                            and not k.startswith("_")
                        },
                    })

            if matches:
                result.results[project_id] = matches
                result.total_matches += len(matches)

        return result

    def find_vulnerable_patterns(
        self,
        pattern_type: str,
    ) -> CrossProjectQueryResult:
        """Find functions matching vulnerability patterns.

        Args:
            pattern_type: Type of vulnerability (reentrancy, access_control, etc.)

        Returns:
            CrossProjectQueryResult with matches
        """
        result = CrossProjectQueryResult(query=f"vulnerability:{pattern_type}")

        # Define pattern checks
        pattern_checks: Dict[str, Dict[str, Any]] = {
            "reentrancy": {
                "state_write_after_external_call": True,
                "has_reentrancy_guard": False,
            },
            "access_control": {
                "writes_privileged_state": True,
                "has_access_gate": False,
            },
            "oracle": {
                "reads_oracle_price": True,
                "has_staleness_check": False,
            },
            "dos": {
                "has_unbounded_loop": True,
            },
        }

        checks = pattern_checks.get(pattern_type, {})
        if not checks:
            return result

        for project_id, project in self.projects.items():
            if not project.graph:
                continue

            matches: List[Dict[str, Any]] = []
            for node in project.graph.nodes.values():
                if node.type != "Function":
                    continue

                # Check if function matches pattern
                matches_pattern = all(
                    node.properties.get(prop) == expected
                    for prop, expected in checks.items()
                )

                if matches_pattern:
                    matches.append({
                        "function": node.label,
                        "contract": node.properties.get("contract_name", ""),
                        "vulnerability": pattern_type,
                        "visibility": node.properties.get("visibility", ""),
                    })

            if matches:
                result.results[project_id] = matches
                result.total_matches += len(matches)

        return result

    def find_by_property(
        self,
        property_name: str,
        property_value: Any,
    ) -> CrossProjectQueryResult:
        """Find functions with a specific property value.

        Args:
            property_name: Property name
            property_value: Property value to match

        Returns:
            CrossProjectQueryResult with matches
        """
        result = CrossProjectQueryResult(
            query=f"property:{property_name}={property_value}"
        )

        for project_id, project in self.projects.items():
            if not project.graph:
                continue

            matches: List[Dict[str, Any]] = []
            for node in project.graph.nodes.values():
                if node.type != "Function":
                    continue

                if node.properties.get(property_name) == property_value:
                    matches.append({
                        "function": node.label,
                        "contract": node.properties.get("contract_name", ""),
                        property_name: property_value,
                    })

            if matches:
                result.results[project_id] = matches
                result.total_matches += len(matches)

        return result


class MultiProjectManager:
    """Manages multiple project graphs.

    Provides loading, unloading, and querying across multiple projects.
    """

    def __init__(self):
        """Initialize manager."""
        self._projects: Dict[str, ProjectInfo] = {}

    def add_project(self, project: ProjectInfo) -> None:
        """Add a project.

        Args:
            project: Project to add
        """
        self._projects[project.id] = project

    def remove_project(self, project_id: str) -> bool:
        """Remove a project.

        Args:
            project_id: Project ID

        Returns:
            True if project was removed
        """
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False

    def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            ProjectInfo or None
        """
        return self._projects.get(project_id)

    def list_projects(self) -> List[ProjectInfo]:
        """List all projects.

        Returns:
            List of projects
        """
        return list(self._projects.values())

    def load_graph(
        self,
        project_id: str,
        graph: KnowledgeGraph,
    ) -> bool:
        """Load a graph for a project.

        Args:
            project_id: Project ID
            graph: Knowledge graph to load

        Returns:
            True if graph was loaded
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        project.graph = graph

        # Update contract list
        contracts: Set[str] = set()
        for node in graph.nodes.values():
            if node.type == "Contract":
                contracts.add(node.label)
            elif node.type == "Function":
                contract_name = node.properties.get("contract_name")
                if contract_name:
                    contracts.add(contract_name)

        project.contracts = sorted(contracts)
        return True

    def unload_graph(self, project_id: str) -> bool:
        """Unload a project's graph.

        Args:
            project_id: Project ID

        Returns:
            True if graph was unloaded
        """
        project = self._projects.get(project_id)
        if not project:
            return False

        project.graph = None
        project.contracts = []
        return True

    def get_cross_project_query(self) -> CrossProjectQuery:
        """Get a cross-project query executor.

        Returns:
            CrossProjectQuery instance
        """
        return CrossProjectQuery(list(self._projects.values()))

    def get_total_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics across all projects.

        Returns:
            Dictionary of statistics
        """
        total_contracts = 0
        total_functions = 0
        loaded_projects = 0

        for project in self._projects.values():
            if project.is_loaded:
                loaded_projects += 1
                total_contracts += project.contract_count
                total_functions += project.function_count

        return {
            "total_projects": len(self._projects),
            "loaded_projects": loaded_projects,
            "total_contracts": total_contracts,
            "total_functions": total_functions,
        }


__all__ = [
    "ProjectInfo",
    "CrossProjectQueryResult",
    "CrossProjectQuery",
    "MultiProjectManager",
]
