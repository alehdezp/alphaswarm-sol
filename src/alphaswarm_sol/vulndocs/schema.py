"""Knowledge Schema for VulnDocs.

Task 17.0: Define YAML schema for vulnerability knowledge documentation.

This module defines the structure for:
- Vulnerability categories (reentrancy, access-control, oracle, etc.)
- Subcategories within each category
- Document types (detection, patterns, exploits, fixes)
- Knowledge depth levels for context retrieval

Schema Design Principles:
1. Minimal token footprint - each field justified
2. LLM-navigable structure - clear hierarchy
3. Cacheable blocks - stable content for prompt caching
4. Evidence-linked - references to real exploits
5. Self-describing - schema explains itself to LLMs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class VulnCategory(Enum):
    """Top-level vulnerability categories.

    Each category represents a distinct class of smart contract vulnerabilities.
    Categories are designed to be mutually exclusive - a vulnerability belongs
    to exactly one category.
    """

    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access-control"
    ORACLE = "oracle"
    FLASH_LOAN = "flash-loan"
    MEV = "mev"
    DOS = "dos"
    TOKEN = "token"
    UPGRADE = "upgrade"
    CRYPTO = "crypto"
    GOVERNANCE = "governance"
    LOGIC = "logic"

    @classmethod
    def from_string(cls, value: str) -> "VulnCategory":
        """Parse category from string, handling common variations."""
        normalized = value.lower().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError:
            # Handle common aliases
            aliases = {
                "access": cls.ACCESS_CONTROL,
                "access_control": cls.ACCESS_CONTROL,
                "price": cls.ORACLE,
                "price-manipulation": cls.ORACLE,
                "flashloan": cls.FLASH_LOAN,
                "mev-attack": cls.MEV,
                "denial-of-service": cls.DOS,
                "erc20": cls.TOKEN,
                "upgradability": cls.UPGRADE,
                "cryptography": cls.CRYPTO,
                "gov": cls.GOVERNANCE,
                "business-logic": cls.LOGIC,
            }
            if normalized in aliases:
                return aliases[normalized]
            raise ValueError(f"Unknown category: {value}")

    @classmethod
    def all_categories(cls) -> List[str]:
        """Get all category values."""
        return [c.value for c in cls]


class KnowledgeDepth(Enum):
    """Depth levels for knowledge retrieval.

    Controls how much detail to retrieve when navigating the knowledge hierarchy.
    """

    INDEX = "index"  # Just category/subcategory names
    OVERVIEW = "overview"  # High-level description
    DETECTION = "detection"  # How to detect (graph signals, patterns)
    PATTERNS = "patterns"  # Known code patterns
    EXPLOITS = "exploits"  # Real-world exploit examples
    FIXES = "fixes"  # Remediation guidance
    FULL = "full"  # All available content

    @classmethod
    def from_string(cls, value: str) -> "KnowledgeDepth":
        """Parse depth from string."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.DETECTION  # Default


class DocumentType(Enum):
    """Types of knowledge documents.

    Each document type serves a specific purpose in vulnerability analysis.
    """

    INDEX = "index"  # Navigation index (index.yaml)
    OVERVIEW = "overview"  # Category overview (overview.md)
    DETECTION = "detection"  # Detection guidance (detection.md)
    PATTERNS = "patterns"  # Code patterns (patterns.md)
    EXPLOITS = "exploits"  # Real exploits (exploits.md)
    FIXES = "fixes"  # Remediation (fixes.md)


@dataclass
class GraphSignal:
    """A graph property signal for detection.

    Represents a property from the VKG that indicates potential vulnerability.
    """

    property_name: str
    expected_value: Any
    is_critical: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "property": self.property_name,
            "expected": self.expected_value,
            "critical": self.is_critical,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphSignal":
        """Deserialize from dictionary."""
        return cls(
            property_name=data.get("property", ""),
            expected_value=data.get("expected"),
            is_critical=data.get("critical", False),
            description=data.get("description", ""),
        )


@dataclass
class CodePattern:
    """A code pattern example for detection.

    Shows vulnerable and safe code variants for comparison.
    """

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
class RealExploit:
    """A real-world exploit reference.

    Links to actual security incidents for evidence-based analysis.
    """

    name: str
    date: str = ""
    loss_usd: str = ""
    protocol: str = ""
    chain: str = "ethereum"
    description: str = ""
    references: List[str] = field(default_factory=list)
    cve_id: str = ""
    solodit_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "date": self.date,
            "loss_usd": self.loss_usd,
            "protocol": self.protocol,
            "chain": self.chain,
            "description": self.description,
            "references": self.references,
            "cve_id": self.cve_id,
            "solodit_id": self.solodit_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RealExploit":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            date=data.get("date", ""),
            loss_usd=data.get("loss_usd", ""),
            protocol=data.get("protocol", ""),
            chain=data.get("chain", "ethereum"),
            description=data.get("description", ""),
            references=data.get("references", []),
            cve_id=data.get("cve_id", ""),
            solodit_id=data.get("solodit_id", ""),
        )


@dataclass
class FixRecommendation:
    """A remediation recommendation.

    Provides guidance on how to fix a vulnerability.
    """

    name: str
    description: str
    code_example: str = ""
    effectiveness: str = "high"  # high, medium, low
    complexity: str = "low"  # high, medium, low

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
class VulnSubcategory:
    """A vulnerability subcategory within a category.

    Subcategories represent specific variants of a vulnerability class.
    For example, "classic" reentrancy vs "cross-function" reentrancy.
    """

    id: str
    name: str
    description: str
    parent_category: str
    severity_range: List[str] = field(default_factory=lambda: ["medium", "high"])
    patterns: List[str] = field(default_factory=list)  # Pattern IDs
    relevant_properties: List[str] = field(default_factory=list)
    graph_signals: List[GraphSignal] = field(default_factory=list)
    code_patterns: List[CodePattern] = field(default_factory=list)
    exploits: List[RealExploit] = field(default_factory=list)
    fixes: List[FixRecommendation] = field(default_factory=list)
    false_positive_indicators: List[str] = field(default_factory=list)
    token_estimate: int = 500  # Estimated tokens for this subcategory

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_category": self.parent_category,
            "severity_range": self.severity_range,
            "patterns": self.patterns,
            "relevant_properties": self.relevant_properties,
            "graph_signals": [s.to_dict() for s in self.graph_signals],
            "code_patterns": [p.to_dict() for p in self.code_patterns],
            "exploits": [e.to_dict() for e in self.exploits],
            "fixes": [f.to_dict() for f in self.fixes],
            "false_positive_indicators": self.false_positive_indicators,
            "token_estimate": self.token_estimate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VulnSubcategory":
        """Deserialize from dictionary."""
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
            code_patterns=[
                CodePattern.from_dict(p) for p in data.get("code_patterns", [])
            ],
            exploits=[RealExploit.from_dict(e) for e in data.get("exploits", [])],
            fixes=[FixRecommendation.from_dict(f) for f in data.get("fixes", [])],
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
                critical = "YES" if sig.is_critical else "NO"
                lines.append(f"| {sig.property_name} | {sig.expected_value} | {critical} |")
            lines.append("")

        if self.relevant_properties:
            lines.append("## Relevant Properties")
            lines.append(", ".join(self.relevant_properties))
            lines.append("")

        if self.false_positive_indicators:
            lines.append("## False Positive Indicators")
            for fp in self.false_positive_indicators:
                lines.append(f"- {fp}")
            lines.append("")

        return "\n".join(lines)

    def get_patterns_context(self) -> str:
        """Generate patterns-focused context string."""
        lines = [
            f"# Patterns: {self.name}",
            "",
        ]

        if self.patterns:
            lines.append(f"**Associated Patterns:** {', '.join(self.patterns)}")
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


@dataclass
class CategoryIndex:
    """Index for a vulnerability category.

    Contains metadata and references to all subcategories.
    Used for navigation and context retrieval.
    """

    id: str
    name: str
    description: str
    severity_range: List[str] = field(default_factory=lambda: ["medium", "critical"])
    subcategories: List[VulnSubcategory] = field(default_factory=list)
    relevant_properties: List[str] = field(default_factory=list)
    context_cache_key: str = ""
    token_estimate: int = 1500  # Estimated tokens for category overview

    def __post_init__(self):
        """Set default cache key if not provided."""
        if not self.context_cache_key:
            self.context_cache_key = f"{self.id}-v1"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity_range": self.severity_range,
            "subcategories": [s.to_dict() for s in self.subcategories],
            "relevant_properties": self.relevant_properties,
            "context_cache_key": self.context_cache_key,
            "token_estimate": self.token_estimate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CategoryIndex":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            severity_range=data.get("severity_range", ["medium", "critical"]),
            subcategories=[
                VulnSubcategory.from_dict(s) for s in data.get("subcategories", [])
            ],
            relevant_properties=data.get("relevant_properties", []),
            context_cache_key=data.get("context_cache_key", ""),
            token_estimate=data.get("token_estimate", 1500),
        )

    def get_subcategory(self, subcategory_id: str) -> Optional[VulnSubcategory]:
        """Get a subcategory by ID."""
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
            lines.append(f"- **{sub.name}** (`{sub.id}`): {sub.description}")

        lines.append("")
        lines.append("## Relevant Graph Properties")
        lines.append(", ".join(self.relevant_properties[:10]))

        return "\n".join(lines)


@dataclass
class SubcategoryIndex:
    """Lightweight index for a subcategory.

    Used for navigation without loading full subcategory data.
    """

    id: str
    name: str
    description: str
    parent_category: str
    patterns: List[str] = field(default_factory=list)
    token_estimate: int = 500

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parent_category": self.parent_category,
            "patterns": self.patterns,
            "token_estimate": self.token_estimate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubcategoryIndex":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            parent_category=data.get("parent_category", ""),
            patterns=data.get("patterns", []),
            token_estimate=data.get("token_estimate", 500),
        )


@dataclass
class DetectionDocument:
    """Detection guidance document.

    Contains specific guidance on how to detect a vulnerability.
    """

    subcategory_id: str
    graph_signals: List[GraphSignal] = field(default_factory=list)
    operation_sequences: List[str] = field(default_factory=list)
    behavioral_signatures: List[str] = field(default_factory=list)
    false_positive_indicators: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "subcategory_id": self.subcategory_id,
            "graph_signals": [s.to_dict() for s in self.graph_signals],
            "operation_sequences": self.operation_sequences,
            "behavioral_signatures": self.behavioral_signatures,
            "false_positive_indicators": self.false_positive_indicators,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DetectionDocument":
        """Deserialize from dictionary."""
        return cls(
            subcategory_id=data.get("subcategory_id", ""),
            graph_signals=[
                GraphSignal.from_dict(s) for s in data.get("graph_signals", [])
            ],
            operation_sequences=data.get("operation_sequences", []),
            behavioral_signatures=data.get("behavioral_signatures", []),
            false_positive_indicators=data.get("false_positive_indicators", []),
        )

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        lines = [
            f"# Detection: {self.subcategory_id}",
            "",
        ]

        if self.graph_signals:
            lines.append("## Graph Signals")
            lines.append("| Property | Expected | Critical? |")
            lines.append("|----------|----------|-----------|")
            for sig in self.graph_signals:
                critical = "YES" if sig.is_critical else "NO"
                lines.append(f"| {sig.property_name} | {sig.expected_value} | {critical} |")
            lines.append("")

        if self.operation_sequences:
            lines.append("## Operation Sequences")
            for seq in self.operation_sequences:
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


@dataclass
class PatternDocument:
    """Code patterns document.

    Contains example vulnerable and safe code patterns.
    """

    subcategory_id: str
    patterns: List[CodePattern] = field(default_factory=list)
    associated_pattern_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "subcategory_id": self.subcategory_id,
            "patterns": [p.to_dict() for p in self.patterns],
            "associated_pattern_ids": self.associated_pattern_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternDocument":
        """Deserialize from dictionary."""
        return cls(
            subcategory_id=data.get("subcategory_id", ""),
            patterns=[CodePattern.from_dict(p) for p in data.get("patterns", [])],
            associated_pattern_ids=data.get("associated_pattern_ids", []),
        )

    def to_markdown(self) -> str:
        """Generate markdown representation."""
        lines = [
            f"# Patterns: {self.subcategory_id}",
            "",
        ]

        if self.associated_pattern_ids:
            lines.append(f"**Associated Patterns:** {', '.join(self.associated_pattern_ids)}")
            lines.append("")

        for pattern in self.patterns:
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


@dataclass
class KnowledgeIndex:
    """Top-level knowledge index.

    The root of the vulnerability knowledge hierarchy.
    Contains all categories and navigation metadata.
    """

    version: str = "1.0"
    categories: Dict[str, CategoryIndex] = field(default_factory=dict)
    last_updated: str = ""
    source_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "version": self.version,
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
            "last_updated": self.last_updated,
            "source_count": self.source_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeIndex":
        """Deserialize from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            categories={
                k: CategoryIndex.from_dict(v)
                for k, v in data.get("categories", {}).items()
            },
            last_updated=data.get("last_updated", ""),
            source_count=data.get("source_count", 0),
        )

    def get_category(self, category_id: str) -> Optional[CategoryIndex]:
        """Get a category by ID."""
        return self.categories.get(category_id)

    def get_all_category_ids(self) -> List[str]:
        """Get all category IDs."""
        return list(self.categories.keys())

    def get_subcategory(
        self, category_id: str, subcategory_id: str
    ) -> Optional[VulnSubcategory]:
        """Get a subcategory by category and subcategory ID."""
        category = self.get_category(category_id)
        if category:
            return category.get_subcategory(subcategory_id)
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
            lines.append(cat.description[:100] + "..." if len(cat.description) > 100 else cat.description)
            lines.append("")
            lines.append("Subcategories:")
            for sub in cat.subcategories[:5]:  # Limit for token efficiency
                lines.append(f"  - `{sub.id}`: {sub.name}")
            if len(cat.subcategories) > 5:
                lines.append(f"  - ... and {len(cat.subcategories) - 5} more")

        lines.append("")
        lines.append("## Navigation Commands")
        lines.append("- `get_context(category, subcategory, depth)` - Get knowledge for specific vulnerability")
        lines.append("- `search(query)` - Search knowledge base")
        lines.append("- Depths: index, overview, detection, patterns, exploits, fixes, full")

        return "\n".join(lines)

    def estimate_total_tokens(self) -> int:
        """Estimate total tokens for all knowledge."""
        total = 0
        for cat in self.categories.values():
            total += cat.token_estimate
            for sub in cat.subcategories:
                total += sub.token_estimate
        return total


# =============================================================================
# Schema Validation
# =============================================================================


def validate_category_index(data: Dict[str, Any]) -> List[str]:
    """Validate category index data against schema.

    Args:
        data: Category index data dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    required_fields = ["id", "name", "description"]
    for field_name in required_fields:
        if field_name not in data or not data[field_name]:
            errors.append(f"Missing required field: {field_name}")

    if "subcategories" in data:
        for i, sub in enumerate(data["subcategories"]):
            if not isinstance(sub, dict):
                errors.append(f"Subcategory {i} is not a dictionary")
                continue
            if "id" not in sub or not sub["id"]:
                errors.append(f"Subcategory {i} missing 'id'")
            if "name" not in sub or not sub["name"]:
                errors.append(f"Subcategory {i} missing 'name'")

    return errors


def validate_subcategory(data: Dict[str, Any]) -> List[str]:
    """Validate subcategory data against schema.

    Args:
        data: Subcategory data dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    required_fields = ["id", "name", "description", "parent_category"]
    for field_name in required_fields:
        if field_name not in data or not data[field_name]:
            errors.append(f"Missing required field: {field_name}")

    if "graph_signals" in data:
        for i, sig in enumerate(data["graph_signals"]):
            if not isinstance(sig, dict):
                errors.append(f"Graph signal {i} is not a dictionary")
                continue
            if "property" not in sig:
                errors.append(f"Graph signal {i} missing 'property'")

    return errors


# =============================================================================
# Phase 5.4: Pydantic Schema Models for Unified VulnDocs-Patterns System
# =============================================================================
#
# These pydantic models validate the NEW unified structure created in Phase 5.4.
# They are separate from the dataclass-based models above (Phase 17-18 system).
#

from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any

from alphaswarm_sol.vulndocs.types import (
    Severity,
    ValidationLevel,
    PatternId,
    CategoryPath,
    VqlQuery,
    GraphPattern,
    SemanticTrigger,
    PatternScope,
    TestStatus,
    VALID_SEMANTIC_OPERATIONS,
    VALID_PATTERN_SCOPES,
    VALID_TEST_STATUSES,
)


class TestCoverage(BaseModel):
    """Test coverage tracking for patterns.

    Tracks precision, recall, and overall status as patterns mature.
    """

    precision: float | None = None
    recall: float | None = None
    status: TestStatus = "draft"

    @field_validator("precision", "recall")
    @classmethod
    def validate_percentage(cls, v: float | None) -> float | None:
        """Validate precision/recall are between 0 and 1."""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Precision and recall must be between 0.0 and 1.0")
        return v


class VulnDocIndex(BaseModel):
    """Pydantic model for index.yaml validation.

    Validates the structure of index.yaml files in vulnerability subcategory folders.
    Supports Phase 7 test generation fields (semantic_triggers, vql_queries, etc.).

    Required fields:
    - id: Unique vulnerability identifier
    - category: Top-level category (e.g., "oracle", "reentrancy")
    - subcategory: Specific subcategory (e.g., "price-manipulation", "classic")
    - severity: Severity level
    - vulndoc: Explicit path for validation (must match category/subcategory)

    Phase 7 test generation fields (optional):
    - semantic_triggers: VKG operations to look for
    - vql_queries: VQL queries for detection
    - graph_patterns: Structural patterns in the knowledge graph
    - reasoning_template: Pseudocode/semantic logic for test generation

    Pattern and test tracking:
    - patterns: List of pattern IDs associated with this vulnerability
    - test_coverage: List of test files that cover this vulnerability
    """

    # Required fields
    id: str = Field(..., description="Unique vulnerability identifier")

    # Category fields - accept both formats (parent_category from entries, category from schema)
    parent_category: str | None = Field(None, description="Top-level category (from index.yaml entries)")
    category: str | None = Field(None, description="Top-level category (derived or explicit)")
    subcategory: str | None = Field(None, description="Specific subcategory (derived from id if absent)")
    name: str | None = Field(None, description="Human-readable vulnerability name")

    # Severity - accept single value or range
    severity: Severity | None = Field(None, description="Severity level (single)")
    vulndoc: str | None = Field(
        None,
        description="Explicit vulndoc path for validation (category/subcategory)",
    )

    # Description
    description: str | None = Field(
        None, description="Clear description of vulnerability"
    )

    # Phase 7 test generation fields
    semantic_triggers: list[SemanticTrigger] = Field(
        default_factory=list,
        description="VKG operations to look for (e.g., TRANSFERS_ETH, WRITES_BALANCE)",
    )
    vql_queries: list[VqlQuery] = Field(
        default_factory=list, description="Example VQL queries for detection"
    )
    graph_patterns: list[GraphPattern] = Field(
        default_factory=list,
        description="Graph patterns (e.g., 'R:bal->X:out->W:bal')",
    )
    reasoning_template: str | None = Field(
        None, description="Reasoning template for LLM-based detection"
    )

    # VKG properties
    relevant_properties: list[str] = Field(
        default_factory=list, description="VKG properties relevant for detection"
    )

    # Graph signals
    graph_signals: list[dict[str, Any]] = Field(
        default_factory=list, description="Graph property signals"
    )

    # Behavioral signatures
    behavioral_signatures: list[str] = Field(
        default_factory=list, description="Behavioral signatures (operation sequences)"
    )

    # Operation sequences
    operation_sequences: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Operation sequences (vulnerable vs safe)",
    )

    # False positive indicators
    false_positive_indicators: list[str] = Field(
        default_factory=list,
        description="Indicators that suggest false positive",
    )

    # Pattern and test tracking
    patterns: list[PatternId] = Field(
        default_factory=list, description="Associated pattern IDs"
    )
    test_coverage: list[str] = Field(
        default_factory=list, description="Test files covering this vulnerability"
    )

    # Metadata
    severity_range: list[Severity] = Field(
        default_factory=list, description="Range of possible severities"
    )
    related_exploits: list[str] = Field(
        default_factory=list, description="Related exploit references (one-line)"
    )
    created: str | None = Field(None, description="Creation date (YYYY-MM-DD)")
    updated: str | None = Field(None, description="Last update date (YYYY-MM-DD)")
    token_estimate: int | None = Field(
        None, description="Estimated tokens for this vulnerability"
    )

    @field_validator("semantic_triggers")
    @classmethod
    def validate_semantic_triggers(cls, v: list[str]) -> list[str]:
        """Validate semantic triggers against known operations."""
        for trigger in v:
            if trigger not in VALID_SEMANTIC_OPERATIONS:
                raise ValueError(
                    f"Invalid semantic operation: {trigger}. "
                    f"Must be one of: {', '.join(VALID_SEMANTIC_OPERATIONS)}"
                )
        return v

    @model_validator(mode="after")
    def normalize_fields(self) -> "VulnDocIndex":
        """Normalize fields: derive category/subcategory from parent_category/id.

        Entries in vulndocs/ use parent_category instead of category, and
        subcategory is derived from the id or folder name. This validator
        ensures both old-style (explicit category/subcategory/vulndoc) and
        new-style (parent_category + id) entries work.
        """
        # Derive category from parent_category if not set
        if not self.category and self.parent_category:
            self.category = self.parent_category

        # Derive subcategory from id if not set
        if not self.subcategory and self.id:
            self.subcategory = self.id

        # Derive vulndoc path from category/subcategory if not set
        if not self.vulndoc and self.category and self.subcategory:
            self.vulndoc = f"{self.category}/{self.subcategory}"

        # Derive severity from severity_range if not set
        if not self.severity and self.severity_range:
            self.severity = self.severity_range[0]

        # Validate vulndoc path if all fields are present
        if self.vulndoc and self.category and self.subcategory:
            expected_path = f"{self.category}/{self.subcategory}"
            if self.vulndoc != expected_path:
                raise ValueError(
                    f"vulndoc path '{self.vulndoc}' does not match "
                    f"expected '{expected_path}' (category/subcategory)"
                )
        return self


class PatternRef(BaseModel):
    """Pydantic model for pattern YAML validation.

    Validates the structure of pattern YAML files, ensuring they link back
    to their parent vulnerability folder via the vulndoc field.

    Required fields:
    - id: Pattern identifier (e.g., "oracle-001-twap")
    - name: Human-readable pattern name
    - severity: Severity level
    - vulndoc: CRITICAL - links to vulnerability folder (category/subcategory)

    Optional fields:
    - scope: Function, Contract, or Transaction
    - lens: List of lens categories
    - match: Pattern matching rules (tier_a, tier_b, tier_c)
    - test_coverage: Test metrics
    """

    # Required fields
    id: PatternId = Field(..., description="Pattern identifier (e.g., oracle-001-twap)")
    name: str = Field(..., description="Human-readable pattern name")
    severity: Severity = Field(..., description="Severity level")
    vulndoc: CategoryPath = Field(
        ..., description="Link to vulnerability folder (category/subcategory)"
    )

    # Optional fields
    scope: PatternScope = Field(
        default="Function", description="Pattern scope (Function, Contract, Transaction)"
    )
    lens: list[str] = Field(default_factory=list, description="Lens categories")
    match: dict[str, Any] | None = Field(
        None, description="Pattern matching rules (tier_a, tier_b, tier_c)"
    )

    # Test coverage
    test_coverage: TestCoverage | None = Field(
        None, description="Test coverage metrics"
    )

    # Additional metadata
    description: str | None = Field(None, description="Pattern description")
    confidence: str | None = Field(None, description="Detection confidence (high/medium/low)")
    tags: list[str] = Field(default_factory=list, description="Pattern tags")

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        """Validate scope is a valid value."""
        if v not in VALID_PATTERN_SCOPES:
            raise ValueError(
                f"Invalid scope: {v}. Must be one of: {', '.join(VALID_PATTERN_SCOPES)}"
            )
        return v


class VulnDocCategory(BaseModel):
    """Pydantic model for category-level metadata.

    Represents a top-level vulnerability category (e.g., reentrancy, oracle).
    """

    id: str = Field(..., description="Category identifier")
    name: str = Field(..., description="Category name")
    overview: str | None = Field(None, description="Category overview")
    subcategories: list[str] = Field(
        default_factory=list, description="List of subcategory IDs"
    )


# =============================================================================
# Helper Functions
# =============================================================================


def generate_json_schema() -> dict[str, Any]:
    """Generate JSON Schema from pydantic models.

    Returns a dictionary containing JSON Schemas for all models,
    suitable for external validation tools.

    Returns:
        dict: JSON Schema definitions for VulnDocIndex, PatternRef, etc.
    """
    return {
        "VulnDocIndex": VulnDocIndex.model_json_schema(),
        "PatternRef": PatternRef.model_json_schema(),
        "TestCoverage": TestCoverage.model_json_schema(),
        "VulnDocCategory": VulnDocCategory.model_json_schema(),
    }


def load_vulndoc_index(path: Path) -> VulnDocIndex:
    """Load and validate a VulnDocIndex from an index.yaml file.

    Args:
        path: Path to index.yaml file

    Returns:
        VulnDocIndex: Validated index data

    Raises:
        ValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
    """
    import yaml

    if not path.exists():
        raise FileNotFoundError(f"Index file not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return VulnDocIndex.model_validate(data)


def load_pattern_ref(path: Path) -> PatternRef:
    """Load and validate a PatternRef from a pattern YAML file.

    Args:
        path: Path to pattern YAML file

    Returns:
        PatternRef: Validated pattern data

    Raises:
        ValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
    """
    import yaml

    if not path.exists():
        raise FileNotFoundError(f"Pattern file not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    return PatternRef.model_validate(data)


# =============================================================================
# Phase 5.10: Pattern Context Pack (PCP) v2 Schema
# =============================================================================
#
# PCP v2 provides deterministic, evidence-first context packs for agentic
# pattern discovery. It is cacheable, schema-validated, and graph-first.
# No RAG or semantic search. Missing signals are marked "unknown", not safe.
#


class UnknownsPolicy(str, Enum):
    """How to treat missing evidence/signals."""

    UNKNOWN = "unknown"  # Default: missing = unknown (safe)
    FAIL = "fail"  # Strict: missing = validation failure
    WARN = "warn"  # Lenient: missing = warning only


class RiskPreScore(str, Enum):
    """Pre-computed risk score placeholder for economic context."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class AssetType(str, Enum):
    """Type of asset at risk."""

    NATIVE = "native"  # ETH, BNB, etc.
    TOKEN = "token"  # ERC20, ERC721, etc.
    GOVERNANCE = "governance"  # Voting power
    MIXED = "mixed"  # Multiple types
    UNKNOWN = "unknown"


class TrustBoundary(str, Enum):
    """Trust boundary being crossed."""

    USER_TO_CONTRACT = "user->contract"
    CONTRACT_TO_CONTRACT = "contract->contract"
    EXTERNAL_TO_INTERNAL = "external->internal"
    ADMIN_TO_USER = "admin->user"
    UNKNOWN = "unknown"


class ValueMovement(str, Enum):
    """Direction of value movement."""

    IN = "in"
    OUT = "out"
    INTERNAL = "internal"
    BIDIRECTIONAL = "bidirectional"
    UNKNOWN = "unknown"


class GuardType(str, Enum):
    """Types of guards/mitigations."""

    REENTRANCY_GUARD = "reentrancy_guard"
    ACCESS_CONTROL = "access_control"
    PAUSABLE = "pausable"
    TIMELOCK = "timelock"
    ORACLE_CHECK = "oracle_check"
    SLIPPAGE_CHECK = "slippage_check"
    BALANCE_CHECK = "balance_check"
    CUSTOM = "custom"


class PCPDeterminism(BaseModel):
    """Determinism constraints for PCP v2.

    Ensures no RAG, no name heuristics, and stable serialization.
    """

    no_rag: bool = Field(
        default=True,
        description="No retrieval-augmented generation allowed",
    )
    no_name_heuristics: bool = Field(
        default=True,
        description="No function/variable name heuristics allowed",
    )
    serialization_order: list[str] = Field(
        default_factory=lambda: ["pcp", "slice", "protocol", "evidence"],
        description="Canonical serialization order for deterministic hashing",
    )
    hash_seed: str = Field(
        default="graph_hash + pcp_version + pattern_id",
        description="Hash seed formula for cache keying",
    )


class PCPBudget(BaseModel):
    """Token budget constraints for PCP v2.

    Controls token allocation across cheap/verify/deep passes.
    """

    pcp_max_tokens: int = Field(
        default=800,
        ge=100,
        le=2000,
        description="Maximum tokens for PCP itself",
    )
    context_max_tokens: int = Field(
        default=2200,
        ge=500,
        le=6000,
        description="Maximum tokens for full context (PCP + slice + protocol)",
    )
    cheap_pass_tokens: int = Field(
        default=1200,
        ge=500,
        le=3000,
        description="Token budget for cheap/fast pass",
    )
    verify_pass_tokens: int = Field(
        default=1800,
        ge=1000,
        le=4000,
        description="Token budget for verification pass",
    )
    deep_pass_tokens: int = Field(
        default=2400,
        ge=1500,
        le=6000,
        description="Token budget for deep analysis pass",
    )

    @model_validator(mode="after")
    def validate_budget_ordering(self) -> "PCPBudget":
        """Ensure budget ordering: cheap < verify < deep."""
        if self.cheap_pass_tokens >= self.verify_pass_tokens:
            raise ValueError(
                f"cheap_pass_tokens ({self.cheap_pass_tokens}) must be < "
                f"verify_pass_tokens ({self.verify_pass_tokens})"
            )
        if self.verify_pass_tokens >= self.deep_pass_tokens:
            raise ValueError(
                f"verify_pass_tokens ({self.verify_pass_tokens}) must be < "
                f"deep_pass_tokens ({self.deep_pass_tokens})"
            )
        return self


class PCPEvidenceWeights(BaseModel):
    """Evidence weight categorization for prioritized analysis.

    Categorizes evidence refs by importance for multi-pass detection.
    """

    required: list[str] = Field(
        default_factory=list,
        description="Evidence refs that MUST exist for a match",
    )
    strong: list[str] = Field(
        default_factory=list,
        description="Evidence refs that strongly support a match",
    )
    weak: list[str] = Field(
        default_factory=list,
        description="Evidence refs that weakly support a match",
    )
    optional: list[str] = Field(
        default_factory=list,
        description="Evidence refs that are nice-to-have",
    )


class PCPWitness(BaseModel):
    """Witness requirements for pattern matching.

    Defines minimal proof subgraph (required) and negative witness (must-not-exist).
    """

    minimal_required: list[str] = Field(
        default_factory=list,
        description="Minimal evidence set that must exist for a plausible match",
    )
    negative_required: list[str] = Field(
        default_factory=list,
        description="Evidence that must NOT exist for a match to hold",
    )


class PCPPrecondition(BaseModel):
    """Precondition for pattern applicability."""

    id: str = Field(..., description="Unique precondition identifier")
    description: str = Field(..., description="Human-readable precondition description")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting this precondition",
    )


class PCPExploitStep(BaseModel):
    """A step in the exploit sequence."""

    id: str = Field(..., description="Unique step identifier")
    description: str = Field(..., description="Human-readable step description")
    required_ops: list[str] = Field(
        default_factory=list,
        description="Semantic operations required for this step",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting this step",
    )


class PCPImpactInvariant(BaseModel):
    """An impact invariant describing the vulnerability's effect."""

    id: str = Field(..., description="Unique invariant identifier")
    description: str = Field(..., description="Human-readable impact description")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting this invariant",
    )


class PCPOrderingVariant(BaseModel):
    """A valid operation ordering sequence."""

    id: str = Field(..., description="Unique ordering variant identifier")
    description: str = Field(default="", description="Human-readable description")
    sequence: list[str] = Field(
        ...,
        min_length=1,
        description="Ordered list of semantic operations",
    )


class PCPOpSignatures(BaseModel):
    """Operation signatures and ordering constraints."""

    required_ops: list[str] = Field(
        ...,
        min_length=1,
        description="Semantic operations required for this pattern",
    )
    ordering_variants: list[PCPOrderingVariant] = Field(
        default_factory=list,
        description="Valid operation orderings (multiple variants allowed)",
    )
    forbidden_ops: list[str] = Field(
        default_factory=list,
        description="Semantic operations that must NOT be present",
    )


class PCPAntiSignal(BaseModel):
    """A guard/mitigation that negates the pattern.

    Anti-signals indicate that a pattern does NOT apply due to
    some guard or mitigation being present.
    """

    id: str = Field(..., description="Unique anti-signal identifier")
    guard_type: GuardType = Field(
        ...,
        description="Type of guard/mitigation",
    )
    severity: str = Field(
        default="medium",
        description="How severely this anti-signal negates the pattern",
    )
    expected_context: str = Field(
        default="",
        description="Expected context when this anti-signal is present",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references for this anti-signal",
    )
    bypass_notes: list[str] = Field(
        default_factory=list,
        description="Notes on how this guard might be bypassed",
    )


class PCPCounterfactual(BaseModel):
    """A what-if scenario for Tier-B exploration.

    Counterfactuals model "what if X were removed/changed" scenarios.
    """

    id: str = Field(..., description="Unique counterfactual identifier")
    if_removed: str = Field(
        ...,
        description="ID of anti-signal/guard to hypothetically remove",
    )
    becomes_true: bool = Field(
        default=True,
        description="Whether the pattern would hold if guard removed",
    )
    notes: str = Field(
        default="",
        description="Additional notes about this counterfactual",
    )


class PCPGuardTaxonomyEntry(BaseModel):
    """An entry in the guard taxonomy.

    Describes a specific guard type and its expected behavior.
    """

    id: str = Field(..., description="Unique guard taxonomy entry identifier")
    type: GuardType = Field(..., description="Guard type classification")
    description: str = Field(..., description="Human-readable guard description")
    expected_ops: list[str] = Field(
        default_factory=list,
        description="Semantic operations expected when this guard is present",
    )
    bypass_notes: list[str] = Field(
        default_factory=list,
        description="Notes on potential bypass vectors",
    )


class PCPRiskEnvelope(BaseModel):
    """Risk envelope for semantic risk framing.

    Describes the asset type, trust boundary, and value flow characteristics.
    """

    asset_type: AssetType = Field(
        default=AssetType.UNKNOWN,
        description="Type of asset at risk",
    )
    trust_boundary: TrustBoundary = Field(
        default=TrustBoundary.UNKNOWN,
        description="Trust boundary being crossed",
    )
    value_movement: ValueMovement = Field(
        default=ValueMovement.UNKNOWN,
        description="Direction of value movement",
    )
    severity_floor: str = Field(
        default="medium",
        description="Minimum severity for this pattern",
    )


class PCPCompositionHints(BaseModel):
    """Hints for pattern composition and chaining.

    Describes how this pattern relates to other patterns.
    """

    co_occurs_with: list[str] = Field(
        default_factory=list,
        description="Pattern IDs that frequently co-occur with this pattern",
    )
    combine_with: list[str] = Field(
        default_factory=list,
        description="Pattern IDs to combine for compound detection",
    )


class PCPEconomicPlaceholders(BaseModel):
    """Placeholders for Phase 5.11 economic context overlay.

    These fields are reserved for future economic reasoning integration.
    """

    value_flows: list[str] = Field(
        default_factory=list,
        description="Value flow descriptors (populated in Phase 5.11)",
    )
    incentive_hooks: list[str] = Field(
        default_factory=list,
        description="Incentive mechanism hooks (populated in Phase 5.11)",
    )
    role_assumptions: list[str] = Field(
        default_factory=list,
        description="Role/actor assumptions (populated in Phase 5.11)",
    )
    offchain_dependencies: list[str] = Field(
        default_factory=list,
        description="Off-chain dependency flags (populated in Phase 5.11)",
    )
    risk_pre_score: RiskPreScore = Field(
        default=RiskPreScore.UNKNOWN,
        description="Pre-computed risk score placeholder",
    )


class PCPEvidenceRequirements(BaseModel):
    """Evidence requirements for graph-based matching.

    Specifies what types of nodes, edges, and paths are needed.
    """

    node_types: list[str] = Field(
        default_factory=list,
        description="Required node types in evidence subgraph",
    )
    edge_types: list[str] = Field(
        default_factory=list,
        description="Required edge types in evidence subgraph",
    )
    path_constraints: list[str] = Field(
        default_factory=list,
        description="Path constraint expressions",
    )


class PCPUnknownsPolicy(BaseModel):
    """Explicit policy for handling missing evidence/signals.

    Never infer safety from missing context - missing = unknown.
    """

    missing_required: UnknownsPolicy = Field(
        default=UnknownsPolicy.UNKNOWN,
        description="How to treat missing required evidence",
    )
    missing_optional: UnknownsPolicy = Field(
        default=UnknownsPolicy.UNKNOWN,
        description="How to treat missing optional evidence",
    )
    missing_anti_signal: UnknownsPolicy = Field(
        default=UnknownsPolicy.UNKNOWN,
        description="How to treat missing anti-signals",
    )


class PatternContextPackV2(BaseModel):
    """Pattern Context Pack v2 Schema.

    Deterministic, evidence-first context pack for agentic pattern discovery.
    PCP v2 is cacheable, schema-validated, and graph-first.

    Key invariants:
    - Deterministic serialization and hashing
    - No name heuristics, no external retrieval, no free-form sources
    - Evidence is explicit and stable (canonical IDs)
    - Missing signals are marked "unknown", not safe

    This schema supports:
    - Anti-signals and witnesses (minimal + negative)
    - Evidence weights for prioritized analysis
    - Guard taxonomy with bypass notes
    - Ordering variants and required op signatures
    - Risk envelope (asset type, trust boundary, value flow)
    - Economic placeholders for Phase 5.11 integration
    """

    # Identity
    id: str = Field(..., description="Unique PCP identifier (pcp-<pattern_id>)")
    version: str = Field(
        default="2.0",
        pattern=r"^2\.\d+$",
        description="PCP schema version (must be 2.x)",
    )
    pattern_id: str = Field(..., description="Associated pattern ID")
    name: str = Field(..., description="Human-readable pattern name")
    summary: str = Field(..., description="Brief pattern summary")
    scope: str = Field(
        default="Function",
        description="Pattern scope (Function, Contract, Transaction)",
    )

    # Determinism constraints
    determinism: PCPDeterminism = Field(
        default_factory=PCPDeterminism,
        description="Determinism constraints",
    )

    # Token budget
    budget: PCPBudget = Field(
        default_factory=PCPBudget,
        description="Token budget constraints",
    )

    # Evidence and witness
    evidence_weights: PCPEvidenceWeights = Field(
        default_factory=PCPEvidenceWeights,
        description="Evidence weight categorization",
    )
    witness: PCPWitness = Field(
        default_factory=PCPWitness,
        description="Witness requirements",
    )

    # Exploit modeling
    preconditions: list[PCPPrecondition] = Field(
        default_factory=list,
        description="Preconditions for pattern applicability",
    )
    exploit_steps: list[PCPExploitStep] = Field(
        default_factory=list,
        description="Steps in the exploit sequence",
    )
    impact_invariants: list[PCPImpactInvariant] = Field(
        default_factory=list,
        description="Impact invariants describing the vulnerability's effect",
    )

    # Operation signatures
    op_signatures: PCPOpSignatures = Field(
        ...,
        description="Operation signatures and ordering constraints",
    )

    # Anti-signals and counterfactuals
    anti_signals: list[PCPAntiSignal] = Field(
        default_factory=list,
        description="Guards/mitigations that negate the pattern",
    )
    counterfactuals: list[PCPCounterfactual] = Field(
        default_factory=list,
        description="What-if scenarios for Tier-B exploration",
    )

    # Guard taxonomy
    guard_taxonomy: list[PCPGuardTaxonomyEntry] = Field(
        default_factory=list,
        description="Guard taxonomy entries",
    )

    # Ordering variants (duplicate of op_signatures.ordering_variants for convenience)
    ordering_variants: list[PCPOrderingVariant] = Field(
        default_factory=list,
        description="Valid operation orderings",
    )

    # Risk envelope
    risk_envelope: PCPRiskEnvelope = Field(
        default_factory=PCPRiskEnvelope,
        description="Risk envelope for semantic risk framing",
    )

    # Composition hints
    composition_hints: PCPCompositionHints = Field(
        default_factory=PCPCompositionHints,
        description="Hints for pattern composition and chaining",
    )

    # Economic placeholders (Phase 5.11)
    economic_placeholders: PCPEconomicPlaceholders = Field(
        default_factory=PCPEconomicPlaceholders,
        description="Placeholders for Phase 5.11 economic context",
    )

    # Evidence requirements
    evidence_requirements: PCPEvidenceRequirements = Field(
        default_factory=PCPEvidenceRequirements,
        description="Evidence requirements for graph-based matching",
    )

    # Unknowns policy
    unknowns_policy: PCPUnknownsPolicy = Field(
        default_factory=PCPUnknownsPolicy,
        description="Policy for handling missing evidence/signals",
    )

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        """Validate scope is a valid value."""
        valid_scopes = ["Function", "Contract", "Transaction"]
        if v not in valid_scopes:
            raise ValueError(f"Invalid scope: {v}. Must be one of: {', '.join(valid_scopes)}")
        return v

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate ID follows pcp-<pattern_id> format."""
        if not v.startswith("pcp-"):
            raise ValueError(f"PCP ID must start with 'pcp-': {v}")
        return v

    @model_validator(mode="after")
    def validate_high_severity_anti_signals(self) -> "PatternContextPackV2":
        """Warn if high/critical severity pattern lacks anti-signals or negative witnesses.

        Note: This is a soft validation - it doesn't raise an error, but logs a warning.
        """
        # We could add logging here for soft warnings
        # For now, we just validate structure
        return self

    def to_yaml(self) -> str:
        """Serialize to YAML with canonical field ordering."""
        import yaml

        data = self.model_dump(mode="json")
        return yaml.dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)

    def compute_cache_key(self, graph_hash: str) -> str:
        """Compute cache key for this PCP.

        Args:
            graph_hash: Hash of the source graph

        Returns:
            str: Cache key combining graph_hash, version, and pattern_id
        """
        import hashlib

        key_material = f"{graph_hash}:{self.version}:{self.pattern_id}"
        return hashlib.sha256(key_material.encode()).hexdigest()[:16]


# =============================================================================
# PCP v1 to v2 Migration Shim
# =============================================================================


def migrate_pcp_v1_to_v2(v1_data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate PCP v1 data to v2 format with explicit defaults.

    Migration rules:
    - Populate missing sections with empty lists and unknowns_policy.* = "unknown"
    - Normalize ordering to the canonical serialization order
    - Convert v1 guard fields into anti_signals + guard_taxonomy entries
    - Map v1 operation ordering constraints into ordering_variants
    - Preserve v1 evidence refs and convert to canonical evidence ID format

    Args:
        v1_data: PCP v1 data dictionary

    Returns:
        dict: PCP v2 compatible data dictionary
    """
    v2_data: Dict[str, Any] = {}

    # Identity fields - preserve and normalize
    pattern_id = v1_data.get("pattern_id", v1_data.get("id", "unknown"))
    v2_data["id"] = f"pcp-{pattern_id}" if not str(v1_data.get("id", "")).startswith("pcp-") else v1_data.get("id", f"pcp-{pattern_id}")
    v2_data["version"] = "2.0"  # Upgrade version
    v2_data["pattern_id"] = pattern_id
    v2_data["name"] = v1_data.get("name", "Unknown Pattern")
    v2_data["summary"] = v1_data.get("summary", v1_data.get("description", ""))
    v2_data["scope"] = v1_data.get("scope", "Function")

    # Determinism - set explicit defaults
    v2_data["determinism"] = {
        "no_rag": True,
        "no_name_heuristics": True,
        "serialization_order": ["pcp", "slice", "protocol", "evidence"],
        "hash_seed": "graph_hash + pcp_version + pattern_id",
    }

    # Budget - preserve if present, otherwise use defaults
    if "budget" in v1_data:
        v2_data["budget"] = v1_data["budget"]
    else:
        v2_data["budget"] = {
            "pcp_max_tokens": 800,
            "context_max_tokens": 2200,
            "cheap_pass_tokens": 1200,
            "verify_pass_tokens": 1800,
            "deep_pass_tokens": 2400,
        }

    # Evidence weights - migrate or default
    if "evidence_weights" in v1_data:
        v2_data["evidence_weights"] = v1_data["evidence_weights"]
    else:
        v2_data["evidence_weights"] = {
            "required": [],
            "strong": [],
            "weak": [],
            "optional": [],
        }

    # Witness - migrate or default
    if "witness" in v1_data:
        v2_data["witness"] = v1_data["witness"]
    elif "minimal_witness" in v1_data or "negative_witness" in v1_data:
        # v1 might have these as top-level fields
        v2_data["witness"] = {
            "minimal_required": v1_data.get("minimal_witness", []),
            "negative_required": v1_data.get("negative_witness", []),
        }
    else:
        v2_data["witness"] = {
            "minimal_required": [],
            "negative_required": [],
        }

    # Preconditions, exploit_steps, impact_invariants - preserve or default
    v2_data["preconditions"] = v1_data.get("preconditions", [])
    v2_data["exploit_steps"] = v1_data.get("exploit_steps", [])
    v2_data["impact_invariants"] = v1_data.get("impact_invariants", [])

    # Op signatures - migrate required_ops and ordering
    required_ops = v1_data.get("required_ops", v1_data.get("op_signatures", {}).get("required_ops", []))
    if not required_ops:
        # Try to extract from other v1 fields
        required_ops = v1_data.get("semantic_operations", [])
    if not required_ops:
        required_ops = ["UNKNOWN"]  # Placeholder for invalid v1 data

    ordering_variants = []
    if "ordering_variants" in v1_data:
        ordering_variants = v1_data["ordering_variants"]
    elif "operation_sequence" in v1_data:
        # v1 might have single sequence
        ordering_variants = [{
            "id": "seq-001",
            "description": "Migrated from v1",
            "sequence": v1_data["operation_sequence"],
        }]
    elif "op_signatures" in v1_data and "ordering_variants" in v1_data["op_signatures"]:
        ordering_variants = v1_data["op_signatures"]["ordering_variants"]

    v2_data["op_signatures"] = {
        "required_ops": required_ops,
        "ordering_variants": ordering_variants,
        "forbidden_ops": v1_data.get("forbidden_ops", v1_data.get("op_signatures", {}).get("forbidden_ops", [])),
    }

    # Anti-signals - migrate from v1 guards
    anti_signals = []
    if "anti_signals" in v1_data:
        anti_signals = v1_data["anti_signals"]
    elif "guards" in v1_data:
        # Convert v1 guards to anti_signals
        for i, guard in enumerate(v1_data["guards"]):
            if isinstance(guard, str):
                anti_signals.append({
                    "id": f"guard.{i}",
                    "guard_type": "custom",
                    "severity": "medium",
                    "expected_context": guard,
                    "evidence_refs": [],
                    "bypass_notes": [],
                })
            elif isinstance(guard, dict):
                anti_signals.append({
                    "id": guard.get("id", f"guard.{i}"),
                    "guard_type": guard.get("type", "custom"),
                    "severity": guard.get("severity", "medium"),
                    "expected_context": guard.get("description", guard.get("context", "")),
                    "evidence_refs": guard.get("evidence_refs", []),
                    "bypass_notes": guard.get("bypass_notes", []),
                })
    v2_data["anti_signals"] = anti_signals

    # Counterfactuals - preserve or default
    v2_data["counterfactuals"] = v1_data.get("counterfactuals", [])

    # Guard taxonomy - migrate or default
    guard_taxonomy = []
    if "guard_taxonomy" in v1_data:
        guard_taxonomy = v1_data["guard_taxonomy"]
    elif anti_signals:
        # Auto-generate from anti_signals
        seen_types: Set[str] = set()
        for anti_sig in anti_signals:
            guard_type = anti_sig.get("guard_type", "custom")
            if guard_type not in seen_types:
                seen_types.add(guard_type)
                guard_taxonomy.append({
                    "id": f"g-{len(guard_taxonomy) + 1}",
                    "type": guard_type,
                    "description": f"Guard type: {guard_type}",
                    "expected_ops": [],
                    "bypass_notes": [],
                })
    v2_data["guard_taxonomy"] = guard_taxonomy

    # Top-level ordering_variants (convenience duplicate)
    v2_data["ordering_variants"] = ordering_variants

    # Risk envelope - migrate or default
    if "risk_envelope" in v1_data:
        v2_data["risk_envelope"] = v1_data["risk_envelope"]
    else:
        v2_data["risk_envelope"] = {
            "asset_type": "unknown",
            "trust_boundary": "unknown",
            "value_movement": "unknown",
            "severity_floor": v1_data.get("severity", "medium"),
        }

    # Composition hints - preserve or default
    v2_data["composition_hints"] = v1_data.get("composition_hints", {
        "co_occurs_with": [],
        "combine_with": [],
    })

    # Economic placeholders - always default (Phase 5.11)
    v2_data["economic_placeholders"] = {
        "value_flows": [],
        "incentive_hooks": [],
        "role_assumptions": [],
        "offchain_dependencies": [],
        "risk_pre_score": "unknown",
    }

    # Evidence requirements - migrate or default
    if "evidence_requirements" in v1_data:
        v2_data["evidence_requirements"] = v1_data["evidence_requirements"]
    else:
        v2_data["evidence_requirements"] = {
            "node_types": [],
            "edge_types": [],
            "path_constraints": [],
        }

    # Unknowns policy - CRITICAL: explicit unknown handling
    v2_data["unknowns_policy"] = {
        "missing_required": "unknown",
        "missing_optional": "unknown",
        "missing_anti_signal": "unknown",
    }

    return v2_data


def load_pcp_v2(path: Path, allow_v1_migration: bool = True) -> PatternContextPackV2:
    """Load and validate a PCP from a YAML file.

    Supports automatic migration from v1 format if allow_v1_migration is True.

    Args:
        path: Path to PCP YAML file
        allow_v1_migration: Whether to allow automatic v1 to v2 migration

    Returns:
        PatternContextPackV2: Validated PCP v2 data

    Raises:
        ValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
        ValueError: If v1 data provided and allow_v1_migration is False
    """
    import yaml

    if not path.exists():
        raise FileNotFoundError(f"PCP file not found: {path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"PCP file is empty: {path}")

    # Check version
    version = str(data.get("version", "1.0"))

    if version.startswith("2."):
        # Already v2, validate directly
        return PatternContextPackV2.model_validate(data)
    elif version.startswith("1.") or not version.startswith("2."):
        # v1 format, needs migration
        if not allow_v1_migration:
            raise ValueError(
                f"PCP file is v1 format and allow_v1_migration is False: {path}"
            )
        v2_data = migrate_pcp_v1_to_v2(data)
        return PatternContextPackV2.model_validate(v2_data)
    else:
        raise ValueError(f"Unknown PCP version: {version}")


def generate_pcp_v2_json_schema() -> Dict[str, Any]:
    """Generate JSON Schema for PCP v2.

    Returns a complete JSON Schema suitable for external validation tools.

    Returns:
        dict: JSON Schema for PatternContextPackV2
    """
    return PatternContextPackV2.model_json_schema()


def export_pcp_v2_json_schema(output_path: Path) -> None:
    """Export PCP v2 JSON Schema to a file.

    Args:
        output_path: Path to write the JSON Schema file
    """
    import json

    schema = generate_pcp_v2_json_schema()

    # Add schema metadata
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://alphaswarm.sol/schemas/pattern_context_pack_v2.json"
    schema["title"] = "Pattern Context Pack v2"
    schema["description"] = (
        "Deterministic, evidence-first context pack for agentic pattern discovery. "
        "PCP v2 is cacheable, schema-validated, and graph-first."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)


# Update generate_json_schema to include PCP v2
def generate_json_schema_all() -> Dict[str, Any]:
    """Generate JSON Schema from all pydantic models including PCP v2.

    Returns a dictionary containing JSON Schemas for all models,
    suitable for external validation tools.

    Returns:
        dict: JSON Schema definitions for all models
    """
    return {
        "VulnDocIndex": VulnDocIndex.model_json_schema(),
        "PatternRef": PatternRef.model_json_schema(),
        "TestCoverage": TestCoverage.model_json_schema(),
        "VulnDocCategory": VulnDocCategory.model_json_schema(),
        "PatternContextPackV2": PatternContextPackV2.model_json_schema(),
    }
