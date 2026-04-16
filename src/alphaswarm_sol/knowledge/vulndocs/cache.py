"""VulnDocs Prompt Cache Integration.

Phase 17.5: Prompt Cache Integration for VulnDocs.

This module provides prompt caching functionality for the VulnDocs knowledge
base. It enables efficient LLM interactions by caching knowledge blocks that
can be reused across multiple queries.

Features:
1. CachedBlock dataclass for managing cached content with metadata
2. PromptCache class for cache operations (get, set, invalidate, stats)
3. LLM provider formatting (Anthropic cache_control, OpenAI compatible)
4. Token estimation for content blocks
5. Preload functions for efficient batch loading

Usage:
    from alphaswarm_sol.knowledge.vulndocs import KnowledgeNavigator
    from alphaswarm_sol.knowledge.vulndocs.cache import PromptCache, CachedBlock

    # Initialize
    navigator = KnowledgeNavigator()
    cache = PromptCache(navigator)

    # Preload category knowledge
    blocks = cache.preload_category("reentrancy")

    # Format for Anthropic API
    messages = cache.format_for_anthropic(blocks)

    # Get cache statistics
    stats = cache.get_cache_stats()
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from alphaswarm_sol.knowledge.vulndocs.schema import (
    CacheConfig,
    CacheControlType,
    DocumentType,
    KnowledgeDepth,
)

if TYPE_CHECKING:
    from alphaswarm_sol.knowledge.vulndocs.navigator import KnowledgeNavigator


# =============================================================================
# CONSTANTS
# =============================================================================

# Default token estimation: ~4 characters per token (conservative estimate)
CHARS_PER_TOKEN = 4

# Minimum tokens for cache_control to be effective (Anthropic requirement)
MIN_TOKENS_FOR_CACHE = 1024

# Maximum cache entries to prevent memory bloat
MAX_CACHE_ENTRIES = 1000


# =============================================================================
# CACHED BLOCK DATACLASS
# =============================================================================


@dataclass
class CachedBlock:
    """A cached content block for prompt caching.

    Represents a piece of knowledge that can be cached and reused across
    multiple LLM interactions.

    Attributes:
        key: Unique cache key identifying this block.
        content: The cached content string (markdown format).
        cache_type: Cache control type (static, ephemeral, or none).
        created_at: Timestamp when the block was created.
        last_accessed: Timestamp of last access.
        access_count: Number of times this block has been accessed.
        estimated_tokens: Estimated token count for this content.
    """

    key: str
    content: str
    cache_type: CacheControlType
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    estimated_tokens: int = 0

    def __post_init__(self):
        """Calculate token estimate if not provided."""
        if self.estimated_tokens == 0 and self.content:
            self.estimated_tokens = estimate_tokens(self.content)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "key": self.key,
            "content": self.content,
            "cache_type": self.cache_type.value,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "estimated_tokens": self.estimated_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedBlock":
        """Deserialize from dictionary."""
        cache_type = data.get("cache_type", "none")
        if isinstance(cache_type, str):
            cache_type = CacheControlType(cache_type)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        last_accessed = data.get("last_accessed")
        if isinstance(last_accessed, str):
            last_accessed = datetime.fromisoformat(last_accessed)
        elif last_accessed is None:
            last_accessed = datetime.now()

        return cls(
            key=data.get("key", ""),
            content=data.get("content", ""),
            cache_type=cache_type,
            created_at=created_at,
            last_accessed=last_accessed,
            access_count=data.get("access_count", 0),
            estimated_tokens=data.get("estimated_tokens", 0),
        )

    def touch(self) -> None:
        """Update access time and increment access count."""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def is_cacheable(self) -> bool:
        """Check if this block meets minimum requirements for caching."""
        return (
            self.cache_type != CacheControlType.NONE
            and self.estimated_tokens >= MIN_TOKENS_FOR_CACHE
        )


# =============================================================================
# PROMPT CACHE CLASS
# =============================================================================


class PromptCache:
    """Manager for prompt caching of VulnDocs knowledge.

    Provides efficient caching of knowledge blocks for LLM interactions,
    with support for different cache control types and LLM provider formatting.

    Attributes:
        navigator: KnowledgeNavigator instance for loading knowledge.
        _cache: Internal cache dictionary.
        _hits: Cache hit counter.
        _misses: Cache miss counter.
    """

    def __init__(self, navigator: "KnowledgeNavigator") -> None:
        """Initialize the prompt cache.

        Args:
            navigator: KnowledgeNavigator instance for loading knowledge.
        """
        self.navigator = navigator
        self._cache: Dict[str, CachedBlock] = {}
        self._hits: int = 0
        self._misses: int = 0

    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================

    def get_cached_block(self, key: str) -> Optional[CachedBlock]:
        """Get a cached content block by key.

        Args:
            key: The cache key to look up.

        Returns:
            CachedBlock if found, None otherwise.
        """
        block = self._cache.get(key)
        if block is not None:
            block.touch()
            self._hits += 1
            return block
        self._misses += 1
        return None

    def set_cached_block(
        self,
        key: str,
        content: str,
        cache_type: CacheControlType = CacheControlType.EPHEMERAL,
    ) -> CachedBlock:
        """Set a cached content block.

        Args:
            key: The cache key.
            content: The content to cache.
            cache_type: The cache control type.

        Returns:
            The created CachedBlock.
        """
        # Enforce cache size limit
        if len(self._cache) >= MAX_CACHE_ENTRIES and key not in self._cache:
            self._evict_oldest()

        block = CachedBlock(
            key=key,
            content=content,
            cache_type=cache_type,
        )
        self._cache[key] = block
        return block

    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry.

        Args:
            key: The cache key to invalidate.

        Returns:
            True if entry was found and removed, False otherwise.
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def invalidate_all(self) -> int:
        """Invalidate all cache entries.

        Returns:
            Number of entries that were cleared.
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def invalidate_by_prefix(self, prefix: str) -> int:
        """Invalidate all cache entries with keys starting with prefix.

        Args:
            prefix: The key prefix to match.

        Returns:
            Number of entries that were cleared.
        """
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._cache[key]
        return len(keys_to_remove)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache hit/miss statistics.

        Returns:
            Dictionary with cache statistics.
        """
        total_tokens = sum(b.estimated_tokens for b in self._cache.values())
        cacheable_blocks = sum(1 for b in self._cache.values() if b.is_cacheable())

        return {
            "total_entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0.0,
            "total_estimated_tokens": total_tokens,
            "cacheable_blocks": cacheable_blocks,
            "cache_types": {
                "static": sum(1 for b in self._cache.values() if b.cache_type == CacheControlType.STATIC),
                "ephemeral": sum(1 for b in self._cache.values() if b.cache_type == CacheControlType.EPHEMERAL),
                "none": sum(1 for b in self._cache.values() if b.cache_type == CacheControlType.NONE),
            },
        }

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry (LRU policy)."""
        if not self._cache:
            return
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        del self._cache[oldest_key]

    # =========================================================================
    # LLM PROVIDER FORMATTING
    # =========================================================================

    def format_for_anthropic(self, blocks: List[CachedBlock]) -> List[Dict[str, Any]]:
        """Format cached blocks for Anthropic's cache_control API.

        Args:
            blocks: List of CachedBlock objects to format.

        Returns:
            List of message content blocks formatted for Anthropic API.

        Note:
            Blocks with cache_type=NONE or insufficient tokens will not have
            cache_control set.
        """
        result = []
        for block in blocks:
            content_block: Dict[str, Any] = {
                "type": "text",
                "text": block.content,
            }
            # Only add cache_control for cacheable blocks
            if block.is_cacheable():
                content_block["cache_control"] = {
                    "type": block.cache_type.value,
                }
            result.append(content_block)
        return result

    def format_for_openai(self, blocks: List[CachedBlock]) -> List[Dict[str, Any]]:
        """Format cached blocks for OpenAI API.

        Args:
            blocks: List of CachedBlock objects to format.

        Returns:
            List of message content blocks formatted for OpenAI API.

        Note:
            OpenAI doesn't have native cache_control support as of the current
            API version. This method returns simple text blocks that can be
            used with OpenAI's standard message format.
        """
        result = []
        for block in blocks:
            content_block: Dict[str, Any] = {
                "type": "text",
                "text": block.content,
            }
            # Add metadata for potential future OpenAI cache support
            if block.is_cacheable():
                content_block["metadata"] = {
                    "cache_key": block.key,
                    "cache_type": block.cache_type.value,
                }
            result.append(content_block)
        return result

    def format_system_message(self, blocks: List[CachedBlock]) -> str:
        """Format cached blocks as a single system message string.

        Args:
            blocks: List of CachedBlock objects to combine.

        Returns:
            Combined content string suitable for system message.
        """
        return "\n\n---\n\n".join(block.content for block in blocks)

    # =========================================================================
    # PRELOAD FUNCTIONS
    # =========================================================================

    def preload_category(
        self,
        category_id: str,
        depth: KnowledgeDepth = KnowledgeDepth.DETECTION,
    ) -> List[CachedBlock]:
        """Preload all documents for a category.

        Args:
            category_id: The category to preload.
            depth: The depth level for context retrieval.

        Returns:
            List of CachedBlock objects for the category.
        """
        blocks: List[CachedBlock] = []

        try:
            # Load category context
            category_key = generate_cache_key(category_id, None, depth, None)
            cached = self.get_cached_block(category_key)

            if cached is None:
                content = self.navigator.get_context(category_id, depth=depth)
                cached = self.set_cached_block(
                    category_key,
                    content,
                    CacheControlType.EPHEMERAL,
                )
            blocks.append(cached)

            # Load subcategory contexts
            for sub_id in self.navigator.list_subcategories(category_id):
                sub_key = generate_cache_key(category_id, sub_id, depth, None)
                sub_cached = self.get_cached_block(sub_key)

                if sub_cached is None:
                    try:
                        sub_content = self.navigator.get_context(
                            category_id, sub_id, depth=depth
                        )
                        sub_cached = self.set_cached_block(
                            sub_key,
                            sub_content,
                            CacheControlType.EPHEMERAL,
                        )
                    except (ValueError, FileNotFoundError):
                        continue

                blocks.append(sub_cached)

        except (ValueError, FileNotFoundError):
            pass

        return blocks

    def preload_for_finding(
        self,
        pattern_id: str,
        depth: KnowledgeDepth = KnowledgeDepth.DETECTION,
    ) -> List[CachedBlock]:
        """Preload relevant documents for a pattern finding.

        Uses the pattern ID to determine which categories are relevant and
        preloads their knowledge for efficient LLM context.

        Args:
            pattern_id: The pattern ID that triggered the finding.
            depth: The depth level for context retrieval.

        Returns:
            List of CachedBlock objects relevant to the pattern.
        """
        blocks: List[CachedBlock] = []

        # Map pattern prefixes to categories
        pattern_category_map = {
            "reentrancy": ["reentrancy"],
            "auth": ["access-control"],
            "vm": ["reentrancy", "token"],  # value-movement
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
        }

        # Extract prefix from pattern_id
        prefix = pattern_id.split("-")[0].lower() if "-" in pattern_id else pattern_id.lower()

        # Get relevant categories
        categories = pattern_category_map.get(prefix, [])

        # Also check the full pattern ID for category hints
        if not categories:
            for cat_prefix, cats in pattern_category_map.items():
                if cat_prefix in pattern_id.lower():
                    categories.extend(cats)
                    break

        # Preload each relevant category
        seen_keys = set()
        for category_id in categories:
            try:
                cat_key = generate_cache_key(category_id, None, depth, None)
                if cat_key in seen_keys:
                    continue
                seen_keys.add(cat_key)

                cached = self.get_cached_block(cat_key)
                if cached is None:
                    content = self.navigator.get_context(category_id, depth=depth)
                    cached = self.set_cached_block(
                        cat_key,
                        content,
                        CacheControlType.EPHEMERAL,
                    )
                blocks.append(cached)
            except (ValueError, FileNotFoundError):
                continue

        return blocks

    def preload_navigation(self) -> CachedBlock:
        """Preload the navigation context (system-level cache).

        Returns:
            CachedBlock containing navigation context.
        """
        key = "vulndocs-navigation-v1"
        cached = self.get_cached_block(key)

        if cached is None:
            content = self.navigator.get_navigation_context()
            cached = self.set_cached_block(
                key,
                content,
                CacheControlType.STATIC,  # Navigation rarely changes
            )

        return cached

    def preload_from_config(self) -> List[CachedBlock]:
        """Preload blocks based on index.yaml cache configuration.

        Returns:
            List of CachedBlock objects as defined in cache config.
        """
        blocks: List[CachedBlock] = []

        try:
            index = self.navigator.get_index()
            for layer_name, config in index.cache.items():
                if not isinstance(config, CacheConfig):
                    continue

                key = config.key or f"vulndocs-{layer_name}-v1"
                cached = self.get_cached_block(key)

                if cached is None:
                    # Generate content based on layer type
                    if layer_name == "layer_1" or "system" in layer_name.lower():
                        content = self.navigator.get_navigation_context()
                    elif layer_name == "layer_2" or "category" in layer_name.lower():
                        # Combine all category overviews
                        parts = []
                        for cat_id in self.navigator.list_categories():
                            try:
                                ctx = self.navigator.get_context(
                                    cat_id, depth=KnowledgeDepth.OVERVIEW
                                )
                                parts.append(ctx)
                            except (ValueError, FileNotFoundError):
                                continue
                        content = "\n\n---\n\n".join(parts)
                    else:
                        # Default: use the config content description
                        content = config.content

                    cached = self.set_cached_block(
                        key,
                        content,
                        config.cache_control,
                    )

                blocks.append(cached)

        except (ValueError, FileNotFoundError):
            pass

        return blocks


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def estimate_tokens(content: str) -> int:
    """Estimate token count for content.

    Uses a conservative character-based estimation. For more accurate
    estimates, use tiktoken or provider-specific tokenizers.

    Args:
        content: The content string to estimate.

    Returns:
        Estimated token count.
    """
    if not content:
        return 0

    # Simple estimation: ~4 characters per token
    char_estimate = len(content) // CHARS_PER_TOKEN

    # Adjust for whitespace (tokens often break on whitespace)
    whitespace_count = len(re.findall(r'\s+', content))

    # Adjust for code blocks (may have different tokenization)
    code_block_count = content.count("```")

    # Final estimate
    return max(1, char_estimate + (whitespace_count // 4) + (code_block_count * 2))


def generate_cache_key(
    category_id: Optional[str],
    subcategory_id: Optional[str] = None,
    depth: Optional[KnowledgeDepth] = None,
    doc_type: Optional[DocumentType] = None,
) -> str:
    """Generate a deterministic cache key.

    Creates a stable, unique key based on the provided parameters.
    Keys are designed to be human-readable and predictable.

    Args:
        category_id: The category identifier.
        subcategory_id: The subcategory identifier (optional).
        depth: The knowledge depth level (optional).
        doc_type: The document type (optional).

    Returns:
        A deterministic cache key string.

    Examples:
        >>> generate_cache_key("reentrancy")
        'vulndocs-reentrancy-v1'
        >>> generate_cache_key("reentrancy", "classic")
        'vulndocs-reentrancy-classic-v1'
        >>> generate_cache_key("reentrancy", "classic", KnowledgeDepth.DETECTION)
        'vulndocs-reentrancy-classic-detection-v1'
    """
    parts = ["vulndocs"]

    if category_id:
        parts.append(category_id)

    if subcategory_id:
        parts.append(subcategory_id)

    if depth:
        parts.append(depth.value)

    if doc_type:
        parts.append(doc_type.value)

    parts.append("v1")

    return "-".join(parts)


def generate_content_hash(content: str) -> str:
    """Generate a hash for content verification.

    Args:
        content: The content to hash.

    Returns:
        A short hash string (first 12 characters of SHA256).
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def merge_cached_blocks(blocks: List[CachedBlock], separator: str = "\n\n---\n\n") -> CachedBlock:
    """Merge multiple cached blocks into a single block.

    Args:
        blocks: List of CachedBlock objects to merge.
        separator: String to use between blocks.

    Returns:
        A new CachedBlock containing merged content.
    """
    if not blocks:
        return CachedBlock(
            key="merged-empty",
            content="",
            cache_type=CacheControlType.NONE,
        )

    # Combine content
    combined_content = separator.join(b.content for b in blocks)

    # Use most restrictive cache type
    cache_priority = {
        CacheControlType.NONE: 0,
        CacheControlType.EPHEMERAL: 1,
        CacheControlType.STATIC: 2,
    }
    cache_type = min(
        (b.cache_type for b in blocks),
        key=lambda ct: cache_priority.get(ct, 0),
    )

    # Generate merged key
    merged_key = "merged-" + generate_content_hash(combined_content)

    return CachedBlock(
        key=merged_key,
        content=combined_content,
        cache_type=cache_type,
    )
