"""Phase 9: Agent Base Class.

This module defines the base class for verification agents and the
AgentResult dataclass for returning analysis results.

Each agent specializes in a different aspect of vulnerability verification:
- Explorer: Path tracing and control flow analysis
- Pattern: YAML pattern matching on subgraphs
- Constraint: Z3-based constraint solving
- Risk: Attack scenario generation and assessment
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from alphaswarm_sol.kg.subgraph import SubGraph


class EvidenceType(str, Enum):
    """Types of evidence that agents can produce."""
    PATH = "path"
    PATTERN = "pattern"
    CONSTRAINT = "constraint"
    SCENARIO = "scenario"
    NODE = "node"
    EDGE = "edge"
    PROPERTY = "property"


@dataclass
class AgentEvidence:
    """Evidence supporting an agent's finding.

    Phase 5.10: Added evidence_id and build_hash fields for canonical,
    deterministic, graph-versioned evidence identification. These fields
    enable reproducible evidence gating and audit trails.

    Attributes:
        type: The type of evidence (path, pattern, constraint, scenario)
        data: The evidence data (varies by type)
        description: Human-readable description of the evidence
        confidence: Confidence score for this specific evidence (0-1)
        source_nodes: Node IDs that contributed to this evidence
        source_edges: Edge IDs that contributed to this evidence
        evidence_id: Canonical evidence ID (EVD-xxxxxxxx format, optional)
        build_hash: Graph build hash this evidence is tied to (optional)
        file: Source file path (optional, for evidence_id generation)
        line_start: Starting line number (optional, for evidence_id generation)
        line_end: Ending line number (optional, for evidence_id generation)
        semantic_op: Semantic operation this evidence relates to (optional)
    """
    type: EvidenceType
    data: Any = None
    description: str = ""
    confidence: float = 1.0
    source_nodes: List[str] = field(default_factory=list)
    source_edges: List[str] = field(default_factory=list)
    evidence_id: Optional[str] = None  # EVD-xxxxxxxx format
    build_hash: Optional[str] = None  # 12-char hex graph build hash
    file: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    semantic_op: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Serialization is deterministic: keys are ordered, optional fields
        are included only when set.
        """
        # Core fields always included
        result: Dict[str, Any] = {
            "type": self.type.value if isinstance(self.type, EvidenceType) else self.type,
            "data": self._serialize_data(self.data),
            "description": self.description,
            "confidence": self.confidence,
            "source_nodes": self.source_nodes,
            "source_edges": self.source_edges,
        }

        # Optional fields for evidence ID support (only if set)
        if self.evidence_id is not None:
            result["evidence_id"] = self.evidence_id
        if self.build_hash is not None:
            result["build_hash"] = self.build_hash
        if self.file is not None:
            result["file"] = self.file
        if self.line_start is not None:
            result["line_start"] = self.line_start
        if self.line_end is not None:
            result["line_end"] = self.line_end
        if self.semantic_op is not None:
            result["semantic_op"] = self.semantic_op

        return result

    def _serialize_data(self, data: Any) -> Any:
        """Serialize data to a JSON-compatible format."""
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        if isinstance(data, (list, tuple)):
            return [self._serialize_data(item) for item in data]
        if hasattr(data, "to_dict"):
            return data.to_dict()
        return str(data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AgentEvidence":
        """Deserialize from dictionary."""
        type_val = data.get("type", "property")
        try:
            evidence_type = EvidenceType(type_val)
        except ValueError:
            evidence_type = EvidenceType.PROPERTY

        return AgentEvidence(
            type=evidence_type,
            data=data.get("data"),
            description=str(data.get("description", "")),
            confidence=float(data.get("confidence", 1.0)),
            source_nodes=list(data.get("source_nodes", [])),
            source_edges=list(data.get("source_edges", [])),
            evidence_id=data.get("evidence_id"),
            build_hash=data.get("build_hash"),
            file=data.get("file"),
            line_start=data.get("line_start"),
            line_end=data.get("line_end"),
            semantic_op=data.get("semantic_op"),
        )

    def with_evidence_id(
        self,
        evidence_id: str,
        build_hash: str,
    ) -> "AgentEvidence":
        """Create a copy with evidence_id and build_hash set.

        Args:
            evidence_id: Canonical evidence ID (EVD-xxxxxxxx format)
            build_hash: Graph build hash (12-char hex)

        Returns:
            New AgentEvidence with evidence_id and build_hash
        """
        return AgentEvidence(
            type=self.type,
            data=self.data,
            description=self.description,
            confidence=self.confidence,
            source_nodes=list(self.source_nodes),
            source_edges=list(self.source_edges),
            evidence_id=evidence_id,
            build_hash=build_hash,
            file=self.file,
            line_start=self.line_start,
            line_end=self.line_end,
            semantic_op=self.semantic_op,
        )

    def compute_evidence_id(self, build_hash: str, node_id: str) -> "AgentEvidence":
        """Compute and set evidence_id from source location fields.

        Requires file and line_start to be set. Uses the evidence_id_for()
        function from alphaswarm_sol.kg.evidence_id.

        Args:
            build_hash: Graph build hash (12-char hex)
            node_id: Graph node ID this evidence relates to

        Returns:
            New AgentEvidence with evidence_id computed

        Raises:
            ValueError: If file or line_start is not set
        """
        if not self.file or not self.line_start:
            raise ValueError(
                "Cannot compute evidence_id: file and line_start must be set"
            )

        # Import here to avoid circular dependency
        from alphaswarm_sol.kg.evidence_id import evidence_id_for

        computed_id = evidence_id_for(
            build_hash=build_hash,
            node_id=node_id,
            file=self.file,
            line_start=self.line_start,
            line_end=self.line_end,
            semantic_op=self.semantic_op,
        )

        return self.with_evidence_id(computed_id, build_hash)


@dataclass
class AgentResult:
    """Result of an agent's analysis.

    Attributes:
        agent: Name of the agent that produced this result
        matched: Whether the agent found a vulnerability match
        findings: List of findings (type depends on agent)
        confidence: Overall confidence score (0-1)
        evidence: List of evidence supporting the findings
        metadata: Additional metadata about the analysis
    """
    agent: str
    matched: bool
    findings: List[Any] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[AgentEvidence] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent": self.agent,
            "matched": self.matched,
            "findings": self._serialize_findings(self.findings),
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "metadata": self.metadata,
        }

    def _serialize_findings(self, findings: List[Any]) -> List[Any]:
        """Serialize findings to JSON-compatible format."""
        result = []
        for finding in findings:
            if hasattr(finding, "to_dict"):
                result.append(finding.to_dict())
            elif isinstance(finding, dict):
                result.append(finding)
            else:
                result.append(str(finding))
        return result

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AgentResult":
        """Deserialize from dictionary."""
        return AgentResult(
            agent=str(data.get("agent", "")),
            matched=bool(data.get("matched", False)),
            findings=list(data.get("findings", [])),
            confidence=float(data.get("confidence", 0.0)),
            evidence=[AgentEvidence.from_dict(e) for e in data.get("evidence", [])],
            metadata=dict(data.get("metadata", {})),
        )


class VerificationAgent(ABC):
    """Abstract base class for verification agents.

    Each verification agent analyzes a subgraph from a specific perspective
    and returns findings with confidence scores and evidence.

    Subclasses must implement:
    - analyze(): Main analysis method
    - confidence(): Returns confidence score for the agent
    - agent_name: Property returning the agent's name
    """

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the name of this agent."""
        pass

    @abstractmethod
    def analyze(self, subgraph: "SubGraph", query: str = "") -> AgentResult:
        """Analyze a subgraph for vulnerabilities.

        Args:
            subgraph: The subgraph to analyze
            query: Optional query string for context

        Returns:
            AgentResult with findings, confidence, and evidence
        """
        pass

    @abstractmethod
    def confidence(self) -> float:
        """Return the base confidence level of this agent.

        Returns:
            Float between 0 and 1 indicating agent reliability
        """
        pass

    def _create_empty_result(self) -> AgentResult:
        """Create an empty result with no findings."""
        return AgentResult(
            agent=self.agent_name,
            matched=False,
            findings=[],
            confidence=self.confidence() * 0.5,  # Lower confidence for no findings
            evidence=[],
            metadata={"reason": "no_findings"},
        )

    def _create_error_result(self, error: str) -> AgentResult:
        """Create an error result."""
        return AgentResult(
            agent=self.agent_name,
            matched=False,
            findings=[],
            confidence=0.0,
            evidence=[],
            metadata={"error": error},
        )
