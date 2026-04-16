"""
Semantic Compressor

Converts function data to minimal token-efficient representations.
Implements 5-tier progressive compression strategy.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Dict, Any, List


class CompressionTier(IntEnum):
    """Compression tiers with increasing detail."""
    PROPERTIES = 1      # ~50 tokens
    BEHAVIORAL = 2      # ~75 tokens
    PATTERNS = 3        # ~150 tokens
    CRITICAL_LINES = 4  # ~300 tokens
    FULL = 5            # ~2000+ tokens


@dataclass
class CompressedContext:
    """Token-efficient function representation."""
    tier: CompressionTier
    compressed: str
    token_estimate: int
    original_tokens: int

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        return self.original_tokens / max(self.token_estimate, 1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier": self.tier.value,
            "tier_name": self.tier.name,
            "compressed": self.compressed,
            "token_estimate": self.token_estimate,
            "original_tokens": self.original_tokens,
            "compression_ratio": f"{self.compression_ratio:.1f}x",
        }


class SemanticCompressor:
    """Compress function context to token-efficient representation."""

    def compress(
        self,
        fn_node: Dict[str, Any],
        budget: int,
        kg: Optional[object] = None
    ) -> CompressedContext:
        """
        Compress function to fit within token budget.

        Args:
            fn_node: Function node with properties
            budget: Maximum tokens allowed
            kg: Optional knowledge graph for additional context

        Returns:
            CompressedContext with appropriate tier
        """
        # Estimate original token count
        original = self._estimate_full_tokens(fn_node)

        # Build progressively until budget
        tier = CompressionTier.PROPERTIES
        compressed = self._tier_1_properties(fn_node)
        tokens = self._count_tokens(compressed)

        if budget >= 75 and tokens < budget:
            tier = CompressionTier.BEHAVIORAL
            compressed = self._add_tier_2_behavioral(compressed, fn_node)
            tokens = self._count_tokens(compressed)

        if budget >= 150 and tokens < budget:
            tier = CompressionTier.PATTERNS
            compressed = self._add_tier_3_patterns(compressed, fn_node, kg)
            tokens = self._count_tokens(compressed)

        if budget >= 300 and tokens < budget:
            tier = CompressionTier.CRITICAL_LINES
            compressed = self._add_tier_4_lines(compressed, fn_node)
            tokens = self._count_tokens(compressed)

        if budget >= 1000 and tokens < budget:
            tier = CompressionTier.FULL
            compressed = self._add_tier_5_full(compressed, fn_node, kg)
            tokens = self._count_tokens(compressed)

        return CompressedContext(
            tier=tier,
            compressed=compressed,
            token_estimate=tokens,
            original_tokens=original
        )

    def _tier_1_properties(self, fn_node: Dict[str, Any]) -> str:
        """Core properties only (~50 tokens)."""
        p = fn_node.get("properties", {})
        parts = [
            f"fn:{fn_node.get('name', 'unknown')}",
            f"vis:{p.get('visibility', '?')}",
            f"mut:{p.get('state_mutability', '?')}",
            f"gates:[{','.join(p.get('modifiers', [])) or 'none'}]",
            f"writes:[{','.join(p.get('state_vars_written', [])) or 'none'}]",
            f"reads:[{','.join(p.get('state_vars_read', [])) or 'none'}]",
            f"calls:[{'external' if p.get('has_external_calls') else 'none'}]",
            f"value:{str(p.get('transfers_value', False)).lower()}"
        ]
        return "|".join(parts)

    def _add_tier_2_behavioral(self, base: str, fn_node: Dict[str, Any]) -> str:
        """Add behavioral signature (~25 tokens more)."""
        p = fn_node.get("properties", {})
        sig = p.get("behavioral_signature", "unknown")
        ops = p.get("operations", [])
        cei = p.get("follows_cei_pattern", False)
        risk = p.get("reentrancy_risk_score", 0)

        additions = [
            f"sig:{sig}",
            f"ops:[{','.join(ops[:5])}]",  # Limit to top 5 ops
            f"cei:{str(cei).lower()}",
            f"reent_risk:{risk:.2f}"
        ]
        return base + "|" + "|".join(additions)

    def _add_tier_3_patterns(
        self, base: str, fn_node: Dict[str, Any], kg: Optional[object]
    ) -> str:
        """Add pattern matches (~75 tokens more)."""
        patterns = fn_node.get("matched_patterns", [])
        pattern_strs = [f"{p.get('id', '?')}({p.get('score', 0):.2f})" for p in patterns[:3]]

        cross_graph = fn_node.get("cross_graph_links", [])
        cross_strs = [f"{c.get('spec', '?')}:{c.get('requirement', '?')}" for c in cross_graph[:2]]

        similar = fn_node.get("similar_vulns", [])[:2]

        additions = [
            f"patterns:[{','.join(pattern_strs) or 'none'}]",
            f"specs:[{','.join(cross_strs) or 'none'}]",
            f"similar:[{','.join(similar) or 'none'}]"
        ]
        return base + "|" + "|".join(additions)

    def _add_tier_4_lines(self, base: str, fn_node: Dict[str, Any]) -> str:
        """Add critical code lines (~150 tokens more)."""
        critical = fn_node.get("critical_lines", [])
        line_strs = [f"L{l.get('line', '?')}:{l.get('code', '')[:50]}" for l in critical[:5]]

        if line_strs:
            return base + "|lines:[" + ",".join(line_strs) + "]"
        return base

    def _add_tier_5_full(
        self, base: str, fn_node: Dict[str, Any], kg: Optional[object]
    ) -> str:
        """Add full source and subgraph (~1700 tokens more)."""
        source = fn_node.get("source_code", "")

        # Truncate if needed
        if len(source) > 3000:
            source = source[:3000] + "...[truncated]"

        return base + f"|source:{source}"

    def _count_tokens(self, text: str) -> int:
        """Estimate token count (rough heuristic: 4 chars per token for code)."""
        return len(text) // 4

    def _estimate_full_tokens(self, fn_node: Dict[str, Any]) -> int:
        """Estimate tokens for full uncompressed context."""
        source = fn_node.get("source_code", "")
        props = str(fn_node.get("properties", {}))
        return (len(source) + len(props)) // 4
