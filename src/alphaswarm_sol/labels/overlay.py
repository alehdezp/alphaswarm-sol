"""Label overlay for graph-level label storage.

Labels are stored separately from core graph properties to:
- Keep deterministic properties unchanged
- Allow label updates without rebuilding graph
- Support label export/import
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .schema import FunctionLabel, LabelConfidence, LabelSet


@dataclass
class LabelOverlay:
    """Overlay layer storing labels for a graph.

    Labels are stored separately from core graph properties to:
    - Keep deterministic properties unchanged
    - Allow label updates without rebuilding graph
    - Support label export/import

    Attributes:
        labels: Mapping from function_id to LabelSet
        version: Schema version
        created_at: When overlay was created
        metadata: Additional metadata
    """

    labels: Dict[str, LabelSet] = field(default_factory=dict)
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_labels(self, function_id: str) -> LabelSet:
        """Get labels for a function (creates empty set if missing).

        Args:
            function_id: Function ID to get labels for

        Returns:
            LabelSet for the function
        """
        if function_id not in self.labels:
            self.labels[function_id] = LabelSet(function_id=function_id)
        return self.labels[function_id]

    def add_label(self, function_id: str, label: FunctionLabel) -> None:
        """Add a label to a function.

        Args:
            function_id: Function ID to add label to
            label: Label to add
        """
        label_set = self.get_labels(function_id)
        label_set.add(label)

    def remove_label(self, function_id: str, label_id: str) -> bool:
        """Remove a label from a function.

        Args:
            function_id: Function ID to remove label from
            label_id: Label ID to remove

        Returns:
            True if label was removed, False if not found
        """
        if function_id not in self.labels:
            return False
        return self.labels[function_id].remove(label_id)

    def get_functions_with_label(
        self,
        label_id: str,
        min_confidence: LabelConfidence = LabelConfidence.MEDIUM,
    ) -> List[str]:
        """Find all functions with a specific label.

        Args:
            label_id: Label ID to search for
            min_confidence: Minimum confidence required

        Returns:
            List of function IDs with the label
        """
        result = []
        for function_id, label_set in self.labels.items():
            if label_set.has_label(label_id, min_confidence):
                result.append(function_id)
        return result

    def get_all_labels_by_category(
        self, category: str
    ) -> Dict[str, List[FunctionLabel]]:
        """Get all labels in a category, grouped by function.

        Args:
            category: Category to filter by

        Returns:
            Dict mapping function_id to list of labels in category
        """
        result: Dict[str, List[FunctionLabel]] = {}
        for function_id, label_set in self.labels.items():
            category_labels = label_set.get_by_category(category)
            if category_labels:
                result[function_id] = category_labels
        return result

    def get_all_functions(self) -> List[str]:
        """Get all function IDs with labels.

        Returns:
            List of function IDs
        """
        return list(self.labels.keys())

    def get_label_count(self) -> int:
        """Get total number of labels across all functions.

        Returns:
            Total label count
        """
        return sum(len(ls.labels) for ls in self.labels.values())

    def merge(self, other: "LabelOverlay") -> "LabelOverlay":
        """Merge another overlay (other takes precedence).

        Args:
            other: Overlay to merge in

        Returns:
            New merged overlay
        """
        merged = LabelOverlay(
            version=self.version,
            created_at=datetime.now(),
            metadata={
                **self.metadata,
                "merged_from": [
                    self.created_at.isoformat(),
                    other.created_at.isoformat(),
                ],
            },
        )

        # Copy this overlay's labels
        for function_id, label_set in self.labels.items():
            for label in label_set.labels:
                merged.add_label(function_id, label)

        # Merge other overlay's labels (will replace on conflict)
        for function_id, label_set in other.labels.items():
            for label in label_set.labels:
                merged.add_label(function_id, label)

        return merged

    def export_json(self, path: Path) -> None:
        """Export labels to JSON file.

        Args:
            path: Path to write JSON file
        """
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def export_yaml(self, path: Path) -> None:
        """Export labels to YAML file.

        Args:
            path: Path to write YAML file
        """
        data = self.to_dict()
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_json(cls, path: Path) -> "LabelOverlay":
        """Load from JSON file.

        Args:
            path: Path to JSON file

        Returns:
            LabelOverlay instance
        """
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, path: Path) -> "LabelOverlay":
        """Load from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            LabelOverlay instance
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize overlay to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "labels": {
                function_id: label_set.to_dict()
                for function_id, label_set in self.labels.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LabelOverlay":
        """Deserialize overlay from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            LabelOverlay instance
        """
        overlay = cls(
            version=data.get("version", "1.0"),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(),
            metadata=data.get("metadata", {}),
        )

        # Load labels
        labels_data = data.get("labels", {})
        for function_id, label_set_data in labels_data.items():
            overlay.labels[function_id] = LabelSet.from_dict(label_set_data)

        return overlay


__all__ = [
    "LabelOverlay",
]
