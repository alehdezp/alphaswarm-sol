"""Main URL ingestion orchestration for VulnDocs.

Handles the full ingestion pipeline: fetch -> filter -> extract -> categorize -> insert.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from alphaswarm_sol.vulndocs.ingestion.categorizer import Categorizer, VulndocPath
from alphaswarm_sol.vulndocs.ingestion.extractor import (
    ContentExtractor,
    ExtractedContent,
    QualityLevel,
)


def _default_write_path() -> Path:
    """Get default vulndocs write path via centralized resolution."""
    from alphaswarm_sol.vulndocs.resolution import vulndocs_write_path
    return vulndocs_write_path()


@dataclass
class IngestionConfig:
    """Configuration for URL ingestion."""

    vulndocs_root: Path = field(default_factory=lambda: _default_write_path())
    dry_run: bool = False
    quality_threshold: QualityLevel = QualityLevel.DRAFT
    force: bool = False  # Force even if duplicate detected
    skip_filter: bool = False  # Skip relevance filtering


@dataclass
class DryRunResult:
    """Result of a dry-run ingestion."""

    url: str
    would_create: bool
    path: VulndocPath
    planned_actions: list[str]
    categorization: dict[str, Any]
    quality_gate: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML output."""
        return {
            "url": self.url,
            "would_create": self.would_create,
            "path": self.path.path,
            "planned_actions": self.planned_actions,
            "categorization": self.categorization,
            "quality_gate": self.quality_gate,
        }


@dataclass
class QualityGateResult:
    """Result of quality gate check."""

    passed: bool
    threshold: QualityLevel
    actual: QualityLevel
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "threshold": self.threshold.value,
            "actual": self.actual.value,
            "reason": self.reason,
        }


@dataclass
class IngestionResult:
    """Result of URL ingestion."""

    url: str
    success: bool
    action: str  # created, updated, skipped
    path: VulndocPath | None = None
    files_modified: list[str] = field(default_factory=list)
    patterns_created: list[str] = field(default_factory=list)
    quality: QualityLevel | None = None
    error: str | None = None
    skip_reason: str | None = None
    provenance_updated: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML output."""
        result: dict[str, Any] = {
            "url": self.url,
            "success": self.success,
            "action": self.action,
        }

        if self.path:
            result["path"] = self.path.path

        if self.files_modified:
            result["files_modified"] = self.files_modified

        if self.patterns_created:
            result["patterns_created"] = self.patterns_created

        if self.quality:
            result["quality"] = self.quality.value

        if self.error:
            result["error"] = self.error

        if self.skip_reason:
            result["skip_reason"] = self.skip_reason

        result["provenance_updated"] = self.provenance_updated

        return result


class URLIngester:
    """Main orchestration class for URL ingestion.

    Handles the complete pipeline:
    1. Fetch URL content
    2. Filter for Solidity relevance
    3. Extract patterns and documentation
    4. Categorize into vulndocs hierarchy
    5. Check for duplicates
    6. Insert content (if not dry-run)
    7. Update provenance tracking

    Example:
        ingester = URLIngester(vulndocs_root=Path("vulndocs"))
        result = await ingester.ingest(
            url="https://example.com/vulnerability",
            dry_run=True
        )
        print(result.to_dict())
    """

    def __init__(
        self,
        vulndocs_root: Path | None = None,
        categorizer: Categorizer | None = None,
        extractor: ContentExtractor | None = None,
    ):
        """Initialize the ingester.

        Args:
            vulndocs_root: Root path for vulndocs directory.
            categorizer: Custom categorizer (uses default if None).
            extractor: Custom extractor (uses default if None).
        """
        self.root = vulndocs_root or _default_write_path()
        self.categorizer = categorizer or Categorizer(self.root)
        self.extractor = extractor or ContentExtractor()

    async def ingest(
        self,
        url: str,
        category: str | None = None,
        dry_run: bool = False,
        quality_threshold: str | QualityLevel = "draft",
        force: bool = False,
    ) -> IngestionResult | DryRunResult:
        """Ingest vulnerability knowledge from URL.

        Args:
            url: URL to fetch and ingest.
            category: Force category (auto-categorize if None).
            dry_run: If True, show planned actions without inserting.
            quality_threshold: Minimum quality level (draft/ready/excellent).
            force: Force ingestion even if duplicate detected.

        Returns:
            IngestionResult or DryRunResult depending on dry_run flag.
        """
        # Normalize quality threshold
        if isinstance(quality_threshold, str):
            quality_threshold = QualityLevel(quality_threshold)

        # Step 1: Fetch content
        content = await self._fetch(url)
        if content is None:
            return IngestionResult(
                url=url,
                success=False,
                action="skipped",
                error="Failed to fetch URL",
                skip_reason="URL unreachable",
            )

        # Step 2: Filter for relevance (skip in tests if content provided)
        if not self._is_solidity_relevant(content):
            return IngestionResult(
                url=url,
                success=False,
                action="skipped",
                skip_reason="Not Solidity relevant",
            )

        # Step 3: Extract patterns and docs
        extracted = self.extractor.extract(content, url)

        # Step 4: Categorize
        target = self.categorizer.categorize(extracted, category)

        # Step 5: Check duplicates
        duplicates = self._check_duplicates(url, target)
        if duplicates and not force:
            return IngestionResult(
                url=url,
                success=False,
                action="skipped",
                skip_reason=f"Duplicate detected: {duplicates[0]}",
            )

        # Step 6: Check quality gate
        quality_result = self._check_quality_gate(extracted.quality, quality_threshold)
        if not quality_result.passed and not force:
            return IngestionResult(
                url=url,
                success=False,
                action="skipped",
                quality=extracted.quality,
                skip_reason=quality_result.reason,
            )

        # If dry-run, return planned actions
        if dry_run:
            return self._build_dry_run_result(url, target, extracted, quality_result)

        # Step 7: Insert content
        files_modified = await self._insert(extracted, target)

        # Step 8: Update provenance
        self._update_provenance(target, url, extracted)

        return IngestionResult(
            url=url,
            success=True,
            action="created" if not target.exists(self.root) else "updated",
            path=target,
            files_modified=files_modified,
            patterns_created=[p.id for p in extracted.patterns],
            quality=extracted.quality,
            provenance_updated=True,
        )

    async def ingest_batch(
        self,
        urls: list[str],
        category: str | None = None,
        dry_run: bool = False,
        quality_threshold: str | QualityLevel = "draft",
    ) -> list[IngestionResult | DryRunResult]:
        """Ingest multiple URLs.

        Args:
            urls: List of URLs to ingest.
            category: Force category for all (auto-categorize if None).
            dry_run: If True, show planned actions without inserting.
            quality_threshold: Minimum quality level.

        Returns:
            List of IngestionResult or DryRunResult.
        """
        results = []
        for url in urls:
            result = await self.ingest(
                url=url,
                category=category,
                dry_run=dry_run,
                quality_threshold=quality_threshold,
            )
            results.append(result)
        return results

    async def _fetch(self, url: str) -> str | None:
        """Fetch content from URL.

        Args:
            url: URL to fetch.

        Returns:
            Content string or None if fetch failed.
        """
        # In production, this would use httpx or similar
        # For now, return None to indicate external fetch needed
        # The skill will use WebFetch tool
        return None

    def _is_solidity_relevant(self, content: str) -> bool:
        """Check if content is relevant to Solidity security.

        Args:
            content: Fetched content.

        Returns:
            True if content appears Solidity-relevant.
        """
        # Keywords that indicate Solidity/smart contract security content
        relevance_keywords = [
            "solidity",
            "smart contract",
            "ethereum",
            "evm",
            "defi",
            "erc20",
            "erc721",
            "reentrancy",
            "vulnerability",
            "exploit",
            "audit",
            "wei",
            "gwei",
            "msg.sender",
            "msg.value",
            "require(",
            "revert(",
            "modifier",
            "payable",
            "delegatecall",
        ]

        content_lower = content.lower()
        matches = sum(1 for kw in relevance_keywords if kw.lower() in content_lower)

        # Require at least 3 keyword matches for relevance
        return matches >= 3

    def _check_duplicates(
        self, url: str, target: VulndocPath
    ) -> list[str]:
        """Check for duplicate content.

        Args:
            url: URL being ingested.
            target: Target vulndoc path.

        Returns:
            List of duplicate descriptions (empty if no duplicates).
        """
        duplicates = []

        # Check if URL already in provenance
        prov_path = target.to_path(self.root) / "provenance.yaml"
        if prov_path.exists():
            try:
                provenance = yaml.safe_load(prov_path.read_text())
                processed = provenance.get("processed_urls", [])
                for entry in processed:
                    if isinstance(entry, dict) and entry.get("url") == url:
                        duplicates.append(f"URL already processed in {target.path}")
                    elif isinstance(entry, str) and entry == url:
                        duplicates.append(f"URL already processed in {target.path}")
            except Exception:
                pass  # Ignore provenance read errors

        # Check if exact subcategory already exists
        if target.exists(self.root):
            # Check if it has content (not just empty scaffold)
            index_path = target.to_path(self.root) / "index.yaml"
            if index_path.exists():
                try:
                    index = yaml.safe_load(index_path.read_text())
                    if index.get("status") not in [None, "draft"]:
                        duplicates.append(f"Subcategory already exists: {target.path}")
                except Exception:
                    pass

        return duplicates

    def _check_quality_gate(
        self, actual: QualityLevel, threshold: QualityLevel
    ) -> QualityGateResult:
        """Check if content meets quality threshold.

        Args:
            actual: Actual quality level of content.
            threshold: Required quality threshold.

        Returns:
            QualityGateResult indicating pass/fail.
        """
        quality_order = {
            QualityLevel.DRAFT: 1,
            QualityLevel.READY: 2,
            QualityLevel.EXCELLENT: 3,
        }

        passed = quality_order[actual] >= quality_order[threshold]
        reason = "" if passed else (
            f"Content quality '{actual.value}' below threshold '{threshold.value}'"
        )

        return QualityGateResult(
            passed=passed,
            threshold=threshold,
            actual=actual,
            reason=reason,
        )

    def _build_dry_run_result(
        self,
        url: str,
        target: VulndocPath,
        extracted: ExtractedContent,
        quality_result: QualityGateResult,
    ) -> DryRunResult:
        """Build dry-run result showing planned actions.

        Args:
            url: URL being ingested.
            target: Target vulndoc path.
            extracted: Extracted content.
            quality_result: Quality gate result.

        Returns:
            DryRunResult with planned actions.
        """
        would_create = not target.exists(self.root)
        full_path = target.to_path(self.root)

        actions = []
        if would_create:
            actions.append(f"Create directory: {full_path}")
            actions.append(
                f"Scaffold via CLI: uv run alphaswarm vulndocs scaffold "
                f"{target.category} {target.subcategory}"
            )
        else:
            actions.append(f"Update existing: {full_path}")

        actions.extend([
            "Populate files:",
            "  - index.yaml (with semantic_triggers, vql_queries)",
            "  - overview.md (from extraction)",
            "  - detection.md (graph-first approach)",
        ])

        for pattern in extracted.patterns:
            actions.append(f"Create pattern: patterns/{pattern.id}.yaml")

        actions.append("Update provenance.yaml")

        # Get category scores for explanation
        cat_scores = self.categorizer.score_categories(extracted)
        categorization = {
            "category": target.category,
            "subcategory": target.subcategory,
            "confidence": cat_scores[0].confidence if cat_scores else "auto",
            "matched_keywords": cat_scores[0].matched_keywords if cat_scores else [],
        }

        return DryRunResult(
            url=url,
            would_create=would_create,
            path=target,
            planned_actions=actions,
            categorization=categorization,
            quality_gate=quality_result.to_dict(),
        )

    async def _insert(
        self, extracted: ExtractedContent, target: VulndocPath
    ) -> list[str]:
        """Insert extracted content into vulndocs.

        Args:
            extracted: Extracted content to insert.
            target: Target vulndoc path.

        Returns:
            List of files modified.
        """
        files_modified = []
        full_path = target.to_path(self.root)

        # Create structure if needed
        if not full_path.exists():
            try:
                subprocess.run(
                    [
                        "uv", "run", "alphaswarm", "vulndocs", "scaffold",
                        target.category, target.subcategory,
                    ],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                # Fallback: create directory manually
                full_path.mkdir(parents=True, exist_ok=True)

        # Update index.yaml
        index_path = full_path / "index.yaml"
        self._update_index(index_path, extracted, target)
        files_modified.append("index.yaml")

        # Update documentation files
        if extracted.documentation:
            for doc_type, content in extracted.documentation.items():
                doc_path = full_path / f"{doc_type}.md"
                if content:
                    doc_path.write_text(content)
                    files_modified.append(f"{doc_type}.md")

        # Create pattern files
        patterns_dir = full_path / "patterns"
        patterns_dir.mkdir(exist_ok=True)
        for pattern in extracted.patterns:
            pattern_path = patterns_dir / f"{pattern.id}.yaml"
            self._write_pattern(pattern_path, pattern, target)
            files_modified.append(f"patterns/{pattern.id}.yaml")

        return files_modified

    def _update_index(
        self,
        index_path: Path,
        extracted: ExtractedContent,
        target: VulndocPath,
    ) -> None:
        """Update index.yaml with extracted content.

        Args:
            index_path: Path to index.yaml.
            extracted: Extracted content.
            target: Target vulndoc path.
        """
        # Load existing or create new
        if index_path.exists():
            index = yaml.safe_load(index_path.read_text()) or {}
        else:
            index = {}

        # Update fields
        index.update({
            "id": f"{target.category}-{target.subcategory}",
            "category": target.category,
            "subcategory": target.subcategory,
            "severity": extracted.severity or "medium",
            "vulndoc": target.path,
            "description": extracted.description or "",
            "semantic_triggers": extracted.semantic_ops or [],
            "graph_patterns": (
                [extracted.graph_signals.get("behavioral_signature")]
                if extracted.graph_signals else []
            ),
            "status": "draft",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
        })

        # Add pattern references
        if extracted.patterns:
            index["patterns"] = [p.id for p in extracted.patterns]

        # Write back
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(yaml.dump(index, default_flow_style=False, sort_keys=False))

    def _write_pattern(
        self, pattern_path: Path, pattern: Any, target: VulndocPath
    ) -> None:
        """Write a pattern file.

        Args:
            pattern_path: Path to write pattern.
            pattern: Extracted pattern data.
            target: Target vulndoc path.
        """
        pattern_data = {
            "id": pattern.id,
            "name": pattern.name or pattern.id,
            "severity": pattern.severity or "medium",
            "vulndoc": target.path,
            "description": pattern.description or "",
            "tier": pattern.tier or "A",
            "match": {
                "tier_a": {
                    "all": pattern.conditions or [],
                },
            },
            "created": datetime.now().strftime("%Y-%m-%d"),
            "status": "draft",
        }

        pattern_path.write_text(
            yaml.dump(pattern_data, default_flow_style=False, sort_keys=False)
        )

    def _update_provenance(
        self,
        target: VulndocPath,
        url: str,
        extracted: ExtractedContent,
    ) -> None:
        """Update provenance.yaml with source tracking.

        Args:
            target: Target vulndoc path.
            url: Source URL.
            extracted: Extracted content.
        """
        prov_path = target.to_path(self.root) / "provenance.yaml"

        # Load existing or create new
        if prov_path.exists():
            try:
                provenance = yaml.safe_load(prov_path.read_text()) or {}
            except Exception:
                provenance = {}
        else:
            provenance = {
                "schema_version": "1.0",
                "sources": [],
                "processed_urls": [],
            }

        # Ensure lists exist
        if "sources" not in provenance:
            provenance["sources"] = []
        if "processed_urls" not in provenance:
            provenance["processed_urls"] = []

        # Add source entry
        source_entry = {
            "url": url,
            "type": self._classify_source_type(url),
            "fetched": datetime.now().strftime("%Y-%m-%d"),
            "quality": extracted.quality.value,
            "extracted": {
                "docs": list(extracted.documentation.keys()) if extracted.documentation else [],
                "patterns": [p.id for p in extracted.patterns],
            },
            "notes": "Auto-ingested via /vrs-ingest-url",
        }
        provenance["sources"].append(source_entry)

        # Add to processed URLs
        content_hash = hashlib.sha256(
            (extracted.description or "").encode()
        ).hexdigest()[:16]

        provenance["processed_urls"].append({
            "url": url,
            "hash": content_hash,
            "processed_date": datetime.now().strftime("%Y-%m-%d"),
        })

        provenance["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        # Write back
        prov_path.parent.mkdir(parents=True, exist_ok=True)
        prov_path.write_text(
            yaml.dump(provenance, default_flow_style=False, sort_keys=False)
        )

    def _classify_source_type(self, url: str) -> str:
        """Classify source type from URL.

        Args:
            url: Source URL.

        Returns:
            Source type string.
        """
        url_lower = url.lower()

        if "rekt.news" in url_lower or "postmortem" in url_lower:
            return "postmortem"
        if any(x in url_lower for x in ["solodit", "code4rena", "audit"]):
            return "audit"
        if "github.com" in url_lower and "security" in url_lower:
            return "advisory"
        if "exploit" in url_lower or "hack" in url_lower:
            return "exploit"
        if any(x in url_lower for x in ["blog", "medium.com"]):
            return "research"

        return "research"
