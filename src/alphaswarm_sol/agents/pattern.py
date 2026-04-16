"""Phase 9: Pattern Agent.

The Pattern Agent matches vulnerability patterns against subgraphs.
It evaluates property conditions, operation conditions, and edge requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import re

from alphaswarm_sol.agents.base import (
    VerificationAgent,
    AgentResult,
    AgentEvidence,
    EvidenceType,
)

if TYPE_CHECKING:
    from alphaswarm_sol.kg.subgraph import SubGraph, SubGraphNode


@dataclass
class VulnerabilityPattern:
    """A vulnerability pattern for matching.

    Simplified pattern structure for subgraph matching.
    """
    id: str
    name: str
    severity: str = "medium"
    description: str = ""
    # Property conditions
    match_all: List[Dict[str, Any]] = field(default_factory=list)
    match_any: List[Dict[str, Any]] = field(default_factory=list)
    match_none: List[Dict[str, Any]] = field(default_factory=list)
    # Operation conditions
    ops_required: List[str] = field(default_factory=list)
    ops_forbidden: List[str] = field(default_factory=list)
    # Behavioral signature pattern
    signature_pattern: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity,
            "description": self.description,
            "match_all": self.match_all,
            "match_any": self.match_any,
            "match_none": self.match_none,
            "ops_required": self.ops_required,
            "ops_forbidden": self.ops_forbidden,
            "signature_pattern": self.signature_pattern,
        }


@dataclass
class PatternMatch:
    """A pattern match on a node."""
    pattern: VulnerabilityPattern
    matched_node_id: str
    matched_node_label: str
    severity: str
    match_details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern.id,
            "pattern_name": self.pattern.name,
            "matched_node_id": self.matched_node_id,
            "matched_node_label": self.matched_node_label,
            "severity": self.severity,
            "match_details": self.match_details,
            "confidence": self.confidence,
        }


# Built-in vulnerability patterns for common issues
BUILTIN_PATTERNS = [
    VulnerabilityPattern(
        id="reentrancy-cei-violation",
        name="Reentrancy (CEI Violation)",
        severity="critical",
        description="State write after external call",
        match_all=[
            {"property": "state_write_after_external_call", "value": True},
        ],
        match_none=[
            {"property": "has_reentrancy_guard", "value": True},
        ],
        ops_required=["TRANSFERS_VALUE_OUT"],
    ),
    VulnerabilityPattern(
        id="missing-access-control",
        name="Missing Access Control",
        severity="high",
        description="Privileged state modification without access gate",
        match_all=[
            {"property": "writes_privileged_state", "value": True},
            {"property": "visibility", "value": ["public", "external"], "op": "in"},
        ],
        match_none=[
            {"property": "has_access_gate", "value": True},
        ],
    ),
    VulnerabilityPattern(
        id="unprotected-delegatecall",
        name="Unprotected Delegatecall",
        severity="critical",
        description="Delegatecall without access control",
        match_all=[
            {"property": "uses_delegatecall", "value": True},
        ],
        match_none=[
            {"property": "has_access_gate", "value": True},
        ],
    ),
    VulnerabilityPattern(
        id="unbounded-loop-dos",
        name="Unbounded Loop DoS",
        severity="medium",
        description="Loop without bound that could cause DoS",
        match_all=[
            {"property": "has_unbounded_loop", "value": True},
        ],
    ),
    VulnerabilityPattern(
        id="tx-origin-auth",
        name="tx.origin Authentication",
        severity="high",
        description="Using tx.origin for authentication",
        match_all=[
            {"property": "uses_tx_origin", "value": True},
        ],
    ),
    VulnerabilityPattern(
        id="oracle-no-staleness-check",
        name="Oracle Without Staleness Check",
        severity="medium",
        description="Oracle price read without staleness validation",
        match_all=[
            {"property": "reads_oracle_price", "value": True},
        ],
        match_none=[
            {"property": "has_staleness_check", "value": True},
        ],
    ),
    VulnerabilityPattern(
        id="unsafe-ecrecover",
        name="Unsafe ecrecover",
        severity="high",
        description="ecrecover without proper validation",
        match_all=[
            {"property": "uses_ecrecover", "value": True},
        ],
        match_none=[
            {"property": "checks_zero_address", "value": True},
        ],
    ),
]


class PatternAgent(VerificationAgent):
    """Pattern Agent for vulnerability pattern matching.

    This agent matches vulnerability patterns against nodes in the subgraph.
    It supports:
    - Property conditions (eq, in, gt, lt, etc.)
    - Operation requirements
    - Behavioral signature matching
    """

    SEVERITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4,
        "info": 0.2,
    }

    def __init__(self, patterns: Optional[List[VulnerabilityPattern]] = None):
        """Initialize the Pattern Agent.

        Args:
            patterns: Custom patterns to use. If None, uses builtin patterns.
        """
        self.patterns = patterns if patterns is not None else BUILTIN_PATTERNS

    @property
    def agent_name(self) -> str:
        return "pattern"

    def confidence(self) -> float:
        return 0.90

    def analyze(self, subgraph: "SubGraph", query: str = "") -> AgentResult:
        """Analyze the subgraph by matching vulnerability patterns.

        Args:
            subgraph: SubGraph to analyze
            query: Optional query context

        Returns:
            AgentResult with pattern matches as findings
        """
        if not subgraph.nodes:
            return self._create_empty_result()

        matches: List[PatternMatch] = []

        for pattern in self.patterns:
            for node_id, node in subgraph.nodes.items():
                if node.type != "Function":
                    continue

                match_result = self._match_pattern(pattern, node)
                if match_result:
                    matches.append(match_result)

        # Sort by severity
        matches.sort(
            key=lambda m: self.SEVERITY_WEIGHTS.get(m.severity, 0.5),
            reverse=True,
        )

        # Create evidence
        evidence = []
        for match in matches:
            evidence.append(AgentEvidence(
                type=EvidenceType.PATTERN,
                data=match.to_dict(),
                description=f"{match.pattern.name}: {match.pattern.description}",
                confidence=match.confidence,
                source_nodes=[match.matched_node_id],
            ))

        # Compute overall confidence
        if matches:
            avg_confidence = sum(m.confidence for m in matches) / len(matches)
            overall_confidence = self.confidence() * avg_confidence
        else:
            overall_confidence = self.confidence() * 0.5

        return AgentResult(
            agent=self.agent_name,
            matched=bool(matches),
            findings=[m.to_dict() for m in matches],
            confidence=overall_confidence,
            evidence=evidence,
            metadata={
                "patterns_evaluated": len(self.patterns),
                "nodes_evaluated": sum(1 for n in subgraph.nodes.values() if n.type == "Function"),
                "matches_found": len(matches),
                "severity_distribution": self._count_severities(matches),
            },
        )

    def _match_pattern(
        self, pattern: VulnerabilityPattern, node: "SubGraphNode"
    ) -> Optional[PatternMatch]:
        """Try to match a pattern against a node.

        Returns PatternMatch if successful, None otherwise.
        """
        props = node.properties
        match_details: Dict[str, Any] = {
            "conditions_matched": [],
            "conditions_failed": [],
        }
        confidence = 0.8

        # Check match_all conditions
        for cond in pattern.match_all:
            prop = cond.get("property", "")
            expected = cond.get("value")
            op = cond.get("op", "eq")

            actual = props.get(prop)
            matched = self._evaluate_condition(actual, expected, op)

            if not matched:
                match_details["conditions_failed"].append({
                    "type": "match_all",
                    "property": prop,
                    "expected": expected,
                    "actual": actual,
                })
                return None
            else:
                match_details["conditions_matched"].append({
                    "type": "match_all",
                    "property": prop,
                })
                confidence += 0.02

        # Check match_any conditions (at least one must match)
        if pattern.match_any:
            any_matched = False
            for cond in pattern.match_any:
                prop = cond.get("property", "")
                expected = cond.get("value")
                op = cond.get("op", "eq")

                actual = props.get(prop)
                if self._evaluate_condition(actual, expected, op):
                    any_matched = True
                    match_details["conditions_matched"].append({
                        "type": "match_any",
                        "property": prop,
                    })
                    break

            if not any_matched:
                return None

        # Check match_none conditions (none must match)
        for cond in pattern.match_none:
            prop = cond.get("property", "")
            expected = cond.get("value")
            op = cond.get("op", "eq")

            actual = props.get(prop)
            matched = self._evaluate_condition(actual, expected, op)

            if matched:
                match_details["conditions_failed"].append({
                    "type": "match_none",
                    "property": prop,
                    "actual": actual,
                })
                return None

        # Check required operations
        node_ops = set(props.get("semantic_ops", []))
        for req_op in pattern.ops_required:
            if req_op not in node_ops:
                match_details["conditions_failed"].append({
                    "type": "ops_required",
                    "operation": req_op,
                })
                return None
            match_details["conditions_matched"].append({
                "type": "ops_required",
                "operation": req_op,
            })

        # Check forbidden operations
        for forbidden_op in pattern.ops_forbidden:
            if forbidden_op in node_ops:
                match_details["conditions_failed"].append({
                    "type": "ops_forbidden",
                    "operation": forbidden_op,
                })
                return None

        # Check behavioral signature pattern
        if pattern.signature_pattern:
            sig = props.get("behavioral_signature", "")
            if not re.search(pattern.signature_pattern, sig):
                return None
            match_details["conditions_matched"].append({
                "type": "signature_match",
                "pattern": pattern.signature_pattern,
            })

        # Adjust confidence based on severity
        confidence *= self.SEVERITY_WEIGHTS.get(pattern.severity, 0.6)

        return PatternMatch(
            pattern=pattern,
            matched_node_id=node.id,
            matched_node_label=node.label,
            severity=pattern.severity,
            match_details=match_details,
            confidence=min(confidence, 1.0),
        )

    def _evaluate_condition(
        self, actual: Any, expected: Any, op: str
    ) -> bool:
        """Evaluate a condition with the given operator."""
        if op == "eq":
            return actual == expected
        elif op == "ne":
            return actual != expected
        elif op == "in":
            if isinstance(expected, list):
                return actual in expected
            return False
        elif op == "not_in":
            if isinstance(expected, list):
                return actual not in expected
            return True
        elif op == "gt":
            try:
                return float(actual) > float(expected)
            except (TypeError, ValueError):
                return False
        elif op == "gte":
            try:
                return float(actual) >= float(expected)
            except (TypeError, ValueError):
                return False
        elif op == "lt":
            try:
                return float(actual) < float(expected)
            except (TypeError, ValueError):
                return False
        elif op == "lte":
            try:
                return float(actual) <= float(expected)
            except (TypeError, ValueError):
                return False
        elif op == "contains":
            if isinstance(actual, (list, str)):
                return expected in actual
            return False
        elif op == "regex":
            if isinstance(actual, str) and isinstance(expected, str):
                return bool(re.search(expected, actual))
            return False
        elif op == "exists":
            return actual is not None
        elif op == "not_exists":
            return actual is None
        else:
            # Default: truthy check
            if expected is True:
                return bool(actual)
            elif expected is False:
                return not bool(actual)
            return actual == expected

    def _count_severities(self, matches: List[PatternMatch]) -> Dict[str, int]:
        """Count matches by severity."""
        counts: Dict[str, int] = {}
        for match in matches:
            sev = match.severity
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def add_pattern(self, pattern: VulnerabilityPattern) -> None:
        """Add a custom pattern to the agent."""
        self.patterns.append(pattern)

    def remove_pattern(self, pattern_id: str) -> bool:
        """Remove a pattern by ID."""
        for i, p in enumerate(self.patterns):
            if p.id == pattern_id:
                self.patterns.pop(i)
                return True
        return False
