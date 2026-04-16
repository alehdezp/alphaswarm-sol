"""
Pattern and Clone Matching

Detect code clones and pattern matches across contracts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from enum import Enum
import logging

from .fingerprint import SemanticFingerprint, OperationSequence
from .similarity import SimilarityCalculator, SimilarityResult, SimilarityType

logger = logging.getLogger(__name__)


class CloneType(Enum):
    """Types of code clones."""
    TYPE_1 = "type_1"  # Exact copy (identical except whitespace/comments)
    TYPE_2 = "type_2"  # Renamed (identical structure, different names)
    TYPE_3 = "type_3"  # Modified (similar with insertions/deletions)
    TYPE_4 = "type_4"  # Semantic (same behavior, different implementation)


class MatchType(Enum):
    """Types of pattern matches."""
    EXACT = "exact"  # Pattern matches exactly
    PARTIAL = "partial"  # Pattern matches partially
    STRUCTURAL = "structural"  # Same structure as pattern
    BEHAVIORAL = "behavioral"  # Same behavior as pattern


@dataclass
class Clone:
    """A detected code clone."""
    clone_id: str
    clone_type: CloneType
    similarity: float

    # Source info
    source_function: str
    source_contract: str
    source_fingerprint_id: str

    # Target info
    target_function: str
    target_contract: str
    target_fingerprint_id: str

    # Details
    matching_operations: List[str] = field(default_factory=list)
    differing_operations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clone_id": self.clone_id,
            "type": self.clone_type.value,
            "similarity": round(self.similarity, 3),
            "source": f"{self.source_contract}.{self.source_function}",
            "target": f"{self.target_contract}.{self.target_function}",
            "matching_ops": len(self.matching_operations),
            "differing_ops": len(self.differing_operations),
        }


@dataclass
class MatchResult:
    """Result of pattern matching."""
    match_type: MatchType
    pattern_id: str
    target_function: str
    target_contract: str
    confidence: float

    # Match details
    matched_conditions: List[str] = field(default_factory=list)
    unmatched_conditions: List[str] = field(default_factory=list)

    # Vulnerability implications
    vulnerability_type: Optional[str] = None
    severity: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_type": self.match_type.value,
            "pattern": self.pattern_id,
            "target": f"{self.target_contract}.{self.target_function}",
            "confidence": round(self.confidence, 3),
            "vulnerability": self.vulnerability_type,
            "severity": self.severity,
        }


class CloneDetector:
    """Detect code clones across contracts."""

    def __init__(self):
        self.calculator = SimilarityCalculator()
        self._clone_counter = 0

    def _generate_clone_id(self) -> str:
        """Generate unique clone ID."""
        self._clone_counter += 1
        return f"CLN-{self._clone_counter:06d}"

    def detect_clones(
        self,
        fingerprints: List[SemanticFingerprint],
        min_similarity: float = 0.7,
    ) -> List[Clone]:
        """Detect clones among a set of fingerprints."""
        clones = []

        for i, fp1 in enumerate(fingerprints):
            for fp2 in fingerprints[i+1:]:
                # Skip same contract
                if fp1.contract_name == fp2.contract_name:
                    continue

                # Calculate similarity
                result = self.calculator.calculate(fp1, fp2)

                if result.score.score >= min_similarity:
                    clone_type = self._classify_clone(result)

                    clone = Clone(
                        clone_id=self._generate_clone_id(),
                        clone_type=clone_type,
                        similarity=result.score.score,
                        source_function=fp1.source_name,
                        source_contract=fp1.contract_name or "",
                        source_fingerprint_id=fp1.fingerprint_id,
                        target_function=fp2.source_name,
                        target_contract=fp2.contract_name or "",
                        target_fingerprint_id=fp2.fingerprint_id,
                        matching_operations=result.score.matching_operations,
                        differing_operations=result.score.differing_operations,
                    )
                    clones.append(clone)

        # Sort by similarity descending
        clones.sort(key=lambda c: c.similarity, reverse=True)

        return clones

    def _classify_clone(self, result: SimilarityResult) -> CloneType:
        """Classify the type of clone based on similarity."""
        score = result.score

        if score.similarity_type == SimilarityType.EXACT:
            # Check if it's truly exact (TYPE_1) or renamed (TYPE_2)
            if score.operation_score >= 0.99 and score.structure_score >= 0.99:
                return CloneType.TYPE_1
            return CloneType.TYPE_2

        elif score.similarity_type == SimilarityType.STRUCTURAL:
            return CloneType.TYPE_3

        elif score.similarity_type == SimilarityType.BEHAVIORAL:
            return CloneType.TYPE_4

        # Default based on score
        if score.score >= 0.95:
            return CloneType.TYPE_1
        elif score.score >= 0.85:
            return CloneType.TYPE_2
        elif score.score >= 0.70:
            return CloneType.TYPE_3
        else:
            return CloneType.TYPE_4

    def find_clones_of(
        self,
        target: SemanticFingerprint,
        candidates: List[SemanticFingerprint],
        min_similarity: float = 0.7,
    ) -> List[Clone]:
        """Find clones of a specific function."""
        clones = []

        for candidate in candidates:
            if candidate.fingerprint_id == target.fingerprint_id:
                continue

            result = self.calculator.calculate(target, candidate)

            if result.score.score >= min_similarity:
                clone = Clone(
                    clone_id=self._generate_clone_id(),
                    clone_type=self._classify_clone(result),
                    similarity=result.score.score,
                    source_function=target.source_name,
                    source_contract=target.contract_name or "",
                    source_fingerprint_id=target.fingerprint_id,
                    target_function=candidate.source_name,
                    target_contract=candidate.contract_name or "",
                    target_fingerprint_id=candidate.fingerprint_id,
                    matching_operations=result.score.matching_operations,
                    differing_operations=result.score.differing_operations,
                )
                clones.append(clone)

        clones.sort(key=lambda c: c.similarity, reverse=True)
        return clones


@dataclass
class VulnerabilityPattern:
    """A vulnerability pattern for matching."""
    pattern_id: str
    name: str
    vulnerability_type: str
    severity: str

    # Required operations
    required_operations: List[str] = field(default_factory=list)

    # Operation sequence (order matters)
    operation_sequence: Optional[List[str]] = None

    # Forbidden operations (pattern doesn't match if present)
    forbidden_operations: List[str] = field(default_factory=list)

    # Properties
    required_properties: Dict[str, Any] = field(default_factory=dict)
    forbidden_properties: Dict[str, Any] = field(default_factory=dict)


class PatternMatcher:
    """Match vulnerability patterns against fingerprints."""

    def __init__(self):
        self.patterns: Dict[str, VulnerabilityPattern] = {}
        self._load_default_patterns()

    def _load_default_patterns(self):
        """Load default vulnerability patterns."""
        default_patterns = [
            VulnerabilityPattern(
                pattern_id="REENTRANCY-001",
                name="Classic Reentrancy",
                vulnerability_type="reentrancy",
                severity="critical",
                required_operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                operation_sequence=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
                forbidden_operations=["USES_REENTRANCY_GUARD"],
            ),
            VulnerabilityPattern(
                pattern_id="ACCESS-001",
                name="Missing Access Control",
                vulnerability_type="access_control",
                severity="high",
                required_operations=["MODIFIES_CRITICAL_STATE"],
                forbidden_operations=["CHECKS_PERMISSION", "CHECKS_OWNER"],
                required_properties={"visibility": ["public", "external"]},
            ),
            VulnerabilityPattern(
                pattern_id="ORACLE-001",
                name="Stale Oracle Price",
                vulnerability_type="oracle_manipulation",
                severity="high",
                required_operations=["READS_ORACLE"],
                forbidden_operations=["CHECKS_STALENESS"],
            ),
            VulnerabilityPattern(
                pattern_id="VALUE-001",
                name="Unchecked Return Value",
                vulnerability_type="unchecked_return",
                severity="medium",
                required_operations=["CALLS_EXTERNAL"],
                forbidden_operations=["CHECKS_RETURN_VALUE"],
            ),
        ]

        for pattern in default_patterns:
            self.patterns[pattern.pattern_id] = pattern

    def add_pattern(self, pattern: VulnerabilityPattern):
        """Add a vulnerability pattern."""
        self.patterns[pattern.pattern_id] = pattern

    def match(
        self,
        fingerprint: SemanticFingerprint,
        pattern_id: Optional[str] = None,
    ) -> List[MatchResult]:
        """Match fingerprint against patterns."""
        matches = []

        patterns_to_check = (
            [self.patterns[pattern_id]] if pattern_id and pattern_id in self.patterns
            else self.patterns.values()
        )

        for pattern in patterns_to_check:
            result = self._match_pattern(fingerprint, pattern)
            if result:
                matches.append(result)

        return matches

    def _match_pattern(
        self,
        fingerprint: SemanticFingerprint,
        pattern: VulnerabilityPattern,
    ) -> Optional[MatchResult]:
        """Match fingerprint against a single pattern."""
        ops = set(fingerprint.operations)
        matched_conditions = []
        unmatched_conditions = []

        # Check required operations
        for req_op in pattern.required_operations:
            if req_op in ops:
                matched_conditions.append(f"has_{req_op}")
            else:
                unmatched_conditions.append(f"missing_{req_op}")

        # Check forbidden operations
        for forb_op in pattern.forbidden_operations:
            if forb_op in ops:
                # Forbidden operation present = no match
                return None
            matched_conditions.append(f"no_{forb_op}")

        # Check operation sequence if specified
        if pattern.operation_sequence:
            if self._check_sequence(fingerprint.operations, pattern.operation_sequence):
                matched_conditions.append("sequence_match")
            else:
                unmatched_conditions.append("sequence_mismatch")

        # Check properties
        props = fingerprint.features or {}
        for prop, expected in pattern.required_properties.items():
            actual = props.get(prop)
            if isinstance(expected, list):
                if actual in expected:
                    matched_conditions.append(f"{prop}={actual}")
                else:
                    unmatched_conditions.append(f"{prop}_mismatch")
            else:
                if actual == expected:
                    matched_conditions.append(f"{prop}={actual}")
                else:
                    unmatched_conditions.append(f"{prop}_mismatch")

        for prop, forbidden_value in pattern.forbidden_properties.items():
            actual = props.get(prop)
            if actual == forbidden_value:
                return None
            matched_conditions.append(f"{prop}!={forbidden_value}")

        # Determine match type and confidence
        total_conditions = len(matched_conditions) + len(unmatched_conditions)
        if total_conditions == 0:
            return None

        match_ratio = len(matched_conditions) / total_conditions

        if match_ratio < 0.5:
            return None

        if match_ratio >= 0.95:
            match_type = MatchType.EXACT
        elif match_ratio >= 0.8:
            match_type = MatchType.STRUCTURAL
        elif match_ratio >= 0.6:
            match_type = MatchType.BEHAVIORAL
        else:
            match_type = MatchType.PARTIAL

        return MatchResult(
            match_type=match_type,
            pattern_id=pattern.pattern_id,
            target_function=fingerprint.source_name,
            target_contract=fingerprint.contract_name or "",
            confidence=match_ratio,
            matched_conditions=matched_conditions,
            unmatched_conditions=unmatched_conditions,
            vulnerability_type=pattern.vulnerability_type,
            severity=pattern.severity,
        )

    def _check_sequence(self, ops: List[str], required_sequence: List[str]) -> bool:
        """Check if required sequence appears in ops (in order)."""
        seq_idx = 0

        for op in ops:
            if seq_idx < len(required_sequence) and op == required_sequence[seq_idx]:
                seq_idx += 1

        return seq_idx == len(required_sequence)

    def batch_match(
        self,
        fingerprints: List[SemanticFingerprint],
    ) -> Dict[str, List[MatchResult]]:
        """Match all fingerprints against all patterns."""
        results: Dict[str, List[MatchResult]] = {}

        for fp in fingerprints:
            matches = self.match(fp)
            if matches:
                key = f"{fp.contract_name}.{fp.source_name}"
                results[key] = matches

        return results
