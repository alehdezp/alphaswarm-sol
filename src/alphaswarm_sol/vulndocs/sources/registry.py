"""Comprehensive Sources Registry for VulnDocs.

This module defines all known sources of vulnerability knowledge in the
smart contract security ecosystem. Sources are organized by category
and priority for systematic scraping and processing.

Design Goals:
1. Complete coverage of public vulnerability knowledge
2. Structured metadata for intelligent processing
3. Priority-based scraping for resource optimization
4. Deduplication and merge tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceCategory(Enum):
    """Categories of vulnerability knowledge sources."""

    # Primary Sources - Direct vulnerability reports
    AUDIT_REPORTS = "audit_reports"  # Solodit, Code4rena, Sherlock
    EXPLOIT_DATABASE = "exploit_database"  # Rekt, DeFiLlama hacks
    BUG_BOUNTY = "bug_bounty"  # Immunefi, HackerOne

    # Research Sources - Analysis and research
    SECURITY_RESEARCH = "security_research"  # Trail of Bits, Consensys
    ACADEMIC_PAPERS = "academic_papers"  # IEEE, ACM security papers

    # Code Sources - Patterns and examples
    GITHUB_REPOS = "github_repos"  # SWC, smart contract repos
    CODE_EXAMPLES = "code_examples"  # Damn Vulnerable DeFi, Ethernaut

    # Educational Sources - Tutorials and explanations
    BLOG_POSTS = "blog_posts"  # Medium, security blogs
    VIDEO_CONTENT = "video_content"  # YouTube security channels
    COURSES = "courses"  # Secureum, OpenZeppelin courses

    # Documentation Sources - Official docs
    OFFICIAL_DOCS = "official_docs"  # Solidity docs, EIPs
    FRAMEWORK_DOCS = "framework_docs"  # OpenZeppelin, Foundry

    # Checklist Sources - Security checklists
    CHECKLISTS = "checklists"  # SCSVS, audit checklists
    BEST_PRACTICES = "best_practices"  # Security guidelines


class SourcePriority(Enum):
    """Priority levels for source processing."""

    CRITICAL = 1  # Must have - primary vulnerability data
    HIGH = 2  # Important - detailed analysis
    MEDIUM = 3  # Useful - additional context
    LOW = 4  # Nice to have - supplementary


class SourceType(Enum):
    """Type of source for crawler configuration."""

    WEBSITE = "website"  # Standard website crawl
    API = "api"  # API-based data retrieval
    GITHUB_REPO = "github_repo"  # GitHub repository crawl
    GITHUB_MARKDOWN = "github_markdown"  # GitHub markdown files
    RSS_FEED = "rss_feed"  # RSS/Atom feed
    YOUTUBE = "youtube"  # YouTube video transcripts
    PDF = "pdf"  # PDF documents
    NOTION = "notion"  # Notion databases


@dataclass
class CrawlConfig:
    """Configuration for crawling a source."""

    max_depth: int = 3
    max_pages: int = 1000
    rate_limit: float = 1.0  # Requests per second
    use_javascript: bool = False
    virtual_scroll: bool = False
    scroll_count: int = 10
    adaptive_crawl: bool = True
    confidence_threshold: float = 0.7
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "max_depth": self.max_depth,
            "max_pages": self.max_pages,
            "rate_limit": self.rate_limit,
            "use_javascript": self.use_javascript,
            "virtual_scroll": self.virtual_scroll,
            "scroll_count": self.scroll_count,
            "adaptive_crawl": self.adaptive_crawl,
            "confidence_threshold": self.confidence_threshold,
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
        }


@dataclass
class KnowledgeSource:
    """A source of vulnerability knowledge.

    Represents a single source to be scraped and processed
    for vulnerability knowledge extraction.
    """

    id: str
    name: str
    description: str
    category: SourceCategory
    source_type: SourceType
    priority: SourcePriority
    url: str
    api_endpoint: Optional[str] = None
    github_repo: Optional[str] = None  # owner/repo format
    github_path: str = ""  # Path within repo
    categories_covered: List[str] = field(default_factory=list)
    last_scraped: Optional[str] = None
    crawl_config: CrawlConfig = field(default_factory=CrawlConfig)
    requires_auth: bool = False
    auth_type: str = ""  # api_key, oauth, none
    notes: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "source_type": self.source_type.value,
            "priority": self.priority.value,
            "url": self.url,
            "api_endpoint": self.api_endpoint,
            "github_repo": self.github_repo,
            "github_path": self.github_path,
            "categories_covered": self.categories_covered,
            "last_scraped": self.last_scraped,
            "crawl_config": self.crawl_config.to_dict(),
            "requires_auth": self.requires_auth,
            "auth_type": self.auth_type,
            "notes": self.notes,
            "tags": self.tags,
        }


class SourceRegistry:
    """Registry of all vulnerability knowledge sources.

    Maintains a catalog of sources to be scraped and their
    processing status.
    """

    def __init__(self):
        self.sources: Dict[str, KnowledgeSource] = {}

    def add_source(self, source: KnowledgeSource) -> None:
        """Add a source to the registry."""
        self.sources[source.id] = source

    def get_source(self, source_id: str) -> Optional[KnowledgeSource]:
        """Get a source by ID."""
        return self.sources.get(source_id)

    def get_by_category(self, category: SourceCategory) -> List[KnowledgeSource]:
        """Get all sources in a category."""
        return [s for s in self.sources.values() if s.category == category]

    def get_by_priority(self, priority: SourcePriority) -> List[KnowledgeSource]:
        """Get all sources with a priority."""
        return [s for s in self.sources.values() if s.priority == priority]

    def get_by_vuln_category(self, vuln_category: str) -> List[KnowledgeSource]:
        """Get sources covering a vulnerability category."""
        return [
            s for s in self.sources.values()
            if vuln_category in s.categories_covered
        ]

    def get_all(self) -> List[KnowledgeSource]:
        """Get all sources."""
        return list(self.sources.values())

    def get_prioritized(self) -> List[KnowledgeSource]:
        """Get sources sorted by priority."""
        return sorted(self.sources.values(), key=lambda s: s.priority.value)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "sources": {k: v.to_dict() for k, v in self.sources.items()},
            "total_count": len(self.sources),
            "by_category": {
                cat.value: len(self.get_by_category(cat))
                for cat in SourceCategory
            },
            "by_priority": {
                p.value: len(self.get_by_priority(p))
                for p in SourcePriority
            },
        }


def get_default_sources() -> SourceRegistry:
    """Get the default comprehensive sources registry.

    This defines ALL known sources of smart contract vulnerability
    knowledge that should be scraped and processed.

    Returns:
        SourceRegistry with all configured sources
    """
    registry = SourceRegistry()

    # =========================================================================
    # AUDIT REPORTS & FINDINGS (CRITICAL)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="solodit",
        name="Solodit",
        description="Comprehensive database of smart contract audit findings from multiple firms",
        category=SourceCategory.AUDIT_REPORTS,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.CRITICAL,
        url="https://solodit.xyz",
        api_endpoint="https://solodit.xyz/api",
        categories_covered=[
            "reentrancy", "access-control", "oracle", "flash-loan",
            "mev", "dos", "token", "upgrade", "crypto", "governance", "logic"
        ],
        crawl_config=CrawlConfig(
            max_depth=5,
            max_pages=10000,
            use_javascript=True,
            adaptive_crawl=True,
            include_patterns=["/findings/", "/audits/"],
        ),
        tags=["audit", "findings", "critical"],
    ))

    registry.add_source(KnowledgeSource(
        id="code4rena",
        name="Code4rena",
        description="Competitive audit platform with public findings",
        category=SourceCategory.AUDIT_REPORTS,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.CRITICAL,
        url="https://code4rena.com",
        categories_covered=[
            "reentrancy", "access-control", "oracle", "flash-loan", "logic"
        ],
        crawl_config=CrawlConfig(
            max_depth=4,
            max_pages=5000,
            use_javascript=True,
            include_patterns=["/reports/", "/findings/"],
        ),
        tags=["audit", "competitive", "findings"],
    ))

    registry.add_source(KnowledgeSource(
        id="sherlock",
        name="Sherlock",
        description="DeFi audit marketplace with detailed findings",
        category=SourceCategory.AUDIT_REPORTS,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.CRITICAL,
        url="https://app.sherlock.xyz",
        categories_covered=[
            "reentrancy", "access-control", "oracle", "flash-loan", "defi"
        ],
        crawl_config=CrawlConfig(
            max_depth=4,
            max_pages=3000,
            use_javascript=True,
        ),
        tags=["audit", "defi", "findings"],
    ))

    registry.add_source(KnowledgeSource(
        id="cantina",
        name="Cantina",
        description="Security audit and competition platform",
        category=SourceCategory.AUDIT_REPORTS,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://cantina.xyz",
        categories_covered=["reentrancy", "access-control", "logic"],
        crawl_config=CrawlConfig(max_depth=3, max_pages=2000),
        tags=["audit", "competition"],
    ))

    # =========================================================================
    # EXPLOIT DATABASES (CRITICAL)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="rekt-news",
        name="Rekt News",
        description="Comprehensive DeFi exploit news and analysis",
        category=SourceCategory.EXPLOIT_DATABASE,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.CRITICAL,
        url="https://rekt.news",
        categories_covered=[
            "reentrancy", "oracle", "flash-loan", "access-control",
            "governance", "bridge", "exploit"
        ],
        crawl_config=CrawlConfig(
            max_depth=3,
            max_pages=1000,
            include_patterns=["/news/", "/leaderboard/"],
        ),
        tags=["exploit", "news", "analysis"],
    ))

    registry.add_source(KnowledgeSource(
        id="defillama-hacks",
        name="DeFiLlama Hacks",
        description="DeFi hacks database with loss amounts and details",
        category=SourceCategory.EXPLOIT_DATABASE,
        source_type=SourceType.API,
        priority=SourcePriority.CRITICAL,
        url="https://defillama.com/hacks",
        api_endpoint="https://api.llama.fi/hacks",
        categories_covered=["exploit", "hack", "loss-tracking"],
        tags=["exploit", "api", "loss"],
    ))

    registry.add_source(KnowledgeSource(
        id="slowmist-hacked",
        name="SlowMist Hacked",
        description="Blockchain security incident database",
        category=SourceCategory.EXPLOIT_DATABASE,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://hacked.slowmist.io",
        categories_covered=["exploit", "incident", "forensics"],
        crawl_config=CrawlConfig(max_depth=2, max_pages=500),
        tags=["exploit", "forensics"],
    ))

    # =========================================================================
    # BUG BOUNTY PLATFORMS (HIGH)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="immunefi",
        name="Immunefi",
        description="Largest Web3 bug bounty platform with public reports",
        category=SourceCategory.BUG_BOUNTY,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://immunefi.com",
        categories_covered=[
            "reentrancy", "access-control", "oracle", "flash-loan", "critical"
        ],
        crawl_config=CrawlConfig(
            max_depth=3,
            max_pages=2000,
            use_javascript=True,
            include_patterns=["/bounty/", "/bug-fix/"],
        ),
        tags=["bounty", "critical", "rewards"],
    ))

    # =========================================================================
    # SECURITY RESEARCH (HIGH)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="trail-of-bits-blog",
        name="Trail of Bits Blog",
        description="Security research and vulnerability analysis",
        category=SourceCategory.SECURITY_RESEARCH,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://blog.trailofbits.com",
        categories_covered=[
            "reentrancy", "crypto", "formal-verification", "tooling"
        ],
        crawl_config=CrawlConfig(
            max_depth=2,
            max_pages=500,
            include_patterns=["/category/blockchain/", "/category/ethereum/"],
        ),
        tags=["research", "tools", "analysis"],
    ))

    registry.add_source(KnowledgeSource(
        id="openzeppelin-blog",
        name="OpenZeppelin Blog",
        description="Smart contract security best practices",
        category=SourceCategory.SECURITY_RESEARCH,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://blog.openzeppelin.com",
        categories_covered=["upgrade", "access-control", "token", "governance"],
        crawl_config=CrawlConfig(max_depth=2, max_pages=300),
        tags=["best-practices", "contracts", "research"],
    ))

    registry.add_source(KnowledgeSource(
        id="consensys-diligence",
        name="Consensys Diligence",
        description="Ethereum security best practices and research",
        category=SourceCategory.SECURITY_RESEARCH,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://consensys.io/diligence",
        categories_covered=["reentrancy", "access-control", "audit-methodology"],
        crawl_config=CrawlConfig(max_depth=3, max_pages=500),
        tags=["methodology", "research"],
    ))

    registry.add_source(KnowledgeSource(
        id="samczsun-blog",
        name="samczsun Blog",
        description="Paradigm researcher's security insights",
        category=SourceCategory.SECURITY_RESEARCH,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://samczsun.com",
        categories_covered=["exploit", "mev", "defi", "analysis"],
        crawl_config=CrawlConfig(max_depth=2, max_pages=100),
        tags=["researcher", "analysis", "mev"],
    ))

    # =========================================================================
    # GITHUB REPOSITORIES (CRITICAL)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="swc-registry",
        name="Smart Contract Weakness Classification",
        description="SWC registry of smart contract vulnerabilities",
        category=SourceCategory.GITHUB_REPOS,
        source_type=SourceType.GITHUB_MARKDOWN,
        priority=SourcePriority.CRITICAL,
        url="https://swcregistry.io",
        github_repo="SmartContractSecurity/SWC-registry",
        github_path="entries",
        categories_covered=[
            "reentrancy", "access-control", "oracle", "dos", "crypto", "logic"
        ],
        crawl_config=CrawlConfig(max_depth=3),
        tags=["classification", "standards", "swc"],
    ))

    registry.add_source(KnowledgeSource(
        id="not-so-smart-contracts",
        name="Not So Smart Contracts",
        description="Trail of Bits vulnerable contract examples",
        category=SourceCategory.GITHUB_REPOS,
        source_type=SourceType.GITHUB_REPO,
        priority=SourcePriority.HIGH,
        url="https://github.com/crytic/not-so-smart-contracts",
        github_repo="crytic/not-so-smart-contracts",
        categories_covered=["reentrancy", "access-control", "dos", "logic"],
        tags=["examples", "vulnerable", "educational"],
    ))

    registry.add_source(KnowledgeSource(
        id="building-secure-contracts",
        name="Building Secure Contracts",
        description="Trail of Bits secure development guidelines",
        category=SourceCategory.GITHUB_REPOS,
        source_type=SourceType.GITHUB_MARKDOWN,
        priority=SourcePriority.HIGH,
        url="https://github.com/crytic/building-secure-contracts",
        github_repo="crytic/building-secure-contracts",
        categories_covered=[
            "development", "testing", "guidelines", "token", "governance"
        ],
        tags=["guidelines", "development", "best-practices"],
    ))

    registry.add_source(KnowledgeSource(
        id="solcurity",
        name="Solcurity",
        description="Opinionated security checklist for smart contracts",
        category=SourceCategory.GITHUB_REPOS,
        source_type=SourceType.GITHUB_MARKDOWN,
        priority=SourcePriority.HIGH,
        url="https://github.com/transmissions11/solcurity",
        github_repo="transmissions11/solcurity",
        categories_covered=["checklist", "all"],
        tags=["checklist", "comprehensive"],
    ))

    registry.add_source(KnowledgeSource(
        id="defi-vulns",
        name="DeFi Vulnerabilities",
        description="Collection of DeFi vulnerability patterns",
        category=SourceCategory.GITHUB_REPOS,
        source_type=SourceType.GITHUB_MARKDOWN,
        priority=SourcePriority.HIGH,
        url="https://github.com/SunWeb3Sec/DeFiVulnLabs",
        github_repo="SunWeb3Sec/DeFiVulnLabs",
        categories_covered=[
            "reentrancy", "oracle", "flash-loan", "token", "defi"
        ],
        tags=["defi", "labs", "examples"],
    ))

    # =========================================================================
    # CODE EXAMPLES / CHALLENGES (HIGH)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="damn-vulnerable-defi",
        name="Damn Vulnerable DeFi",
        description="CTF-style DeFi security challenges",
        category=SourceCategory.CODE_EXAMPLES,
        source_type=SourceType.GITHUB_REPO,
        priority=SourcePriority.HIGH,
        url="https://www.damnvulnerabledefi.xyz",
        github_repo="tinchoabbate/damn-vulnerable-defi",
        categories_covered=[
            "reentrancy", "flash-loan", "oracle", "governance", "upgrade"
        ],
        tags=["ctf", "challenges", "defi"],
    ))

    registry.add_source(KnowledgeSource(
        id="ethernaut",
        name="Ethernaut",
        description="OpenZeppelin's Web3/Solidity security game",
        category=SourceCategory.CODE_EXAMPLES,
        source_type=SourceType.GITHUB_REPO,
        priority=SourcePriority.HIGH,
        url="https://ethernaut.openzeppelin.com",
        github_repo="OpenZeppelin/ethernaut",
        categories_covered=["reentrancy", "access-control", "crypto", "logic"],
        tags=["ctf", "game", "educational"],
    ))

    registry.add_source(KnowledgeSource(
        id="capture-the-ether",
        name="Capture The Ether",
        description="Ethereum security game challenges",
        category=SourceCategory.CODE_EXAMPLES,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.MEDIUM,
        url="https://capturetheether.com",
        categories_covered=["crypto", "logic", "math"],
        tags=["ctf", "game"],
    ))

    # =========================================================================
    # EDUCATIONAL CONTENT - BLOGS (MEDIUM)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="medium-blockchain-security",
        name="Medium - Blockchain Security",
        description="Security articles on Medium platform",
        category=SourceCategory.BLOG_POSTS,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.MEDIUM,
        url="https://medium.com/tag/blockchain-security",
        categories_covered=["all"],
        crawl_config=CrawlConfig(
            max_depth=2,
            max_pages=500,
            use_javascript=True,
            virtual_scroll=True,
        ),
        tags=["blog", "articles", "varied"],
    ))

    registry.add_source(KnowledgeSource(
        id="hackernoon-web3-security",
        name="HackerNoon Web3 Security",
        description="Web3 security articles on HackerNoon",
        category=SourceCategory.BLOG_POSTS,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.MEDIUM,
        url="https://hackernoon.com/tagged/web3-security",
        categories_covered=["all"],
        crawl_config=CrawlConfig(max_depth=2, max_pages=300),
        tags=["blog", "articles"],
    ))

    # =========================================================================
    # OFFICIAL DOCUMENTATION (HIGH)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="solidity-docs",
        name="Solidity Documentation",
        description="Official Solidity language documentation",
        category=SourceCategory.OFFICIAL_DOCS,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://docs.soliditylang.org",
        categories_covered=["language", "security", "patterns"],
        crawl_config=CrawlConfig(
            max_depth=4,
            max_pages=500,
            include_patterns=["/security/", "/common-patterns/"],
        ),
        tags=["official", "language", "reference"],
    ))

    registry.add_source(KnowledgeSource(
        id="openzeppelin-docs",
        name="OpenZeppelin Contracts Docs",
        description="OpenZeppelin contracts documentation",
        category=SourceCategory.FRAMEWORK_DOCS,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.HIGH,
        url="https://docs.openzeppelin.com/contracts",
        categories_covered=["token", "access-control", "upgrade", "governance"],
        crawl_config=CrawlConfig(max_depth=3, max_pages=300),
        tags=["library", "standards", "reference"],
    ))

    registry.add_source(KnowledgeSource(
        id="eips",
        name="Ethereum Improvement Proposals",
        description="EIP standards and security considerations",
        category=SourceCategory.OFFICIAL_DOCS,
        source_type=SourceType.GITHUB_MARKDOWN,
        priority=SourcePriority.HIGH,
        url="https://eips.ethereum.org",
        github_repo="ethereum/EIPs",
        github_path="EIPS",
        categories_covered=["standards", "token", "governance"],
        crawl_config=CrawlConfig(
            include_patterns=["eip-20", "eip-721", "eip-1155", "eip-4626"],
        ),
        tags=["standards", "official"],
    ))

    # =========================================================================
    # CHECKLISTS & FRAMEWORKS (HIGH)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="scsvs",
        name="Smart Contract Security Verification Standard",
        description="OWASP-style verification standard for smart contracts",
        category=SourceCategory.CHECKLISTS,
        source_type=SourceType.GITHUB_MARKDOWN,
        priority=SourcePriority.HIGH,
        url="https://github.com/securing/SCSVS",
        github_repo="securing/SCSVS",
        categories_covered=["all", "checklist", "verification"],
        tags=["standard", "verification", "comprehensive"],
    ))

    registry.add_source(KnowledgeSource(
        id="secureum-mindmap",
        name="Secureum Security Mindmap",
        description="Comprehensive security mindmap from Secureum",
        category=SourceCategory.CHECKLISTS,
        source_type=SourceType.GITHUB_MARKDOWN,
        priority=SourcePriority.HIGH,
        url="https://github.com/x676f64/secureum-mind_map",
        github_repo="x676f64/secureum-mind_map",
        categories_covered=["all", "mindmap", "comprehensive"],
        tags=["mindmap", "comprehensive", "educational"],
    ))

    registry.add_source(KnowledgeSource(
        id="simple-security-toolkit",
        name="Simple Security Toolkit",
        description="Nascent's simple security toolkit for audits",
        category=SourceCategory.CHECKLISTS,
        source_type=SourceType.GITHUB_MARKDOWN,
        priority=SourcePriority.MEDIUM,
        url="https://github.com/nascentxyz/simple-security-toolkit",
        github_repo="nascentxyz/simple-security-toolkit",
        categories_covered=["checklist", "methodology"],
        tags=["toolkit", "audit", "methodology"],
    ))

    # =========================================================================
    # VIDEO CONTENT (MEDIUM)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="youtube-smart-contract-programmer",
        name="Smart Contract Programmer",
        description="Educational YouTube channel on Solidity security",
        category=SourceCategory.VIDEO_CONTENT,
        source_type=SourceType.YOUTUBE,
        priority=SourcePriority.MEDIUM,
        url="https://www.youtube.com/@smartcontractprogrammer",
        categories_covered=["educational", "tutorials", "defi"],
        notes="Requires YouTube transcript extraction",
        tags=["video", "tutorials", "educational"],
    ))

    registry.add_source(KnowledgeSource(
        id="youtube-patrick-collins",
        name="Patrick Collins - Cyfrin",
        description="Cyfrin audits and educational content",
        category=SourceCategory.VIDEO_CONTENT,
        source_type=SourceType.YOUTUBE,
        priority=SourcePriority.MEDIUM,
        url="https://www.youtube.com/@PatrickAlphaC",
        categories_covered=["educational", "auditing", "defi"],
        notes="Requires YouTube transcript extraction",
        tags=["video", "tutorials", "auditing"],
    ))

    # =========================================================================
    # COURSES (MEDIUM)
    # =========================================================================

    registry.add_source(KnowledgeSource(
        id="secureum-epoch0",
        name="Secureum Epoch 0",
        description="Secureum security bootcamp materials",
        category=SourceCategory.COURSES,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.MEDIUM,
        url="https://secureum.substack.com",
        categories_covered=["all", "educational", "comprehensive"],
        crawl_config=CrawlConfig(max_depth=2, max_pages=200),
        tags=["course", "bootcamp", "comprehensive"],
    ))

    registry.add_source(KnowledgeSource(
        id="updraft-security",
        name="Cyfrin Updraft Security",
        description="Cyfrin's comprehensive security course",
        category=SourceCategory.COURSES,
        source_type=SourceType.WEBSITE,
        priority=SourcePriority.MEDIUM,
        url="https://updraft.cyfrin.io",
        categories_covered=["all", "educational"],
        crawl_config=CrawlConfig(max_depth=3, max_pages=300, use_javascript=True),
        tags=["course", "comprehensive"],
    ))

    return registry


# =============================================================================
# Source Statistics
# =============================================================================


def get_source_statistics(registry: SourceRegistry) -> Dict[str, Any]:
    """Get statistics about the source registry.

    Args:
        registry: Source registry to analyze

    Returns:
        Dictionary of statistics
    """
    sources = registry.get_all()

    by_category = {}
    for cat in SourceCategory:
        by_category[cat.value] = len(registry.get_by_category(cat))

    by_priority = {}
    for p in SourcePriority:
        by_priority[p.name] = len(registry.get_by_priority(p))

    by_type = {}
    for s in sources:
        type_name = s.source_type.value
        by_type[type_name] = by_type.get(type_name, 0) + 1

    # Vulnerability category coverage
    vuln_coverage = {}
    for s in sources:
        for cat in s.categories_covered:
            vuln_coverage[cat] = vuln_coverage.get(cat, 0) + 1

    return {
        "total_sources": len(sources),
        "by_category": by_category,
        "by_priority": by_priority,
        "by_type": by_type,
        "vuln_category_coverage": vuln_coverage,
        "critical_sources": len(registry.get_by_priority(SourcePriority.CRITICAL)),
        "high_priority_sources": len(registry.get_by_priority(SourcePriority.HIGH)),
    }
