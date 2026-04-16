"""Coverage Analysis for VulnDocs Knowledge System.

Task 18.13d: Identify pattern gaps in vulnerability knowledge.

This module provides tools for:
- Analyzing knowledge base coverage across categories
- Identifying gaps in vulnerability documentation
- Mapping patterns to knowledge documents
- Detecting missing detection guidance
- Generating coverage reports

Per PHILOSOPHY.md:
- Coverage analysis must be threat-model driven
- Each attack surface maps to at least one pattern
- New patterns specify which threat they address
"""

from alphaswarm_sol.vulndocs.analysis.coverage import (
    CoverageAnalyzer,
    CoverageReport,
    CoverageGap,
    PatternMapping,
    CategoryCoverage,
)
from alphaswarm_sol.vulndocs.analysis.gaps import (
    GapFinder,
    GapType,
    GapSeverity,
    KnowledgeGap,
)
from alphaswarm_sol.vulndocs.analysis.reports import (
    ReportGenerator,
    ReportFormat,
    CoverageMatrix,
)

__all__ = [
    # Coverage
    "CoverageAnalyzer",
    "CoverageReport",
    "CoverageGap",
    "PatternMapping",
    "CategoryCoverage",
    # Gaps
    "GapFinder",
    "GapType",
    "GapSeverity",
    "KnowledgeGap",
    # Reports
    "ReportGenerator",
    "ReportFormat",
    "CoverageMatrix",
]
