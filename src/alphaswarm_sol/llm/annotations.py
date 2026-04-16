"""Phase 12: LLM Annotation Schema.

This module provides the data structures for LLM-generated annotations
that enhance the knowledge graph with semantic understanding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
import hashlib


class AnnotationType(str, Enum):
    """Types of LLM annotations."""
    RISK_ASSESSMENT = "risk_assessment"
    INTENT_ANALYSIS = "intent_analysis"
    BUSINESS_CONTEXT = "business_context"
    VULNERABILITY_EXPLANATION = "vulnerability_explanation"
    REMEDIATION_SUGGESTION = "remediation_suggestion"
    FALSE_POSITIVE_ANALYSIS = "false_positive_analysis"
    PATTERN_MATCH = "pattern_match"


class AnnotationSource(str, Enum):
    """Source of annotation."""
    LLM_GPT4 = "llm_gpt4"
    LLM_CLAUDE = "llm_claude"
    LLM_LOCAL = "llm_local"
    PATTERN_LIBRARY = "pattern_library"
    USER = "user"
    AUTOMATED = "automated"


@dataclass
class LLMAnnotation:
    """Represents an LLM-generated annotation.

    Annotations provide semantic enrichment to graph nodes, adding
    context that deterministic analysis cannot provide.

    Attributes:
        node_id: ID of the annotated node
        annotation_type: Type of annotation
        risk_tags: List of risk classification tags
        confidence: Confidence score (0.0 - 1.0)
        description: Human-readable description
        developer_intent: Inferred developer intent
        business_context: Business context if available
        source: Source of the annotation
        timestamp: When annotation was created
        model: Model used for generation
        metadata: Additional metadata
    """
    node_id: str
    annotation_type: AnnotationType
    risk_tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    description: str = ""
    developer_intent: Optional[str] = None
    business_context: Optional[str] = None
    source: AnnotationSource = AnnotationSource.AUTOMATED
    timestamp: Optional[str] = None
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize annotation to dictionary."""
        return {
            "node_id": self.node_id,
            "annotation_type": self.annotation_type.value,
            "risk_tags": self.risk_tags,
            "confidence": self.confidence,
            "description": self.description,
            "developer_intent": self.developer_intent,
            "business_context": self.business_context,
            "source": self.source.value,
            "timestamp": self.timestamp,
            "model": self.model,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "LLMAnnotation":
        """Deserialize annotation from dictionary."""
        return LLMAnnotation(
            node_id=data.get("node_id", ""),
            annotation_type=AnnotationType(data.get("annotation_type", "risk_assessment")),
            risk_tags=data.get("risk_tags", []),
            confidence=float(data.get("confidence", 0.0)),
            description=data.get("description", ""),
            developer_intent=data.get("developer_intent"),
            business_context=data.get("business_context"),
            source=AnnotationSource(data.get("source", "automated")),
            timestamp=data.get("timestamp"),
            model=data.get("model"),
            metadata=data.get("metadata", {}),
        )

    def get_hash(self) -> str:
        """Get hash for caching purposes."""
        content = f"{self.node_id}:{self.annotation_type.value}:{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class AnnotationSet:
    """Collection of annotations for a node or subgraph.

    Attributes:
        annotations: List of annotations
        node_id: Optional node ID if set is for a single node
        summary: Optional summary combining annotations
    """
    annotations: List[LLMAnnotation] = field(default_factory=list)
    node_id: Optional[str] = None
    summary: Optional[str] = None

    def add(self, annotation: LLMAnnotation) -> None:
        """Add an annotation to the set."""
        self.annotations.append(annotation)

    def get_by_type(self, ann_type: AnnotationType) -> List[LLMAnnotation]:
        """Get annotations by type."""
        return [a for a in self.annotations if a.annotation_type == ann_type]

    def get_high_confidence(self, threshold: float = 0.8) -> List[LLMAnnotation]:
        """Get high-confidence annotations."""
        return [a for a in self.annotations if a.confidence >= threshold]

    def get_risk_tags(self) -> List[str]:
        """Get all unique risk tags."""
        tags = set()
        for ann in self.annotations:
            tags.update(ann.risk_tags)
        return sorted(tags)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annotations": [a.to_dict() for a in self.annotations],
            "node_id": self.node_id,
            "summary": self.summary,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AnnotationSet":
        return AnnotationSet(
            annotations=[LLMAnnotation.from_dict(a) for a in data.get("annotations", [])],
            node_id=data.get("node_id"),
            summary=data.get("summary"),
        )


def create_annotation(
    node_id: str,
    ann_type: AnnotationType,
    description: str,
    confidence: float = 0.8,
    risk_tags: Optional[List[str]] = None,
    developer_intent: Optional[str] = None,
    business_context: Optional[str] = None,
    source: AnnotationSource = AnnotationSource.AUTOMATED,
    model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> LLMAnnotation:
    """Create an annotation with sensible defaults.

    Args:
        node_id: Node being annotated
        ann_type: Type of annotation
        description: Description text
        confidence: Confidence score
        risk_tags: Optional risk tags
        developer_intent: Optional intent description
        business_context: Optional business context
        source: Annotation source
        model: Optional model name
        metadata: Optional metadata

    Returns:
        LLMAnnotation instance
    """
    return LLMAnnotation(
        node_id=node_id,
        annotation_type=ann_type,
        description=description,
        confidence=confidence,
        risk_tags=risk_tags or [],
        developer_intent=developer_intent,
        business_context=business_context,
        source=source,
        model=model,
        metadata=metadata or {},
    )


def merge_annotations(
    annotations: List[LLMAnnotation],
) -> LLMAnnotation:
    """Merge multiple annotations into one.

    Takes the highest confidence annotation as base and merges risk tags.

    Args:
        annotations: List of annotations to merge

    Returns:
        Merged annotation
    """
    if not annotations:
        raise ValueError("Cannot merge empty annotation list")

    if len(annotations) == 1:
        return annotations[0]

    # Sort by confidence
    sorted_anns = sorted(annotations, key=lambda a: a.confidence, reverse=True)
    base = sorted_anns[0]

    # Merge risk tags
    all_tags = set(base.risk_tags)
    for ann in sorted_anns[1:]:
        all_tags.update(ann.risk_tags)

    # Merge descriptions
    descriptions = [base.description]
    for ann in sorted_anns[1:]:
        if ann.description and ann.description not in descriptions:
            descriptions.append(ann.description)

    merged_description = " | ".join(descriptions) if len(descriptions) > 1 else base.description

    # Create merged annotation
    return LLMAnnotation(
        node_id=base.node_id,
        annotation_type=base.annotation_type,
        risk_tags=sorted(all_tags),
        confidence=base.confidence,
        description=merged_description,
        developer_intent=base.developer_intent,
        business_context=base.business_context,
        source=base.source,
        model=base.model,
        metadata={
            "merged_from": len(annotations),
            "original_hashes": [a.get_hash() for a in annotations],
        },
    )


__all__ = [
    "AnnotationType",
    "AnnotationSource",
    "LLMAnnotation",
    "AnnotationSet",
    "create_annotation",
    "merge_annotations",
]
