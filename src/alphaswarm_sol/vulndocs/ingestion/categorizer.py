"""Auto-categorization for URL ingestion.

Categorizes extracted vulnerability content into the vulndocs/ hierarchy
using keyword matching and semantic analysis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alphaswarm_sol.vulndocs.ingestion.extractor import ExtractedContent


@dataclass
class VulndocPath:
    """Target path in vulndocs hierarchy."""

    category: str
    subcategory: str

    @property
    def path(self) -> str:
        """Return the relative path."""
        return f"{self.category}/{self.subcategory}"

    def to_path(self, root: Path) -> Path:
        """Convert to absolute path given vulndocs root."""
        return root / self.category / self.subcategory

    def exists(self, root: Path) -> bool:
        """Check if this path already exists."""
        return self.to_path(root).exists()


@dataclass
class CategoryScore:
    """Score for a category match."""

    category: str
    score: float
    matched_keywords: list[str] = field(default_factory=list)
    confidence: str = "low"  # low, medium, high

    def __post_init__(self) -> None:
        """Set confidence based on score."""
        if self.score >= 0.7:
            self.confidence = "high"
        elif self.score >= 0.4:
            self.confidence = "medium"
        else:
            self.confidence = "low"


class Categorizer:
    """Auto-categorization of vulnerability content into vulndocs hierarchy.

    Uses keyword matching with optional semantic analysis to determine
    the best category and suggest subcategory names.

    Example:
        categorizer = Categorizer()
        path = categorizer.categorize(extracted_content)
        print(f"Category: {path.category}, Subcategory: {path.subcategory}")
    """

    # Category keywords for matching
    # Each category has primary keywords (high weight) and secondary (lower weight)
    CATEGORY_KEYWORDS: dict[str, dict[str, list[str]]] = {
        "reentrancy": {
            "primary": ["reentrancy", "reentrant", "reentering", "re-enter"],
            "secondary": ["callback", "CEI", "checks-effects-interactions", "nonReentrant"],
        },
        "oracle": {
            "primary": ["oracle", "price feed", "chainlink", "price manipulation"],
            "secondary": ["twap", "stale price", "heartbeat", "updatedAt", "latestAnswer"],
        },
        "access-control": {
            "primary": ["access control", "authorization", "permission", "privilege"],
            "secondary": ["admin", "owner", "onlyOwner", "modifier", "role", "hasRole"],
        },
        "arithmetic": {
            "primary": ["overflow", "underflow", "integer overflow", "arithmetic"],
            "secondary": ["precision", "rounding", "division", "mulDiv", "unchecked"],
        },
        "flash-loan": {
            "primary": ["flash loan", "flash mint", "flashloan"],
            "secondary": ["atomic arbitrage", "flash", "instant borrow"],
        },
        "dos": {
            "primary": ["denial of service", "DoS", "gas griefing"],
            "secondary": ["unbounded loop", "gas limit", "out of gas", "block gas"],
        },
        "governance": {
            "primary": ["governance", "voting", "proposal", "DAO"],
            "secondary": ["timelock", "quorum", "vote", "delegate", "snapshot"],
        },
        "token": {
            "primary": ["ERC20", "ERC721", "ERC1155", "token"],
            "secondary": ["transfer", "approval", "allowance", "safeTransfer", "mint", "burn"],
        },
        "upgrade": {
            "primary": ["proxy", "upgrade", "UUPS", "upgradeable"],
            "secondary": ["transparent", "diamond", "beacon", "implementation", "delegatecall"],
        },
        "vault": {
            "primary": ["vault", "deposit", "withdrawal", "share"],
            "secondary": ["inflation", "ERC4626", "totalAssets", "convertToShares"],
        },
        "cross-chain": {
            "primary": ["bridge", "cross-chain", "crosschain", "LayerZero"],
            "secondary": ["message passing", "relay", "finality", "L1", "L2"],
        },
        "logic": {
            "primary": ["business logic", "logic error", "state machine"],
            "secondary": ["invariant", "condition", "edge case", "assumption"],
        },
        "mev": {
            "primary": ["MEV", "frontrun", "frontrunning", "sandwich"],
            "secondary": ["backrun", "arbitrage", "sequencer", "mempool"],
        },
        "crypto": {
            "primary": ["signature", "ECDSA", "cryptographic", "ecrecover"],
            "secondary": ["keccak", "hash collision", "randomness", "VRF", "commit-reveal"],
        },
        "precision-loss": {
            "primary": ["precision loss", "precision error", "decimal"],
            "secondary": ["truncation", "rounding error", "significant digits"],
        },
        "restaking": {
            "primary": ["restaking", "liquid staking", "LST"],
            "secondary": ["validator", "slash", "stETH", "rETH", "EigenLayer"],
        },
        "account-abstraction": {
            "primary": ["ERC-4337", "account abstraction", "AA"],
            "secondary": ["paymaster", "bundler", "UserOperation", "entrypoint"],
        },
        "zk-rollup": {
            "primary": ["zkSNARK", "zkSTARK", "zero knowledge", "ZK"],
            "secondary": ["validity proof", "data availability", "zkEVM", "prover"],
        },
    }

    # Keywords that indicate the content should go to uncategorized
    UNCATEGORIZED_KEYWORDS = ["general", "miscellaneous", "other"]

    def __init__(self, vulndocs_root: Path | None = None):
        """Initialize categorizer.

        Args:
            vulndocs_root: Path to vulndocs directory for existence checks.
        """
        if vulndocs_root is not None:
            self.vulndocs_root = vulndocs_root
        else:
            from alphaswarm_sol.vulndocs.resolution import vulndocs_write_path
            self.vulndocs_root = vulndocs_write_path()

    def categorize(
        self,
        content: "ExtractedContent",
        hint: str | None = None,
    ) -> VulndocPath:
        """Categorize extracted content into vulndocs hierarchy.

        Args:
            content: Extracted vulnerability content.
            hint: Optional category hint (overrides auto-detection).

        Returns:
            VulndocPath with category and subcategory.
        """
        # If hint provided, validate and use it
        if hint:
            validated = self._validate_category(hint)
            if validated:
                return VulndocPath(
                    category=validated,
                    subcategory=self._suggest_subcategory(content),
                )

        # Score all categories
        scores = self._score_categories(content)

        # Get best match
        if not scores:
            return VulndocPath(
                category="uncategorized",
                subcategory=self._suggest_subcategory(content),
            )

        best = max(scores, key=lambda s: s.score)

        # If confidence too low, use uncategorized
        if best.score < 0.3:
            return VulndocPath(
                category="uncategorized",
                subcategory=self._suggest_subcategory(content),
            )

        return VulndocPath(
            category=best.category,
            subcategory=self._suggest_subcategory(content),
        )

    def score_categories(self, content: "ExtractedContent") -> list[CategoryScore]:
        """Get scores for all categories (for debugging/explanation).

        Args:
            content: Extracted vulnerability content.

        Returns:
            List of CategoryScore sorted by score descending.
        """
        scores = self._score_categories(content)
        return sorted(scores, key=lambda s: s.score, reverse=True)

    def _score_categories(self, content: "ExtractedContent") -> list[CategoryScore]:
        """Score each category based on keyword matching.

        Args:
            content: Extracted vulnerability content.

        Returns:
            List of CategoryScore for categories with matches.
        """
        # Combine all searchable text
        search_text = self._get_searchable_text(content)
        search_text_lower = search_text.lower()

        scores: list[CategoryScore] = []

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            primary = keywords.get("primary", [])
            secondary = keywords.get("secondary", [])

            # Score primary keywords (weight: 2.0)
            primary_matches = [
                kw for kw in primary if kw.lower() in search_text_lower
            ]
            primary_score = len(primary_matches) * 2.0

            # Score secondary keywords (weight: 1.0)
            secondary_matches = [
                kw for kw in secondary if kw.lower() in search_text_lower
            ]
            secondary_score = len(secondary_matches) * 1.0

            total_score = primary_score + secondary_score

            if total_score > 0:
                # Normalize score (max ~10 for excellent match)
                normalized = min(total_score / 5.0, 1.0)
                scores.append(
                    CategoryScore(
                        category=category,
                        score=normalized,
                        matched_keywords=primary_matches + secondary_matches,
                    )
                )

        return scores

    def _get_searchable_text(self, content: "ExtractedContent") -> str:
        """Get all searchable text from extracted content.

        Args:
            content: Extracted vulnerability content.

        Returns:
            Combined text for keyword matching.
        """
        parts = [
            content.vulnerability_type or "",
            content.suggested_name or "",
            content.description or "",
        ]

        # Add semantic operations
        if content.semantic_ops:
            parts.extend(content.semantic_ops)

        # Add pattern descriptions
        for pattern in content.patterns:
            if pattern.description:
                parts.append(pattern.description)

        return " ".join(parts)

    def _validate_category(self, hint: str) -> str | None:
        """Validate a category hint.

        Args:
            hint: Category name to validate.

        Returns:
            Normalized category name if valid, None otherwise.
        """
        # Normalize hint
        normalized = hint.lower().strip().replace(" ", "-").replace("_", "-")

        # Check if it's a known category
        if normalized in self.CATEGORY_KEYWORDS:
            return normalized

        # Check for close matches (handle common variations)
        variations = {
            "reentrant": "reentrancy",
            "access": "access-control",
            "accesscontrol": "access-control",
            "overflow": "arithmetic",
            "underflow": "arithmetic",
            "flashloan": "flash-loan",
            "denialofservice": "dos",
            "erc20": "token",
            "erc721": "token",
            "nft": "token",
            "upgradeable": "upgrade",
            "proxy": "upgrade",
            "crosschain": "cross-chain",
            "bridge": "cross-chain",
            "frontrun": "mev",
            "sandwich": "mev",
            "signature": "crypto",
            "random": "crypto",
            "precision": "precision-loss",
            "rounding": "precision-loss",
            "restake": "restaking",
            "aa": "account-abstraction",
            "zk": "zk-rollup",
        }

        return variations.get(normalized)

    def _suggest_subcategory(self, content: "ExtractedContent") -> str:
        """Suggest a subcategory name from content.

        Args:
            content: Extracted vulnerability content.

        Returns:
            Suggested subcategory in kebab-case.
        """
        # Use suggested_name if available
        if content.suggested_name:
            return self._to_kebab_case(content.suggested_name)

        # Fall back to vulnerability_type
        if content.vulnerability_type:
            return self._to_kebab_case(content.vulnerability_type)

        # Last resort: use part of description
        if content.description:
            # Take first few words
            words = content.description.split()[:3]
            return self._to_kebab_case(" ".join(words))

        return "unknown"

    def _to_kebab_case(self, text: str) -> str:
        """Convert text to kebab-case.

        Args:
            text: Input text.

        Returns:
            Kebab-case version.
        """
        # Remove special characters
        text = re.sub(r"[^\w\s-]", "", text)
        # Replace spaces and underscores with hyphens
        text = re.sub(r"[\s_]+", "-", text)
        # Convert to lowercase
        text = text.lower()
        # Remove consecutive hyphens
        text = re.sub(r"-+", "-", text)
        # Remove leading/trailing hyphens
        text = text.strip("-")
        return text
