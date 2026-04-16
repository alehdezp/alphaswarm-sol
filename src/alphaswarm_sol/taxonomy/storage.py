"""Phase 13: Tag Storage.

This module provides functionality for storing and querying risk tags
on knowledge graph nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.kg.schema import KnowledgeGraph, Node
from alphaswarm_sol.taxonomy.tags import RiskCategory, RiskTag, get_tag_category
from alphaswarm_sol.taxonomy.assignment import TagAssignment


@dataclass
class NodeTags:
    """Container for tags assigned to a node.

    Attributes:
        node_id: ID of the node
        assignments: List of tag assignments
    """
    node_id: str
    assignments: List[TagAssignment] = field(default_factory=list)

    def add_assignment(self, assignment: TagAssignment) -> None:
        """Add a tag assignment."""
        # Check for duplicates
        existing_tags = {a.tag for a in self.assignments}
        if assignment.tag not in existing_tags:
            self.assignments.append(assignment)

    def get_tags(self) -> List[RiskTag]:
        """Get all assigned tags."""
        return [a.tag for a in self.assignments]

    def get_tags_in_category(self, category: RiskCategory) -> List[RiskTag]:
        """Get tags in a specific category."""
        return [
            a.tag for a in self.assignments
            if get_tag_category(a.tag) == category
        ]

    def has_tag(self, tag: RiskTag) -> bool:
        """Check if node has a specific tag."""
        return tag in self.get_tags()

    def has_category(self, category: RiskCategory) -> bool:
        """Check if node has any tag in category."""
        return len(self.get_tags_in_category(category)) > 0

    def get_highest_confidence(self) -> Optional[TagAssignment]:
        """Get assignment with highest confidence."""
        if not self.assignments:
            return None
        return max(self.assignments, key=lambda a: a.confidence)

    def get_by_source(self, source: str) -> List[TagAssignment]:
        """Get assignments by source."""
        return [a for a in self.assignments if a.source == source]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "assignments": [a.to_dict() for a in self.assignments],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "NodeTags":
        """Create from dictionary."""
        return NodeTags(
            node_id=data.get("node_id", ""),
            assignments=[
                TagAssignment.from_dict(a)
                for a in data.get("assignments", [])
            ],
        )


class TagStore:
    """Central storage for node tags.

    Provides efficient querying by tag, category, and node.
    """

    def __init__(self):
        """Initialize empty tag store."""
        # Primary storage: node_id -> NodeTags
        self._node_tags: Dict[str, NodeTags] = {}

        # Indexes for efficient querying
        self._tag_index: Dict[RiskTag, Set[str]] = {}  # tag -> node_ids
        self._category_index: Dict[RiskCategory, Set[str]] = {}  # category -> node_ids

    def add_tag(
        self,
        node_id: str,
        assignment: TagAssignment,
    ) -> None:
        """Add a tag assignment to a node.

        Args:
            node_id: ID of the node
            assignment: Tag assignment to add
        """
        # Get or create NodeTags
        if node_id not in self._node_tags:
            self._node_tags[node_id] = NodeTags(node_id=node_id)

        node_tags = self._node_tags[node_id]

        # Check if already exists
        if not node_tags.has_tag(assignment.tag):
            node_tags.add_assignment(assignment)

            # Update indexes
            if assignment.tag not in self._tag_index:
                self._tag_index[assignment.tag] = set()
            self._tag_index[assignment.tag].add(node_id)

            category = get_tag_category(assignment.tag)
            if category not in self._category_index:
                self._category_index[category] = set()
            self._category_index[category].add(node_id)

    def get_node_tags(self, node_id: str) -> Optional[NodeTags]:
        """Get tags for a node.

        Args:
            node_id: ID of the node

        Returns:
            NodeTags or None if no tags
        """
        return self._node_tags.get(node_id)

    def query_by_tag(self, tag: RiskTag) -> List[str]:
        """Get all node IDs with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of node IDs
        """
        return list(self._tag_index.get(tag, set()))

    def query_by_category(self, category: RiskCategory) -> List[str]:
        """Get all node IDs with any tag in category.

        Args:
            category: Category to search for

        Returns:
            List of node IDs
        """
        return list(self._category_index.get(category, set()))

    def query_by_tags(
        self,
        tags: List[RiskTag],
        match_all: bool = True,
    ) -> List[str]:
        """Get node IDs matching multiple tags.

        Args:
            tags: Tags to search for
            match_all: If True, require all tags; if False, any tag

        Returns:
            List of matching node IDs
        """
        if not tags:
            return []

        tag_sets = [self._tag_index.get(tag, set()) for tag in tags]

        if match_all:
            # Intersection - nodes with all tags
            result = tag_sets[0].copy()
            for s in tag_sets[1:]:
                result &= s
        else:
            # Union - nodes with any tag
            result = set()
            for s in tag_sets:
                result |= s

        return list(result)

    def query_by_confidence(
        self,
        min_confidence: float = 0.5,
        tag: Optional[RiskTag] = None,
    ) -> List[str]:
        """Get node IDs with tags above confidence threshold.

        Args:
            min_confidence: Minimum confidence threshold
            tag: Optional specific tag to filter by

        Returns:
            List of matching node IDs
        """
        results = []
        for node_id, node_tags in self._node_tags.items():
            for assignment in node_tags.assignments:
                if assignment.confidence >= min_confidence:
                    if tag is None or assignment.tag == tag:
                        results.append(node_id)
                        break  # Only add node once
        return results

    def get_all_tags(self) -> List[RiskTag]:
        """Get all tags currently in store.

        Returns:
            List of unique tags
        """
        return list(self._tag_index.keys())

    def get_tag_counts(self) -> Dict[RiskTag, int]:
        """Get count of nodes per tag.

        Returns:
            Dict mapping tag to count
        """
        return {tag: len(nodes) for tag, nodes in self._tag_index.items()}

    def get_category_counts(self) -> Dict[RiskCategory, int]:
        """Get count of nodes per category.

        Returns:
            Dict mapping category to count
        """
        return {cat: len(nodes) for cat, nodes in self._category_index.items()}

    def remove_tag(self, node_id: str, tag: RiskTag) -> bool:
        """Remove a tag from a node.

        Args:
            node_id: ID of the node
            tag: Tag to remove

        Returns:
            True if removed, False if not found
        """
        if node_id not in self._node_tags:
            return False

        node_tags = self._node_tags[node_id]
        original_len = len(node_tags.assignments)
        node_tags.assignments = [
            a for a in node_tags.assignments if a.tag != tag
        ]

        if len(node_tags.assignments) < original_len:
            # Update indexes
            if tag in self._tag_index:
                self._tag_index[tag].discard(node_id)
            category = get_tag_category(tag)
            if category in self._category_index:
                # Only remove from category if no other tags in category
                if not node_tags.has_category(category):
                    self._category_index[category].discard(node_id)
            return True
        return False

    def clear(self) -> None:
        """Clear all stored tags."""
        self._node_tags.clear()
        self._tag_index.clear()
        self._category_index.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize store to dictionary."""
        return {
            "node_tags": {
                node_id: tags.to_dict()
                for node_id, tags in self._node_tags.items()
            }
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TagStore":
        """Deserialize store from dictionary."""
        store = TagStore()
        for node_id, tags_data in data.get("node_tags", {}).items():
            node_tags = NodeTags.from_dict(tags_data)
            for assignment in node_tags.assignments:
                store.add_tag(node_id, assignment)
        return store


# Convenience functions for common operations

def add_tag_to_node(
    store: TagStore,
    node_id: str,
    tag: RiskTag,
    confidence: float = 1.0,
    source: str = "manual",
    reason: str = "",
) -> None:
    """Add a tag to a node.

    Args:
        store: Tag store
        node_id: ID of the node
        tag: Tag to add
        confidence: Confidence score
        source: Source of assignment
        reason: Reason for assignment
    """
    assignment = TagAssignment(
        tag=tag,
        confidence=confidence,
        source=source,
        reason=reason,
    )
    store.add_tag(node_id, assignment)


def get_node_tags(
    store: TagStore,
    node_id: str,
) -> List[RiskTag]:
    """Get all tags for a node.

    Args:
        store: Tag store
        node_id: ID of the node

    Returns:
        List of tags
    """
    node_tags = store.get_node_tags(node_id)
    if node_tags:
        return node_tags.get_tags()
    return []


def query_nodes_by_tag(
    store: TagStore,
    tag: RiskTag,
) -> List[str]:
    """Query nodes by tag.

    Args:
        store: Tag store
        tag: Tag to search for

    Returns:
        List of node IDs
    """
    return store.query_by_tag(tag)


__all__ = [
    "NodeTags",
    "TagStore",
    "add_tag_to_node",
    "get_node_tags",
    "query_nodes_by_tag",
]
