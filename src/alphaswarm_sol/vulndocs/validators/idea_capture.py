"""Idea Capture Validator.

Task 18.2: Ensures no unique ideas from source summaries are lost
during the merge process.

Design Principle: "Every unique idea captured" guarantee.
- Even slightly different scenarios should be preserved
- We err on the side of capturing too much rather than losing information
- Source A says "attack works on ETH transfers" and Source B says
  "attack works on ERC20 transfers" - BOTH should be in merged doc

This validator compares source summaries against merged documents to
detect any information loss.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from alphaswarm_sol.vulndocs.knowledge_doc import (
    MergeResult,
    SourceSummary,
    UniqueIdea,
    VulnKnowledgeDoc,
)


class IdeaLossType(Enum):
    """Type of idea loss detected."""

    # Critical losses
    ATTACK_VARIANT = "attack_variant"  # Missing attack scenario
    MITIGATION = "mitigation"  # Missing fix approach
    EDGE_CASE = "edge_case"  # Missing edge case/gotcha
    REAL_EXPLOIT = "real_exploit"  # Missing real-world example

    # Important losses
    CODE_EXAMPLE = "code_example"  # Missing code sample
    DETECTION_HINT = "detection_hint"  # Missing detection approach
    PREREQUISITE = "prerequisite"  # Missing attack prerequisite

    # Minor losses
    KEYWORD = "keyword"  # Missing important keyword
    SOURCE_REF = "source_ref"  # Missing source attribution


@dataclass
class IdeaCapture:
    """A captured idea from source summaries."""

    id: str
    content: str
    idea_type: IdeaLossType
    source_url: str
    source_name: str
    content_hash: str = ""

    def __post_init__(self):
        """Compute hash if not provided."""
        if not self.content_hash:
            self.content_hash = hashlib.md5(
                self.content.lower().encode()
            ).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "idea_type": self.idea_type.value,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "content_hash": self.content_hash,
        }


@dataclass
class IdeaLoss:
    """A lost idea detected during validation."""

    idea: IdeaCapture
    severity: str  # "critical", "important", "minor"
    reason: str
    suggestion: str = ""  # Suggestion for recovery

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "idea": self.idea.to_dict(),
            "severity": self.severity,
            "reason": self.reason,
            "suggestion": self.suggestion,
        }


@dataclass
class IdeaCaptureResult:
    """Result of idea capture validation."""

    success: bool  # True if no critical losses
    total_ideas: int
    captured_ideas: int
    lost_ideas: List[IdeaLoss] = field(default_factory=list)
    capture_rate: float = 0.0
    critical_losses: int = 0
    important_losses: int = 0
    minor_losses: int = 0

    def __post_init__(self):
        """Calculate rates and counts."""
        if self.total_ideas > 0:
            self.capture_rate = self.captured_ideas / self.total_ideas

        for loss in self.lost_ideas:
            if loss.severity == "critical":
                self.critical_losses += 1
            elif loss.severity == "important":
                self.important_losses += 1
            else:
                self.minor_losses += 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "total_ideas": self.total_ideas,
            "captured_ideas": self.captured_ideas,
            "lost_ideas": [l.to_dict() for l in self.lost_ideas],
            "capture_rate": self.capture_rate,
            "critical_losses": self.critical_losses,
            "important_losses": self.important_losses,
            "minor_losses": self.minor_losses,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Idea Capture Validation: {'PASSED' if self.success else 'FAILED'}",
            f"  Total Ideas: {self.total_ideas}",
            f"  Captured: {self.captured_ideas} ({self.capture_rate*100:.1f}%)",
        ]

        if self.lost_ideas:
            lines.append(f"  Lost: {len(self.lost_ideas)}")
            lines.append(f"    Critical: {self.critical_losses}")
            lines.append(f"    Important: {self.important_losses}")
            lines.append(f"    Minor: {self.minor_losses}")

        return "\n".join(lines)


class IdeaCaptureValidator:
    """Validates that no unique ideas are lost during merging.

    Uses content hashing and semantic similarity to detect if ideas
    from source summaries appear in the merged document.

    Example:
        >>> validator = IdeaCaptureValidator()
        >>> result = validator.validate(summaries, merged_doc)
        >>> if not result.success:
        ...     print(f"Lost {len(result.lost_ideas)} ideas!")
    """

    def __init__(
        self,
        similarity_threshold: float = 0.7,
        critical_loss_types: Optional[List[IdeaLossType]] = None,
    ):
        """Initialize the validator.

        Args:
            similarity_threshold: Minimum similarity for "captured" (0-1)
            critical_loss_types: Types considered critical losses
        """
        self.similarity_threshold = similarity_threshold
        self.critical_loss_types = critical_loss_types or [
            IdeaLossType.ATTACK_VARIANT,
            IdeaLossType.MITIGATION,
            IdeaLossType.EDGE_CASE,
            IdeaLossType.REAL_EXPLOIT,
        ]

        # Stop words for similarity calculation
        self.stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "to", "of", "in", "for", "on", "with", "at",
            "by", "from", "as", "into", "through", "during", "before",
            "after", "above", "below", "between", "under", "again",
            "further", "then", "once", "here", "there", "when", "where",
            "why", "how", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "and",
            "but", "if", "or", "because", "until", "while", "this",
            "that", "these", "those", "it", "its",
        }

    def validate(
        self,
        summaries: List[SourceSummary],
        document: VulnKnowledgeDoc,
    ) -> IdeaCaptureResult:
        """Validate that all ideas from summaries appear in document.

        Args:
            summaries: Source summaries with extracted ideas
            document: Merged document to validate against

        Returns:
            Validation result with any lost ideas
        """
        # Extract all ideas from summaries
        ideas = self._extract_ideas_from_summaries(summaries)

        # Extract searchable content from document
        doc_content = self._get_document_content(document)

        # Check each idea for capture
        lost_ideas = []
        captured_count = 0

        for idea in ideas:
            if self._is_idea_captured(idea, doc_content):
                captured_count += 1
            else:
                loss = self._create_loss_record(idea, document)
                lost_ideas.append(loss)

        # Determine success (no critical losses)
        success = all(
            loss.severity != "critical" for loss in lost_ideas
        )

        return IdeaCaptureResult(
            success=success,
            total_ideas=len(ideas),
            captured_ideas=captured_count,
            lost_ideas=lost_ideas,
        )

    def validate_merge_result(
        self,
        merge_result: MergeResult,
        summaries: List[SourceSummary],
    ) -> IdeaCaptureResult:
        """Validate a MergeResult against its source summaries.

        Args:
            merge_result: The merge result with document and unique ideas
            summaries: Original source summaries

        Returns:
            Validation result
        """
        # First check the tracked unique ideas
        tracked_losses = []

        for idea in merge_result.unique_ideas:
            if not idea.merged:
                # This idea wasn't merged - check if it's critical
                idea_capture = IdeaCapture(
                    id=idea.id,
                    content=idea.description,
                    idea_type=self._classify_idea_type(idea.idea_type),
                    source_url=idea.source_urls[0] if idea.source_urls else "",
                    source_name=idea.category,
                )
                loss = self._create_loss_record(idea_capture, merge_result.document)
                tracked_losses.append(loss)

        # Then do full validation against summaries
        full_result = self.validate(summaries, merge_result.document)

        # Combine losses (avoid duplicates by content hash)
        existing_hashes = {l.idea.content_hash for l in full_result.lost_ideas}
        for loss in tracked_losses:
            if loss.idea.content_hash not in existing_hashes:
                full_result.lost_ideas.append(loss)

        # Recalculate success
        full_result.success = all(
            loss.severity != "critical" for loss in full_result.lost_ideas
        )

        return full_result

    def _extract_ideas_from_summaries(
        self,
        summaries: List[SourceSummary],
    ) -> List[IdeaCapture]:
        """Extract all unique ideas from summaries.

        Args:
            summaries: Source summaries to process

        Returns:
            List of unique ideas
        """
        ideas = []
        seen_hashes: Set[str] = set()

        for summary in summaries:
            # Key points
            for i, point in enumerate(summary.key_points):
                idea = IdeaCapture(
                    id=f"{summary.source_name}_keypoint_{i}",
                    content=point,
                    idea_type=IdeaLossType.DETECTION_HINT,
                    source_url=summary.source_url,
                    source_name=summary.source_name,
                )
                if idea.content_hash not in seen_hashes:
                    seen_hashes.add(idea.content_hash)
                    ideas.append(idea)

            # Attack vector
            if summary.attack_vector:
                idea = IdeaCapture(
                    id=f"{summary.source_name}_attack",
                    content=summary.attack_vector,
                    idea_type=IdeaLossType.ATTACK_VARIANT,
                    source_url=summary.source_url,
                    source_name=summary.source_name,
                )
                if idea.content_hash not in seen_hashes:
                    seen_hashes.add(idea.content_hash)
                    ideas.append(idea)

            # Attack steps
            for i, step in enumerate(summary.attack_steps):
                idea = IdeaCapture(
                    id=f"{summary.source_name}_step_{i}",
                    content=step,
                    idea_type=IdeaLossType.ATTACK_VARIANT,
                    source_url=summary.source_url,
                    source_name=summary.source_name,
                )
                if idea.content_hash not in seen_hashes:
                    seen_hashes.add(idea.content_hash)
                    ideas.append(idea)

            # Mitigation
            if summary.mitigation:
                idea = IdeaCapture(
                    id=f"{summary.source_name}_mitigation",
                    content=summary.mitigation,
                    idea_type=IdeaLossType.MITIGATION,
                    source_url=summary.source_url,
                    source_name=summary.source_name,
                )
                if idea.content_hash not in seen_hashes:
                    seen_hashes.add(idea.content_hash)
                    ideas.append(idea)

            # Safe patterns
            for i, pattern in enumerate(summary.safe_patterns):
                idea = IdeaCapture(
                    id=f"{summary.source_name}_pattern_{i}",
                    content=pattern,
                    idea_type=IdeaLossType.MITIGATION,
                    source_url=summary.source_url,
                    source_name=summary.source_name,
                )
                if idea.content_hash not in seen_hashes:
                    seen_hashes.add(idea.content_hash)
                    ideas.append(idea)

            # Code examples (only count as ideas if substantial)
            if summary.vulnerable_code and len(summary.vulnerable_code) > 50:
                idea = IdeaCapture(
                    id=f"{summary.source_name}_vuln_code",
                    content=summary.vulnerable_code[:200],  # Truncate for hash
                    idea_type=IdeaLossType.CODE_EXAMPLE,
                    source_url=summary.source_url,
                    source_name=summary.source_name,
                )
                if idea.content_hash not in seen_hashes:
                    seen_hashes.add(idea.content_hash)
                    ideas.append(idea)

            # Incidents
            for i, incident in enumerate(summary.incidents):
                incident_text = incident.get("name", "") + " " + incident.get("brief", "")
                if incident_text.strip():
                    idea = IdeaCapture(
                        id=f"{summary.source_name}_incident_{i}",
                        content=incident_text,
                        idea_type=IdeaLossType.REAL_EXPLOIT,
                        source_url=summary.source_url,
                        source_name=summary.source_name,
                    )
                    if idea.content_hash not in seen_hashes:
                        seen_hashes.add(idea.content_hash)
                        ideas.append(idea)

        return ideas

    def _get_document_content(self, document: VulnKnowledgeDoc) -> str:
        """Extract all searchable content from a document.

        Args:
            document: Document to extract content from

        Returns:
            Combined content string (lowercase)
        """
        parts = [
            document.name,
            document.one_liner,
            document.tldr,
            # Detection
            " ".join(document.detection.graph_signals),
            document.detection.vulnerable_sequence,
            document.detection.safe_sequence,
            " ".join(document.detection.indicators),
            " ".join(document.detection.checklist),
            # Exploitation
            document.exploitation.attack_vector,
            " ".join(document.exploitation.prerequisites),
            " ".join(document.exploitation.attack_steps),
            document.exploitation.potential_impact,
            # Mitigation
            document.mitigation.primary_fix,
            " ".join(document.mitigation.alternative_fixes),
            document.mitigation.safe_pattern,
            " ".join(document.mitigation.how_to_verify),
            # Examples
            document.examples.vulnerable_code,
            document.examples.vulnerable_code_explanation,
            document.examples.fixed_code,
            document.examples.fixed_code_explanation,
        ]

        # Add real exploit references
        for exploit in document.examples.real_exploits:
            parts.extend([
                exploit.name,
                exploit.protocol,
                exploit.brief,
            ])

        return " ".join(parts).lower()

    def _is_idea_captured(
        self,
        idea: IdeaCapture,
        doc_content: str,
    ) -> bool:
        """Check if an idea is captured in document content.

        Args:
            idea: The idea to check
            doc_content: Document content to search

        Returns:
            True if idea is captured
        """
        # Exact substring match (case-insensitive)
        idea_lower = idea.content.lower()
        if idea_lower in doc_content:
            return True

        # Token-based similarity
        idea_tokens = self._tokenize(idea_lower)
        doc_tokens = set(self._tokenize(doc_content))

        if not idea_tokens:
            return True  # Empty idea is "captured"

        # Calculate token overlap
        overlap = sum(1 for t in idea_tokens if t in doc_tokens)
        similarity = overlap / len(idea_tokens)

        return similarity >= self.similarity_threshold

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text, removing stop words.

        Args:
            text: Text to tokenize

        Returns:
            List of significant tokens
        """
        # Extract words
        words = re.findall(r'\b[a-z]+\b', text.lower())

        # Remove stop words and very short words
        return [w for w in words if w not in self.stop_words and len(w) > 2]

    def _classify_idea_type(self, type_str: str) -> IdeaLossType:
        """Classify idea type from string.

        Args:
            type_str: String type representation

        Returns:
            IdeaLossType enum value
        """
        type_map = {
            "attack_variant": IdeaLossType.ATTACK_VARIANT,
            "attack": IdeaLossType.ATTACK_VARIANT,
            "detection": IdeaLossType.DETECTION_HINT,
            "mitigation": IdeaLossType.MITIGATION,
            "fix": IdeaLossType.MITIGATION,
            "edge_case": IdeaLossType.EDGE_CASE,
            "example": IdeaLossType.CODE_EXAMPLE,
            "code": IdeaLossType.CODE_EXAMPLE,
            "exploit": IdeaLossType.REAL_EXPLOIT,
            "incident": IdeaLossType.REAL_EXPLOIT,
        }
        return type_map.get(type_str.lower(), IdeaLossType.KEYWORD)

    def _create_loss_record(
        self,
        idea: IdeaCapture,
        document: VulnKnowledgeDoc,
    ) -> IdeaLoss:
        """Create a loss record for an uncaptured idea.

        Args:
            idea: The lost idea
            document: Document that should have captured it

        Returns:
            IdeaLoss record with severity and suggestions
        """
        # Determine severity based on idea type
        if idea.idea_type in self.critical_loss_types:
            severity = "critical"
        elif idea.idea_type in [IdeaLossType.CODE_EXAMPLE, IdeaLossType.DETECTION_HINT]:
            severity = "important"
        else:
            severity = "minor"

        # Generate suggestion based on type
        suggestion_map = {
            IdeaLossType.ATTACK_VARIANT: f"Add to exploitation.attack_steps",
            IdeaLossType.MITIGATION: f"Add to mitigation.alternative_fixes",
            IdeaLossType.EDGE_CASE: f"Add as detection indicator or checklist item",
            IdeaLossType.REAL_EXPLOIT: f"Add to examples.real_exploits",
            IdeaLossType.CODE_EXAMPLE: f"Add to examples.vulnerable_code or fixed_code",
            IdeaLossType.DETECTION_HINT: f"Add to detection.indicators",
            IdeaLossType.PREREQUISITE: f"Add to exploitation.prerequisites",
            IdeaLossType.KEYWORD: f"Consider adding to metadata.keywords",
            IdeaLossType.SOURCE_REF: f"Add to metadata.sources",
        }

        return IdeaLoss(
            idea=idea,
            severity=severity,
            reason=f"Content not found in merged document section for {idea.idea_type.value}",
            suggestion=suggestion_map.get(idea.idea_type, "Review and add to appropriate section"),
        )


def validate_idea_capture(
    summaries: List[SourceSummary],
    document: VulnKnowledgeDoc,
    similarity_threshold: float = 0.7,
) -> IdeaCaptureResult:
    """Convenience function for idea capture validation.

    Args:
        summaries: Source summaries with extracted ideas
        document: Merged document to validate against
        similarity_threshold: Minimum similarity for "captured"

    Returns:
        Validation result with any lost ideas
    """
    validator = IdeaCaptureValidator(similarity_threshold=similarity_threshold)
    return validator.validate(summaries, document)
