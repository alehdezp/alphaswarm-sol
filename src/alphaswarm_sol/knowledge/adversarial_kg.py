"""
Adversarial Knowledge Graph - Core Implementation

Captures HOW CODE GETS BROKEN through historical exploits, attack patterns,
and vulnerability taxonomies. Enables detecting code similar to known exploits.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any, Tuple
from enum import Enum
import re


class AttackCategory(Enum):
    """High-level vulnerability categories."""
    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access_control"
    ORACLE_MANIPULATION = "oracle_manipulation"
    FLASH_LOAN = "flash_loan"
    MEV = "mev"
    GOVERNANCE = "governance"
    ECONOMIC = "economic"
    UPGRADE = "upgrade"
    CRYPTOGRAPHIC = "cryptographic"
    DOS = "dos"
    TOKEN = "token"


class Severity(Enum):
    """Vulnerability severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class AttackPattern:
    """
    Generalized attack pattern extracted from exploits.

    KEY DESIGN: Maps directly to VKG's semantic operations and
    behavioral signatures for precise matching.
    """
    id: str
    name: str
    category: AttackCategory
    severity: Severity
    description: str

    # === MATCHING CRITERIA ===

    # Required semantic operations (from VKG operations.py)
    # Pattern matches if function has ALL of these
    required_operations: List[str]

    # Behavioral signature pattern (regex)
    # Matches against VKG behavioral_signature property
    # e.g., ".*X:out.*W:bal.*" matches external call before balance write
    operation_sequence: Optional[str] = None

    # Additional operations that INCREASE confidence
    supporting_operations: List[str] = field(default_factory=list)

    # === PRECONDITIONS ===

    # Property checks that must be true for vulnerability
    # Maps to VKG node properties
    preconditions: List[str] = field(default_factory=list)

    # Property checks that PREVENT this vulnerability
    # If ANY of these are true, pattern doesn't match
    false_positive_indicators: List[str] = field(default_factory=list)

    # === CONTEXT ===

    # What security properties this violates
    violated_properties: List[str] = field(default_factory=list)

    # Related CWE identifiers
    cwes: List[str] = field(default_factory=list)

    # Detection hints for auditors
    detection_hints: List[str] = field(default_factory=list)

    # Remediation guidance
    remediation: str = ""

    # === METADATA ===

    # Historical exploits that match this pattern
    known_exploits: List[str] = field(default_factory=list)

    # Related patterns (for pattern composition)
    related_patterns: List[str] = field(default_factory=list)

    # Minimum VKG properties needed to evaluate this pattern
    required_properties: Set[str] = field(default_factory=set)


@dataclass
class ExploitRecord:
    """
    A historical exploit with extracted patterns.

    Links real-world incidents to abstract patterns.
    """
    id: str
    name: str  # "The DAO", "Cream Finance", "Wormhole"
    date: str  # ISO format
    loss_usd: int
    chain: str  # "ethereum", "bsc", "solana"

    # Classification
    category: AttackCategory
    cwes: List[str]

    # The extracted attack pattern
    pattern_ids: List[str]  # Links to AttackPattern.id

    # Attack details
    attack_summary: str
    attack_steps: List[str]

    # Source links
    postmortem_url: Optional[str] = None
    vulnerable_code_url: Optional[str] = None
    fixed_code_url: Optional[str] = None
    tx_hash: Optional[str] = None


@dataclass
class PatternMatch:
    """Result of matching a pattern against a function."""
    pattern: AttackPattern
    confidence: float  # 0.0 to 1.0
    matched_operations: List[str]  # Which ops matched
    matched_signature: bool  # Did sequence match
    matched_preconditions: List[str]  # Which preconditions matched
    blocked_by: List[str]  # Which FP indicators blocked (empty if vulnerable)
    evidence: List[str]  # Human-readable match explanations


class AdversarialKnowledgeGraph:
    """
    Knowledge graph of HOW THINGS GET BROKEN.

    Enables:
    1. "Have we seen similar vulnerable patterns before?"
    2. "What attack techniques apply to this code structure?"
    3. "What would an attacker try here?"
    """

    def __init__(self):
        """Initialize empty adversarial knowledge graph."""
        self.patterns: Dict[str, AttackPattern] = {}
        self.exploits: Dict[str, ExploitRecord] = {}
        self._category_index: Dict[AttackCategory, List[str]] = {}
        self._cwe_index: Dict[str, List[str]] = {}
        self._ops_index: Dict[str, Set[str]] = {}  # op -> pattern_ids

    def add_pattern(self, pattern: AttackPattern) -> None:
        """
        Add pattern and index it for fast lookup.

        Args:
            pattern: AttackPattern to add
        """
        self.patterns[pattern.id] = pattern

        # Index by category
        if pattern.category not in self._category_index:
            self._category_index[pattern.category] = []
        self._category_index[pattern.category].append(pattern.id)

        # Index by CWE
        for cwe in pattern.cwes:
            if cwe not in self._cwe_index:
                self._cwe_index[cwe] = []
            self._cwe_index[cwe].append(pattern.id)

        # Index by required operations for fast filtering
        for op in pattern.required_operations:
            if op not in self._ops_index:
                self._ops_index[op] = set()
            self._ops_index[op].add(pattern.id)

    def add_exploit(self, exploit: ExploitRecord) -> None:
        """
        Add historical exploit record.

        Args:
            exploit: ExploitRecord to add
        """
        self.exploits[exploit.id] = exploit

    def find_similar_patterns(
        self,
        fn_node: Dict[str, Any],
        min_confidence: float = 0.5,
        categories: Optional[List[AttackCategory]] = None,
    ) -> List[PatternMatch]:
        """
        Find attack patterns similar to this function.

        Matching algorithm:
        1. Filter by category if specified
        2. Pre-filter by required operations (fast rejection)
        3. Score each candidate pattern
        4. Return matches above threshold

        Args:
            fn_node: Function node from Code KG
            min_confidence: Minimum confidence threshold
            categories: Optional category filter

        Returns:
            List of PatternMatch sorted by confidence (descending)
        """
        # Get function operations
        props = fn_node.get("properties", {})
        fn_ops = set(props.get("operations", []))

        # Pre-filter candidate patterns
        candidate_ids: Set[str] = set()

        if categories:
            # Filter by category
            for cat in categories:
                candidate_ids.update(self._category_index.get(cat, []))
        else:
            # All patterns
            candidate_ids = set(self.patterns.keys())

        # Further filter by operations (fast rejection)
        if fn_ops:
            # Find patterns that require ops we have
            ops_candidates: Set[str] = set()
            for op in fn_ops:
                ops_candidates.update(self._ops_index.get(op, set()))

            # Intersect with category candidates
            candidate_ids = candidate_ids & ops_candidates

        # Score each candidate
        matches: List[PatternMatch] = []
        for pattern_id in candidate_ids:
            pattern = self.patterns[pattern_id]
            match = self._score_pattern_match(fn_node, pattern)

            if match.confidence >= min_confidence:
                matches.append(match)

        # Sort by confidence descending
        matches.sort(key=lambda m: m.confidence, reverse=True)

        return matches

    def _score_pattern_match(
        self,
        fn_node: Dict[str, Any],
        pattern: AttackPattern
    ) -> PatternMatch:
        """
        Score how well a function matches an attack pattern.

        Scoring components:
        1. Required operations overlap (40% weight)
        2. Behavioral signature match (30% weight)
        3. Precondition satisfaction (20% weight)
        4. Supporting operations (10% bonus)
        5. False positive indicators (subtract confidence)

        Args:
            fn_node: Function node from Code KG
            pattern: AttackPattern to match against

        Returns:
            PatternMatch with confidence score
        """
        props = fn_node.get("properties", {})
        fn_ops = set(props.get("operations", []))
        behavioral_sig = props.get("behavioral_signature", "")

        score = 0.0
        evidence: List[str] = []
        matched_ops: List[str] = []
        matched_preconds: List[str] = []
        blocked_by: List[str] = []
        matched_signature = False

        # 1. Required operations (40% weight)
        if pattern.required_operations:
            pattern_ops = set(pattern.required_operations)
            overlap = fn_ops & pattern_ops
            required_overlap = len(overlap) / len(pattern_ops)
            score += 0.4 * required_overlap

            matched_ops = list(overlap)
            if overlap:
                evidence.append(
                    f"Matched {len(overlap)}/{len(pattern_ops)} required operations: "
                    f"{', '.join(overlap)}"
                )
        else:
            # No required ops = automatic partial score
            score += 0.2

        # 2. Behavioral signature (30% weight)
        if pattern.operation_sequence and behavioral_sig:
            try:
                if re.search(pattern.operation_sequence, behavioral_sig):
                    score += 0.3
                    matched_signature = True
                    evidence.append(
                        f"Behavioral signature '{behavioral_sig}' matches pattern "
                        f"'{pattern.operation_sequence}'"
                    )
            except re.error:
                # Invalid regex, skip
                pass

        # 3. Preconditions (20% weight)
        if pattern.preconditions:
            satisfied = []
            for precond in pattern.preconditions:
                if props.get(precond, False):
                    satisfied.append(precond)

            precond_score = len(satisfied) / len(pattern.preconditions)
            score += 0.2 * precond_score

            matched_preconds = satisfied
            if satisfied:
                evidence.append(
                    f"Satisfied {len(satisfied)}/{len(pattern.preconditions)} preconditions: "
                    f"{', '.join(satisfied)}"
                )
        else:
            # No preconditions = automatic score
            score += 0.1

        # 4. Supporting operations (10% bonus)
        if pattern.supporting_operations:
            supporting_ops = set(pattern.supporting_operations)
            support_overlap = fn_ops & supporting_ops
            if support_overlap:
                bonus = 0.1 * (len(support_overlap) / len(supporting_ops))
                score += bonus
                evidence.append(
                    f"Has {len(support_overlap)} supporting operations: "
                    f"{', '.join(support_overlap)}"
                )

        # 5. False positive indicators (penalty)
        if pattern.false_positive_indicators:
            for fp in pattern.false_positive_indicators:
                if props.get(fp, False):
                    score -= 0.2
                    blocked_by.append(fp)
                    evidence.append(
                        f"False positive indicator detected: {fp} (reduced confidence)"
                    )

        # Clamp to [0.0, 1.0]
        confidence = max(0.0, min(1.0, score))

        return PatternMatch(
            pattern=pattern,
            confidence=confidence,
            matched_operations=matched_ops,
            matched_signature=matched_signature,
            matched_preconditions=matched_preconds,
            blocked_by=blocked_by,
            evidence=evidence,
        )

    def get_patterns_by_category(self, category: AttackCategory) -> List[AttackPattern]:
        """
        Get all patterns in a category.

        Args:
            category: AttackCategory to filter by

        Returns:
            List of patterns in that category
        """
        pattern_ids = self._category_index.get(category, [])
        return [self.patterns[pid] for pid in pattern_ids]

    def get_patterns_by_cwe(self, cwe: str) -> List[AttackPattern]:
        """
        Get patterns matching a CWE identifier.

        Args:
            cwe: CWE identifier (e.g., "CWE-841")

        Returns:
            List of patterns with that CWE
        """
        pattern_ids = self._cwe_index.get(cwe, [])
        return [self.patterns[pid] for pid in pattern_ids]

    def get_related_exploits(self, pattern_id: str) -> List[ExploitRecord]:
        """
        Get historical exploits matching a pattern.

        Args:
            pattern_id: Pattern ID to find exploits for

        Returns:
            List of exploits with that pattern
        """
        return [
            exploit for exploit in self.exploits.values()
            if pattern_id in exploit.pattern_ids
        ]

    def list_patterns(self, category: Optional[AttackCategory] = None) -> List[AttackPattern]:
        """
        List all patterns, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of patterns
        """
        if category:
            return self.get_patterns_by_category(category)
        return list(self.patterns.values())

    def list_exploits(self, category: Optional[AttackCategory] = None) -> List[ExploitRecord]:
        """
        List all exploits, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of exploits
        """
        if category:
            return [e for e in self.exploits.values() if e.category == category]
        return list(self.exploits.values())

    def stats(self) -> Dict[str, int]:
        """
        Get statistics about the adversarial knowledge graph.

        Returns:
            Dict with counts
        """
        return {
            "total_patterns": len(self.patterns),
            "total_exploits": len(self.exploits),
            "patterns_by_category": {
                cat.value: len(self._category_index.get(cat, []))
                for cat in AttackCategory
            },
            "unique_cwes": len(self._cwe_index),
        }
