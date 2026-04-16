"""Content Merger for VulnDocs.

Intelligently merges and deduplicates scraped content into
well-structured vulnerability knowledge documents.

Key Goals:
1. No duplicate information - deduplicate at paragraph level
2. Category organization - group by vulnerability category
3. Section structure - testing, business context, examples, links
4. Quality prioritization - keep highest quality content
5. Source attribution - track where content came from
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from alphaswarm_sol.vulndocs.schema import VulnCategory


@dataclass
class ContentSection:
    """A section of merged content."""

    section_type: str  # overview, detection, testing, business, examples, links
    content: str
    sources: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    token_estimate: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "section_type": self.section_type,
            "content": self.content,
            "sources": self.sources,
            "quality_score": self.quality_score,
            "token_estimate": self.token_estimate,
        }


@dataclass
class MergedCategory:
    """Merged content for a vulnerability category."""

    category: str
    subcategory: str = ""
    sections: Dict[str, ContentSection] = field(default_factory=dict)
    total_sources: int = 0
    total_tokens: int = 0
    content_hashes: Set[str] = field(default_factory=set)

    def add_section(self, section: ContentSection) -> None:
        """Add or merge a section."""
        if section.section_type in self.sections:
            # Merge with existing
            existing = self.sections[section.section_type]
            existing.content += "\n\n" + section.content
            existing.sources.extend(section.sources)
            existing.quality_score = max(existing.quality_score, section.quality_score)
            existing.token_estimate += section.token_estimate
        else:
            self.sections[section.section_type] = section
        self.total_tokens += section.token_estimate

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "sections": {k: v.to_dict() for k, v in self.sections.items()},
            "total_sources": self.total_sources,
            "total_tokens": self.total_tokens,
        }

    def to_markdown(self) -> str:
        """Generate merged markdown document."""
        lines = [
            f"# {self.category.replace('-', ' ').title()}",
            "",
        ]

        if self.subcategory:
            lines.append(f"## Subcategory: {self.subcategory}")
            lines.append("")

        # Standard section order
        section_order = [
            "overview",
            "detection",
            "testing",
            "business",
            "examples",
            "exploitation",
            "remediation",
            "links",
        ]

        for section_type in section_order:
            if section_type in self.sections:
                section = self.sections[section_type]
                lines.append(f"## {section_type.title()}")
                lines.append("")
                lines.append(section.content)
                lines.append("")

                if section.sources:
                    lines.append("**Sources:**")
                    for source in section.sources[:5]:  # Limit displayed sources
                        lines.append(f"- {source}")
                    if len(section.sources) > 5:
                        lines.append(f"- ... and {len(section.sources) - 5} more")
                    lines.append("")

        return "\n".join(lines)


class ContentMerger:
    """Intelligent content merger for vulnerability knowledge.

    Merges scraped content from multiple sources into deduplicated,
    well-structured category documents.

    Features:
    1. Paragraph-level deduplication using content hashing
    2. Section detection and organization
    3. Quality scoring based on source authority
    4. Link extraction and categorization
    5. Code example preservation

    Usage:
        merger = ContentMerger()

        # Add content items from crawl results
        for item in crawl_result.content_items:
            merger.add_content(item)

        # Get merged categories
        merged = merger.get_merged_categories()

        # Export to markdown
        for category, content in merged.items():
            md = content.to_markdown()
    """

    # Section type detection patterns
    SECTION_PATTERNS = {
        "overview": [
            r"(?i)^#+\s*overview",
            r"(?i)^#+\s*introduction",
            r"(?i)^#+\s*summary",
            r"(?i)^#+\s*what is",
            r"(?i)^#+\s*description",
        ],
        "detection": [
            r"(?i)^#+\s*detection",
            r"(?i)^#+\s*how to detect",
            r"(?i)^#+\s*identifying",
            r"(?i)^#+\s*signals",
            r"(?i)^#+\s*indicators",
        ],
        "testing": [
            r"(?i)^#+\s*testing",
            r"(?i)^#+\s*test cases",
            r"(?i)^#+\s*how to test",
            r"(?i)^#+\s*verification",
            r"(?i)^#+\s*audit checklist",
        ],
        "business": [
            r"(?i)^#+\s*business",
            r"(?i)^#+\s*impact",
            r"(?i)^#+\s*risk",
            r"(?i)^#+\s*monetary",
            r"(?i)^#+\s*financial",
            r"(?i)^#+\s*user trust",
        ],
        "examples": [
            r"(?i)^#+\s*example",
            r"(?i)^#+\s*code",
            r"(?i)^#+\s*vulnerable",
            r"(?i)^#+\s*proof of concept",
            r"(?i)^#+\s*poc",
        ],
        "exploitation": [
            r"(?i)^#+\s*exploit",
            r"(?i)^#+\s*attack",
            r"(?i)^#+\s*how to exploit",
            r"(?i)^#+\s*exploitation",
        ],
        "remediation": [
            r"(?i)^#+\s*fix",
            r"(?i)^#+\s*remediation",
            r"(?i)^#+\s*mitigation",
            r"(?i)^#+\s*prevention",
            r"(?i)^#+\s*recommendation",
            r"(?i)^#+\s*solution",
        ],
        "links": [
            r"(?i)^#+\s*reference",
            r"(?i)^#+\s*link",
            r"(?i)^#+\s*resource",
            r"(?i)^#+\s*further reading",
            r"(?i)^#+\s*see also",
        ],
    }

    # Source authority scores
    SOURCE_AUTHORITY = {
        "solodit": 1.0,
        "code4rena": 0.95,
        "sherlock": 0.95,
        "immunefi": 0.9,
        "rekt-news": 0.9,
        "trail-of-bits": 0.95,
        "openzeppelin": 0.95,
        "swc-registry": 0.9,
        "consensys": 0.9,
        "secureum": 0.85,
        "medium": 0.6,
        "default": 0.5,
    }

    def __init__(self):
        self._content_hashes: Set[str] = set()
        self._categories: Dict[str, MergedCategory] = {}
        self._links_found: List[str] = []

    def add_content(
        self,
        content_item: Dict[str, Any],
        source_id: str = "",
    ) -> None:
        """Add a content item for merging.

        Args:
            content_item: Content item dictionary from crawler
            source_id: Source identifier for quality scoring
        """
        content = content_item.get("content", "")
        categories = content_item.get("categories", [])
        url = content_item.get("url", "")

        if not content or not categories:
            return

        # Extract sections from content
        sections = self._extract_sections(content, url, source_id)

        # Add to each relevant category
        for category in categories:
            self._add_to_category(category, sections, source_id)

    def _extract_sections(
        self,
        content: str,
        url: str,
        source_id: str,
    ) -> List[ContentSection]:
        """Extract sections from content.

        Args:
            content: Raw markdown content
            url: Source URL
            source_id: Source identifier

        Returns:
            List of ContentSections
        """
        sections = []
        current_section = "overview"  # Default section
        current_content: List[str] = []

        lines = content.split("\n")

        for line in lines:
            # Check for section headers
            new_section = self._detect_section_type(line)
            if new_section and new_section != current_section:
                # Save current section
                if current_content:
                    section_text = "\n".join(current_content).strip()
                    if section_text and not self._is_duplicate(section_text):
                        sections.append(ContentSection(
                            section_type=current_section,
                            content=section_text,
                            sources=[url],
                            quality_score=self._get_quality_score(source_id),
                            token_estimate=len(section_text) // 4,
                        ))
                current_section = new_section
                current_content = []
            else:
                current_content.append(line)

        # Add final section
        if current_content:
            section_text = "\n".join(current_content).strip()
            if section_text and not self._is_duplicate(section_text):
                sections.append(ContentSection(
                    section_type=current_section,
                    content=section_text,
                    sources=[url],
                    quality_score=self._get_quality_score(source_id),
                    token_estimate=len(section_text) // 4,
                ))

        # Extract links
        self._extract_links(content)

        return sections

    def _detect_section_type(self, line: str) -> Optional[str]:
        """Detect section type from a line.

        Args:
            line: Line to check

        Returns:
            Section type or None
        """
        for section_type, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, line):
                    return section_type
        return None

    def _is_duplicate(self, content: str) -> bool:
        """Check if content is a duplicate.

        Uses paragraph-level hashing for deduplication.

        Args:
            content: Content to check

        Returns:
            True if duplicate
        """
        # Hash at paragraph level
        paragraphs = content.split("\n\n")
        is_duplicate = True

        for para in paragraphs:
            para = para.strip()
            if len(para) > 50:  # Skip short paragraphs
                para_hash = hashlib.md5(para.encode()).hexdigest()[:16]
                if para_hash not in self._content_hashes:
                    self._content_hashes.add(para_hash)
                    is_duplicate = False

        return is_duplicate

    def _get_quality_score(self, source_id: str) -> float:
        """Get quality score based on source authority.

        Args:
            source_id: Source identifier

        Returns:
            Quality score (0-1)
        """
        # Check for partial matches
        for key, score in self.SOURCE_AUTHORITY.items():
            if key in source_id.lower():
                return score
        return self.SOURCE_AUTHORITY["default"]

    def _extract_links(self, content: str) -> None:
        """Extract and collect links from content.

        Args:
            content: Content to extract links from
        """
        # Extract markdown links
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        matches = re.findall(link_pattern, content)

        for _, url in matches:
            if url.startswith("http") and url not in self._links_found:
                self._links_found.append(url)

        # Extract raw URLs
        url_pattern = r"https?://[^\s\)\]\"'<>]+"
        raw_urls = re.findall(url_pattern, content)
        for url in raw_urls:
            if url not in self._links_found:
                self._links_found.append(url)

    def _add_to_category(
        self,
        category: str,
        sections: List[ContentSection],
        source_id: str,
    ) -> None:
        """Add sections to a category.

        Args:
            category: Category identifier
            sections: Sections to add
            source_id: Source identifier
        """
        if category not in self._categories:
            self._categories[category] = MergedCategory(category=category)

        merged = self._categories[category]
        merged.total_sources += 1

        for section in sections:
            merged.add_section(section)

    def get_merged_categories(self) -> Dict[str, MergedCategory]:
        """Get all merged categories.

        Returns:
            Dictionary of category -> MergedCategory
        """
        return self._categories

    def get_category(self, category: str) -> Optional[MergedCategory]:
        """Get a specific merged category.

        Args:
            category: Category identifier

        Returns:
            MergedCategory or None
        """
        return self._categories.get(category)

    def get_all_links(self) -> List[str]:
        """Get all extracted links.

        Returns:
            List of URLs
        """
        return self._links_found

    def get_statistics(self) -> Dict[str, Any]:
        """Get merger statistics.

        Returns:
            Statistics dictionary
        """
        total_sections = 0
        total_tokens = 0

        for cat in self._categories.values():
            total_sections += len(cat.sections)
            total_tokens += cat.total_tokens

        return {
            "categories_merged": len(self._categories),
            "total_sections": total_sections,
            "total_tokens": total_tokens,
            "unique_content_blocks": len(self._content_hashes),
            "links_extracted": len(self._links_found),
        }

    def export_all(self, output_dir: "Path") -> Dict[str, "Path"]:
        """Export all merged categories to markdown files.

        Args:
            output_dir: Output directory

        Returns:
            Dictionary of category -> file path
        """
        from pathlib import Path

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        paths = {}
        for category, merged in self._categories.items():
            filepath = output_dir / f"{category}.md"
            with open(filepath, "w") as f:
                f.write(merged.to_markdown())
            paths[category] = filepath

        # Export links
        links_path = output_dir / "extracted_links.txt"
        with open(links_path, "w") as f:
            for link in self._links_found:
                f.write(link + "\n")
        paths["_links"] = links_path

        return paths


# =============================================================================
# Convenience Functions
# =============================================================================


def merge_content_items(
    items: List[Dict[str, Any]],
    source_id: str = "",
) -> Dict[str, MergedCategory]:
    """Convenience function to merge content items.

    Args:
        items: List of content item dictionaries
        source_id: Source identifier

    Returns:
        Dictionary of category -> MergedCategory
    """
    merger = ContentMerger()
    for item in items:
        merger.add_content(item, source_id)
    return merger.get_merged_categories()
