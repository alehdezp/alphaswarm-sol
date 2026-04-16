"""VulnDocs Context Builder.

Phase 17.6: Context Builder for VulnDocs.

This module provides the ContextBuilder class for building optimized LLM context
from multiple VulnDocs knowledge sources. It enables:

1. Building context from patterns, findings, categories, and operations
2. Token budget optimization with priority-based truncation
3. Document coherence preservation (no mid-section cuts)
4. Multiple output formats (system message, user context, bead format)

Usage:
    from alphaswarm_sol.knowledge.vulndocs import KnowledgeNavigator
    from alphaswarm_sol.knowledge.vulndocs.cache import PromptCache
    from alphaswarm_sol.knowledge.vulndocs.builder import ContextBuilder, BuiltContext

    # Initialize
    navigator = KnowledgeNavigator()
    cache = PromptCache(navigator)
    builder = ContextBuilder(navigator, cache)

    # Build context for a pattern
    context = builder.build_for_pattern("vm-001-classic", max_tokens=4000)

    # Build context for a finding
    context = builder.build_for_finding(finding_dict, max_tokens=4000)

    # Format for different uses
    system_msg = format_as_system_message(context)
    user_ctx = format_as_user_context(context)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from alphaswarm_sol.knowledge.vulndocs.schema import (
    Category,
    KnowledgeDepth,
    Subcategory,
)
from alphaswarm_sol.knowledge.vulndocs.cache import (
    CachedBlock,
    CacheControlType,
    estimate_tokens,
    generate_cache_key,
)

if TYPE_CHECKING:
    from alphaswarm_sol.knowledge.vulndocs.navigator import KnowledgeNavigator
    from alphaswarm_sol.knowledge.vulndocs.cache import PromptCache


# =============================================================================
# CONSTANTS
# =============================================================================

# Default token budgets
DEFAULT_MAX_TOKENS = 4000
MIN_TOKENS_PER_SOURCE = 200
NAVIGATION_HINT_TOKENS = 100

# Priority levels (higher = more important)
PRIORITY_CRITICAL = 100
PRIORITY_HIGH = 80
PRIORITY_MEDIUM = 60
PRIORITY_LOW = 40
PRIORITY_NAVIGATION = 20

# Pattern prefix to category mapping
PATTERN_CATEGORY_MAP = {
    "reentrancy": ["reentrancy"],
    "vm": ["reentrancy", "token"],  # value-movement
    "auth": ["access-control"],
    "oracle": ["oracle"],
    "token": ["token"],
    "upgrade": ["upgrade"],
    "mev": ["mev"],
    "dos": ["dos"],
    "crypto": ["crypto"],
    "flash": ["flash-loan"],
    "gov": ["governance"],
    "logic": ["logic"],
    "ext": ["reentrancy", "dos"],  # external-influence
    "emergency": ["access-control"],
    "multisig": ["crypto", "access-control"],
    "price": ["oracle"],
    "swap": ["mev", "token"],
    "vault": ["reentrancy", "token"],
    "staking": ["token", "reentrancy"],
    "lending": ["oracle", "reentrancy"],
}

# Operation to category mapping
OPERATION_CATEGORY_MAP = {
    "TRANSFERS_VALUE_OUT": ["reentrancy", "token"],
    "WRITES_USER_BALANCE": ["reentrancy", "token"],
    "READS_USER_BALANCE": ["reentrancy"],
    "CHECKS_PERMISSION": ["access-control"],
    "MODIFIES_OWNER": ["access-control"],
    "MODIFIES_ROLES": ["access-control"],
    "CALLS_EXTERNAL": ["reentrancy", "dos"],
    "CALLS_UNTRUSTED": ["reentrancy"],
    "READS_EXTERNAL_VALUE": ["oracle"],
    "READS_ORACLE": ["oracle"],
    "MODIFIES_CRITICAL_STATE": ["access-control", "reentrancy"],
    "USES_BLOCK_TIMESTAMP": ["mev"],
    "USES_MSG_SENDER": ["access-control"],
    "USES_TX_ORIGIN": ["access-control"],
    "EMITS_EVENT": [],
    "USES_ECRECOVER": ["crypto"],
    "HANDLES_ETH": ["reentrancy", "dos"],
}


# =============================================================================
# DATACLASSES
# =============================================================================


@dataclass
class ContextSource:
    """A single source of context content.

    Represents a piece of knowledge that can be included in the built context.

    Attributes:
        source_type: Type of source ("category", "subcategory", "document", "custom").
        source_id: Unique identifier for the source.
        content: The actual content string.
        tokens: Estimated token count for this content.
        priority: Priority level (higher = more important, included first).
    """

    source_type: str
    source_id: str
    content: str
    tokens: int
    priority: int = PRIORITY_MEDIUM

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "content": self.content,
            "tokens": self.tokens,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextSource":
        """Deserialize from dictionary."""
        return cls(
            source_type=data.get("source_type", "custom"),
            source_id=data.get("source_id", ""),
            content=data.get("content", ""),
            tokens=data.get("tokens", 0),
            priority=data.get("priority", PRIORITY_MEDIUM),
        )

    def __post_init__(self):
        """Calculate token estimate if not provided."""
        if self.tokens == 0 and self.content:
            self.tokens = estimate_tokens(self.content)


@dataclass
class BuiltContext:
    """A built context ready for LLM consumption.

    Contains the formatted content, source information, and metadata about
    how the context was constructed.

    Attributes:
        content: The final formatted context string.
        sources: List of ContextSource objects that were used.
        estimated_tokens: Total estimated token count.
        cache_blocks: List of CachedBlock objects for prompt caching.
        metadata: Build metadata (categories, patterns, depth, etc.).
    """

    content: str
    sources: List[ContextSource] = field(default_factory=list)
    estimated_tokens: int = 0
    cache_blocks: List[CachedBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate token estimate if not provided."""
        if self.estimated_tokens == 0 and self.content:
            self.estimated_tokens = estimate_tokens(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "content": self.content,
            "sources": [s.to_dict() for s in self.sources],
            "estimated_tokens": self.estimated_tokens,
            "cache_blocks": [b.to_dict() for b in self.cache_blocks],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuiltContext":
        """Deserialize from dictionary."""
        return cls(
            content=data.get("content", ""),
            sources=[ContextSource.from_dict(s) for s in data.get("sources", [])],
            estimated_tokens=data.get("estimated_tokens", 0),
            cache_blocks=[CachedBlock.from_dict(b) for b in data.get("cache_blocks", [])],
            metadata=data.get("metadata", {}),
        )

    def is_empty(self) -> bool:
        """Check if context has no content."""
        return not self.content or len(self.content.strip()) == 0

    def get_source_ids(self) -> List[str]:
        """Get all source IDs."""
        return [s.source_id for s in self.sources]

    def get_source_types(self) -> List[str]:
        """Get unique source types."""
        return list(set(s.source_type for s in self.sources))


# =============================================================================
# CONTEXT BUILDER CLASS
# =============================================================================


class ContextBuilder:
    """Builder for optimized LLM context from VulnDocs knowledge.

    Provides methods to build context from patterns, findings, categories,
    operations, and custom sources. Optimizes for token budget and
    maintains document coherence.

    Attributes:
        navigator: KnowledgeNavigator instance for loading knowledge.
        cache: PromptCache instance for caching.
    """

    def __init__(
        self,
        navigator: "KnowledgeNavigator",
        cache: "PromptCache",
    ) -> None:
        """Initialize the context builder.

        Args:
            navigator: KnowledgeNavigator instance for loading knowledge.
            cache: PromptCache instance for caching.
        """
        self.navigator = navigator
        self.cache = cache

    # =========================================================================
    # BUILD METHODS
    # =========================================================================

    def build_for_pattern(
        self,
        pattern_id: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> BuiltContext:
        """Build context for a specific vulnerability pattern.

        Uses the pattern ID to determine relevant categories and builds
        optimized context for LLM analysis.

        Args:
            pattern_id: The pattern ID (e.g., "vm-001-classic", "auth-002-weak").
            max_tokens: Maximum token budget.

        Returns:
            BuiltContext with relevant knowledge.
        """
        sources: List[ContextSource] = []
        cache_blocks: List[CachedBlock] = []

        # Determine relevant categories from pattern ID
        categories = self._categories_from_pattern(pattern_id)

        # Load context for each relevant category
        for category_id in categories:
            try:
                # Get category-level context
                content = self.navigator.get_context(
                    category_id, depth=KnowledgeDepth.DETECTION
                )
                source = ContextSource(
                    source_type="category",
                    source_id=category_id,
                    content=content,
                    tokens=estimate_tokens(content),
                    priority=PRIORITY_HIGH,
                )
                sources.append(source)

                # Cache the content
                cache_key = generate_cache_key(
                    category_id, None, KnowledgeDepth.DETECTION, None
                )
                block = self.cache.set_cached_block(
                    cache_key, content, CacheControlType.EPHEMERAL
                )
                cache_blocks.append(block)

                # Try to get more specific subcategory if pattern hints at it
                subcategory_id = self._subcategory_from_pattern(pattern_id, category_id)
                if subcategory_id:
                    try:
                        sub_content = self.navigator.get_context(
                            category_id, subcategory_id, depth=KnowledgeDepth.DETECTION
                        )
                        sub_source = ContextSource(
                            source_type="subcategory",
                            source_id=f"{category_id}/{subcategory_id}",
                            content=sub_content,
                            tokens=estimate_tokens(sub_content),
                            priority=PRIORITY_CRITICAL,
                        )
                        sources.append(sub_source)

                        sub_cache_key = generate_cache_key(
                            category_id, subcategory_id, KnowledgeDepth.DETECTION, None
                        )
                        sub_block = self.cache.set_cached_block(
                            sub_cache_key, sub_content, CacheControlType.EPHEMERAL
                        )
                        cache_blocks.append(sub_block)
                    except (ValueError, FileNotFoundError):
                        pass

            except (ValueError, FileNotFoundError):
                continue

        # Add navigation hints if room in budget
        nav_source = self._create_navigation_hint(pattern_id, categories)
        if nav_source:
            sources.append(nav_source)

        # Optimize and build final context
        return self._build_optimized(sources, cache_blocks, max_tokens, {
            "pattern_id": pattern_id,
            "categories": categories,
            "build_type": "pattern",
        })

    def build_for_finding(
        self,
        finding: Dict[str, Any],
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> BuiltContext:
        """Build context for a vulnerability finding.

        Extracts relevant information from the finding to build targeted context.

        Args:
            finding: Dictionary containing finding information (pattern_id,
                     operations, severity, etc.).
            max_tokens: Maximum token budget.

        Returns:
            BuiltContext with relevant knowledge.
        """
        sources: List[ContextSource] = []
        cache_blocks: List[CachedBlock] = []

        # Extract pattern ID from finding
        pattern_id = finding.get("pattern_id") or finding.get("pattern") or ""
        operations = finding.get("operations", [])
        signature = finding.get("signature") or finding.get("behavioral_signature", "")
        severity = finding.get("severity", "medium")

        # Determine categories from multiple signals
        categories = set()

        # From pattern
        if pattern_id:
            categories.update(self._categories_from_pattern(pattern_id))

        # From operations
        for op in operations:
            if op in OPERATION_CATEGORY_MAP:
                categories.update(OPERATION_CATEGORY_MAP[op])

        # From signature search
        if signature:
            try:
                sig_categories = self.navigator.search_by_signature(signature)
                for cat in sig_categories:
                    categories.add(cat.id)
            except (ValueError, FileNotFoundError):
                pass

        # Convert to list and limit to top 3 most relevant
        category_list = list(categories)[:3]

        # Load context for each category
        for category_id in category_list:
            try:
                content = self.navigator.get_context(
                    category_id, depth=KnowledgeDepth.DETECTION
                )
                priority = PRIORITY_CRITICAL if severity in ["critical", "high"] else PRIORITY_HIGH
                source = ContextSource(
                    source_type="category",
                    source_id=category_id,
                    content=content,
                    tokens=estimate_tokens(content),
                    priority=priority,
                )
                sources.append(source)

                cache_key = generate_cache_key(
                    category_id, None, KnowledgeDepth.DETECTION, None
                )
                block = self.cache.set_cached_block(
                    cache_key, content, CacheControlType.EPHEMERAL
                )
                cache_blocks.append(block)

            except (ValueError, FileNotFoundError):
                continue

        # Add finding-specific context
        if finding.get("function_name") or finding.get("contract_name"):
            finding_context = self._format_finding_context(finding)
            finding_source = ContextSource(
                source_type="finding",
                source_id=f"finding-{pattern_id}",
                content=finding_context,
                tokens=estimate_tokens(finding_context),
                priority=PRIORITY_CRITICAL,
            )
            sources.append(finding_source)

        return self._build_optimized(sources, cache_blocks, max_tokens, {
            "pattern_id": pattern_id,
            "operations": operations,
            "signature": signature,
            "severity": severity,
            "categories": category_list,
            "build_type": "finding",
        })

    def build_for_category(
        self,
        category_id: str,
        depth: KnowledgeDepth = KnowledgeDepth.DETECTION,
    ) -> BuiltContext:
        """Build context for a vulnerability category.

        Args:
            category_id: The category identifier.
            depth: Depth level for context retrieval.

        Returns:
            BuiltContext for the category.
        """
        sources: List[ContextSource] = []
        cache_blocks: List[CachedBlock] = []

        try:
            # Get category context
            content = self.navigator.get_context(category_id, depth=depth)
            source = ContextSource(
                source_type="category",
                source_id=category_id,
                content=content,
                tokens=estimate_tokens(content),
                priority=PRIORITY_HIGH,
            )
            sources.append(source)

            cache_key = generate_cache_key(category_id, None, depth, None)
            block = self.cache.set_cached_block(
                cache_key, content, CacheControlType.EPHEMERAL
            )
            cache_blocks.append(block)

            # For deeper depths, include subcategory information
            if depth in [KnowledgeDepth.FULL, KnowledgeDepth.PATTERNS, KnowledgeDepth.EXPLOITS]:
                for sub_id in self.navigator.list_subcategories(category_id)[:5]:
                    try:
                        sub_content = self.navigator.get_context(
                            category_id, sub_id, depth=depth
                        )
                        sub_source = ContextSource(
                            source_type="subcategory",
                            source_id=f"{category_id}/{sub_id}",
                            content=sub_content,
                            tokens=estimate_tokens(sub_content),
                            priority=PRIORITY_MEDIUM,
                        )
                        sources.append(sub_source)

                        sub_cache_key = generate_cache_key(category_id, sub_id, depth, None)
                        sub_block = self.cache.set_cached_block(
                            sub_cache_key, sub_content, CacheControlType.EPHEMERAL
                        )
                        cache_blocks.append(sub_block)
                    except (ValueError, FileNotFoundError):
                        continue

        except (ValueError, FileNotFoundError):
            pass

        # No max_tokens limit for category builds - include everything
        total_tokens = sum(s.tokens for s in sources)
        combined_content = "\n\n---\n\n".join(s.content for s in sources)

        return BuiltContext(
            content=combined_content,
            sources=sources,
            estimated_tokens=total_tokens,
            cache_blocks=cache_blocks,
            metadata={
                "category_id": category_id,
                "depth": depth.value,
                "build_type": "category",
            },
        )

    def build_for_operations(
        self,
        operations: List[str],
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> BuiltContext:
        """Build context based on semantic operations.

        Uses the operations to determine relevant vulnerability categories
        and builds targeted context.

        Args:
            operations: List of semantic operation names.
            max_tokens: Maximum token budget.

        Returns:
            BuiltContext with relevant knowledge.
        """
        sources: List[ContextSource] = []
        cache_blocks: List[CachedBlock] = []

        # Determine categories from operations
        categories = set()
        for op in operations:
            if op in OPERATION_CATEGORY_MAP:
                categories.update(OPERATION_CATEGORY_MAP[op])

            # Also try navigator search
            try:
                op_categories = self.navigator.search_by_operation(op)
                for cat in op_categories:
                    categories.add(cat.id)
            except (ValueError, FileNotFoundError):
                pass

        # Limit and prioritize
        category_list = list(categories)[:4]

        # Load context for each category
        for category_id in category_list:
            try:
                content = self.navigator.get_context(
                    category_id, depth=KnowledgeDepth.DETECTION
                )
                source = ContextSource(
                    source_type="category",
                    source_id=category_id,
                    content=content,
                    tokens=estimate_tokens(content),
                    priority=PRIORITY_HIGH,
                )
                sources.append(source)

                cache_key = generate_cache_key(
                    category_id, None, KnowledgeDepth.DETECTION, None
                )
                block = self.cache.set_cached_block(
                    cache_key, content, CacheControlType.EPHEMERAL
                )
                cache_blocks.append(block)

            except (ValueError, FileNotFoundError):
                continue

        # Add operations summary
        ops_summary = self._format_operations_summary(operations, category_list)
        ops_source = ContextSource(
            source_type="summary",
            source_id="operations-summary",
            content=ops_summary,
            tokens=estimate_tokens(ops_summary),
            priority=PRIORITY_CRITICAL,
        )
        sources.append(ops_source)

        return self._build_optimized(sources, cache_blocks, max_tokens, {
            "operations": operations,
            "categories": category_list,
            "build_type": "operations",
        })

    def build_for_signature(
        self,
        signature: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> BuiltContext:
        """Build context based on a behavioral signature.

        Uses the signature to find matching vulnerability categories
        and builds targeted context.

        Args:
            signature: Behavioral signature (e.g., "R:bal->X:out->W:bal").
            max_tokens: Maximum token budget.

        Returns:
            BuiltContext with relevant knowledge.
        """
        sources: List[ContextSource] = []
        cache_blocks: List[CachedBlock] = []

        # Search for categories matching signature
        try:
            sig_categories = self.navigator.search_by_signature(signature)
        except (ValueError, FileNotFoundError):
            sig_categories = []

        # Also try operation-based search by parsing signature
        operations = self._parse_signature_operations(signature)
        op_categories = set()
        for op in operations:
            if op in OPERATION_CATEGORY_MAP:
                op_categories.update(OPERATION_CATEGORY_MAP[op])

        # Combine category IDs
        category_ids = [c.id for c in sig_categories]
        category_ids.extend(op_categories)
        category_ids = list(set(category_ids))[:3]

        # Load context for each category
        for category_id in category_ids:
            try:
                content = self.navigator.get_context(
                    category_id, depth=KnowledgeDepth.DETECTION
                )
                priority = PRIORITY_CRITICAL if category_id in [c.id for c in sig_categories] else PRIORITY_HIGH
                source = ContextSource(
                    source_type="category",
                    source_id=category_id,
                    content=content,
                    tokens=estimate_tokens(content),
                    priority=priority,
                )
                sources.append(source)

                cache_key = generate_cache_key(
                    category_id, None, KnowledgeDepth.DETECTION, None
                )
                block = self.cache.set_cached_block(
                    cache_key, content, CacheControlType.EPHEMERAL
                )
                cache_blocks.append(block)

            except (ValueError, FileNotFoundError):
                continue

        # Add signature analysis
        sig_analysis = self._format_signature_analysis(signature, operations)
        sig_source = ContextSource(
            source_type="analysis",
            source_id="signature-analysis",
            content=sig_analysis,
            tokens=estimate_tokens(sig_analysis),
            priority=PRIORITY_CRITICAL,
        )
        sources.append(sig_source)

        return self._build_optimized(sources, cache_blocks, max_tokens, {
            "signature": signature,
            "operations": operations,
            "categories": category_ids,
            "build_type": "signature",
        })

    def build_custom(
        self,
        sources: List[ContextSource],
    ) -> BuiltContext:
        """Build context from explicit sources.

        Allows building context from a custom list of sources
        without automatic category detection.

        Args:
            sources: List of ContextSource objects.

        Returns:
            BuiltContext with the provided sources.
        """
        cache_blocks: List[CachedBlock] = []

        # Cache each source
        for source in sources:
            cache_key = f"custom-{source.source_id}-{_content_hash(source.content)[:8]}"
            block = self.cache.set_cached_block(
                cache_key, source.content, CacheControlType.EPHEMERAL
            )
            cache_blocks.append(block)

        # Sort by priority
        sorted_sources = sorted(sources, key=lambda s: s.priority, reverse=True)

        # Combine content
        combined_content = "\n\n---\n\n".join(s.content for s in sorted_sources)
        total_tokens = sum(s.tokens for s in sorted_sources)

        return BuiltContext(
            content=combined_content,
            sources=sorted_sources,
            estimated_tokens=total_tokens,
            cache_blocks=cache_blocks,
            metadata={
                "source_count": len(sources),
                "build_type": "custom",
            },
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _categories_from_pattern(self, pattern_id: str) -> List[str]:
        """Extract relevant categories from a pattern ID."""
        categories = []

        # Try prefix matching
        parts = pattern_id.lower().split("-")
        for i in range(len(parts)):
            prefix = "-".join(parts[:i + 1]) if i > 0 else parts[0]
            if prefix in PATTERN_CATEGORY_MAP:
                categories.extend(PATTERN_CATEGORY_MAP[prefix])
                break

        # If no prefix match, try keyword matching
        if not categories:
            for keyword, cats in PATTERN_CATEGORY_MAP.items():
                if keyword in pattern_id.lower():
                    categories.extend(cats)
                    break

        # Default to reentrancy if nothing found (most common)
        if not categories:
            categories = ["reentrancy"]

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for cat in categories:
            if cat not in seen:
                seen.add(cat)
                unique.append(cat)

        return unique[:3]  # Limit to 3 categories

    def _subcategory_from_pattern(
        self, pattern_id: str, category_id: str
    ) -> Optional[str]:
        """Try to extract subcategory ID from pattern ID."""
        # Common subcategory keywords
        subcategory_hints = {
            "classic": "classic",
            "cross": "cross-function",
            "cross-function": "cross-function",
            "cross-contract": "cross-contract",
            "read-only": "read-only",
            "readonly": "read-only",
            "weak": "weak-controls",
            "missing": "missing-controls",
            "oracle": "price-manipulation",
            "price": "price-manipulation",
            "stale": "stale-data",
            "frontrun": "frontrunning",
            "sandwich": "sandwich-attack",
        }

        pattern_lower = pattern_id.lower()
        for hint, subcategory in subcategory_hints.items():
            if hint in pattern_lower:
                # Verify subcategory exists
                try:
                    self.navigator.get_subcategory(category_id, subcategory)
                    return subcategory
                except (ValueError, FileNotFoundError):
                    continue

        return None

    def _create_navigation_hint(
        self, pattern_id: str, categories: List[str]
    ) -> Optional[ContextSource]:
        """Create a navigation hint for the LLM."""
        if not categories:
            return None

        hints = [
            f"## Navigation Hint",
            f"",
            f"Pattern: `{pattern_id}`",
            f"Related Categories: {', '.join(f'`{c}`' for c in categories)}",
            f"",
            f"For deeper analysis, consider:",
            f"- Use `get_context(category, subcategory, KnowledgeDepth.FULL)` for complete details",
            f"- Check related patterns in the same category",
            f"- Review exploit examples for similar vulnerabilities",
        ]

        content = "\n".join(hints)
        return ContextSource(
            source_type="navigation",
            source_id="navigation-hint",
            content=content,
            tokens=estimate_tokens(content),
            priority=PRIORITY_NAVIGATION,
        )

    def _format_finding_context(self, finding: Dict[str, Any]) -> str:
        """Format finding-specific context."""
        lines = ["## Finding Context", ""]

        if finding.get("contract_name"):
            lines.append(f"**Contract:** `{finding['contract_name']}`")
        if finding.get("function_name"):
            lines.append(f"**Function:** `{finding['function_name']}`")
        if finding.get("severity"):
            lines.append(f"**Severity:** {finding['severity']}")
        if finding.get("pattern_id") or finding.get("pattern"):
            pattern = finding.get("pattern_id") or finding.get("pattern")
            lines.append(f"**Pattern:** `{pattern}`")

        lines.append("")

        if finding.get("operations"):
            lines.append("**Detected Operations:**")
            for op in finding["operations"]:
                lines.append(f"- `{op}`")
            lines.append("")

        if finding.get("signature") or finding.get("behavioral_signature"):
            sig = finding.get("signature") or finding.get("behavioral_signature")
            lines.append(f"**Behavioral Signature:** `{sig}`")
            lines.append("")

        return "\n".join(lines)

    def _format_operations_summary(
        self, operations: List[str], categories: List[str]
    ) -> str:
        """Format operations summary."""
        lines = [
            "## Operations Analysis",
            "",
            "**Detected Operations:**",
        ]
        for op in operations:
            lines.append(f"- `{op}`")

        lines.append("")
        lines.append("**Relevant Vulnerability Categories:**")
        for cat in categories:
            lines.append(f"- `{cat}`")

        lines.append("")
        lines.append("Consider checking for:")
        if any("VALUE" in op or "BALANCE" in op for op in operations):
            lines.append("- Reentrancy vulnerabilities")
            lines.append("- Token transfer issues")
        if any("PERMISSION" in op or "OWNER" in op or "ROLE" in op for op in operations):
            lines.append("- Access control weaknesses")
        if any("EXTERNAL" in op or "ORACLE" in op for op in operations):
            lines.append("- External call safety")
            lines.append("- Price oracle manipulation")

        return "\n".join(lines)

    def _parse_signature_operations(self, signature: str) -> List[str]:
        """Parse operations from a behavioral signature."""
        # Signature format: R:bal->X:out->W:bal
        operations = []

        # Map signature components to operations
        sig_op_map = {
            "R:bal": "READS_USER_BALANCE",
            "W:bal": "WRITES_USER_BALANCE",
            "X:out": "TRANSFERS_VALUE_OUT",
            "X:ext": "CALLS_EXTERNAL",
            "C:perm": "CHECKS_PERMISSION",
            "M:owner": "MODIFIES_OWNER",
            "R:oracle": "READS_ORACLE",
        }

        for sig_part, op in sig_op_map.items():
            if sig_part in signature:
                operations.append(op)

        return operations

    def _format_signature_analysis(
        self, signature: str, operations: List[str]
    ) -> str:
        """Format signature analysis."""
        lines = [
            "## Behavioral Signature Analysis",
            "",
            f"**Signature:** `{signature}`",
            "",
        ]

        if operations:
            lines.append("**Extracted Operations:**")
            for op in operations:
                lines.append(f"- `{op}`")
            lines.append("")

        # Analyze signature pattern
        if "X:out" in signature and "W:bal" in signature:
            if signature.index("X:out") < signature.index("W:bal"):
                lines.append("**Warning:** External call before state write detected")
                lines.append("This pattern may indicate reentrancy vulnerability.")
            else:
                lines.append("**Note:** State write before external call (CEI pattern)")
                lines.append("This is the recommended secure pattern.")

        return "\n".join(lines)

    def _build_optimized(
        self,
        sources: List[ContextSource],
        cache_blocks: List[CachedBlock],
        max_tokens: int,
        metadata: Dict[str, Any],
    ) -> BuiltContext:
        """Build optimized context within token budget.

        Sorts sources by priority, includes as many as fit within budget,
        and maintains document coherence.
        """
        if not sources:
            return BuiltContext(
                content="",
                sources=[],
                estimated_tokens=0,
                cache_blocks=[],
                metadata=metadata,
            )

        # Sort by priority (highest first)
        sorted_sources = sorted(sources, key=lambda s: s.priority, reverse=True)

        # Select sources that fit in budget
        selected: List[ContextSource] = []
        total_tokens = 0

        for source in sorted_sources:
            if total_tokens + source.tokens <= max_tokens:
                selected.append(source)
                total_tokens += source.tokens
            elif source.priority >= PRIORITY_CRITICAL:
                # Critical sources get truncated if needed
                remaining = max_tokens - total_tokens
                if remaining >= MIN_TOKENS_PER_SOURCE:
                    truncated_content = self._truncate_content(
                        source.content, remaining
                    )
                    truncated_source = ContextSource(
                        source_type=source.source_type,
                        source_id=source.source_id,
                        content=truncated_content,
                        tokens=estimate_tokens(truncated_content),
                        priority=source.priority,
                    )
                    selected.append(truncated_source)
                    total_tokens += truncated_source.tokens
                break

        # Combine content with separators
        combined_content = "\n\n---\n\n".join(s.content for s in selected)

        return BuiltContext(
            content=combined_content,
            sources=selected,
            estimated_tokens=total_tokens,
            cache_blocks=cache_blocks,
            metadata=metadata,
        )

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit token budget, preserving section coherence."""
        if estimate_tokens(content) <= max_tokens:
            return content

        # Try to truncate at section boundaries
        sections = re.split(r'\n(?=##?\s)', content)

        truncated = []
        total = 0

        for section in sections:
            section_tokens = estimate_tokens(section)
            if total + section_tokens <= max_tokens:
                truncated.append(section)
                total += section_tokens
            else:
                # Check if we have room for a partial section
                remaining = max_tokens - total
                if remaining >= MIN_TOKENS_PER_SOURCE:
                    # Truncate within section at paragraph boundary
                    paragraphs = section.split("\n\n")
                    partial = []
                    partial_tokens = 0
                    for para in paragraphs:
                        para_tokens = estimate_tokens(para)
                        if partial_tokens + para_tokens <= remaining:
                            partial.append(para)
                            partial_tokens += para_tokens
                        else:
                            break
                    if partial:
                        truncated.append("\n\n".join(partial))
                        truncated.append("\n\n[...truncated...]")
                break

        return "\n".join(truncated)


# =============================================================================
# FORMAT FUNCTIONS
# =============================================================================


def format_as_system_message(context: BuiltContext) -> str:
    """Format built context as a system message.

    Creates a formatted system message suitable for LLM system prompts.

    Args:
        context: The BuiltContext to format.

    Returns:
        Formatted system message string.
    """
    if context.is_empty():
        return ""

    lines = [
        "# VulnDocs Knowledge Context",
        "",
        f"Sources: {len(context.sources)} | Tokens: ~{context.estimated_tokens}",
        "",
        "---",
        "",
        context.content,
    ]

    return "\n".join(lines)


def format_as_user_context(context: BuiltContext) -> str:
    """Format built context as user-provided context.

    Creates a formatted context block suitable for including in user messages.

    Args:
        context: The BuiltContext to format.

    Returns:
        Formatted user context string.
    """
    if context.is_empty():
        return ""

    lines = [
        "<vulnerability-knowledge>",
        context.content,
        "</vulnerability-knowledge>",
    ]

    return "\n".join(lines)


def format_for_bead(context: BuiltContext, bead_id: str) -> str:
    """Format built context for a specific bead in a chain.

    Creates a formatted context block for use in LLM bead chains.

    Args:
        context: The BuiltContext to format.
        bead_id: Identifier for the bead.

    Returns:
        Formatted bead context string.
    """
    if context.is_empty():
        return ""

    metadata_str = ", ".join(
        f"{k}={v}" for k, v in context.metadata.items()
        if k not in ["build_type"]
    )

    lines = [
        f"<!-- Bead: {bead_id} | {context.metadata.get('build_type', 'unknown')} -->",
        f"<!-- Metadata: {metadata_str} -->",
        "",
        context.content,
        "",
        f"<!-- End Bead: {bead_id} -->",
    ]

    return "\n".join(lines)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _content_hash(content: str) -> str:
    """Generate a short hash for content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
