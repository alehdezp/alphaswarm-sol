"""Grimoire Schema Definitions.

Task 13.1: Define the schema for grimoire definitions.

A Grimoire contains:
- Identification (id, name, category)
- Procedure steps (ordered verification actions)
- Tools configuration (what tools each step uses)
- Verdict rules (how to interpret results)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GrimoireStepAction(Enum):
    """Actions that a grimoire step can perform."""

    # Static analysis actions
    CHECK_GRAPH = "check_graph"  # Query the VKG graph
    CHECK_PROPERTY = "check_property"  # Check specific node properties
    CHECK_SEQUENCE = "check_sequence"  # Verify operation sequence

    # Code generation actions
    GENERATE_TEST = "generate_test"  # Generate exploit test
    GENERATE_INVARIANT = "generate_invariant"  # Generate invariant check

    # Execution actions
    EXECUTE_TEST = "execute_test"  # Run Foundry/Hardhat test
    EXECUTE_FUZZ = "execute_fuzz"  # Run Medusa/Echidna fuzzer
    EXECUTE_FORK = "execute_fork"  # Run on mainnet fork

    # Analysis actions
    ANALYZE_RESULTS = "analyze_results"  # Analyze test results
    COMPARE_PATTERNS = "compare_patterns"  # Compare with known patterns

    # Verdict actions
    DETERMINE_VERDICT = "determine_verdict"  # Make final determination


class VerdictConfidence(Enum):
    """Confidence levels for verdicts."""

    HIGH = "high"  # Very confident (test confirms, multiple signals)
    MEDIUM = "medium"  # Moderately confident (some evidence)
    LOW = "low"  # Low confidence (uncertain)
    UNKNOWN = "unknown"  # Cannot determine


class GrimoireVerdict(Enum):
    """Possible verdicts from grimoire execution."""

    VULNERABLE = "vulnerable"  # Confirmed vulnerable
    SAFE = "safe"  # Confirmed safe
    LIKELY_VULNERABLE = "likely_vulnerable"  # Probably vulnerable
    LIKELY_SAFE = "likely_safe"  # Probably safe
    UNCERTAIN = "uncertain"  # Cannot determine
    NEEDS_REVIEW = "needs_review"  # Requires human review


@dataclass
class VerdictRule:
    """Rule for determining verdict from step results."""

    condition: str  # Condition expression (e.g., "test_passes_exploit")
    verdict: GrimoireVerdict
    confidence: VerdictConfidence
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "condition": self.condition,
            "verdict": self.verdict.value,
            "confidence": self.confidence.value,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerdictRule":
        """Deserialize from dictionary."""
        return cls(
            condition=data["condition"],
            verdict=GrimoireVerdict(data["verdict"]),
            confidence=VerdictConfidence(data.get("confidence", "medium")),
            explanation=data.get("explanation", ""),
        )


@dataclass
class GrimoireStep:
    """A single step in a grimoire procedure.

    Each step has:
    - An action to perform
    - Required inputs (from context or previous steps)
    - Expected outputs
    - Tools to use
    - Optional queries or templates
    """

    step_number: int
    name: str
    action: GrimoireStepAction
    description: str = ""

    # Input/output
    inputs: List[str] = field(default_factory=list)  # Keys from context/previous steps
    outputs: List[str] = field(default_factory=list)  # Keys this step produces

    # Tools and configuration
    tools: List[str] = field(default_factory=list)  # Tools required (foundry, medusa, etc.)
    queries: List[str] = field(default_factory=list)  # Graph queries to run
    template: str = ""  # Template name for code generation
    command: str = ""  # Command to execute

    # Timing and optional
    timeout_seconds: int = 60
    optional: bool = False  # If true, failure doesn't stop procedure
    skip_if: str = ""  # Condition to skip this step

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_number": self.step_number,
            "name": self.name,
            "action": self.action.value,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "tools": self.tools,
            "queries": self.queries,
            "template": self.template,
            "command": self.command,
            "timeout_seconds": self.timeout_seconds,
            "optional": self.optional,
            "skip_if": self.skip_if,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GrimoireStep":
        """Deserialize from dictionary."""
        return cls(
            step_number=data["step_number"],
            name=data["name"],
            action=GrimoireStepAction(data["action"]),
            description=data.get("description", ""),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            tools=data.get("tools", []),
            queries=data.get("queries", []),
            template=data.get("template", ""),
            command=data.get("command", ""),
            timeout_seconds=data.get("timeout_seconds", 60),
            optional=data.get("optional", False),
            skip_if=data.get("skip_if", ""),
        )


@dataclass
class GrimoireProcedure:
    """The procedure (ordered steps) for a grimoire."""

    steps: List[GrimoireStep] = field(default_factory=list)
    verdict_rules: List[VerdictRule] = field(default_factory=list)
    default_verdict: GrimoireVerdict = GrimoireVerdict.UNCERTAIN

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "steps": [s.to_dict() for s in self.steps],
            "verdict_rules": [r.to_dict() for r in self.verdict_rules],
            "default_verdict": self.default_verdict.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GrimoireProcedure":
        """Deserialize from dictionary."""
        return cls(
            steps=[GrimoireStep.from_dict(s) for s in data.get("steps", [])],
            verdict_rules=[VerdictRule.from_dict(r) for r in data.get("verdict_rules", [])],
            default_verdict=GrimoireVerdict(data.get("default_verdict", "uncertain")),
        )

    def add_step(self, step: GrimoireStep) -> "GrimoireProcedure":
        """Add a step to the procedure."""
        self.steps.append(step)
        return self

    def add_verdict_rule(self, rule: VerdictRule) -> "GrimoireProcedure":
        """Add a verdict rule."""
        self.verdict_rules.append(rule)
        return self


@dataclass
class ToolsConfig:
    """Configuration for tools used by a grimoire."""

    # Test frameworks
    foundry_enabled: bool = True
    hardhat_enabled: bool = False

    # Fuzzers
    medusa_enabled: bool = False
    echidna_enabled: bool = False
    medusa_duration: int = 60  # seconds
    echidna_duration: int = 60  # seconds

    # Fork testing
    fork_enabled: bool = False
    fork_rpc: str = ""
    fork_block: str = "latest"

    # Testnet deployment
    testnet_enabled: bool = False
    testnet_network: str = "sepolia"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "foundry_enabled": self.foundry_enabled,
            "hardhat_enabled": self.hardhat_enabled,
            "medusa_enabled": self.medusa_enabled,
            "echidna_enabled": self.echidna_enabled,
            "medusa_duration": self.medusa_duration,
            "echidna_duration": self.echidna_duration,
            "fork_enabled": self.fork_enabled,
            "fork_rpc": self.fork_rpc,
            "fork_block": self.fork_block,
            "testnet_enabled": self.testnet_enabled,
            "testnet_network": self.testnet_network,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolsConfig":
        """Deserialize from dictionary."""
        return cls(
            foundry_enabled=data.get("foundry_enabled", True),
            hardhat_enabled=data.get("hardhat_enabled", False),
            medusa_enabled=data.get("medusa_enabled", False),
            echidna_enabled=data.get("echidna_enabled", False),
            medusa_duration=data.get("medusa_duration", 60),
            echidna_duration=data.get("echidna_duration", 60),
            fork_enabled=data.get("fork_enabled", False),
            fork_rpc=data.get("fork_rpc", ""),
            fork_block=data.get("fork_block", "latest"),
            testnet_enabled=data.get("testnet_enabled", False),
            testnet_network=data.get("testnet_network", "sepolia"),
        )


@dataclass
class Grimoire:
    """A complete grimoire definition.

    Grimoires are per-vulnerability testing playbooks that encode
    expert knowledge for how to verify, test, and exploit vulnerabilities.

    Example:
        grimoire = Grimoire(
            id="grimoire-reentrancy",
            name="Reentrancy Verification Grimoire",
            category="reentrancy",
            skill="/test-reentrancy",
        )
    """

    # Identification
    id: str
    name: str
    category: str  # Vulnerability category (reentrancy, access-control, etc.)
    subcategories: List[str] = field(default_factory=list)  # Specific variants

    # Skill invocation
    skill: str = ""  # Skill name (e.g., /test-reentrancy)
    aliases: List[str] = field(default_factory=list)  # Alternative names

    # Description
    description: str = ""
    version: str = "1.0.0"

    # The procedure
    procedure: GrimoireProcedure = field(default_factory=GrimoireProcedure)

    # Tools configuration
    tools_config: ToolsConfig = field(default_factory=ToolsConfig)

    # Context requirements
    required_context: List[str] = field(default_factory=list)  # Required bead fields
    optional_context: List[str] = field(default_factory=list)  # Optional bead fields

    # Graph queries to pre-load
    graph_queries: List[str] = field(default_factory=list)

    # Test templates
    test_templates: Dict[str, str] = field(default_factory=dict)

    # Metadata
    author: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "subcategories": self.subcategories,
            "skill": self.skill,
            "aliases": self.aliases,
            "description": self.description,
            "version": self.version,
            "procedure": self.procedure.to_dict(),
            "tools_config": self.tools_config.to_dict(),
            "required_context": self.required_context,
            "optional_context": self.optional_context,
            "graph_queries": self.graph_queries,
            "test_templates": self.test_templates,
            "author": self.author,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Grimoire":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            subcategories=data.get("subcategories", []),
            skill=data.get("skill", ""),
            aliases=data.get("aliases", []),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            procedure=GrimoireProcedure.from_dict(data.get("procedure", {})),
            tools_config=ToolsConfig.from_dict(data.get("tools_config", {})),
            required_context=data.get("required_context", []),
            optional_context=data.get("optional_context", []),
            graph_queries=data.get("graph_queries", []),
            test_templates=data.get("test_templates", {}),
            author=data.get("author", ""),
            tags=data.get("tags", []),
        )

    def get_step(self, step_number: int) -> Optional[GrimoireStep]:
        """Get a specific step by number."""
        for step in self.procedure.steps:
            if step.step_number == step_number:
                return step
        return None

    def get_required_tools(self) -> List[str]:
        """Get list of all required tools across all steps."""
        tools = set()
        for step in self.procedure.steps:
            tools.update(step.tools)
        return sorted(tools)


@dataclass
class StepEvidence:
    """Evidence collected from a single step."""

    step_number: int
    step_name: str
    action: GrimoireStepAction
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "action": self.action.value,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class GrimoireResult:
    """Result of executing a grimoire.

    Contains the verdict, confidence, evidence from each step,
    and any generated artifacts (tests, reports).
    """

    grimoire_id: str
    finding_id: str = ""

    # Verdict
    verdict: GrimoireVerdict = GrimoireVerdict.UNCERTAIN
    confidence: VerdictConfidence = VerdictConfidence.UNKNOWN
    verdict_explanation: str = ""

    # Evidence from steps
    step_evidence: List[StepEvidence] = field(default_factory=list)

    # Timing
    total_duration_ms: int = 0
    started_at: str = ""
    completed_at: str = ""

    # Generated artifacts
    generated_test: str = ""  # Path to generated test file
    test_output: str = ""  # Output from test execution
    fuzz_report: str = ""  # Fuzzing results

    # Success tracking
    steps_completed: int = 0
    steps_total: int = 0
    steps_failed: int = 0

    # Error
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "grimoire_id": self.grimoire_id,
            "finding_id": self.finding_id,
            "verdict": self.verdict.value,
            "confidence": self.confidence.value,
            "verdict_explanation": self.verdict_explanation,
            "step_evidence": [e.to_dict() for e in self.step_evidence],
            "total_duration_ms": self.total_duration_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "generated_test": self.generated_test,
            "test_output": self.test_output,
            "fuzz_report": self.fuzz_report,
            "steps_completed": self.steps_completed,
            "steps_total": self.steps_total,
            "steps_failed": self.steps_failed,
            "error": self.error,
        }

    @property
    def is_vulnerable(self) -> bool:
        """Check if verdict indicates vulnerability."""
        return self.verdict in (
            GrimoireVerdict.VULNERABLE,
            GrimoireVerdict.LIKELY_VULNERABLE,
        )

    @property
    def is_safe(self) -> bool:
        """Check if verdict indicates safety."""
        return self.verdict in (
            GrimoireVerdict.SAFE,
            GrimoireVerdict.LIKELY_SAFE,
        )

    @property
    def is_high_confidence(self) -> bool:
        """Check if verdict is high confidence."""
        return self.confidence == VerdictConfidence.HIGH

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Grimoire: {self.grimoire_id}",
            f"Verdict: {self.verdict.value} ({self.confidence.value} confidence)",
            "",
            f"Steps: {self.steps_completed}/{self.steps_total} completed, {self.steps_failed} failed",
            f"Duration: {self.total_duration_ms}ms",
            "",
        ]

        if self.verdict_explanation:
            lines.append(f"Explanation: {self.verdict_explanation}")
            lines.append("")

        if self.step_evidence:
            lines.append("Step Evidence:")
            for evidence in self.step_evidence:
                status = "OK" if evidence.success else "FAILED"
                lines.append(f"  {evidence.step_number}. {evidence.step_name}: {status}")
                if evidence.error:
                    lines.append(f"     Error: {evidence.error}")

        if self.error:
            lines.append("")
            lines.append(f"Error: {self.error}")

        return "\n".join(lines)
