"""File-based storage for VulnKnowledgeDoc.

Task 18.14: Persistent storage for vulnerability knowledge documents.

Features:
- JSON-based persistence for debuggability
- Hierarchical organization: category/subcategory/doc_id.json
- Versioning with content hash change detection
- Batch operations for efficiency
- Thread-safe operations
"""

from __future__ import annotations

import json
import os
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class DocumentNotFoundError(StorageError):
    """Raised when a document is not found."""

    pass


class DocumentExistsError(StorageError):
    """Raised when trying to create a document that already exists."""

    pass


@dataclass
class StorageConfig:
    """Configuration for KnowledgeStore."""

    # Base directory for storage - now unified under vulndocs/
    base_path: str = "vulndocs"

    # Whether to create directories automatically
    auto_create_dirs: bool = True

    # Whether to pretty-print JSON (readable but larger)
    pretty_json: bool = True

    # Version tracking file
    version_file: str = ".version"

    # Backup before overwrite
    backup_on_update: bool = False

    # Maximum backup versions to keep
    max_backups: int = 3


@dataclass
class StorageStats:
    """Statistics about storage contents."""

    total_documents: int = 0
    total_categories: int = 0
    total_subcategories: int = 0
    total_size_bytes: int = 0
    documents_by_category: Dict[str, int] = field(default_factory=dict)
    last_updated: str = ""


class KnowledgeStore:
    """File-based storage for VulnKnowledgeDoc.

    Organizes documents hierarchically:
        {base_path}/
            index.json           # Master index
            categories/
                reentrancy/
                    index.json   # Category index
                    classic/
                        overview.json
                        doc1.json
                        doc2.json
                    cross-function/
                        ...
                access-control/
                    ...
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """Initialize knowledge store.

        Args:
            config: Storage configuration. Uses defaults if not provided.
        """
        self.config = config or StorageConfig()
        self.base_path = Path(self.config.base_path)
        self._lock = threading.RLock()

        if self.config.auto_create_dirs:
            self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create base directory structure."""
        categories_dir = self.base_path / "categories"
        categories_dir.mkdir(parents=True, exist_ok=True)

    def _get_doc_path(self, doc_id: str) -> Path:
        """Get file path for a document ID.

        Args:
            doc_id: Document ID like "reentrancy/classic/state-after-call"

        Returns:
            Path to the document file
        """
        parts = doc_id.split("/")
        if len(parts) < 2:
            raise StorageError(f"Invalid doc_id format: {doc_id}")

        category = parts[0]
        subcategory = parts[1]
        filename = "-".join(parts[2:]) if len(parts) > 2 else "overview"

        return (
            self.base_path
            / "categories"
            / category
            / subcategory
            / f"{filename}.json"
        )

    def _serialize(self, doc: VulnKnowledgeDoc) -> str:
        """Serialize document to JSON string."""
        data = doc.to_dict()
        if self.config.pretty_json:
            return json.dumps(data, indent=2, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)

    def _deserialize(self, json_str: str) -> VulnKnowledgeDoc:
        """Deserialize JSON string to document."""
        data = json.loads(json_str)
        return VulnKnowledgeDoc.from_dict(data)

    def save(self, doc: VulnKnowledgeDoc, overwrite: bool = True) -> str:
        """Save a document to storage.

        Args:
            doc: Document to save
            overwrite: Whether to overwrite existing document

        Returns:
            Path where document was saved

        Raises:
            DocumentExistsError: If document exists and overwrite=False
        """
        with self._lock:
            path = self._get_doc_path(doc.id)

            if path.exists() and not overwrite:
                raise DocumentExistsError(f"Document already exists: {doc.id}")

            # Backup if updating
            if path.exists() and self.config.backup_on_update:
                self._create_backup(path)

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write document
            content = self._serialize(doc)
            path.write_text(content, encoding="utf-8")

            return str(path)

    def load(self, doc_id: str) -> VulnKnowledgeDoc:
        """Load a document from storage.

        Args:
            doc_id: Document ID

        Returns:
            The loaded document

        Raises:
            DocumentNotFoundError: If document doesn't exist
        """
        with self._lock:
            path = self._get_doc_path(doc_id)

            if not path.exists():
                raise DocumentNotFoundError(f"Document not found: {doc_id}")

            content = path.read_text(encoding="utf-8")
            return self._deserialize(content)

    def exists(self, doc_id: str) -> bool:
        """Check if a document exists.

        Args:
            doc_id: Document ID

        Returns:
            True if document exists
        """
        return self._get_doc_path(doc_id).exists()

    def delete(self, doc_id: str) -> bool:
        """Delete a document.

        Args:
            doc_id: Document ID

        Returns:
            True if document was deleted, False if it didn't exist
        """
        with self._lock:
            path = self._get_doc_path(doc_id)

            if not path.exists():
                return False

            path.unlink()
            return True

    def list_documents(
        self,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
    ) -> List[str]:
        """List document IDs.

        Args:
            category: Filter by category
            subcategory: Filter by subcategory (requires category)

        Returns:
            List of document IDs
        """
        doc_ids = []
        categories_dir = self.base_path / "categories"

        if not categories_dir.exists():
            return doc_ids

        # Determine which categories to scan
        if category:
            cat_dirs = [categories_dir / category]
        else:
            cat_dirs = [d for d in categories_dir.iterdir() if d.is_dir()]

        for cat_dir in cat_dirs:
            if not cat_dir.exists():
                continue

            cat_name = cat_dir.name

            # Determine which subcategories to scan
            if subcategory and category:
                subcat_dirs = [cat_dir / subcategory]
            else:
                subcat_dirs = [d for d in cat_dir.iterdir() if d.is_dir()]

            for subcat_dir in subcat_dirs:
                if not subcat_dir.exists():
                    continue

                subcat_name = subcat_dir.name

                # Find all JSON files
                for json_file in subcat_dir.glob("*.json"):
                    if json_file.name == "index.json":
                        continue

                    # Reconstruct doc_id
                    filename = json_file.stem
                    if filename == "overview":
                        doc_id = f"{cat_name}/{subcat_name}"
                    else:
                        doc_id = f"{cat_name}/{subcat_name}/{filename}"

                    doc_ids.append(doc_id)

        return sorted(doc_ids)

    def list_categories(self) -> List[str]:
        """List all categories.

        Returns:
            List of category names
        """
        categories_dir = self.base_path / "categories"

        if not categories_dir.exists():
            return []

        return sorted([d.name for d in categories_dir.iterdir() if d.is_dir()])

    def list_subcategories(self, category: str) -> List[str]:
        """List subcategories for a category.

        Args:
            category: Category name

        Returns:
            List of subcategory names
        """
        cat_dir = self.base_path / "categories" / category

        if not cat_dir.exists():
            return []

        return sorted([d.name for d in cat_dir.iterdir() if d.is_dir()])

    def save_batch(
        self, docs: List[VulnKnowledgeDoc], overwrite: bool = True
    ) -> List[str]:
        """Save multiple documents.

        Args:
            docs: Documents to save
            overwrite: Whether to overwrite existing documents

        Returns:
            List of paths where documents were saved
        """
        paths = []
        for doc in docs:
            path = self.save(doc, overwrite=overwrite)
            paths.append(path)
        return paths

    def load_batch(self, doc_ids: List[str]) -> List[VulnKnowledgeDoc]:
        """Load multiple documents.

        Args:
            doc_ids: Document IDs to load

        Returns:
            List of loaded documents (skips missing)
        """
        docs = []
        for doc_id in doc_ids:
            try:
                doc = self.load(doc_id)
                docs.append(doc)
            except DocumentNotFoundError:
                pass
        return docs

    def load_category(self, category: str) -> List[VulnKnowledgeDoc]:
        """Load all documents in a category.

        Args:
            category: Category name

        Returns:
            List of documents
        """
        doc_ids = self.list_documents(category=category)
        return self.load_batch(doc_ids)

    def load_subcategory(
        self, category: str, subcategory: str
    ) -> List[VulnKnowledgeDoc]:
        """Load all documents in a subcategory.

        Args:
            category: Category name
            subcategory: Subcategory name

        Returns:
            List of documents
        """
        doc_ids = self.list_documents(category=category, subcategory=subcategory)
        return self.load_batch(doc_ids)

    def iterate_documents(
        self,
        category: Optional[str] = None,
    ) -> Iterator[VulnKnowledgeDoc]:
        """Iterate over documents without loading all into memory.

        Args:
            category: Optional category filter

        Yields:
            Documents one at a time
        """
        doc_ids = self.list_documents(category=category)
        for doc_id in doc_ids:
            try:
                yield self.load(doc_id)
            except DocumentNotFoundError:
                pass

    def get_stats(self) -> StorageStats:
        """Get storage statistics.

        Returns:
            StorageStats with counts and sizes
        """
        stats = StorageStats()
        stats.last_updated = datetime.utcnow().isoformat()

        categories_dir = self.base_path / "categories"

        if not categories_dir.exists():
            return stats

        for cat_dir in categories_dir.iterdir():
            if not cat_dir.is_dir():
                continue

            cat_name = cat_dir.name
            stats.total_categories += 1
            stats.documents_by_category[cat_name] = 0

            for subcat_dir in cat_dir.iterdir():
                if not subcat_dir.is_dir():
                    continue

                stats.total_subcategories += 1

                for json_file in subcat_dir.glob("*.json"):
                    if json_file.name != "index.json":
                        stats.total_documents += 1
                        stats.documents_by_category[cat_name] += 1
                        stats.total_size_bytes += json_file.stat().st_size

        return stats

    def _create_backup(self, path: Path) -> None:
        """Create backup of a file before updating."""
        backup_dir = path.parent / ".backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{path.stem}_{timestamp}.json"

        shutil.copy2(path, backup_path)

        # Clean old backups
        backups = sorted(backup_dir.glob(f"{path.stem}_*.json"))
        while len(backups) > self.config.max_backups:
            oldest = backups.pop(0)
            oldest.unlink()

    def clear(self) -> int:
        """Clear all documents from storage.

        Returns:
            Number of documents deleted
        """
        with self._lock:
            count = 0
            categories_dir = self.base_path / "categories"

            if categories_dir.exists():
                for json_file in categories_dir.rglob("*.json"):
                    if json_file.name != "index.json":
                        json_file.unlink()
                        count += 1

            return count

    def search_by_keyword(
        self,
        keywords: List[str],
        category: Optional[str] = None,
        max_results: int = 10,
    ) -> List[VulnKnowledgeDoc]:
        """Search documents by keywords in metadata.

        Args:
            keywords: Keywords to search for
            category: Optional category filter
            max_results: Maximum results to return

        Returns:
            List of matching documents
        """
        results = []
        keywords_lower = [k.lower() for k in keywords]

        for doc in self.iterate_documents(category=category):
            # Check keywords in metadata
            doc_keywords = [k.lower() for k in doc.metadata.keywords]
            if any(kw in doc_keywords for kw in keywords_lower):
                results.append(doc)
                if len(results) >= max_results:
                    break
                continue

            # Check in name and one_liner
            text = f"{doc.name} {doc.one_liner}".lower()
            if any(kw in text for kw in keywords_lower):
                results.append(doc)
                if len(results) >= max_results:
                    break

        return results

    def search_by_severity(
        self,
        severity: str,
        category: Optional[str] = None,
    ) -> List[VulnKnowledgeDoc]:
        """Search documents by severity level.

        Args:
            severity: Severity level (critical, high, medium, low, info)
            category: Optional category filter

        Returns:
            List of matching documents
        """
        results = []
        severity_lower = severity.lower()

        for doc in self.iterate_documents(category=category):
            if doc.severity.value == severity_lower:
                results.append(doc)

        return results

    def get_document_version(self, doc_id: str) -> Optional[str]:
        """Get the content hash (version) of a document.

        Args:
            doc_id: Document ID

        Returns:
            Content hash or None if not found
        """
        try:
            doc = self.load(doc_id)
            return doc.metadata.content_hash
        except DocumentNotFoundError:
            return None

    def has_changed(self, doc: VulnKnowledgeDoc) -> bool:
        """Check if a document has changed compared to stored version.

        Args:
            doc: Document to check

        Returns:
            True if document has changed or doesn't exist
        """
        stored_hash = self.get_document_version(doc.id)
        if stored_hash is None:
            return True
        return stored_hash != doc.metadata.content_hash

    def save_if_changed(self, doc: VulnKnowledgeDoc) -> bool:
        """Save document only if it has changed.

        Args:
            doc: Document to save

        Returns:
            True if document was saved, False if unchanged
        """
        if self.has_changed(doc):
            self.save(doc, overwrite=True)
            return True
        return False

    def export_to_dict(self) -> Dict[str, Any]:
        """Export entire store to a dictionary.

        Returns:
            Dictionary with all documents
        """
        export = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "stats": {
                "total_documents": 0,
                "categories": [],
            },
            "documents": {},
        }

        for doc in self.iterate_documents():
            export["documents"][doc.id] = doc.to_dict()
            export["stats"]["total_documents"] += 1

        export["stats"]["categories"] = self.list_categories()
        return export

    def import_from_dict(
        self, data: Dict[str, Any], overwrite: bool = True
    ) -> int:
        """Import documents from a dictionary.

        Args:
            data: Dictionary from export_to_dict
            overwrite: Whether to overwrite existing documents

        Returns:
            Number of documents imported
        """
        count = 0
        documents = data.get("documents", {})

        for doc_id, doc_data in documents.items():
            doc = VulnKnowledgeDoc.from_dict(doc_data)
            try:
                self.save(doc, overwrite=overwrite)
                count += 1
            except DocumentExistsError:
                pass

        return count
