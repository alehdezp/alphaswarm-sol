"""Prompt caching support for VulnDocs context.

Implements caching strategies for Anthropic prompt caching:
- Layer 1: System context (cached for session)
- Layer 2: Category context (cached per category)
- Layer 3: Dynamic context (not cached)

Per TRACKER.md prompt caching architecture:
- System context: ~3,000 tokens (navigation, category index)
- Category context: ~1,500 tokens per category
- Dynamic context: ~500-1,000 tokens per finding
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import md5
from typing import Any, Dict, List, Optional


class CacheLayer(Enum):
    """Cache layer for context sections."""

    # Session-level cache (system instructions, navigation)
    SYSTEM = "system"

    # Category-level cache (changes when category docs updated)
    CATEGORY = "category"

    # No caching (finding-specific content)
    DYNAMIC = "dynamic"


@dataclass
class CacheableContext:
    """Context with caching metadata.

    Supports Anthropic's prompt caching via cache_control markers.
    """

    # The context content
    content: str

    # Cache layer
    layer: CacheLayer

    # Cache key (for invalidation)
    cache_key: str = ""

    # Version for cache invalidation
    version: str = ""

    # Token estimate
    token_estimate: int = 0

    # Metadata
    source: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.cache_key:
            self.cache_key = self._generate_cache_key()
        if not self.token_estimate:
            self.token_estimate = len(self.content) // 4

    def _generate_cache_key(self) -> str:
        """Generate cache key from content hash."""
        content_hash = md5(self.content.encode()).hexdigest()[:12]
        return f"{self.layer.value}-{content_hash}"

    def to_anthropic_block(self) -> Dict[str, Any]:
        """Convert to Anthropic message block with cache_control.

        Returns block suitable for Anthropic API with caching.
        """
        block = {
            "type": "text",
            "text": self.content,
        }

        # Add cache_control for cacheable layers
        if self.layer in (CacheLayer.SYSTEM, CacheLayer.CATEGORY):
            block["cache_control"] = {"type": "ephemeral"}

        return block

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "content": self.content,
            "layer": self.layer.value,
            "cache_key": self.cache_key,
            "version": self.version,
            "token_estimate": self.token_estimate,
            "source": self.source,
            "created_at": self.created_at,
        }


@dataclass
class CachedContextSet:
    """A set of cached context blocks for a prompt."""

    # System-level context (always first)
    system_context: Optional[CacheableContext] = None

    # Category-level context
    category_contexts: List[CacheableContext] = field(default_factory=list)

    # Dynamic context (finding-specific)
    dynamic_context: Optional[CacheableContext] = None

    def get_total_tokens(self) -> int:
        """Get total token estimate."""
        total = 0
        if self.system_context:
            total += self.system_context.token_estimate
        for cat in self.category_contexts:
            total += cat.token_estimate
        if self.dynamic_context:
            total += self.dynamic_context.token_estimate
        return total

    def to_anthropic_blocks(self) -> List[Dict[str, Any]]:
        """Convert to list of Anthropic message blocks.

        Returns blocks in correct order for caching:
        1. System context (cached)
        2. Category contexts (cached)
        3. Dynamic context (not cached)
        """
        blocks = []

        if self.system_context:
            blocks.append(self.system_context.to_anthropic_block())

        for cat_ctx in self.category_contexts:
            blocks.append(cat_ctx.to_anthropic_block())

        if self.dynamic_context:
            blocks.append(self.dynamic_context.to_anthropic_block())

        return blocks

    def get_combined_content(self) -> str:
        """Get all context as a single string."""
        parts = []
        if self.system_context:
            parts.append(self.system_context.content)
        for cat in self.category_contexts:
            parts.append(cat.content)
        if self.dynamic_context:
            parts.append(self.dynamic_context.content)
        return "\n\n---\n\n".join(parts)


class PromptCacheManager:
    """Manages prompt caching for VulnDocs.

    Implements the three-layer caching strategy:
    - Layer 1 (SYSTEM): Navigation, tool instructions (session lifetime)
    - Layer 2 (CATEGORY): Category overviews (until docs updated)
    - Layer 3 (DYNAMIC): Finding-specific context (no caching)

    Example:
        manager = PromptCacheManager()

        # Get cached system context
        system = manager.get_system_context()

        # Get cached category context
        category = manager.get_category_context("reentrancy")

        # Build cached context set
        context_set = manager.build_context_set(
            categories=["reentrancy"],
            finding={"category": "reentrancy", "signals": [...]}
        )

        # Use with Anthropic API
        blocks = context_set.to_anthropic_blocks()
    """

    def __init__(
        self,
        system_context: Optional[str] = None,
        version: str = "1.0",
    ):
        """Initialize cache manager.

        Args:
            system_context: Optional pre-built system context
            version: Version for cache invalidation
        """
        self.version = version
        self._system_cache: Optional[CacheableContext] = None
        self._category_cache: Dict[str, CacheableContext] = {}

        if system_context:
            self._system_cache = CacheableContext(
                content=system_context,
                layer=CacheLayer.SYSTEM,
                version=version,
                source="system",
            )

    def get_system_context(self) -> Optional[CacheableContext]:
        """Get cached system context.

        Returns system context (navigation, tool guide) if available.
        """
        return self._system_cache

    def set_system_context(
        self,
        content: str,
        version: Optional[str] = None,
    ) -> CacheableContext:
        """Set system context for caching.

        Args:
            content: System context content
            version: Optional version override

        Returns:
            CacheableContext for system layer
        """
        self._system_cache = CacheableContext(
            content=content,
            layer=CacheLayer.SYSTEM,
            version=version or self.version,
            source="system",
        )
        return self._system_cache

    def get_category_context(
        self,
        category: str,
    ) -> Optional[CacheableContext]:
        """Get cached category context.

        Args:
            category: Category name

        Returns:
            CacheableContext for category if cached
        """
        return self._category_cache.get(category)

    def set_category_context(
        self,
        category: str,
        content: str,
        version: Optional[str] = None,
    ) -> CacheableContext:
        """Set category context for caching.

        Args:
            category: Category name
            content: Category context content
            version: Optional version override

        Returns:
            CacheableContext for category
        """
        ctx = CacheableContext(
            content=content,
            layer=CacheLayer.CATEGORY,
            version=version or self.version,
            source=category,
        )
        self._category_cache[category] = ctx
        return ctx

    def create_dynamic_context(
        self,
        content: str,
        source: str = "",
    ) -> CacheableContext:
        """Create a dynamic (non-cached) context.

        Args:
            content: Context content
            source: Source identifier

        Returns:
            CacheableContext with DYNAMIC layer
        """
        return CacheableContext(
            content=content,
            layer=CacheLayer.DYNAMIC,
            version="",  # No version for dynamic
            source=source,
        )

    def build_context_set(
        self,
        categories: Optional[List[str]] = None,
        dynamic_content: Optional[str] = None,
        include_system: bool = True,
    ) -> CachedContextSet:
        """Build a context set with cached components.

        Args:
            categories: Categories to include
            dynamic_content: Dynamic finding-specific content
            include_system: Whether to include system context

        Returns:
            CachedContextSet ready for API use
        """
        context_set = CachedContextSet()

        # Add system context
        if include_system and self._system_cache:
            context_set.system_context = self._system_cache

        # Add category contexts
        if categories:
            for cat in categories:
                cat_ctx = self._category_cache.get(cat)
                if cat_ctx:
                    context_set.category_contexts.append(cat_ctx)

        # Add dynamic context
        if dynamic_content:
            context_set.dynamic_context = self.create_dynamic_context(
                content=dynamic_content,
                source="finding",
            )

        return context_set

    def invalidate_category(self, category: str) -> bool:
        """Invalidate cached category context.

        Args:
            category: Category to invalidate

        Returns:
            True if cache was invalidated
        """
        if category in self._category_cache:
            del self._category_cache[category]
            return True
        return False

    def invalidate_all(self) -> None:
        """Invalidate all caches."""
        self._system_cache = None
        self._category_cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache status information
        """
        return {
            "has_system_cache": self._system_cache is not None,
            "system_tokens": (
                self._system_cache.token_estimate if self._system_cache else 0
            ),
            "category_count": len(self._category_cache),
            "categories_cached": list(self._category_cache.keys()),
            "total_category_tokens": sum(
                c.token_estimate for c in self._category_cache.values()
            ),
            "version": self.version,
        }

    def estimate_cache_savings(
        self,
        context_set: CachedContextSet,
        calls_per_session: int = 10,
    ) -> Dict[str, Any]:
        """Estimate cache savings for a context set.

        Args:
            context_set: Context set to analyze
            calls_per_session: Expected API calls per session

        Returns:
            Dict with savings estimates
        """
        cacheable_tokens = 0
        uncacheable_tokens = 0

        if context_set.system_context:
            cacheable_tokens += context_set.system_context.token_estimate

        for cat_ctx in context_set.category_contexts:
            cacheable_tokens += cat_ctx.token_estimate

        if context_set.dynamic_context:
            uncacheable_tokens += context_set.dynamic_context.token_estimate

        # With caching, cacheable tokens are only charged once
        # Without caching, all tokens charged every call
        total_without_cache = (
            (cacheable_tokens + uncacheable_tokens) * calls_per_session
        )
        total_with_cache = cacheable_tokens + (uncacheable_tokens * calls_per_session)

        savings = total_without_cache - total_with_cache
        savings_percent = (savings / total_without_cache * 100) if total_without_cache else 0

        return {
            "cacheable_tokens": cacheable_tokens,
            "uncacheable_tokens": uncacheable_tokens,
            "total_without_cache": total_without_cache,
            "total_with_cache": total_with_cache,
            "savings_tokens": savings,
            "savings_percent": round(savings_percent, 1),
            "calls_assumed": calls_per_session,
        }


# =============================================================================
# Convenience Functions
# =============================================================================

_default_cache_manager: Optional[PromptCacheManager] = None


def get_cache_manager() -> PromptCacheManager:
    """Get or create default cache manager."""
    global _default_cache_manager
    if _default_cache_manager is None:
        _default_cache_manager = PromptCacheManager()
    return _default_cache_manager


def set_cache_manager(manager: PromptCacheManager) -> None:
    """Set the default cache manager."""
    global _default_cache_manager
    _default_cache_manager = manager
