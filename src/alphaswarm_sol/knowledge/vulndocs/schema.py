"""VulnDocs Knowledge Schema Classes.

DEPRECATED: Use alphaswarm_sol.vulndocs.schema instead.
This module is maintained for backward compatibility.

Phase 17.0: Knowledge Schema Design for VulnDocs.

This module provides dataclasses and validation for the VulnDocs knowledge
schema. The schema content now lives in vulndocs/ directory.

The schema supports:
- Hierarchical category/subcategory/document structure
- Prompt caching markers for LLM efficiency
- Version tracking for knowledge updates
- Severity mappings per category
- Real-world exploit references
- Detection pattern linkage
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import yaml

# =============================================================================
# CONSTANTS
# =============================================================================

SCHEMA_VERSION = "1.0"
# DEPRECATED: knowledge/vulndocs is now unified under vulndocs/
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent.parent / "vulndocs"

# Pattern for valid IDs (lowercase alphanumeric with dashes)
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")

# Pattern for cache keys
CACHE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9-]*-v[0-9]+$")

# Valid severity values
VALID_SEVERITIES = {"critical", "high", "medium", "low", "informational"}


# =============================================================================
# ENUMS
# =============================================================================


class Severity(Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Parse severity from string."""
        normalized = value.lower()
        try:
            return cls(normalized)
        except ValueError:
            return cls.MEDIUM  # Default


class KnowledgeDepth(Enum):
    """Depth levels for knowledge retrieval."""

    INDEX = "index"
    OVERVIEW = "overview"
    DETECTION = "detection"
    PATTERNS = "patterns"
    EXPLOITS = "exploits"
    FIXES = "fixes"
    FULL = "full"

    @classmethod
    def from_string(cls, value: str) -> "KnowledgeDepth":
        """Parse depth from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.DETECTION  # Default

    @property
    def token_estimate(self) -> int:
        """Get estimated token count for this depth."""
        estimates = {
            self.INDEX: 200,
            self.OVERVIEW: 500,
            self.DETECTION: 1000,
            self.PATTERNS: 1500,
            self.EXPLOITS: 1000,
            self.FIXES: 800,
            self.FULL: 5000,
        }
        return estimates.get(self, 1000)


class DocumentType(Enum):
    """Types of knowledge documents."""

    INDEX = "index"
    OVERVIEW = "overview"
    DETECTION = "detection"
    PATTERNS = "patterns"
    EXPLOITS = "exploits"
    FIXES = "fixes"

    @classmethod
    def from_string(cls, value: str) -> "DocumentType":
        """Parse document type from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.INDEX  # Default


class CacheControlType(Enum):
    """Cache control types for prompt caching."""

    EPHEMERAL = "ephemeral"  # Session-duration cache
    STATIC = "static"  # Long-term cache
    NONE = "none"  # No caching


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class GraphSignal:
    """A graph property signal for detection.

    Represents a VKG property that indicates potential vulnerability.
    """

    property_name: str
    expected: Any
    critical: bool = False
    description: str = ""
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "property": self.property_name,
            "expected": self.expected,
            "critical": self.critical,
            "description": self.description,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphSignal":
        """Deserialize from dictionary."""
        return cls(
            property_name=data.get("property", ""),
            expected=data.get("expected"),
            critical=data.get("critical", False),
            description=data.get("description", ""),
            confidence=data.get("confidence", 0.8),
        )


@dataclass
class CodePattern:
    """A code pattern example for detection."""

    name: str
    vulnerable_code: str
    safe_code: str = ""
    description: str = ""
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "vulnerable": self.vulnerable_code,
            "safe": self.safe_code,
            "description": self.description,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodePattern":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            vulnerable_code=data.get("vulnerable", ""),
            safe_code=data.get("safe", ""),
            description=data.get("description", ""),
            severity=data.get("severity", "medium"),
        )


@dataclass
class ExploitReference:
    """A real-world exploit reference."""

    id: str
    name: str
    date: str = ""
    loss_usd: str = ""
    protocol: str = ""
    chain: str = "ethereum"
    category: str = ""
    subcategory: str = ""
    description: str = ""
    attack_steps: List[str] = field(default_factory=list)
    tx_hash: str = ""
    postmortem_url: str = ""
    cve_id: str = ""
    solodit_id: str = ""
    vulnerable_code_url: str = ""
    fixed_code_url: str = ""
    pattern_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date,
            "loss_usd": self.loss_usd,
            "protocol": self.protocol,
            "chain": self.chain,
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "attack_steps": self.attack_steps,
            "tx_hash": self.tx_hash,
            "postmortem_url": self.postmortem_url,
            "cve_id": self.cve_id,
            "solodit_id": self.solodit_id,
            "vulnerable_code_url": self.vulnerable_code_url,
            "fixed_code_url": self.fixed_code_url,
            "pattern_ids": self.pattern_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExploitReference":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            date=data.get("date", ""),
            loss_usd=data.get("loss_usd", ""),
            protocol=data.get("protocol", ""),
            chain=data.get("chain", "ethereum"),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            description=data.get("description", ""),
            attack_steps=data.get("attack_steps", []),
            tx_hash=data.get("tx_hash", ""),
            postmortem_url=data.get("postmortem_url", ""),
            cve_id=data.get("cve_id", ""),
            solodit_id=data.get("solodit_id", ""),
            vulnerable_code_url=data.get("vulnerable_code_url", ""),
            fixed_code_url=data.get("fixed_code_url", ""),
            pattern_ids=data.get("pattern_ids", []),
        )


@dataclass
class FixRecommendation:
    """A remediation recommendation."""

    name: str
    description: str
    code_example: str = ""
    effectiveness: str = "high"
    complexity: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "code_example": self.code_example,
            "effectiveness": self.effectiveness,
            "complexity": self.complexity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FixRecommendation":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            code_example=data.get("code_example", ""),
            effectiveness=data.get("effectiveness", "high"),
            complexity=data.get("complexity", "low"),
        )


@dataclass
class OperationSequences:
    """Vulnerable and safe operation sequences."""

    vulnerable: List[str] = field(default_factory=list)
    safe: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "vulnerable": self.vulnerable,
            "safe": self.safe,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OperationSequences":
        """Deserialize from dictionary."""
        return cls(
            vulnerable=data.get("vulnerable", []),
            safe=data.get("safe", []),
        )


@dataclass
class Subcategory:
    """A vulnerability subcategory within a category."""

    id: str
    name: str
    description: str
    parent_category: str
    severity_range: List[str] = field(default_factory=lambda: ["medium", "high"])
    patterns: List[str] = field(default_factory=list)
    relevant_properties: List[str] = field(default_factory=list)
    graph_signals: List[GraphSignal] = field(default_factory=list)
    behavioral_signatures: List[str] = field(default_factory=list)
    operation_sequences: Optional[OperationSequences] = None
    code_patterns: List[CodePattern] = field(default_factory=list)
    exploits: List[ExploitReference] = field(default_factory=list)
    fixes: List[FixRecommendation] = field(default_factory=list)
    false_positive_indicators: List[str] = field(default_factory=list)
    token_estimate: int = 500

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_category": self.parent_category,
            "severity_range": self.severity_range,
            "patterns": self.patterns,
            "relevant_properties": self.relevant_properties,
            "graph_signals": [s.to_dict() for s in self.graph_signals],
            "behavioral_signatures": self.behavioral_signatures,
            "code_patterns": [p.to_dict() for p in self.code_patterns],
            "exploits": [e.to_dict() for e in self.exploits],
            "fixes": [f.to_dict() for f in self.fixes],
            "false_positive_indicators": self.false_positive_indicators,
            "token_estimate": self.token_estimate,
        }
        if self.operation_sequences:
            result["operation_sequences"] = self.operation_sequences.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Subcategory":
        """Deserialize from dictionary."""
        op_seq = data.get("operation_sequences")
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            parent_category=data.get("parent_category", ""),
            severity_range=data.get("severity_range", ["medium", "high"]),
            patterns=data.get("patterns", []),
            relevant_properties=data.get("relevant_properties", []),
            graph_signals=[
                GraphSignal.from_dict(s) for s in data.get("graph_signals", [])
            ],
            behavioral_signatures=data.get("behavioral_signatures", []),
            operation_sequences=OperationSequences.from_dict(op_seq) if op_seq else None,
            code_patterns=[
                CodePattern.from_dict(p) for p in data.get("code_patterns", [])
            ],
            exploits=[
                ExploitReference.from_dict(e) for e in data.get("exploits", [])
            ],
            fixes=[
                FixRecommendation.from_dict(f) for f in data.get("fixes", [])
            ],
            false_positive_indicators=data.get("false_positive_indicators", []),
            token_estimate=data.get("token_estimate", 500),
        )

    def get_detection_context(self) -> str:
        """Generate detection-focused context string."""
        lines = [
            f"# Detection: {self.name}",
            "",
            f"**Category:** {self.parent_category}",
            f"**Severity:** {', '.join(self.severity_range)}",
            "",
        ]

        if self.graph_signals:
            lines.append("## Graph Signals")
            lines.append("| Property | Expected | Critical? |")
            lines.append("|----------|----------|-----------|")
            for sig in self.graph_signals:
                critical = "YES" if sig.critical else "NO"
                lines.append(f"| {sig.property_name} | {sig.expected} | {critical} |")
            lines.append("")

        if self.behavioral_signatures:
            lines.append("## Behavioral Signatures")
            for sig in self.behavioral_signatures:
                lines.append(f"- `{sig}`")
            lines.append("")

        if self.operation_sequences:
            lines.append("## Operation Sequences")
            if self.operation_sequences.vulnerable:
                lines.append("**Vulnerable:**")
                for seq in self.operation_sequences.vulnerable:
                    lines.append(f"- `{seq}`")
            if self.operation_sequences.safe:
                lines.append("**Safe:**")
                for seq in self.operation_sequences.safe:
                    lines.append(f"- `{seq}`")
            lines.append("")

        if self.false_positive_indicators:
            lines.append("## False Positive Indicators")
            for fp in self.false_positive_indicators:
                lines.append(f"- {fp}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class SubcategoryRef:
    """Lightweight reference to a subcategory (for navigation)."""

    id: str
    name: str
    description: str
    patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "patterns": self.patterns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubcategoryRef":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            patterns=data.get("patterns", []),
        )


@dataclass
class Category:
    """A top-level vulnerability category."""

    id: str
    name: str
    description: str
    severity_range: List[str] = field(default_factory=lambda: ["medium", "critical"])
    subcategories: List[SubcategoryRef] = field(default_factory=list)
    relevant_properties: List[str] = field(default_factory=list)
    semantic_operations: List[str] = field(default_factory=list)
    context_cache_key: str = ""
    token_estimate: int = 1500
    related_cwes: List[str] = field(default_factory=list)
    external_refs: Dict[str, str] = field(default_factory=dict)
    path: str = ""

    def __post_init__(self):
        """Set defaults after initialization."""
        if not self.context_cache_key:
            self.context_cache_key = f"{self.id}-v1"
        if not self.path:
            self.path = f"categories/{self.id}/"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity_range": self.severity_range,
            "subcategories": [s.to_dict() for s in self.subcategories],
            "relevant_properties": self.relevant_properties,
            "semantic_operations": self.semantic_operations,
            "context_cache_key": self.context_cache_key,
            "token_estimate": self.token_estimate,
            "related_cwes": self.related_cwes,
            "external_refs": self.external_refs,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Category":
        """Deserialize from dictionary."""
        # Handle both full subcategory objects and simple ID lists
        subcats_data = data.get("subcategories", [])
        subcategories = []
        for sub in subcats_data:
            if isinstance(sub, dict):
                subcategories.append(SubcategoryRef.from_dict(sub))
            elif isinstance(sub, str):
                # Just an ID, create minimal ref
                subcategories.append(SubcategoryRef(id=sub, name=sub, description=""))

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            severity_range=data.get("severity_range", ["medium", "critical"]),
            subcategories=subcategories,
            relevant_properties=data.get("relevant_properties", data.get("key_properties", [])),
            semantic_operations=data.get("semantic_operations", data.get("key_operations", [])),
            context_cache_key=data.get("context_cache_key", ""),
            token_estimate=data.get("token_estimate", 1500),
            related_cwes=data.get("related_cwes", []),
            external_refs=data.get("external_refs", {}),
            path=data.get("path", ""),
        )

    def get_subcategory(self, subcategory_id: str) -> Optional[SubcategoryRef]:
        """Get a subcategory reference by ID."""
        for sub in self.subcategories:
            if sub.id == subcategory_id:
                return sub
        return None

    def get_subcategory_ids(self) -> List[str]:
        """Get all subcategory IDs."""
        return [s.id for s in self.subcategories]

    def get_overview_context(self) -> str:
        """Generate overview context string."""
        lines = [
            f"# {self.name}",
            "",
            self.description,
            "",
            f"**Severity Range:** {', '.join(self.severity_range)}",
            "",
            "## Subcategories",
        ]

        for sub in self.subcategories:
            desc = f": {sub.description}" if sub.description else ""
            lines.append(f"- **{sub.name}** (`{sub.id}`){desc}")

        if self.relevant_properties:
            lines.append("")
            lines.append("## Relevant Graph Properties")
            lines.append(", ".join(self.relevant_properties[:10]))

        if self.semantic_operations:
            lines.append("")
            lines.append("## Key Operations")
            lines.append(", ".join(self.semantic_operations[:10]))

        return "\n".join(lines)


@dataclass
class Document:
    """A knowledge document within a subcategory."""

    subcategory_id: str
    document_type: DocumentType
    content: str = ""
    graph_signals: List[GraphSignal] = field(default_factory=list)
    operation_sequences: Optional[OperationSequences] = None
    behavioral_signatures: List[str] = field(default_factory=list)
    false_positive_indicators: List[str] = field(default_factory=list)
    code_patterns: List[CodePattern] = field(default_factory=list)
    exploits: List[ExploitReference] = field(default_factory=list)
    fixes: List[FixRecommendation] = field(default_factory=list)
    associated_pattern_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "subcategory_id": self.subcategory_id,
            "document_type": self.document_type.value,
            "content": self.content,
            "graph_signals": [s.to_dict() for s in self.graph_signals],
            "behavioral_signatures": self.behavioral_signatures,
            "false_positive_indicators": self.false_positive_indicators,
            "code_patterns": [p.to_dict() for p in self.code_patterns],
            "exploits": [e.to_dict() for e in self.exploits],
            "fixes": [f.to_dict() for f in self.fixes],
            "associated_pattern_ids": self.associated_pattern_ids,
        }
        if self.operation_sequences:
            result["operation_sequences"] = self.operation_sequences.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """Deserialize from dictionary."""
        op_seq = data.get("operation_sequences")
        return cls(
            subcategory_id=data.get("subcategory_id", ""),
            document_type=DocumentType.from_string(data.get("document_type", "index")),
            content=data.get("content", ""),
            graph_signals=[
                GraphSignal.from_dict(s) for s in data.get("graph_signals", [])
            ],
            operation_sequences=OperationSequences.from_dict(op_seq) if op_seq else None,
            behavioral_signatures=data.get("behavioral_signatures", []),
            false_positive_indicators=data.get("false_positive_indicators", []),
            code_patterns=[
                CodePattern.from_dict(p) for p in data.get("code_patterns", [])
            ],
            exploits=[
                ExploitReference.from_dict(e) for e in data.get("exploits", [])
            ],
            fixes=[
                FixRecommendation.from_dict(f) for f in data.get("fixes", [])
            ],
            associated_pattern_ids=data.get("associated_pattern_ids", []),
        )

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        if self.content:
            return self.content

        lines = [f"# {self.document_type.value.title()}: {self.subcategory_id}", ""]

        if self.document_type == DocumentType.DETECTION:
            return self._detection_markdown()
        elif self.document_type == DocumentType.PATTERNS:
            return self._patterns_markdown()
        elif self.document_type == DocumentType.EXPLOITS:
            return self._exploits_markdown()
        elif self.document_type == DocumentType.FIXES:
            return self._fixes_markdown()

        return "\n".join(lines)

    def _detection_markdown(self) -> str:
        """Generate detection document markdown."""
        lines = [f"# Detection: {self.subcategory_id}", ""]

        if self.graph_signals:
            lines.append("## Graph Signals")
            lines.append("| Property | Expected | Critical? |")
            lines.append("|----------|----------|-----------|")
            for sig in self.graph_signals:
                critical = "YES" if sig.critical else "NO"
                lines.append(f"| {sig.property_name} | {sig.expected} | {critical} |")
            lines.append("")

        if self.operation_sequences:
            lines.append("## Operation Sequences")
            if self.operation_sequences.vulnerable:
                lines.append("**Vulnerable:**")
                for seq in self.operation_sequences.vulnerable:
                    lines.append(f"- `{seq}`")
            if self.operation_sequences.safe:
                lines.append("**Safe:**")
                for seq in self.operation_sequences.safe:
                    lines.append(f"- `{seq}`")
            lines.append("")

        if self.behavioral_signatures:
            lines.append("## Behavioral Signatures")
            for sig in self.behavioral_signatures:
                lines.append(f"- `{sig}`")
            lines.append("")

        if self.false_positive_indicators:
            lines.append("## False Positive Indicators")
            for fp in self.false_positive_indicators:
                lines.append(f"- {fp}")
            lines.append("")

        return "\n".join(lines)

    def _patterns_markdown(self) -> str:
        """Generate patterns document markdown."""
        lines = [f"# Patterns: {self.subcategory_id}", ""]

        if self.associated_pattern_ids:
            lines.append(f"**Associated Patterns:** {', '.join(self.associated_pattern_ids)}")
            lines.append("")

        for pattern in self.code_patterns:
            lines.append(f"## {pattern.name}")
            if pattern.description:
                lines.append(pattern.description)
            lines.append("")
            lines.append("**Vulnerable:**")
            lines.append("```solidity")
            lines.append(pattern.vulnerable_code)
            lines.append("```")
            if pattern.safe_code:
                lines.append("")
                lines.append("**Safe:**")
                lines.append("```solidity")
                lines.append(pattern.safe_code)
                lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _exploits_markdown(self) -> str:
        """Generate exploits document markdown."""
        lines = [f"# Exploits: {self.subcategory_id}", ""]

        for exploit in self.exploits:
            lines.append(f"## {exploit.name}")
            lines.append(f"**Date:** {exploit.date}")
            if exploit.loss_usd:
                lines.append(f"**Loss:** ${exploit.loss_usd}")
            if exploit.protocol:
                lines.append(f"**Protocol:** {exploit.protocol}")
            lines.append("")
            if exploit.description:
                lines.append(exploit.description)
                lines.append("")
            if exploit.attack_steps:
                lines.append("**Attack Steps:**")
                for step in exploit.attack_steps:
                    lines.append(f"- {step}")
                lines.append("")
            if exploit.postmortem_url:
                lines.append(f"**Postmortem:** [{exploit.postmortem_url}]({exploit.postmortem_url})")
                lines.append("")

        return "\n".join(lines)

    def _fixes_markdown(self) -> str:
        """Generate fixes document markdown."""
        lines = [f"# Fixes: {self.subcategory_id}", ""]

        for fix in self.fixes:
            lines.append(f"## {fix.name}")
            lines.append(fix.description)
            lines.append("")
            if fix.code_example:
                lines.append("**Example:**")
                lines.append("```solidity")
                lines.append(fix.code_example)
                lines.append("```")
                lines.append("")
            lines.append(f"**Effectiveness:** {fix.effectiveness}")
            lines.append(f"**Complexity:** {fix.complexity}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class NavigationMetadata:
    """Navigation metadata for LLM agents."""

    hints: List[str] = field(default_factory=list)
    depth_guide: Dict[str, str] = field(default_factory=dict)
    retrieval_strategy: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "hints": self.hints,
            "depth_guide": self.depth_guide,
            "retrieval_strategy": self.retrieval_strategy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NavigationMetadata":
        """Deserialize from dictionary."""
        return cls(
            hints=data.get("hints", []),
            depth_guide=data.get("depth_guide", {}),
            retrieval_strategy=data.get("retrieval_strategy", {}),
        )


@dataclass
class CacheConfig:
    """Cache configuration for prompt caching."""

    name: str
    content: str
    cache_control: CacheControlType
    estimated_tokens: int
    key: str = ""
    key_pattern: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "content": self.content,
            "cache_control": self.cache_control.value,
            "estimated_tokens": self.estimated_tokens,
            "key": self.key,
            "key_pattern": self.key_pattern,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheConfig":
        """Deserialize from dictionary."""
        cache_control = data.get("cache_control", "none")
        if isinstance(cache_control, str):
            cache_control = CacheControlType(cache_control)
        return cls(
            name=data.get("name", ""),
            content=data.get("content", ""),
            cache_control=cache_control,
            estimated_tokens=data.get("estimated_tokens", 0),
            key=data.get("key", ""),
            key_pattern=data.get("key_pattern", ""),
        )


@dataclass
class KnowledgeIndex:
    """Top-level knowledge index."""

    version: str = SCHEMA_VERSION
    last_updated: str = ""
    categories: Dict[str, Category] = field(default_factory=dict)
    navigation: Optional[NavigationMetadata] = None
    operation_to_categories: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    signature_to_categories: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cache: Dict[str, CacheConfig] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "schema_version": self.version,
            "last_updated": self.last_updated,
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
            "operation_to_categories": self.operation_to_categories,
            "signature_to_categories": self.signature_to_categories,
            "cache": {k: v.to_dict() for k, v in self.cache.items()},
            "stats": self.stats,
        }
        if self.navigation:
            result["navigation"] = self.navigation.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeIndex":
        """Deserialize from dictionary."""
        nav_data = data.get("navigation")
        categories = {}
        for cat_id, cat_data in data.get("categories", {}).items():
            if isinstance(cat_data, dict):
                cat_data["id"] = cat_id
                categories[cat_id] = Category.from_dict(cat_data)

        cache = {}
        for layer_name, layer_data in data.get("cache", {}).items():
            if isinstance(layer_data, dict):
                cache[layer_name] = CacheConfig.from_dict(layer_data)

        return cls(
            version=data.get("schema_version", SCHEMA_VERSION),
            last_updated=data.get("last_updated", ""),
            categories=categories,
            navigation=NavigationMetadata.from_dict(nav_data) if nav_data else None,
            operation_to_categories=data.get("operation_to_categories", {}),
            signature_to_categories=data.get("signature_to_categories", {}),
            cache=cache,
            stats=data.get("stats", {}),
        )

    def get_category(self, category_id: str) -> Optional[Category]:
        """Get a category by ID."""
        return self.categories.get(category_id)

    def get_all_category_ids(self) -> List[str]:
        """Get all category IDs."""
        return list(self.categories.keys())

    def get_categories_for_operation(
        self, operation: str, include_secondary: bool = False
    ) -> List[str]:
        """Get categories relevant to a semantic operation."""
        mapping = self.operation_to_categories.get(operation, {})
        result = mapping.get("primary", [])
        if include_secondary:
            result = result + mapping.get("secondary", [])
        return result

    def get_category_for_signature(
        self, signature: str
    ) -> Optional[Tuple[str, str, str]]:
        """Get category/subcategory/severity for a behavioral signature."""
        mapping = self.signature_to_categories.get(signature)
        if mapping:
            return (
                mapping.get("category", ""),
                mapping.get("subcategory", ""),
                mapping.get("severity", ""),
            )
        return None

    def get_navigation_context(self) -> str:
        """Generate navigation context for LLM agents."""
        lines = [
            "# VulnDocs Knowledge Navigation",
            "",
            "## Available Categories",
        ]

        for cat_id, cat in self.categories.items():
            lines.append(f"")
            lines.append(f"### {cat.name} (`{cat_id}`)")
            desc = cat.description[:100] + "..." if len(cat.description) > 100 else cat.description
            lines.append(desc)
            lines.append("")
            lines.append("Subcategories:")
            for sub in cat.subcategories[:5]:
                lines.append(f"  - `{sub.id}`: {sub.name}")
            if len(cat.subcategories) > 5:
                lines.append(f"  - ... and {len(cat.subcategories) - 5} more")

        lines.append("")
        lines.append("## Navigation Commands")
        lines.append("- `get_context(category, subcategory, depth)` - Get knowledge")
        lines.append("- `search(query)` - Search knowledge base")
        lines.append("- Depths: index, overview, detection, patterns, exploits, fixes, full")

        return "\n".join(lines)

    def estimate_total_tokens(self) -> int:
        """Estimate total tokens for all knowledge."""
        total = 0
        for cat in self.categories.values():
            total += cat.token_estimate
            for sub in cat.subcategories:
                # Subcategory refs don't have token estimates, use default
                total += 500
        return total


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_id(value: str) -> List[str]:
    """Validate an ID value."""
    errors = []
    if not value:
        errors.append("ID cannot be empty")
    elif not ID_PATTERN.match(value):
        errors.append(f"ID '{value}' must be lowercase alphanumeric with dashes")
    return errors


def validate_severity_range(severities: List[str]) -> List[str]:
    """Validate severity range."""
    errors = []
    for sev in severities:
        if sev.lower() not in VALID_SEVERITIES:
            errors.append(f"Invalid severity: {sev}")
    return errors


def validate_category(data: Dict[str, Any]) -> List[str]:
    """Validate category data against schema.

    Args:
        data: Category data dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required fields
    required_fields = ["id", "name", "description"]
    for field_name in required_fields:
        if field_name not in data or not data[field_name]:
            errors.append(f"Missing required field: {field_name}")

    # Validate ID
    if "id" in data:
        errors.extend(validate_id(data["id"]))

    # Validate severity range
    if "severity_range" in data:
        errors.extend(validate_severity_range(data["severity_range"]))

    # Validate subcategories
    if "subcategories" in data:
        for i, sub in enumerate(data["subcategories"]):
            if isinstance(sub, dict):
                if "id" not in sub or not sub["id"]:
                    errors.append(f"Subcategory {i} missing 'id'")
                elif not ID_PATTERN.match(sub["id"]):
                    errors.append(f"Subcategory {i} has invalid ID: {sub['id']}")
            elif isinstance(sub, str):
                if not ID_PATTERN.match(sub):
                    errors.append(f"Subcategory {i} has invalid ID: {sub}")

    return errors


def validate_subcategory(data: Dict[str, Any]) -> List[str]:
    """Validate subcategory data against schema.

    Args:
        data: Subcategory data dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required fields
    required_fields = ["id", "name", "description", "parent_category"]
    for field_name in required_fields:
        if field_name not in data or not data[field_name]:
            errors.append(f"Missing required field: {field_name}")

    # Validate ID
    if "id" in data:
        errors.extend(validate_id(data["id"]))

    # Validate parent category
    if "parent_category" in data:
        errors.extend(validate_id(data["parent_category"]))

    # Validate severity range
    if "severity_range" in data:
        errors.extend(validate_severity_range(data["severity_range"]))

    # Validate graph signals
    if "graph_signals" in data:
        for i, sig in enumerate(data["graph_signals"]):
            if not isinstance(sig, dict):
                errors.append(f"Graph signal {i} is not a dictionary")
            elif "property" not in sig:
                errors.append(f"Graph signal {i} missing 'property'")

    return errors


def validate_document(data: Dict[str, Any]) -> List[str]:
    """Validate document data against schema.

    Args:
        data: Document data dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required fields
    if "subcategory_id" not in data or not data["subcategory_id"]:
        errors.append("Missing required field: subcategory_id")

    # Validate document type
    if "document_type" in data:
        valid_types = {"index", "overview", "detection", "patterns", "exploits", "fixes"}
        if data["document_type"] not in valid_types:
            errors.append(f"Invalid document_type: {data['document_type']}")

    return errors


def validate_index(data: Dict[str, Any]) -> List[str]:
    """Validate knowledge index data against schema.

    Args:
        data: Index data dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate version
    if "schema_version" in data:
        version = data["schema_version"]
        if not re.match(r"^\d+\.\d+$", version):
            errors.append(f"Invalid version format: {version}")

    # Validate categories
    if "categories" in data:
        for cat_id, cat_data in data["categories"].items():
            if not ID_PATTERN.match(cat_id):
                errors.append(f"Invalid category ID: {cat_id}")
            if isinstance(cat_data, dict):
                cat_errors = validate_category(cat_data)
                for err in cat_errors:
                    errors.append(f"Category '{cat_id}': {err}")

    return errors


# =============================================================================
# LOADING FUNCTIONS
# =============================================================================


def load_index(knowledge_dir: Optional[Path] = None) -> KnowledgeIndex:
    """Load the knowledge index from disk.

    Args:
        knowledge_dir: Path to knowledge directory (default: KNOWLEDGE_DIR)

    Returns:
        KnowledgeIndex object
    """
    if knowledge_dir is None:
        knowledge_dir = KNOWLEDGE_DIR

    index_path = knowledge_dir / "index.yaml"
    if not index_path.exists():
        return KnowledgeIndex()

    with open(index_path, "r") as f:
        data = yaml.safe_load(f)

    return KnowledgeIndex.from_dict(data)


def load_category(
    category_id: str, knowledge_dir: Optional[Path] = None
) -> Optional[Category]:
    """Load a category from disk.

    Args:
        category_id: Category ID
        knowledge_dir: Path to knowledge directory (default: KNOWLEDGE_DIR)

    Returns:
        Category object or None if not found
    """
    if knowledge_dir is None:
        knowledge_dir = KNOWLEDGE_DIR

    cat_path = knowledge_dir / "categories" / category_id / "index.yaml"
    if not cat_path.exists():
        # Try loading from main index
        index = load_index(knowledge_dir)
        return index.get_category(category_id)

    with open(cat_path, "r") as f:
        data = yaml.safe_load(f)
        data["id"] = category_id

    return Category.from_dict(data)


def load_subcategory(
    category_id: str,
    subcategory_id: str,
    knowledge_dir: Optional[Path] = None,
) -> Optional[Subcategory]:
    """Load a subcategory from disk.

    Args:
        category_id: Parent category ID
        subcategory_id: Subcategory ID
        knowledge_dir: Path to knowledge directory (default: KNOWLEDGE_DIR)

    Returns:
        Subcategory object or None if not found
    """
    if knowledge_dir is None:
        knowledge_dir = KNOWLEDGE_DIR

    sub_path = (
        knowledge_dir
        / "categories"
        / category_id
        / "subcategories"
        / subcategory_id
        / "index.yaml"
    )
    if not sub_path.exists():
        return None

    with open(sub_path, "r") as f:
        data = yaml.safe_load(f)
        data["id"] = subcategory_id
        data["parent_category"] = category_id

    return Subcategory.from_dict(data)
