"""Continuous Solodit fetcher for new audit findings.

Solodit is a vulnerability aggregator that collects findings from various
audit firms. This fetcher polls Solodit for new findings and queues them
for human review before integration into VulnDocs.

Key Design Decisions:
1. NO auto-integration - all findings require human review
2. Uses crawl4ai for web scraping (Solodit has no public API)
3. State tracking for incremental fetches
4. Queue-based workflow for review

Usage:
    fetcher = SoloditFetcher()
    findings = await fetcher.fetch_new(days_back=7)
    fetcher.queue_for_review(findings)

CLI:
    uv run alphaswarm vulndocs fetch-solodit --since 7d
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class SoloditFinding:
    """A finding from Solodit.

    Represents a single vulnerability finding extracted from Solodit,
    ready for human review and potential VulnDocs integration.
    """

    id: str
    title: str
    severity: str
    protocol: str
    category: str
    description: str
    url: str
    discovered_at: datetime
    auditor: str = ""
    tags: list[str] = field(default_factory=list)

    # Auto-extracted VKG metadata (suggested, not authoritative)
    suggested_category: str = ""
    suggested_operations: list[str] = field(default_factory=list)
    suggested_signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for YAML storage."""
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "protocol": self.protocol,
            "category": self.category,
            "description": self.description,
            "url": self.url,
            "discovered_at": self.discovered_at.isoformat(),
            "auditor": self.auditor,
            "tags": self.tags,
            "suggested_category": self.suggested_category,
            "suggested_operations": self.suggested_operations,
            "suggested_signature": self.suggested_signature,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SoloditFinding:
        """Deserialize from dictionary."""
        discovered_at = data.get("discovered_at", "")
        if isinstance(discovered_at, str):
            discovered_at = datetime.fromisoformat(discovered_at)
        elif not isinstance(discovered_at, datetime):
            discovered_at = datetime.now()

        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            severity=data.get("severity", "UNKNOWN"),
            protocol=data.get("protocol", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            url=data.get("url", ""),
            discovered_at=discovered_at,
            auditor=data.get("auditor", ""),
            tags=data.get("tags", []),
            suggested_category=data.get("suggested_category", ""),
            suggested_operations=data.get("suggested_operations", []),
            suggested_signature=data.get("suggested_signature", ""),
        )


class SoloditFetcher:
    """Fetches new findings from Solodit.

    This fetcher uses crawl4ai to scrape Solodit's website for new
    audit findings. Since Solodit doesn't have a public API, we
    rely on web scraping with intelligent content extraction.

    State Management:
    - Tracks last fetch timestamp
    - Maintains set of processed finding IDs to avoid duplicates
    - Stores state in YAML for human readability

    Queue Workflow:
    1. fetch_new() retrieves findings newer than last fetch
    2. queue_for_review() adds to pending review queue
    3. Human reviews queue and decides: ACCEPT, MERGE, REJECT, DEFER
    4. Accepted findings are integrated into VulnDocs
    """

    SOLODIT_BASE_URL = "https://solodit.xyz"
    SOLODIT_FINDINGS_URL = "https://solodit.xyz/issues"

    # Severity mapping from Solodit to standard
    SEVERITY_MAP = {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
        "informational": "INFO",
        "gas": "INFO",
    }

    # VKG category mapping hints
    CATEGORY_HINTS = {
        "reentrancy": "reentrancy",
        "access control": "access-control",
        "access-control": "access-control",
        "oracle": "oracle",
        "flash loan": "flash-loan",
        "flash-loan": "flash-loan",
        "price manipulation": "oracle",
        "overflow": "arithmetic",
        "underflow": "arithmetic",
        "front-running": "mev",
        "frontrunning": "mev",
        "mev": "mev",
        "dos": "dos",
        "denial of service": "dos",
        "token": "token",
        "erc20": "token",
        "erc721": "token",
        "upgrade": "upgradeability",
        "proxy": "upgradeability",
        "initialization": "initialization",
        "governance": "governance",
        "signature": "crypto",
        "cryptography": "crypto",
        "cross-chain": "cross-chain",
        "bridge": "cross-chain",
        "precision": "precision-loss",
        "rounding": "precision-loss",
    }

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        docker_mode: bool = False,
    ):
        """Initialize the Solodit fetcher.

        Args:
            cache_dir: Directory for state and cache files
            docker_mode: Use Docker-deployed crawl4ai
        """
        self.cache_dir = cache_dir or Path(".vrs/discovery")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.cache_dir / "solodit_state.yaml"
        self.queue_file = self.cache_dir / "solodit_queue.yaml"
        self.docker_mode = docker_mode
        self._load_state()
        self._crawl4ai_available = self._check_crawl4ai()

    def _check_crawl4ai(self) -> bool:
        """Check if crawl4ai is available."""
        try:
            import crawl4ai  # noqa: F401

            return True
        except ImportError:
            return False

    def _load_state(self) -> None:
        """Load last fetch state."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                self.state = yaml.safe_load(f) or {}
        else:
            self.state = {
                "last_fetch": None,
                "last_fetch_count": 0,
                "total_fetched": 0,
                "processed_ids": [],
            }

    def _save_state(self) -> None:
        """Save current state to file."""
        with open(self.state_file, "w") as f:
            yaml.dump(self.state, f, default_flow_style=False)

    async def fetch_new(
        self,
        days_back: int = 7,
        max_results: int = 50,
    ) -> list[SoloditFinding]:
        """Fetch findings newer than specified days.

        Args:
            days_back: How many days back to look for findings
            max_results: Maximum number of results to return

        Returns:
            List of new SoloditFinding objects
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # If we have a last_fetch that's more recent, use that
        if self.state.get("last_fetch"):
            last_fetch = datetime.fromisoformat(self.state["last_fetch"])
            if last_fetch > cutoff_date:
                cutoff_date = last_fetch

        findings = await self._scrape_findings(cutoff_date, max_results)

        # Filter out already processed
        processed_ids = set(self.state.get("processed_ids", []))
        new_findings = [f for f in findings if f.id not in processed_ids]

        # Update state
        self.state["last_fetch"] = datetime.now().isoformat()
        self.state["last_fetch_count"] = len(new_findings)
        self.state["total_fetched"] = self.state.get("total_fetched", 0) + len(
            new_findings
        )
        self._save_state()

        return new_findings

    async def _scrape_findings(
        self,
        since: datetime,
        max_results: int,
    ) -> list[SoloditFinding]:
        """Scrape findings from Solodit website.

        Note: This is a best-effort scraping approach. Solodit's structure
        may change, and the fetcher should gracefully handle failures.
        """
        findings: list[SoloditFinding] = []

        if not self._crawl4ai_available and not self.docker_mode:
            # Fallback: return empty with warning
            print(
                "Warning: crawl4ai not available. "
                "Install with: pip install crawl4ai"
            )
            return findings

        try:
            if self.docker_mode:
                findings = await self._scrape_with_docker(since, max_results)
            else:
                findings = await self._scrape_with_crawl4ai(since, max_results)
        except Exception as e:
            print(f"Solodit scraping error: {e}")

        return findings

    async def _scrape_with_crawl4ai(
        self,
        since: datetime,
        max_results: int,
    ) -> list[SoloditFinding]:
        """Scrape using local crawl4ai installation."""
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        findings: list[SoloditFinding] = []

        browser_config = BrowserConfig(headless=True, verbose=False)

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Crawl the issues page
            run_config = CrawlerRunConfig()

            result = await crawler.arun(
                url=self.SOLODIT_FINDINGS_URL,
                config=run_config,
            )

            if result.success:
                findings = self._parse_findings_page(
                    result.markdown.raw_markdown if result.markdown else "",
                    result.html if hasattr(result, "html") else "",
                    since,
                    max_results,
                )

        return findings

    async def _scrape_with_docker(
        self,
        since: datetime,
        max_results: int,
    ) -> list[SoloditFinding]:
        """Scrape using Docker-deployed crawl4ai."""
        import aiohttp

        findings: list[SoloditFinding] = []

        payload = {
            "urls": [self.SOLODIT_FINDINGS_URL],
            "priority": 10,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:11235/crawl",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for page in data.get("results", []):
                            page_findings = self._parse_findings_page(
                                page.get("markdown", ""),
                                page.get("html", ""),
                                since,
                                max_results - len(findings),
                            )
                            findings.extend(page_findings)
                            if len(findings) >= max_results:
                                break
        except Exception as e:
            print(f"Docker crawl error: {e}")

        return findings

    def _parse_findings_page(
        self,
        markdown: str,
        html: str,
        since: datetime,
        max_results: int,
    ) -> list[SoloditFinding]:
        """Parse findings from page content.

        This parser handles Solodit's typical structure. It uses both
        markdown and HTML content for robust extraction.
        """
        findings: list[SoloditFinding] = []

        # Extract finding blocks from markdown
        # Solodit typically shows: Title, Severity, Protocol, Date, Description
        finding_patterns = [
            # Pattern for markdown-style finding blocks
            r"#{1,3}\s*(.+?)\n.*?(?:severity|risk)[:\s]*(\w+).*?(?:protocol)[:\s]*(.+?)\n",
            # Pattern for list-style findings
            r"\*\*(.+?)\*\*.*?(?:severity|risk)[:\s]*(\w+)",
        ]

        # Also try to extract from structured HTML if available
        if html:
            findings.extend(self._parse_html_findings(html, since, max_results))

        # Process markdown patterns as fallback
        for pattern in finding_patterns:
            for match in re.finditer(pattern, markdown, re.IGNORECASE | re.DOTALL):
                if len(findings) >= max_results:
                    break

                title = match.group(1).strip()
                severity = self._normalize_severity(match.group(2).strip())

                # Generate unique ID
                finding_id = self._generate_finding_id(title)

                # Skip if already processed
                if finding_id in self.state.get("processed_ids", []):
                    continue

                finding = SoloditFinding(
                    id=finding_id,
                    title=title,
                    severity=severity,
                    protocol="",  # Extract from context if available
                    category=self._suggest_category(title),
                    description="",  # Would need full page fetch
                    url=f"{self.SOLODIT_BASE_URL}/issues/{finding_id}",
                    discovered_at=datetime.now(),  # Use actual date if extractable
                )

                # Add suggested VKG metadata
                finding.suggested_category = self._suggest_vkg_category(title)
                finding.suggested_operations = self._suggest_operations(title)

                findings.append(finding)

        return findings[:max_results]

    def _parse_html_findings(
        self,
        html: str,
        since: datetime,
        max_results: int,
    ) -> list[SoloditFinding]:
        """Parse findings from HTML content."""
        findings: list[SoloditFinding] = []

        # Look for common Solodit finding card patterns
        # This is a simplified parser - production would use BeautifulSoup
        card_pattern = r'<div[^>]*class="[^"]*finding[^"]*"[^>]*>(.*?)</div>'

        for match in re.finditer(card_pattern, html, re.IGNORECASE | re.DOTALL):
            if len(findings) >= max_results:
                break

            card_html = match.group(1)

            # Extract title
            title_match = re.search(r"<h[23][^>]*>([^<]+)</h[23]>", card_html)
            title = title_match.group(1).strip() if title_match else ""

            # Extract severity
            severity_match = re.search(
                r'(?:severity|risk)[^>]*>([^<]+)', card_html, re.IGNORECASE
            )
            severity = (
                self._normalize_severity(severity_match.group(1).strip())
                if severity_match
                else "UNKNOWN"
            )

            if title:
                finding_id = self._generate_finding_id(title)

                finding = SoloditFinding(
                    id=finding_id,
                    title=title,
                    severity=severity,
                    protocol="",
                    category=self._suggest_category(title),
                    description="",
                    url=f"{self.SOLODIT_BASE_URL}/issues/{finding_id}",
                    discovered_at=datetime.now(),
                )

                finding.suggested_category = self._suggest_vkg_category(title)
                finding.suggested_operations = self._suggest_operations(title)

                findings.append(finding)

        return findings

    def _generate_finding_id(self, title: str) -> str:
        """Generate a unique finding ID from title."""
        title_hash = hashlib.md5(title.lower().encode()).hexdigest()[:8]
        return f"solodit-{title_hash}"

    def _normalize_severity(self, severity: str) -> str:
        """Normalize severity to standard format."""
        return self.SEVERITY_MAP.get(severity.lower(), "UNKNOWN")

    def _suggest_category(self, title: str) -> str:
        """Suggest a category based on title keywords."""
        title_lower = title.lower()

        for keyword, category in self.CATEGORY_HINTS.items():
            if keyword in title_lower:
                return category

        return "logic"  # Default category

    def _suggest_vkg_category(self, title: str) -> str:
        """Suggest VKG category path."""
        category = self._suggest_category(title)
        # Map to full path
        return f"{category}/general"

    def _suggest_operations(self, title: str) -> list[str]:
        """Suggest VKG operations based on title."""
        operations: list[str] = []
        title_lower = title.lower()

        # Operation hints
        if any(x in title_lower for x in ["reentrancy", "reentrant", "callback"]):
            operations.extend(["CALLS_EXTERNAL", "WRITES_USER_BALANCE"])
        if any(x in title_lower for x in ["access", "permission", "auth"]):
            operations.append("CHECKS_PERMISSION")
        if any(x in title_lower for x in ["transfer", "withdraw", "send"]):
            operations.append("TRANSFERS_VALUE_OUT")
        if any(x in title_lower for x in ["oracle", "price"]):
            operations.append("READS_ORACLE")
        if any(x in title_lower for x in ["overflow", "underflow", "arithmetic"]):
            operations.extend(["PERFORMS_MULTIPLICATION", "PERFORMS_DIVISION"])
        if any(x in title_lower for x in ["front", "mev", "sandwich"]):
            operations.append("READS_EXTERNAL_VALUE")

        return list(set(operations)) if operations else ["MODIFIES_CRITICAL_STATE"]

    def queue_for_review(self, findings: list[SoloditFinding]) -> int:
        """Add findings to the review queue.

        Args:
            findings: List of findings to queue

        Returns:
            Number of findings added to queue
        """
        # Load existing queue
        queue = self._load_queue()

        # Add new findings to pending
        added = 0
        existing_ids = {f["id"] for f in queue.get("pending_review", [])}

        for finding in findings:
            if finding.id not in existing_ids:
                queue["pending_review"].append(finding.to_dict())
                added += 1

        # Update queue
        queue["last_updated"] = datetime.now().isoformat()
        queue["pending_count"] = len(queue["pending_review"])

        # Save queue
        self._save_queue(queue)

        return added

    def _load_queue(self) -> dict[str, Any]:
        """Load the review queue."""
        if self.queue_file.exists():
            with open(self.queue_file) as f:
                queue = yaml.safe_load(f) or {}
        else:
            queue = {}

        # Ensure structure
        queue.setdefault("queue_type", "solodit")
        queue.setdefault("schema_version", "1.0")
        queue.setdefault("last_updated", None)
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
        finding_id: str,
        action: str,
        target: Optional[str] = None,
    ) -> bool:
        """Mark a finding as processed.

        Args:
            finding_id: ID of the finding
            action: Action taken (ACCEPT, MERGE, REJECT, DEFER)
            target: Target VulnDocs path if accepted/merged

        Returns:
            True if finding was found and marked
        """
        queue = self._load_queue()

        # Find in pending
        pending = queue.get("pending_review", [])
        finding = None
        for i, f in enumerate(pending):
            if f["id"] == finding_id:
                finding = pending.pop(i)
                break

        if not finding:
            return False

        # Add to processed
        queue["processed"].append(
            {
                "id": finding_id,
                "title": finding.get("title", ""),
                "action": action,
                "target": target,
                "processed_at": datetime.now().isoformat(),
            }
        )

        # Update state
        processed_ids = self.state.get("processed_ids", [])
        if finding_id not in processed_ids:
            processed_ids.append(finding_id)
            self.state["processed_ids"] = processed_ids
            self._save_state()

        # Update pending count
        queue["pending_count"] = len(queue["pending_review"])
        self._save_queue(queue)

        return True

    def get_pending_count(self) -> int:
        """Get count of pending findings."""
        queue = self._load_queue()
        return len(queue.get("pending_review", []))

    def get_pending_findings(self) -> list[SoloditFinding]:
        """Get all pending findings."""
        queue = self._load_queue()
        return [
            SoloditFinding.from_dict(f) for f in queue.get("pending_review", [])
        ]


# =============================================================================
# Convenience Functions
# =============================================================================


async def fetch_solodit(
    days_back: int = 7,
    max_results: int = 50,
    cache_dir: Optional[Path] = None,
) -> list[SoloditFinding]:
    """Convenience function to fetch and queue Solodit findings.

    Args:
        days_back: Days to look back
        max_results: Maximum results
        cache_dir: Cache directory

    Returns:
        List of new findings
    """
    fetcher = SoloditFetcher(cache_dir=cache_dir)
    findings = await fetcher.fetch_new(days_back=days_back, max_results=max_results)
    fetcher.queue_for_review(findings)
    return findings
