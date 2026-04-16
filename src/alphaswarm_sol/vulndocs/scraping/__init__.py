"""Crawl4AI-based Scraping Infrastructure for VulnDocs.

This module provides intelligent web scraping capabilities using Crawl4AI
for extracting vulnerability knowledge from public sources.

Features:
1. Adaptive crawling - learns website patterns automatically
2. LLM-optimized markdown output - preserves structure for analysis
3. Docker-based deployment - isolated, scalable scraping
4. Rate limiting and politeness - respectful crawling
5. Content deduplication - intelligent merging

Usage:
    from alphaswarm_sol.vulndocs.scraping import VulnDocsCrawler

    crawler = VulnDocsCrawler()
    results = await crawler.crawl_source(source)
"""

from alphaswarm_sol.vulndocs.scraping.crawler import (
    CrawlResult,
    VulnDocsCrawler,
    crawl_source,
)

__all__ = [
    "CrawlResult",
    "VulnDocsCrawler",
    "crawl_source",
]
