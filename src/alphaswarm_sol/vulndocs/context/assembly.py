"""Context assembly strategies for VulnDocs.

Provides different strategies for assembling context from multiple sources:
- Priority-based assembly (most important first)
- Token-balanced assembly (distribute evenly)
- Progressive assembly (start minimal, expand)
- Hybrid assembly (combine strategies)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc
from alphaswarm_sol.vulndocs.tools.formatters import (
    OutputFormat,
    FormatterConfig,
    format_output,
    estimate_tokens,
)


class AssemblyStrategy(Enum):
    """Strategies for assembling context."""

    # Include sections by priority until budget exhausted
    PRIORITY_FIRST = "priority_first"

    # Distribute tokens evenly across sources
    TOKEN_BALANCED = "token_balanced"

    # Start minimal, designed for expansion
    PROGRESSIVE = "progressive"

    # Combine priority and balance
    HYBRID = "hybrid"

    # Pack as much relevant content as possible
    GREEDY = "greedy"


@dataclass
class ContentSource:
    """A source of content for assembly."""

    # Identifier for this source
    source_id: str

    # The content to include
    content: str

    # Priority (lower = higher priority)
    priority: int = 10

    # Token estimate
    token_estimate: int = 0

    # Minimum tokens to include (for progressive)
    min_tokens: int = 0

    # Source category
    category: str = ""

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.token_estimate and self.content:
            self.token_estimate = estimate_tokens(self.content)


@dataclass
class AssembledContext:
    """Result of context assembly."""

    # The assembled content
    content: str

    # Sources that were included
    included_sources: List[str] = field(default_factory=list)

    # Sources that were excluded
    excluded_sources: List[str] = field(default_factory=list)

    # Strategy used
    strategy: AssemblyStrategy = AssemblyStrategy.PRIORITY_FIRST

    # Token accounting
    total_tokens: int = 0
    budget: int = 0
    budget_used: float = 0.0

    # Whether content was truncated
    truncated: bool = False

    # Expansion potential (for progressive)
    expansion_available: bool = False
    expansion_sources: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.total_tokens and self.content:
            self.total_tokens = estimate_tokens(self.content)
        if self.budget > 0:
            self.budget_used = self.total_tokens / self.budget

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "content": self.content,
            "included_sources": self.included_sources,
            "excluded_sources": self.excluded_sources,
            "strategy": self.strategy.value,
            "total_tokens": self.total_tokens,
            "budget": self.budget,
            "budget_used": round(self.budget_used, 3),
            "truncated": self.truncated,
            "expansion_available": self.expansion_available,
            "expansion_sources": self.expansion_sources,
        }


class ContextAssembler:
    """Assembles context from multiple sources using configurable strategies.

    Example:
        assembler = ContextAssembler()

        # Add content sources
        assembler.add_source(ContentSource(
            source_id="detection",
            content="...",
            priority=1,
        ))
        assembler.add_source(ContentSource(
            source_id="business",
            content="...",
            priority=2,
        ))

        # Assemble with priority strategy
        result = assembler.assemble(
            strategy=AssemblyStrategy.PRIORITY_FIRST,
            max_tokens=4000
        )

        # Or use progressive assembly
        result = assembler.assemble(
            strategy=AssemblyStrategy.PROGRESSIVE,
            max_tokens=1000,
            initial_depth=0.3  # Start with 30% of each source
        )
    """

    def __init__(
        self,
        output_format: OutputFormat = OutputFormat.TOON,
        separator: str = "\n\n---\n\n",
    ):
        """Initialize assembler.

        Args:
            output_format: Output format for formatting
            separator: Separator between sections
        """
        self.output_format = output_format
        self.separator = separator
        self.sources: List[ContentSource] = []

    def add_source(self, source: ContentSource) -> "ContextAssembler":
        """Add a content source.

        Args:
            source: ContentSource to add

        Returns:
            Self for chaining
        """
        self.sources.append(source)
        return self

    def add_sources(self, sources: List[ContentSource]) -> "ContextAssembler":
        """Add multiple content sources.

        Args:
            sources: List of ContentSource

        Returns:
            Self for chaining
        """
        self.sources.extend(sources)
        return self

    def clear_sources(self) -> "ContextAssembler":
        """Clear all sources.

        Returns:
            Self for chaining
        """
        self.sources = []
        return self

    def assemble(
        self,
        strategy: AssemblyStrategy = AssemblyStrategy.PRIORITY_FIRST,
        max_tokens: int = 4000,
        **kwargs,
    ) -> AssembledContext:
        """Assemble context using specified strategy.

        Args:
            strategy: Assembly strategy to use
            max_tokens: Token budget
            **kwargs: Strategy-specific options

        Returns:
            AssembledContext with assembled content
        """
        if not self.sources:
            return AssembledContext(
                content="",
                strategy=strategy,
                budget=max_tokens,
            )

        if strategy == AssemblyStrategy.PRIORITY_FIRST:
            return self._assemble_priority_first(max_tokens)
        elif strategy == AssemblyStrategy.TOKEN_BALANCED:
            return self._assemble_balanced(max_tokens)
        elif strategy == AssemblyStrategy.PROGRESSIVE:
            initial_depth = kwargs.get("initial_depth", 0.3)
            return self._assemble_progressive(max_tokens, initial_depth)
        elif strategy == AssemblyStrategy.HYBRID:
            critical_ratio = kwargs.get("critical_ratio", 0.5)
            return self._assemble_hybrid(max_tokens, critical_ratio)
        elif strategy == AssemblyStrategy.GREEDY:
            return self._assemble_greedy(max_tokens)
        else:
            return self._assemble_priority_first(max_tokens)

    def _assemble_priority_first(
        self,
        max_tokens: int,
    ) -> AssembledContext:
        """Assemble by priority until budget exhausted."""
        sorted_sources = sorted(self.sources, key=lambda s: s.priority)

        included = []
        excluded = []
        parts = []
        total = 0

        for source in sorted_sources:
            if total + source.token_estimate <= max_tokens:
                parts.append(source.content)
                included.append(source.source_id)
                total += source.token_estimate
            else:
                excluded.append(source.source_id)

        return AssembledContext(
            content=self.separator.join(parts),
            included_sources=included,
            excluded_sources=excluded,
            strategy=AssemblyStrategy.PRIORITY_FIRST,
            total_tokens=total,
            budget=max_tokens,
            truncated=bool(excluded),
        )

    def _assemble_balanced(
        self,
        max_tokens: int,
    ) -> AssembledContext:
        """Distribute tokens evenly across sources."""
        if not self.sources:
            return AssembledContext(
                content="", strategy=AssemblyStrategy.TOKEN_BALANCED, budget=max_tokens
            )

        tokens_per_source = max_tokens // len(self.sources)

        included = []
        parts = []
        total = 0

        for source in self.sources:
            # Truncate content to fit allocation
            if source.token_estimate <= tokens_per_source:
                parts.append(source.content)
                included.append(source.source_id)
                total += source.token_estimate
            else:
                # Truncate to fit
                truncated_content = self._truncate_content(
                    source.content, tokens_per_source
                )
                parts.append(truncated_content)
                included.append(source.source_id)
                total += estimate_tokens(truncated_content)

        return AssembledContext(
            content=self.separator.join(parts),
            included_sources=included,
            excluded_sources=[],
            strategy=AssemblyStrategy.TOKEN_BALANCED,
            total_tokens=total,
            budget=max_tokens,
            truncated=False,
        )

    def _assemble_progressive(
        self,
        max_tokens: int,
        initial_depth: float = 0.3,
    ) -> AssembledContext:
        """Start with minimal content, designed for expansion.

        Args:
            max_tokens: Total budget
            initial_depth: Fraction of each source to include initially
        """
        sorted_sources = sorted(self.sources, key=lambda s: s.priority)

        included = []
        expansion = []
        parts = []
        total = 0

        for source in sorted_sources:
            # Calculate initial allocation
            initial_tokens = max(
                source.min_tokens,
                int(source.token_estimate * initial_depth),
            )

            if total + initial_tokens <= max_tokens:
                # Include initial portion
                truncated_content = self._truncate_content(
                    source.content, initial_tokens
                )
                parts.append(truncated_content)
                included.append(source.source_id)
                total += estimate_tokens(truncated_content)

                # Mark as expandable if truncated
                if initial_tokens < source.token_estimate:
                    expansion.append(source.source_id)

        return AssembledContext(
            content=self.separator.join(parts),
            included_sources=included,
            excluded_sources=[s.source_id for s in sorted_sources if s.source_id not in included],
            strategy=AssemblyStrategy.PROGRESSIVE,
            total_tokens=total,
            budget=max_tokens,
            truncated=bool(expansion),
            expansion_available=bool(expansion),
            expansion_sources=expansion,
        )

    def _assemble_hybrid(
        self,
        max_tokens: int,
        critical_ratio: float = 0.5,
    ) -> AssembledContext:
        """Hybrid: priority for critical, balanced for rest.

        Args:
            max_tokens: Token budget
            critical_ratio: Fraction of budget for critical (priority <= 2)
        """
        # Split sources by criticality
        critical = [s for s in self.sources if s.priority <= 2]
        other = [s for s in self.sources if s.priority > 2]

        # Allocate budget
        critical_budget = int(max_tokens * critical_ratio)
        other_budget = max_tokens - critical_budget

        # Assemble critical by priority
        critical_sorted = sorted(critical, key=lambda s: s.priority)
        critical_parts = []
        critical_tokens = 0
        critical_included = []

        for source in critical_sorted:
            if critical_tokens + source.token_estimate <= critical_budget:
                critical_parts.append(source.content)
                critical_included.append(source.source_id)
                critical_tokens += source.token_estimate

        # Assemble other balanced
        other_parts = []
        other_tokens = 0
        other_included = []

        if other:
            per_source = other_budget // len(other)
            for source in other:
                if source.token_estimate <= per_source:
                    other_parts.append(source.content)
                    other_tokens += source.token_estimate
                else:
                    truncated = self._truncate_content(source.content, per_source)
                    other_parts.append(truncated)
                    other_tokens += estimate_tokens(truncated)
                other_included.append(source.source_id)

        # Combine
        all_parts = critical_parts + other_parts
        all_included = critical_included + other_included
        all_excluded = [s.source_id for s in self.sources if s.source_id not in all_included]

        return AssembledContext(
            content=self.separator.join(all_parts),
            included_sources=all_included,
            excluded_sources=all_excluded,
            strategy=AssemblyStrategy.HYBRID,
            total_tokens=critical_tokens + other_tokens,
            budget=max_tokens,
            truncated=bool(all_excluded),
        )

    def _assemble_greedy(
        self,
        max_tokens: int,
    ) -> AssembledContext:
        """Pack as much content as possible, prioritizing smaller sources."""
        # Sort by token count (smallest first) to pack more sources
        sorted_sources = sorted(self.sources, key=lambda s: s.token_estimate)

        included = []
        excluded = []
        parts = []
        total = 0

        for source in sorted_sources:
            if total + source.token_estimate <= max_tokens:
                parts.append(source.content)
                included.append(source.source_id)
                total += source.token_estimate
            else:
                # Try to fit partial
                remaining = max_tokens - total
                if remaining >= 100:  # Minimum useful size
                    truncated = self._truncate_content(source.content, remaining)
                    parts.append(truncated)
                    included.append(source.source_id)
                    total += estimate_tokens(truncated)
                else:
                    excluded.append(source.source_id)

        # Re-sort output by original priority for readability
        source_order = {s.source_id: s.priority for s in self.sources}
        ordered_parts = sorted(
            zip(included, parts),
            key=lambda x: source_order.get(x[0], 999)
        )
        included = [x[0] for x in ordered_parts]
        parts = [x[1] for x in ordered_parts]

        return AssembledContext(
            content=self.separator.join(parts),
            included_sources=included,
            excluded_sources=excluded,
            strategy=AssemblyStrategy.GREEDY,
            total_tokens=total,
            budget=max_tokens,
            truncated=bool(excluded),
        )

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit token budget.

        Args:
            content: Content to truncate
            max_tokens: Maximum tokens

        Returns:
            Truncated content
        """
        # Rough: 1 token ~= 4 chars
        max_chars = max_tokens * 4

        if len(content) <= max_chars:
            return content

        # Try to truncate at paragraph boundary
        truncated = content[:max_chars]
        last_para = truncated.rfind("\n\n")
        if last_para > max_chars // 2:
            truncated = truncated[:last_para]

        # Add truncation marker
        return truncated.rstrip() + "\n[...]"

    def expand(
        self,
        current: AssembledContext,
        source_id: str,
        additional_tokens: int,
    ) -> AssembledContext:
        """Expand a source within the context.

        Args:
            current: Current assembled context
            source_id: Source to expand
            additional_tokens: Additional tokens to allow

        Returns:
            Expanded AssembledContext
        """
        # Find the source
        source = next(
            (s for s in self.sources if s.source_id == source_id), None
        )
        if not source:
            return current

        # Find current content for this source
        # This is a simplified expansion - in practice you'd track positions
        new_budget = current.budget + additional_tokens

        # Re-assemble with new budget
        return self.assemble(
            strategy=current.strategy,
            max_tokens=new_budget,
        )


# =============================================================================
# Convenience Functions
# =============================================================================


def assemble_for_finding(
    documents: List[VulnKnowledgeDoc],
    max_tokens: int = 4000,
    strategy: AssemblyStrategy = AssemblyStrategy.PRIORITY_FIRST,
    output_format: OutputFormat = OutputFormat.TOON,
) -> AssembledContext:
    """Assemble context from documents for a finding.

    Args:
        documents: Documents to assemble
        max_tokens: Token budget
        strategy: Assembly strategy
        output_format: Output format

    Returns:
        AssembledContext
    """
    assembler = ContextAssembler(output_format=output_format)

    for i, doc in enumerate(documents):
        content = format_output(
            doc, output_format, FormatterConfig(max_tokens=max_tokens // len(documents))
        )
        assembler.add_source(
            ContentSource(
                source_id=f"doc_{i}_{doc.id}",
                content=content,
                priority=i + 1,
                category=doc.category,
            )
        )

    return assembler.assemble(strategy=strategy, max_tokens=max_tokens)


def quick_assemble(
    contents: Dict[str, str],
    priorities: Optional[Dict[str, int]] = None,
    max_tokens: int = 4000,
) -> str:
    """Quick assembly of content dict to string.

    Args:
        contents: Dict of source_id -> content
        priorities: Optional priority overrides
        max_tokens: Token budget

    Returns:
        Assembled content string
    """
    priorities = priorities or {}
    assembler = ContextAssembler()

    for source_id, content in contents.items():
        assembler.add_source(
            ContentSource(
                source_id=source_id,
                content=content,
                priority=priorities.get(source_id, 10),
            )
        )

    result = assembler.assemble(
        strategy=AssemblyStrategy.PRIORITY_FIRST,
        max_tokens=max_tokens,
    )

    return result.content
