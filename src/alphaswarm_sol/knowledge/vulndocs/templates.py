"""VulnDocs Document Templates.

Phase 17.2: Document Templates for VulnDocs.

This module provides template dataclasses and rendering functions for the
four document types in the VulnDocs knowledge system:

1. detection.md - How to detect the vulnerability
2. patterns.md - Code patterns (vulnerable and safe)
3. exploits.md - Real-world exploits
4. fixes.md - Remediation guidance

Templates produce LLM-friendly markdown that can be cached for prompt efficiency.

Usage:
    from alphaswarm_sol.knowledge.vulndocs.templates import (
        DetectionTemplate,
        PatternsTemplate,
        ExploitsTemplate,
        FixesTemplate,
        render_detection_md,
        render_patterns_md,
        render_exploits_md,
        render_fixes_md,
        generate_document_templates,
    )

    # Create a detection template
    template = DetectionTemplate(
        subcategory_id="classic",
        subcategory_name="Classic Reentrancy",
        overview="State write after external call",
        signals=[...],
        behavioral_signatures=[...],
    )

    # Render to markdown
    md = render_detection_md(
        subcategory=template.subcategory_name,
        signals=template.signals,
        checks=template.detection_checklist,
    )

    # Or use the template's render method
    md = template.render()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from alphaswarm_sol.knowledge.vulndocs.schema import (
    CodePattern,
    DocumentType,
    ExploitReference,
    FixRecommendation,
    GraphSignal,
    OperationSequences,
)


# =============================================================================
# CONSTANTS
# =============================================================================

TEMPLATE_VERSION = "1.0"

# Token budget guidelines for LLM efficiency
TOKEN_BUDGET = {
    "detection": 1500,
    "patterns": 2000,
    "exploits": 1500,
    "fixes": 1200,
}


# =============================================================================
# TEMPLATE DATACLASSES
# =============================================================================


@dataclass
class DetectionTemplate:
    """Template for detection.md document.

    Contains structured data for generating detection guidance.
    Focuses on graph signals, behavioral signatures, and detection checklist.

    Attributes:
        subcategory_id: Unique identifier for the subcategory
        subcategory_name: Human-readable name
        category_id: Parent category identifier
        category_name: Parent category human-readable name
        overview: Brief overview of the vulnerability and detection approach
        signals: List of graph signals that indicate the vulnerability
        behavioral_signatures: List of behavioral signature patterns
        operation_sequences: Vulnerable and safe operation sequences
        detection_checklist: List of detection checks to perform
        false_positive_indicators: Conditions that indicate false positives
        severity: Severity level (critical, high, medium, low)
        confidence_notes: Notes about detection confidence
        related_patterns: List of related pattern IDs
    """

    subcategory_id: str
    subcategory_name: str
    category_id: str = ""
    category_name: str = ""
    overview: str = ""
    signals: List[GraphSignal] = field(default_factory=list)
    behavioral_signatures: List[str] = field(default_factory=list)
    operation_sequences: Optional[OperationSequences] = None
    detection_checklist: List[str] = field(default_factory=list)
    false_positive_indicators: List[str] = field(default_factory=list)
    severity: str = "high"
    confidence_notes: str = ""
    related_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "subcategory_id": self.subcategory_id,
            "subcategory_name": self.subcategory_name,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "overview": self.overview,
            "signals": [s.to_dict() for s in self.signals],
            "behavioral_signatures": self.behavioral_signatures,
            "detection_checklist": self.detection_checklist,
            "false_positive_indicators": self.false_positive_indicators,
            "severity": self.severity,
            "confidence_notes": self.confidence_notes,
            "related_patterns": self.related_patterns,
        }
        if self.operation_sequences:
            result["operation_sequences"] = self.operation_sequences.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectionTemplate":
        """Deserialize from dictionary."""
        op_seq = data.get("operation_sequences")
        return cls(
            subcategory_id=data.get("subcategory_id", ""),
            subcategory_name=data.get("subcategory_name", ""),
            category_id=data.get("category_id", ""),
            category_name=data.get("category_name", ""),
            overview=data.get("overview", ""),
            signals=[GraphSignal.from_dict(s) for s in data.get("signals", [])],
            behavioral_signatures=data.get("behavioral_signatures", []),
            operation_sequences=OperationSequences.from_dict(op_seq) if op_seq else None,
            detection_checklist=data.get("detection_checklist", []),
            false_positive_indicators=data.get("false_positive_indicators", []),
            severity=data.get("severity", "high"),
            confidence_notes=data.get("confidence_notes", ""),
            related_patterns=data.get("related_patterns", []),
        )

    def render(self) -> str:
        """Render template to markdown."""
        return render_detection_md(
            subcategory=self.subcategory_name,
            signals=self.signals,
            checks=self.detection_checklist,
            overview=self.overview,
            behavioral_signatures=self.behavioral_signatures,
            operation_sequences=self.operation_sequences,
            false_positive_indicators=self.false_positive_indicators,
            severity=self.severity,
            confidence_notes=self.confidence_notes,
            related_patterns=self.related_patterns,
            category=self.category_name,
        )


@dataclass
class PatternsTemplate:
    """Template for patterns.md document.

    Contains structured data for generating code pattern documentation.
    Shows both vulnerable and safe code variants.

    Attributes:
        subcategory_id: Unique identifier for the subcategory
        subcategory_name: Human-readable name
        category_id: Parent category identifier
        overview: Brief overview of the patterns
        vulnerable_patterns: List of vulnerable code patterns
        safe_patterns: List of safe code patterns
        edge_cases: List of edge case descriptions
        pattern_ids: List of associated VKG pattern IDs
        common_mistakes: List of common implementation mistakes
        best_practices: List of best practice recommendations
    """

    subcategory_id: str
    subcategory_name: str
    category_id: str = ""
    overview: str = ""
    vulnerable_patterns: List[CodePattern] = field(default_factory=list)
    safe_patterns: List[CodePattern] = field(default_factory=list)
    edge_cases: List[str] = field(default_factory=list)
    pattern_ids: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "subcategory_id": self.subcategory_id,
            "subcategory_name": self.subcategory_name,
            "category_id": self.category_id,
            "overview": self.overview,
            "vulnerable_patterns": [p.to_dict() for p in self.vulnerable_patterns],
            "safe_patterns": [p.to_dict() for p in self.safe_patterns],
            "edge_cases": self.edge_cases,
            "pattern_ids": self.pattern_ids,
            "common_mistakes": self.common_mistakes,
            "best_practices": self.best_practices,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternsTemplate":
        """Deserialize from dictionary."""
        return cls(
            subcategory_id=data.get("subcategory_id", ""),
            subcategory_name=data.get("subcategory_name", ""),
            category_id=data.get("category_id", ""),
            overview=data.get("overview", ""),
            vulnerable_patterns=[
                CodePattern.from_dict(p) for p in data.get("vulnerable_patterns", [])
            ],
            safe_patterns=[
                CodePattern.from_dict(p) for p in data.get("safe_patterns", [])
            ],
            edge_cases=data.get("edge_cases", []),
            pattern_ids=data.get("pattern_ids", []),
            common_mistakes=data.get("common_mistakes", []),
            best_practices=data.get("best_practices", []),
        )

    def render(self) -> str:
        """Render template to markdown."""
        return render_patterns_md(
            subcategory=self.subcategory_name,
            vulnerable_patterns=self.vulnerable_patterns,
            safe_patterns=self.safe_patterns,
            overview=self.overview,
            edge_cases=self.edge_cases,
            pattern_ids=self.pattern_ids,
            common_mistakes=self.common_mistakes,
            best_practices=self.best_practices,
        )


@dataclass
class ExploitIncident:
    """A real-world exploit incident with full details.

    Extends ExploitReference with additional incident-specific fields.

    Attributes:
        id: Unique incident identifier
        name: Incident name (e.g., "DAO Hack")
        date: Date of incident (ISO format)
        loss_usd: Financial loss in USD
        protocol: Affected protocol name
        chain: Blockchain (e.g., ethereum, bsc)
        description: Detailed description of the exploit
        attack_vector: High-level attack vector description
        attack_steps: Step-by-step attack sequence
        root_cause: Root cause of the vulnerability
        postmortem_url: Link to postmortem analysis
        tx_hash: Transaction hash of the exploit
        cve_id: CVE identifier if available
        solodit_id: Solodit finding ID if available
        attacker_address: Address of the attacker
        victim_contracts: List of affected contract addresses
    """

    id: str
    name: str
    date: str = ""
    loss_usd: str = ""
    protocol: str = ""
    chain: str = "ethereum"
    description: str = ""
    attack_vector: str = ""
    attack_steps: List[str] = field(default_factory=list)
    root_cause: str = ""
    postmortem_url: str = ""
    tx_hash: str = ""
    cve_id: str = ""
    solodit_id: str = ""
    attacker_address: str = ""
    victim_contracts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date,
            "loss_usd": self.loss_usd,
            "protocol": self.protocol,
            "chain": self.chain,
            "description": self.description,
            "attack_vector": self.attack_vector,
            "attack_steps": self.attack_steps,
            "root_cause": self.root_cause,
            "postmortem_url": self.postmortem_url,
            "tx_hash": self.tx_hash,
            "cve_id": self.cve_id,
            "solodit_id": self.solodit_id,
            "attacker_address": self.attacker_address,
            "victim_contracts": self.victim_contracts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExploitIncident":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            date=data.get("date", ""),
            loss_usd=data.get("loss_usd", ""),
            protocol=data.get("protocol", ""),
            chain=data.get("chain", "ethereum"),
            description=data.get("description", ""),
            attack_vector=data.get("attack_vector", ""),
            attack_steps=data.get("attack_steps", []),
            root_cause=data.get("root_cause", ""),
            postmortem_url=data.get("postmortem_url", ""),
            tx_hash=data.get("tx_hash", ""),
            cve_id=data.get("cve_id", ""),
            solodit_id=data.get("solodit_id", ""),
            attacker_address=data.get("attacker_address", ""),
            victim_contracts=data.get("victim_contracts", []),
        )

    @classmethod
    def from_exploit_reference(cls, ref: ExploitReference) -> "ExploitIncident":
        """Create from ExploitReference."""
        return cls(
            id=ref.id,
            name=ref.name,
            date=ref.date,
            loss_usd=ref.loss_usd,
            protocol=ref.protocol,
            chain=ref.chain,
            description=ref.description,
            attack_steps=ref.attack_steps,
            postmortem_url=ref.postmortem_url,
            tx_hash=ref.tx_hash,
            cve_id=ref.cve_id,
            solodit_id=ref.solodit_id,
        )


@dataclass
class ExploitsTemplate:
    """Template for exploits.md document.

    Contains structured data for documenting real-world exploits.

    Attributes:
        subcategory_id: Unique identifier for the subcategory
        subcategory_name: Human-readable name
        category_id: Parent category identifier
        overview: Brief overview of exploit history
        incidents: List of exploit incidents
        attack_vectors: List of high-level attack vector descriptions
        total_losses: Total financial losses in USD
        common_targets: Types of protocols commonly targeted
        prevention_timeline: Key dates and prevention milestones
    """

    subcategory_id: str
    subcategory_name: str
    category_id: str = ""
    overview: str = ""
    incidents: List[ExploitIncident] = field(default_factory=list)
    attack_vectors: List[str] = field(default_factory=list)
    total_losses: str = ""
    common_targets: List[str] = field(default_factory=list)
    prevention_timeline: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "subcategory_id": self.subcategory_id,
            "subcategory_name": self.subcategory_name,
            "category_id": self.category_id,
            "overview": self.overview,
            "incidents": [i.to_dict() for i in self.incidents],
            "attack_vectors": self.attack_vectors,
            "total_losses": self.total_losses,
            "common_targets": self.common_targets,
            "prevention_timeline": self.prevention_timeline,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExploitsTemplate":
        """Deserialize from dictionary."""
        return cls(
            subcategory_id=data.get("subcategory_id", ""),
            subcategory_name=data.get("subcategory_name", ""),
            category_id=data.get("category_id", ""),
            overview=data.get("overview", ""),
            incidents=[
                ExploitIncident.from_dict(i) for i in data.get("incidents", [])
            ],
            attack_vectors=data.get("attack_vectors", []),
            total_losses=data.get("total_losses", ""),
            common_targets=data.get("common_targets", []),
            prevention_timeline=data.get("prevention_timeline", []),
        )

    def render(self) -> str:
        """Render template to markdown."""
        return render_exploits_md(
            subcategory=self.subcategory_name,
            exploits=self.incidents,
            overview=self.overview,
            attack_vectors=self.attack_vectors,
            total_losses=self.total_losses,
            common_targets=self.common_targets,
        )


@dataclass
class FixRecommendationExtended:
    """Extended fix recommendation with additional guidance.

    Extends FixRecommendation with testing strategies and migration notes.

    Attributes:
        name: Name of the fix approach
        description: Detailed description of the fix
        code_example: Example code implementing the fix
        effectiveness: Effectiveness rating (high, medium, low)
        complexity: Implementation complexity (high, medium, low)
        testing_strategy: How to test the fix
        migration_notes: Notes for migrating existing code
        gas_impact: Expected gas impact
        dependencies: Required dependencies or imports
    """

    name: str
    description: str
    code_example: str = ""
    effectiveness: str = "high"
    complexity: str = "low"
    testing_strategy: str = ""
    migration_notes: str = ""
    gas_impact: str = ""
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "code_example": self.code_example,
            "effectiveness": self.effectiveness,
            "complexity": self.complexity,
            "testing_strategy": self.testing_strategy,
            "migration_notes": self.migration_notes,
            "gas_impact": self.gas_impact,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FixRecommendationExtended":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            code_example=data.get("code_example", ""),
            effectiveness=data.get("effectiveness", "high"),
            complexity=data.get("complexity", "low"),
            testing_strategy=data.get("testing_strategy", ""),
            migration_notes=data.get("migration_notes", ""),
            gas_impact=data.get("gas_impact", ""),
            dependencies=data.get("dependencies", []),
        )

    @classmethod
    def from_fix_recommendation(cls, rec: FixRecommendation) -> "FixRecommendationExtended":
        """Create from FixRecommendation."""
        return cls(
            name=rec.name,
            description=rec.description,
            code_example=rec.code_example,
            effectiveness=rec.effectiveness,
            complexity=rec.complexity,
        )


@dataclass
class FixesTemplate:
    """Template for fixes.md document.

    Contains structured data for documenting remediation guidance.

    Attributes:
        subcategory_id: Unique identifier for the subcategory
        subcategory_name: Human-readable name
        category_id: Parent category identifier
        overview: Brief overview of remediation approaches
        recommendations: List of fix recommendations
        code_examples: Additional code examples
        testing_strategies: List of testing strategies
        tools: Recommended tools for prevention
        audit_checklist: Checklist for auditors
    """

    subcategory_id: str
    subcategory_name: str
    category_id: str = ""
    overview: str = ""
    recommendations: List[FixRecommendationExtended] = field(default_factory=list)
    code_examples: List[Dict[str, str]] = field(default_factory=list)
    testing_strategies: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    audit_checklist: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "subcategory_id": self.subcategory_id,
            "subcategory_name": self.subcategory_name,
            "category_id": self.category_id,
            "overview": self.overview,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "code_examples": self.code_examples,
            "testing_strategies": self.testing_strategies,
            "tools": self.tools,
            "audit_checklist": self.audit_checklist,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FixesTemplate":
        """Deserialize from dictionary."""
        return cls(
            subcategory_id=data.get("subcategory_id", ""),
            subcategory_name=data.get("subcategory_name", ""),
            category_id=data.get("category_id", ""),
            overview=data.get("overview", ""),
            recommendations=[
                FixRecommendationExtended.from_dict(r)
                for r in data.get("recommendations", [])
            ],
            code_examples=data.get("code_examples", []),
            testing_strategies=data.get("testing_strategies", []),
            tools=data.get("tools", []),
            audit_checklist=data.get("audit_checklist", []),
        )

    def render(self) -> str:
        """Render template to markdown."""
        return render_fixes_md(
            subcategory=self.subcategory_name,
            recommendations=self.recommendations,
            overview=self.overview,
            code_examples=self.code_examples,
            testing_strategies=self.testing_strategies,
            tools=self.tools,
            audit_checklist=self.audit_checklist,
        )


# =============================================================================
# TEMPLATE RENDERING FUNCTIONS
# =============================================================================


def render_detection_md(
    subcategory: str,
    signals: List[GraphSignal],
    checks: List[str],
    overview: str = "",
    behavioral_signatures: Optional[List[str]] = None,
    operation_sequences: Optional[OperationSequences] = None,
    false_positive_indicators: Optional[List[str]] = None,
    severity: str = "",
    confidence_notes: str = "",
    related_patterns: Optional[List[str]] = None,
    category: str = "",
) -> str:
    """Render detection document to markdown.

    Produces LLM-friendly markdown with structured sections for vulnerability
    detection guidance.

    Args:
        subcategory: Subcategory name (e.g., "Classic Reentrancy")
        signals: List of graph signals for detection
        checks: Detection checklist items
        overview: Overview description
        behavioral_signatures: Behavioral signature patterns
        operation_sequences: Vulnerable and safe operation sequences
        false_positive_indicators: False positive conditions
        severity: Severity level
        confidence_notes: Notes about detection confidence
        related_patterns: Related pattern IDs
        category: Parent category name

    Returns:
        Formatted markdown string
    """
    lines = [f"# Detection: {subcategory}", ""]

    # Category and severity header
    if category or severity:
        if category:
            lines.append(f"**Category:** {category}")
        if severity:
            lines.append(f"**Severity:** {severity}")
        lines.append("")

    # Overview section
    if overview:
        lines.append("## Overview")
        lines.append("")
        lines.append(overview)
        lines.append("")

    # Graph Signals section
    if signals:
        lines.append("## Graph Signals")
        lines.append("")
        lines.append("| Property | Expected | Critical? |")
        lines.append("|----------|----------|-----------|")
        for sig in signals:
            critical = "YES" if sig.critical else "NO"
            lines.append(f"| `{sig.property_name}` | {sig.expected} | {critical} |")
        lines.append("")

    # Behavioral Signatures section
    if behavioral_signatures:
        lines.append("## Behavioral Signatures")
        lines.append("")
        for sig in behavioral_signatures:
            lines.append(f"- `{sig}`")
        lines.append("")

    # Operation Sequences section
    if operation_sequences:
        lines.append("## Operation Sequences")
        lines.append("")
        if operation_sequences.vulnerable:
            lines.append("**Vulnerable Sequences:**")
            for seq in operation_sequences.vulnerable:
                lines.append(f"- `{seq}`")
            lines.append("")
        if operation_sequences.safe:
            lines.append("**Safe Sequences:**")
            for seq in operation_sequences.safe:
                lines.append(f"- `{seq}`")
            lines.append("")

    # Detection Checklist section
    if checks:
        lines.append("## Detection Checklist")
        lines.append("")
        for check in checks:
            lines.append(f"- [ ] {check}")
        lines.append("")

    # False Positive Indicators section
    if false_positive_indicators:
        lines.append("## False Positive Indicators")
        lines.append("")
        lines.append("The following conditions indicate a potential false positive:")
        lines.append("")
        for indicator in false_positive_indicators:
            lines.append(f"- {indicator}")
        lines.append("")

    # Confidence Notes section
    if confidence_notes:
        lines.append("## Confidence Notes")
        lines.append("")
        lines.append(confidence_notes)
        lines.append("")

    # Related Patterns section
    if related_patterns:
        lines.append("## Related Patterns")
        lines.append("")
        lines.append(f"**Pattern IDs:** {', '.join(related_patterns)}")
        lines.append("")

    return "\n".join(lines)


def render_patterns_md(
    subcategory: str,
    vulnerable_patterns: List[CodePattern],
    safe_patterns: List[CodePattern],
    overview: str = "",
    edge_cases: Optional[List[str]] = None,
    pattern_ids: Optional[List[str]] = None,
    common_mistakes: Optional[List[str]] = None,
    best_practices: Optional[List[str]] = None,
) -> str:
    """Render patterns document to markdown.

    Produces LLM-friendly markdown showing vulnerable and safe code patterns.

    Args:
        subcategory: Subcategory name
        vulnerable_patterns: List of vulnerable code patterns
        safe_patterns: List of safe code patterns
        overview: Overview description
        edge_cases: Edge case descriptions
        pattern_ids: Associated VKG pattern IDs
        common_mistakes: Common implementation mistakes
        best_practices: Best practice recommendations

    Returns:
        Formatted markdown string
    """
    lines = [f"# Patterns: {subcategory}", ""]

    # Overview section
    if overview:
        lines.append("## Overview")
        lines.append("")
        lines.append(overview)
        lines.append("")

    # Pattern IDs section
    if pattern_ids:
        lines.append(f"**Associated Pattern IDs:** {', '.join(pattern_ids)}")
        lines.append("")

    # Vulnerable Patterns section
    if vulnerable_patterns:
        lines.append("## Vulnerable Patterns")
        lines.append("")
        for pattern in vulnerable_patterns:
            lines.append(f"### {pattern.name}")
            lines.append("")
            if pattern.description:
                lines.append(pattern.description)
                lines.append("")
            lines.append(f"**Severity:** {pattern.severity}")
            lines.append("")
            lines.append("```solidity")
            lines.append(pattern.vulnerable_code)
            lines.append("```")
            lines.append("")

    # Safe Patterns section
    if safe_patterns:
        lines.append("## Safe Patterns")
        lines.append("")
        for pattern in safe_patterns:
            lines.append(f"### {pattern.name}")
            lines.append("")
            if pattern.description:
                lines.append(pattern.description)
                lines.append("")
            if pattern.safe_code:
                lines.append("```solidity")
                lines.append(pattern.safe_code)
                lines.append("```")
            elif pattern.vulnerable_code:
                # For safe patterns, the "vulnerable_code" field may hold the safe code
                lines.append("```solidity")
                lines.append(pattern.vulnerable_code)
                lines.append("```")
            lines.append("")

    # Edge Cases section
    if edge_cases:
        lines.append("## Edge Cases")
        lines.append("")
        for case in edge_cases:
            lines.append(f"- {case}")
        lines.append("")

    # Common Mistakes section
    if common_mistakes:
        lines.append("## Common Mistakes")
        lines.append("")
        for mistake in common_mistakes:
            lines.append(f"- {mistake}")
        lines.append("")

    # Best Practices section
    if best_practices:
        lines.append("## Best Practices")
        lines.append("")
        for practice in best_practices:
            lines.append(f"- {practice}")
        lines.append("")

    return "\n".join(lines)


def render_exploits_md(
    subcategory: str,
    exploits: List[Union[ExploitIncident, ExploitReference]],
    overview: str = "",
    attack_vectors: Optional[List[str]] = None,
    total_losses: str = "",
    common_targets: Optional[List[str]] = None,
) -> str:
    """Render exploits document to markdown.

    Produces LLM-friendly markdown documenting real-world exploits.

    Args:
        subcategory: Subcategory name
        exploits: List of exploit incidents
        overview: Overview of exploit history
        attack_vectors: High-level attack vector descriptions
        total_losses: Total financial losses
        common_targets: Commonly targeted protocol types

    Returns:
        Formatted markdown string
    """
    lines = [f"# Exploits: {subcategory}", ""]

    # Overview section
    if overview:
        lines.append("## Overview")
        lines.append("")
        lines.append(overview)
        lines.append("")

    # Summary statistics
    if total_losses or common_targets:
        lines.append("## Summary")
        lines.append("")
        if total_losses:
            lines.append(f"**Total Losses:** ${total_losses}")
        if common_targets:
            lines.append(f"**Common Targets:** {', '.join(common_targets)}")
        lines.append("")

    # Attack Vectors section
    if attack_vectors:
        lines.append("## Attack Vectors")
        lines.append("")
        for vector in attack_vectors:
            lines.append(f"- {vector}")
        lines.append("")

    # Incidents section
    if exploits:
        lines.append("## Incidents")
        lines.append("")
        for exploit in exploits:
            # Handle both ExploitIncident and ExploitReference
            name = exploit.name
            date = getattr(exploit, "date", "")
            loss_usd = getattr(exploit, "loss_usd", "")
            protocol = getattr(exploit, "protocol", "")
            chain = getattr(exploit, "chain", "ethereum")
            description = getattr(exploit, "description", "")
            postmortem_url = getattr(exploit, "postmortem_url", "")
            attack_steps = getattr(exploit, "attack_steps", [])

            lines.append(f"### {name}")
            lines.append("")

            # Metadata table
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            if date:
                lines.append(f"| Date | {date} |")
            if loss_usd:
                lines.append(f"| Loss | ${loss_usd} |")
            if protocol:
                lines.append(f"| Protocol | {protocol} |")
            if chain:
                lines.append(f"| Chain | {chain} |")
            lines.append("")

            # Description
            if description:
                lines.append(description)
                lines.append("")

            # Attack steps
            if attack_steps:
                lines.append("**Attack Steps:**")
                lines.append("")
                for i, step in enumerate(attack_steps, 1):
                    lines.append(f"{i}. {step}")
                lines.append("")

            # Postmortem link
            if postmortem_url:
                lines.append(f"**Postmortem:** [{postmortem_url}]({postmortem_url})")
                lines.append("")

    return "\n".join(lines)


def render_fixes_md(
    subcategory: str,
    recommendations: List[Union[FixRecommendationExtended, FixRecommendation]],
    overview: str = "",
    code_examples: Optional[List[Dict[str, str]]] = None,
    testing_strategies: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    audit_checklist: Optional[List[str]] = None,
) -> str:
    """Render fixes document to markdown.

    Produces LLM-friendly markdown with remediation guidance.

    Args:
        subcategory: Subcategory name
        recommendations: List of fix recommendations
        overview: Overview of remediation approaches
        code_examples: Additional code examples
        testing_strategies: Testing strategies
        tools: Recommended tools
        audit_checklist: Auditor checklist

    Returns:
        Formatted markdown string
    """
    lines = [f"# Fixes: {subcategory}", ""]

    # Overview section
    if overview:
        lines.append("## Overview")
        lines.append("")
        lines.append(overview)
        lines.append("")

    # Recommendations section
    if recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in recommendations:
            lines.append(f"### {rec.name}")
            lines.append("")
            lines.append(rec.description)
            lines.append("")

            # Metadata
            lines.append(f"**Effectiveness:** {rec.effectiveness}")
            lines.append(f"**Complexity:** {rec.complexity}")

            # Gas impact (if available on extended type)
            gas_impact = getattr(rec, "gas_impact", "")
            if gas_impact:
                lines.append(f"**Gas Impact:** {gas_impact}")

            lines.append("")

            # Code example
            if rec.code_example:
                lines.append("**Code Example:**")
                lines.append("")
                lines.append("```solidity")
                lines.append(rec.code_example)
                lines.append("```")
                lines.append("")

            # Testing strategy (if available on extended type)
            testing_strategy = getattr(rec, "testing_strategy", "")
            if testing_strategy:
                lines.append("**Testing Strategy:**")
                lines.append("")
                lines.append(testing_strategy)
                lines.append("")

            # Migration notes (if available on extended type)
            migration_notes = getattr(rec, "migration_notes", "")
            if migration_notes:
                lines.append("**Migration Notes:**")
                lines.append("")
                lines.append(migration_notes)
                lines.append("")

            # Dependencies (if available on extended type)
            dependencies = getattr(rec, "dependencies", [])
            if dependencies:
                lines.append("**Dependencies:**")
                lines.append("")
                for dep in dependencies:
                    lines.append(f"- {dep}")
                lines.append("")

    # Additional Code Examples section
    if code_examples:
        lines.append("## Code Examples")
        lines.append("")
        for example in code_examples:
            name = example.get("name", "Example")
            code = example.get("code", "")
            desc = example.get("description", "")

            lines.append(f"### {name}")
            lines.append("")
            if desc:
                lines.append(desc)
                lines.append("")
            if code:
                lines.append("```solidity")
                lines.append(code)
                lines.append("```")
                lines.append("")

    # Testing Strategies section
    if testing_strategies:
        lines.append("## Testing Strategies")
        lines.append("")
        for strategy in testing_strategies:
            lines.append(f"- {strategy}")
        lines.append("")

    # Tools section
    if tools:
        lines.append("## Recommended Tools")
        lines.append("")
        for tool in tools:
            lines.append(f"- {tool}")
        lines.append("")

    # Audit Checklist section
    if audit_checklist:
        lines.append("## Audit Checklist")
        lines.append("")
        for item in audit_checklist:
            lines.append(f"- [ ] {item}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# TEMPLATE GENERATION CLI HELPER
# =============================================================================


def generate_document_templates(
    category_id: str,
    subcategory_id: str,
    category_name: str = "",
    subcategory_name: str = "",
) -> Dict[str, str]:
    """Generate all four document templates for a subcategory.

    Creates skeleton templates with placeholder content that can be
    filled in later. Useful for bootstrapping new subcategories.

    Args:
        category_id: Category identifier (e.g., "reentrancy")
        subcategory_id: Subcategory identifier (e.g., "classic")
        category_name: Human-readable category name (optional)
        subcategory_name: Human-readable subcategory name (optional)

    Returns:
        Dictionary with keys: "detection", "patterns", "exploits", "fixes"
        Values are the rendered markdown strings
    """
    # Default names if not provided
    if not category_name:
        category_name = category_id.replace("-", " ").title()
    if not subcategory_name:
        subcategory_name = subcategory_id.replace("-", " ").title()

    # Create placeholder templates
    detection_template = DetectionTemplate(
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        category_id=category_id,
        category_name=category_name,
        overview=f"[TODO: Add overview for {subcategory_name} detection]",
        signals=[
            GraphSignal(
                property_name="[property_name]",
                expected=True,
                critical=True,
                description="[TODO: Add signal description]",
            )
        ],
        behavioral_signatures=["[TODO: Add behavioral signature]"],
        operation_sequences=OperationSequences(
            vulnerable=["[TODO: Add vulnerable sequence]"],
            safe=["[TODO: Add safe sequence]"],
        ),
        detection_checklist=[
            "[TODO: Add detection check 1]",
            "[TODO: Add detection check 2]",
        ],
        false_positive_indicators=["[TODO: Add false positive indicator]"],
        severity="high",
        related_patterns=["[pattern-id]"],
    )

    patterns_template = PatternsTemplate(
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        category_id=category_id,
        overview=f"[TODO: Add overview for {subcategory_name} patterns]",
        vulnerable_patterns=[
            CodePattern(
                name=f"Vulnerable {subcategory_name}",
                vulnerable_code="// [TODO: Add vulnerable code]\nfunction example() public {\n    // Vulnerable pattern\n}",
                description="[TODO: Add description]",
                severity="high",
            )
        ],
        safe_patterns=[
            CodePattern(
                name=f"Safe {subcategory_name}",
                vulnerable_code="// [TODO: Add safe code]\nfunction example() public {\n    // Safe pattern\n}",
                description="[TODO: Add description]",
                severity="informational",
            )
        ],
        edge_cases=["[TODO: Add edge case]"],
        pattern_ids=["[pattern-id]"],
        common_mistakes=["[TODO: Add common mistake]"],
        best_practices=["[TODO: Add best practice]"],
    )

    exploits_template = ExploitsTemplate(
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        category_id=category_id,
        overview=f"[TODO: Add overview for {subcategory_name} exploits]",
        incidents=[
            ExploitIncident(
                id=f"{subcategory_id}-001",
                name="[TODO: Exploit Name]",
                date="[YYYY-MM-DD]",
                loss_usd="[amount]",
                protocol="[Protocol Name]",
                chain="ethereum",
                description="[TODO: Add description]",
                attack_steps=[
                    "[TODO: Step 1]",
                    "[TODO: Step 2]",
                ],
                postmortem_url="[URL]",
            )
        ],
        attack_vectors=["[TODO: Add attack vector]"],
        total_losses="[TODO]",
        common_targets=["[TODO: Add target type]"],
    )

    fixes_template = FixesTemplate(
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        category_id=category_id,
        overview=f"[TODO: Add overview for {subcategory_name} fixes]",
        recommendations=[
            FixRecommendationExtended(
                name="[TODO: Fix Name]",
                description="[TODO: Add description]",
                code_example="// [TODO: Add fix code]\nfunction example() public {\n    // Fixed pattern\n}",
                effectiveness="high",
                complexity="low",
                testing_strategy="[TODO: Add testing strategy]",
                migration_notes="[TODO: Add migration notes]",
            )
        ],
        code_examples=[
            {
                "name": "[TODO: Example Name]",
                "code": "// [TODO: Add code]",
                "description": "[TODO: Add description]",
            }
        ],
        testing_strategies=["[TODO: Add testing strategy]"],
        tools=["[TODO: Add tool]"],
        audit_checklist=["[TODO: Add audit item]"],
    )

    return {
        "detection": detection_template.render(),
        "patterns": patterns_template.render(),
        "exploits": exploits_template.render(),
        "fixes": fixes_template.render(),
    }


def create_template_bundle(
    category_id: str,
    subcategory_id: str,
    category_name: str = "",
    subcategory_name: str = "",
) -> Dict[str, Any]:
    """Create a complete template bundle with both templates and markdown.

    Args:
        category_id: Category identifier
        subcategory_id: Subcategory identifier
        category_name: Human-readable category name (optional)
        subcategory_name: Human-readable subcategory name (optional)

    Returns:
        Dictionary containing:
        - "templates": Dict of template dataclass instances
        - "markdown": Dict of rendered markdown strings
        - "metadata": Bundle metadata
    """
    # Default names if not provided
    if not category_name:
        category_name = category_id.replace("-", " ").title()
    if not subcategory_name:
        subcategory_name = subcategory_id.replace("-", " ").title()

    # Create templates
    detection_template = DetectionTemplate(
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        category_id=category_id,
        category_name=category_name,
    )

    patterns_template = PatternsTemplate(
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        category_id=category_id,
    )

    exploits_template = ExploitsTemplate(
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        category_id=category_id,
    )

    fixes_template = FixesTemplate(
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
        category_id=category_id,
    )

    return {
        "templates": {
            "detection": detection_template,
            "patterns": patterns_template,
            "exploits": exploits_template,
            "fixes": fixes_template,
        },
        "markdown": generate_document_templates(
            category_id, subcategory_id, category_name, subcategory_name
        ),
        "metadata": {
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "category_name": category_name,
            "subcategory_name": subcategory_name,
            "template_version": TEMPLATE_VERSION,
            "generated_at": datetime.utcnow().isoformat(),
        },
    }


# =============================================================================
# TEMPLATE VALIDATION
# =============================================================================


def validate_detection_template(template: DetectionTemplate) -> List[str]:
    """Validate a detection template.

    Args:
        template: DetectionTemplate instance

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not template.subcategory_id:
        errors.append("Missing subcategory_id")
    if not template.subcategory_name:
        errors.append("Missing subcategory_name")

    return errors


def validate_patterns_template(template: PatternsTemplate) -> List[str]:
    """Validate a patterns template.

    Args:
        template: PatternsTemplate instance

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not template.subcategory_id:
        errors.append("Missing subcategory_id")
    if not template.subcategory_name:
        errors.append("Missing subcategory_name")

    return errors


def validate_exploits_template(template: ExploitsTemplate) -> List[str]:
    """Validate an exploits template.

    Args:
        template: ExploitsTemplate instance

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not template.subcategory_id:
        errors.append("Missing subcategory_id")
    if not template.subcategory_name:
        errors.append("Missing subcategory_name")

    # Validate incidents
    for i, incident in enumerate(template.incidents):
        if not incident.id:
            errors.append(f"Incident {i} missing id")
        if not incident.name:
            errors.append(f"Incident {i} missing name")

    return errors


def validate_fixes_template(template: FixesTemplate) -> List[str]:
    """Validate a fixes template.

    Args:
        template: FixesTemplate instance

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not template.subcategory_id:
        errors.append("Missing subcategory_id")
    if not template.subcategory_name:
        errors.append("Missing subcategory_name")

    # Validate recommendations
    for i, rec in enumerate(template.recommendations):
        if not rec.name:
            errors.append(f"Recommendation {i} missing name")
        if not rec.description:
            errors.append(f"Recommendation {i} missing description")

    return errors
