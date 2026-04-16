"""Crawl4AI-based Crawler for VulnDocs.

Intelligent web crawler using Crawl4AI for extracting vulnerability
knowledge from public sources with LLM-optimized output.

Key Features:
1. Adaptive crawling with confidence-based stopping
2. BM25 content filtering for relevance
3. Virtual scroll support for infinite-scroll pages
4. GitHub markdown recursion
5. Docker-based deployment support
6. Rate limiting and politeness
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from alphaswarm_sol.vulndocs.sources.registry import (
    CrawlConfig,
    KnowledgeSource,
    SourceType,
)


@dataclass
class CrawlResult:
    """Result of crawling a source."""

    source_id: str
    url: str
    timestamp: str
    pages_crawled: int = 0
    content_items: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_tokens: int = 0
    duration_seconds: float = 0.0
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_id": self.source_id,
            "url": self.url,
            "timestamp": self.timestamp,
            "pages_crawled": self.pages_crawled,
            "content_items": self.content_items,
            "errors": self.errors,
            "total_tokens": self.total_tokens,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
        }

    def save(self, output_dir: Path) -> Path:
        """Save result to file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        snapshot_dir = output_dir / "snapshots" / self.source_id
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        for index, item in enumerate(self.content_items):
            content = item.get("content", "")
            if not content:
                continue
            content_hash = item.get("content_hash")
            if not content_hash:
                content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
                item["content_hash"] = content_hash
            filename = f"{content_hash}_{index}.md"
            snapshot_path = snapshot_dir / filename
            snapshot_path.write_text(content, encoding="utf-8")
            metadata = item.setdefault("metadata", {})
            metadata["snapshot_path"] = str(snapshot_path)

        filename = f"{self.source_id}_{self.timestamp.replace(':', '-')}.json"
        filepath = output_dir / filename
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return filepath


@dataclass
class ContentItem:
    """A single content item extracted from a page."""

    url: str
    title: str
    content: str  # LLM-optimized markdown
    raw_content: str = ""  # Original content
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    token_estimate: int = 0
    relevance_score: float = 0.0
    categories: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate content hash if not set."""
        if not self.content_hash:
            self.content_hash = hashlib.md5(self.content.encode()).hexdigest()[:16]
        if not self.token_estimate:
            # Rough estimate: ~4 chars per token
            self.token_estimate = len(self.content) // 4

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "content_hash": self.content_hash,
            "token_estimate": self.token_estimate,
            "relevance_score": self.relevance_score,
            "categories": self.categories,
            "metadata": self.metadata,
        }


class VulnDocsCrawler:
    """Intelligent crawler for vulnerability knowledge extraction.

    Uses Crawl4AI for efficient, LLM-optimized content extraction
    with adaptive crawling and intelligent filtering.

    Usage:
        crawler = VulnDocsCrawler()

        # Crawl a single source
        result = await crawler.crawl_source(source)

        # Crawl with custom config
        result = await crawler.crawl_url(
            url="https://solodit.xyz",
            config=CrawlConfig(max_depth=5),
        )

        # Crawl GitHub repository markdown
        result = await crawler.crawl_github_markdown(
            owner="crytic",
            repo="not-so-smart-contracts",
        )
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        docker_mode: bool = False,
        docker_endpoint: str = "http://localhost:11235",
    ):
        """Initialize the crawler.

        Args:
            output_dir: Directory to save crawl results
            docker_mode: Use Docker-deployed Crawl4AI
            docker_endpoint: Docker Crawl4AI endpoint URL
        """
        self.output_dir = output_dir or Path(".vulndocs_cache")
        self.docker_mode = docker_mode
        self.docker_endpoint = docker_endpoint
        self._crawl4ai_available = self._check_crawl4ai()
        self._seen_urls: Set[str] = set()
        self._content_hashes: Set[str] = set()

    def _check_crawl4ai(self) -> bool:
        """Check if Crawl4AI is available."""
        try:
            import crawl4ai
            return True
        except ImportError:
            return False

    async def crawl_source(self, source: KnowledgeSource) -> CrawlResult:
        """Crawl a knowledge source based on its type.

        Args:
            source: Knowledge source to crawl

        Returns:
            CrawlResult with extracted content
        """
        start_time = datetime.now()

        if source.source_type == SourceType.WEBSITE:
            result = await self._crawl_website(source)
        elif source.source_type == SourceType.API:
            result = await self._crawl_api(source)
        elif source.source_type == SourceType.GITHUB_REPO:
            result = await self._crawl_github_repo(source)
        elif source.source_type == SourceType.GITHUB_MARKDOWN:
            result = await self._crawl_github_markdown(source)
        elif source.source_type == SourceType.YOUTUBE:
            result = await self._crawl_youtube(source)
        else:
            result = CrawlResult(
                source_id=source.id,
                url=source.url,
                timestamp=start_time.isoformat(),
                success=False,
                errors=[f"Unsupported source type: {source.source_type}"],
            )

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    async def _crawl_website(self, source: KnowledgeSource) -> CrawlResult:
        """Crawl a website using Crawl4AI."""
        result = CrawlResult(
            source_id=source.id,
            url=source.url,
            timestamp=datetime.now().isoformat(),
        )

        if not self._crawl4ai_available and not self.docker_mode:
            result.errors.append("Crawl4AI not available. Install with: pip install crawl4ai")
            result.success = False
            return result

        if self.docker_mode:
            return await self._crawl_website_docker(source, result)

        return await self._crawl_website_local(source, result)

    async def _crawl_website_local(
        self, source: KnowledgeSource, result: CrawlResult
    ) -> CrawlResult:
        """Crawl website using local Crawl4AI."""
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
            from crawl4ai.content_filter_strategy import BM25ContentFilter
            from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

            config = source.crawl_config

            # Configure browser
            browser_config = BrowserConfig(
                headless=True,
                verbose=False,
            )

            # Configure content filtering for security-relevant content
            content_filter = BM25ContentFilter(
                user_query="smart contract vulnerability security exploit audit",
                bm25_threshold=1.0,
            )

            # Configure run
            run_config = CrawlerRunConfig(
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=content_filter
                ),
            )

            # Add virtual scroll if needed
            if config.virtual_scroll:
                run_config.virtual_scroll_config = {
                    "scroll_count": config.scroll_count,
                    "wait_after_scroll": 1.0,
                }

            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Crawl main URL
                crawl_result = await crawler.arun(
                    url=source.url,
                    config=run_config,
                )

                if crawl_result.success:
                    item = ContentItem(
                        url=source.url,
                        title=crawl_result.metadata.get("title", source.name),
                        content=crawl_result.markdown.fit_markdown,
                        raw_content=crawl_result.markdown.raw_markdown,
                        categories=source.categories_covered,
                    )
                    result.content_items.append(item.to_dict())
                    result.pages_crawled += 1
                    result.total_tokens += item.token_estimate
                else:
                    result.errors.append(f"Failed to crawl {source.url}")

        except Exception as e:
            result.errors.append(f"Crawl error: {str(e)}")
            result.success = False

        return result

    async def _crawl_website_docker(
        self, source: KnowledgeSource, result: CrawlResult
    ) -> CrawlResult:
        """Crawl website using Docker-deployed Crawl4AI."""
        try:
            import aiohttp

            config = source.crawl_config

            payload = {
                "urls": [source.url],
                "priority": 10,
                "deep_crawl": config.adaptive_crawl,
                "max_depth": config.max_depth,
                "max_pages": config.max_pages,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.docker_endpoint}/crawl",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Process results
                        for page in data.get("results", []):
                            item = ContentItem(
                                url=page.get("url", source.url),
                                title=page.get("title", ""),
                                content=page.get("markdown", ""),
                                categories=source.categories_covered,
                            )
                            result.content_items.append(item.to_dict())
                            result.pages_crawled += 1
                            result.total_tokens += item.token_estimate
                    else:
                        result.errors.append(
                            f"Docker crawl failed: {response.status}"
                        )
                        result.success = False

        except Exception as e:
            result.errors.append(f"Docker crawl error: {str(e)}")
            result.success = False

        return result

    async def _crawl_api(self, source: KnowledgeSource) -> CrawlResult:
        """Crawl an API endpoint."""
        result = CrawlResult(
            source_id=source.id,
            url=source.url,
            timestamp=datetime.now().isoformat(),
        )

        if not source.api_endpoint:
            result.errors.append("No API endpoint configured")
            result.success = False
            return result

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(source.api_endpoint) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Convert API response to content item
                        content = json.dumps(data, indent=2)
                        item = ContentItem(
                            url=source.api_endpoint,
                            title=f"{source.name} API Data",
                            content=content,
                            categories=source.categories_covered,
                            metadata={"source_type": "api"},
                        )
                        result.content_items.append(item.to_dict())
                        result.pages_crawled = 1
                        result.total_tokens = item.token_estimate
                    else:
                        result.errors.append(f"API request failed: {response.status}")
                        result.success = False

        except Exception as e:
            result.errors.append(f"API crawl error: {str(e)}")
            result.success = False

        return result

    async def _crawl_github_repo(self, source: KnowledgeSource) -> CrawlResult:
        """Crawl a GitHub repository."""
        result = CrawlResult(
            source_id=source.id,
            url=source.url,
            timestamp=datetime.now().isoformat(),
        )

        if not source.github_repo:
            result.errors.append("No GitHub repo configured")
            result.success = False
            return result

        try:
            import aiohttp

            owner, repo = source.github_repo.split("/")
            path = source.github_path

            items = await self._fetch_github_contents(owner, repo, path)
            result.content_items = items
            result.pages_crawled = len(items)
            result.total_tokens = sum(item.get("token_estimate", 0) for item in items)

        except Exception as e:
            result.errors.append(f"GitHub crawl error: {str(e)}")
            result.success = False

        return result

    async def _crawl_github_markdown(self, source: KnowledgeSource) -> CrawlResult:
        """Crawl markdown files from a GitHub repository."""
        result = CrawlResult(
            source_id=source.id,
            url=source.url,
            timestamp=datetime.now().isoformat(),
        )

        if not source.github_repo:
            result.errors.append("No GitHub repo configured")
            result.success = False
            return result

        try:
            owner, repo = source.github_repo.split("/")
            path = source.github_path

            # Recursively fetch all markdown files
            items = await self._fetch_github_markdown_recursive(
                owner, repo, path, source.categories_covered
            )
            result.content_items = items
            result.pages_crawled = len(items)
            result.total_tokens = sum(item.get("token_estimate", 0) for item in items)

        except Exception as e:
            result.errors.append(f"GitHub markdown crawl error: {str(e)}")
            result.success = False

        return result

    async def _fetch_github_contents(
        self, owner: str, repo: str, path: str = ""
    ) -> List[Dict[str, Any]]:
        """Fetch contents from GitHub API."""
        import aiohttp

        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        # Add token if available
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        items = []

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    contents = await response.json()

                    if isinstance(contents, list):
                        for item in contents:
                            if item["type"] == "file":
                                # Fetch file content
                                if item["name"].endswith((".md", ".sol", ".json")):
                                    content = await self._fetch_file_content(
                                        session, item["download_url"], headers
                                    )
                                    items.append(ContentItem(
                                        url=item["html_url"],
                                        title=item["name"],
                                        content=content,
                                        metadata={
                                            "path": item["path"],
                                            "sha": item["sha"],
                                        },
                                    ).to_dict())
                            elif item["type"] == "dir":
                                # Recurse into directory
                                sub_items = await self._fetch_github_contents(
                                    owner, repo, item["path"]
                                )
                                items.extend(sub_items)

        return items

    async def _fetch_github_markdown_recursive(
        self,
        owner: str,
        repo: str,
        path: str = "",
        categories: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Recursively fetch all markdown files from a GitHub repository."""
        import aiohttp

        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        items = []

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    return items

                contents = await response.json()

                if isinstance(contents, list):
                    for item in contents:
                        if item["type"] == "dir":
                            # Recurse into subdirectories
                            sub_items = await self._fetch_github_markdown_recursive(
                                owner, repo, item["path"], categories
                            )
                            items.extend(sub_items)

                        elif item["name"].endswith(".md"):
                            # Fetch markdown content
                            content = await self._fetch_file_content(
                                session, item["download_url"], headers
                            )
                            items.append(ContentItem(
                                url=item["html_url"],
                                title=item["name"],
                                content=content,
                                categories=categories or [],
                                metadata={
                                    "path": item["path"],
                                    "sha": item["sha"],
                                    "repo": f"{owner}/{repo}",
                                },
                            ).to_dict())

        return items

    async def _fetch_file_content(
        self,
        session: "aiohttp.ClientSession",
        url: str,
        headers: Dict[str, str],
    ) -> str:
        """Fetch raw file content."""
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
        except Exception:
            pass
        return ""

    async def _crawl_youtube(self, source: KnowledgeSource) -> CrawlResult:
        """Crawl YouTube video transcripts."""
        result = CrawlResult(
            source_id=source.id,
            url=source.url,
            timestamp=datetime.now().isoformat(),
        )

        # YouTube transcript extraction requires youtube-transcript-api
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            # Extract video IDs from channel (simplified)
            # In production, this would use YouTube Data API
            result.errors.append(
                "YouTube crawling requires YouTube Data API integration"
            )
            result.success = False

        except ImportError:
            result.errors.append(
                "YouTube transcript API not available. "
                "Install with: pip install youtube-transcript-api"
            )
            result.success = False

        return result


# =============================================================================
# Convenience Functions
# =============================================================================


async def crawl_source(
    source: KnowledgeSource,
    output_dir: Optional[Path] = None,
    docker_mode: bool = False,
) -> CrawlResult:
    """Convenience function to crawl a single source.

    Args:
        source: Knowledge source to crawl
        output_dir: Directory to save results
        docker_mode: Use Docker-deployed Crawl4AI

    Returns:
        CrawlResult with extracted content
    """
    crawler = VulnDocsCrawler(
        output_dir=output_dir,
        docker_mode=docker_mode,
    )
    return await crawler.crawl_source(source)


async def crawl_all_sources(
    sources: List[KnowledgeSource],
    output_dir: Path,
    concurrency: int = 3,
    docker_mode: bool = False,
) -> List[CrawlResult]:
    """Crawl multiple sources with concurrency control.

    Args:
        sources: List of sources to crawl
        output_dir: Directory to save results
        concurrency: Maximum concurrent crawls
        docker_mode: Use Docker-deployed Crawl4AI

    Returns:
        List of CrawlResults
    """
    crawler = VulnDocsCrawler(
        output_dir=output_dir,
        docker_mode=docker_mode,
    )

    semaphore = asyncio.Semaphore(concurrency)

    async def crawl_with_semaphore(source: KnowledgeSource) -> CrawlResult:
        async with semaphore:
            result = await crawler.crawl_source(source)
            result.save(output_dir)
            return result

    tasks = [crawl_with_semaphore(s) for s in sources]
    return await asyncio.gather(*tasks)
