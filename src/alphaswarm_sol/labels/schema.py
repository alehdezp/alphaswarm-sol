"""Label schema definitions for function labeling.

This module provides the data structures for attaching semantic labels
to functions, including confidence levels and source tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class LabelConfidence(str, Enum):
    """Confidence level for label assignments.

    HIGH: >= 0.8 confidence - Strong indicators present
    MEDIUM: >= 0.5 confidence - Moderate indicators present
    LOW: < 0.5 confidence - Weak indicators, requires review
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def threshold(self) -> float:
        """Get the numeric threshold for this confidence level.

        Returns:
            Float threshold value
        """
        return {"high": 0.8, "medium": 0.5, "low": 0.0}[self.value]

    @classmethod
    def from_score(cls, score: float) -> "LabelConfidence":
        """Convert a numeric score to confidence level.

        Args:
            score: Confidence score between 0.0 and 1.0

        Returns:
            Corresponding LabelConfidence level
        """
        if score >= 0.8:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        else:
            return cls.LOW


class LabelSource(str, Enum):
    """Source of the label assignment."""

    LLM = "llm"  # LLM-assigned via tool calling
    USER_OVERRIDE = "user_override"  # Manual override by user
    PATTERN_INFERRED = "pattern"  # Inferred from pattern match


@dataclass
class FunctionLabel:
    """A semantic label attached to a function.

    Attributes:
        label_id: Label ID in category.subcategory format
        confidence: Confidence level of the assignment
        source: Source of the label assignment
        reasoning: Required if confidence is LOW - explain uncertainty
        timestamp: When the label was assigned
        source_hash: Hash of function source for staleness detection
    """

    label_id: str
    confidence: LabelConfidence
    source: LabelSource
    reasoning: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    source_hash: Optional[str] = None

    def __post_init__(self):
        """Validate label and convert types if needed."""
        # Ensure confidence is enum
        if isinstance(self.confidence, str):
            self.confidence = LabelConfidence(self.confidence)
        # Ensure source is enum
        if isinstance(self.source, str):
            self.source = LabelSource(self.source)
        # Ensure timestamp is datetime
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    @property
    def category(self) -> str:
        """Get the category portion of the label ID.

        Returns:
            Category string (e.g., "access_control")
        """
        return self.label_id.split(".")[0]

    @property
    def subcategory(self) -> str:
        """Get the subcategory portion of the label ID.

        Returns:
            Subcategory string (e.g., "owner_only")
        """
        parts = self.label_id.split(".")
        return parts[1] if len(parts) > 1 else ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize label to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "label_id": self.label_id,
            "confidence": self.confidence.value,
            "source": self.source.value,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
            "source_hash": self.source_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FunctionLabel":
        """Deserialize label from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            FunctionLabel instance
        """
        return cls(
            label_id=data["label_id"],
            confidence=LabelConfidence(data["confidence"]),
            source=LabelSource(data["source"]),
            reasoning=data.get("reasoning"),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(),
            source_hash=data.get("source_hash"),
        )


@dataclass
class LabelSet:
    """Collection of labels for a single function.

    Attributes:
        function_id: ID of the labeled function
        labels: List of labels attached to the function
    """

    function_id: str
    labels: List[FunctionLabel] = field(default_factory=list)

    def add(self, label: FunctionLabel) -> None:
        """Add a label to the set.

        If a label with the same ID already exists, it is replaced
        if the new label has higher confidence.

        Args:
            label: Label to add
        """
        # Check if label with same ID exists
        for i, existing in enumerate(self.labels):
            if existing.label_id == label.label_id:
                # Replace if new label has higher confidence or newer timestamp
                confidence_order = {
                    LabelConfidence.HIGH: 3,
                    LabelConfidence.MEDIUM: 2,
                    LabelConfidence.LOW: 1,
                }
                if confidence_order[label.confidence] >= confidence_order[
                    existing.confidence
                ]:
                    self.labels[i] = label
                return

        # No existing label, add new one
        self.labels.append(label)

    def remove(self, label_id: str) -> bool:
        """Remove a label by ID.

        Args:
            label_id: ID of label to remove

        Returns:
            True if label was removed, False if not found
        """
        for i, label in enumerate(self.labels):
            if label.label_id == label_id:
                self.labels.pop(i)
                return True
        return False

    def get_by_category(self, category: str) -> List[FunctionLabel]:
        """Get labels in a specific category.

        Args:
            category: Category to filter by

        Returns:
            List of labels in the category
        """
        return [l for l in self.labels if l.category == category]

    def get_high_confidence(self) -> List[FunctionLabel]:
        """Get labels with HIGH confidence.

        Returns:
            List of high-confidence labels
        """
        return [l for l in self.labels if l.confidence == LabelConfidence.HIGH]

    def get_by_confidence(
        self, min_confidence: LabelConfidence
    ) -> List[FunctionLabel]:
        """Get labels meeting minimum confidence threshold.

        Args:
            min_confidence: Minimum confidence level

        Returns:
            List of labels meeting threshold
        """
        threshold = min_confidence.threshold()
        return [l for l in self.labels if l.confidence.threshold() >= threshold]

    def has_label(
        self,
        label_id: str,
        min_confidence: LabelConfidence = LabelConfidence.LOW,
    ) -> bool:
        """Check if function has a specific label with minimum confidence.

        Args:
            label_id: Label ID to check
            min_confidence: Minimum confidence required

        Returns:
            True if label exists with sufficient confidence
        """
        threshold = min_confidence.threshold()
        for label in self.labels:
            if (
                label.label_id == label_id
                and label.confidence.threshold() >= threshold
            ):
                return True
        return False

    def get_label(self, label_id: str) -> Optional[FunctionLabel]:
        """Get a specific label by ID.

        Args:
            label_id: Label ID to retrieve

        Returns:
            FunctionLabel if found, None otherwise
        """
        for label in self.labels:
            if label.label_id == label_id:
                return label
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize label set to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "function_id": self.function_id,
            "labels": [l.to_dict() for l in self.labels],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LabelSet":
        """Deserialize label set from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            LabelSet instance
        """
        return cls(
            function_id=data["function_id"],
            labels=[FunctionLabel.from_dict(l) for l in data.get("labels", [])],
        )


__all__ = [
    "LabelConfidence",
    "LabelSource",
    "FunctionLabel",
    "LabelSet",
]
