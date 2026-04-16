"""Navigation index builder for VulnDocs knowledge.

Task 18.15: Index generation for efficient navigation and retrieval.

Features:
- Master index with category summaries
- Per-category indexes with subcategory details
- Keyword index for search
- Pattern linkage index
- Severity index
- Change detection support
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.vulndocs.knowledge_doc import (
    PatternLinkageType,
    Severity,
    VulnKnowledgeDoc,
)
from alphaswarm_sol.vulndocs.storage.knowledge_store import KnowledgeStore


@dataclass
class IndexEntry:
    """Entry in the navigation index."""

    doc_id: str
    name: str
    category: str
    subcategory: str
    severity: str
    one_liner: str
    keywords: List[str] = field(default_factory=list)
    pattern_ids: List[str] = field(default_factory=list)
    linkage_type: str = "theoretical"
    token_estimate: int = 0
    content_hash: str = ""
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "doc_id": self.doc_id,
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "severity": self.severity,
            "one_liner": self.one_liner,
            "keywords": self.keywords,
            "pattern_ids": self.pattern_ids,
            "linkage_type": self.linkage_type,
            "token_estimate": self.token_estimate,
            "content_hash": self.content_hash,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexEntry":
        """Deserialize from dictionary."""
        return cls(
            doc_id=data.get("doc_id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            subcategory=data.get("subcategory", ""),
            severity=data.get("severity", "medium"),
            one_liner=data.get("one_liner", ""),
            keywords=data.get("keywords", []),
            pattern_ids=data.get("pattern_ids", []),
            linkage_type=data.get("linkage_type", "theoretical"),
            token_estimate=data.get("token_estimate", 0),
            content_hash=data.get("content_hash", ""),
            last_updated=data.get("last_updated", ""),
        )

    @classmethod
    def from_document(cls, doc: VulnKnowledgeDoc) -> "IndexEntry":
        """Create index entry from a document."""
        return cls(
            doc_id=doc.id,
            name=doc.name,
            category=doc.category,
            subcategory=doc.subcategory,
            severity=doc.severity.value,
            one_liner=doc.one_liner,
            keywords=doc.metadata.keywords,
            pattern_ids=doc.pattern_linkage.pattern_ids,
            linkage_type=doc.pattern_linkage.linkage_type.value,
            token_estimate=doc.estimate_tokens(),
            content_hash=doc.metadata.content_hash,
            last_updated=doc.metadata.last_updated,
        )


@dataclass
class CategorySummary:
    """Summary of a vulnerability category."""

    name: str
    display_name: str
    description: str
    subcategory_count: int = 0
    document_count: int = 0
    total_tokens: int = 0
    subcategories: List[str] = field(default_factory=list)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    pattern_coverage: float = 0.0  # % with pattern linkage

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "subcategory_count": self.subcategory_count,
            "document_count": self.document_count,
            "total_tokens": self.total_tokens,
            "subcategories": self.subcategories,
            "severity_distribution": self.severity_distribution,
            "pattern_coverage": self.pattern_coverage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CategorySummary":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            subcategory_count=data.get("subcategory_count", 0),
            document_count=data.get("document_count", 0),
            total_tokens=data.get("total_tokens", 0),
            subcategories=data.get("subcategories", []),
            severity_distribution=data.get("severity_distribution", {}),
            pattern_coverage=data.get("pattern_coverage", 0.0),
        )


# Category display names and descriptions
CATEGORY_METADATA = {
    "reentrancy": {
        "display_name": "Reentrancy",
        "description": "Vulnerabilities where external calls allow re-entry into contracts before state updates complete.",
    },
    "access-control": {
        "display_name": "Access Control",
        "description": "Vulnerabilities in authorization and permission systems.",
    },
    "oracle": {
        "display_name": "Oracle",
        "description": "Vulnerabilities in price feeds and external data sources.",
    },
    "flash-loan": {
        "display_name": "Flash Loan",
        "description": "Attack vectors utilizing flash loans for manipulation.",
    },
    "mev": {
        "display_name": "MEV",
        "description": "Maximal Extractable Value vulnerabilities including sandwich attacks.",
    },
    "dos": {
        "display_name": "Denial of Service",
        "description": "Vulnerabilities that can block or halt contract operations.",
    },
    "token": {
        "display_name": "Token",
        "description": "Vulnerabilities related to token implementations and interactions.",
    },
    "upgrade": {
        "display_name": "Upgrade",
        "description": "Vulnerabilities in proxy patterns and contract upgradeability.",
    },
    "crypto": {
        "display_name": "Cryptographic",
        "description": "Vulnerabilities in signatures, hashing, and randomness.",
    },
    "governance": {
        "display_name": "Governance",
        "description": "Vulnerabilities in voting and governance mechanisms.",
    },
    "logic": {
        "display_name": "Logic",
        "description": "Business logic and state machine vulnerabilities.",
    },
    "arithmetic": {
        "display_name": "Arithmetic",
        "description": "Integer overflow, underflow, and precision vulnerabilities.",
    },
    "gas": {
        "display_name": "Gas Optimization",
        "description": "Gas-related vulnerabilities and inefficiencies.",
    },
    "external-interaction": {
        "display_name": "External Interaction",
        "description": "Vulnerabilities in external contract calls and integrations.",
    },
    "data-validation": {
        "display_name": "Data Validation",
        "description": "Input validation and data integrity vulnerabilities.",
    },
}


@dataclass
class KnowledgeIndex:
    """Master index for the knowledge base."""

    version: str = "1.0"
    generated_at: str = ""
    total_documents: int = 0
    total_categories: int = 0
    total_tokens: int = 0

    # Main data
    entries: Dict[str, IndexEntry] = field(default_factory=dict)  # doc_id -> entry
    categories: Dict[str, CategorySummary] = field(
        default_factory=dict
    )  # category -> summary

    # Secondary indexes for fast lookup
    by_severity: Dict[str, List[str]] = field(
        default_factory=dict
    )  # severity -> doc_ids
    by_keyword: Dict[str, List[str]] = field(
        default_factory=dict
    )  # keyword -> doc_ids
    by_pattern: Dict[str, List[str]] = field(
        default_factory=dict
    )  # pattern_id -> doc_ids
    by_subcategory: Dict[str, List[str]] = field(
        default_factory=dict
    )  # cat/subcat -> doc_ids

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "total_documents": self.total_documents,
            "total_categories": self.total_categories,
            "total_tokens": self.total_tokens,
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "categories": {k: v.to_dict() for k, v in self.categories.items()},
            "by_severity": self.by_severity,
            "by_keyword": self.by_keyword,
            "by_pattern": self.by_pattern,
            "by_subcategory": self.by_subcategory,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeIndex":
        """Deserialize from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            generated_at=data.get("generated_at", ""),
            total_documents=data.get("total_documents", 0),
            total_categories=data.get("total_categories", 0),
            total_tokens=data.get("total_tokens", 0),
            entries={
                k: IndexEntry.from_dict(v) for k, v in data.get("entries", {}).items()
            },
            categories={
                k: CategorySummary.from_dict(v)
                for k, v in data.get("categories", {}).items()
            },
            by_severity=data.get("by_severity", {}),
            by_keyword=data.get("by_keyword", {}),
            by_pattern=data.get("by_pattern", {}),
            by_subcategory=data.get("by_subcategory", {}),
        )

    def get_entry(self, doc_id: str) -> Optional[IndexEntry]:
        """Get index entry by document ID."""
        return self.entries.get(doc_id)

    def get_category(self, category: str) -> Optional[CategorySummary]:
        """Get category summary."""
        return self.categories.get(category)

    def get_by_severity(self, severity: str) -> List[str]:
        """Get document IDs by severity."""
        return self.by_severity.get(severity.lower(), [])

    def get_by_keyword(self, keyword: str) -> List[str]:
        """Get document IDs by keyword."""
        return self.by_keyword.get(keyword.lower(), [])

    def get_by_pattern(self, pattern_id: str) -> List[str]:
        """Get document IDs linked to a pattern."""
        return self.by_pattern.get(pattern_id, [])

    def get_by_subcategory(self, category: str, subcategory: str) -> List[str]:
        """Get document IDs in a subcategory."""
        key = f"{category}/{subcategory}"
        return self.by_subcategory.get(key, [])

    def search(
        self,
        query: str,
        max_results: int = 10,
        severity_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> List[IndexEntry]:
        """Search index by query string.

        Args:
            query: Search query (searches name, one_liner, keywords)
            max_results: Maximum results
            severity_filter: Optional severity filter
            category_filter: Optional category filter

        Returns:
            Matching index entries
        """
        results = []
        query_lower = query.lower()

        for entry in self.entries.values():
            # Apply filters
            if severity_filter and entry.severity != severity_filter.lower():
                continue
            if category_filter and entry.category != category_filter:
                continue

            # Search in multiple fields
            searchable = f"{entry.name} {entry.one_liner} {' '.join(entry.keywords)}"
            if query_lower in searchable.lower():
                results.append(entry)

            if len(results) >= max_results:
                break

        return results


class IndexBuilder:
    """Builds and maintains the knowledge index."""

    def __init__(self, store: KnowledgeStore):
        """Initialize index builder.

        Args:
            store: Knowledge store to index
        """
        self.store = store
        self._index: Optional[KnowledgeIndex] = None

    def build(self) -> KnowledgeIndex:
        """Build complete index from store.

        Returns:
            New KnowledgeIndex
        """
        index = KnowledgeIndex()

        # Track data for category summaries
        category_docs: Dict[str, List[VulnKnowledgeDoc]] = {}

        # Process all documents
        for doc in self.store.iterate_documents():
            # Create entry
            entry = IndexEntry.from_document(doc)
            index.entries[doc.id] = entry
            index.total_documents += 1
            index.total_tokens += entry.token_estimate

            # Track by category
            if doc.category not in category_docs:
                category_docs[doc.category] = []
            category_docs[doc.category].append(doc)

            # Build secondary indexes
            self._add_to_severity_index(index, entry)
            self._add_to_keyword_index(index, entry)
            self._add_to_pattern_index(index, entry)
            self._add_to_subcategory_index(index, entry)

        # Build category summaries
        for category, docs in category_docs.items():
            summary = self._build_category_summary(category, docs)
            index.categories[category] = summary

        index.total_categories = len(index.categories)
        self._index = index

        return index

    def _add_to_severity_index(
        self, index: KnowledgeIndex, entry: IndexEntry
    ) -> None:
        """Add entry to severity index."""
        severity = entry.severity.lower()
        if severity not in index.by_severity:
            index.by_severity[severity] = []
        index.by_severity[severity].append(entry.doc_id)

    def _add_to_keyword_index(
        self, index: KnowledgeIndex, entry: IndexEntry
    ) -> None:
        """Add entry to keyword index."""
        for keyword in entry.keywords:
            kw_lower = keyword.lower()
            if kw_lower not in index.by_keyword:
                index.by_keyword[kw_lower] = []
            index.by_keyword[kw_lower].append(entry.doc_id)

    def _add_to_pattern_index(
        self, index: KnowledgeIndex, entry: IndexEntry
    ) -> None:
        """Add entry to pattern index."""
        for pattern_id in entry.pattern_ids:
            if pattern_id not in index.by_pattern:
                index.by_pattern[pattern_id] = []
            index.by_pattern[pattern_id].append(entry.doc_id)

    def _add_to_subcategory_index(
        self, index: KnowledgeIndex, entry: IndexEntry
    ) -> None:
        """Add entry to subcategory index."""
        key = f"{entry.category}/{entry.subcategory}"
        if key not in index.by_subcategory:
            index.by_subcategory[key] = []
        index.by_subcategory[key].append(entry.doc_id)

    def _build_category_summary(
        self, category: str, docs: List[VulnKnowledgeDoc]
    ) -> CategorySummary:
        """Build summary for a category."""
        meta = CATEGORY_METADATA.get(
            category,
            {
                "display_name": category.title().replace("-", " "),
                "description": f"Vulnerabilities in the {category} category.",
            },
        )

        # Collect subcategories
        subcategories: Set[str] = set()
        severity_dist: Dict[str, int] = {}
        total_tokens = 0
        with_patterns = 0

        for doc in docs:
            subcategories.add(doc.subcategory)
            total_tokens += doc.estimate_tokens()

            # Severity distribution
            sev = doc.severity.value
            severity_dist[sev] = severity_dist.get(sev, 0) + 1

            # Pattern coverage
            if doc.pattern_linkage.pattern_ids:
                with_patterns += 1

        pattern_coverage = with_patterns / len(docs) if docs else 0.0

        return CategorySummary(
            name=category,
            display_name=meta["display_name"],
            description=meta["description"],
            subcategory_count=len(subcategories),
            document_count=len(docs),
            total_tokens=total_tokens,
            subcategories=sorted(subcategories),
            severity_distribution=severity_dist,
            pattern_coverage=pattern_coverage,
        )

    def get_index(self) -> KnowledgeIndex:
        """Get current index, building if necessary.

        Returns:
            The knowledge index
        """
        if self._index is None:
            return self.build()
        return self._index

    def update_entry(self, doc: VulnKnowledgeDoc) -> None:
        """Update index for a single document.

        Args:
            doc: Document to update
        """
        index = self.get_index()

        # Remove old entry if exists
        old_entry = index.entries.get(doc.id)
        if old_entry:
            self._remove_entry(index, old_entry)

        # Add new entry
        entry = IndexEntry.from_document(doc)
        index.entries[doc.id] = entry
        self._add_to_severity_index(index, entry)
        self._add_to_keyword_index(index, entry)
        self._add_to_pattern_index(index, entry)
        self._add_to_subcategory_index(index, entry)

        # Update stats
        index.total_documents = len(index.entries)
        index.total_tokens = sum(e.token_estimate for e in index.entries.values())

    def _remove_entry(self, index: KnowledgeIndex, entry: IndexEntry) -> None:
        """Remove entry from all indexes."""
        # Remove from severity index
        if entry.severity in index.by_severity:
            if entry.doc_id in index.by_severity[entry.severity]:
                index.by_severity[entry.severity].remove(entry.doc_id)

        # Remove from keyword index
        for keyword in entry.keywords:
            kw_lower = keyword.lower()
            if kw_lower in index.by_keyword:
                if entry.doc_id in index.by_keyword[kw_lower]:
                    index.by_keyword[kw_lower].remove(entry.doc_id)

        # Remove from pattern index
        for pattern_id in entry.pattern_ids:
            if pattern_id in index.by_pattern:
                if entry.doc_id in index.by_pattern[pattern_id]:
                    index.by_pattern[pattern_id].remove(entry.doc_id)

        # Remove from subcategory index
        key = f"{entry.category}/{entry.subcategory}"
        if key in index.by_subcategory:
            if entry.doc_id in index.by_subcategory[key]:
                index.by_subcategory[key].remove(entry.doc_id)

    def remove_entry(self, doc_id: str) -> bool:
        """Remove a document from the index.

        Args:
            doc_id: Document ID to remove

        Returns:
            True if removed, False if not found
        """
        index = self.get_index()

        entry = index.entries.get(doc_id)
        if not entry:
            return False

        self._remove_entry(index, entry)
        del index.entries[doc_id]

        # Update stats
        index.total_documents = len(index.entries)
        index.total_tokens = sum(e.token_estimate for e in index.entries.values())

        return True

    def save_index(self, path: Optional[Path] = None) -> str:
        """Save index to file.

        Args:
            path: Path to save to. Uses default if not provided.

        Returns:
            Path where index was saved
        """
        if path is None:
            path = Path(self.store.config.base_path) / "index.json"

        path.parent.mkdir(parents=True, exist_ok=True)

        index = self.get_index()
        data = index.to_dict()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(path)

    def load_index(self, path: Optional[Path] = None) -> KnowledgeIndex:
        """Load index from file.

        Args:
            path: Path to load from. Uses default if not provided.

        Returns:
            Loaded index
        """
        if path is None:
            path = Path(self.store.config.base_path) / "index.json"

        if not path.exists():
            return self.build()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._index = KnowledgeIndex.from_dict(data)
        return self._index

    def get_navigation_context(self, max_tokens: int = 2000) -> str:
        """Generate navigation context for LLM.

        Args:
            max_tokens: Maximum tokens for context

        Returns:
            Markdown context for LLM navigation
        """
        index = self.get_index()

        lines = [
            "# VulnDocs Knowledge Base Navigation",
            "",
            f"Total Documents: {index.total_documents}",
            f"Categories: {index.total_categories}",
            "",
            "## Categories",
            "",
        ]

        # Sort categories by document count
        sorted_cats = sorted(
            index.categories.values(),
            key=lambda c: c.document_count,
            reverse=True,
        )

        for cat in sorted_cats:
            lines.append(f"### {cat.display_name} ({cat.name})")
            lines.append(f"{cat.description}")
            lines.append(f"- Documents: {cat.document_count}")
            lines.append(f"- Subcategories: {', '.join(cat.subcategories[:5])}")
            if len(cat.subcategories) > 5:
                lines.append(f"  ... and {len(cat.subcategories) - 5} more")
            lines.append("")

            # Stop if too long
            if len("\n".join(lines)) > max_tokens * 4:  # Rough char estimate
                lines.append("*[More categories available]*")
                break

        lines.extend(
            [
                "## How to Use",
                "",
                "1. Use `get_vulnerability_knowledge(category, subcategory)` to retrieve docs",
                "2. Use `search_vulnerability_knowledge(query)` to search",
                "3. Severity levels: critical, high, medium, low, info",
                "",
            ]
        )

        return "\n".join(lines)

    def get_category_index(self, category: str) -> str:
        """Generate category-specific index for LLM.

        Args:
            category: Category name

        Returns:
            Markdown index for the category
        """
        index = self.get_index()
        cat_summary = index.get_category(category)

        if not cat_summary:
            return f"Category '{category}' not found."

        lines = [
            f"# {cat_summary.display_name}",
            "",
            cat_summary.description,
            "",
            "## Subcategories",
            "",
        ]

        for subcat in cat_summary.subcategories:
            doc_ids = index.get_by_subcategory(category, subcat)
            lines.append(f"### {subcat}")

            for doc_id in doc_ids[:3]:  # Show first 3 docs
                entry = index.get_entry(doc_id)
                if entry:
                    lines.append(
                        f"- **{entry.name}** ({entry.severity}): {entry.one_liner}"
                    )

            if len(doc_ids) > 3:
                lines.append(f"  *... and {len(doc_ids) - 3} more*")
            lines.append("")

        # Add severity distribution
        lines.extend(
            [
                "## Severity Distribution",
                "",
            ]
        )
        for sev, count in cat_summary.severity_distribution.items():
            lines.append(f"- {sev}: {count}")

        return "\n".join(lines)
