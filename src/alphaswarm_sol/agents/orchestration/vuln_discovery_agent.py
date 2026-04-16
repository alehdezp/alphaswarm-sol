"""Vuln-discovery agent for converting context beads to finding beads.

VulnDiscoveryAgent consumes ContextMergeBead (verified context bundles) and
produces FindingBeads (vulnerability findings with full evidence chains) by:
1. Loading the VKG for the target scope
2. Executing VQL queries from the context bundle
3. Analyzing results to extract findings with evidence
4. Creating finding beads via FindingBeadFactory
5. Linking findings back to the context bead

Per 05.5-06 plan requirements:
- Agent receives context from ContextMergeBead
- Produces findings with full evidence chain (code locations, vulndoc ref, reasoning)
- Uses VQL queries to search graph for evidence
- Findings created via FindingBeadFactory
- Context bead status transitions: PENDING -> IN_PROGRESS -> COMPLETE/FAILED

Usage:
    from alphaswarm_sol.agents.orchestration import VulnDiscoveryAgent, VulnDiscoveryConfig
    from alphaswarm_sol.beads.context_merge import ContextMergeBead

    # Configure agent
    config = VulnDiscoveryConfig(
        max_findings_per_context=10,
        min_confidence_to_report="uncertain",
        graph_path="/path/to/graph.json"
    )

    # Create agent with factory
    agent = VulnDiscoveryAgent(finding_factory, config)

    # Execute discovery
    result = agent.execute(context_bead, graph=None)

    print(f"Found {result.findings_count} findings")
    print(f"VQL queries executed: {result.vql_queries_executed}")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from alphaswarm_sol.beads.context_merge import ContextMergeBead, ContextBeadStatus
from alphaswarm_sol.beads.types import Severity
from alphaswarm_sol.kg.builder import VKGBuilder
from alphaswarm_sol.kg.schema import KnowledgeGraph
from alphaswarm_sol.queries.executor import QueryExecutor
from alphaswarm_sol.queries.planner import QueryPlanner

from .finding_factory import (
    FindingBeadFactory,
    FindingInput,
    EvidenceChain,
)


@dataclass
class VulnDiscoveryConfig:
    """Configuration for vuln-discovery agent.

    Attributes:
        max_findings_per_context: Max findings to create per context bead
        min_confidence_to_report: Minimum confidence level to report
        graph_path: Optional path to pre-built graph (else builds from scope)
    """
    max_findings_per_context: int = 10
    min_confidence_to_report: str = "uncertain"  # uncertain, likely, confirmed
    graph_path: Optional[Path] = None


@dataclass
class VulnDiscoveryResult:
    """Result of vuln-discovery execution.

    Attributes:
        success: Whether execution succeeded
        context_bead_id: ID of processed context bead
        findings: List of finding bead IDs created
        findings_count: Number of findings created
        errors: List of error messages
        vql_queries_executed: List of VQL queries executed
    """
    success: bool
    context_bead_id: str
    findings: List[str] = field(default_factory=list)
    findings_count: int = 0
    errors: List[str] = field(default_factory=list)
    vql_queries_executed: List[str] = field(default_factory=list)


class VulnDiscoveryAgent:
    """Agent for discovering vulnerabilities from context beads.

    Consumes ContextMergeBead (verified context bundles) and produces
    FindingBeads via VQL graph queries and evidence analysis.

    Attributes:
        finding_factory: Factory for creating finding beads
        config: Agent configuration
    """

    # Confidence threshold ordering
    CONFIDENCE_ORDER = {
        "rejected": 0,
        "uncertain": 1,
        "likely": 2,
        "confirmed": 3,
    }

    def __init__(
        self,
        finding_factory: FindingBeadFactory,
        config: VulnDiscoveryConfig,
    ):
        """Initialize agent.

        Args:
            finding_factory: Factory for creating finding beads
            config: Agent configuration
        """
        self.finding_factory = finding_factory
        self.config = config
        self.query_planner = QueryPlanner()
        self.query_executor = QueryExecutor()

    def execute(
        self,
        context_bead: ContextMergeBead,
        graph: Optional[KnowledgeGraph] = None,
    ) -> VulnDiscoveryResult:
        """Execute vuln-discovery for a context bead.

        Workflow:
        1. Mark context bead IN_PROGRESS
        2. Extract prompts from context bead
        3. Load or use provided graph
        4. Execute VQL queries from context bundle
        5. Analyze results, create findings
        6. Save finding beads, link to context
        7. Mark context bead COMPLETE

        Args:
            context_bead: ContextMergeBead to process
            graph: Optional pre-built graph (else loads from target_scope)

        Returns:
            VulnDiscoveryResult with findings and execution details
        """
        # Mark context bead as in-progress
        context_bead.status = ContextBeadStatus.IN_PROGRESS

        result = VulnDiscoveryResult(
            success=False,
            context_bead_id=context_bead.id,
        )

        try:
            # Extract context
            system_prompt = context_bead.get_system_prompt()
            user_context = context_bead.get_user_context()

            # Load graph if not provided
            if graph is None:
                graph = self._load_graph(context_bead.target_scope)

            # Execute VQL queries
            vql_queries = context_bead.context_bundle.vql_queries
            vql_results = []

            for query in vql_queries:
                # Parse and execute query (errors propagate to outer try-catch)
                query_result = self._execute_vql(query, graph)
                vql_results.append({
                    "query": query,
                    "results": query_result,
                })
                result.vql_queries_executed.append(query)

            # Analyze results and create findings
            findings = self._analyze_results(
                context_bead,
                vql_results,
                system_prompt,
                user_context,
            )

            # Create finding beads
            for finding_input in findings[:self.config.max_findings_per_context]:
                try:
                    # Create finding bead
                    bead = self.finding_factory.create_finding(
                        finding_input,
                        context_bead,
                    )

                    # Save finding bead
                    self.finding_factory.save_finding(bead)

                    # Link to context bead
                    self.finding_factory.link_to_context_bead(bead, context_bead)

                    result.findings.append(bead.id)
                    result.findings_count += 1

                except Exception as e:
                    result.errors.append(f"Failed to create finding: {e}")

            # Mark context bead as complete
            context_bead.mark_complete()
            result.success = True

        except Exception as e:
            # Mark context bead as failed
            context_bead.mark_failed(str(e))
            result.errors.append(str(e))

        return result

    def _load_graph(self, target_scope: List[str]) -> KnowledgeGraph:
        """Load VKG from target scope.

        Args:
            target_scope: List of contract files to analyze

        Returns:
            Built KnowledgeGraph

        Raises:
            ValueError: If target_scope is empty or files don't exist
        """
        if not target_scope:
            raise ValueError("Target scope is empty")

        # Use first file as entry point (VKGBuilder handles project detection)
        entry_point = Path(target_scope[0])
        if not entry_point.exists():
            raise ValueError(f"Target file does not exist: {entry_point}")

        # Build graph
        builder = VKGBuilder(entry_point.parent)
        graph = builder.build(entry_point)

        return graph

    def _execute_vql(
        self,
        query: str,
        graph: KnowledgeGraph,
    ) -> Dict[str, Any]:
        """Execute VQL query against graph.

        Args:
            query: VQL query string
            graph: KnowledgeGraph to query

        Returns:
            Query results dictionary

        Raises:
            Exception: If query execution fails
        """
        # Parse query into plan
        plan = self.query_planner.plan(query)

        # Execute plan
        result = self.query_executor.execute(graph, plan)

        return result

    def _analyze_results(
        self,
        context_bead: ContextMergeBead,
        vql_results: List[Dict[str, Any]],
        system_prompt: str,
        user_context: str,
    ) -> List[FindingInput]:
        """Analyze VQL results to extract findings.

        This is a simplified implementation that creates findings based on
        VQL query matches. In a full implementation, this would involve
        LLM analysis of the results.

        Args:
            context_bead: Context bead being processed
            vql_results: Results from VQL query execution
            system_prompt: System prompt from context bundle
            user_context: User context from context bundle

        Returns:
            List of FindingInput instances
        """
        findings = []

        for vql_result in vql_results:
            query = vql_result["query"]
            results = vql_result["results"]

            # Extract matches from results
            matches = results.get("matches", [])

            for match in matches:
                # Extract evidence from match
                node_id = match.get("node_id", "")
                if not node_id:
                    continue

                # Build evidence chain
                code_locations = [
                    f"{match.get('file_path', 'unknown')}:{match.get('line_number', 0)}"
                ]

                reasoning_steps = [
                    f"VQL query matched: {query}",
                    f"Found node: {node_id}",
                    f"Match details: {match.get('why_matched', 'No explanation')}",
                ]

                # Extract confidence from match or default to "uncertain"
                confidence = match.get("confidence", "uncertain")
                if not self._meets_confidence_threshold(confidence):
                    continue

                evidence_chain = EvidenceChain(
                    code_locations=code_locations,
                    vulndoc_reference=context_bead.vulnerability_class,
                    reasoning_steps=reasoning_steps,
                    vql_queries=[query],
                    protocol_context_applied=[
                        f"Protocol: {context_bead.protocol_name}",
                        f"Risk profile applied",
                    ],
                    confidence=confidence,
                    confidence_reason=f"VQL query matched with {confidence} confidence",
                )

                # Infer severity from vulnerability class
                severity = self._infer_severity(context_bead.vulnerability_class)

                # Create finding input
                finding = FindingInput(
                    vulnerability_class=context_bead.vulnerability_class,
                    severity=severity,
                    summary=match.get("description", f"Potential {context_bead.vulnerability_class} vulnerability"),
                    evidence_chain=evidence_chain,
                    context_bead_id=context_bead.id,
                    pool_id=context_bead.pool_id,
                )

                findings.append(finding)

        return findings

    def _infer_severity(self, vuln_class: str) -> Severity:
        """Infer severity from vulnerability class.

        Args:
            vuln_class: Vulnerability class (e.g., "reentrancy", "access-control")

        Returns:
            Severity level
        """
        # Map vulnerability classes to default severities
        severity_map = {
            "reentrancy": Severity.CRITICAL,
            "access-control": Severity.HIGH,
            "oracle": Severity.HIGH,
            "flash-loan": Severity.CRITICAL,
            "upgrade": Severity.HIGH,
            "arithmetic": Severity.MEDIUM,
            "denial-of-service": Severity.MEDIUM,
            "front-running": Severity.MEDIUM,
            "weak-randomness": Severity.HIGH,
        }

        # Extract base category from vuln_class
        base_category = vuln_class.split("/")[0] if "/" in vuln_class else vuln_class
        base_category = base_category.lower().replace("_", "-")

        return severity_map.get(base_category, Severity.MEDIUM)

    def _meets_confidence_threshold(self, confidence: str) -> bool:
        """Check if confidence meets minimum threshold.

        Args:
            confidence: Confidence level string

        Returns:
            True if confidence meets threshold
        """
        confidence_level = self.CONFIDENCE_ORDER.get(confidence.lower(), 0)
        threshold_level = self.CONFIDENCE_ORDER.get(
            self.config.min_confidence_to_report.lower(),
            1
        )

        return confidence_level >= threshold_level
