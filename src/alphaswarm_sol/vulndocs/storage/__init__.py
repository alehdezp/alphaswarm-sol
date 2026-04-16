"""Storage and retrieval system for VulnDocs knowledge.

Task 18.14-18.15: File-based storage and navigation index for VulnKnowledgeDoc.

Key Components:
- KnowledgeStore: File-based storage with JSON persistence
- IndexBuilder: Navigation index generation for efficient retrieval
- KnowledgeRetriever: High-level retrieval interface

Design Principles:
- File-based storage for simplicity and debuggability
- Hierarchical organization by category/subcategory
- Versioned documents with change detection
- Efficient index for navigation and search
"""

from alphaswarm_sol.vulndocs.storage.knowledge_store import (
    KnowledgeStore,
    StorageConfig,
    StorageError,
    StorageStats,
)
from alphaswarm_sol.vulndocs.storage.index_builder import (
    IndexBuilder,
    KnowledgeIndex,
    IndexEntry,
    CategorySummary,
)
from alphaswarm_sol.vulndocs.storage.retrieval import (
    KnowledgeRetriever,
    RetrievalConfig,
    RetrievalResult,
    RetrievalQuery,
)

__all__ = [
    # Knowledge Store
    "KnowledgeStore",
    "StorageConfig",
    "StorageError",
    "StorageStats",
    # Index Builder
    "IndexBuilder",
    "KnowledgeIndex",
    "IndexEntry",
    "CategorySummary",
    # Retrieval
    "KnowledgeRetriever",
    "RetrievalConfig",
    "RetrievalResult",
    "RetrievalQuery",
]
