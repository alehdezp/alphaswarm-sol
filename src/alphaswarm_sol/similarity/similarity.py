"""
Similarity Calculation

Calculate semantic similarity between code fragments,
functions, or contracts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import logging

from .fingerprint import SemanticFingerprint, FingerprintType

logger = logging.getLogger(__name__)


class SimilarityType(Enum):
    """Types of similarity measures."""
    EXACT = "exact"  # Identical operations
    STRUCTURAL = "structural"  # Same structure, different names
    BEHAVIORAL = "behavioral"  # Same behavior, different implementation
    PARTIAL = "partial"  # Partially similar
    NONE = "none"  # No meaningful similarity


@dataclass
class SimilarityScore:
    """Similarity score between two items."""
    score: float  # 0.0 to 1.0
    similarity_type: SimilarityType
    confidence: float = 1.0  # How confident in this score

    # Component scores
    operation_score: float = 0.0
    structure_score: float = 0.0
    behavior_score: float = 0.0

    # Details
    matching_operations: List[str] = field(default_factory=list)
    differing_operations: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "type": self.similarity_type.value,
            "confidence": round(self.confidence, 3),
            "operation_score": round(self.operation_score, 3),
            "structure_score": round(self.structure_score, 3),
            "behavior_score": round(self.behavior_score, 3),
            "matching_ops": len(self.matching_operations),
            "differing_ops": len(self.differing_operations),
        }

    def is_significant(self, threshold: float = 0.5) -> bool:
        """Check if similarity is significant."""
        return self.score >= threshold


@dataclass
class SimilarityResult:
    """Result of similarity comparison."""
    source_id: str
    target_id: str
    source_name: str
    target_name: str

    score: SimilarityScore

    # Additional context
    source_contract: Optional[str] = None
    target_contract: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_name,
            "target": self.target_name,
            "source_contract": self.source_contract,
            "target_contract": self.target_contract,
            "score": self.score.to_dict(),
        }


@dataclass
class SimilarityConfig:
    """Configuration for similarity calculation."""
    # Weights for different similarity components
    operation_weight: float = 0.5
    structure_weight: float = 0.3
    behavior_weight: float = 0.2

    # Thresholds
    exact_threshold: float = 0.95  # Above this = EXACT
    structural_threshold: float = 0.80  # Above this = STRUCTURAL
    behavioral_threshold: float = 0.60  # Above this = BEHAVIORAL
    partial_threshold: float = 0.30  # Above this = PARTIAL

    # Options
    ignore_function_names: bool = True
    ignore_variable_names: bool = True
    ignore_constant_values: bool = True
    consider_order: bool = True  # Consider operation order


class SimilarityCalculator:
    """Calculate semantic similarity between code elements."""

    def __init__(self, config: Optional[SimilarityConfig] = None):
        self.config = config or SimilarityConfig()

    def calculate(
        self,
        fp1: SemanticFingerprint,
        fp2: SemanticFingerprint,
    ) -> SimilarityResult:
        """Calculate similarity between two fingerprints."""
        # Calculate component scores
        op_score = self._operation_similarity(fp1.operations, fp2.operations)
        struct_score = self._structure_similarity(fp1, fp2)
        behavior_score = self._behavior_similarity(fp1, fp2)

        # Weighted combination
        total_score = (
            self.config.operation_weight * op_score +
            self.config.structure_weight * struct_score +
            self.config.behavior_weight * behavior_score
        )

        # Determine similarity type
        sim_type = self._classify_similarity(total_score)

        # Find matching/differing operations
        matching = set(fp1.operations) & set(fp2.operations)
        differing = set(fp1.operations) ^ set(fp2.operations)

        score = SimilarityScore(
            score=total_score,
            similarity_type=sim_type,
            confidence=self._calculate_confidence(fp1, fp2, total_score),
            operation_score=op_score,
            structure_score=struct_score,
            behavior_score=behavior_score,
            matching_operations=list(matching),
            differing_operations=list(differing),
        )

        return SimilarityResult(
            source_id=fp1.fingerprint_id,
            target_id=fp2.fingerprint_id,
            source_name=fp1.source_name,
            target_name=fp2.source_name,
            source_contract=fp1.contract_name,
            target_contract=fp2.contract_name,
            score=score,
        )

    def _operation_similarity(
        self,
        ops1: List[str],
        ops2: List[str],
    ) -> float:
        """Calculate similarity based on operations."""
        if not ops1 and not ops2:
            return 1.0
        if not ops1 or not ops2:
            return 0.0

        set1 = set(ops1)
        set2 = set(ops2)

        # Jaccard similarity
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        jaccard = intersection / union if union > 0 else 0.0

        # Order similarity if configured
        if self.config.consider_order:
            order_sim = self._sequence_similarity(ops1, ops2)
            return 0.7 * jaccard + 0.3 * order_sim

        return jaccard

    def _sequence_similarity(self, seq1: List[str], seq2: List[str]) -> float:
        """Calculate sequence similarity (order-aware)."""
        # Edit distance based similarity
        m, n = len(seq1), len(seq2)
        if m == 0 or n == 0:
            return 0.0

        # Levenshtein distance
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if seq1[i-1] == seq2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # deletion
                    dp[i][j-1] + 1,      # insertion
                    dp[i-1][j-1] + cost  # substitution
                )

        max_len = max(m, n)
        return 1.0 - (dp[m][n] / max_len) if max_len > 0 else 1.0

    def _structure_similarity(
        self,
        fp1: SemanticFingerprint,
        fp2: SemanticFingerprint,
    ) -> float:
        """Calculate structural similarity."""
        # Compare complexity metrics
        complexity_diff = abs(fp1.complexity - fp2.complexity)
        max_complexity = max(fp1.complexity, fp2.complexity, 1)
        complexity_sim = 1.0 - (complexity_diff / max_complexity)

        # Compare counts
        ops_diff = abs(fp1.num_operations - fp2.num_operations)
        max_ops = max(fp1.num_operations, fp2.num_operations, 1)
        ops_sim = 1.0 - (ops_diff / max_ops)

        ext_diff = abs(fp1.num_external_calls - fp2.num_external_calls)
        max_ext = max(fp1.num_external_calls, fp2.num_external_calls, 1)
        ext_sim = 1.0 - (ext_diff / max_ext)

        return (complexity_sim + ops_sim + ext_sim) / 3.0

    def _behavior_similarity(
        self,
        fp1: SemanticFingerprint,
        fp2: SemanticFingerprint,
    ) -> float:
        """Calculate behavioral similarity."""
        # Compare high-level behaviors

        # 1. Both transfer value?
        transfers_value1 = any("TRANSFER" in op for op in fp1.operations)
        transfers_value2 = any("TRANSFER" in op for op in fp2.operations)
        transfer_sim = 1.0 if transfers_value1 == transfers_value2 else 0.0

        # 2. Both have access control?
        has_access1 = any("CHECKS_PERMISSION" in op or "ACCESS" in op for op in fp1.operations)
        has_access2 = any("CHECKS_PERMISSION" in op or "ACCESS" in op for op in fp2.operations)
        access_sim = 1.0 if has_access1 == has_access2 else 0.0

        # 3. Both read external data?
        reads_external1 = any("READS_ORACLE" in op or "READS_EXTERNAL" in op for op in fp1.operations)
        reads_external2 = any("READS_ORACLE" in op or "READS_EXTERNAL" in op for op in fp2.operations)
        external_sim = 1.0 if reads_external1 == reads_external2 else 0.0

        # 4. Both modify state?
        modifies1 = any("WRITES" in op or "MODIFIES" in op for op in fp1.operations)
        modifies2 = any("WRITES" in op or "MODIFIES" in op for op in fp2.operations)
        modify_sim = 1.0 if modifies1 == modifies2 else 0.0

        # 5. Guard similarity
        guards1 = fp1.num_guards
        guards2 = fp2.num_guards
        guard_diff = abs(guards1 - guards2)
        max_guards = max(guards1, guards2, 1)
        guard_sim = 1.0 - (guard_diff / max_guards)

        return (transfer_sim + access_sim + external_sim + modify_sim + guard_sim) / 5.0

    def _classify_similarity(self, score: float) -> SimilarityType:
        """Classify similarity score into type."""
        if score >= self.config.exact_threshold:
            return SimilarityType.EXACT
        elif score >= self.config.structural_threshold:
            return SimilarityType.STRUCTURAL
        elif score >= self.config.behavioral_threshold:
            return SimilarityType.BEHAVIORAL
        elif score >= self.config.partial_threshold:
            return SimilarityType.PARTIAL
        else:
            return SimilarityType.NONE

    def _calculate_confidence(
        self,
        fp1: SemanticFingerprint,
        fp2: SemanticFingerprint,
        score: float,
    ) -> float:
        """Calculate confidence in the similarity score."""
        # More operations = more confident
        min_ops = min(fp1.num_operations, fp2.num_operations)
        op_confidence = min(1.0, min_ops / 5.0)  # Full confidence at 5+ operations

        # Similar complexity = more confident
        complexity_ratio = min(fp1.complexity, fp2.complexity) / max(fp1.complexity, fp2.complexity, 1)

        return (op_confidence + complexity_ratio) / 2.0

    def batch_compare(
        self,
        fingerprints: List[SemanticFingerprint],
        threshold: float = 0.5,
    ) -> List[SimilarityResult]:
        """Compare all fingerprints against each other."""
        results = []

        for i, fp1 in enumerate(fingerprints):
            for fp2 in fingerprints[i+1:]:
                result = self.calculate(fp1, fp2)
                if result.score.score >= threshold:
                    results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.score.score, reverse=True)

        return results

    def find_most_similar(
        self,
        target: SemanticFingerprint,
        candidates: List[SemanticFingerprint],
        top_k: int = 5,
    ) -> List[SimilarityResult]:
        """Find most similar fingerprints to target."""
        results = []

        for candidate in candidates:
            if candidate.fingerprint_id == target.fingerprint_id:
                continue

            result = self.calculate(target, candidate)
            results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.score.score, reverse=True)

        return results[:top_k]
