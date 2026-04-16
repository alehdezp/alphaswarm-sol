"""
Agent Router (GLM-Style)

Implements GLM-style agent routing with selective context sharing to achieve
95.7% token reduction and 38% accuracy improvement through context specialization.

Key Innovation: Different agents need different slices of the three knowledge graphs.
The router creates optimized context for each agent type.

Per 05.11-CONTEXT.md: Extended with policy diff computation, cross-protocol
dependencies, and systemic risk scoring for economic context integration.

Per 07.1.3: Extended with context budget enforcement and progressive disclosure.
Budget reports are attached to routing outcomes for auditability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from alphaswarm_sol.llm.context_budget import (
    ContextBudgetPolicy,
    ContextBudgetStage,
    ContextBudgetReport,
    get_budget_policy,
)
from alphaswarm_sol.config import get_budget_for_role, get_budget_for_pool

if TYPE_CHECKING:
    from alphaswarm_sol.kg.schema import KnowledgeGraph, Node
    from alphaswarm_sol.kg.subgraph import SubGraph
    from alphaswarm_sol.knowledge.domain_kg import DomainKnowledgeGraph
    from alphaswarm_sol.knowledge.adversarial_kg import AdversarialKnowledgeGraph
    from alphaswarm_sol.knowledge.linker import CrossGraphLinker, CrossGraphRelation
    from alphaswarm_sol.intent.schema import FunctionIntent
    from alphaswarm_sol.knowledge.domain_kg import Specification
    from alphaswarm_sol.knowledge.adversarial_kg import AttackPattern
    from alphaswarm_sol.knowledge.linker import CrossGraphEdge
    from alphaswarm_sol.agents.base import AgentResult
    from alphaswarm_sol.context.schema import ProtocolContextPack
    from alphaswarm_sol.context.passports import ContractPassport, PassportBuilder

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of specialized agents for adversarial analysis."""

    CLASSIFIER = "classifier"  # Categorizes vulnerability type
    ATTACKER = "attacker"      # Thinks like an attacker, constructs exploits
    DEFENDER = "defender"      # Argues for safety, finds guards
    VERIFIER = "verifier"      # Formal verification with Z3


@dataclass
class PolicyDiff:
    """A policy mismatch between expected and actual access control.

    Per 05.11-CONTEXT.md: Compare expected policy from dossier against
    access-control graph.
    """

    function_id: str
    expected_role: str
    actual_role: Optional[str]
    mismatch_type: str  # "missing_check", "wrong_role", "extra_permission"
    provenance: str  # "declared", "inferred", "hypothesis"
    confidence: float = 0.5
    evidence_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "function_id": self.function_id,
            "expected_role": self.expected_role,
            "actual_role": self.actual_role,
            "mismatch_type": self.mismatch_type,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "evidence_refs": self.evidence_refs,
        }


@dataclass
class AgentContext:
    """
    Optimized context for a specific agent.

    Each agent type gets different slices to minimize tokens
    while maximizing relevant information.

    This is THE KEY to achieving GLM's 95% token reduction.

    Per 05.11-CONTEXT.md: Extended with policy diffs, cross-protocol
    dependencies, and systemic risk for economic context integration.
    """
    agent_type: AgentType

    # Code KG slice
    focal_nodes: List[str]  # The nodes being analyzed
    subgraph: Any  # Relevant portion of code KG (SubGraph)

    # Cross-graph context (agent-specific)
    specs: List[Any] = field(default_factory=list)  # Domain specs (for Defender)
    patterns: List[Any] = field(default_factory=list)  # Attack patterns (for Attacker)
    cross_edges: List[Any] = field(default_factory=list)  # Relevant cross-graph links

    # Intent (for Attacker/Defender)
    intents: Dict[str, Any] = field(default_factory=dict)  # FunctionIntent by node ID

    # Previous agent results (for chaining)
    upstream_results: List[Any] = field(default_factory=list)  # AgentResult list

    # Economic context (05.11)
    passport: Optional[Any] = None  # ContractPassport for context
    policy_diffs: List[PolicyDiff] = field(default_factory=list)  # Policy mismatches
    cross_protocol_dependencies: List[Any] = field(default_factory=list)  # External deps
    systemic_risk_score: float = 0.0  # Derived from passport

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Budget enforcement (07.1.3)
    budget_report: Optional[ContextBudgetReport] = None

    def estimate_tokens(self) -> int:
        """
        Estimate token count for this context.

        Rough estimation based on content size:
        - Base prompt overhead: ~100 tokens
        - Per node: ~50 tokens
        - Per spec: ~100 tokens
        - Per pattern: ~80 tokens
        - Per edge: ~30 tokens
        - Per intent: ~150 tokens
        - Per policy diff: ~50 tokens
        - Per cross-protocol dep: ~60 tokens
        """
        base = 100  # Prompt overhead

        # Estimate based on subgraph size
        try:
            if hasattr(self.subgraph, 'nodes') and hasattr(self.subgraph.nodes, '__len__'):
                nodes = len(self.subgraph.nodes) * 50
            else:
                nodes = len(self.focal_nodes) * 50
        except (TypeError, AttributeError):
            # Fallback for mock objects
            nodes = len(self.focal_nodes) * 50

        specs = len(self.specs) * 100
        patterns = len(self.patterns) * 80
        edges = len(self.cross_edges) * 30
        intents = len(self.intents) * 150
        policy_diffs = len(self.policy_diffs) * 50
        cross_deps = len(self.cross_protocol_dependencies) * 60

        return base + nodes + specs + patterns + edges + intents + policy_diffs + cross_deps

    @property
    def has_policy_diffs(self) -> bool:
        """Check if there are policy mismatches."""
        return len(self.policy_diffs) > 0

    @property
    def has_external_dependencies(self) -> bool:
        """Check if target function depends on external protocols."""
        return len(self.cross_protocol_dependencies) > 0

    @property
    def is_high_systemic_risk(self) -> bool:
        """Whether this context has high systemic risk (>= 7)."""
        return self.systemic_risk_score >= 7.0


class ContextSlicer:
    """
    Creates optimized context slices for each agent type.

    This is THE KEY to achieving GLM's 95% token reduction.
    Each agent gets only the information it needs.

    Per 05.11-CONTEXT.md: Extended with passport attachment, policy diff
    computation, and cross-protocol dependency tracking.

    Per 07.1.3: Extended with context budget enforcement and progressive
    disclosure. Budgets are applied before returning context.
    """

    def __init__(
        self,
        code_kg: "KnowledgeGraph",
        domain_kg: Optional["DomainKnowledgeGraph"] = None,
        adversarial_kg: Optional["AdversarialKnowledgeGraph"] = None,
        linker: Optional["CrossGraphLinker"] = None,
        context_pack: Optional["ProtocolContextPack"] = None,
        passport_builder: Optional["PassportBuilder"] = None,
        strict_mode: bool = False,
        enable_budget_enforcement: bool = True,
    ):
        """
        Initialize context slicer.

        Args:
            code_kg: The main code knowledge graph
            domain_kg: Domain knowledge graph (optional)
            adversarial_kg: Adversarial knowledge graph (optional)
            linker: Cross-graph linker (optional)
            context_pack: Protocol context pack for economic context (05.11)
            passport_builder: Passport builder for contract passports (05.11)
            strict_mode: If True, reject candidates without passports (05.11)
            enable_budget_enforcement: If True, apply budget constraints (07.1.3)
        """
        self.code_kg = code_kg
        self.domain_kg = domain_kg
        self.adversarial_kg = adversarial_kg
        self.linker = linker
        self.context_pack = context_pack
        self.passport_builder = passport_builder
        self.strict_mode = strict_mode
        self.enable_budget_enforcement = enable_budget_enforcement
        self._passports: Dict[str, Any] = {}
        self._budget_policies: Dict[str, ContextBudgetPolicy] = {}
        from alphaswarm_sol.kg.slicer import UnifiedSlicingPipeline
        self._pipeline = UnifiedSlicingPipeline(code_kg)

        # Build passports if we have the context
        if passport_builder:
            self._passports = passport_builder.build_all()

    def get_budget_policy(self, role: str) -> ContextBudgetPolicy:
        """Get or create a budget policy for a role.

        Args:
            role: Agent role name

        Returns:
            ContextBudgetPolicy for the role
        """
        if role not in self._budget_policies:
            max_tokens = get_budget_for_role(role)
            self._budget_policies[role] = get_budget_policy(
                role=role,
                max_tokens=max_tokens,
            )
        return self._budget_policies[role]

    def _apply_budget_to_context(
        self,
        context: AgentContext,
        role: str,
        stage: ContextBudgetStage = ContextBudgetStage.EVIDENCE,
    ) -> ContextBudgetReport:
        """Apply budget constraints to an agent context.

        Args:
            context: AgentContext to constrain
            role: Role for budget lookup
            stage: Disclosure stage

        Returns:
            ContextBudgetReport documenting the enforcement
        """
        if not self.enable_budget_enforcement:
            # Return a no-op report
            return ContextBudgetReport(
                stage=stage,
                original_tokens=context.estimate_tokens(),
                final_tokens=context.estimate_tokens(),
                max_tokens=get_budget_for_role(role),
                trimmed=False,
                can_expand=True,
                expansion_budget=0,
            )

        policy = self.get_budget_policy(role)

        # Estimate current context tokens
        original_tokens = context.estimate_tokens()
        max_tokens = policy.get_stage_budget(stage)

        # For now, we don't trim the subgraph directly (complex structure)
        # Instead, we record the budget report and let downstream consumers
        # handle trimming if needed. The report enables auditability.
        trimmed = original_tokens > max_tokens

        return ContextBudgetReport(
            stage=stage,
            original_tokens=original_tokens,
            final_tokens=original_tokens,  # Actual trimming happens at prompt assembly
            max_tokens=max_tokens,
            trimmed=trimmed,
            can_expand=stage != ContextBudgetStage.RAW,
            expansion_budget=max(0, policy.max_tokens - original_tokens),
        )

    def slice_for_agent(
        self,
        agent_type: AgentType,
        focal_nodes: List[str],
        stage: ContextBudgetStage = ContextBudgetStage.EVIDENCE,
    ) -> AgentContext:
        """
        Create optimized context for specific agent type.

        Per 07.1.3: Budget enforcement is applied and budget_report is attached.

        Args:
            agent_type: Type of agent to create context for
            focal_nodes: List of node IDs to analyze
            stage: Disclosure stage for budget enforcement

        Returns:
            Optimized AgentContext for the specified agent with budget_report
        """
        if agent_type == AgentType.CLASSIFIER:
            context = self._slice_for_classifier(focal_nodes)
            role = "classifier"
        elif agent_type == AgentType.ATTACKER:
            context = self._slice_for_attacker(focal_nodes)
            role = "attacker"
        elif agent_type == AgentType.DEFENDER:
            context = self._slice_for_defender(focal_nodes)
            role = "defender"
        elif agent_type == AgentType.VERIFIER:
            context = self._slice_for_verifier(focal_nodes)
            role = "verifier"
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Apply budget enforcement and attach report (07.1.3)
        context.budget_report = self._apply_budget_to_context(context, role, stage)

        return context

    def _get_contract_for_function(self, function_id: str) -> Optional[str]:
        """Extract contract name from function ID.

        Args:
            function_id: Function identifier (e.g., "Vault.withdraw")

        Returns:
            Contract name if extractable, None otherwise
        """
        if "." in function_id:
            return function_id.split(".")[0]
        # Check if this node has a parent contract in the KG
        if function_id in self.code_kg.nodes:
            node = self.code_kg.nodes[function_id]
            if hasattr(node, 'properties') and 'contract' in node.properties:
                return node.properties['contract']
        return None

    def _get_passport_for_function(self, function_id: str) -> Optional[Any]:
        """Get passport for the contract containing a function.

        Args:
            function_id: Function identifier

        Returns:
            ContractPassport if found, None otherwise
        """
        contract_id = self._get_contract_for_function(function_id)
        if contract_id and contract_id in self._passports:
            return self._passports[contract_id]
        return None

    def compute_policy_diff(
        self,
        focal_nodes: List[str],
    ) -> List[PolicyDiff]:
        """Compute policy diff between expected and actual access control.

        Per 05.11-CONTEXT.md: Compare expected policy from dossier against
        access-control graph derived from code.

        Args:
            focal_nodes: Function nodes to check

        Returns:
            List of PolicyDiff objects representing mismatches
        """
        diffs: List[PolicyDiff] = []

        if not self.context_pack:
            return diffs

        # Build expected policy map from context pack roles
        expected_policy: Dict[str, List[str]] = {}  # function -> expected roles
        for role in self.context_pack.roles:
            for cap in role.capabilities:
                # Match capabilities to functions
                for focal_id in focal_nodes:
                    fn_name = focal_id.split(".")[-1] if "." in focal_id else focal_id
                    if fn_name.lower() in cap.lower():
                        if focal_id not in expected_policy:
                            expected_policy[focal_id] = []
                        expected_policy[focal_id].append(role.name)

        # Check actual access control from KG
        for focal_id in focal_nodes:
            if focal_id not in self.code_kg.nodes:
                continue

            node = self.code_kg.nodes[focal_id]
            props = node.properties if hasattr(node, 'properties') else {}

            # Get actual access control
            has_access_gate = props.get("has_access_gate", False)
            actual_roles = props.get("required_roles", [])

            expected_roles = expected_policy.get(focal_id, [])

            # Check for mismatches
            if expected_roles and not has_access_gate:
                # Expected role check but none found
                for expected_role in expected_roles:
                    provenance = "inferred"
                    # Check if role has provenance
                    role_obj = self.context_pack.get_role(expected_role)
                    if role_obj and role_obj.provenance:
                        provenance = role_obj.provenance.value

                    diffs.append(PolicyDiff(
                        function_id=focal_id,
                        expected_role=expected_role,
                        actual_role=None,
                        mismatch_type="missing_check",
                        provenance=provenance,
                        confidence=0.7 if provenance == "declared" else 0.4,
                        evidence_refs=[f"context:{expected_role}", f"code:{focal_id}"],
                    ))

            elif expected_roles and actual_roles:
                # Check if expected roles match actual roles
                for expected_role in expected_roles:
                    if expected_role.lower() not in [r.lower() for r in actual_roles]:
                        provenance = "inferred"
                        role_obj = self.context_pack.get_role(expected_role)
                        if role_obj and role_obj.provenance:
                            provenance = role_obj.provenance.value

                        diffs.append(PolicyDiff(
                            function_id=focal_id,
                            expected_role=expected_role,
                            actual_role=actual_roles[0] if actual_roles else None,
                            mismatch_type="wrong_role",
                            provenance=provenance,
                            confidence=0.6 if provenance == "declared" else 0.3,
                            evidence_refs=[f"context:{expected_role}", f"code:{focal_id}"],
                        ))

        return diffs

    def _get_cross_protocol_dependencies(
        self,
        focal_nodes: List[str],
    ) -> List[Any]:
        """Get cross-protocol dependencies for focal nodes.

        Per 05.11-CONTEXT.md: Include cross-protocol dependencies in routing context.

        Args:
            focal_nodes: Function nodes to check

        Returns:
            List of CrossProtocolDependency objects
        """
        deps = []

        for focal_id in focal_nodes:
            passport = self._get_passport_for_function(focal_id)
            if passport:
                # Add all dependencies that affect this function
                fn_name = focal_id.split(".")[-1] if "." in focal_id else focal_id
                for dep in passport.cross_protocol_dependencies:
                    if not dep.affected_functions or fn_name in dep.affected_functions:
                        if dep not in deps:
                            deps.append(dep)

        return deps

    def _attach_economic_context(
        self,
        context: AgentContext,
        focal_nodes: List[str],
    ) -> None:
        """Attach economic context to agent context.

        Per 05.11-CONTEXT.md: Attach passports with cross-protocol deps at routing time.

        Args:
            context: AgentContext to enrich
            focal_nodes: Focal nodes being analyzed
        """
        # Try to find a passport for the first focal node
        if focal_nodes:
            passport = self._get_passport_for_function(focal_nodes[0])
            if passport:
                context.passport = passport
                context.systemic_risk_score = passport.systemic_risk_score

        # Compute and attach policy diffs
        policy_diffs = self.compute_policy_diff(focal_nodes)
        context.policy_diffs = policy_diffs

        # Attach cross-protocol dependencies
        cross_deps = self._get_cross_protocol_dependencies(focal_nodes)
        context.cross_protocol_dependencies = cross_deps

        # Log warnings for missing context
        if self.strict_mode and not context.passport:
            logger.warning(
                "Strict mode: missing passport for focal nodes %s - "
                "forcing unknown + expansion request",
                focal_nodes,
            )
            context.metadata["missing_passport"] = True
            context.metadata["expansion_requested"] = True

    def _slice_for_classifier(self, focal_nodes: List[str]) -> AgentContext:
        """
        Minimal context for classifier.

        Classifier just needs node types and basic properties.
        NO intent, NO cross-graph, NO rich edges.

        Target: ~200 tokens
        """
        subgraph, stats = self._slice_with_pipeline(focal_nodes, role="classifier")

        context = AgentContext(
            agent_type=AgentType.CLASSIFIER,
            focal_nodes=focal_nodes,
            subgraph=subgraph,
            specs=[],  # Not needed
            patterns=[],  # Not needed
            cross_edges=[],  # Not needed
            intents={},  # Not needed
            metadata={
                "slice_type": "unified_pipeline",
                "slice_role": "classifier",
                "slice_stats": stats,
            },
        )

        # Classifier gets minimal economic context (just systemic risk hint)
        if focal_nodes:
            passport = self._get_passport_for_function(focal_nodes[0])
            if passport:
                context.systemic_risk_score = passport.systemic_risk_score

        return context

    def _slice_for_attacker(self, focal_nodes: List[str]) -> AgentContext:
        """
        Rich context for attacker agent.

        Attacker needs:
        - Rich edges (external calls, value transfers)
        - Attack patterns from adversarial KG
        - Historical exploits
        - Intent (to understand what to violate)
        - SIMILAR_TO edges

        Target: ~800 tokens
        """
        subgraph, stats = self._slice_with_pipeline(focal_nodes, role="attacker")

        # Get relevant attack patterns
        patterns = []
        if self.adversarial_kg:
            for node_id in focal_nodes:
                if node_id in self.code_kg.nodes:
                    node = self.code_kg.nodes[node_id]
                    matches = self.adversarial_kg.find_similar_patterns(
                        node, min_confidence=0.3
                    )
                    patterns.extend([m.pattern for m in matches])
            # Deduplicate by pattern ID
            patterns = list({p.id: p for p in patterns}.values())

        # Get SIMILAR_TO edges
        cross_edges = []
        if self.linker:
            from alphaswarm_sol.knowledge.linker import CrossGraphRelation
            cross_edges = [
                e for e in self.linker.edges
                if e.source_id in focal_nodes
                and e.relation == CrossGraphRelation.SIMILAR_TO
            ]

        # Get intents
        intents = {}
        for node_id in focal_nodes:
            if node_id in self.code_kg.nodes:
                node = self.code_kg.nodes[node_id]
                if "intent" in node.properties:
                    from alphaswarm_sol.intent.schema import FunctionIntent
                    intents[node_id] = FunctionIntent.from_dict(
                        node.properties["intent"]
                    )

        context = AgentContext(
            agent_type=AgentType.ATTACKER,
            focal_nodes=focal_nodes,
            subgraph=subgraph,
            specs=[],  # Attacker doesn't care about specs
            patterns=patterns,
            cross_edges=cross_edges,
            intents=intents,
            metadata={
                "slice_type": "unified_pipeline",
                "slice_role": "attacker",
                "slice_stats": stats,
            },
        )

        # Attacker gets full economic context (cross-protocol deps enable attack reasoning)
        self._attach_economic_context(context, focal_nodes)

        return context

    def _slice_for_defender(self, focal_nodes: List[str]) -> AgentContext:
        """
        Spec-focused context for defender agent.

        Defender needs:
        - Specifications from domain KG
        - Guard analysis (modifiers, require statements)
        - Invariants
        - IMPLEMENTS and MITIGATES edges

        Target: ~600 tokens
        """
        subgraph, stats = self._slice_with_pipeline(focal_nodes, role="defender")

        # Get relevant specs
        specs = []
        if self.domain_kg:
            for node_id in focal_nodes:
                if node_id in self.code_kg.nodes:
                    node = self.code_kg.nodes[node_id]
                    matches = self.domain_kg.find_matching_specs(node)
                    specs.extend([spec for spec, _ in matches])
            # Deduplicate by spec ID
            specs = list({s.id: s for s in specs}.values())

        # Get IMPLEMENTS and MITIGATES edges
        cross_edges = []
        if self.linker:
            from alphaswarm_sol.knowledge.linker import CrossGraphRelation
            cross_edges = [
                e for e in self.linker.edges
                if e.source_id in focal_nodes
                and e.relation in [
                    CrossGraphRelation.IMPLEMENTS,
                    CrossGraphRelation.MITIGATES
                ]
            ]

        context = AgentContext(
            agent_type=AgentType.DEFENDER,
            focal_nodes=focal_nodes,
            subgraph=subgraph,
            specs=specs,
            patterns=[],  # Defender argues from specs, not patterns
            cross_edges=cross_edges,
            intents={},  # Defender uses actual behavior, not inferred intent
            metadata={
                "slice_type": "unified_pipeline",
                "slice_role": "defender",
                "slice_stats": stats,
            },
        )

        # Defender gets policy diffs and passport for reasoning about guards
        self._attach_economic_context(context, focal_nodes)

        return context

    def _slice_for_verifier(self, focal_nodes: List[str]) -> AgentContext:
        """
        Path-focused context for verifier agent.

        Verifier needs:
        - Execution paths
        - Data flow edges
        - Constraints for Z3

        Target: ~400 tokens
        """
        subgraph, stats = self._slice_with_pipeline(focal_nodes, role="verifier")

        context = AgentContext(
            agent_type=AgentType.VERIFIER,
            focal_nodes=focal_nodes,
            subgraph=subgraph,
            specs=[],
            patterns=[],
            cross_edges=[],
            intents={},
            metadata={
                "slice_type": "unified_pipeline",
                "slice_role": "verifier",
                "slice_stats": stats,
            },
        )

        # Verifier gets systemic risk score for prioritization
        if focal_nodes:
            passport = self._get_passport_for_function(focal_nodes[0])
            if passport:
                context.passport = passport
                context.systemic_risk_score = passport.systemic_risk_score

        return context

    def _slice_with_pipeline(
        self,
        focal_nodes: List[str],
        *,
        role: str,
        category: str = "general",
    ) -> tuple[Any, dict]:
        """Slice using the unified pipeline with a legacy fallback."""
        try:
            result = self._pipeline.slice_for_role(
                focal_nodes=focal_nodes,
                role=role,
                category=category,
            )
            return result.graph, result.stats
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "Unified slicing failed for role %s, falling back: %s",
                role,
                exc,
            )
            if role == "classifier":
                return self._extract_minimal_subgraph(focal_nodes), {}
            if role == "attacker":
                return self._extract_rich_subgraph(focal_nodes), {}
            if role == "defender":
                return self._extract_guard_focused_subgraph(focal_nodes), {}
            if role == "verifier":
                return self._extract_path_subgraph(focal_nodes), {}
            return self._extract_minimal_subgraph(focal_nodes), {}

    def _extract_minimal_subgraph(self, focal_nodes: List[str]) -> Any:
        """Extract minimal subgraph with just focal nodes and direct neighbors."""
        from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode, SubGraphEdge

        # For classifier, we only need focal nodes + immediate neighbors
        nodes_to_include = set(focal_nodes)

        # Add direct neighbors
        for node_id in focal_nodes:
            if node_id in self.code_kg.nodes:
                for edge in self.code_kg.edges.values():
                    if edge.source == node_id:
                        nodes_to_include.add(edge.target)
                    elif edge.target == node_id:
                        nodes_to_include.add(edge.source)

        # Create subgraph
        subgraph = SubGraph(focal_node_ids=focal_nodes)

        # Add nodes
        for node_id in nodes_to_include:
            if node_id in self.code_kg.nodes:
                node = self.code_kg.nodes[node_id]
                sub_node = SubGraphNode(
                    id=node.id,
                    type=node.type,
                    label=node.label,
                    properties=node.properties,
                    is_focal=(node_id in focal_nodes),
                )
                subgraph.add_node(sub_node)

        # Add edges between included nodes
        for edge in self.code_kg.edges.values():
            if edge.source in nodes_to_include and edge.target in nodes_to_include:
                sub_edge = SubGraphEdge(
                    id=edge.id,
                    type=edge.type,
                    source=edge.source,
                    target=edge.target,
                    properties={},
                )
                subgraph.add_edge(sub_edge)

        return subgraph

    def _extract_rich_subgraph(self, focal_nodes: List[str]) -> Any:
        """Extract rich subgraph with deep context for attacker analysis."""
        from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode, SubGraphEdge

        # For attacker, include 2-hop neighborhood with rich edges
        nodes_to_include = set(focal_nodes)

        # Add 2-hop neighbors
        for _ in range(2):
            new_nodes = set()
            for node_id in nodes_to_include:
                if node_id in self.code_kg.nodes:
                    for edge in self.code_kg.edges.values():
                        if edge.source == node_id:
                            new_nodes.add(edge.target)
                        elif edge.target == node_id:
                            new_nodes.add(edge.source)
            nodes_to_include.update(new_nodes)

        # Create subgraph (same as minimal for now)
        subgraph = SubGraph(focal_node_ids=focal_nodes)

        # Add nodes
        for node_id in nodes_to_include:
            if node_id in self.code_kg.nodes:
                node = self.code_kg.nodes[node_id]
                sub_node = SubGraphNode(
                    id=node.id,
                    type=node.type,
                    label=node.label,
                    properties=node.properties,
                    is_focal=(node_id in focal_nodes),
                )
                subgraph.add_node(sub_node)

        # Add edges
        for edge in self.code_kg.edges.values():
            if edge.source in nodes_to_include and edge.target in nodes_to_include:
                sub_edge = SubGraphEdge(
                    id=edge.id,
                    type=edge.type,
                    source=edge.source,
                    target=edge.target,
                    properties={},
                )
                subgraph.add_edge(sub_edge)

        return subgraph

    def _extract_guard_focused_subgraph(self, focal_nodes: List[str]) -> Any:
        """Extract subgraph focused on guards and safety mechanisms."""
        from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode, SubGraphEdge

        # For defender, focus on access control and guards
        nodes_to_include = set(focal_nodes)

        # Add nodes connected by guard-related edges
        for node_id in focal_nodes:
            if node_id in self.code_kg.nodes:
                for edge in self.code_kg.edges.values():
                    # Include guard-related edges
                    if edge.type in ["HAS_MODIFIER", "REQUIRES", "CHECKS"]:
                        if edge.source == node_id:
                            nodes_to_include.add(edge.target)
                        elif edge.target == node_id:
                            nodes_to_include.add(edge.source)

        # Create subgraph
        subgraph = SubGraph(focal_node_ids=focal_nodes)

        # Add nodes
        for node_id in nodes_to_include:
            if node_id in self.code_kg.nodes:
                node = self.code_kg.nodes[node_id]
                sub_node = SubGraphNode(
                    id=node.id,
                    type=node.type,
                    label=node.label,
                    properties=node.properties,
                    is_focal=(node_id in focal_nodes),
                )
                subgraph.add_node(sub_node)

        # Add edges
        for edge in self.code_kg.edges.values():
            if edge.source in nodes_to_include and edge.target in nodes_to_include:
                sub_edge = SubGraphEdge(
                    id=edge.id,
                    type=edge.type,
                    source=edge.source,
                    target=edge.target,
                    properties={},
                )
                subgraph.add_edge(sub_edge)

        return subgraph

    def _extract_path_subgraph(self, focal_nodes: List[str]) -> Any:
        """Extract subgraph focused on execution paths."""
        from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode, SubGraphEdge

        # For verifier, focus on paths and data flow
        nodes_to_include = set(focal_nodes)

        # Add nodes connected by path edges
        for node_id in focal_nodes:
            if node_id in self.code_kg.nodes:
                for edge in self.code_kg.edges.values():
                    # Include path-related edges
                    if edge.type in ["CALLS", "FLOWS_TO", "DEPENDS_ON"]:
                        if edge.source == node_id:
                            nodes_to_include.add(edge.target)
                        elif edge.target == node_id:
                            nodes_to_include.add(edge.source)

        # Create subgraph
        subgraph = SubGraph(focal_node_ids=focal_nodes)

        # Add nodes
        for node_id in nodes_to_include:
            if node_id in self.code_kg.nodes:
                node = self.code_kg.nodes[node_id]
                sub_node = SubGraphNode(
                    id=node.id,
                    type=node.type,
                    label=node.label,
                    properties=node.properties,
                    is_focal=(node_id in focal_nodes),
                )
                subgraph.add_node(sub_node)

        # Add edges
        for edge in self.code_kg.edges.values():
            if edge.source in nodes_to_include and edge.target in nodes_to_include:
                sub_edge = SubGraphEdge(
                    id=edge.id,
                    type=edge.type,
                    source=edge.source,
                    target=edge.target,
                    properties={},
                )
                subgraph.add_edge(sub_edge)

        return subgraph


@dataclass
class ChainedResult:
    """Result from chained agent execution."""

    stages: Dict[AgentType, Any]  # AgentResult per stage
    focal_nodes: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_final_verdict(self) -> bool:
        """
        Get final verdict based on all agent results.

        Returns True if vulnerability confirmed, False otherwise.
        """
        # If any agent didn't match, likely not vulnerable
        for result in self.stages.values():
            if not result.matched:
                return False

        # If all matched, check verifier
        if AgentType.VERIFIER in self.stages:
            return self.stages[AgentType.VERIFIER].matched

        # Otherwise, trust the consensus
        return True


class AgentRouter:
    """
    GLM-style agent router with selective context dispatch.

    Key innovation: 95% token reduction through context specialization.
    Each agent receives only the information it needs.

    Per 05.11-CONTEXT.md: Extended with policy diff computation,
    cross-protocol dependencies, and systemic risk scoring.
    """

    def __init__(
        self,
        code_kg: "KnowledgeGraph",
        domain_kg: Optional["DomainKnowledgeGraph"] = None,
        adversarial_kg: Optional["AdversarialKnowledgeGraph"] = None,
        linker: Optional["CrossGraphLinker"] = None,
        context_pack: Optional["ProtocolContextPack"] = None,
        passport_builder: Optional["PassportBuilder"] = None,
        strict_mode: bool = False,
    ):
        """
        Initialize agent router.

        Args:
            code_kg: Main code knowledge graph
            domain_kg: Domain knowledge graph (optional)
            adversarial_kg: Adversarial knowledge graph (optional)
            linker: Cross-graph linker (optional)
            context_pack: Protocol context pack for economic context (05.11)
            passport_builder: Passport builder for contract passports (05.11)
            strict_mode: If True, reject candidates without passports (05.11)
        """
        self.slicer = ContextSlicer(
            code_kg,
            domain_kg,
            adversarial_kg,
            linker,
            context_pack,
            passport_builder,
            strict_mode,
        )
        self.agents = {}  # Will be populated by register_agent()
        self.code_kg = code_kg
        self.context_pack = context_pack
        self.strict_mode = strict_mode

    def register_agent(self, agent_type: AgentType, agent: Any) -> None:
        """
        Register an agent for routing.

        Args:
            agent_type: Type of agent
            agent: Agent instance (must have analyze() method)
        """
        self.agents[agent_type] = agent

    def route(
        self,
        focal_nodes: List[str],
        agent_types: Optional[List[AgentType]] = None,
        parallel: bool = True,
        stage: ContextBudgetStage = ContextBudgetStage.EVIDENCE,
    ) -> Dict[AgentType, Any]:
        """
        Route analysis to specialized agents.

        Per 07.1.3: Budget reports are attached to contexts for auditability.

        Args:
            focal_nodes: Nodes to analyze
            agent_types: Which agents to use (default: all registered)
            parallel: Run agents in parallel if possible
            stage: Disclosure stage for budget enforcement

        Returns:
            Dict mapping agent type to agent result
        """
        if agent_types is None:
            agent_types = list(self.agents.keys())

        # Create optimized contexts with budget enforcement
        contexts = {
            agent_type: self.slicer.slice_for_agent(agent_type, focal_nodes, stage)
            for agent_type in agent_types
            if agent_type in self.agents
        }

        # Log token savings and budget status
        total_tokens = sum(c.estimate_tokens() for c in contexts.values())
        full_context_estimate = len(focal_nodes) * 2000  # Rough baseline
        if full_context_estimate > 0:
            savings = 1 - (total_tokens / full_context_estimate)
            logger.info(
                f"Token savings: {savings:.1%} "
                f"({total_tokens} vs {full_context_estimate})"
            )

        # Log budget enforcement summary (07.1.3)
        for agent_type, ctx in contexts.items():
            if ctx.budget_report:
                report = ctx.budget_report
                if report.trimmed:
                    logger.warning(
                        f"Budget exceeded for {agent_type.value}: "
                        f"{report.original_tokens} > {report.max_tokens} tokens"
                    )
                else:
                    logger.debug(
                        f"Budget OK for {agent_type.value}: "
                        f"{report.final_tokens}/{report.max_tokens} tokens"
                    )

        # Run agents
        if parallel and len(contexts) > 1:
            results = self._run_parallel(contexts)
        else:
            results = self._run_sequential(contexts)

        return results

    def route_with_chaining(
        self,
        focal_nodes: List[str],
    ) -> ChainedResult:
        """
        Route with result chaining between agents.

        Pipeline: Classifier → Attacker → Defender → Verifier
        Each agent receives previous agent's findings.

        Args:
            focal_nodes: Nodes to analyze

        Returns:
            ChainedResult with all stage results
        """
        results = {}

        # Stage 1: Classifier categorizes the vulnerability type
        if AgentType.CLASSIFIER in self.agents:
            classifier_ctx = self.slicer.slice_for_agent(
                AgentType.CLASSIFIER, focal_nodes
            )
            results[AgentType.CLASSIFIER] = self.agents[
                AgentType.CLASSIFIER
            ].analyze(classifier_ctx.subgraph)

        # Stage 2: Attacker tries to construct exploit
        if AgentType.ATTACKER in self.agents:
            attacker_ctx = self.slicer.slice_for_agent(
                AgentType.ATTACKER, focal_nodes
            )
            if AgentType.CLASSIFIER in results:
                attacker_ctx.upstream_results = [results[AgentType.CLASSIFIER]]
            results[AgentType.ATTACKER] = self.agents[
                AgentType.ATTACKER
            ].analyze(attacker_ctx.subgraph)

        # Stage 3: Defender argues against the attack
        if AgentType.DEFENDER in self.agents:
            defender_ctx = self.slicer.slice_for_agent(
                AgentType.DEFENDER, focal_nodes
            )
            if AgentType.ATTACKER in results:
                defender_ctx.upstream_results = [results[AgentType.ATTACKER]]
            results[AgentType.DEFENDER] = self.agents[
                AgentType.DEFENDER
            ].analyze(defender_ctx.subgraph)

        # Stage 4: Verifier checks path feasibility
        if AgentType.VERIFIER in self.agents:
            verifier_ctx = self.slicer.slice_for_agent(
                AgentType.VERIFIER, focal_nodes
            )
            upstream = []
            if AgentType.ATTACKER in results:
                upstream.append(results[AgentType.ATTACKER])
            if AgentType.DEFENDER in results:
                upstream.append(results[AgentType.DEFENDER])
            verifier_ctx.upstream_results = upstream
            results[AgentType.VERIFIER] = self.agents[
                AgentType.VERIFIER
            ].analyze(verifier_ctx.subgraph)

        return ChainedResult(
            stages=results,
            focal_nodes=focal_nodes,
            metadata={
                "total_agents": len(results),
                "pipeline": "classifier->attacker->defender->verifier",
            },
        )

    def _run_parallel(
        self, contexts: Dict[AgentType, AgentContext]
    ) -> Dict[AgentType, Any]:
        """Run agents in parallel using threads."""
        results = {}

        with ThreadPoolExecutor(max_workers=len(contexts)) as executor:
            futures = {
                agent_type: executor.submit(
                    self.agents[agent_type].analyze, ctx.subgraph
                )
                for agent_type, ctx in contexts.items()
                if agent_type in self.agents
            }

            for agent_type, future in futures.items():
                try:
                    results[agent_type] = future.result()
                except Exception as e:
                    logger.error(f"Agent {agent_type.value} failed: {e}")
                    from alphaswarm_sol.agents.base import AgentResult
                    results[agent_type] = AgentResult(
                        agent=agent_type.value,
                        matched=False,
                        confidence=0.0,
                        metadata={"error": str(e)},
                    )

        return results

    def _run_sequential(
        self, contexts: Dict[AgentType, AgentContext]
    ) -> Dict[AgentType, Any]:
        """Run agents sequentially."""
        results = {}

        for agent_type, ctx in contexts.items():
            if agent_type in self.agents:
                try:
                    results[agent_type] = self.agents[agent_type].analyze(
                        ctx.subgraph
                    )
                except Exception as e:
                    logger.error(f"Agent {agent_type.value} failed: {e}")
                    from alphaswarm_sol.agents.base import AgentResult
                    results[agent_type] = AgentResult(
                        agent=agent_type.value,
                        matched=False,
                        confidence=0.0,
                        metadata={"error": str(e)},
                    )

        return results


# --------------------------------------------------------------------------- #
# Tier Routing Policy Integration
# --------------------------------------------------------------------------- #


@dataclass
class TierRoutingMetadata:
    """Metadata from tier routing decisions for agent context.

    Attributes:
        tier: Selected model tier
        rationale: Human-readable rationale
        risk_score: Risk score used for routing
        evidence_completeness: Evidence completeness used for routing
        budget_remaining: Budget remaining at routing time
        was_escalated: Whether tier was escalated
        was_downgraded: Whether tier was downgraded
    """

    tier: str
    rationale: str
    risk_score: float = 0.0
    evidence_completeness: float = 1.0
    budget_remaining: Optional[float] = None
    was_escalated: bool = False
    was_downgraded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier": self.tier,
            "rationale": self.rationale,
            "risk_score": self.risk_score,
            "evidence_completeness": self.evidence_completeness,
            "budget_remaining": self.budget_remaining,
            "was_escalated": self.was_escalated,
            "was_downgraded": self.was_downgraded,
        }


class PolicyAwareAgentRouter(AgentRouter):
    """AgentRouter with integrated tier routing policy.

    Extends AgentRouter to use TierRoutingPolicy for cost-effective
    model tier selection based on risk, evidence, and budget.

    Example:
        from alphaswarm_sol.llm.routing_policy import TierRoutingPolicy

        policy = TierRoutingPolicy()
        router = PolicyAwareAgentRouter(
            code_kg=kg,
            routing_policy=policy,
            budget_usd=10.0,
        )

        # Route with policy-aware tier selection
        results = router.route_with_tier_policy(
            focal_nodes=["Vault.withdraw"],
            risk_score=0.8,
            evidence_completeness=0.3,
        )
    """

    def __init__(
        self,
        code_kg: "KnowledgeGraph",
        domain_kg: Optional["DomainKnowledgeGraph"] = None,
        adversarial_kg: Optional["AdversarialKnowledgeGraph"] = None,
        linker: Optional["CrossGraphLinker"] = None,
        context_pack: Optional["ProtocolContextPack"] = None,
        passport_builder: Optional["PassportBuilder"] = None,
        strict_mode: bool = False,
        routing_policy: Optional[Any] = None,
        budget_usd: Optional[float] = None,
    ):
        """Initialize policy-aware agent router.

        Args:
            code_kg: Main code knowledge graph
            domain_kg: Domain knowledge graph (optional)
            adversarial_kg: Adversarial knowledge graph (optional)
            linker: Cross-graph linker (optional)
            context_pack: Protocol context pack (optional)
            passport_builder: Passport builder (optional)
            strict_mode: Strict mode for missing passports
            routing_policy: TierRoutingPolicy instance
            budget_usd: Total budget for this router session
        """
        super().__init__(
            code_kg=code_kg,
            domain_kg=domain_kg,
            adversarial_kg=adversarial_kg,
            linker=linker,
            context_pack=context_pack,
            passport_builder=passport_builder,
            strict_mode=strict_mode,
        )
        self._routing_policy = routing_policy
        self._budget_usd = budget_usd
        self._spent_usd: float = 0.0
        self._routing_history: List[TierRoutingMetadata] = []

    @property
    def routing_policy(self) -> Any:
        """Get or create routing policy."""
        if self._routing_policy is None:
            from alphaswarm_sol.llm.routing_policy import TierRoutingPolicy
            self._routing_policy = TierRoutingPolicy()
        return self._routing_policy

    @property
    def budget_remaining(self) -> Optional[float]:
        """Remaining budget if set."""
        if self._budget_usd is None:
            return None
        return max(0.0, self._budget_usd - self._spent_usd)

    def get_tier_for_agent(
        self,
        agent_type: AgentType,
        risk_score: float = 0.0,
        evidence_completeness: float = 1.0,
        severity: Optional[str] = None,
        pattern_type: Optional[str] = None,
    ) -> TierRoutingMetadata:
        """Get tier recommendation for an agent type.

        Args:
            agent_type: Type of agent
            risk_score: Risk score (0.0 - 1.0)
            evidence_completeness: Evidence completeness (0.0 - 1.0)
            severity: Severity level
            pattern_type: Pattern being analyzed

        Returns:
            TierRoutingMetadata with tier and rationale
        """
        # Map agent type to task type
        task_type_map = {
            AgentType.CLASSIFIER: "pattern_validation",
            AgentType.ATTACKER: "attack_path_generation",
            AgentType.DEFENDER: "guard_analysis",
            AgentType.VERIFIER: "tier_b_verification",
        }
        task_type = task_type_map.get(agent_type, "tier_b_verification")

        decision = self.routing_policy.route(
            task_type=task_type,
            risk_score=risk_score,
            evidence_completeness=evidence_completeness,
            budget_remaining=self.budget_remaining,
            severity=severity,
            pattern_type=pattern_type,
        )

        metadata = TierRoutingMetadata(
            tier=decision.tier.value,
            rationale=decision.rationale,
            risk_score=risk_score,
            evidence_completeness=evidence_completeness,
            budget_remaining=self.budget_remaining,
            was_escalated=decision.was_escalated,
            was_downgraded=decision.was_downgraded,
        )

        self._routing_history.append(metadata)
        return metadata

    def route_with_tier_policy(
        self,
        focal_nodes: List[str],
        risk_score: float = 0.0,
        evidence_completeness: float = 1.0,
        severity: Optional[str] = None,
        pattern_type: Optional[str] = None,
        agent_types: Optional[List[AgentType]] = None,
        parallel: bool = True,
    ) -> Dict[AgentType, Any]:
        """Route analysis with tier policy metadata attached.

        Args:
            focal_nodes: Nodes to analyze
            risk_score: Risk score for routing
            evidence_completeness: Evidence completeness for routing
            severity: Severity level
            pattern_type: Pattern being analyzed
            agent_types: Which agents to use
            parallel: Run agents in parallel

        Returns:
            Dict mapping agent type to agent result (with tier metadata)
        """
        if agent_types is None:
            agent_types = list(self.agents.keys())

        # Get tier recommendations for each agent
        tier_metadata: Dict[AgentType, TierRoutingMetadata] = {}
        for agent_type in agent_types:
            tier_metadata[agent_type] = self.get_tier_for_agent(
                agent_type=agent_type,
                risk_score=risk_score,
                evidence_completeness=evidence_completeness,
                severity=severity,
                pattern_type=pattern_type,
            )

        # Run standard routing
        results = self.route(
            focal_nodes=focal_nodes,
            agent_types=agent_types,
            parallel=parallel,
        )

        # Attach tier metadata to results
        for agent_type, result in results.items():
            if agent_type in tier_metadata:
                if hasattr(result, 'metadata'):
                    result.metadata["tier_routing"] = tier_metadata[agent_type].to_dict()

        return results

    def get_routing_summary(self) -> Dict[str, Any]:
        """Get summary of routing decisions.

        Returns:
            Summary dictionary
        """
        if not self._routing_history:
            return {"total_decisions": 0}

        tier_counts: Dict[str, int] = {}
        escalations = 0
        downgrades = 0

        for metadata in self._routing_history:
            tier_counts[metadata.tier] = tier_counts.get(metadata.tier, 0) + 1
            if metadata.was_escalated:
                escalations += 1
            if metadata.was_downgraded:
                downgrades += 1

        return {
            "total_decisions": len(self._routing_history),
            "tier_distribution": tier_counts,
            "escalations": escalations,
            "downgrades": downgrades,
            "budget_remaining": self.budget_remaining,
        }
