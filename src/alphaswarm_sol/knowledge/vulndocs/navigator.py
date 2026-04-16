"""VulnDocs Knowledge Navigator API.

Phase 17.4: Knowledge Navigator for VulnDocs.

This module provides the KnowledgeNavigator class for programmatic navigation
of the VulnDocs knowledge base. It enables:

1. Loading and caching of categories and subcategories
2. Search by semantic operation, behavioral signature, or CWE
3. Context retrieval at various depth levels
4. Automatic cache invalidation based on file modification times

Usage:
    from alphaswarm_sol.knowledge.vulndocs.navigator import KnowledgeNavigator

    # Initialize navigator
    navigator = KnowledgeNavigator()

    # Get the knowledge index
    index = navigator.get_index()

    # Load a specific category
    category = navigator.get_category("reentrancy")

    # Load a subcategory
    subcategory = navigator.get_subcategory("reentrancy", "classic")

    # Search by semantic operation
    categories = navigator.search_by_operation("TRANSFERS_VALUE_OUT")

    # Search by behavioral signature
    categories = navigator.search_by_signature("R:bal->X:out->W:bal")

    # Get formatted context for LLM
    context = navigator.get_context("reentrancy", "classic", KnowledgeDepth.DETECTION)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from alphaswarm_sol.knowledge.vulndocs.schema import (
    Category,
    CacheConfig,
    CodePattern,
    Document,
    DocumentType,
    ExploitReference,
    FixRecommendation,
    GraphSignal,
    KnowledgeDepth,
    KnowledgeIndex,
    NavigationMetadata,
    OperationSequences,
    Subcategory,
    SubcategoryRef,
    KNOWLEDGE_DIR,
    SCHEMA_VERSION,
)

from alphaswarm_sol.knowledge.vulndocs.templates import (
    DetectionTemplate,
    ExploitsTemplate,
    FixesTemplate,
    PatternsTemplate,
    render_detection_md,
    render_exploits_md,
    render_fixes_md,
    render_patterns_md,
)


# =============================================================================
# CACHE ENTRY
# =============================================================================


@dataclass
class CacheEntry:
    """Entry in the navigator cache with modification time tracking."""

    data: Any
    mtime: float
    path: Path


# =============================================================================
# KNOWLEDGE NAVIGATOR
# =============================================================================


class KnowledgeNavigator:
    """Navigator for the VulnDocs knowledge base.

    Provides programmatic access to the knowledge hierarchy with in-memory
    caching and automatic cache invalidation based on file modification times.

    Attributes:
        base_path: Path to the knowledge base root directory.
        _index_cache: Cached KnowledgeIndex.
        _category_cache: Cache of loaded categories keyed by category_id.
        _subcategory_cache: Cache of loaded subcategories keyed by (category_id, subcategory_id).
        _document_cache: Cache of loaded documents keyed by (category_id, subcategory_id, doc_type).
    """

    def __init__(self, base_path: Optional[Path] = None) -> None:
        """Initialize the navigator.

        Args:
            base_path: Path to the knowledge base root directory.
                       Defaults to KNOWLEDGE_DIR from schema.
        """
        self.base_path = Path(base_path) if base_path else KNOWLEDGE_DIR
        self._index_cache: Optional[CacheEntry] = None
        self._category_cache: Dict[str, CacheEntry] = {}
        self._subcategory_cache: Dict[Tuple[str, str], CacheEntry] = {}
        self._document_cache: Dict[Tuple[str, str, str], CacheEntry] = {}

    # =========================================================================
    # INDEX OPERATIONS
    # =========================================================================

    def get_index(self) -> KnowledgeIndex:
        """Load and return the top-level knowledge index.

        Returns:
            KnowledgeIndex object with all category references.

        Raises:
            FileNotFoundError: If index.yaml does not exist.
        """
        index_path = self.base_path / "index.yaml"

        # Check cache validity
        if self._index_cache is not None:
            if self._is_cache_valid(self._index_cache, index_path):
                return self._index_cache.data

        # Load from disk
        if not index_path.exists():
            raise FileNotFoundError(f"Knowledge index not found at {index_path}")

        with open(index_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        index = KnowledgeIndex.from_dict(data)

        # Cache the result
        self._index_cache = CacheEntry(
            data=index,
            mtime=index_path.stat().st_mtime,
            path=index_path,
        )

        return index

    # =========================================================================
    # CATEGORY OPERATIONS
    # =========================================================================

    def get_category(self, category_id: str) -> Category:
        """Load a category by ID.

        Args:
            category_id: The category identifier (e.g., "reentrancy").

        Returns:
            Category object with full metadata.

        Raises:
            FileNotFoundError: If category index.yaml does not exist.
            ValueError: If category_id is not found.
        """
        # Check cache validity
        if category_id in self._category_cache:
            cache_entry = self._category_cache[category_id]
            if self._is_cache_valid(cache_entry, cache_entry.path):
                return cache_entry.data

        # Load from disk
        category = load_category_from_disk(self.base_path, category_id)
        if category is None:
            raise ValueError(f"Category not found: {category_id}")

        # Cache the result
        category_path = self.base_path / "categories" / category_id / "index.yaml"
        self._category_cache[category_id] = CacheEntry(
            data=category,
            mtime=category_path.stat().st_mtime if category_path.exists() else 0,
            path=category_path,
        )

        return category

    def list_categories(self) -> List[str]:
        """List all available category IDs.

        Returns:
            List of category ID strings.
        """
        index = self.get_index()
        return index.get_all_category_ids()

    # =========================================================================
    # SUBCATEGORY OPERATIONS
    # =========================================================================

    def get_subcategory(self, category_id: str, subcategory_id: str) -> Subcategory:
        """Load a subcategory by category and subcategory IDs.

        Args:
            category_id: The parent category identifier.
            subcategory_id: The subcategory identifier.

        Returns:
            Subcategory object with full metadata.

        Raises:
            FileNotFoundError: If subcategory index.yaml does not exist.
            ValueError: If subcategory is not found.
        """
        cache_key = (category_id, subcategory_id)

        # Check cache validity
        if cache_key in self._subcategory_cache:
            cache_entry = self._subcategory_cache[cache_key]
            if self._is_cache_valid(cache_entry, cache_entry.path):
                return cache_entry.data

        # Load from disk
        subcategory = load_subcategory_from_disk(
            self.base_path, category_id, subcategory_id
        )
        if subcategory is None:
            raise ValueError(
                f"Subcategory not found: {category_id}/{subcategory_id}"
            )

        # Cache the result
        sub_path = (
            self.base_path
            / "categories"
            / category_id
            / "subcategories"
            / subcategory_id
            / "index.yaml"
        )
        self._subcategory_cache[cache_key] = CacheEntry(
            data=subcategory,
            mtime=sub_path.stat().st_mtime if sub_path.exists() else 0,
            path=sub_path,
        )

        return subcategory

    def list_subcategories(self, category_id: str) -> List[str]:
        """List all subcategory IDs for a category.

        Args:
            category_id: The category identifier.

        Returns:
            List of subcategory ID strings.
        """
        category = self.get_category(category_id)
        return category.get_subcategory_ids()

    # =========================================================================
    # DOCUMENT OPERATIONS
    # =========================================================================

    def get_document(
        self,
        category_id: str,
        subcategory_id: str,
        doc_type: DocumentType,
    ) -> Document:
        """Load a specific document from a subcategory.

        Args:
            category_id: The parent category identifier.
            subcategory_id: The subcategory identifier.
            doc_type: The type of document to load.

        Returns:
            Document object with full content.

        Raises:
            FileNotFoundError: If document file does not exist.
        """
        cache_key = (category_id, subcategory_id, doc_type.value)

        # Check cache validity
        if cache_key in self._document_cache:
            cache_entry = self._document_cache[cache_key]
            if self._is_cache_valid(cache_entry, cache_entry.path):
                return cache_entry.data

        # Load from disk
        doc_path = (
            self.base_path
            / "categories"
            / category_id
            / "subcategories"
            / subcategory_id
            / f"{doc_type.value}.yaml"
        )

        document = load_document_from_disk(doc_path, doc_type, subcategory_id)

        # Cache the result
        self._document_cache[cache_key] = CacheEntry(
            data=document,
            mtime=doc_path.stat().st_mtime if doc_path.exists() else 0,
            path=doc_path,
        )

        return document

    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================

    def search_by_operation(
        self, operation: str, include_secondary: bool = False
    ) -> List[Category]:
        """Find categories relevant to a semantic operation.

        Args:
            operation: The semantic operation (e.g., "TRANSFERS_VALUE_OUT").
            include_secondary: Whether to include secondary category matches.

        Returns:
            List of Category objects matching the operation.
        """
        index = self.get_index()
        category_ids = index.get_categories_for_operation(operation, include_secondary)

        categories = []
        for cat_id in category_ids:
            try:
                categories.append(self.get_category(cat_id))
            except (FileNotFoundError, ValueError):
                # Skip categories that don't exist on disk yet
                pass

        return categories

    def search_by_signature(self, signature: str) -> List[Category]:
        """Find categories relevant to a behavioral signature.

        Args:
            signature: The behavioral signature (e.g., "R:bal->X:out->W:bal").

        Returns:
            List of Category objects matching the signature.
        """
        index = self.get_index()
        result = index.get_category_for_signature(signature)

        if result is None:
            return []

        category_id, subcategory_id, severity = result
        try:
            category = self.get_category(category_id)
            return [category]
        except (FileNotFoundError, ValueError):
            return []

    def search_by_cwe(self, cwe_id: str) -> List[Category]:
        """Find categories related to a CWE identifier.

        Args:
            cwe_id: The CWE identifier (e.g., "CWE-841" or just "841").

        Returns:
            List of Category objects related to the CWE.
        """
        # Normalize the CWE ID
        if not cwe_id.upper().startswith("CWE-"):
            cwe_id = f"CWE-{cwe_id}"
        else:
            cwe_id = cwe_id.upper()

        categories = []
        for cat_id in self.list_categories():
            try:
                category = self.get_category(cat_id)
                # Check if CWE is in related_cwes
                if cwe_id in category.related_cwes:
                    categories.append(category)
            except (FileNotFoundError, ValueError):
                pass

        return categories

    def search_by_property(self, property_name: str) -> List[Category]:
        """Find categories that use a specific VKG property.

        Args:
            property_name: The property name (e.g., "has_reentrancy_guard").

        Returns:
            List of Category objects that reference this property.
        """
        categories = []
        for cat_id in self.list_categories():
            try:
                category = self.get_category(cat_id)
                if property_name in category.relevant_properties:
                    categories.append(category)
            except (FileNotFoundError, ValueError):
                pass

        return categories

    # =========================================================================
    # CONTEXT FORMATTING
    # =========================================================================

    def get_context(
        self,
        category_id: str,
        subcategory_id: Optional[str] = None,
        depth: KnowledgeDepth = KnowledgeDepth.DETECTION,
    ) -> str:
        """Get formatted context for LLM consumption.

        Args:
            category_id: The category identifier.
            subcategory_id: The subcategory identifier (optional).
            depth: The depth of context to retrieve.

        Returns:
            Formatted markdown string suitable for LLM context.
        """
        category = self.get_category(category_id)

        if subcategory_id is None:
            # Return category-level context
            return format_context_for_llm(category, None, depth)

        subcategory = self.get_subcategory(category_id, subcategory_id)
        return format_context_for_llm(category, subcategory, depth)

    def get_navigation_context(self) -> str:
        """Get navigation context for LLM agents.

        Returns:
            Formatted markdown string with navigation hints.
        """
        index = self.get_index()
        return index.get_navigation_context()

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================

    def invalidate_cache(
        self,
        category_id: Optional[str] = None,
        subcategory_id: Optional[str] = None,
    ) -> None:
        """Invalidate cached data.

        Args:
            category_id: If provided, only invalidate this category.
            subcategory_id: If provided with category_id, only invalidate this subcategory.
        """
        if category_id is None:
            # Invalidate everything
            self._index_cache = None
            self._category_cache.clear()
            self._subcategory_cache.clear()
            self._document_cache.clear()
        elif subcategory_id is None:
            # Invalidate specific category and its subcategories
            self._category_cache.pop(category_id, None)
            # Remove all subcategories for this category
            keys_to_remove = [
                k for k in self._subcategory_cache.keys() if k[0] == category_id
            ]
            for key in keys_to_remove:
                del self._subcategory_cache[key]
            # Remove all documents for this category
            doc_keys_to_remove = [
                k for k in self._document_cache.keys() if k[0] == category_id
            ]
            for key in doc_keys_to_remove:
                del self._document_cache[key]
        else:
            # Invalidate specific subcategory
            cache_key = (category_id, subcategory_id)
            self._subcategory_cache.pop(cache_key, None)
            # Remove documents for this subcategory
            doc_keys_to_remove = [
                k
                for k in self._document_cache.keys()
                if k[0] == category_id and k[1] == subcategory_id
            ]
            for key in doc_keys_to_remove:
                del self._document_cache[key]

    def _is_cache_valid(self, cache_entry: CacheEntry, path: Path) -> bool:
        """Check if a cache entry is still valid based on file mtime.

        Args:
            cache_entry: The cache entry to check.
            path: The path to the source file.

        Returns:
            True if cache is valid, False if it should be refreshed.
        """
        if not path.exists():
            return False
        current_mtime = path.stat().st_mtime
        return cache_entry.mtime >= current_mtime


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_category_from_disk(base_path: Path, category_id: str) -> Optional[Category]:
    """Load a category from disk.

    Args:
        base_path: Path to the knowledge base root.
        category_id: The category identifier.

    Returns:
        Category object or None if not found.
    """
    category_path = base_path / "categories" / category_id / "index.yaml"

    if not category_path.exists():
        # Try loading from main index
        index_path = base_path / "index.yaml"
        if not index_path.exists():
            return None
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = yaml.safe_load(f) or {}
        categories = index_data.get("categories", {})
        if category_id in categories:
            cat_data = categories[category_id]
            if isinstance(cat_data, dict):
                cat_data["id"] = category_id
                return Category.from_dict(cat_data)
        return None

    with open(category_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Ensure id is set
    data["id"] = category_id

    # Parse subcategories from the data
    subcategories_data = data.get("subcategories", [])
    subcategories = []
    for sub in subcategories_data:
        if isinstance(sub, dict):
            subcategories.append(SubcategoryRef.from_dict(sub))
        elif isinstance(sub, str):
            subcategories.append(SubcategoryRef(id=sub, name=sub, description=""))

    # Build category with parsed subcategories
    return Category(
        id=data.get("id", category_id),
        name=data.get("name", ""),
        description=data.get("description", ""),
        severity_range=data.get("severity_range", ["medium", "critical"]),
        subcategories=subcategories,
        relevant_properties=data.get(
            "relevant_properties", data.get("graph_signals", [])
        ),
        semantic_operations=data.get("semantic_operations", data.get("key_operations", [])),
        context_cache_key=data.get("context_cache_key", ""),
        token_estimate=data.get("token_estimate", 1500),
        related_cwes=data.get("related_cwes", []),
        external_refs=data.get("external_refs", {}),
        path=data.get("path", f"categories/{category_id}/"),
    )


def load_subcategory_from_disk(
    base_path: Path, category_id: str, subcategory_id: str
) -> Optional[Subcategory]:
    """Load a subcategory from disk.

    Args:
        base_path: Path to the knowledge base root.
        category_id: The parent category identifier.
        subcategory_id: The subcategory identifier.

    Returns:
        Subcategory object or None if not found.
    """
    sub_path = (
        base_path
        / "categories"
        / category_id
        / "subcategories"
        / subcategory_id
        / "index.yaml"
    )

    if not sub_path.exists():
        return None

    with open(sub_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Ensure required fields are set
    data["id"] = subcategory_id
    data["parent_category"] = category_id

    # Parse graph signals
    graph_signals = []
    for sig_data in data.get("graph_signals", []):
        if isinstance(sig_data, dict):
            graph_signals.append(GraphSignal.from_dict(sig_data))

    # Parse operation sequences
    op_seq_data = data.get("operation_sequences")
    operation_sequences = None
    if op_seq_data and isinstance(op_seq_data, dict):
        operation_sequences = OperationSequences.from_dict(op_seq_data)

    # Parse code patterns
    code_patterns = []
    for pattern_data in data.get("code_patterns", []):
        if isinstance(pattern_data, dict):
            code_patterns.append(CodePattern.from_dict(pattern_data))

    # Parse exploits
    exploits = []
    for exploit_data in data.get("exploits", data.get("related_exploits", [])):
        if isinstance(exploit_data, dict):
            exploits.append(ExploitReference.from_dict(exploit_data))
        elif isinstance(exploit_data, str):
            # Just an ID reference
            exploits.append(ExploitReference(id=exploit_data, name=exploit_data))

    # Parse fixes
    fixes = []
    for fix_data in data.get("fixes", []):
        if isinstance(fix_data, dict):
            fixes.append(FixRecommendation.from_dict(fix_data))

    return Subcategory(
        id=data.get("id", subcategory_id),
        name=data.get("name", ""),
        description=data.get("description", ""),
        parent_category=data.get("parent_category", category_id),
        severity_range=data.get("severity_range", ["medium", "high"]),
        patterns=data.get("patterns", []),
        relevant_properties=data.get("relevant_properties", []),
        graph_signals=graph_signals,
        behavioral_signatures=data.get("behavioral_signatures", []),
        operation_sequences=operation_sequences,
        code_patterns=code_patterns,
        exploits=exploits,
        fixes=fixes,
        false_positive_indicators=data.get("false_positive_indicators", []),
        token_estimate=data.get("token_estimate", 500),
    )


def load_document_from_disk(
    path: Path, doc_type: DocumentType, subcategory_id: str
) -> Document:
    """Load a document from disk.

    Args:
        path: Path to the document YAML file.
        doc_type: The type of document.
        subcategory_id: The parent subcategory identifier.

    Returns:
        Document object.
    """
    if not path.exists():
        # Return empty document if file doesn't exist
        return Document(
            subcategory_id=subcategory_id,
            document_type=doc_type,
            content="",
        )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    data["subcategory_id"] = subcategory_id
    data["document_type"] = doc_type.value

    return Document.from_dict(data)


def format_context_for_llm(
    category: Category,
    subcategory: Optional[Subcategory],
    depth: KnowledgeDepth,
) -> str:
    """Format knowledge context for LLM consumption.

    Args:
        category: The Category object.
        subcategory: The Subcategory object (optional).
        depth: The depth of context to generate.

    Returns:
        Formatted markdown string.
    """
    lines: List[str] = []

    if depth == KnowledgeDepth.INDEX:
        # Minimal index-level context
        lines.append(f"# {category.name}")
        lines.append("")
        lines.append(f"**ID:** {category.id}")
        lines.append(f"**Severity:** {', '.join(category.severity_range)}")
        lines.append("")
        if subcategory:
            lines.append(f"## Subcategory: {subcategory.name}")
            lines.append(f"**ID:** {subcategory.id}")
        else:
            lines.append("## Subcategories")
            for sub in category.subcategories:
                lines.append(f"- `{sub.id}`: {sub.name}")
        return "\n".join(lines)

    if depth == KnowledgeDepth.OVERVIEW:
        # Overview context
        lines.append(f"# {category.name}")
        lines.append("")
        lines.append(category.description)
        lines.append("")
        lines.append(f"**Severity Range:** {', '.join(category.severity_range)}")
        lines.append("")
        if subcategory:
            lines.append(f"## {subcategory.name}")
            lines.append("")
            lines.append(subcategory.description)
            lines.append("")
            lines.append(f"**Patterns:** {', '.join(subcategory.patterns)}")
        else:
            lines.append("## Subcategories")
            for sub in category.subcategories:
                lines.append(f"- **{sub.name}** (`{sub.id}`): {sub.description}")
        return "\n".join(lines)

    if depth == KnowledgeDepth.DETECTION:
        # Detection-focused context
        if subcategory:
            return _format_detection_context(category, subcategory)
        else:
            return _format_category_detection_context(category)

    if depth == KnowledgeDepth.PATTERNS:
        # Pattern-focused context
        if subcategory:
            return _format_patterns_context(category, subcategory)
        else:
            return category.get_overview_context()

    if depth == KnowledgeDepth.EXPLOITS:
        # Exploit-focused context
        if subcategory:
            return _format_exploits_context(category, subcategory)
        else:
            return category.get_overview_context()

    if depth == KnowledgeDepth.FIXES:
        # Fix-focused context
        if subcategory:
            return _format_fixes_context(category, subcategory)
        else:
            return category.get_overview_context()

    if depth == KnowledgeDepth.FULL:
        # Full context with everything
        if subcategory:
            return _format_full_context(category, subcategory)
        else:
            # For category-level, combine overview with all subcategory detection info
            parts = [category.get_overview_context()]
            for sub_ref in category.subcategories[:5]:  # Limit to 5 subcategories
                parts.append(f"\n---\n\n## {sub_ref.name}\n")
                parts.append(f"**ID:** {sub_ref.id}")
                parts.append(f"\n{sub_ref.description}")
            return "\n".join(parts)

    # Default: return overview
    return category.get_overview_context()


def _format_detection_context(category: Category, subcategory: Subcategory) -> str:
    """Format detection context for a subcategory."""
    return render_detection_md(
        subcategory=subcategory.name,
        signals=subcategory.graph_signals,
        checks=[],  # Detection checklist from subcategory
        overview=subcategory.description,
        behavioral_signatures=subcategory.behavioral_signatures,
        operation_sequences=subcategory.operation_sequences,
        false_positive_indicators=subcategory.false_positive_indicators,
        severity=", ".join(subcategory.severity_range),
        confidence_notes="",
        related_patterns=subcategory.patterns,
        category=category.name,
    )


def _format_category_detection_context(category: Category) -> str:
    """Format detection context for a category (no specific subcategory)."""
    lines = [
        f"# Detection: {category.name}",
        "",
        category.description,
        "",
        f"**Severity Range:** {', '.join(category.severity_range)}",
        "",
    ]

    if category.relevant_properties:
        lines.append("## Key Properties")
        for prop in category.relevant_properties:
            lines.append(f"- `{prop}`")
        lines.append("")

    if category.semantic_operations:
        lines.append("## Semantic Operations")
        for op in category.semantic_operations:
            lines.append(f"- `{op}`")
        lines.append("")

    lines.append("## Subcategories")
    for sub in category.subcategories:
        lines.append(f"- **{sub.name}** (`{sub.id}`): {sub.description}")

    return "\n".join(lines)


def _format_patterns_context(category: Category, subcategory: Subcategory) -> str:
    """Format patterns context for a subcategory."""
    return render_patterns_md(
        subcategory=subcategory.name,
        vulnerable_patterns=subcategory.code_patterns,
        safe_patterns=[],  # Would need separate list in schema
        overview=f"{category.name} > {subcategory.name}",
        edge_cases=[],
        pattern_ids=subcategory.patterns,
        common_mistakes=[],
        best_practices=[],
    )


def _format_exploits_context(category: Category, subcategory: Subcategory) -> str:
    """Format exploits context for a subcategory."""
    return render_exploits_md(
        subcategory=subcategory.name,
        exploits=subcategory.exploits,
        overview=f"Real-world exploits for {category.name} > {subcategory.name}",
        attack_vectors=[],
        total_losses="",
        common_targets=[],
    )


def _format_fixes_context(category: Category, subcategory: Subcategory) -> str:
    """Format fixes context for a subcategory."""
    return render_fixes_md(
        subcategory=subcategory.name,
        recommendations=subcategory.fixes,
        overview=f"Remediation for {category.name} > {subcategory.name}",
        code_examples=[],
        testing_strategies=[],
        tools=[],
        audit_checklist=[],
    )


def _format_full_context(category: Category, subcategory: Subcategory) -> str:
    """Format full context for a subcategory."""
    parts = [
        f"# {category.name}: {subcategory.name}",
        "",
        "## Overview",
        "",
        subcategory.description,
        "",
        f"**Category:** {category.name}",
        f"**Severity:** {', '.join(subcategory.severity_range)}",
        f"**Patterns:** {', '.join(subcategory.patterns)}",
        "",
    ]

    # Detection section
    parts.append("---")
    parts.append("")
    parts.append(_format_detection_context(category, subcategory))
    parts.append("")

    # Patterns section (if code patterns exist)
    if subcategory.code_patterns:
        parts.append("---")
        parts.append("")
        parts.append(_format_patterns_context(category, subcategory))
        parts.append("")

    # Exploits section (if exploits exist)
    if subcategory.exploits:
        parts.append("---")
        parts.append("")
        parts.append(_format_exploits_context(category, subcategory))
        parts.append("")

    # Fixes section (if fixes exist)
    if subcategory.fixes:
        parts.append("---")
        parts.append("")
        parts.append(_format_fixes_context(category, subcategory))

    return "\n".join(parts)
