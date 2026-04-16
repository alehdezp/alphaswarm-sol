"""VulnerabilityBead - comprehensive investigation package.

The VulnerabilityBead is a self-contained context package that provides
everything an LLM needs to investigate a potential vulnerability WITHOUT
requesting additional context.

Design Principles (from R6.1 Anthropic Beads Pattern):
1. Self-Containment: All information needed is included
2. Structured Context: Organized in predictable sections
3. Task Clarity: Clear objective and success criteria
4. Evidence-Based: Supporting data included, not just claims
5. Handoff-Ready: Can be passed to any capable agent

Usage:
    from alphaswarm_sol.beads import VulnerabilityBead, PatternContext, InvestigationGuide

    bead = VulnerabilityBead(
        id="VKG-001",
        vulnerability_class="reentrancy",
        pattern_id="vm-001",
        severity=Severity.CRITICAL,
        confidence=0.95,
        vulnerable_code=CodeSnippet(...),
        related_code=[...],
        pattern_context=PatternContext(...),
        investigation_guide=InvestigationGuide(...),
        test_context=TestContext(...),
        similar_exploits=[...],
        fix_recommendations=[...]
    )

    # Generate LLM investigation prompt
    prompt = bead.get_llm_prompt()

    # Serialize for storage
    json_data = bead.to_json()
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import (
    BeadStatus,
    CodeSnippet,
    ExploitReference,
    InvestigationStep,
    Severity,
    Verdict,
    VerdictType,
)

# Optional import for graph context - only needed if using graph slicing
try:
    from alphaswarm_sol.kg.slicer import SlicedGraph
except ImportError:
    SlicedGraph = None  # type: ignore


@dataclass
class TestContext:
    """Context for writing exploit tests.

    Provides a scaffold for creating proof-of-concept tests that
    demonstrate the vulnerability.

    Attributes:
        scaffold_code: Foundry/Hardhat test template
        attack_scenario: Step-by-step attack description
        setup_requirements: What needs to be set up for the test
        expected_outcome: What confirms the exploit works

    Usage:
        test_ctx = TestContext(
            scaffold_code="// SPDX-License-Identifier: MIT\\ncontract AttackTest...",
            attack_scenario="1. Deploy attacker contract\\n2. Call withdraw...",
            setup_requirements=["Attacker contract with fallback"],
            expected_outcome="Attacker extracts more than their balance"
        )
    """
    scaffold_code: str
    attack_scenario: str
    setup_requirements: List[str]
    expected_outcome: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "scaffold_code": self.scaffold_code,
            "attack_scenario": self.attack_scenario,
            "setup_requirements": self.setup_requirements,
            "expected_outcome": self.expected_outcome,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestContext":
        """Create TestContext from dictionary."""
        return cls(
            scaffold_code=str(data.get("scaffold_code", "")),
            attack_scenario=str(data.get("attack_scenario", "")),
            setup_requirements=list(data.get("setup_requirements", [])),
            expected_outcome=str(data.get("expected_outcome", "")),
        )


@dataclass
class PatternContext:
    """Context about why the pattern matched.

    Explains what pattern triggered, why it flagged this specific code,
    and what evidence was found.

    Attributes:
        pattern_name: Human-readable name (e.g., "Classic Reentrancy")
        pattern_description: What this pattern detects
        why_flagged: Specific reason THIS code matched
        matched_properties: Which VKG properties triggered the match
        evidence_lines: Specific line numbers where evidence was found

    Usage:
        ctx = PatternContext(
            pattern_name="Classic Reentrancy",
            pattern_description="Detects external calls before state updates",
            why_flagged="External call on line 46 before balance update on line 47",
            matched_properties=["state_write_after_external_call"],
            evidence_lines=[46, 47]
        )
    """
    pattern_name: str
    pattern_description: str
    why_flagged: str
    matched_properties: List[str]
    evidence_lines: List[int]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pattern_name": self.pattern_name,
            "pattern_description": self.pattern_description,
            "why_flagged": self.why_flagged,
            "matched_properties": self.matched_properties,
            "evidence_lines": self.evidence_lines,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternContext":
        """Create PatternContext from dictionary."""
        return cls(
            pattern_name=str(data.get("pattern_name", "")),
            pattern_description=str(data.get("pattern_description", "")),
            why_flagged=str(data.get("why_flagged", "")),
            matched_properties=list(data.get("matched_properties", [])),
            evidence_lines=list(data.get("evidence_lines", [])),
        )


@dataclass
class InvestigationGuide:
    """Complete investigation guidance for this vulnerability type.

    Provides structured guidance for investigating the potential
    vulnerability, including steps, questions, and indicators.

    Attributes:
        steps: Ordered investigation steps to follow
        questions_to_answer: Key questions that determine TP/FP
        common_false_positives: Known patterns that look vulnerable but aren't
        key_indicators: What confirms it's a real vulnerability
        safe_patterns: What would make the code safe

    Usage:
        guide = InvestigationGuide(
            steps=[InvestigationStep(...)],
            questions_to_answer=["Is the external call target user-controlled?"],
            common_false_positives=["nonReentrant modifier present"],
            key_indicators=["State update after external call"],
            safe_patterns=["CEI pattern", "reentrancy guard"]
        )
    """
    steps: List[InvestigationStep]
    questions_to_answer: List[str]
    common_false_positives: List[str]
    key_indicators: List[str]
    safe_patterns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "steps": [s.to_dict() for s in self.steps],
            "questions_to_answer": self.questions_to_answer,
            "common_false_positives": self.common_false_positives,
            "key_indicators": self.key_indicators,
            "safe_patterns": self.safe_patterns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationGuide":
        """Create InvestigationGuide from dictionary."""
        steps_data = data.get("steps", [])
        steps = [InvestigationStep.from_dict(s) for s in steps_data]
        return cls(
            steps=steps,
            questions_to_answer=list(data.get("questions_to_answer", [])),
            common_false_positives=list(data.get("common_false_positives", [])),
            key_indicators=list(data.get("key_indicators", [])),
            safe_patterns=list(data.get("safe_patterns", [])),
        )


@dataclass
class VulnerabilityBead:
    """A self-contained investigation package for a potential vulnerability.

    Design principle: The LLM should be able to make a verdict using ONLY
    the information in this bead, without asking for more context.

    The name "Bead" comes from the Anthropic pattern of structuring
    context for effective AI reasoning - each bead is a complete unit
    of investigation work.

    Sections:
    - IDENTITY: What this bead represents
    - CODE CONTEXT: The code being analyzed
    - PATTERN CONTEXT: Why the pattern flagged this code
    - INVESTIGATION GUIDANCE: How to analyze the finding
    - TEST CONTEXT: How to write a PoC
    - HISTORICAL CONTEXT: Similar real-world exploits
    - STATUS: Current investigation state

    Attributes:
        id: Unique identifier (e.g., "VKG-001")
        vulnerability_class: Category (e.g., "reentrancy", "access-control")
        pattern_id: Pattern that matched (e.g., "vm-001")
        severity: Severity level
        confidence: Initial confidence from pattern matching (0.0-1.0)
        vulnerable_code: The flagged code snippet
        related_code: Called functions, modifiers, etc.
        full_contract: Full contract source if < 500 lines
        inheritance_chain: Parent contracts
        pattern_context: Why the pattern matched
        investigation_guide: How to investigate
        test_context: How to write PoC tests
        similar_exploits: Historical exploits
        fix_recommendations: How to fix
        status: Current investigation status
        notes: Investigation notes
        verdict: Final determination (if made)
        created_at: When bead was created
        updated_at: Last update time
        context_hash: Hash for change detection

    Usage:
        # Create a bead
        bead = VulnerabilityBead(
            id="VKG-001",
            vulnerability_class="reentrancy",
            ...
        )

        # Generate LLM prompt
        prompt = bead.get_llm_prompt()

        # Add investigation notes
        bead.add_note("Checked modifiers - no reentrancy guard found")

        # Set verdict
        bead.set_verdict(Verdict(
            type=VerdictType.TRUE_POSITIVE,
            reason="Confirmed via PoC",
            confidence=0.99,
            evidence=["External call before state update"]
        ))

        # Serialize
        json_str = bead.to_json()
    """

    # === IDENTITY ===
    id: str
    vulnerability_class: str
    pattern_id: str
    severity: Severity
    confidence: float

    # === CODE CONTEXT ===
    vulnerable_code: CodeSnippet
    related_code: List[CodeSnippet]
    full_contract: Optional[str]
    inheritance_chain: List[str]

    # === PATTERN CONTEXT ===
    pattern_context: PatternContext

    # === INVESTIGATION GUIDANCE ===
    investigation_guide: InvestigationGuide

    # === TEST CONTEXT ===
    test_context: TestContext

    # === HISTORICAL CONTEXT ===
    similar_exploits: List[ExploitReference]
    fix_recommendations: List[str]

    # === GRAPH IDENTITY ===
    function_id: str = ""

    # === STATUS & METADATA ===
    status: BeadStatus = BeadStatus.PENDING
    notes: List[str] = field(default_factory=list)
    verdict: Optional[Verdict] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # === CONTEXT HASH ===
    context_hash: str = ""

    # === GRAPH CONTEXT (Task 9.D) ===
    # Category-sliced graph context for token-efficient LLM analysis
    graph_context: Optional[Dict[str, Any]] = None
    graph_context_category: str = ""  # Category used for slicing
    full_graph_available: bool = True  # Whether full graph can be requested

    # === POOL INTEGRATION (ORCH-04/08) ===
    # Pool association for orchestration layer
    pool_id: Optional[str] = None  # ID of pool this bead belongs to

    # === DEBATE PROTOCOL (ORCH-06) ===
    # Multi-agent debate outcomes for human review
    debate_summary: Optional[str] = None  # Summary of debate outcome
    attacker_claim: Optional[str] = None  # Attacker agent's exploitation claim
    defender_claim: Optional[str] = None  # Defender agent's mitigation claim
    verifier_verdict: Optional[str] = None  # Verifier agent's synthesis

    # === HUMAN FLAG (ORCH-08) ===
    # Human review requirement from debate
    human_flag: bool = False  # True if debate outcome requires human review

    # === WORK STATE (ORCH-08) ===
    # Agent resumption state for work state persistence
    work_state: Optional[Dict[str, Any]] = None  # State for agent resumption
    last_agent: Optional[str] = None  # Last agent that processed this bead
    last_updated: Optional[datetime] = None  # Last update timestamp

    # === TOOL INTEGRATION (Phase 5.1) ===
    # Metadata for tool-generated beads
    metadata: Dict[str, Any] = field(default_factory=dict)  # Tool-specific context

    def __post_init__(self) -> None:
        """Calculate context hash if not provided and validate confidence."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if not self.context_hash:
            self.context_hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate hash of code context for change detection.

        Used to detect when underlying code has changed since bead creation.
        """
        content = self.vulnerable_code.source
        for snippet in self.related_code:
            content += snippet.source
        if self.full_contract:
            content += self.full_contract
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "vulnerability_class": self.vulnerability_class,
            "pattern_id": self.pattern_id,
            "function_id": self.function_id,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "vulnerable_code": self.vulnerable_code.to_dict(),
            "related_code": [c.to_dict() for c in self.related_code],
            "full_contract": self.full_contract,
            "inheritance_chain": self.inheritance_chain,
            "pattern_context": self.pattern_context.to_dict(),
            "investigation_guide": self.investigation_guide.to_dict(),
            "test_context": self.test_context.to_dict(),
            "similar_exploits": [e.to_dict() for e in self.similar_exploits],
            "fix_recommendations": self.fix_recommendations,
            "status": self.status.value,
            "notes": self.notes,
            "verdict": self.verdict.to_dict() if self.verdict else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "context_hash": self.context_hash,
            "graph_context": self.graph_context,
            "graph_context_category": self.graph_context_category,
            "full_graph_available": self.full_graph_available,
            # Pool integration (ORCH-04)
            "pool_id": self.pool_id,
            # Debate protocol (ORCH-06)
            "debate_summary": self.debate_summary,
            "attacker_claim": self.attacker_claim,
            "defender_claim": self.defender_claim,
            "verifier_verdict": self.verifier_verdict,
            # Human flag (ORCH-08)
            "human_flag": self.human_flag,
            # Work state (ORCH-08)
            "work_state": self.work_state,
            "last_agent": self.last_agent,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            # Tool integration (Phase 5.1)
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VulnerabilityBead":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with bead fields

        Returns:
            VulnerabilityBead instance
        """
        # Parse timestamps
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        else:
            updated_at = datetime.now()

        # Parse verdict if present
        verdict_data = data.get("verdict")
        verdict = Verdict.from_dict(verdict_data) if verdict_data else None

        # Parse severity
        severity = data.get("severity", "medium")
        if isinstance(severity, str):
            severity = Severity(severity)

        # Parse status
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = BeadStatus(status)

        # Parse last_updated timestamp
        last_updated_str = data.get("last_updated")
        last_updated = None
        if isinstance(last_updated_str, str):
            last_updated = datetime.fromisoformat(last_updated_str)

        return cls(
            id=str(data.get("id", "")),
            vulnerability_class=str(data.get("vulnerability_class", "")),
            pattern_id=str(data.get("pattern_id", "")),
            function_id=str(data.get("function_id", "")),
            severity=severity,
            confidence=float(data.get("confidence", 0.0)),
            vulnerable_code=CodeSnippet.from_dict(data.get("vulnerable_code", {})),
            related_code=[CodeSnippet.from_dict(c) for c in data.get("related_code", [])],
            full_contract=data.get("full_contract"),
            inheritance_chain=list(data.get("inheritance_chain", [])),
            pattern_context=PatternContext.from_dict(data.get("pattern_context", {})),
            investigation_guide=InvestigationGuide.from_dict(data.get("investigation_guide", {})),
            test_context=TestContext.from_dict(data.get("test_context", {})),
            similar_exploits=[ExploitReference.from_dict(e) for e in data.get("similar_exploits", [])],
            fix_recommendations=list(data.get("fix_recommendations", [])),
            status=status,
            notes=list(data.get("notes", [])),
            verdict=verdict,
            created_at=created_at,
            updated_at=updated_at,
            context_hash=str(data.get("context_hash", "")),
            graph_context=data.get("graph_context"),
            graph_context_category=str(data.get("graph_context_category", "")),
            full_graph_available=bool(data.get("full_graph_available", True)),
            # Pool integration (ORCH-04)
            pool_id=data.get("pool_id"),
            # Debate protocol (ORCH-06)
            debate_summary=data.get("debate_summary"),
            attacker_claim=data.get("attacker_claim"),
            defender_claim=data.get("defender_claim"),
            verifier_verdict=data.get("verifier_verdict"),
            # Human flag (ORCH-08)
            human_flag=bool(data.get("human_flag", False)),
            # Work state (ORCH-08)
            work_state=data.get("work_state"),
            last_agent=data.get("last_agent"),
            last_updated=last_updated,
            # Tool integration (Phase 5.1)
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "VulnerabilityBead":
        """Deserialize from JSON string.

        Args:
            json_str: JSON-encoded bead

        Returns:
            VulnerabilityBead instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def add_note(self, note: str) -> None:
        """Add an investigation note with timestamp.

        Args:
            note: Note text to add
        """
        timestamp = datetime.now().isoformat()
        self.notes.append(f"[{timestamp}] {note}")
        self.updated_at = datetime.now()

    def set_verdict(self, verdict: Verdict) -> None:
        """Set the final verdict on this finding.

        Updates status based on verdict type:
        - TRUE_POSITIVE -> CONFIRMED
        - FALSE_POSITIVE -> REJECTED
        - INCONCLUSIVE -> NEEDS_INFO

        Args:
            verdict: Verdict instance
        """
        self.verdict = verdict
        if verdict.type == VerdictType.TRUE_POSITIVE:
            self.status = BeadStatus.CONFIRMED
        elif verdict.type == VerdictType.FALSE_POSITIVE:
            self.status = BeadStatus.REJECTED
        else:
            self.status = BeadStatus.NEEDS_INFO
        self.updated_at = datetime.now()
        self._run_post_bead_learning()

    def _run_post_bead_learning(self) -> None:
        """Trigger post-bead learning pipeline if enabled."""
        try:
            from alphaswarm_sol.learning.post_bead import PostBeadLearner

            PostBeadLearner().process(self)
        except Exception:
            # Learning is optional; ignore failures to avoid blocking verdicts
            return

    def is_complete(self) -> bool:
        """Check if bead has all required fields populated.

        Required for a bead to be considered complete:
        - Has an ID
        - Has vulnerable code
        - Has at least one investigation step
        - Has at least one question to answer
        - Has a reason for why it was flagged

        Returns:
            True if all required fields are present
        """
        required_checks = [
            bool(self.id),
            bool(self.vulnerable_code.source),
            len(self.investigation_guide.steps) > 0,
            len(self.investigation_guide.questions_to_answer) > 0,
            bool(self.pattern_context.why_flagged),
        ]
        return all(required_checks)

    def get_llm_prompt(self) -> str:
        """Generate a prompt for LLM investigation.

        This is the key method - produces a self-contained prompt
        that an LLM can use to investigate without additional context.

        The prompt includes:
        - Summary with severity and pattern info
        - Why the code was flagged
        - The vulnerable code snippet
        - Related code (if any)
        - Investigation steps
        - Questions to answer
        - Common false positives to check
        - Similar real-world exploits
        - The task: determine TP/FP with evidence

        Returns:
            Complete investigation prompt string
        """
        prompt = f"""# Vulnerability Investigation: {self.id}

## Summary
- **Class:** {self.vulnerability_class}
- **Severity:** {self.severity.value}
- **Confidence:** {self.confidence:.0%}
- **Pattern:** {self.pattern_context.pattern_name}

## Why Flagged
{self.pattern_context.why_flagged}

## Vulnerable Code
```solidity
{self.vulnerable_code.source}
```
File: {self.vulnerable_code.file_path}
Lines: {self.vulnerable_code.start_line}-{self.vulnerable_code.end_line}
"""

        if self.related_code:
            prompt += "\n## Related Code\n"
            for i, snippet in enumerate(self.related_code, 1):
                name = snippet.function_name or "unknown"
                prompt += f"""
### Related #{i}: {name}
```solidity
{snippet.source}
```
Location: {snippet.location}
"""

        if self.investigation_guide.steps:
            prompt += "\n## Investigation Steps\n"
            for step in self.investigation_guide.steps:
                prompt += f"""
### Step {step.step_number}: {step.action}
- **Look for:** {step.look_for}
- **Evidence needed:** {step.evidence_needed}
"""
                if step.red_flag:
                    prompt += f"- **Red flag:** {step.red_flag}\n"
                if step.safe_if:
                    prompt += f"- **Safe if:** {step.safe_if}\n"

        if self.investigation_guide.questions_to_answer:
            prompt += "\n## Questions to Answer\n"
            for q in self.investigation_guide.questions_to_answer:
                prompt += f"- {q}\n"

        if self.investigation_guide.common_false_positives:
            prompt += "\n## Common False Positives\n"
            for fp in self.investigation_guide.common_false_positives:
                prompt += f"- {fp}\n"

        if self.investigation_guide.safe_patterns:
            prompt += "\n## Safe Patterns (would make this NOT vulnerable)\n"
            for sp in self.investigation_guide.safe_patterns:
                prompt += f"- {sp}\n"

        if self.similar_exploits:
            prompt += "\n## Similar Real-World Exploits\n"
            for exploit in self.similar_exploits:
                prompt += f"- **{exploit.name}** ({exploit.date}): {exploit.loss}\n"
                prompt += f"  {exploit.exploit_summary}\n"

        if self.fix_recommendations:
            prompt += "\n## Fix Recommendations\n"
            for fix in self.fix_recommendations:
                prompt += f"- {fix}\n"

        prompt += """
## Your Task
Based on the above information, determine:
1. Is this a TRUE POSITIVE (real vulnerability) or FALSE POSITIVE?
2. What specific evidence supports your conclusion?
3. If TRUE POSITIVE: What is the attack scenario?
4. If FALSE POSITIVE: What makes the code safe?

Provide your verdict with confidence level and reasoning.
"""
        return prompt

    def get_compact_summary(self) -> str:
        """Get a compact one-line summary of the bead.

        Returns:
            Summary like "VKG-001 [critical] reentrancy in Vault.withdraw() - PENDING"
        """
        location = f"{self.vulnerable_code.contract_name or 'unknown'}.{self.vulnerable_code.function_name or 'unknown'}()"
        return f"{self.id} [{self.severity.value}] {self.vulnerability_class} in {location} - {self.status.value.upper()}"

    def to_minimal_yaml(self) -> str:
        """Serialize bead to minimal YAML for pool storage.

        Produces a human-readable YAML format with essential fields only.
        Used for storing beads in pool directories.

        Returns:
            YAML string with minimal bead representation

        Usage:
            yaml_str = bead.to_minimal_yaml()
            with open(f"pool/{pool_id}/beads/{bead.id}.yaml", "w") as f:
                f.write(yaml_str)
        """
        import yaml

        minimal = {
            "id": self.id,
            "vulnerability_class": self.vulnerability_class,
            "pattern_id": self.pattern_id,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "status": self.status.value,
            "location": {
                "contract": self.vulnerable_code.contract_name,
                "function": self.vulnerable_code.function_name,
                "file": self.vulnerable_code.file_path,
                "lines": f"{self.vulnerable_code.start_line}-{self.vulnerable_code.end_line}",
            },
            "why_flagged": self.pattern_context.why_flagged,
            "human_flag": self.human_flag,
        }

        # Include pool association if set
        if self.pool_id:
            minimal["pool_id"] = self.pool_id

        # Include debate outcomes if present
        if self.debate_summary:
            minimal["debate"] = {
                "summary": self.debate_summary,
                "attacker_claim": self.attacker_claim,
                "defender_claim": self.defender_claim,
                "verifier_verdict": self.verifier_verdict,
            }

        # Include work state for agent resumption if present
        if self.work_state:
            minimal["work_state"] = {
                "state": self.work_state,
                "last_agent": self.last_agent,
                "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            }

        # Include verdict if present
        if self.verdict:
            minimal["verdict"] = {
                "type": self.verdict.type.value,
                "reason": self.verdict.reason,
                "confidence": self.verdict.confidence,
            }

        return yaml.dump(minimal, default_flow_style=False, sort_keys=False)

    @property
    def is_resolved(self) -> bool:
        """Whether this bead has a final verdict."""
        return self.status in (BeadStatus.CONFIRMED, BeadStatus.REJECTED)

    @property
    def is_true_positive(self) -> bool:
        """Whether this bead was confirmed as a true positive."""
        return self.status == BeadStatus.CONFIRMED

    @property
    def is_false_positive(self) -> bool:
        """Whether this bead was rejected as a false positive."""
        return self.status == BeadStatus.REJECTED


# Export for module
__all__ = [
    "VulnerabilityBead",
    "TestContext",
    "PatternContext",
    "InvestigationGuide",
]
