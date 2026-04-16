"""Reference Extraction Utilities for VulnDocs.

This module provides utilities for extracting and validating source references
from VulnDocs entries, and managing the canonical URL provenance ledger.

Key features:
- Extract URLs from vulndocs/**/index.yaml sources/references fields
- Extract URLs from vulndocs/**/research/*.md files
- Deduplicate by URL, preserving first-seen metadata
- Append-only updates to .vrs/corpus/metadata/urls.yaml

Per Phase 7.2 CONTEXT.md:
- Every visited URL must be logged with timestamp, query, and extraction status
- URL log is append-only (never delete for audit trail)

Schema per entry (from CONTEXT.md):
- url: Full URL accessed
- accessed_at: ISO 8601 timestamp
- query: Search query that led to this URL
- category: VulnDocs category (e.g., "oracle/sequencer-uptime")
- agent: Agent/skill that accessed this URL
- extracted: Whether content was extracted and used
- notes: Additional context

Part of Plan 07.2-02: VulnDocs Reference Extraction
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# URL pattern for extraction from markdown and YAML
URL_PATTERN = re.compile(
    r'https?://[^\s\)\]\>\"\'\,]+',
    re.IGNORECASE,
)


@dataclass
class URLEntry:
    """A URL provenance entry for the ledger.

    Attributes:
        url: Full URL accessed
        accessed_at: ISO 8601 timestamp
        query: Search query that led to this URL
        category: VulnDocs category path
        agent: Agent/skill that accessed this URL
        extracted: Whether content was extracted and used
        notes: Additional context
    """

    url: str
    accessed_at: str
    query: str
    category: str
    agent: str
    extracted: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "url": self.url,
            "accessed_at": self.accessed_at,
            "query": self.query,
            "category": self.category,
            "agent": self.agent,
            "extracted": self.extracted,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "URLEntry":
        """Create from dictionary."""
        return cls(
            url=data.get("url", ""),
            accessed_at=data.get("accessed_at", ""),
            query=data.get("query", ""),
            category=data.get("category", ""),
            agent=data.get("agent", ""),
            extracted=data.get("extracted", False),
            notes=data.get("notes", ""),
        )


@dataclass
class ExtractionResult:
    """Result of extracting references from VulnDocs.

    Attributes:
        entries: List of extracted URL entries
        source_files: List of source files processed
        errors: List of errors encountered
        duplicates_skipped: Count of duplicate URLs skipped
    """

    entries: list[URLEntry] = field(default_factory=list)
    source_files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duplicates_skipped: int = 0


@dataclass
class URLLedger:
    """Manager for the URL provenance ledger.

    The ledger is append-only - entries are never deleted.
    Duplicate URLs are skipped, preserving first-seen metadata.
    """

    path: Path
    schema_version: str = "1.0"
    entries: list[URLEntry] = field(default_factory=list)
    _existing_urls: set[str] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        """Load existing entries on initialization."""
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        """Load existing entries from YAML file."""
        with open(self.path, "r") as f:
            data = yaml.safe_load(f)

        if data:
            self.schema_version = data.get("schema_version", "1.0")
            for entry_data in data.get("entries", []):
                entry = URLEntry.from_dict(entry_data)
                self.entries.append(entry)
                self._existing_urls.add(entry.url)

    def has_url(self, url: str) -> bool:
        """Check if URL already exists in ledger."""
        return url in self._existing_urls

    def add_entry(self, entry: URLEntry) -> bool:
        """Add entry if URL doesn't already exist.

        Args:
            entry: URL entry to add

        Returns:
            bool: True if added, False if duplicate
        """
        if self.has_url(entry.url):
            return False

        self.entries.append(entry)
        self._existing_urls.add(entry.url)
        return True

    def add_entries(self, entries: list[URLEntry]) -> int:
        """Add multiple entries, skipping duplicates.

        Args:
            entries: List of URL entries to add

        Returns:
            int: Count of entries actually added
        """
        added = 0
        for entry in entries:
            if self.add_entry(entry):
                added += 1
        return added

    def save(self) -> None:
        """Save ledger to YAML file (append-only behavior preserved)."""
        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "schema_version": self.schema_version,
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "entries": [entry.to_dict() for entry in self.entries],
        }

        # Write with comments header
        header = """# URL Provenance Ledger
# Tracks every URL accessed during corpus research/ingestion
# Required per Phase 7.2 CONTEXT.md: "Every visited URL must be logged"
#
# Schema version: 1.0

"""
        with open(self.path, "w") as f:
            f.write(header)
            yaml.dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)


def extract_urls_from_text(text: str) -> list[str]:
    """Extract all URLs from text.

    Args:
        text: Text content to extract URLs from

    Returns:
        list[str]: List of unique URLs found
    """
    matches = URL_PATTERN.findall(text)
    # Clean up trailing punctuation that might be captured
    cleaned = []
    for url in matches:
        # Remove common trailing characters that aren't part of URLs
        url = url.rstrip(".,;:!?)")
        # Handle markdown link syntax
        if url.endswith("]"):
            url = url[:-1]
        cleaned.append(url)
    return list(set(cleaned))


def extract_urls_from_yaml_sources(data: dict[str, Any]) -> list[str]:
    """Extract URLs from VulnDoc index.yaml sources/references fields.

    Args:
        data: Parsed YAML data from index.yaml

    Returns:
        list[str]: List of unique URLs found
    """
    urls = []

    # Check 'sources' field (list of strings or dicts)
    sources = data.get("sources", [])
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, str):
                urls.extend(extract_urls_from_text(source))
            elif isinstance(source, dict):
                # Source might have a 'url' field
                if "url" in source:
                    urls.append(source["url"])
                # Or embedded in text fields
                for key in ["reference", "link", "href"]:
                    if key in source:
                        urls.extend(extract_urls_from_text(str(source[key])))

    # Check 'references' field
    references = data.get("references", [])
    if isinstance(references, list):
        for ref in references:
            if isinstance(ref, str):
                urls.extend(extract_urls_from_text(ref))
            elif isinstance(ref, dict):
                if "url" in ref:
                    urls.append(ref["url"])
                for key in ["reference", "link", "href"]:
                    if key in ref:
                        urls.extend(extract_urls_from_text(str(ref[key])))

    # Check 'related_exploits' field (might contain URLs)
    related_exploits = data.get("related_exploits", [])
    if isinstance(related_exploits, list):
        for exploit in related_exploits:
            if isinstance(exploit, str):
                urls.extend(extract_urls_from_text(exploit))
            elif isinstance(exploit, dict):
                for key in ["url", "reference", "link", "report"]:
                    if key in exploit:
                        urls.extend(extract_urls_from_text(str(exploit[key])))

    return list(set(urls))


def extract_from_vulndocs(
    vulndocs_root: Path,
    category_filter: str | None = None,
    agent: str = "reference_extract",
) -> ExtractionResult:
    """Extract all URLs from VulnDocs index.yaml and research files.

    Scans:
    - vulndocs/**/index.yaml (sources, references, related_exploits)
    - vulndocs/**/research/*.md (embedded URLs)

    Args:
        vulndocs_root: Path to vulndocs directory
        category_filter: Optional category to filter (e.g., "oracle")
        agent: Agent name to record in provenance

    Returns:
        ExtractionResult with all extracted entries
    """
    result = ExtractionResult()
    seen_urls: set[str] = set()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not vulndocs_root.exists():
        result.errors.append(f"VulnDocs root not found: {vulndocs_root}")
        return result

    # Find all index.yaml files
    index_files = list(vulndocs_root.glob("**/index.yaml"))

    for index_path in index_files:
        # Determine category from path
        rel_path = index_path.relative_to(vulndocs_root)
        parts = rel_path.parts[:-1]  # Remove 'index.yaml'

        if len(parts) == 0:
            continue  # Skip root-level files

        # Build category path (e.g., "oracle/price-manipulation")
        category = "/".join(parts)

        # Apply filter if specified
        if category_filter and not category.startswith(category_filter):
            continue

        try:
            with open(index_path, "r") as f:
                data = yaml.safe_load(f)

            if not data:
                continue

            result.source_files.append(index_path)

            # Extract URLs from index.yaml
            urls = extract_urls_from_yaml_sources(data)

            for url in urls:
                if url in seen_urls:
                    result.duplicates_skipped += 1
                    continue

                seen_urls.add(url)
                entry = URLEntry(
                    url=url,
                    accessed_at=timestamp,
                    query=f"vulndocs_index:{category}",
                    category=category,
                    agent=agent,
                    extracted=True,
                    notes=f"Extracted from {rel_path}",
                )
                result.entries.append(entry)

        except yaml.YAMLError as e:
            result.errors.append(f"YAML error in {index_path}: {e}")
        except Exception as e:
            result.errors.append(f"Error reading {index_path}: {e}")

    # Find all research markdown files
    research_files = list(vulndocs_root.glob("**/research/*.md"))

    for md_path in research_files:
        # Determine category from path
        rel_path = md_path.relative_to(vulndocs_root)
        parts = rel_path.parts[:-2]  # Remove 'research/file.md'

        if len(parts) == 0:
            continue

        category = "/".join(parts)

        # Apply filter if specified
        if category_filter and not category.startswith(category_filter):
            continue

        try:
            with open(md_path, "r") as f:
                content = f.read()

            result.source_files.append(md_path)

            # Extract URLs from markdown
            urls = extract_urls_from_text(content)

            for url in urls:
                if url in seen_urls:
                    result.duplicates_skipped += 1
                    continue

                seen_urls.add(url)
                entry = URLEntry(
                    url=url,
                    accessed_at=timestamp,
                    query=f"vulndocs_research:{category}",
                    category=category,
                    agent=agent,
                    extracted=True,
                    notes=f"Extracted from research/{md_path.name}",
                )
                result.entries.append(entry)

        except Exception as e:
            result.errors.append(f"Error reading {md_path}: {e}")

    return result


def update_ledger(
    ledger_path: Path,
    extraction_result: ExtractionResult,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Update the URL ledger with extracted entries.

    Args:
        ledger_path: Path to urls.yaml ledger
        extraction_result: Result from extract_from_vulndocs
        dry_run: If True, don't actually write changes

    Returns:
        tuple[int, int]: (entries_added, entries_skipped)
    """
    ledger = URLLedger(ledger_path)

    added = 0
    skipped = 0

    for entry in extraction_result.entries:
        if ledger.has_url(entry.url):
            skipped += 1
        else:
            if not dry_run:
                ledger.add_entry(entry)
            added += 1

    if not dry_run and added > 0:
        ledger.save()

    return added, skipped


def find_missing_provenance(
    vulndocs_root: Path,
    ledger_path: Path,
) -> list[tuple[str, str]]:
    """Find VulnDocs URLs that are not yet in the ledger.

    Args:
        vulndocs_root: Path to vulndocs directory
        ledger_path: Path to urls.yaml ledger

    Returns:
        list[tuple[str, str]]: List of (url, category) tuples missing from ledger
    """
    # Extract all URLs
    extraction = extract_from_vulndocs(vulndocs_root)

    # Load existing ledger
    ledger = URLLedger(ledger_path)

    # Find missing
    missing = []
    for entry in extraction.entries:
        if not ledger.has_url(entry.url):
            missing.append((entry.url, entry.category))

    return missing


def generate_provenance_report(
    vulndocs_root: Path,
    ledger_path: Path,
) -> dict[str, Any]:
    """Generate a report on VulnDocs provenance coverage.

    Args:
        vulndocs_root: Path to vulndocs directory
        ledger_path: Path to urls.yaml ledger

    Returns:
        dict with coverage statistics and gaps
    """
    extraction = extract_from_vulndocs(vulndocs_root)
    ledger = URLLedger(ledger_path)

    # Categorize by coverage
    covered = []
    missing = []

    for entry in extraction.entries:
        if ledger.has_url(entry.url):
            covered.append(entry)
        else:
            missing.append(entry)

    # Group by category
    categories: dict[str, dict[str, int]] = {}
    for entry in extraction.entries:
        cat = entry.category.split("/")[0]  # Top-level category
        if cat not in categories:
            categories[cat] = {"total": 0, "covered": 0, "missing": 0}
        categories[cat]["total"] += 1
        if ledger.has_url(entry.url):
            categories[cat]["covered"] += 1
        else:
            categories[cat]["missing"] += 1

    return {
        "total_urls": len(extraction.entries),
        "covered": len(covered),
        "missing": len(missing),
        "coverage_pct": (len(covered) / len(extraction.entries) * 100) if extraction.entries else 100.0,
        "ledger_total": len(ledger.entries),
        "categories": categories,
        "missing_urls": [(e.url, e.category) for e in missing[:20]],  # First 20 for brevity
        "errors": extraction.errors,
    }
