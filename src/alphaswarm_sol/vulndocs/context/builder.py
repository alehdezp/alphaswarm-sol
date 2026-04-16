"""Context Builder for dynamic LLM context assembly.

Builds structured context from vulnerability knowledge documents
optimized for LLM consumption with token budget management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc
from alphaswarm_sol.vulndocs.storage.retrieval import (
    KnowledgeRetriever,
    RetrievalDepth,
    RetrievalResult,
)
from alphaswarm_sol.vulndocs.tools.formatters import (
    OutputFormat,
    FormatterConfig,
    format_output,
    estimate_tokens,
)


class ContextMode(Enum):
    """Context assembly modes for different use cases."""

    # Finding analysis - focused on single vulnerability
    FINDING_ANALYSIS = auto()

    # Investigation mode - multiple related vulnerabilities
    INVESTIGATION = auto()

    # Navigation - overview for exploration
    NAVIGATION = auto()

    # Verification - testing and proving findings
    VERIFICATION = auto()

    # Remediation - fixing vulnerabilities
    REMEDIATION = auto()

    # Minimal - just enough to understand
    MINIMAL = auto()


class ContextPriority(Enum):
    """Priority levels for context sections."""

    CRITICAL = 1  # Must include
    HIGH = 2  # Include if budget allows
    MEDIUM = 3  # Include if space
    LOW = 4  # Nice to have


@dataclass
class ContextSection:
    """A section of context with priority and token estimate.

    Sections are ordered by priority and assembled within budget.
    """

    name: str
    content: str
    priority: ContextPriority
    token_estimate: int = 0
    cacheable: bool = False  # Can be cached in prompt caching
    source: str = ""  # Where this content came from

    def __post_init__(self):
        if not self.token_estimate and self.content:
            self.token_estimate = estimate_tokens(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "content": self.content,
            "priority": self.priority.name,
            "token_estimate": self.token_estimate,
            "cacheable": self.cacheable,
            "source": self.source,
        }


@dataclass
class ContextConfig:
    """Configuration for context building."""

    # Token budgets
    max_total_tokens: int = 4000
    max_per_section: int = 1000
    min_tokens_for_content: int = 100

    # Output format
    output_format: OutputFormat = OutputFormat.TOON
    include_metadata: bool = False
    include_sources: bool = True

    # Mode-specific settings
    mode: ContextMode = ContextMode.FINDING_ANALYSIS

    # Progressive loading
    enable_progressive: bool = True
    initial_depth: RetrievalDepth = RetrievalDepth.MINIMAL


@dataclass
class BuiltContext:
    """Result of context building."""

    # Assembled context string
    content: str

    # Breakdown by section
    sections: List[ContextSection] = field(default_factory=list)

    # Token accounting
    total_tokens: int = 0
    budget_used: float = 0.0  # Percentage of budget used

    # Metadata
    mode: ContextMode = ContextMode.FINDING_ANALYSIS
    truncated: bool = False
    excluded_sections: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.total_tokens and self.content:
            self.total_tokens = estimate_tokens(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "content": self.content,
            "sections": [s.to_dict() for s in self.sections],
            "total_tokens": self.total_tokens,
            "budget_used": self.budget_used,
            "mode": self.mode.name,
            "truncated": self.truncated,
            "excluded_sections": self.excluded_sections,
        }

    def get_cacheable_prefix(self) -> str:
        """Get cacheable portion for Anthropic prompt caching."""
        cacheable_parts = []
        for section in self.sections:
            if section.cacheable:
                cacheable_parts.append(section.content)
        return "\n\n".join(cacheable_parts)

    def get_dynamic_suffix(self) -> str:
        """Get dynamic portion (not cacheable)."""
        dynamic_parts = []
        for section in self.sections:
            if not section.cacheable:
                dynamic_parts.append(section.content)
        return "\n\n".join(dynamic_parts)


class ContextBuilder:
    """Builds dynamic context for LLM consumption.

    Example:
        builder = ContextBuilder()

        # Build context for a finding
        context = builder.build_for_finding({
            "category": "reentrancy",
            "subcategory": "classic",
            "signals": ["state_write_after_external_call"]
        })

        # Build investigation context
        context = builder.build_investigation(
            categories=["reentrancy", "access-control"],
            max_tokens=6000
        )

        # Build with specific mode
        context = builder.build(
            mode=ContextMode.VERIFICATION,
            finding=finding,
            include_tests=True
        )
    """

    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
        config: Optional[ContextConfig] = None,
    ):
        """Initialize context builder.

        Args:
            retriever: Knowledge retriever (creates default if not provided)
            config: Context configuration
        """
        self.retriever = retriever or KnowledgeRetriever()
        self.config = config or ContextConfig()

    def build_for_finding(
        self,
        finding: Dict[str, Any],
        max_tokens: Optional[int] = None,
        mode: Optional[ContextMode] = None,
    ) -> BuiltContext:
        """Build context tailored for a specific finding.

        Args:
            finding: Finding dictionary with category, signals, etc.
            max_tokens: Optional token limit override
            mode: Optional mode override

        Returns:
            BuiltContext with assembled content
        """
        max_tokens = max_tokens or self.config.max_total_tokens
        mode = mode or self.config.mode

        sections: List[ContextSection] = []

        # Extract finding info
        category = finding.get("category", "")
        subcategory = finding.get("subcategory")
        signals = finding.get("signals", [])
        pattern_ids = finding.get("pattern_ids", finding.get("pattern_id", []))
        if isinstance(pattern_ids, str):
            pattern_ids = [pattern_ids]

        # Section 1: Detection context (CRITICAL)
        detection_section = self._build_detection_section(
            category, subcategory, signals, pattern_ids
        )
        if detection_section:
            sections.append(detection_section)

        # Section 2: Business impact (HIGH)
        if mode != ContextMode.MINIMAL:
            business_section = self._build_business_section(category, subcategory)
            if business_section:
                sections.append(business_section)

        # Section 3: Mitigation (HIGH for REMEDIATION mode)
        if mode in (ContextMode.REMEDIATION, ContextMode.FINDING_ANALYSIS):
            mitigation_section = self._build_mitigation_section(category, subcategory)
            if mitigation_section:
                sections.append(mitigation_section)

        # Section 4: Testing guidance (HIGH for VERIFICATION mode)
        if mode == ContextMode.VERIFICATION:
            testing_section = self._build_testing_section(category, subcategory)
            if testing_section:
                sections.append(testing_section)

        # Section 5: Real exploits (MEDIUM)
        if mode not in (ContextMode.MINIMAL, ContextMode.NAVIGATION):
            exploits_section = self._build_exploits_section(category, subcategory)
            if exploits_section:
                sections.append(exploits_section)

        return self._assemble_sections(sections, max_tokens, mode)

    def build_investigation(
        self,
        categories: List[str],
        max_tokens: Optional[int] = None,
        depth: RetrievalDepth = RetrievalDepth.STANDARD,
    ) -> BuiltContext:
        """Build context for multi-category investigation.

        Args:
            categories: Categories to include
            max_tokens: Optional token limit
            depth: How much detail per category

        Returns:
            BuiltContext with investigation context
        """
        max_tokens = max_tokens or self.config.max_total_tokens
        tokens_per_category = max(500, max_tokens // len(categories))

        sections: List[ContextSection] = []

        # Add navigation header (cacheable)
        nav_section = ContextSection(
            name="navigation",
            content=self._build_nav_header(categories),
            priority=ContextPriority.CRITICAL,
            cacheable=True,
            source="index",
        )
        sections.append(nav_section)

        # Add context for each category
        for i, category in enumerate(categories):
            priority = (
                ContextPriority.CRITICAL if i == 0 else ContextPriority.HIGH
            )

            result = self.retriever.get_by_category(
                category=category,
                depth=depth,
                max_results=3,
            )

            if result.documents:
                content = format_output(
                    result.documents,
                    self.config.output_format,
                    FormatterConfig(max_tokens=tokens_per_category),
                )

                sections.append(
                    ContextSection(
                        name=f"category_{category}",
                        content=content,
                        priority=priority,
                        source=category,
                    )
                )

        return self._assemble_sections(sections, max_tokens, ContextMode.INVESTIGATION)

    def build_navigation(
        self,
        max_tokens: Optional[int] = None,
    ) -> BuiltContext:
        """Build navigation context for exploration.

        Args:
            max_tokens: Optional token limit

        Returns:
            BuiltContext with navigation context
        """
        max_tokens = max_tokens or min(2000, self.config.max_total_tokens)

        sections: List[ContextSection] = []

        # Navigation index (cacheable - stable content)
        nav_content = self.retriever.get_navigation_context(max_tokens=max_tokens - 200)
        sections.append(
            ContextSection(
                name="navigation_index",
                content=nav_content,
                priority=ContextPriority.CRITICAL,
                cacheable=True,
                source="index",
            )
        )

        # Tool usage guide (cacheable)
        tool_guide = self._build_tool_guide()
        sections.append(
            ContextSection(
                name="tool_guide",
                content=tool_guide,
                priority=ContextPriority.HIGH,
                cacheable=True,
                source="system",
            )
        )

        return self._assemble_sections(sections, max_tokens, ContextMode.NAVIGATION)

    def build_verification(
        self,
        finding: Dict[str, Any],
        max_tokens: Optional[int] = None,
    ) -> BuiltContext:
        """Build context for finding verification.

        Args:
            finding: Finding to verify
            max_tokens: Optional token limit

        Returns:
            BuiltContext for verification
        """
        return self.build_for_finding(
            finding=finding,
            max_tokens=max_tokens,
            mode=ContextMode.VERIFICATION,
        )

    def build_remediation(
        self,
        finding: Dict[str, Any],
        max_tokens: Optional[int] = None,
    ) -> BuiltContext:
        """Build context for remediation guidance.

        Args:
            finding: Finding to remediate
            max_tokens: Optional token limit

        Returns:
            BuiltContext for remediation
        """
        return self.build_for_finding(
            finding=finding,
            max_tokens=max_tokens,
            mode=ContextMode.REMEDIATION,
        )

    def build_minimal(
        self,
        finding: Dict[str, Any],
        max_tokens: int = 500,
    ) -> BuiltContext:
        """Build minimal context (just enough to understand).

        Args:
            finding: Finding dict
            max_tokens: Token limit (default 500)

        Returns:
            Minimal BuiltContext
        """
        return self.build_for_finding(
            finding=finding,
            max_tokens=max_tokens,
            mode=ContextMode.MINIMAL,
        )

    def expand_context(
        self,
        current: BuiltContext,
        finding: Dict[str, Any],
        expand_sections: List[str],
        additional_tokens: int = 1000,
    ) -> BuiltContext:
        """Expand existing context with more detail.

        Args:
            current: Current context to expand
            finding: Finding for additional context
            expand_sections: Which sections to expand
            additional_tokens: Additional token budget

        Returns:
            Expanded BuiltContext
        """
        new_max = current.total_tokens + additional_tokens
        sections = list(current.sections)

        category = finding.get("category", "")
        subcategory = finding.get("subcategory")

        for section_name in expand_sections:
            new_section = None

            if section_name == "exploits":
                new_section = self._build_exploits_section(
                    category, subcategory, detailed=True
                )
            elif section_name == "testing":
                new_section = self._build_testing_section(category, subcategory)
            elif section_name == "mitigation":
                new_section = self._build_mitigation_section(
                    category, subcategory, detailed=True
                )
            elif section_name == "patterns":
                new_section = self._build_patterns_section(category, subcategory)

            if new_section:
                # Remove existing section with same name
                sections = [s for s in sections if s.name != new_section.name]
                sections.append(new_section)

        return self._assemble_sections(sections, new_max, current.mode)

    # =========================================================================
    # Section Builders
    # =========================================================================

    def _build_detection_section(
        self,
        category: str,
        subcategory: Optional[str],
        signals: List[str],
        pattern_ids: List[str],
    ) -> Optional[ContextSection]:
        """Build detection guidance section."""
        parts = []

        # Try to get relevant knowledge
        if pattern_ids:
            result = self.retriever.get_by_pattern(
                pattern_ids=pattern_ids,
                depth=RetrievalDepth.MINIMAL,
            )
            if result.documents:
                for doc in result.documents[:2]:
                    parts.append(f"**{doc.name}**")
                    parts.append(f"> {doc.one_liner or doc.tldr or ''}")
                    if doc.detection.graph_signals:
                        parts.append(
                            f"Signals: {', '.join(doc.detection.graph_signals[:5])}"
                        )

        if category and not parts:
            result = self.retriever.get_by_category(
                category=category,
                subcategory=subcategory,
                depth=RetrievalDepth.MINIMAL,
                max_results=1,
            )
            if result.documents:
                doc = result.documents[0]
                parts.append(format_output(doc, self.config.output_format))

        # Add signal context if provided
        if signals and not parts:
            parts.append("**Observed Signals:**")
            for signal in signals[:5]:
                parts.append(f"- `{signal}`")

        if not parts:
            return None

        return ContextSection(
            name="detection",
            content="\n".join(parts),
            priority=ContextPriority.CRITICAL,
            cacheable=False,  # Finding-specific
            source=f"{category}/{subcategory}" if subcategory else category,
        )

    def _build_business_section(
        self,
        category: str,
        subcategory: Optional[str],
    ) -> Optional[ContextSection]:
        """Build business impact section."""
        result = self.retriever.get_by_category(
            category=category,
            subcategory=subcategory,
            depth=RetrievalDepth.STANDARD,
            max_results=1,
        )

        if not result.documents:
            return None

        doc = result.documents[0]
        parts = []

        # Use exploitation section for impact info (no business_context in schema)
        if doc.exploitation.potential_impact:
            parts.append(f"**Potential Impact:** {doc.exploitation.potential_impact}")
        if doc.exploitation.prerequisites:
            prereqs = ", ".join(doc.exploitation.prerequisites[:3])
            parts.append(f"**Prerequisites:** {prereqs}")

        if not parts:
            return None

        return ContextSection(
            name="business_impact",
            content="\n".join(parts),
            priority=ContextPriority.HIGH,
            cacheable=True,  # Category-level, stable
            source=category,
        )

    def _build_mitigation_section(
        self,
        category: str,
        subcategory: Optional[str],
        detailed: bool = False,
    ) -> Optional[ContextSection]:
        """Build mitigation guidance section."""
        result = self.retriever.get_by_category(
            category=category,
            subcategory=subcategory,
            depth=RetrievalDepth.FULL if detailed else RetrievalDepth.STANDARD,
            max_results=1,
        )

        if not result.documents:
            return None

        doc = result.documents[0]
        parts = []

        if doc.mitigation.primary_fix:
            parts.append(f"**Primary Fix:** {doc.mitigation.primary_fix}")
        if doc.mitigation.alternative_fixes:
            alts = ", ".join(doc.mitigation.alternative_fixes[:3])
            parts.append(f"**Alternatives:** {alts}")
        if detailed and doc.mitigation.how_to_verify:
            parts.append("**Verification Steps:**")
            for step in doc.mitigation.how_to_verify[:5]:
                parts.append(f"- {step}")
        if doc.mitigation.safe_pattern:
            parts.append(f"**Safe Pattern:** {doc.mitigation.safe_pattern}")

        if not parts:
            return None

        return ContextSection(
            name="mitigation",
            content="\n".join(parts),
            priority=(
                ContextPriority.CRITICAL
                if self.config.mode == ContextMode.REMEDIATION
                else ContextPriority.HIGH
            ),
            cacheable=True,
            source=category,
        )

    def _build_testing_section(
        self,
        category: str,
        subcategory: Optional[str],
    ) -> Optional[ContextSection]:
        """Build testing guidance section from exploitation info."""
        result = self.retriever.get_by_category(
            category=category,
            subcategory=subcategory,
            depth=RetrievalDepth.FULL,
            max_results=1,
        )

        if not result.documents:
            return None

        doc = result.documents[0]
        parts = []

        # Use exploitation section for testing guidance
        if doc.exploitation.attack_steps:
            parts.append("**Attack Steps to Test:**")
            for step in doc.exploitation.attack_steps[:5]:
                parts.append(f"- {step}")

        if doc.exploitation.prerequisites:
            parts.append("**Test Prerequisites:**")
            for prereq in doc.exploitation.prerequisites[:5]:
                parts.append(f"- {prereq}")

        # Use detection checklist for verification
        if doc.detection.checklist:
            parts.append("**Verification Checklist:**")
            for item in doc.detection.checklist[:5]:
                parts.append(f"- [ ] {item}")

        if not parts:
            return None

        return ContextSection(
            name="testing",
            content="\n".join(parts),
            priority=ContextPriority.HIGH,
            cacheable=True,
            source=category,
        )

    def _build_exploits_section(
        self,
        category: str,
        subcategory: Optional[str],
        detailed: bool = False,
    ) -> Optional[ContextSection]:
        """Build real exploits section."""
        result = self.retriever.get_by_category(
            category=category,
            subcategory=subcategory,
            depth=RetrievalDepth.FULL if detailed else RetrievalDepth.STANDARD,
            max_results=1,
        )

        if not result.documents:
            return None

        doc = result.documents[0]
        parts = []

        if doc.examples.real_exploits:
            parts.append("**Real-World Exploits:**")
            for exploit in doc.examples.real_exploits[:3]:
                line = f"- {exploit.name}"
                if exploit.loss:
                    line += f" ({exploit.loss})"
                if exploit.date:
                    line += f" - {exploit.date}"
                parts.append(line)
                if detailed and exploit.brief:
                    parts.append(f"  {exploit.brief[:200]}")

        if not parts:
            return None

        return ContextSection(
            name="exploits",
            content="\n".join(parts),
            priority=ContextPriority.MEDIUM,
            cacheable=True,
            source=category,
        )

    def _build_patterns_section(
        self,
        category: str,
        subcategory: Optional[str],
    ) -> Optional[ContextSection]:
        """Build code patterns section."""
        result = self.retriever.get_by_category(
            category=category,
            subcategory=subcategory,
            depth=RetrievalDepth.FULL,
            max_results=1,
        )

        if not result.documents:
            return None

        doc = result.documents[0]
        parts = []

        if doc.examples.vulnerable_code:
            parts.append("**Vulnerable Pattern:**")
            parts.append(f"```solidity\n{doc.examples.vulnerable_code[:500]}\n```")

        if doc.examples.fixed_code:
            parts.append("**Safe Pattern:**")
            parts.append(f"```solidity\n{doc.examples.fixed_code[:500]}\n```")

        if not parts:
            return None

        return ContextSection(
            name="patterns",
            content="\n".join(parts),
            priority=ContextPriority.MEDIUM,
            cacheable=True,
            source=category,
        )

    def _build_nav_header(self, categories: List[str]) -> str:
        """Build navigation header for investigation."""
        lines = [
            "# Vulnerability Investigation Context",
            "",
            f"**Categories:** {', '.join(categories)}",
            "",
            "Use `get_vulnerability_knowledge` tool for detailed information.",
            "",
        ]
        return "\n".join(lines)

    def _build_tool_guide(self) -> str:
        """Build tool usage guide."""
        return """## Available Tools

- `get_vulnerability_knowledge(category, subcategory?, depth?)` - Get detailed knowledge
- `search_vulnerability_knowledge(query, max_results?)` - Search by keywords
- `get_knowledge_for_finding(finding)` - Get context for a finding
- `list_vulnerability_categories()` - List all categories
- `get_pattern_knowledge(pattern_ids)` - Get knowledge for patterns"""

    # =========================================================================
    # Assembly
    # =========================================================================

    def _assemble_sections(
        self,
        sections: List[ContextSection],
        max_tokens: int,
        mode: ContextMode,
    ) -> BuiltContext:
        """Assemble sections within token budget.

        Args:
            sections: Sections to assemble
            max_tokens: Token budget
            mode: Context mode

        Returns:
            Assembled BuiltContext
        """
        # Sort by priority
        sorted_sections = sorted(sections, key=lambda s: s.priority.value)

        included: List[ContextSection] = []
        excluded: List[str] = []
        total_tokens = 0

        for section in sorted_sections:
            if total_tokens + section.token_estimate <= max_tokens:
                included.append(section)
                total_tokens += section.token_estimate
            else:
                excluded.append(section.name)

        # Build content
        parts = []
        for section in included:
            if section.content:
                parts.append(section.content)

        content = "\n\n---\n\n".join(parts) if parts else ""

        return BuiltContext(
            content=content,
            sections=included,
            total_tokens=total_tokens,
            budget_used=total_tokens / max_tokens if max_tokens > 0 else 0,
            mode=mode,
            truncated=bool(excluded),
            excluded_sections=excluded,
        )


# =============================================================================
# Convenience Functions
# =============================================================================

_default_builder: Optional[ContextBuilder] = None


def get_builder() -> ContextBuilder:
    """Get or create default context builder."""
    global _default_builder
    if _default_builder is None:
        _default_builder = ContextBuilder()
    return _default_builder


def set_builder(builder: ContextBuilder) -> None:
    """Set the default context builder."""
    global _default_builder
    _default_builder = builder


def build_context_for_finding(
    finding: Dict[str, Any],
    max_tokens: int = 4000,
    mode: ContextMode = ContextMode.FINDING_ANALYSIS,
) -> BuiltContext:
    """Build context for a finding using the default builder.

    Args:
        finding: Finding dictionary
        max_tokens: Token budget
        mode: Context mode

    Returns:
        BuiltContext
    """
    builder = get_builder()
    return builder.build_for_finding(finding, max_tokens, mode)


def build_navigation_context(max_tokens: int = 2000) -> BuiltContext:
    """Build navigation context using the default builder.

    Args:
        max_tokens: Token budget

    Returns:
        BuiltContext with navigation
    """
    builder = get_builder()
    return builder.build_navigation(max_tokens)
