"""URL ingestion infrastructure for VulnDocs.

Phase 5.7: Automated ingestion of vulnerability knowledge from URLs.

This module provides:
- URLIngester: Main orchestration class for URL ingestion
- Categorizer: Auto-categorization into vulndocs/ hierarchy
- ContentExtractor: Pattern and documentation extraction
- IngestionResult: Result dataclass for ingestion operations

Usage:
    from alphaswarm_sol.vulndocs.ingestion import URLIngester, IngestionResult

    ingester = URLIngester(vulndocs_root=Path("vulndocs"))
    result = await ingester.ingest(
        url="https://example.com/vulnerability",
        category=None,  # auto-categorize
        dry_run=False,
        quality_threshold="draft"
    )

    if result.success:
        print(f"Created: {result.path}")
"""

from alphaswarm_sol.vulndocs.ingestion.ingester import (
    URLIngester,
    IngestionResult,
    IngestionConfig,
    DryRunResult,
    QualityGateResult,
)
from alphaswarm_sol.vulndocs.ingestion.categorizer import (
    Categorizer,
    VulndocPath,
    CategoryScore,
)
from alphaswarm_sol.vulndocs.ingestion.extractor import (
    ContentExtractor,
    ExtractedContent,
    ExtractedPattern,
    QualityLevel,
)

__all__ = [
    # Main ingestion
    "URLIngester",
    "IngestionResult",
    "IngestionConfig",
    "DryRunResult",
    "QualityGateResult",
    # Categorization
    "Categorizer",
    "VulndocPath",
    "CategoryScore",
    # Extraction
    "ContentExtractor",
    "ExtractedContent",
    "ExtractedPattern",
    "QualityLevel",
]
