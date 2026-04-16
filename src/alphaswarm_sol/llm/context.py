"""Context data structure for LLM consumption.

Task 9.0: Context data structure for data minimization security.

This module provides the data structures for representing code context
that will be sent to LLMs, enabling filtering and optimization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class ContextItem:
    """A single item in the context (function, variable, etc).

    Attributes:
        id: Unique identifier for this item
        type: Item type ("function", "state_variable", "modifier", "contract", etc)
        name: Human-readable name
        content: Source code or representation
        metadata: Additional properties from the knowledge graph
    """

    id: str
    type: str
    name: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def size_bytes(self) -> int:
        """Get the size of content in bytes."""
        return len(self.content.encode("utf-8"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextItem":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            name=data["name"],
            content=data["content"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExternalCall:
    """External call reference in a finding."""

    target_id: str
    call_type: str = "external"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    """Finding reference for context filtering.

    This is a simplified finding structure used by the context policy
    to determine what code is relevant for analysis.

    Attributes:
        id: Finding ID
        function_id: ID of the function containing the finding
        state_reads: IDs of state variables read
        state_writes: IDs of state variables written
        external_calls: External call references
    """

    id: str
    function_id: str
    state_reads: List[str] = field(default_factory=list)
    state_writes: List[str] = field(default_factory=list)
    external_calls: List[ExternalCall] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "function_id": self.function_id,
            "state_reads": self.state_reads,
            "state_writes": self.state_writes,
            "external_calls": [
                {"target_id": c.target_id, "call_type": c.call_type}
                for c in self.external_calls
            ],
        }


@dataclass
class Context:
    """Collection of context items for LLM analysis.

    Provides methods to filter, serialize, and measure context.

    Usage:
        ctx = Context()
        ctx.add(ContextItem(id="f1", type="function", name="withdraw", content="..."))
        filtered = ctx.filter_to_ids({"f1"})
    """

    items: Dict[str, ContextItem] = field(default_factory=dict)

    def add(self, item: ContextItem) -> None:
        """Add item to context."""
        self.items[item.id] = item

    def remove(self, item_id: str) -> Optional[ContextItem]:
        """Remove and return item from context."""
        return self.items.pop(item_id, None)

    def get(self, item_id: str) -> Optional[ContextItem]:
        """Get item by ID."""
        return self.items.get(item_id)

    def get_function(self, func_id: str) -> Optional[ContextItem]:
        """Get function by ID (alias for get)."""
        item = self.items.get(func_id)
        if item and item.type == "function":
            return item
        return None

    def get_all_ids(self) -> List[str]:
        """Get all item IDs."""
        return list(self.items.keys())

    def get_items_by_type(self, item_type: str) -> List[ContextItem]:
        """Get all items of a specific type."""
        return [item for item in self.items.values() if item.type == item_type]

    def filter_to_ids(self, ids: Set[str]) -> "Context":
        """Create new context with only specified IDs.

        Args:
            ids: Set of item IDs to include

        Returns:
            New Context containing only the specified items
        """
        new_context = Context()
        for item_id in ids:
            if item_id in self.items:
                new_context.add(self.items[item_id])
        return new_context

    def size_bytes(self) -> int:
        """Total size of all content in bytes."""
        return sum(item.size_bytes() for item in self.items.values())

    def item_count(self) -> int:
        """Number of items in context."""
        return len(self.items)

    def to_string(self) -> str:
        """Serialize to string for LLM consumption.

        Returns:
            Formatted string with all items separated by comments
        """
        if not self.items:
            return ""

        parts = []
        for item in sorted(self.items.values(), key=lambda x: (x.type, x.name)):
            parts.append(f"// {item.type}: {item.name}\n{item.content}")
        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "items": {k: v.to_dict() for k, v in self.items.items()},
            "size_bytes": self.size_bytes(),
            "item_count": self.item_count(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        """Create from dictionary."""
        ctx = cls()
        for item_data in data.get("items", {}).values():
            ctx.add(ContextItem.from_dict(item_data))
        return ctx

    def merge(self, other: "Context") -> "Context":
        """Merge with another context.

        Args:
            other: Context to merge with

        Returns:
            New Context containing items from both
        """
        merged = Context()
        for item in self.items.values():
            merged.add(item)
        for item in other.items.values():
            merged.add(item)
        return merged

    def copy(self) -> "Context":
        """Create a shallow copy."""
        new_ctx = Context()
        for item in self.items.values():
            new_ctx.add(item)
        return new_ctx

    def __len__(self) -> int:
        """Return number of items."""
        return len(self.items)

    def __contains__(self, item_id: str) -> bool:
        """Check if item ID is in context."""
        return item_id in self.items

    def __iter__(self):
        """Iterate over items."""
        return iter(self.items.values())
