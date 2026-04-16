"""Content Processing Pipeline for VulnDocs.

This module handles the processing, deduplication, and intelligent
merging of scraped vulnerability knowledge content.

Key Features:
1. Content deduplication - avoid redundant information
2. Category-based merging - combine content by vulnerability category
3. Quality scoring - prioritize high-value content
4. Structure extraction - pull out testing techniques, business context
5. Link extraction - identify additional resources
"""

from alphaswarm_sol.vulndocs.processing.merger import (
    ContentMerger,
    MergedCategory,
    merge_content_items,
)

__all__ = [
    "ContentMerger",
    "MergedCategory",
    "merge_content_items",
]
