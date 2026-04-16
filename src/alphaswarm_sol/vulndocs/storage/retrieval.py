"""High-level retrieval interface for VulnDocs knowledge.

Task 18.17: Retrieval API for accessing vulnerability knowledge.

Features:
- Category/subcategory navigation
- Semantic search (keyword-based)
- Pattern-based retrieval
- Token-budgeted context assembly
- Multi-document retrieval
- LLM-optimized output formats
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc
from alphaswarm_sol.vulndocs.storage.index_builder import (
    IndexBuilder,
    IndexEntry,
    KnowledgeIndex,
)
from alphaswarm_sol.vulndocs.storage.knowledge_store import (
    DocumentNotFoundError,
    KnowledgeStore,
    StorageConfig,
)


class RetrievalDepth(Enum):
    """How much detail to retrieve."""

    MINIMAL = "minimal"  # Just summary and detection signals
    STANDARD = "standard"  # Summary, detection, mitigation
    FULL = "full"  # All sections
    COMPACT = "compact"  # Token-optimized compact format


@dataclass
class RetrievalConfig:
    """Configuration for retrieval operations."""

    # Default retrieval depth
    default_depth: RetrievalDepth = RetrievalDepth.STANDARD

    # Maximum tokens per retrieval
    max_tokens: int = 4000

    # Maximum documents per retrieval
    max_documents: int = 5

    # Include metadata in output
    include_metadata: bool = False

    # Include source URLs
    include_sources: bool = True


@dataclass
class RetrievalQuery:
    """Query for knowledge retrieval."""

    # Direct category/subcategory navigation
    category: Optional[str] = None
    subcategory: Optional[str] = None
    doc_id: Optional[str] = None

    # Search parameters
    keywords: List[str] = field(default_factory=list)
    pattern_ids: List[str] = field(default_factory=list)

    # Filters
    severity_filter: Optional[str] = None
    max_results: int = 5

    # Output options
    depth: RetrievalDepth = RetrievalDepth.STANDARD
    max_tokens: int = 4000

    @classmethod
    def by_category(
        cls,
        category: str,
        subcategory: Optional[str] = None,
        depth: RetrievalDepth = RetrievalDepth.STANDARD,
    ) -> "RetrievalQuery":
        """Create query for category navigation."""
        return cls(category=category, subcategory=subcategory, depth=depth)

    @classmethod
    def by_doc_id(
        cls,
        doc_id: str,
        depth: RetrievalDepth = RetrievalDepth.FULL,
    ) -> "RetrievalQuery":
        """Create query for specific document."""
        return cls(doc_id=doc_id, depth=depth)

    @classmethod
    def by_keywords(
        cls,
        keywords: List[str],
        max_results: int = 5,
        depth: RetrievalDepth = RetrievalDepth.STANDARD,
    ) -> "RetrievalQuery":
        """Create query for keyword search."""
        return cls(keywords=keywords, max_results=max_results, depth=depth)

    @classmethod
    def by_pattern(
        cls,
        pattern_ids: List[str],
        depth: RetrievalDepth = RetrievalDepth.STANDARD,
    ) -> "RetrievalQuery":
        """Create query for pattern-linked documents."""
        return cls(pattern_ids=pattern_ids, depth=depth)


@dataclass
class RetrievalResult:
    """Result of a knowledge retrieval operation."""

    # Retrieved documents
    documents: List[VulnKnowledgeDoc] = field(default_factory=list)

    # Index entries (lightweight metadata)
    entries: List[IndexEntry] = field(default_factory=list)

    # Formatted context for LLM
    context: str = ""

    # Token estimate
    token_estimate: int = 0

    # Query metadata
    query_type: str = ""  # "category", "search", "pattern", "direct"
    result_count: int = 0
    truncated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "documents": [d.to_dict() for d in self.documents],
            "entries": [e.to_dict() for e in self.entries],
            "context": self.context,
            "token_estimate": self.token_estimate,
            "query_type": self.query_type,
            "result_count": self.result_count,
            "truncated": self.truncated,
        }

    def get_first(self) -> Optional[VulnKnowledgeDoc]:
        """Get first document if available."""
        return self.documents[0] if self.documents else None

    def get_context(self) -> str:
        """Get formatted context string."""
        return self.context


class KnowledgeRetriever:
    """High-level interface for retrieving vulnerability knowledge.

    Example usage:
        retriever = KnowledgeRetriever()

        # Navigate by category
        result = retriever.get_by_category("reentrancy", "classic")

        # Search by keywords
        result = retriever.search(["external call", "state update"])

        # Get context for LLM
        context = retriever.get_context_for_finding({
            "category": "reentrancy",
            "signals": ["state_write_after_external_call"]
        })
    """

    def __init__(
        self,
        store: Optional[KnowledgeStore] = None,
        config: Optional[RetrievalConfig] = None,
    ):
        """Initialize retriever.

        Args:
            store: Knowledge store to retrieve from
            config: Retrieval configuration
        """
        self.config = config or RetrievalConfig()
        self.store = store or KnowledgeStore()
        self.index_builder = IndexBuilder(self.store)
        self._index: Optional[KnowledgeIndex] = None

    @property
    def index(self) -> KnowledgeIndex:
        """Get the knowledge index, building if needed."""
        if self._index is None:
            self._index = self.index_builder.get_index()
        return self._index

    def execute(self, query: RetrievalQuery) -> RetrievalResult:
        """Execute a retrieval query.

        Args:
            query: The retrieval query

        Returns:
            RetrievalResult with documents and context
        """
        if query.doc_id:
            return self._retrieve_by_doc_id(query)
        elif query.pattern_ids:
            return self._retrieve_by_patterns(query)
        elif query.keywords:
            return self._retrieve_by_keywords(query)
        elif query.category:
            return self._retrieve_by_category(query)
        else:
            return RetrievalResult(query_type="empty")

    def _retrieve_by_doc_id(self, query: RetrievalQuery) -> RetrievalResult:
        """Retrieve a specific document."""
        result = RetrievalResult(query_type="direct")

        try:
            doc = self.store.load(query.doc_id)
            result.documents = [doc]
            result.result_count = 1

            entry = self.index.get_entry(query.doc_id)
            if entry:
                result.entries = [entry]

            result.context = self._format_documents([doc], query.depth)
            result.token_estimate = self._estimate_tokens(result.context)

        except DocumentNotFoundError:
            pass

        return result

    def _retrieve_by_category(self, query: RetrievalQuery) -> RetrievalResult:
        """Retrieve documents by category/subcategory."""
        result = RetrievalResult(query_type="category")

        if query.subcategory:
            doc_ids = self.index.get_by_subcategory(
                query.category, query.subcategory
            )
        else:
            # Get all docs in category
            doc_ids = []
            cat_summary = self.index.get_category(query.category)
            if cat_summary:
                for subcat in cat_summary.subcategories:
                    doc_ids.extend(
                        self.index.get_by_subcategory(query.category, subcat)
                    )

        # Apply severity filter
        if query.severity_filter:
            filtered = []
            for doc_id in doc_ids:
                entry = self.index.get_entry(doc_id)
                if entry and entry.severity == query.severity_filter.lower():
                    filtered.append(doc_id)
            doc_ids = filtered

        # Limit results
        if len(doc_ids) > query.max_results:
            doc_ids = doc_ids[: query.max_results]
            result.truncated = True

        # Load documents
        result.documents = self.store.load_batch(doc_ids)
        result.entries = [
            self.index.get_entry(d_id)
            for d_id in doc_ids
            if self.index.get_entry(d_id)
        ]
        result.result_count = len(result.documents)

        # Format context within token budget
        result.context = self._format_documents(
            result.documents, query.depth, query.max_tokens
        )
        result.token_estimate = self._estimate_tokens(result.context)

        return result

    def _retrieve_by_keywords(self, query: RetrievalQuery) -> RetrievalResult:
        """Retrieve documents by keyword search."""
        result = RetrievalResult(query_type="search")

        # Collect matching doc_ids
        matching_ids: Dict[str, int] = {}  # doc_id -> match count

        for keyword in query.keywords:
            # Check keyword index
            ids_from_index = self.index.get_by_keyword(keyword.lower())
            for doc_id in ids_from_index:
                matching_ids[doc_id] = matching_ids.get(doc_id, 0) + 1

            # Also search in entries
            for entry in self.index.search(
                keyword, max_results=20, severity_filter=query.severity_filter
            ):
                matching_ids[entry.doc_id] = matching_ids.get(entry.doc_id, 0) + 1

        # Sort by match count
        sorted_ids = sorted(
            matching_ids.keys(), key=lambda x: matching_ids[x], reverse=True
        )

        # Limit results
        if len(sorted_ids) > query.max_results:
            sorted_ids = sorted_ids[: query.max_results]
            result.truncated = True

        # Load documents
        result.documents = self.store.load_batch(sorted_ids)
        result.entries = [
            self.index.get_entry(d_id)
            for d_id in sorted_ids
            if self.index.get_entry(d_id)
        ]
        result.result_count = len(result.documents)

        # Format context
        result.context = self._format_documents(
            result.documents, query.depth, query.max_tokens
        )
        result.token_estimate = self._estimate_tokens(result.context)

        return result

    def _retrieve_by_patterns(self, query: RetrievalQuery) -> RetrievalResult:
        """Retrieve documents linked to patterns."""
        result = RetrievalResult(query_type="pattern")

        # Collect matching doc_ids
        doc_ids_set: set = set()
        for pattern_id in query.pattern_ids:
            ids = self.index.get_by_pattern(pattern_id)
            doc_ids_set.update(ids)

        doc_ids = list(doc_ids_set)

        # Limit results
        if len(doc_ids) > query.max_results:
            doc_ids = doc_ids[: query.max_results]
            result.truncated = True

        # Load documents
        result.documents = self.store.load_batch(doc_ids)
        result.entries = [
            self.index.get_entry(d_id)
            for d_id in doc_ids
            if self.index.get_entry(d_id)
        ]
        result.result_count = len(result.documents)

        # Format context
        result.context = self._format_documents(
            result.documents, query.depth, query.max_tokens
        )
        result.token_estimate = self._estimate_tokens(result.context)

        return result

    def _format_documents(
        self,
        docs: List[VulnKnowledgeDoc],
        depth: RetrievalDepth,
        max_tokens: int = 4000,
    ) -> str:
        """Format documents into LLM context.

        Args:
            docs: Documents to format
            depth: How much detail to include
            max_tokens: Maximum tokens

        Returns:
            Formatted markdown string
        """
        if not docs:
            return ""

        parts = []
        remaining_tokens = max_tokens

        for doc in docs:
            if remaining_tokens <= 0:
                break

            if depth == RetrievalDepth.COMPACT:
                text = doc.to_compact_context(max_tokens=remaining_tokens)
            elif depth == RetrievalDepth.MINIMAL:
                text = self._format_minimal(doc)
            elif depth == RetrievalDepth.STANDARD:
                text = self._format_standard(doc)
            else:  # FULL
                text = doc.to_markdown(include_metadata=self.config.include_metadata)

            token_est = self._estimate_tokens(text)
            if token_est <= remaining_tokens:
                parts.append(text)
                remaining_tokens -= token_est
            elif parts:
                # Already have some content, stop here
                break
            else:
                # First doc is too big, use compact version
                text = doc.to_compact_context(max_tokens=remaining_tokens)
                parts.append(text)
                break

        return "\n---\n".join(parts)

    def _format_minimal(self, doc: VulnKnowledgeDoc) -> str:
        """Format document in minimal form."""
        lines = [
            f"# {doc.name} ({doc.category}/{doc.subcategory})",
            f"**Severity:** {doc.severity.value}",
            "",
        ]

        if doc.one_liner:
            lines.append(f"> {doc.one_liner}")
            lines.append("")

        if doc.detection.graph_signals:
            lines.append(
                f"**Signals:** {', '.join(doc.detection.graph_signals[:5])}"
            )

        if doc.mitigation.primary_fix:
            lines.append(f"**Fix:** {doc.mitigation.primary_fix}")

        return "\n".join(lines)

    def _format_standard(self, doc: VulnKnowledgeDoc) -> str:
        """Format document in standard form."""
        lines = [
            f"# {doc.name}",
            f"**Category:** {doc.category}/{doc.subcategory} | **Severity:** {doc.severity.value}",
            "",
        ]

        if doc.one_liner:
            lines.append(f"> {doc.one_liner}")
            lines.append("")

        if doc.tldr:
            lines.append(doc.tldr)
            lines.append("")

        # Detection section
        lines.append(doc.detection.to_markdown())

        # Mitigation section
        lines.append(doc.mitigation.to_markdown())

        # Pattern linkage (brief)
        if doc.pattern_linkage.pattern_ids:
            lines.append(
                f"**Linked Patterns:** {', '.join(doc.pattern_linkage.pattern_ids)}"
            )

        return "\n".join(lines)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Rough estimate: 1 token ~= 4 characters
        """
        return len(text) // 4

    # =========================================================================
    # High-level convenience methods
    # =========================================================================

    def get_by_category(
        self,
        category: str,
        subcategory: Optional[str] = None,
        depth: RetrievalDepth = RetrievalDepth.STANDARD,
        max_results: int = 5,
    ) -> RetrievalResult:
        """Get knowledge by category.

        Args:
            category: Vulnerability category
            subcategory: Optional subcategory
            depth: How much detail
            max_results: Maximum documents

        Returns:
            RetrievalResult
        """
        query = RetrievalQuery.by_category(category, subcategory, depth)
        query.max_results = max_results
        return self.execute(query)

    def get_document(
        self,
        doc_id: str,
        depth: RetrievalDepth = RetrievalDepth.FULL,
    ) -> RetrievalResult:
        """Get a specific document.

        Args:
            doc_id: Document ID
            depth: How much detail

        Returns:
            RetrievalResult
        """
        return self.execute(RetrievalQuery.by_doc_id(doc_id, depth))

    def search(
        self,
        keywords: Union[str, List[str]],
        max_results: int = 5,
        depth: RetrievalDepth = RetrievalDepth.STANDARD,
        severity_filter: Optional[str] = None,
    ) -> RetrievalResult:
        """Search by keywords.

        Args:
            keywords: Search keywords (string or list)
            max_results: Maximum results
            depth: How much detail
            severity_filter: Optional severity filter

        Returns:
            RetrievalResult
        """
        if isinstance(keywords, str):
            keywords = keywords.split()

        query = RetrievalQuery.by_keywords(keywords, max_results, depth)
        query.severity_filter = severity_filter
        return self.execute(query)

    def get_by_pattern(
        self,
        pattern_ids: Union[str, List[str]],
        depth: RetrievalDepth = RetrievalDepth.STANDARD,
    ) -> RetrievalResult:
        """Get documents linked to patterns.

        Args:
            pattern_ids: Pattern ID(s)
            depth: How much detail

        Returns:
            RetrievalResult
        """
        if isinstance(pattern_ids, str):
            pattern_ids = [pattern_ids]

        return self.execute(RetrievalQuery.by_pattern(pattern_ids, depth))

    def get_context_for_finding(
        self,
        finding: Dict[str, Any],
        depth: RetrievalDepth = RetrievalDepth.STANDARD,
        max_tokens: int = 2000,
    ) -> str:
        """Get context relevant to a finding.

        Args:
            finding: Finding dict with category, signals, etc.
            depth: How much detail
            max_tokens: Maximum tokens

        Returns:
            Formatted context string
        """
        query = RetrievalQuery(depth=depth, max_tokens=max_tokens)

        # Try to extract category from finding
        if "category" in finding:
            query.category = finding["category"]
        if "subcategory" in finding:
            query.subcategory = finding["subcategory"]

        # Try pattern IDs
        if "pattern_id" in finding:
            query.pattern_ids = [finding["pattern_id"]]
        elif "pattern_ids" in finding:
            query.pattern_ids = finding["pattern_ids"]

        # Fall back to keyword search
        if not query.category and not query.pattern_ids:
            keywords = []
            if "name" in finding:
                keywords.extend(finding["name"].lower().split())
            if "signals" in finding:
                keywords.extend(finding["signals"])
            query.keywords = keywords[:5]

        result = self.execute(query)
        return result.context

    def get_navigation_context(self, max_tokens: int = 2000) -> str:
        """Get navigation context for LLM.

        Args:
            max_tokens: Maximum tokens

        Returns:
            Navigation context string
        """
        return self.index_builder.get_navigation_context(max_tokens)

    def get_category_index(self, category: str) -> str:
        """Get index for a specific category.

        Args:
            category: Category name

        Returns:
            Category index string
        """
        return self.index_builder.get_category_index(category)

    def list_categories(self) -> List[str]:
        """List all available categories."""
        return list(self.index.categories.keys())

    def list_subcategories(self, category: str) -> List[str]:
        """List subcategories for a category."""
        cat_summary = self.index.get_category(category)
        if cat_summary:
            return cat_summary.subcategories
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "total_documents": self.index.total_documents,
            "total_categories": self.index.total_categories,
            "total_tokens": self.index.total_tokens,
            "categories": list(self.index.categories.keys()),
        }
