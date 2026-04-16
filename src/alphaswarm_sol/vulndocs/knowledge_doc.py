"""Multi-Model Knowledge Document Schema.

Task 18.2: VulnKnowledgeDoc - optimized for LLM consumption.

This module defines the enhanced document structure for the multi-model
knowledge pipeline. Documents are structured for efficient LLM processing
with clear sections and token budgets.

Key Features:
- Optimized for 800-1500 tokens per document
- Clear sections for detection, exploitation, mitigation, examples
- Pattern linkage for VKG integration
- Source attribution and quality scoring
- Multi-model processing metadata
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PatternLinkageType(Enum):
    """How vulnerability knowledge links to VKG detection patterns."""

    EXACT_MATCH = "exact_match"
    # Pattern directly detects this vulnerability
    # Example: reentrancy-001 pattern detects classic reentrancy
    # Confidence: HIGH
    # Action: Show pattern detection + knowledge docs

    PARTIAL_MATCH = "partial_match"
    # Pattern covers subset of vulnerability variants
    # Example: access-control-001 catches some but not all access issues
    # Confidence: MEDIUM
    # Action: Show pattern detection + warn about uncovered variants

    THEORETICAL = "theoretical"
    # No automated pattern exists, knowledge-only
    # Example: Complex business logic flaws
    # Confidence: N/A (no detection)
    # Action: Surface knowledge docs during manual review

    REQUIRES_LLM = "requires_llm"
    # Detection requires Tier-B LLM reasoning
    # Example: Intent deviation, semantic mismatches
    # Confidence: MEDIUM (depends on LLM)
    # Action: Trigger LLM analysis with knowledge context

    COMPOSITE = "composite"
    # Multiple patterns needed together
    # Example: Flash loan + oracle = attack
    # Confidence: HIGH when all patterns match
    # Action: Check for pattern combination

    @classmethod
    def from_string(cls, value: str) -> "PatternLinkageType":
        """Parse linkage type from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.THEORETICAL  # Default


class Severity(Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Parse severity from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.MEDIUM


class Prevalence(Enum):
    """How common a vulnerability is."""

    VERY_COMMON = "very_common"
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"

    @classmethod
    def from_string(cls, value: str) -> "Prevalence":
        """Parse prevalence from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.COMMON


@dataclass
class DetectionSection:
    """How to detect this vulnerability.

    Token budget: ~200 tokens
    """

    # Graph signals (what VKG looks for)
    graph_signals: List[str] = field(default_factory=list)
    # Example: ["state_write_after_external_call", "no_reentrancy_guard"]

    # Operation sequence
    vulnerable_sequence: str = ""
    # Example: "R:bal -> X:out -> W:bal (read, external, write)"
    safe_sequence: str = ""
    # Example: "R:bal -> W:bal -> X:out (CEI pattern)"

    # Key indicators
    indicators: List[str] = field(default_factory=list)
    # Example: ["external call before state update", "no mutex"]

    # What to check
    checklist: List[str] = field(default_factory=list)
    # Example: ["Check call ordering", "Verify guard presence"]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "graph_signals": self.graph_signals,
            "vulnerable_sequence": self.vulnerable_sequence,
            "safe_sequence": self.safe_sequence,
            "indicators": self.indicators,
            "checklist": self.checklist,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectionSection":
        """Deserialize from dictionary."""
        return cls(
            graph_signals=data.get("graph_signals", []),
            vulnerable_sequence=data.get("vulnerable_sequence", ""),
            safe_sequence=data.get("safe_sequence", ""),
            indicators=data.get("indicators", []),
            checklist=data.get("checklist", []),
        )

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        lines = ["## Detection", ""]

        if self.graph_signals:
            lines.append("**Graph Signals:**")
            for sig in self.graph_signals:
                lines.append(f"- `{sig}`")
            lines.append("")

        if self.vulnerable_sequence:
            lines.append(f"**Vulnerable Sequence:** `{self.vulnerable_sequence}`")
        if self.safe_sequence:
            lines.append(f"**Safe Sequence:** `{self.safe_sequence}`")
        lines.append("")

        if self.indicators:
            lines.append("**Key Indicators:**")
            for ind in self.indicators:
                lines.append(f"- {ind}")
            lines.append("")

        if self.checklist:
            lines.append("**Detection Checklist:**")
            for item in self.checklist:
                lines.append(f"- [ ] {item}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class ExploitationSection:
    """How this vulnerability is exploited.

    Token budget: ~200 tokens
    """

    # Attack mechanism
    attack_vector: str = ""
    # How attacker exploits this

    # Prerequisites
    prerequisites: List[str] = field(default_factory=list)
    # What attacker needs

    # Attack flow
    attack_steps: List[str] = field(default_factory=list)
    # Step-by-step attack

    # Impact
    potential_impact: str = ""
    # What can be stolen/broken
    monetary_risk: str = "high"
    # "high" | "critical" - funds at risk

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "attack_vector": self.attack_vector,
            "prerequisites": self.prerequisites,
            "attack_steps": self.attack_steps,
            "potential_impact": self.potential_impact,
            "monetary_risk": self.monetary_risk,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExploitationSection":
        """Deserialize from dictionary."""
        return cls(
            attack_vector=data.get("attack_vector", ""),
            prerequisites=data.get("prerequisites", []),
            attack_steps=data.get("attack_steps", []),
            potential_impact=data.get("potential_impact", ""),
            monetary_risk=data.get("monetary_risk", "high"),
        )

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        lines = ["## Exploitation", ""]

        if self.attack_vector:
            lines.append(f"**Attack Vector:** {self.attack_vector}")
            lines.append("")

        if self.prerequisites:
            lines.append("**Prerequisites:**")
            for prereq in self.prerequisites:
                lines.append(f"- {prereq}")
            lines.append("")

        if self.attack_steps:
            lines.append("**Attack Steps:**")
            for i, step in enumerate(self.attack_steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if self.potential_impact:
            lines.append(f"**Potential Impact:** {self.potential_impact}")
        if self.monetary_risk:
            lines.append(f"**Monetary Risk:** {self.monetary_risk}")
        lines.append("")

        return "\n".join(lines)


@dataclass
class MitigationSection:
    """How to fix this vulnerability.

    Token budget: ~200 tokens
    """

    # Primary fix
    primary_fix: str = ""
    # Main remediation approach

    # Alternative fixes
    alternative_fixes: List[str] = field(default_factory=list)
    # Other valid approaches

    # Code pattern
    safe_pattern: str = ""
    # Name of safe pattern (e.g., "CEI")

    # Verification
    how_to_verify: List[str] = field(default_factory=list)
    # How to confirm fix works

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "primary_fix": self.primary_fix,
            "alternative_fixes": self.alternative_fixes,
            "safe_pattern": self.safe_pattern,
            "how_to_verify": self.how_to_verify,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MitigationSection":
        """Deserialize from dictionary."""
        return cls(
            primary_fix=data.get("primary_fix", ""),
            alternative_fixes=data.get("alternative_fixes", []),
            safe_pattern=data.get("safe_pattern", ""),
            how_to_verify=data.get("how_to_verify", []),
        )

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        lines = ["## Mitigation", ""]

        if self.primary_fix:
            lines.append(f"**Primary Fix:** {self.primary_fix}")
            lines.append("")

        if self.alternative_fixes:
            lines.append("**Alternative Fixes:**")
            for fix in self.alternative_fixes:
                lines.append(f"- {fix}")
            lines.append("")

        if self.safe_pattern:
            lines.append(f"**Safe Pattern:** {self.safe_pattern}")
            lines.append("")

        if self.how_to_verify:
            lines.append("**Verification Steps:**")
            for step in self.how_to_verify:
                lines.append(f"- [ ] {step}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class RealExploitRef:
    """A real-world exploit reference.

    Compact version optimized for token efficiency.
    """

    name: str  # "The DAO Hack"
    date: str = ""  # "2016-06-17"
    loss: str = ""  # "$60M"
    protocol: str = ""  # "The DAO"
    brief: str = ""  # One sentence description
    source_url: str = ""  # Link to analysis

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "date": self.date,
            "loss": self.loss,
            "protocol": self.protocol,
            "brief": self.brief,
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RealExploitRef":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            date=data.get("date", ""),
            loss=data.get("loss", ""),
            protocol=data.get("protocol", ""),
            brief=data.get("brief", ""),
            source_url=data.get("source_url", ""),
        )

    def to_inline(self) -> str:
        """Generate inline reference."""
        parts = [self.name]
        if self.date:
            parts.append(f"({self.date})")
        if self.loss:
            parts.append(f"- {self.loss}")
        if self.protocol:
            parts.append(f"@ {self.protocol}")
        return " ".join(parts)


@dataclass
class ExamplesSection:
    """Real-world examples and code samples.

    Token budget: ~300 tokens
    """

    # Vulnerable code (minimal, illustrative)
    vulnerable_code: str = ""  # 10-20 lines max
    vulnerable_code_explanation: str = ""  # What's wrong

    # Fixed code
    fixed_code: str = ""  # Same example, fixed
    fixed_code_explanation: str = ""  # What changed

    # Real-world incidents
    real_exploits: List[RealExploitRef] = field(default_factory=list)  # CVEs, hacks

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "vulnerable_code": self.vulnerable_code,
            "vulnerable_code_explanation": self.vulnerable_code_explanation,
            "fixed_code": self.fixed_code,
            "fixed_code_explanation": self.fixed_code_explanation,
            "real_exploits": [e.to_dict() for e in self.real_exploits],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExamplesSection":
        """Deserialize from dictionary."""
        return cls(
            vulnerable_code=data.get("vulnerable_code", ""),
            vulnerable_code_explanation=data.get("vulnerable_code_explanation", ""),
            fixed_code=data.get("fixed_code", ""),
            fixed_code_explanation=data.get("fixed_code_explanation", ""),
            real_exploits=[
                RealExploitRef.from_dict(e) for e in data.get("real_exploits", [])
            ],
        )

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        lines = ["## Examples", ""]

        if self.vulnerable_code:
            lines.append("**Vulnerable Code:**")
            lines.append("```solidity")
            lines.append(self.vulnerable_code)
            lines.append("```")
            if self.vulnerable_code_explanation:
                lines.append(f"*{self.vulnerable_code_explanation}*")
            lines.append("")

        if self.fixed_code:
            lines.append("**Fixed Code:**")
            lines.append("```solidity")
            lines.append(self.fixed_code)
            lines.append("```")
            if self.fixed_code_explanation:
                lines.append(f"*{self.fixed_code_explanation}*")
            lines.append("")

        if self.real_exploits:
            lines.append("**Real-World Exploits:**")
            for exp in self.real_exploits:
                lines.append(f"- {exp.to_inline()}")
                if exp.brief:
                    lines.append(f"  {exp.brief}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class PatternLinkage:
    """Links this knowledge to VKG detection patterns.

    Token budget: ~100 tokens
    """

    linkage_type: PatternLinkageType = PatternLinkageType.THEORETICAL

    # For exact/partial match
    pattern_ids: List[str] = field(default_factory=list)
    # ["reentrancy-001", "reentrancy-002"]
    coverage_pct: float = 0.0
    # 0.95 = 95% of variants covered

    # For theoretical
    why_no_pattern: Optional[str] = None
    # Why automated detection is hard
    manual_hints: List[str] = field(default_factory=list)
    # What to look for manually

    # For requires_llm
    llm_context_needed: List[str] = field(default_factory=list)
    # What context LLM needs

    # For composite
    composite_patterns: List[str] = field(default_factory=list)
    # Patterns that must co-occur
    combination_logic: str = ""
    # "AND" | "OR" | "SEQUENCE"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "linkage_type": self.linkage_type.value,
            "pattern_ids": self.pattern_ids,
            "coverage_pct": self.coverage_pct,
            "why_no_pattern": self.why_no_pattern,
            "manual_hints": self.manual_hints,
            "llm_context_needed": self.llm_context_needed,
            "composite_patterns": self.composite_patterns,
            "combination_logic": self.combination_logic,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternLinkage":
        """Deserialize from dictionary."""
        return cls(
            linkage_type=PatternLinkageType.from_string(
                data.get("linkage_type", "theoretical")
            ),
            pattern_ids=data.get("pattern_ids", []),
            coverage_pct=data.get("coverage_pct", 0.0),
            why_no_pattern=data.get("why_no_pattern"),
            manual_hints=data.get("manual_hints", []),
            llm_context_needed=data.get("llm_context_needed", []),
            composite_patterns=data.get("composite_patterns", []),
            combination_logic=data.get("combination_logic", ""),
        )

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        lines = ["## Pattern Linkage", ""]

        lines.append(f"**Type:** {self.linkage_type.value}")

        if self.pattern_ids:
            lines.append(f"**Patterns:** {', '.join(self.pattern_ids)}")
        if self.coverage_pct > 0:
            lines.append(f"**Coverage:** {self.coverage_pct * 100:.0f}%")

        if self.why_no_pattern:
            lines.append(f"**Why No Pattern:** {self.why_no_pattern}")
        if self.manual_hints:
            lines.append("**Manual Hints:**")
            for hint in self.manual_hints:
                lines.append(f"- {hint}")

        if self.llm_context_needed:
            lines.append("**LLM Context Needed:**")
            for ctx in self.llm_context_needed:
                lines.append(f"- {ctx}")

        if self.composite_patterns:
            lines.append(f"**Composite Patterns:** {', '.join(self.composite_patterns)}")
            if self.combination_logic:
                lines.append(f"**Logic:** {self.combination_logic}")

        lines.append("")
        return "\n".join(lines)


@dataclass
class DocMetadata:
    """Document metadata for tracking and retrieval.

    Token budget: ~50 tokens
    """

    # Sources
    sources: List[str] = field(default_factory=list)
    # URLs this knowledge came from
    source_authority: float = 0.0
    # 0-1 weighted authority score

    # Freshness
    last_updated: str = ""
    # ISO date
    content_hash: str = ""
    # For change detection

    # Retrieval optimization
    keywords: List[str] = field(default_factory=list)
    # For keyword search
    embedding_id: Optional[str] = None
    # For vector search

    # Quality
    completeness_score: float = 0.0
    # 0-1 how complete
    confidence_score: float = 0.0
    # 0-1 how confident in accuracy
    missing_fields: List[str] = field(default_factory=list)
    # Missing SVR fields for targeted enrichment

    # Processing tracking
    processing_model: str = ""
    # Which model processed this (haiku/opus)
    processing_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "sources": self.sources,
            "source_authority": self.source_authority,
            "last_updated": self.last_updated,
            "content_hash": self.content_hash,
            "keywords": self.keywords,
            "embedding_id": self.embedding_id,
            "completeness_score": self.completeness_score,
            "confidence_score": self.confidence_score,
            "missing_fields": self.missing_fields,
            "processing_model": self.processing_model,
            "processing_timestamp": self.processing_timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocMetadata":
        """Deserialize from dictionary."""
        return cls(
            sources=data.get("sources", []),
            source_authority=data.get("source_authority", 0.0),
            last_updated=data.get("last_updated", ""),
            content_hash=data.get("content_hash", ""),
            keywords=data.get("keywords", []),
            embedding_id=data.get("embedding_id"),
            completeness_score=data.get("completeness_score", 0.0),
            confidence_score=data.get("confidence_score", 0.0),
            missing_fields=data.get("missing_fields", []),
            processing_model=data.get("processing_model", ""),
            processing_timestamp=data.get("processing_timestamp", ""),
        )


@dataclass
class VulnKnowledgeDoc:
    """Single vulnerability knowledge document.

    Optimized for LLM consumption with clear sections.
    Target: 800-1500 tokens per document.
    """

    # === IDENTIFICATION (50 tokens) ===
    id: str  # "reentrancy/classic/state-after-call"
    name: str  # "State Write After External Call"
    category: str  # "reentrancy"
    subcategory: str  # "classic-reentrancy"
    severity: Severity = Severity.HIGH
    prevalence: Prevalence = Prevalence.COMMON

    # === QUICK SUMMARY (100 tokens) ===
    one_liner: str = ""  # Single sentence description
    tldr: str = ""  # 2-3 sentence summary for quick understanding

    # === DETECTION (200 tokens) ===
    detection: DetectionSection = field(default_factory=DetectionSection)

    # === EXPLOITATION (200 tokens) ===
    exploitation: ExploitationSection = field(default_factory=ExploitationSection)

    # === MITIGATION (200 tokens) ===
    mitigation: MitigationSection = field(default_factory=MitigationSection)

    # === EXAMPLES (300 tokens) ===
    examples: ExamplesSection = field(default_factory=ExamplesSection)

    # === PATTERN LINKAGE (100 tokens) ===
    pattern_linkage: PatternLinkage = field(default_factory=PatternLinkage)

    # === METADATA (50 tokens) ===
    metadata: DocMetadata = field(default_factory=DocMetadata)

    def __post_init__(self):
        """Validate and compute derived fields."""
        if not self.metadata.content_hash:
            self.metadata.content_hash = self._compute_hash()
        if not self.metadata.last_updated:
            self.metadata.last_updated = datetime.utcnow().isoformat()

    def _compute_hash(self) -> str:
        """Compute content hash for change detection."""
        content = f"{self.id}{self.name}{self.one_liner}{self.tldr}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "severity": self.severity.value,
            "prevalence": self.prevalence.value,
            "one_liner": self.one_liner,
            "tldr": self.tldr,
            "detection": self.detection.to_dict(),
            "exploitation": self.exploitation.to_dict(),
            "mitigation": self.mitigation.to_dict(),
            "examples": self.examples.to_dict(),
            "pattern_linkage": self.pattern_linkage.to_dict(),
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VulnKnowledgeDoc":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            severity=Severity.from_string(data.get("severity", "high")),
            prevalence=Prevalence.from_string(data.get("prevalence", "common")),
            one_liner=data.get("one_liner", ""),
            tldr=data.get("tldr", ""),
            detection=DetectionSection.from_dict(data.get("detection", {})),
            exploitation=ExploitationSection.from_dict(data.get("exploitation", {})),
            mitigation=MitigationSection.from_dict(data.get("mitigation", {})),
            examples=ExamplesSection.from_dict(data.get("examples", {})),
            pattern_linkage=PatternLinkage.from_dict(data.get("pattern_linkage", {})),
            metadata=DocMetadata.from_dict(data.get("metadata", {})),
        )

    def to_markdown(self, include_metadata: bool = False) -> str:
        """Generate full markdown representation.

        Args:
            include_metadata: Whether to include metadata section

        Returns:
            Markdown string optimized for LLM consumption
        """
        lines = [
            f"# {self.name}",
            "",
            f"**Category:** {self.category} / {self.subcategory}",
            f"**Severity:** {self.severity.value} | **Prevalence:** {self.prevalence.value}",
            "",
        ]

        if self.one_liner:
            lines.append(f"> {self.one_liner}")
            lines.append("")

        if self.tldr:
            lines.append(self.tldr)
            lines.append("")

        lines.append(self.detection.to_markdown())
        lines.append(self.exploitation.to_markdown())
        lines.append(self.mitigation.to_markdown())
        lines.append(self.examples.to_markdown())
        lines.append(self.pattern_linkage.to_markdown())

        if include_metadata:
            lines.append("---")
            lines.append("## Metadata")
            lines.append(f"- **Sources:** {len(self.metadata.sources)} sources")
            lines.append(f"- **Authority:** {self.metadata.source_authority:.2f}")
            lines.append(f"- **Completeness:** {self.metadata.completeness_score:.2f}")
            lines.append(f"- **Last Updated:** {self.metadata.last_updated}")
            lines.append("")

        return "\n".join(lines)

    def to_compact_context(self, max_tokens: int = 500) -> str:
        """Generate compact context for token-limited situations.

        Args:
            max_tokens: Approximate token limit

        Returns:
            Compact markdown string
        """
        lines = [
            f"# {self.name} ({self.category}/{self.subcategory})",
            f"Severity: {self.severity.value} | {self.one_liner}",
            "",
        ]

        if self.tldr:
            lines.append(self.tldr)
            lines.append("")

        # Detection signals only
        if self.detection.graph_signals:
            lines.append(f"**Signals:** {', '.join(self.detection.graph_signals[:5])}")

        # Primary fix only
        if self.mitigation.primary_fix:
            lines.append(f"**Fix:** {self.mitigation.primary_fix}")

        # Pattern linkage
        if self.pattern_linkage.pattern_ids:
            lines.append(f"**Patterns:** {', '.join(self.pattern_linkage.pattern_ids)}")
        else:
            lines.append(f"**Detection:** {self.pattern_linkage.linkage_type.value}")

        return "\n".join(lines)

    def estimate_tokens(self) -> int:
        """Estimate token count for this document.

        Returns:
            Approximate token count
        """
        # Rough estimate: 1 token ~= 4 characters
        full_text = self.to_markdown()
        return len(full_text) // 4

    def get_section(self, section_name: str) -> str:
        """Get a specific section as markdown.

        Args:
            section_name: One of: detection, exploitation, mitigation, examples, pattern_linkage

        Returns:
            Markdown string for that section
        """
        section_map = {
            "detection": self.detection.to_markdown,
            "exploitation": self.exploitation.to_markdown,
            "mitigation": self.mitigation.to_markdown,
            "examples": self.examples.to_markdown,
            "pattern_linkage": self.pattern_linkage.to_markdown,
        }
        if section_name in section_map:
            return section_map[section_name]()
        return ""


# =============================================================================
# Source Summary (Haiku output)
# =============================================================================


@dataclass
class SourceSummary:
    """Summary of a single source document.

    Created by Haiku workers during processing phase.
    """

    source_url: str
    source_name: str
    category: str
    subcategory: str
    content_hash: str = ""

    # Key points extracted
    key_points: List[str] = field(default_factory=list)

    # Attack information
    attack_vector: str = ""
    attack_steps: List[str] = field(default_factory=list)

    # Mitigation information
    mitigation: str = ""
    safe_patterns: List[str] = field(default_factory=list)

    # Code examples
    vulnerable_code: str = ""
    fixed_code: str = ""

    # Real incidents
    incidents: List[Dict[str, str]] = field(default_factory=list)

    # Quality
    source_authority: float = 0.5
    extraction_confidence: float = 0.8
    review_status: str = "accept"
    review_novelty: str = "medium"
    review_value: str = "medium"
    review_rationale: str = ""
    missing_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_url": self.source_url,
            "source_name": self.source_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "content_hash": self.content_hash,
            "key_points": self.key_points,
            "attack_vector": self.attack_vector,
            "attack_steps": self.attack_steps,
            "mitigation": self.mitigation,
            "safe_patterns": self.safe_patterns,
            "vulnerable_code": self.vulnerable_code,
            "fixed_code": self.fixed_code,
            "incidents": self.incidents,
            "source_authority": self.source_authority,
            "extraction_confidence": self.extraction_confidence,
            "review_status": self.review_status,
            "review_novelty": self.review_novelty,
            "review_value": self.review_value,
            "review_rationale": self.review_rationale,
            "missing_fields": self.missing_fields,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SourceSummary":
        """Deserialize from dictionary."""
        return cls(
            source_url=data.get("source_url", ""),
            source_name=data.get("source_name", ""),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            content_hash=data.get("content_hash", ""),
            key_points=data.get("key_points", []),
            attack_vector=data.get("attack_vector", ""),
            attack_steps=data.get("attack_steps", []),
            mitigation=data.get("mitigation", ""),
            safe_patterns=data.get("safe_patterns", []),
            vulnerable_code=data.get("vulnerable_code", ""),
            fixed_code=data.get("fixed_code", ""),
            incidents=data.get("incidents", []),
            source_authority=data.get("source_authority", 0.5),
            extraction_confidence=data.get("extraction_confidence", 0.8),
            review_status=data.get("review_status", "accept"),
            review_novelty=data.get("review_novelty", "medium"),
            review_value=data.get("review_value", "medium"),
            review_rationale=data.get("review_rationale", ""),
            missing_fields=data.get("missing_fields", []),
        )


# =============================================================================
# Merge Result (Opus output)
# =============================================================================


@dataclass
class UniqueIdea:
    """A unique idea identified during merging.

    Opus identifies these to ensure no knowledge is lost.
    """

    id: str
    description: str
    source_urls: List[str]
    category: str
    idea_type: str  # "attack_variant", "detection", "mitigation", "edge_case", "example"
    merged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "source_urls": self.source_urls,
            "category": self.category,
            "idea_type": self.idea_type,
            "merged": self.merged,
        }


@dataclass
class MergeConflict:
    """A conflict detected during merging."""

    conflict_id: str
    description: str
    claim_a: str
    source_a: str
    authority_a: float
    claim_b: str
    source_b: str
    authority_b: float
    resolution: str = ""
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "conflict_id": self.conflict_id,
            "description": self.description,
            "claim_a": self.claim_a,
            "source_a": self.source_a,
            "authority_a": self.authority_a,
            "claim_b": self.claim_b,
            "source_b": self.source_b,
            "authority_b": self.authority_b,
            "resolution": self.resolution,
            "reasoning": self.reasoning,
        }


@dataclass
class MergeResult:
    """Result of merging multiple sources into a VulnKnowledgeDoc."""

    subcategory_id: str
    document: VulnKnowledgeDoc
    unique_ideas: List[UniqueIdea]
    conflicts: List[MergeConflict]
    source_count: int
    merge_timestamp: str = ""

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.merge_timestamp:
            self.merge_timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "subcategory_id": self.subcategory_id,
            "document": self.document.to_dict(),
            "unique_ideas": [i.to_dict() for i in self.unique_ideas],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "source_count": self.source_count,
            "merge_timestamp": self.merge_timestamp,
        }

    def get_unmerged_ideas(self) -> List[UniqueIdea]:
        """Get ideas that weren't merged into the document."""
        return [i for i in self.unique_ideas if not i.merged]

    def get_unresolved_conflicts(self) -> List[MergeConflict]:
        """Get conflicts without resolution."""
        return [c for c in self.conflicts if not c.resolution]
