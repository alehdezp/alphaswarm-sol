"""
Research Client

Integrates with Exa Search for:
- Vulnerability research
- CVE lookups
- Documentation search
- Code pattern search
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    score: float


@dataclass
class ResearchResults:
    """Collection of research results."""
    query: str
    results: List[SearchResult]
    total_found: int

    def to_context(self, max_chars: int = 10000) -> str:
        """Convert to LLM-friendly context string."""
        lines = [f"Research: {self.query}\n"]
        char_count = len(lines[0])

        for r in self.results:
            entry = f"\n## {r.title}\nURL: {r.url}\n{r.snippet}\n"
            if char_count + len(entry) > max_chars:
                break
            lines.append(entry)
            char_count += len(entry)

        return "".join(lines)


class ResearchClient:
    """
    Research client using Exa Search.

    Integrates with the exa-search MCP tools for:
    - Vulnerability research
    - CVE lookups
    - Documentation search
    - Code pattern search
    """

    async def search_vulnerabilities(
        self,
        topic: str,
        year: Optional[int] = None,
    ) -> ResearchResults:
        """Search for vulnerability information."""
        query = f"{topic} vulnerability exploit"
        if year:
            query += f" {year}"

        # Would call mcp__exa-search__web_search_exa
        # This is a placeholder for the integration
        return ResearchResults(
            query=query,
            results=[],
            total_found=0,
        )

    async def search_code_patterns(
        self,
        pattern: str,
        language: str = "solidity",
    ) -> ResearchResults:
        """Search for code patterns using Exa Code Search."""
        # Would call mcp__exa-search__get_code_context_exa
        return ResearchResults(
            query=f"{language} {pattern}",
            results=[],
            total_found=0,
        )

    async def search_documentation(
        self,
        topic: str,
        domains: Optional[List[str]] = None,
    ) -> ResearchResults:
        """Search for documentation."""
        domains = domains or ["docs.openzeppelin.com", "ethereum.org", "solidity.readthedocs.io"]
        # Would filter search to these domains
        return ResearchResults(
            query=topic,
            results=[],
            total_found=0,
        )
