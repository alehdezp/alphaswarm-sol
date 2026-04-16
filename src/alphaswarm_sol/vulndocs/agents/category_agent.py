"""Category Agent for Multi-Model Pipeline.

Task 18.2: Haiku-powered agent for processing a single vulnerability category.

The CategoryAgent:
1. Receives crawled sources for a category (e.g., "reentrancy")
2. Spawns SubcategoryWorkers in parallel (one per subcategory)
3. Aggregates results for the MergeOrchestrator
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from alphaswarm_sol.vulndocs.agents.base import (
    AgentConfig,
    AgentModel,
    AgentResult,
    BaseAgent,
    SubagentCoordinator,
    SubagentTask,
)
from alphaswarm_sol.vulndocs.knowledge_doc import SourceSummary

logger = logging.getLogger(__name__)


@dataclass
class CategorySource:
    """A source document for a category."""

    url: str
    content: str
    source_name: str = ""
    source_authority: float = 0.5
    content_path: str = ""
    doc_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_content(self) -> str:
        """Load content, preferring in-memory text then local snapshot."""
        if self.content:
            return self.content
        if self.content_path:
            try:
                return Path(self.content_path).read_text(encoding="utf-8")
            except OSError:
                return ""
        return ""


@dataclass
class SubcategoryResult:
    """Result from processing a subcategory."""

    subcategory: str
    summaries: List[SourceSummary]
    unique_ideas: List[str]
    source_count: int


@dataclass
class CategoryResult:
    """Result from processing an entire category."""

    category: str
    subcategory_results: List[SubcategoryResult]
    total_sources: int
    total_summaries: int


# Vulnerability taxonomy - subcategories per category
CATEGORY_SUBCATEGORIES: Dict[str, List[str]] = {
    "reentrancy": [
        "classic-reentrancy",
        "cross-function-reentrancy",
        "cross-contract-reentrancy",
        "read-only-reentrancy",
        "erc721-reentrancy",
        "erc1155-reentrancy",
        "governor-reentrancy",
    ],
    "access-control": [
        "missing-access-control",
        "incorrect-modifier",
        "tx-origin-authentication",
        "unprotected-initializer",
        "privilege-escalation",
        "role-misconfiguration",
        "centralization-risk",
    ],
    "oracle": [
        "spot-price-manipulation",
        "twap-manipulation",
        "stale-price-data",
        "oracle-frontrunning",
        "flash-loan-oracle-attack",
        "multi-oracle-inconsistency",
    ],
    "flash-loan": [
        "price-manipulation",
        "governance-attack",
        "liquidation-attack",
        "arbitrage-exploit",
        "collateral-manipulation",
    ],
    "mev": [
        "sandwich-attack",
        "frontrunning",
        "backrunning",
        "time-bandit-attack",
        "jit-liquidity",
    ],
    "arithmetic": [
        "integer-overflow",
        "integer-underflow",
        "precision-loss",
        "phantom-overflow",
        "first-depositor-inflation",
        "fee-on-transfer-tokens",
    ],
    "signature": [
        "signature-replay",
        "signature-malleability",
        "missing-nonce",
        "cross-chain-replay",
        "ecrecover-zero-address",
        "permit-frontrunning",
    ],
    "upgrade": [
        "storage-collision",
        "uninitialized-proxy",
        "function-selector-clash",
        "delegatecall-to-untrusted",
        "selfdestruct-in-impl",
        "implementation-takeover",
        "upgrade-without-timelock",
    ],
    "dos": [
        "unbounded-loop",
        "block-gas-limit",
        "external-call-dos",
        "gas-griefing",
        "selfdestruct-dos",
        "storage-dos",
    ],
    "governance": [
        "flash-loan-voting",
        "proposal-spam",
        "quorum-manipulation",
        "timelock-bypass",
        "snapshot-manipulation",
        "bribery-attack",
    ],
    "bridge": [
        "message-replay",
        "validator-compromise",
        "merkle-proof-forgery",
        "finality-assumption",
        "token-mapping-error",
    ],
    "lending": [
        "bad-debt-accumulation",
        "liquidation-manipulation",
        "interest-rate-manipulation",
        "collateral-factor-abuse",
        "empty-pool-attack",
    ],
    "token": [
        "fee-on-transfer",
        "rebasing-token",
        "pausable-token",
        "blocklist-token",
        "upgradeable-token",
        "erc20-return-value",
    ],
    "crypto": [
        "weak-randomness",
        "hash-collision",
        "ecdsa-malleability",
        "insecure-ecrecover",
    ],
    "logic": [
        "business-logic-flaw",
        "state-machine-violation",
        "invariant-violation",
        "off-by-one",
        "unchecked-return-value",
    ],
}


def get_subcategories(category: str) -> List[str]:
    """Get subcategories for a category.

    Args:
        category: Category name

    Returns:
        List of subcategory names
    """
    return CATEGORY_SUBCATEGORIES.get(category, [])


def get_all_categories() -> List[str]:
    """Get all category names.

    Returns:
        List of category names
    """
    return list(CATEGORY_SUBCATEGORIES.keys())


class CategoryAgent(BaseAgent):
    """Haiku-powered agent for processing a single category.

    Spawns subcategory workers for parallel processing.
    """

    def __init__(
        self,
        category: str,
        config: Optional[AgentConfig] = None,
        worker_class: Optional[type] = None,
    ):
        """Initialize the category agent.

        Args:
            category: Category to process (e.g., "reentrancy")
            config: Agent configuration
            worker_class: SubcategoryWorker class to use
        """
        config = config or AgentConfig.for_haiku_worker()
        super().__init__(name=f"category-{category}", config=config)

        self.category = category
        self.subcategories = get_subcategories(category)
        self.max_workers = min(len(self.subcategories), 7)  # One per subcategory
        self.worker_class = worker_class

        # Import here to avoid circular import
        if self.worker_class is None:
            from alphaswarm_sol.vulndocs.agents.subcategory_worker import SubcategoryWorker

            self.worker_class = SubcategoryWorker

    async def process(self, input_data: Any) -> AgentResult[CategoryResult]:
        """Process all sources for this category.

        Args:
            input_data: List of CategorySource objects

        Returns:
            CategoryResult with subcategory processing results
        """
        sources: List[CategorySource] = input_data

        if not sources:
            return AgentResult.failure_result("No sources provided")

        self.log(f"Processing {len(sources)} sources for {self.category}")

        # Classify sources by subcategory
        classified = await self._classify_sources(sources)

        # Spawn parallel workers for each subcategory
        coordinator = SubagentCoordinator(max_concurrent=self.max_workers)

        for subcategory, subcategory_sources in classified.items():
            worker = self.worker_class(
                category=self.category,
                subcategory=subcategory,
            )
            coordinator.register_agent(worker)
            coordinator.add_task(
                SubagentTask(
                    task_id=f"{self.category}-{subcategory}",
                    agent_name=worker.name,
                    input_data=subcategory_sources,
                )
            )

        # Execute all workers in parallel
        results = await coordinator.execute_all()

        # Aggregate results
        subcategory_results = []
        for task_id, result in results.items():
            if result.success and result.data:
                subcategory_results.append(result.data)

        category_result = CategoryResult(
            category=self.category,
            subcategory_results=subcategory_results,
            total_sources=len(sources),
            total_summaries=sum(r.source_count for r in subcategory_results),
        )

        self.log(
            f"Completed {self.category}: {len(subcategory_results)} subcategories, "
            f"{category_result.total_summaries} summaries"
        )

        return AgentResult.success_result(category_result)

    async def _classify_sources(
        self, sources: List[CategorySource]
    ) -> Dict[str, List[CategorySource]]:
        """Classify sources into subcategories.

        Uses keyword matching and content analysis to determine
        which subcategory each source belongs to.

        Args:
            sources: List of sources to classify

        Returns:
            Dictionary of subcategory -> sources
        """
        classified: Dict[str, List[CategorySource]] = {
            sub: [] for sub in self.subcategories
        }

        # Subcategory keywords for classification
        subcategory_keywords = self._get_subcategory_keywords()

        for source in sources:
            content_lower = source.get_content().lower()
            best_match = None
            best_score = 0

            for subcategory, keywords in subcategory_keywords.items():
                score = sum(1 for kw in keywords if kw in content_lower)
                if score > best_score:
                    best_score = score
                    best_match = subcategory

            if best_match and best_score > 0:
                classified[best_match].append(source)
            else:
                # Default to first subcategory if no match
                if self.subcategories:
                    classified[self.subcategories[0]].append(source)

        # Remove empty subcategories
        return {k: v for k, v in classified.items() if v}

    def _get_subcategory_keywords(self) -> Dict[str, List[str]]:
        """Get keywords for each subcategory.

        Returns:
            Dictionary of subcategory -> keywords
        """
        # Base keywords by category
        if self.category == "reentrancy":
            return {
                "classic-reentrancy": [
                    "classic reentrancy",
                    "state after call",
                    "external call",
                    "call before state",
                ],
                "cross-function-reentrancy": [
                    "cross function",
                    "cross-function",
                    "multiple functions",
                    "shared state",
                ],
                "cross-contract-reentrancy": [
                    "cross contract",
                    "cross-contract",
                    "multiple contracts",
                    "inter-contract",
                ],
                "read-only-reentrancy": [
                    "read only",
                    "read-only",
                    "view function",
                    "oracle manipulation",
                ],
                "erc721-reentrancy": [
                    "erc721",
                    "erc-721",
                    "nft",
                    "onERC721Received",
                ],
                "erc1155-reentrancy": [
                    "erc1155",
                    "erc-1155",
                    "multi-token",
                    "onERC1155Received",
                ],
                "governor-reentrancy": [
                    "governor",
                    "governance",
                    "proposal",
                    "voting callback",
                ],
            }
        elif self.category == "access-control":
            return {
                "missing-access-control": [
                    "missing access",
                    "no access control",
                    "public function",
                    "unprotected",
                ],
                "incorrect-modifier": [
                    "incorrect modifier",
                    "wrong modifier",
                    "modifier logic",
                    "bypassed modifier",
                ],
                "tx-origin-authentication": [
                    "tx.origin",
                    "tx origin",
                    "origin authentication",
                    "phishing",
                ],
                "unprotected-initializer": [
                    "initializer",
                    "initialize",
                    "constructor",
                    "upgradeable",
                ],
                "privilege-escalation": [
                    "privilege",
                    "escalation",
                    "admin",
                    "owner takeover",
                ],
                "role-misconfiguration": [
                    "role",
                    "rbac",
                    "access role",
                    "permission",
                ],
                "centralization-risk": [
                    "centralization",
                    "single admin",
                    "owner risk",
                    "multisig",
                ],
            }
        elif self.category == "oracle":
            return {
                "spot-price-manipulation": [
                    "spot price",
                    "price manipulation",
                    "reserve ratio",
                    "instant price",
                ],
                "twap-manipulation": [
                    "twap",
                    "time weighted",
                    "time-weighted",
                    "average price",
                ],
                "stale-price-data": [
                    "stale",
                    "outdated",
                    "timestamp check",
                    "price freshness",
                ],
                "oracle-frontrunning": [
                    "frontrun",
                    "front-run",
                    "oracle update",
                    "price update",
                ],
                "flash-loan-oracle-attack": [
                    "flash loan",
                    "flashloan",
                    "single block",
                    "same transaction",
                ],
                "multi-oracle-inconsistency": [
                    "multi oracle",
                    "multiple oracle",
                    "oracle disagreement",
                    "price deviation",
                ],
            }
        # Default: use subcategory name as keyword
        return {sub: [sub.replace("-", " ")] for sub in self.subcategories}

    def get_prompt_template(self, template_name: str) -> str:
        """Get prompt template for classification.

        Args:
            template_name: Template name

        Returns:
            Template string
        """
        if template_name == "classify":
            return """Classify this vulnerability content into a subcategory.

Category: {category}
Available Subcategories: {subcategories}

Content:
{content}

Which subcategory best matches this content?
Respond with just the subcategory name."""

        return ""
