"""Pattern similarity metrics for learning transfer.

Based on R7.1 research: What makes two findings "similar" for learning purposes.

Key insight: Pattern ID alone is too broad (nonReentrant guard vs no guard both
match vm-001), but function signature is too narrow. We use a multi-tier
approach based on:
1. Pattern ID (base)
2. Modifier presence (strong signal)
3. Guard patterns in code (specific protection)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from alphaswarm_sol.learning.types import SimilarityKey, SimilarityTier


# Common guard patterns to detect
GUARD_PATTERNS = {
    # Reentrancy guards
    "REENTRANCY_GUARD": [
        r"\bnonReentrant\b",
        r"\bReentrancyGuard\b",
        r"\b_locked\b",
        r"\b_notEntered\b",
    ],
    # Access control
    "ACCESS_CONTROL": [
        r"\bonlyOwner\b",
        r"\bonlyRole\b",
        r"\bonlyAdmin\b",
        r"\brequire\s*\(\s*msg\.sender\s*==",
        r"\b_checkRole\b",
        r"\b_checkOwner\b",
    ],
    # Pausable
    "PAUSABLE": [
        r"\bwhenNotPaused\b",
        r"\bPausable\b",
        r"\bpaused\s*\(\s*\)",
    ],
    # Initializable (proxy safety)
    "INITIALIZABLE": [
        r"\binitializer\b",
        r"\bonlyInitializing\b",
        r"\b_disableInitializers\b",
    ],
    # CEI pattern indicators
    "CEI_PATTERN": [
        # Balance update before external call pattern
        r"balances?\s*\[.*\]\s*[-=].*;\s*\n.*\.call",
    ],
}


def extract_guards(code: str) -> str:
    """Extract guard patterns from code.

    Returns a deterministic hash of detected guards.
    This allows matching findings with similar protection mechanisms.

    Args:
        code: Source code to analyze

    Returns:
        Sorted, joined string of detected guards (for hashing)
    """
    if not code:
        return ""

    detected_guards = []

    for guard_name, patterns in GUARD_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                detected_guards.append(guard_name)
                break  # Only add each guard type once

    # Return sorted and joined for deterministic comparison
    return "|".join(sorted(set(detected_guards)))


def hash_guards(guards_str: str) -> str:
    """Create a short hash of guard string.

    Args:
        guards_str: Output from extract_guards()

    Returns:
        Short hash for storage
    """
    if not guards_str:
        return ""
    return hashlib.md5(guards_str.encode()).hexdigest()[:8]


@dataclass
class SimilarityMatch:
    """Result of a similarity match."""

    key: SimilarityKey
    tier: SimilarityTier
    score: float  # 0.0 to 1.0

    def is_strong(self) -> bool:
        """Check if this is a strong (Tier 1) match."""
        return self.tier == SimilarityTier.EXACT


class SimilarityEngine:
    """Engine for finding similar findings.

    Used to:
    1. Transfer FP warnings to similar findings
    2. Aggregate learning events by similarity
    3. Predict likely verdicts based on similar findings
    """

    def __init__(
        self,
        transfer_tier: SimilarityTier = SimilarityTier.STRUCTURAL,
        warn_tier: SimilarityTier = SimilarityTier.PATTERN,
    ):
        """Initialize similarity engine.

        Args:
            transfer_tier: Minimum tier for direct FP transfer
            warn_tier: Minimum tier for soft warnings
        """
        self.transfer_tier = transfer_tier
        self.warn_tier = warn_tier
        self._index: dict[str, list[SimilarityKey]] = {}  # pattern_id -> keys

    def add_key(self, key: SimilarityKey) -> None:
        """Add a similarity key to the index."""
        if key.pattern_id not in self._index:
            self._index[key.pattern_id] = []
        self._index[key.pattern_id].append(key)

    def find_similar(
        self,
        key: SimilarityKey,
        min_tier: SimilarityTier = SimilarityTier.PATTERN,
    ) -> list[SimilarityMatch]:
        """Find all keys similar to the given key.

        Args:
            key: Key to match against
            min_tier: Minimum similarity tier to return

        Returns:
            List of matches sorted by tier (strongest first)
        """
        matches = []

        # Get candidates with same pattern_id
        candidates = self._index.get(key.pattern_id, [])

        for candidate in candidates:
            # Try matching at each tier
            for tier in [SimilarityTier.EXACT, SimilarityTier.STRUCTURAL, SimilarityTier.PATTERN]:
                if tier.value > min_tier.value:
                    continue

                if key.matches(candidate, tier):
                    score = self._calculate_score(key, candidate, tier)
                    matches.append(SimilarityMatch(key=candidate, tier=tier, score=score))
                    break  # Use highest tier match only

        # Sort by tier (lowest value = strongest)
        return sorted(matches, key=lambda m: (m.tier.value, -m.score))

    def should_transfer_fp(self, source_key: SimilarityKey, target_key: SimilarityKey) -> bool:
        """Check if FP from source should transfer to target.

        Args:
            source_key: Key of the confirmed FP
            target_key: Key of the finding to potentially warn

        Returns:
            True if FP warning should transfer
        """
        return source_key.matches(target_key, self.transfer_tier)

    def should_warn(self, source_key: SimilarityKey, target_key: SimilarityKey) -> bool:
        """Check if a soft warning should be shown.

        Args:
            source_key: Key of a known verdict
            target_key: Key of the finding to potentially warn

        Returns:
            True if soft warning should show
        """
        return source_key.matches(target_key, self.warn_tier)

    def _calculate_score(
        self,
        key1: SimilarityKey,
        key2: SimilarityKey,
        tier: SimilarityTier,
    ) -> float:
        """Calculate similarity score between two keys.

        Returns a value between 0.0 and 1.0 based on
        how many features match beyond the tier minimum.
        """
        score = 0.0
        features_checked = 0

        # Pattern ID match (always required)
        if key1.pattern_id == key2.pattern_id:
            score += 0.4
        features_checked += 1

        # Modifier signature match
        if key1.modifier_signature == key2.modifier_signature:
            score += 0.3
        elif key1.modifier_signature and key2.modifier_signature:
            # Partial match - check overlap
            mods1 = set(key1.modifier_signature.split("|"))
            mods2 = set(key2.modifier_signature.split("|"))
            overlap = len(mods1 & mods2) / max(len(mods1 | mods2), 1)
            score += 0.3 * overlap
        features_checked += 1

        # Guard hash match
        if key1.guard_hash == key2.guard_hash:
            score += 0.2
        features_checked += 1

        # Inheritance hash match (bonus)
        if key1.inheritance_hash and key1.inheritance_hash == key2.inheritance_hash:
            score += 0.1
        features_checked += 1

        return min(1.0, score)

    def create_key_from_node(self, node: Any, pattern_id: str) -> SimilarityKey:
        """Create a similarity key from a graph node.

        Args:
            node: KnowledgeGraph node
            pattern_id: Pattern that matched this node

        Returns:
            SimilarityKey for the finding
        """
        # Extract modifiers from node properties
        modifiers = []
        if hasattr(node, "props"):
            modifiers = node.props.get("modifiers", [])
            if isinstance(modifiers, str):
                modifiers = [modifiers]

        # Extract code for guard detection
        code = ""
        if hasattr(node, "props"):
            code = node.props.get("source_code", "")

        # Extract inheritance
        inheritance = []
        if hasattr(node, "props"):
            inheritance = node.props.get("inheritance_chain", [])

        return SimilarityKey(
            pattern_id=pattern_id,
            modifier_signature="|".join(sorted(modifiers)),
            guard_hash=extract_guards(code),
            inheritance_hash="|".join(sorted(inheritance)),
        )
