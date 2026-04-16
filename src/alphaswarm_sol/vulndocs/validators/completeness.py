"""Completeness Validator.

Task 18.2: Validates that VulnKnowledgeDoc has all required sections
filled with meaningful content.

A complete document should have:
- Identification: name, category, subcategory
- Summary: one_liner, tldr
- Detection: graph signals, indicators, checklist
- Exploitation: attack vector, steps, impact
- Mitigation: primary fix, verification steps
- Examples: vulnerable code, fixed code
- Pattern linkage: type, patterns or manual hints
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from alphaswarm_sol.vulndocs.knowledge_doc import VulnKnowledgeDoc, PatternLinkageType


class MissingSectionType(Enum):
    """Type of missing section."""

    # Critical - document is unusable without these
    IDENTIFICATION = "identification"
    SUMMARY = "summary"

    # Required - document is incomplete without these
    DETECTION = "detection"
    EXPLOITATION = "exploitation"
    MITIGATION = "mitigation"

    # Important - document quality suffers without these
    EXAMPLES = "examples"
    PATTERN_LINKAGE = "pattern_linkage"

    # Optional - nice to have
    METADATA = "metadata"


@dataclass
class SectionCompleteness:
    """Completeness status of a single section."""

    section: MissingSectionType
    is_complete: bool
    completion_pct: float  # 0-1
    missing_fields: List[str] = field(default_factory=list)
    quality_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "section": self.section.value,
            "is_complete": self.is_complete,
            "completion_pct": self.completion_pct,
            "missing_fields": self.missing_fields,
            "quality_notes": self.quality_notes,
        }


@dataclass
class CompletenessResult:
    """Result of completeness validation."""

    success: bool  # True if meets minimum completeness
    overall_score: float  # 0-1 overall completeness
    sections: Dict[str, SectionCompleteness] = field(default_factory=dict)
    critical_missing: List[str] = field(default_factory=list)
    required_missing: List[str] = field(default_factory=list)
    important_missing: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "overall_score": self.overall_score,
            "sections": {k: v.to_dict() for k, v in self.sections.items()},
            "critical_missing": self.critical_missing,
            "required_missing": self.required_missing,
            "important_missing": self.important_missing,
        }

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Completeness Validation: {'PASSED' if self.success else 'FAILED'}",
            f"  Overall Score: {self.overall_score*100:.0f}%",
            "",
        ]

        # Section breakdown
        lines.append("  Sections:")
        for name, section in self.sections.items():
            status = "OK" if section.is_complete else "INCOMPLETE"
            lines.append(f"    {name}: {status} ({section.completion_pct*100:.0f}%)")
            if section.missing_fields:
                for field in section.missing_fields[:3]:
                    lines.append(f"      - Missing: {field}")

        # Summary of issues
        if self.critical_missing:
            lines.append("")
            lines.append(f"  Critical Missing: {', '.join(self.critical_missing)}")

        if self.required_missing:
            lines.append(f"  Required Missing: {', '.join(self.required_missing)}")

        return "\n".join(lines)


class CompletenessValidator:
    """Validates completeness of VulnKnowledgeDoc documents.

    Checks that all required sections have meaningful content.

    Example:
        >>> validator = CompletenessValidator()
        >>> result = validator.validate(document)
        >>> if result.success:
        ...     print(f"Document is {result.overall_score*100:.0f}% complete")
    """

    def __init__(
        self,
        min_completeness: float = 0.7,
        require_examples: bool = True,
        require_pattern_linkage: bool = True,
    ):
        """Initialize the validator.

        Args:
            min_completeness: Minimum overall completeness to pass (0-1)
            require_examples: Whether to require code examples
            require_pattern_linkage: Whether to require pattern linkage
        """
        self.min_completeness = min_completeness
        self.require_examples = require_examples
        self.require_pattern_linkage = require_pattern_linkage

        # Section weights for overall score
        self.section_weights = {
            MissingSectionType.IDENTIFICATION: 0.15,
            MissingSectionType.SUMMARY: 0.15,
            MissingSectionType.DETECTION: 0.20,
            MissingSectionType.EXPLOITATION: 0.15,
            MissingSectionType.MITIGATION: 0.15,
            MissingSectionType.EXAMPLES: 0.10,
            MissingSectionType.PATTERN_LINKAGE: 0.10,
        }

    def validate(self, document: VulnKnowledgeDoc) -> CompletenessResult:
        """Validate document completeness.

        Args:
            document: Document to validate

        Returns:
            Completeness result with section breakdown
        """
        sections = {}
        critical_missing = []
        required_missing = []
        important_missing = []

        # Check identification
        id_result = self._check_identification(document)
        sections["identification"] = id_result
        if not id_result.is_complete:
            critical_missing.extend(id_result.missing_fields)

        # Check summary
        summary_result = self._check_summary(document)
        sections["summary"] = summary_result
        if not summary_result.is_complete:
            critical_missing.extend(summary_result.missing_fields)

        # Check detection
        detection_result = self._check_detection(document)
        sections["detection"] = detection_result
        if not detection_result.is_complete:
            required_missing.extend(detection_result.missing_fields)

        # Check exploitation
        exploitation_result = self._check_exploitation(document)
        sections["exploitation"] = exploitation_result
        if not exploitation_result.is_complete:
            required_missing.extend(exploitation_result.missing_fields)

        # Check mitigation
        mitigation_result = self._check_mitigation(document)
        sections["mitigation"] = mitigation_result
        if not mitigation_result.is_complete:
            required_missing.extend(mitigation_result.missing_fields)

        # Check examples
        examples_result = self._check_examples(document)
        sections["examples"] = examples_result
        if not examples_result.is_complete and self.require_examples:
            important_missing.extend(examples_result.missing_fields)

        # Check pattern linkage
        linkage_result = self._check_pattern_linkage(document)
        sections["pattern_linkage"] = linkage_result
        if not linkage_result.is_complete and self.require_pattern_linkage:
            important_missing.extend(linkage_result.missing_fields)

        # Calculate overall score
        overall_score = self._calculate_overall_score(sections)

        # Determine success
        success = (
            overall_score >= self.min_completeness
            and len(critical_missing) == 0
        )

        return CompletenessResult(
            success=success,
            overall_score=overall_score,
            sections=sections,
            critical_missing=critical_missing,
            required_missing=required_missing,
            important_missing=important_missing,
        )

    def _check_identification(self, document: VulnKnowledgeDoc) -> SectionCompleteness:
        """Check identification section completeness."""
        missing = []
        notes = []

        # Required fields
        if not document.id:
            missing.append("id")
        if not document.name:
            missing.append("name")
        if not document.category:
            missing.append("category")
        if not document.subcategory:
            missing.append("subcategory")

        # Quality checks
        if document.name and len(document.name) < 10:
            notes.append("name is very short")
        if document.id and "/" not in document.id:
            notes.append("id should use hierarchical format (category/subcategory)")

        total_fields = 4
        complete_fields = total_fields - len(missing)

        return SectionCompleteness(
            section=MissingSectionType.IDENTIFICATION,
            is_complete=len(missing) == 0,
            completion_pct=complete_fields / total_fields,
            missing_fields=missing,
            quality_notes=notes,
        )

    def _check_summary(self, document: VulnKnowledgeDoc) -> SectionCompleteness:
        """Check summary section completeness."""
        missing = []
        notes = []

        # Required fields
        if not document.one_liner:
            missing.append("one_liner")
        if not document.tldr:
            missing.append("tldr")

        # Quality checks
        if document.one_liner and len(document.one_liner) < 20:
            notes.append("one_liner should be more descriptive")
        if document.tldr and len(document.tldr) < 50:
            notes.append("tldr should provide more context")
        if document.one_liner and len(document.one_liner) > 200:
            notes.append("one_liner should be concise (under 200 chars)")

        total_fields = 2
        complete_fields = total_fields - len(missing)

        return SectionCompleteness(
            section=MissingSectionType.SUMMARY,
            is_complete=len(missing) == 0,
            completion_pct=complete_fields / total_fields,
            missing_fields=missing,
            quality_notes=notes,
        )

    def _check_detection(self, document: VulnKnowledgeDoc) -> SectionCompleteness:
        """Check detection section completeness."""
        missing = []
        notes = []
        d = document.detection

        # Required fields
        if not d.graph_signals:
            missing.append("detection.graph_signals")
        if not d.indicators:
            missing.append("detection.indicators")

        # Important fields
        if not d.checklist:
            missing.append("detection.checklist")

        # Quality checks
        if d.graph_signals and len(d.graph_signals) < 2:
            notes.append("should have multiple graph signals")
        if not d.vulnerable_sequence and not d.safe_sequence:
            notes.append("should include vulnerable/safe sequences")

        total_fields = 5  # signals, sequences (2), indicators, checklist
        complete_fields = sum([
            1 if d.graph_signals else 0,
            1 if d.vulnerable_sequence else 0,
            1 if d.safe_sequence else 0,
            1 if d.indicators else 0,
            1 if d.checklist else 0,
        ])

        return SectionCompleteness(
            section=MissingSectionType.DETECTION,
            is_complete=len(missing) <= 1,  # Allow 1 missing
            completion_pct=complete_fields / total_fields,
            missing_fields=missing,
            quality_notes=notes,
        )

    def _check_exploitation(self, document: VulnKnowledgeDoc) -> SectionCompleteness:
        """Check exploitation section completeness."""
        missing = []
        notes = []
        e = document.exploitation

        # Required fields
        if not e.attack_vector:
            missing.append("exploitation.attack_vector")
        if not e.attack_steps:
            missing.append("exploitation.attack_steps")

        # Important fields
        if not e.potential_impact:
            missing.append("exploitation.potential_impact")

        # Quality checks
        if e.attack_steps and len(e.attack_steps) < 2:
            notes.append("should have multiple attack steps")
        if e.attack_vector and len(e.attack_vector) < 30:
            notes.append("attack_vector should be more detailed")

        total_fields = 5  # vector, prerequisites, steps, impact, risk
        complete_fields = sum([
            1 if e.attack_vector else 0,
            1 if e.prerequisites else 0,
            1 if e.attack_steps else 0,
            1 if e.potential_impact else 0,
            1 if e.monetary_risk else 0,
        ])

        return SectionCompleteness(
            section=MissingSectionType.EXPLOITATION,
            is_complete=len(missing) <= 1,  # Allow 1 missing
            completion_pct=complete_fields / total_fields,
            missing_fields=missing,
            quality_notes=notes,
        )

    def _check_mitigation(self, document: VulnKnowledgeDoc) -> SectionCompleteness:
        """Check mitigation section completeness."""
        missing = []
        notes = []
        m = document.mitigation

        # Required fields
        if not m.primary_fix:
            missing.append("mitigation.primary_fix")

        # Important fields
        if not m.how_to_verify:
            missing.append("mitigation.how_to_verify")

        # Quality checks
        if m.primary_fix and len(m.primary_fix) < 20:
            notes.append("primary_fix should be more detailed")
        if not m.safe_pattern:
            notes.append("should name the safe pattern")

        total_fields = 4  # primary_fix, alternative_fixes, safe_pattern, how_to_verify
        complete_fields = sum([
            1 if m.primary_fix else 0,
            1 if m.alternative_fixes else 0,
            1 if m.safe_pattern else 0,
            1 if m.how_to_verify else 0,
        ])

        return SectionCompleteness(
            section=MissingSectionType.MITIGATION,
            is_complete=len(missing) == 0 or (len(missing) == 1 and m.primary_fix),
            completion_pct=complete_fields / total_fields,
            missing_fields=missing,
            quality_notes=notes,
        )

    def _check_examples(self, document: VulnKnowledgeDoc) -> SectionCompleteness:
        """Check examples section completeness."""
        missing = []
        notes = []
        ex = document.examples

        # Important fields
        if not ex.vulnerable_code:
            missing.append("examples.vulnerable_code")
        if not ex.fixed_code:
            missing.append("examples.fixed_code")

        # Nice to have
        if not ex.real_exploits:
            missing.append("examples.real_exploits")

        # Quality checks
        if ex.vulnerable_code and not ex.vulnerable_code_explanation:
            notes.append("should explain what's wrong with vulnerable code")
        if ex.fixed_code and not ex.fixed_code_explanation:
            notes.append("should explain what the fix does")
        if ex.vulnerable_code and len(ex.vulnerable_code) < 20:
            notes.append("code example is very short")

        total_fields = 5  # vuln_code, vuln_explanation, fixed_code, fixed_explanation, exploits
        complete_fields = sum([
            1 if ex.vulnerable_code else 0,
            1 if ex.vulnerable_code_explanation else 0,
            1 if ex.fixed_code else 0,
            1 if ex.fixed_code_explanation else 0,
            1 if ex.real_exploits else 0,
        ])

        return SectionCompleteness(
            section=MissingSectionType.EXAMPLES,
            is_complete=ex.vulnerable_code and ex.fixed_code,
            completion_pct=complete_fields / total_fields,
            missing_fields=missing,
            quality_notes=notes,
        )

    def _check_pattern_linkage(self, document: VulnKnowledgeDoc) -> SectionCompleteness:
        """Check pattern linkage section completeness."""
        missing = []
        notes = []
        p = document.pattern_linkage

        # Check based on linkage type
        if p.linkage_type in [PatternLinkageType.EXACT_MATCH, PatternLinkageType.PARTIAL_MATCH]:
            if not p.pattern_ids:
                missing.append("pattern_linkage.pattern_ids")
            if p.coverage_pct == 0:
                missing.append("pattern_linkage.coverage_pct")
        elif p.linkage_type == PatternLinkageType.THEORETICAL:
            if not p.why_no_pattern:
                missing.append("pattern_linkage.why_no_pattern")
            if not p.manual_hints:
                missing.append("pattern_linkage.manual_hints")
        elif p.linkage_type == PatternLinkageType.REQUIRES_LLM:
            if not p.llm_context_needed:
                missing.append("pattern_linkage.llm_context_needed")
        elif p.linkage_type == PatternLinkageType.COMPOSITE:
            if not p.composite_patterns:
                missing.append("pattern_linkage.composite_patterns")
            if not p.combination_logic:
                missing.append("pattern_linkage.combination_logic")

        # Quality checks
        if p.linkage_type == PatternLinkageType.THEORETICAL and not p.manual_hints:
            notes.append("theoretical vulnerabilities need manual hints")

        # Calculate completeness based on type
        if p.linkage_type in [PatternLinkageType.EXACT_MATCH, PatternLinkageType.PARTIAL_MATCH]:
            total_fields = 2  # pattern_ids, coverage_pct
            complete_fields = sum([
                1 if p.pattern_ids else 0,
                1 if p.coverage_pct > 0 else 0,
            ])
        elif p.linkage_type == PatternLinkageType.THEORETICAL:
            total_fields = 2  # why_no_pattern, manual_hints
            complete_fields = sum([
                1 if p.why_no_pattern else 0,
                1 if p.manual_hints else 0,
            ])
        else:
            total_fields = 2
            complete_fields = 1 if not missing else 0

        return SectionCompleteness(
            section=MissingSectionType.PATTERN_LINKAGE,
            is_complete=len(missing) == 0,
            completion_pct=complete_fields / total_fields if total_fields > 0 else 0,
            missing_fields=missing,
            quality_notes=notes,
        )

    def _calculate_overall_score(
        self,
        sections: Dict[str, SectionCompleteness],
    ) -> float:
        """Calculate weighted overall completeness score.

        Args:
            sections: Section completeness results

        Returns:
            Overall score (0-1)
        """
        total_weight = 0.0
        weighted_score = 0.0

        type_map = {
            "identification": MissingSectionType.IDENTIFICATION,
            "summary": MissingSectionType.SUMMARY,
            "detection": MissingSectionType.DETECTION,
            "exploitation": MissingSectionType.EXPLOITATION,
            "mitigation": MissingSectionType.MITIGATION,
            "examples": MissingSectionType.EXAMPLES,
            "pattern_linkage": MissingSectionType.PATTERN_LINKAGE,
        }

        for name, section in sections.items():
            section_type = type_map.get(name)
            if section_type:
                weight = self.section_weights.get(section_type, 0.1)
                total_weight += weight
                weighted_score += weight * section.completion_pct

        return weighted_score / total_weight if total_weight > 0 else 0.0


def validate_completeness(
    document: VulnKnowledgeDoc,
    min_completeness: float = 0.7,
) -> CompletenessResult:
    """Convenience function for completeness validation.

    Args:
        document: Document to validate
        min_completeness: Minimum completeness to pass

    Returns:
        Completeness result
    """
    validator = CompletenessValidator(min_completeness=min_completeness)
    return validator.validate(document)
