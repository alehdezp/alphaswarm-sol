"""Quality Scorer for VulnKnowledgeDoc.

Task 18.2: Computes multi-dimensional quality scores for documents.

Quality Dimensions:
- Accuracy: How accurate is the information (based on source authority)
- Completeness: How complete is the document (all sections filled)
- Clarity: How clear and well-written is the content
- Actionability: How actionable is the information (practical fixes)
- Evidence: How well-supported by real-world evidence

The overall quality score is a weighted combination of these dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import re

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc, PatternLinkageType
from alphaswarm_sol.vulndocs.validators.completeness import (
    CompletenessValidator,
    CompletenessResult,
)


class QualityDimension(Enum):
    """Dimensions of document quality."""

    ACCURACY = "accuracy"  # Based on source authority
    COMPLETENESS = "completeness"  # All sections present
    CLARITY = "clarity"  # Clear, well-structured content
    ACTIONABILITY = "actionability"  # Practical, implementable fixes
    EVIDENCE = "evidence"  # Supported by real-world examples


@dataclass
class QualityScore:
    """Score for a single quality dimension."""

    dimension: QualityDimension
    score: float  # 0-1
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "notes": self.notes,
        }


@dataclass
class QualityResult:
    """Result of quality scoring."""

    overall_score: float  # 0-1
    grade: str  # A, B, C, D, F
    dimensions: Dict[QualityDimension, QualityScore] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "dimensions": {k.value: v.to_dict() for k, v in self.dimensions.items()},
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Quality Score: {self.overall_score:.2f} (Grade: {self.grade})",
            "",
            "Dimensions:",
        ]

        for dim, score in self.dimensions.items():
            bar = "#" * int(score.score * 10) + "-" * (10 - int(score.score * 10))
            lines.append(f"  {dim.value}: [{bar}] {score.score:.2f}")
            for note in score.notes[:2]:
                lines.append(f"    - {note}")

        if self.strengths:
            lines.append("")
            lines.append("Strengths:")
            for s in self.strengths[:3]:
                lines.append(f"  + {s}")

        if self.weaknesses:
            lines.append("")
            lines.append("Weaknesses:")
            for w in self.weaknesses[:3]:
                lines.append(f"  - {w}")

        if self.suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for s in self.suggestions[:3]:
                lines.append(f"  > {s}")

        return "\n".join(lines)


class QualityScorer:
    """Computes quality scores for VulnKnowledgeDoc documents.

    Uses multiple dimensions to assess document quality and provide
    actionable feedback for improvement.

    Example:
        >>> scorer = QualityScorer()
        >>> result = scorer.score(document)
        >>> print(f"Quality: {result.grade} ({result.overall_score:.2f})")
    """

    def __init__(
        self,
        dimension_weights: Optional[Dict[QualityDimension, float]] = None,
    ):
        """Initialize the scorer.

        Args:
            dimension_weights: Custom weights for each dimension
        """
        self.dimension_weights = dimension_weights or {
            QualityDimension.ACCURACY: 0.25,
            QualityDimension.COMPLETENESS: 0.25,
            QualityDimension.CLARITY: 0.20,
            QualityDimension.ACTIONABILITY: 0.15,
            QualityDimension.EVIDENCE: 0.15,
        }

        self.completeness_validator = CompletenessValidator()

    def score(self, document: VulnKnowledgeDoc) -> QualityResult:
        """Score a document's quality.

        Args:
            document: Document to score

        Returns:
            Quality result with dimension breakdown
        """
        dimensions = {}
        strengths = []
        weaknesses = []
        suggestions = []

        # Score each dimension
        dimensions[QualityDimension.ACCURACY] = self._score_accuracy(document)
        dimensions[QualityDimension.COMPLETENESS] = self._score_completeness(document)
        dimensions[QualityDimension.CLARITY] = self._score_clarity(document)
        dimensions[QualityDimension.ACTIONABILITY] = self._score_actionability(document)
        dimensions[QualityDimension.EVIDENCE] = self._score_evidence(document)

        # Calculate overall score
        overall_score = self._calculate_overall(dimensions)

        # Determine grade
        grade = self._score_to_grade(overall_score)

        # Analyze strengths and weaknesses
        for dim, score in dimensions.items():
            if score.score >= 0.8:
                strengths.append(f"Strong {dim.value}: {score.notes[0] if score.notes else ''}")
            elif score.score < 0.5:
                weaknesses.append(f"Weak {dim.value}: {score.notes[0] if score.notes else ''}")

        # Generate suggestions based on lowest scores
        sorted_dims = sorted(dimensions.items(), key=lambda x: x[1].score)
        for dim, score in sorted_dims[:2]:
            if score.score < 0.7:
                suggestions.extend(self._get_suggestions(dim, score, document))

        return QualityResult(
            overall_score=overall_score,
            grade=grade,
            dimensions=dimensions,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions[:5],  # Limit suggestions
        )

    def _score_accuracy(self, document: VulnKnowledgeDoc) -> QualityScore:
        """Score accuracy based on source authority and confidence.

        Args:
            document: Document to score

        Returns:
            Accuracy score
        """
        notes = []

        # Source authority (0-1)
        authority = document.metadata.source_authority
        if authority >= 0.9:
            notes.append("High-authority sources")
        elif authority >= 0.7:
            notes.append("Good source quality")
        elif authority >= 0.5:
            notes.append("Moderate source authority")
        else:
            notes.append("Low source authority - verify information")

        # Confidence score (0-1)
        confidence = document.metadata.confidence_score

        # Source count factor
        source_count = len(document.metadata.sources)
        source_factor = min(source_count / 3, 1.0)  # Cap at 3 sources
        if source_count >= 3:
            notes.append(f"Corroborated by {source_count} sources")
        elif source_count == 1:
            notes.append("Single source - consider additional verification")

        # Calculate accuracy score
        score = (authority * 0.4 + confidence * 0.4 + source_factor * 0.2)

        return QualityScore(
            dimension=QualityDimension.ACCURACY,
            score=min(score, 1.0),
            notes=notes,
        )

    def _score_completeness(self, document: VulnKnowledgeDoc) -> QualityScore:
        """Score completeness using CompletenessValidator.

        Args:
            document: Document to score

        Returns:
            Completeness score
        """
        result = self.completeness_validator.validate(document)
        notes = []

        if result.success:
            notes.append(f"All sections complete ({result.overall_score*100:.0f}%)")
        else:
            if result.critical_missing:
                notes.append(f"Missing critical: {', '.join(result.critical_missing[:2])}")
            if result.required_missing:
                notes.append(f"Missing required: {', '.join(result.required_missing[:2])}")

        return QualityScore(
            dimension=QualityDimension.COMPLETENESS,
            score=result.overall_score,
            notes=notes,
        )

    def _score_clarity(self, document: VulnKnowledgeDoc) -> QualityScore:
        """Score clarity of content.

        Args:
            document: Document to score

        Returns:
            Clarity score
        """
        notes = []
        score_components = []

        # 1. One-liner quality (should be concise and clear)
        if document.one_liner:
            one_liner_len = len(document.one_liner)
            if 30 <= one_liner_len <= 150:
                score_components.append(1.0)
                notes.append("Clear, concise one-liner")
            elif one_liner_len < 30:
                score_components.append(0.5)
                notes.append("One-liner too brief")
            else:
                score_components.append(0.6)
                notes.append("One-liner could be more concise")
        else:
            score_components.append(0.0)
            notes.append("Missing one-liner summary")

        # 2. TLDR quality (should be 2-3 sentences)
        if document.tldr:
            sentences = len(re.findall(r'[.!?]+', document.tldr))
            if 2 <= sentences <= 4:
                score_components.append(1.0)
            elif sentences == 1:
                score_components.append(0.6)
                notes.append("TLDR could use more detail")
            else:
                score_components.append(0.7)
                notes.append("TLDR is lengthy")
        else:
            score_components.append(0.0)
            notes.append("Missing TLDR")

        # 3. Detection clarity (should have actionable items)
        d = document.detection
        if d.checklist and len(d.checklist) >= 2:
            score_components.append(1.0)
        elif d.checklist:
            score_components.append(0.7)
        elif d.indicators:
            score_components.append(0.5)
        else:
            score_components.append(0.0)
            notes.append("No clear detection checklist")

        # 4. Mitigation clarity (should have clear steps)
        m = document.mitigation
        if m.primary_fix and m.how_to_verify:
            score_components.append(1.0)
            notes.append("Clear fix with verification steps")
        elif m.primary_fix:
            score_components.append(0.7)
        else:
            score_components.append(0.0)
            notes.append("Unclear mitigation guidance")

        # 5. Code examples (should have explanations)
        ex = document.examples
        if ex.vulnerable_code and ex.vulnerable_code_explanation:
            score_components.append(1.0)
        elif ex.vulnerable_code:
            score_components.append(0.6)
            notes.append("Code examples need explanations")
        else:
            score_components.append(0.3)

        # Calculate average
        score = sum(score_components) / len(score_components) if score_components else 0.0

        return QualityScore(
            dimension=QualityDimension.CLARITY,
            score=score,
            notes=notes[:3],
        )

    def _score_actionability(self, document: VulnKnowledgeDoc) -> QualityScore:
        """Score how actionable the information is.

        Args:
            document: Document to score

        Returns:
            Actionability score
        """
        notes = []
        score_components = []

        # 1. Has detection checklist (actionable)
        if document.detection.checklist and len(document.detection.checklist) >= 3:
            score_components.append(1.0)
            notes.append("Clear detection checklist")
        elif document.detection.checklist:
            score_components.append(0.7)
        else:
            score_components.append(0.3)
            notes.append("No detection checklist")

        # 2. Has graph signals (for automated detection)
        if document.detection.graph_signals and len(document.detection.graph_signals) >= 2:
            score_components.append(1.0)
            notes.append("Graph signals for automated detection")
        elif document.detection.graph_signals:
            score_components.append(0.7)
        else:
            score_components.append(0.3)

        # 3. Has specific fix
        m = document.mitigation
        if m.primary_fix and len(m.primary_fix) > 30:
            score_components.append(1.0)
        elif m.primary_fix:
            score_components.append(0.7)
        else:
            score_components.append(0.0)
            notes.append("No specific fix provided")

        # 4. Has alternative fixes (options)
        if m.alternative_fixes and len(m.alternative_fixes) >= 2:
            score_components.append(1.0)
            notes.append("Multiple fix options")
        elif m.alternative_fixes:
            score_components.append(0.7)
        else:
            score_components.append(0.4)

        # 5. Has verification steps
        if m.how_to_verify and len(m.how_to_verify) >= 2:
            score_components.append(1.0)
            notes.append("Verification steps provided")
        elif m.how_to_verify:
            score_components.append(0.7)
        else:
            score_components.append(0.2)
            notes.append("No verification guidance")

        # 6. Pattern linkage actionability
        p = document.pattern_linkage
        if p.linkage_type == PatternLinkageType.EXACT_MATCH:
            score_components.append(1.0)
            notes.append("Direct VKG pattern detection")
        elif p.linkage_type == PatternLinkageType.PARTIAL_MATCH:
            score_components.append(0.8)
        elif p.linkage_type == PatternLinkageType.COMPOSITE:
            score_components.append(0.7)
        elif p.linkage_type == PatternLinkageType.REQUIRES_LLM:
            score_components.append(0.5)
            notes.append("Requires LLM analysis")
        else:  # THEORETICAL
            score_components.append(0.3)
            notes.append("No automated detection")

        score = sum(score_components) / len(score_components) if score_components else 0.0

        return QualityScore(
            dimension=QualityDimension.ACTIONABILITY,
            score=score,
            notes=notes[:3],
        )

    def _score_evidence(self, document: VulnKnowledgeDoc) -> QualityScore:
        """Score how well-supported by evidence the document is.

        Args:
            document: Document to score

        Returns:
            Evidence score
        """
        notes = []
        score_components = []

        # 1. Real-world exploits
        exploits = document.examples.real_exploits
        if exploits and len(exploits) >= 2:
            score_components.append(1.0)
            notes.append(f"{len(exploits)} real-world exploit references")
        elif exploits:
            score_components.append(0.7)
            notes.append("Has real-world example")
        else:
            score_components.append(0.0)
            notes.append("No real-world exploit references")

        # 2. Code examples
        ex = document.examples
        if ex.vulnerable_code and ex.fixed_code:
            score_components.append(1.0)
            notes.append("Complete code examples (vulnerable + fixed)")
        elif ex.vulnerable_code:
            score_components.append(0.6)
        else:
            score_components.append(0.0)
            notes.append("Missing code examples")

        # 3. Source URLs
        sources = document.metadata.sources
        if sources and len(sources) >= 2:
            score_components.append(1.0)
            notes.append(f"Backed by {len(sources)} sources")
        elif sources:
            score_components.append(0.6)
        else:
            score_components.append(0.2)
            notes.append("No source attribution")

        # 4. Attack steps (evidence of understanding)
        attack_steps = document.exploitation.attack_steps
        if attack_steps and len(attack_steps) >= 3:
            score_components.append(1.0)
            notes.append("Detailed attack methodology")
        elif attack_steps:
            score_components.append(0.7)
        else:
            score_components.append(0.3)

        # 5. Behavioral sequence (evidence of pattern understanding)
        d = document.detection
        if d.vulnerable_sequence and d.safe_sequence:
            score_components.append(1.0)
        elif d.vulnerable_sequence or d.safe_sequence:
            score_components.append(0.6)
        else:
            score_components.append(0.3)

        score = sum(score_components) / len(score_components) if score_components else 0.0

        return QualityScore(
            dimension=QualityDimension.EVIDENCE,
            score=score,
            notes=notes[:3],
        )

    def _calculate_overall(
        self,
        dimensions: Dict[QualityDimension, QualityScore],
    ) -> float:
        """Calculate weighted overall score.

        Args:
            dimensions: Dimension scores

        Returns:
            Overall score (0-1)
        """
        total_weight = sum(self.dimension_weights.values())
        weighted_sum = sum(
            self.dimension_weights[dim] * score.score
            for dim, score in dimensions.items()
        )
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade.

        Args:
            score: Score (0-1)

        Returns:
            Letter grade
        """
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"

    def _get_suggestions(
        self,
        dimension: QualityDimension,
        score: QualityScore,
        document: VulnKnowledgeDoc,
    ) -> List[str]:
        """Generate improvement suggestions for a dimension.

        Args:
            dimension: The dimension to improve
            score: Current score
            document: The document

        Returns:
            List of suggestions
        """
        suggestions = []

        if dimension == QualityDimension.ACCURACY:
            if document.metadata.source_authority < 0.7:
                suggestions.append("Add references from authoritative sources (OpenZeppelin, Trail of Bits)")
            if len(document.metadata.sources) < 2:
                suggestions.append("Corroborate with additional sources")

        elif dimension == QualityDimension.COMPLETENESS:
            if not document.detection.checklist:
                suggestions.append("Add detection checklist for auditors")
            if not document.examples.vulnerable_code:
                suggestions.append("Add vulnerable code example")
            if not document.examples.fixed_code:
                suggestions.append("Add fixed code example showing the solution")

        elif dimension == QualityDimension.CLARITY:
            if not document.one_liner:
                suggestions.append("Add concise one-liner summary")
            if document.examples.vulnerable_code and not document.examples.vulnerable_code_explanation:
                suggestions.append("Explain what makes the vulnerable code dangerous")
            if not document.mitigation.how_to_verify:
                suggestions.append("Add verification steps for the fix")

        elif dimension == QualityDimension.ACTIONABILITY:
            if not document.detection.graph_signals:
                suggestions.append("Add VKG graph signals for automated detection")
            if not document.mitigation.alternative_fixes:
                suggestions.append("Provide alternative fix approaches")
            if document.pattern_linkage.linkage_type == PatternLinkageType.THEORETICAL:
                suggestions.append("Consider creating a VKG pattern for automated detection")

        elif dimension == QualityDimension.EVIDENCE:
            if not document.examples.real_exploits:
                suggestions.append("Reference real-world exploits (DAO hack, Parity, etc.)")
            if not document.examples.vulnerable_code:
                suggestions.append("Add minimal vulnerable code example")
            if len(document.metadata.sources) < 2:
                suggestions.append("Add more source references")

        return suggestions


def score_quality(
    document: VulnKnowledgeDoc,
    dimension_weights: Optional[Dict[QualityDimension, float]] = None,
) -> QualityResult:
    """Convenience function for quality scoring.

    Args:
        document: Document to score
        dimension_weights: Optional custom weights

    Returns:
        Quality result
    """
    scorer = QualityScorer(dimension_weights=dimension_weights)
    return scorer.score(document)
