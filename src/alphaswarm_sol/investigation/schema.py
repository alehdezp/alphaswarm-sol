"""Schema definitions for LLM Investigation Patterns.

Task 13.11: Per-vulnerability investigation patterns that guide LLM reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InvestigationAction(Enum):
    """Actions available in investigation steps."""

    EXPLORE_GRAPH = "explore_graph"  # Query the knowledge graph
    LSP_REFERENCES = "lsp_references"  # Find all references to a symbol
    LSP_DEFINITION = "lsp_definition"  # Go to symbol definition
    LSP_CALL_HIERARCHY = "lsp_call_hierarchy"  # Trace call hierarchy
    PPR_EXPAND = "ppr_expand"  # Expand context via PPR
    READ_CODE = "read_code"  # Read specific file/function
    REASON = "reason"  # LLM reasoning step
    SYNTHESIZE = "synthesize"  # Combine multiple findings


class InvestigationVerdict(Enum):
    """Possible verdicts from investigation execution."""

    VULNERABLE = "vulnerable"
    LIKELY_VULNERABLE = "likely_vulnerable"
    UNCERTAIN = "uncertain"
    LIKELY_SAFE = "likely_safe"
    SAFE = "safe"
    SKIPPED = "skipped"  # Trigger conditions not met


@dataclass
class TriggerSignal:
    """A signal that triggers an investigation."""

    signal: str = ""
    property: str = ""
    value: Any = True
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TriggerSignal":
        """Create from dictionary."""
        return cls(
            signal=data.get("signal", ""),
            property=data.get("property", ""),
            value=data.get("value", True),
            description=data.get("description", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "signal": self.signal,
            "property": self.property,
            "value": self.value,
            "description": self.description,
        }


@dataclass
class InvestigationTrigger:
    """Trigger conditions for starting an investigation."""

    description: str = ""
    graph_signals: List[TriggerSignal] = field(default_factory=list)
    require_all: bool = False  # True = AND, False = OR

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationTrigger":
        """Create from dictionary."""
        signals = [
            TriggerSignal.from_dict(s)
            for s in data.get("graph_signals", [])
        ]
        return cls(
            description=data.get("description", ""),
            graph_signals=signals,
            require_all=data.get("require_all", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "description": self.description,
            "graph_signals": [s.to_dict() for s in self.graph_signals],
            "require_all": self.require_all,
        }


@dataclass
class InvestigationStep:
    """A single step in an investigation procedure."""

    id: int
    action: InvestigationAction
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""
    optional: bool = False
    timeout_seconds: int = 30

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationStep":
        """Create from dictionary."""
        action_str = data.get("action", "reason")
        try:
            action = InvestigationAction(action_str)
        except ValueError:
            action = InvestigationAction.REASON

        # Extract params from step data
        params = {}
        for key in ["graph_query", "target", "seed", "depth", "prompt", "file_path"]:
            if key in data:
                params[key] = data[key]

        return cls(
            id=data.get("id", 0),
            action=action,
            description=data.get("description", ""),
            params=params,
            interpretation=data.get("interpretation", ""),
            optional=data.get("optional", False),
            timeout_seconds=data.get("timeout_seconds", 30),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": self.id,
            "action": self.action.value,
            "description": self.description,
            "interpretation": self.interpretation,
            "optional": self.optional,
            "timeout_seconds": self.timeout_seconds,
        }
        result.update(self.params)
        return result


@dataclass
class VerdictCriteria:
    """Criteria for determining investigation verdict."""

    vulnerable: str = ""
    likely_vulnerable: str = ""
    uncertain: str = ""
    likely_safe: str = ""
    safe: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerdictCriteria":
        """Create from dictionary."""
        return cls(
            vulnerable=data.get("vulnerable", ""),
            likely_vulnerable=data.get("likely_vulnerable", ""),
            uncertain=data.get("uncertain", ""),
            likely_safe=data.get("likely_safe", ""),
            safe=data.get("safe", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "vulnerable": self.vulnerable,
            "likely_vulnerable": self.likely_vulnerable,
            "uncertain": self.uncertain,
            "likely_safe": self.likely_safe,
            "safe": self.safe,
        }


@dataclass
class InvestigationProcedure:
    """The investigation procedure with steps and verdict criteria."""

    hypothesis: str = ""
    steps: List[InvestigationStep] = field(default_factory=list)
    verdict_criteria: VerdictCriteria = field(default_factory=VerdictCriteria)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationProcedure":
        """Create from dictionary."""
        steps = [InvestigationStep.from_dict(s) for s in data.get("steps", [])]
        criteria = VerdictCriteria.from_dict(data.get("verdict_criteria", {}))
        return cls(
            hypothesis=data.get("hypothesis", ""),
            steps=steps,
            verdict_criteria=criteria,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hypothesis": self.hypothesis,
            "steps": [s.to_dict() for s in self.steps],
            "verdict_criteria": self.verdict_criteria.to_dict(),
        }


@dataclass
class InvestigationOutput:
    """Expected output format from investigation."""

    verdict: str = "VULNERABLE | UNCERTAIN | SAFE"
    attack_path: str = "Description of attack sequence"
    confidence: str = "0-100"
    evidence: str = "List of code locations"
    recommendation: str = "How to fix if vulnerable"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationOutput":
        """Create from dictionary."""
        return cls(
            verdict=data.get("verdict", ""),
            attack_path=data.get("attack_path", ""),
            confidence=data.get("confidence", ""),
            evidence=data.get("evidence", ""),
            recommendation=data.get("recommendation", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "verdict": self.verdict,
            "attack_path": self.attack_path,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass
class InvestigationPattern:
    """A complete LLM investigation pattern."""

    id: str
    name: str
    type: str = "investigation"  # Always "investigation"
    category: str = ""
    subcategories: List[str] = field(default_factory=list)
    severity_range: List[str] = field(default_factory=list)
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)

    trigger: InvestigationTrigger = field(default_factory=InvestigationTrigger)
    investigation: InvestigationProcedure = field(default_factory=InvestigationProcedure)
    output: InvestigationOutput = field(default_factory=InvestigationOutput)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationPattern":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=data.get("type", "investigation"),
            category=data.get("category", ""),
            subcategories=data.get("subcategories", []),
            severity_range=data.get("severity_range", []),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            tags=data.get("tags", []),
            trigger=InvestigationTrigger.from_dict(data.get("trigger", {})),
            investigation=InvestigationProcedure.from_dict(data.get("investigation", {})),
            output=InvestigationOutput.from_dict(data.get("output", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "category": self.category,
            "subcategories": self.subcategories,
            "severity_range": self.severity_range,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "trigger": self.trigger.to_dict(),
            "investigation": self.investigation.to_dict(),
            "output": self.output.to_dict(),
        }


@dataclass
class StepResult:
    """Result from executing a single investigation step."""

    step_id: int
    action: InvestigationAction
    success: bool = True
    raw_output: Any = None
    llm_interpretation: str = ""
    evidence: List[str] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "action": self.action.value,
            "success": self.success,
            "llm_interpretation": self.llm_interpretation,
            "evidence": self.evidence,
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class InvestigationResult:
    """Complete result from an investigation execution."""

    pattern_id: str
    pattern_name: str = ""
    verdict: InvestigationVerdict = InvestigationVerdict.UNCERTAIN
    confidence: int = 0
    attack_path: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    recommendation: str = ""
    step_results: List[StepResult] = field(default_factory=list)

    # Cost tracking
    total_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0

    # Metadata
    started_at: str = ""
    completed_at: str = ""
    context_used: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set timestamps if not provided."""
        if not self.started_at:
            self.started_at = datetime.utcnow().isoformat()

    @property
    def is_vulnerable(self) -> bool:
        """Check if verdict indicates vulnerability."""
        return self.verdict in [
            InvestigationVerdict.VULNERABLE,
            InvestigationVerdict.LIKELY_VULNERABLE,
        ]

    @property
    def is_safe(self) -> bool:
        """Check if verdict indicates safety."""
        return self.verdict in [
            InvestigationVerdict.SAFE,
            InvestigationVerdict.LIKELY_SAFE,
        ]

    @property
    def steps_completed(self) -> int:
        """Count of completed steps."""
        return len([s for s in self.step_results if s.success])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "attack_path": self.attack_path,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "step_results": [s.to_dict() for s in self.step_results],
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "steps_completed": self.steps_completed,
            "is_vulnerable": self.is_vulnerable,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Investigation: {self.pattern_name or self.pattern_id}",
            f"Verdict: {self.verdict.value.upper()}",
            f"Confidence: {self.confidence}%",
            "",
        ]

        if self.attack_path:
            lines.extend([
                "Attack Path:",
                f"  {self.attack_path}",
                "",
            ])

        if self.evidence:
            lines.append("Evidence:")
            for ev in self.evidence[:5]:  # Limit to 5
                lines.append(f"  - {ev}")
            if len(self.evidence) > 5:
                lines.append(f"  ... and {len(self.evidence) - 5} more")
            lines.append("")

        if self.recommendation:
            lines.extend([
                "Recommendation:",
                f"  {self.recommendation}",
                "",
            ])

        lines.extend([
            f"Steps Completed: {self.steps_completed}/{len(self.step_results)}",
            f"Tokens Used: {self.total_tokens:,}",
            f"Cost: ${self.cost_usd:.4f}",
        ])

        return "\n".join(lines)
