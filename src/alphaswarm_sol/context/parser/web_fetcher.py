"""Web fetcher for protocol document discovery and retrieval.

This module provides tools to discover and fetch protocol documentation
from local files and remote URLs. It supports automatic discovery of
common documentation patterns and source tier classification.

Per 03-CONTEXT.md: "Auto-discover docs (README, docs/, whitepaper links)
+ user can override/add sources"

Source tiers per 03-CONTEXT.md:
- Tier 1: Official docs (README, docs/, whitepaper)
- Tier 2: Audit reports
- Tier 3: Community/forums

Usage:
    from alphaswarm_sol.context.parser import WebFetcher, FetchedDocument
    from pathlib import Path

    # Initialize with project root
    fetcher = WebFetcher(Path("/path/to/project"))

    # Auto-discover documents
    sources = fetcher.discover_docs()

    # Fetch all discovered + additional sources
    documents = await fetcher.fetch_all(additional_sources=["https://example.com/whitepaper.pdf"])

    # Access fetched content
    for doc in documents:
        print(f"Source: {doc.source_url}")
        print(f"Tier: {doc.source_tier}")
        print(f"Content length: {len(doc.content)}")
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from urllib.parse import urlparse

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# =============================================================================
# Source Classification
# =============================================================================


class SourceType(Enum):
    """Type of documentation source.

    Different source types may receive different parsing strategies.
    """
    README = "readme"
    DOCS = "docs"
    WHITEPAPER = "whitepaper"
    SECURITY = "security"
    AUDIT = "audit"
    CHANGELOG = "changelog"
    GOVERNANCE = "governance"
    FORUM = "forum"
    GITHUB_ISSUE = "github_issue"
    TWITTER = "twitter"
    UNKNOWN = "unknown"


class SourceTier(Enum):
    """Source reliability tier per 03-CONTEXT.md.

    Tier 1: Official documentation (highest trust)
    Tier 2: Audit reports (high trust)
    Tier 3: Community sources (lower trust, needs verification)
    """
    OFFICIAL = 1  # README, docs/, whitepaper
    AUDIT = 2     # Audit reports
    COMMUNITY = 3 # Forums, community discussions


# Source type to tier mapping
SOURCE_TIER_MAP: Dict[SourceType, SourceTier] = {
    SourceType.README: SourceTier.OFFICIAL,
    SourceType.DOCS: SourceTier.OFFICIAL,
    SourceType.WHITEPAPER: SourceTier.OFFICIAL,
    SourceType.SECURITY: SourceTier.OFFICIAL,
    SourceType.AUDIT: SourceTier.AUDIT,
    SourceType.CHANGELOG: SourceTier.OFFICIAL,
    SourceType.GOVERNANCE: SourceTier.OFFICIAL,
    SourceType.FORUM: SourceTier.COMMUNITY,
    SourceType.GITHUB_ISSUE: SourceTier.COMMUNITY,
    SourceType.TWITTER: SourceTier.COMMUNITY,
    SourceType.UNKNOWN: SourceTier.COMMUNITY,
}


# =============================================================================
# Fetched Document
# =============================================================================


@dataclass
class FetchedDocument:
    """A fetched document with metadata.

    Contains the content and metadata for a discovered/fetched document.
    Used as input to the DocParser for LLM extraction.

    Attributes:
        content: Raw document content
        source_url: URL or path where document was fetched from
        source_type: Type of source (README, docs, whitepaper, etc.)
        source_tier: Reliability tier (1=official, 2=audit, 3=community)
        fetch_time: When the document was fetched
        content_hash: SHA256 hash of content for deduplication
        encoding: Character encoding detected
        size_bytes: Size of content in bytes
        metadata: Additional metadata (title, description, etc.)
        fetch_error: Error message if fetch failed

    Usage:
        doc = FetchedDocument(
            content="# Protocol Documentation...",
            source_url="/path/to/README.md",
            source_type=SourceType.README,
            source_tier=SourceTier.OFFICIAL,
            fetch_time=datetime.now(timezone.utc),
            content_hash="abc123..."
        )

        if doc.is_valid:
            print(f"Content: {doc.content[:100]}...")
    """
    content: str
    source_url: str
    source_type: SourceType
    source_tier: SourceTier
    fetch_time: datetime
    content_hash: str
    encoding: str = "utf-8"
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    fetch_error: Optional[str] = None

    def __post_init__(self) -> None:
        """Compute derived fields."""
        if self.size_bytes == 0 and self.content:
            self.size_bytes = len(self.content.encode("utf-8"))

    @property
    def is_valid(self) -> bool:
        """Check if document was fetched successfully."""
        return self.fetch_error is None and bool(self.content)

    @property
    def tier_value(self) -> int:
        """Get numeric tier value (1=official, 2=audit, 3=community)."""
        return self.source_tier.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for JSON/YAML encoding
        """
        return {
            "content": self.content,
            "source_url": self.source_url,
            "source_type": self.source_type.value,
            "source_tier": self.source_tier.value,
            "fetch_time": self.fetch_time.isoformat(),
            "content_hash": self.content_hash,
            "encoding": self.encoding,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
            "fetch_error": self.fetch_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FetchedDocument":
        """Create FetchedDocument from dictionary.

        Args:
            data: Dictionary with document data

        Returns:
            FetchedDocument instance
        """
        # Parse source type
        source_type_str = data.get("source_type", "unknown")
        try:
            source_type = SourceType(source_type_str)
        except ValueError:
            source_type = SourceType.UNKNOWN

        # Parse source tier
        source_tier_val = data.get("source_tier", 3)
        if isinstance(source_tier_val, int):
            source_tier = SourceTier(source_tier_val)
        else:
            source_tier = SourceTier.COMMUNITY

        # Parse fetch time
        fetch_time_str = data.get("fetch_time", "")
        if fetch_time_str:
            try:
                fetch_time = datetime.fromisoformat(fetch_time_str.replace("Z", "+00:00"))
            except ValueError:
                fetch_time = datetime.now(timezone.utc)
        else:
            fetch_time = datetime.now(timezone.utc)

        return cls(
            content=str(data.get("content", "")),
            source_url=str(data.get("source_url", "")),
            source_type=source_type,
            source_tier=source_tier,
            fetch_time=fetch_time,
            content_hash=str(data.get("content_hash", "")),
            encoding=str(data.get("encoding", "utf-8")),
            size_bytes=int(data.get("size_bytes", 0)),
            metadata=dict(data.get("metadata", {})),
            fetch_error=data.get("fetch_error"),
        )


# =============================================================================
# Discovery Source
# =============================================================================


@dataclass
class DiscoveredSource:
    """A discovered documentation source before fetching.

    Represents a potential documentation source that has been discovered
    but not yet fetched.

    Attributes:
        url: URL or path to the source
        source_type: Type of source
        source_tier: Reliability tier
        priority: Fetch priority (lower = higher priority)
        discovered_from: How this source was discovered
    """
    url: str
    source_type: SourceType
    source_tier: SourceTier
    priority: int = 100
    discovered_from: str = "auto"

    @property
    def is_local(self) -> bool:
        """Check if this is a local file path."""
        parsed = urlparse(self.url)
        return parsed.scheme in ("", "file")

    @property
    def is_remote(self) -> bool:
        """Check if this is a remote URL."""
        return not self.is_local


# =============================================================================
# Web Fetcher
# =============================================================================


# Patterns for extracting whitepaper/doc links from README
WHITEPAPER_LINK_PATTERNS = [
    # Markdown links: [Whitepaper](url)
    re.compile(r'\[(?:whitepaper|paper|docs?|documentation|technical\s+paper)\]\s*\(([^)]+)\)', re.I),
    # Direct URL mentions
    re.compile(r'(?:whitepaper|paper):\s*(https?://[^\s]+)', re.I),
    # URLs on their own lines containing whitepaper/docs
    re.compile(r'^(https?://[^\s]*(?:whitepaper|paper|docs?)[^\s]*)', re.I | re.M),
]

# Patterns for GitHub issue links
GITHUB_ISSUE_PATTERNS = [
    re.compile(r'https?://github\.com/[^/]+/[^/]+/issues/\d+', re.I),
    re.compile(r'https?://github\.com/[^/]+/[^/]+/discussions/\d+', re.I),
]

# Patterns for audit report links
AUDIT_PATTERNS = [
    re.compile(r'\[(?:audit|security\s+audit|audit\s+report)\]\s*\(([^)]+)\)', re.I),
    re.compile(r'(https?://[^\s]*audit[^\s]*\.pdf)', re.I),
    re.compile(r'(https?://[^\s]*security[^\s]*report[^\s]*)', re.I),
]


class WebFetcher:
    """Discover and fetch protocol documentation.

    This class handles automatic discovery of documentation sources
    from a project directory and fetching content from both local
    files and remote URLs.

    Per 03-CONTEXT.md: "Auto-discover docs (README, docs/, whitepaper links)
    + user can override/add sources"

    Supported discovery:
    - README.md, README.rst, README.txt
    - docs/ directory (markdown files)
    - SECURITY.md
    - CHANGELOG.md
    - Whitepaper links in README
    - Audit report links

    Usage:
        fetcher = WebFetcher(Path("/path/to/project"))

        # Discover sources
        sources = fetcher.discover_docs()

        # Fetch all
        docs = await fetcher.fetch_all()

        # Fetch with additional sources
        docs = await fetcher.fetch_all(
            additional_sources=["https://example.com/whitepaper.pdf"]
        )
    """

    # Files to discover in project root
    ROOT_FILES = [
        ("README.md", SourceType.README),
        ("README.rst", SourceType.README),
        ("README.txt", SourceType.README),
        ("README", SourceType.README),
        ("SECURITY.md", SourceType.SECURITY),
        ("CHANGELOG.md", SourceType.CHANGELOG),
        ("CHANGELOG", SourceType.CHANGELOG),
        ("GOVERNANCE.md", SourceType.GOVERNANCE),
        ("docs/README.md", SourceType.DOCS),
        ("documentation/README.md", SourceType.DOCS),
    ]

    # Glob patterns for docs directories
    DOCS_PATTERNS = [
        "docs/**/*.md",
        "docs/**/*.rst",
        "documentation/**/*.md",
        "documentation/**/*.rst",
    ]

    def __init__(
        self,
        project_root: Path,
        max_file_size: int = 10 * 1024 * 1024,  # 10 MB
        timeout_seconds: float = 30.0,
    ) -> None:
        """Initialize the web fetcher.

        Args:
            project_root: Path to the project root directory
            max_file_size: Maximum file size to fetch (bytes)
            timeout_seconds: Timeout for HTTP requests
        """
        self.project_root = Path(project_root).resolve()
        self.max_file_size = max_file_size
        self.timeout_seconds = timeout_seconds
        self._discovered_sources: List[DiscoveredSource] = []
        self._fetched_hashes: Set[str] = set()  # Track fetched content hashes

    def discover_docs(self) -> List[DiscoveredSource]:
        """Discover documentation sources in the project.

        Searches for:
        - README files (README.md, README.rst, etc.)
        - docs/ directory contents
        - SECURITY.md, CHANGELOG.md
        - Whitepaper/audit links in README

        Returns:
            List of discovered sources sorted by priority

        Usage:
            sources = fetcher.discover_docs()
            for source in sources:
                print(f"{source.url} (tier {source.source_tier.value})")
        """
        sources: List[DiscoveredSource] = []

        # Check root files
        for filename, source_type in self.ROOT_FILES:
            filepath = self.project_root / filename
            if filepath.exists() and filepath.is_file():
                tier = SOURCE_TIER_MAP.get(source_type, SourceTier.OFFICIAL)
                sources.append(DiscoveredSource(
                    url=str(filepath),
                    source_type=source_type,
                    source_tier=tier,
                    priority=10,  # High priority for root files
                    discovered_from="root_scan",
                ))

        # Scan docs directories
        for pattern in self.DOCS_PATTERNS:
            for filepath in self.project_root.glob(pattern):
                if filepath.is_file():
                    sources.append(DiscoveredSource(
                        url=str(filepath),
                        source_type=SourceType.DOCS,
                        source_tier=SourceTier.OFFICIAL,
                        priority=20,  # Medium priority
                        discovered_from="docs_scan",
                    ))

        # Extract links from README if found
        readme_path = self._find_readme()
        if readme_path:
            links = self._extract_whitepaper_links(readme_path)
            for url, source_type in links:
                tier = SOURCE_TIER_MAP.get(source_type, SourceTier.OFFICIAL)
                sources.append(DiscoveredSource(
                    url=url,
                    source_type=source_type,
                    source_tier=tier,
                    priority=30,  # Lower priority for linked docs
                    discovered_from="readme_extraction",
                ))

        # Deduplicate and sort
        seen_urls: Set[str] = set()
        unique_sources: List[DiscoveredSource] = []
        for source in sources:
            normalized_url = self._normalize_url(source.url)
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                unique_sources.append(source)

        unique_sources.sort(key=lambda s: s.priority)
        self._discovered_sources = unique_sources
        return unique_sources

    def _find_readme(self) -> Optional[Path]:
        """Find the main README file."""
        for name in ["README.md", "README.rst", "README.txt", "README"]:
            path = self.project_root / name
            if path.exists():
                return path
        return None

    def _extract_whitepaper_links(self, readme_path: Path) -> List[tuple[str, SourceType]]:
        """Extract whitepaper and doc links from README.

        Per 03-CONTEXT.md: Auto-discover whitepaper links.

        Args:
            readme_path: Path to README file

        Returns:
            List of (url, source_type) tuples
        """
        links: List[tuple[str, SourceType]] = []

        try:
            content = readme_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return links

        # Extract whitepaper links
        for pattern in WHITEPAPER_LINK_PATTERNS:
            for match in pattern.finditer(content):
                url = match.group(1).strip()
                if url and self._is_valid_url(url):
                    links.append((url, SourceType.WHITEPAPER))

        # Extract audit links
        for pattern in AUDIT_PATTERNS:
            for match in pattern.finditer(content):
                url = match.group(1).strip() if match.lastindex else match.group(0).strip()
                if url and self._is_valid_url(url):
                    links.append((url, SourceType.AUDIT))

        # Extract GitHub issue links
        for pattern in GITHUB_ISSUE_PATTERNS:
            for match in pattern.finditer(content):
                url = match.group(0).strip()
                links.append((url, SourceType.GITHUB_ISSUE))

        return links

    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid and fetchable."""
        if not url:
            return False

        # Check for valid scheme or local path
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            return True
        if parsed.scheme in ("", "file"):
            # Local path
            return True

        return False

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        # Remove trailing slashes
        url = url.rstrip("/")
        # Lowercase scheme and host
        parsed = urlparse(url)
        if parsed.scheme:
            url = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}"
        return url

    def fetch_local(self, path: Path) -> FetchedDocument:
        """Fetch content from a local file.

        Args:
            path: Path to local file

        Returns:
            FetchedDocument with content or error

        Usage:
            doc = fetcher.fetch_local(Path("/path/to/README.md"))
            if doc.is_valid:
                print(doc.content)
        """
        source_type, source_tier = self._classify_source(str(path))

        if not path.exists():
            return FetchedDocument(
                content="",
                source_url=str(path),
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash="",
                fetch_error=f"File not found: {path}",
            )

        if not path.is_file():
            return FetchedDocument(
                content="",
                source_url=str(path),
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash="",
                fetch_error=f"Not a file: {path}",
            )

        # Check file size
        try:
            size = path.stat().st_size
            if size > self.max_file_size:
                return FetchedDocument(
                    content="",
                    source_url=str(path),
                    source_type=source_type,
                    source_tier=source_tier,
                    fetch_time=datetime.now(timezone.utc),
                    content_hash="",
                    size_bytes=size,
                    fetch_error=f"File too large: {size} bytes (max: {self.max_file_size})",
                )
        except OSError as e:
            return FetchedDocument(
                content="",
                source_url=str(path),
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash="",
                fetch_error=f"Cannot stat file: {e}",
            )

        # Read content
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

            return FetchedDocument(
                content=content,
                source_url=str(path),
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash=content_hash,
                encoding="utf-8",
                size_bytes=len(content.encode("utf-8")),
                metadata={"filename": path.name},
            )
        except Exception as e:
            return FetchedDocument(
                content="",
                source_url=str(path),
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash="",
                fetch_error=f"Read error: {e}",
            )

    async def fetch_url(
        self,
        url: str,
        source_tier: Optional[SourceTier] = None,
    ) -> FetchedDocument:
        """Fetch content from a remote URL.

        Args:
            url: URL to fetch
            source_tier: Override tier classification

        Returns:
            FetchedDocument with content or error

        Usage:
            doc = await fetcher.fetch_url("https://example.com/whitepaper.pdf")
            if doc.is_valid:
                print(f"Fetched {doc.size_bytes} bytes")
        """
        source_type, auto_tier = self._classify_source(url)
        if source_tier is None:
            source_tier = auto_tier

        if not HTTPX_AVAILABLE:
            return FetchedDocument(
                content="",
                source_url=url,
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash="",
                fetch_error="httpx not available - install with: pip install httpx",
            )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Check content length
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.max_file_size:
                    return FetchedDocument(
                        content="",
                        source_url=url,
                        source_type=source_type,
                        source_tier=source_tier,
                        fetch_time=datetime.now(timezone.utc),
                        content_hash="",
                        size_bytes=int(content_length),
                        fetch_error=f"Content too large: {content_length} bytes",
                    )

                # Get content
                content = response.text
                if len(content.encode("utf-8")) > self.max_file_size:
                    return FetchedDocument(
                        content="",
                        source_url=url,
                        source_type=source_type,
                        source_tier=source_tier,
                        fetch_time=datetime.now(timezone.utc),
                        content_hash="",
                        fetch_error="Content exceeds max size after decoding",
                    )

                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

                # Extract metadata from response
                metadata: Dict[str, Any] = {
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                }

                return FetchedDocument(
                    content=content,
                    source_url=url,
                    source_type=source_type,
                    source_tier=source_tier,
                    fetch_time=datetime.now(timezone.utc),
                    content_hash=content_hash,
                    encoding=response.encoding or "utf-8",
                    size_bytes=len(content.encode("utf-8")),
                    metadata=metadata,
                )

        except httpx.TimeoutException:
            return FetchedDocument(
                content="",
                source_url=url,
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash="",
                fetch_error=f"Timeout after {self.timeout_seconds}s",
            )
        except httpx.HTTPStatusError as e:
            return FetchedDocument(
                content="",
                source_url=url,
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash="",
                fetch_error=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            )
        except Exception as e:
            return FetchedDocument(
                content="",
                source_url=url,
                source_type=source_type,
                source_tier=source_tier,
                fetch_time=datetime.now(timezone.utc),
                content_hash="",
                fetch_error=f"Fetch error: {e}",
            )

    async def fetch_all(
        self,
        additional_sources: Optional[List[str]] = None,
        include_discovered: bool = True,
    ) -> List[FetchedDocument]:
        """Fetch all discovered and additional sources.

        Args:
            additional_sources: Additional URLs/paths to fetch
            include_discovered: Whether to include auto-discovered sources

        Returns:
            List of FetchedDocument objects

        Usage:
            docs = await fetcher.fetch_all(
                additional_sources=["https://example.com/whitepaper.pdf"]
            )
            valid_docs = [d for d in docs if d.is_valid]
        """
        documents: List[FetchedDocument] = []

        # Get sources to fetch
        sources: List[DiscoveredSource] = []
        if include_discovered:
            if not self._discovered_sources:
                self.discover_docs()
            sources.extend(self._discovered_sources)

        # Add additional sources
        if additional_sources:
            for url in additional_sources:
                source_type, source_tier = self._classify_source(url)
                sources.append(DiscoveredSource(
                    url=url,
                    source_type=source_type,
                    source_tier=source_tier,
                    priority=50,  # Medium-low priority for user-provided
                    discovered_from="user_provided",
                ))

        # Fetch each source
        for source in sources:
            if source.is_local:
                doc = self.fetch_local(Path(source.url))
            else:
                doc = await self.fetch_url(source.url, source.source_tier)

            # Skip duplicates by content hash
            if doc.is_valid and doc.content_hash in self._fetched_hashes:
                continue

            if doc.is_valid:
                self._fetched_hashes.add(doc.content_hash)

            documents.append(doc)

        return documents

    def _classify_source(self, url: str) -> tuple[SourceType, SourceTier]:
        """Classify a source by URL/path.

        Determines the source type and tier based on URL patterns.

        Args:
            url: URL or path to classify

        Returns:
            Tuple of (SourceType, SourceTier)
        """
        url_lower = url.lower()
        parsed = urlparse(url)
        path_lower = parsed.path.lower() if parsed.path else url_lower

        # Check for specific file types
        if "readme" in path_lower:
            return SourceType.README, SourceTier.OFFICIAL

        if "security" in path_lower:
            return SourceType.SECURITY, SourceTier.OFFICIAL

        if "changelog" in path_lower:
            return SourceType.CHANGELOG, SourceTier.OFFICIAL

        if "governance" in path_lower:
            return SourceType.GOVERNANCE, SourceTier.OFFICIAL

        if "whitepaper" in path_lower or "paper" in path_lower:
            return SourceType.WHITEPAPER, SourceTier.OFFICIAL

        if "audit" in path_lower:
            return SourceType.AUDIT, SourceTier.AUDIT

        # Check for GitHub patterns
        if "github.com" in url_lower:
            if "/issues/" in url_lower or "/discussions/" in url_lower:
                return SourceType.GITHUB_ISSUE, SourceTier.COMMUNITY

        # Check for forum patterns
        if any(forum in url_lower for forum in ["forum", "discourse", "governance"]):
            return SourceType.FORUM, SourceTier.COMMUNITY

        # Check for Twitter
        if "twitter.com" in url_lower or "x.com" in url_lower:
            return SourceType.TWITTER, SourceTier.COMMUNITY

        # Check for docs directory
        if "/docs/" in path_lower or "/documentation/" in path_lower:
            return SourceType.DOCS, SourceTier.OFFICIAL

        # Default
        return SourceType.UNKNOWN, SourceTier.COMMUNITY


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    "WebFetcher",
    "FetchedDocument",
    "DiscoveredSource",
    "SourceType",
    "SourceTier",
    "SOURCE_TIER_MAP",
]
