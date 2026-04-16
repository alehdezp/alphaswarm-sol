"""Exa-based scanner for emerging vulnerability research.

Uses Exa API to discover:
- New vulnerability writeups
- Emerging attack patterns
- Recent security research
- Protocol exploit analyses

Key Design Decisions:
1. NO auto-integration - all discoveries require human review
2. Query-based discovery from curated query list
3. Relevance scoring for prioritization
4. Rate limiting to respect API quotas

Usage:
    scanner = ExaScanner()
    discoveries = await scanner.scan(days_back=7)
    scanner.queue_for_review(discoveries)

CLI:
    uv run alphaswarm vulndocs scan-exa --days 7
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class ExaDiscovery:
    """A discovery from Exa search.

    Represents a URL/article discovered via Exa that may contain
    new vulnerability knowledge for VulnDocs integration.
    """

    url: str
    title: str
    snippet: str
    relevance_score: float
    published_date: Optional[datetime]
    query_matched: str
    category: str = ""

    # Auto-suggested metadata
    suggested_category: str = ""
    suggested_operations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for YAML storage."""
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score,
            "published_date": (
                self.published_date.isoformat() if self.published_date else None
            ),
            "query_matched": self.query_matched,
            "category": self.category,
            "suggested_category": self.suggested_category,
            "suggested_operations": self.suggested_operations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExaDiscovery:
        """Deserialize from dictionary."""
        published_date = data.get("published_date")
        if isinstance(published_date, str):
            published_date = datetime.fromisoformat(published_date)

        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            snippet=data.get("snippet", ""),
            relevance_score=data.get("relevance_score", 0.0),
            published_date=published_date,
            query_matched=data.get("query_matched", ""),
            category=data.get("category", ""),
            suggested_category=data.get("suggested_category", ""),
            suggested_operations=data.get("suggested_operations", []),
        )


class ExaScanner:
    """Scans for emerging vulnerability knowledge via Exa.

    Uses the Exa API to execute curated search queries and discover
    new security research, vulnerability writeups, and exploit analyses.

    Query Management:
    - Queries are loaded from .vrs/vulndocs_reference/exa_queries.yaml
    - Each query targets a specific vulnerability category
    - Queries can be filtered by category for focused scanning

    State Management:
    - Tracks last scan timestamp per query
    - Maintains seen URLs to avoid duplicates
    - Stores state in YAML for human readability
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        api_key: Optional[str] = None,
        queries_file: Optional[Path] = None,
    ):
        """Initialize the Exa scanner.

        Args:
            cache_dir: Directory for state and cache files
            api_key: Exa API key (or use EXA_API_KEY env var)
            queries_file: Path to queries config file
        """
        self.cache_dir = cache_dir or Path(".vrs/discovery")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key or os.environ.get("EXA_API_KEY")
        self.queries_file = queries_file or Path(
            ".vrs/vulndocs_reference/exa_queries.yaml"
        )
        self.state_file = self.cache_dir / "exa_state.yaml"
        self.queue_file = self.cache_dir / "exa_queue.yaml"
        self._load_state()
        self._load_queries()

    def _load_state(self) -> None:
        """Load scanner state."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                self.state = yaml.safe_load(f) or {}
        else:
            self.state = {
                "last_scan": None,
                "scans_completed": 0,
                "total_discoveries": 0,
                "seen_urls": [],
            }

    def _save_state(self) -> None:
        """Save scanner state."""
        with open(self.state_file, "w") as f:
            yaml.dump(self.state, f, default_flow_style=False)

    def _load_queries(self) -> None:
        """Load search queries from config file."""
        self.queries: list[dict[str, Any]] = []

        if not self.queries_file.exists():
            # Use default queries if file doesn't exist
            self.queries = self._get_default_queries()
            return

        with open(self.queries_file) as f:
            config = yaml.safe_load(f) or {}

        # Extract queries from various sections
        for section in ["novel_vulnerabilities", "source_discovery"]:
            section_data = config.get(section, {})

            if isinstance(section_data, list):
                self.queries.extend(section_data)
            elif isinstance(section_data, dict):
                # Handle nested category structure
                for category, queries in section_data.items():
                    if isinstance(queries, list):
                        for q in queries:
                            q["category_section"] = category
                        self.queries.extend(queries)

    def _get_default_queries(self) -> list[dict[str, Any]]:
        """Get default vulnerability discovery queries."""
        return [
            {
                "id": "emerging-solidity",
                "query": "Solidity vulnerability 2024 2025 new attack",
                "category": "emerging",
            },
            {
                "id": "defi-exploit",
                "query": "DeFi exploit analysis writeup",
                "category": "exploits",
            },
            {
                "id": "smart-contract-audit",
                "query": "smart contract audit finding critical high",
                "category": "audits",
            },
            {
                "id": "reentrancy",
                "query": "reentrancy attack new variant Solidity",
                "category": "reentrancy",
            },
            {
                "id": "flash-loan",
                "query": "flash loan attack exploit writeup",
                "category": "flash-loan",
            },
            {
                "id": "oracle",
                "query": "oracle price manipulation attack Solidity",
                "category": "oracle",
            },
            {
                "id": "governance",
                "query": "governance attack DAO voting exploit",
                "category": "governance",
            },
            {
                "id": "l2-security",
                "query": "Layer 2 security vulnerability Arbitrum Optimism",
                "category": "emerging",
            },
            {
                "id": "bridge-exploit",
                "query": "cross-chain bridge exploit attack",
                "category": "cross-chain",
            },
            {
                "id": "account-abstraction",
                "query": "ERC-4337 account abstraction security",
                "category": "account-abstraction",
            },
        ]

    async def scan(
        self,
        days_back: int = 7,
        max_per_query: int = 5,
        category_filter: Optional[str] = None,
    ) -> list[ExaDiscovery]:
        """Execute all queries for recent timeframe.

        Args:
            days_back: How many days back to search
            max_per_query: Maximum results per query
            category_filter: Optional category to filter queries

        Returns:
            List of ExaDiscovery objects
        """
        if not self.api_key:
            raise ValueError(
                "Exa API key required. Set EXA_API_KEY environment variable."
            )

        start_date = datetime.now() - timedelta(days=days_back)

        # Filter queries by category if specified
        queries = self.queries
        if category_filter:
            queries = [
                q
                for q in queries
                if q.get("category", "") == category_filter
                or q.get("category_section", "") == category_filter
            ]

        all_discoveries: list[ExaDiscovery] = []

        for query_config in queries:
            try:
                results = await self._execute_query(
                    query_config, start_date, max_per_query
                )
                all_discoveries.extend(results)
            except Exception as e:
                print(f"Query failed ({query_config.get('id', 'unknown')}): {e}")

        # Dedupe and rank
        unique_discoveries = self._dedupe_and_rank(all_discoveries)

        # Update state
        self.state["last_scan"] = datetime.now().isoformat()
        self.state["scans_completed"] = self.state.get("scans_completed", 0) + 1
        self.state["total_discoveries"] = (
            self.state.get("total_discoveries", 0) + len(unique_discoveries)
        )
        self._save_state()

        return unique_discoveries

    async def _execute_query(
        self,
        query_config: dict[str, Any],
        since: datetime,
        max_results: int,
    ) -> list[ExaDiscovery]:
        """Execute a single Exa query.

        Uses the Exa API directly with httpx for async support.
        """
        import httpx

        query_text = query_config.get("query", "")
        category = query_config.get("category", "")

        if not query_text:
            return []

        # Format date for Exa API
        start_date_str = since.strftime("%Y-%m-%d")

        # Call Exa API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": query_text,
                    "type": "auto",
                    "numResults": max_results,
                    "startPublishedDate": start_date_str,
                    "contents": {
                        "text": {"maxCharacters": 500},
                    },
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                raise Exception(f"Exa API error: {response.status_code}")

            data = response.json()

        discoveries: list[ExaDiscovery] = []

        for result in data.get("results", []):
            url = result.get("url", "")

            # Skip if already seen
            if url in self.state.get("seen_urls", []):
                continue

            # Parse published date
            published_date = None
            if result.get("publishedDate"):
                try:
                    published_date = datetime.fromisoformat(
                        result["publishedDate"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    pass

            discovery = ExaDiscovery(
                url=url,
                title=result.get("title", ""),
                snippet=result.get("text", ""),
                relevance_score=result.get("score", 0.0),
                published_date=published_date,
                query_matched=query_config.get("id", query_text[:30]),
                category=category,
            )

            # Suggest VKG metadata
            discovery.suggested_category = self._suggest_category(
                discovery.title, discovery.snippet, category
            )
            discovery.suggested_operations = self._suggest_operations(
                discovery.title, discovery.snippet
            )

            discoveries.append(discovery)

        return discoveries

    def _dedupe_and_rank(
        self, discoveries: list[ExaDiscovery]
    ) -> list[ExaDiscovery]:
        """Deduplicate and rank discoveries by relevance."""
        # Dedupe by URL
        seen_urls: set[str] = set()
        unique: list[ExaDiscovery] = []

        for d in discoveries:
            if d.url not in seen_urls:
                seen_urls.add(d.url)
                unique.append(d)

        # Sort by relevance score (higher is better)
        unique.sort(key=lambda x: x.relevance_score, reverse=True)

        return unique

    def _suggest_category(
        self, title: str, snippet: str, query_category: str
    ) -> str:
        """Suggest VKG category based on content."""
        text = f"{title} {snippet}".lower()

        # Category hints
        hints = {
            "reentrancy": ["reentrancy", "reentrant", "callback"],
            "access-control": ["access control", "permission", "auth", "owner"],
            "oracle": ["oracle", "price feed", "chainlink", "twap"],
            "flash-loan": ["flash loan", "flashloan", "atomic"],
            "mev": ["mev", "front-run", "sandwich", "backrun"],
            "dos": ["dos", "denial of service", "gas limit", "out of gas"],
            "token": ["erc20", "erc721", "token transfer", "approval"],
            "upgradeability": ["upgrade", "proxy", "delegatecall", "implementation"],
            "governance": ["governance", "voting", "proposal", "dao"],
            "cross-chain": ["bridge", "cross-chain", "layer 2", "l2"],
            "precision-loss": ["precision", "rounding", "decimal"],
            "arithmetic": ["overflow", "underflow", "integer"],
            "crypto": ["signature", "ecrecover", "hash", "cryptograph"],
        }

        for category, keywords in hints.items():
            if any(kw in text for kw in keywords):
                return category

        # Fall back to query category
        return query_category or "emerging"

    def _suggest_operations(self, title: str, snippet: str) -> list[str]:
        """Suggest VKG operations based on content."""
        text = f"{title} {snippet}".lower()
        operations: list[str] = []

        # Operation hints
        if any(x in text for x in ["reentrancy", "reentrant", "callback"]):
            operations.extend(["CALLS_EXTERNAL", "WRITES_USER_BALANCE"])
        if any(x in text for x in ["access", "permission", "auth"]):
            operations.append("CHECKS_PERMISSION")
        if any(x in text for x in ["transfer", "withdraw", "send"]):
            operations.append("TRANSFERS_VALUE_OUT")
        if any(x in text for x in ["oracle", "price"]):
            operations.append("READS_ORACLE")
        if any(x in text for x in ["overflow", "underflow", "arithmetic"]):
            operations.extend(["PERFORMS_MULTIPLICATION", "PERFORMS_DIVISION"])
        if any(x in text for x in ["front", "mev", "sandwich"]):
            operations.append("READS_EXTERNAL_VALUE")
        if any(x in text for x in ["flash loan", "flashloan"]):
            operations.extend(["CALLS_EXTERNAL", "TRANSFERS_VALUE_OUT"])

        return list(set(operations)) if operations else ["MODIFIES_CRITICAL_STATE"]

    def queue_for_review(self, discoveries: list[ExaDiscovery]) -> int:
        """Add discoveries to the review queue.

        Args:
            discoveries: List of discoveries to queue

        Returns:
            Number of discoveries added to queue
        """
        queue = self._load_queue()

        added = 0
        existing_urls = {d["url"] for d in queue.get("pending_review", [])}

        for discovery in discoveries:
            if discovery.url not in existing_urls:
                queue["pending_review"].append(discovery.to_dict())
                added += 1

                # Track seen URLs
                if discovery.url not in self.state.get("seen_urls", []):
                    self.state.setdefault("seen_urls", []).append(discovery.url)

        # Update queue metadata
        queue["last_scan"] = datetime.now().isoformat()
        queue["pending_count"] = len(queue["pending_review"])

        # Save
        self._save_queue(queue)
        self._save_state()

        return added

    def _load_queue(self) -> dict[str, Any]:
        """Load the review queue."""
        if self.queue_file.exists():
            with open(self.queue_file) as f:
                queue = yaml.safe_load(f) or {}
        else:
            queue = {}

        # Ensure structure
        queue.setdefault("queue_type", "exa")
        queue.setdefault("schema_version", "1.0")
        queue.setdefault("last_scan", None)
        queue.setdefault("pending_count", 0)
        queue.setdefault("pending_review", [])
        queue.setdefault("processed", [])

        return queue

    def _save_queue(self, queue: dict[str, Any]) -> None:
        """Save the review queue."""
        with open(self.queue_file, "w") as f:
            yaml.dump(queue, f, default_flow_style=False, sort_keys=False)

    def mark_processed(
        self,
        url: str,
        action: str,
        target: Optional[str] = None,
    ) -> bool:
        """Mark a discovery as processed.

        Args:
            url: URL of the discovery
            action: Action taken (ACCEPT, MERGE, REJECT, DEFER)
            target: Target VulnDocs path if accepted/merged

        Returns:
            True if discovery was found and marked
        """
        queue = self._load_queue()

        # Find in pending
        pending = queue.get("pending_review", [])
        discovery = None
        for i, d in enumerate(pending):
            if d["url"] == url:
                discovery = pending.pop(i)
                break

        if not discovery:
            return False

        # Add to processed
        queue["processed"].append(
            {
                "url": url,
                "title": discovery.get("title", ""),
                "action": action,
                "target": target,
                "processed_at": datetime.now().isoformat(),
            }
        )

        queue["pending_count"] = len(queue["pending_review"])
        self._save_queue(queue)

        return True

    def get_pending_count(self) -> int:
        """Get count of pending discoveries."""
        queue = self._load_queue()
        return len(queue.get("pending_review", []))

    def get_pending_discoveries(self) -> list[ExaDiscovery]:
        """Get all pending discoveries."""
        queue = self._load_queue()
        return [
            ExaDiscovery.from_dict(d) for d in queue.get("pending_review", [])
        ]


# =============================================================================
# Convenience Functions
# =============================================================================


async def scan_exa(
    days_back: int = 7,
    max_per_query: int = 5,
    cache_dir: Optional[Path] = None,
    category_filter: Optional[str] = None,
) -> list[ExaDiscovery]:
    """Convenience function to scan and queue Exa discoveries.

    Args:
        days_back: Days to look back
        max_per_query: Max results per query
        cache_dir: Cache directory
        category_filter: Optional category filter

    Returns:
        List of new discoveries
    """
    scanner = ExaScanner(cache_dir=cache_dir)
    discoveries = await scanner.scan(
        days_back=days_back,
        max_per_query=max_per_query,
        category_filter=category_filter,
    )
    scanner.queue_for_review(discoveries)
    return discoveries
