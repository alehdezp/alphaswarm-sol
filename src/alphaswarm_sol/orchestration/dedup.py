"""Enhanced Deduplication Logic for Orchestrator Mode (Phase 5.1 Plan 05).

Two-stage deduplication: location-based clustering + semantic similarity.
Supports cross-tool finding correlation with confidence boosting.

Features:
- Location-based clustering (file + line proximity)
- Semantic similarity via embeddings (optional)
- Multi-tool confidence boosting
- Graceful fallback when embeddings unavailable
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from alphaswarm_sol.orchestration.schemas import (
        DeltaEntry,
        MergeBatch,
        MergeConflict,
        MergeResult,
    )

import structlog

from alphaswarm_sol.tools.adapters.sarif import VKGFinding
from alphaswarm_sol.tools.mapping import get_confidence_boost, get_tool_precision


logger = structlog.get_logger(__name__)


# =============================================================================
# Category Aliases for Matching Similar Findings
# =============================================================================

CATEGORY_ALIASES: Dict[str, Set[str]] = {
    "reentrancy": {
        "reentrancy",
        "reentrancy-eth",
        "reentrancy-no-eth",
        "reentrancy-benign",
        "reentrancy-events",
        "read-only-reentrancy",
        "cross-function-reentrancy",
        "reentrancy-state",
        "reentrancy-classic",
    },
    "access_control": {
        "access_control",
        "access-control",
        "unprotected-upgrade",
        "missing-access-control",
        "tx-origin",
        "tx-origin-auth",
        "access-control-missing",
        "access-control-permissive",
    },
    "oracle": {
        "oracle",
        "oracle_manipulation",
        "oracle-manipulation",
        "stale-price",
        "price-manipulation",
        "oracle-stale-data",
    },
    "arithmetic": {
        "arithmetic",
        "integer-overflow",
        "divide-before-multiply",
        "unchecked-math",
        "arithmetic-overflow",
        "arithmetic-underflow",
        "arithmetic-precision-loss",
    },
    "dos": {
        "dos",
        "denial-of-service",
        "unbounded-loop",
        "gas-limit",
        "block-gas-limit",
        "dos-external-call-loop",
        "dos-gas-limit",
    },
    "signature": {
        "signature",
        "ecrecover",
        "signature-malleability",
        "missing-zero-check",
    },
    "unchecked": {
        "unchecked-transfer",
        "unchecked-low-level-call",
        "unchecked-send",
        "return-value",
        "unchecked_return",
        "unchecked-return",
    },
    "delegation": {
        "delegation",
        "delegatecall",
        "delegatecall-injection",
        "delegatecall-loop",
    },
    "state": {
        "state",
        "state-uninitialized",
        "state-corruption",
        "state-double-write",
        "initialization",
    },
    "time_manipulation": {
        "time_manipulation",
        "timestamp",
        "timestamp-dependence",
        "block-timestamp",
    },
    "randomness": {
        "randomness",
        "weak-prng",
        "weak-randomness",
    },
}


# =============================================================================
# High-confidence tools for boosting
# =============================================================================

HIGH_CONFIDENCE_TOOLS: Set[str] = {
    "slither",
    "mythril",
    "halmos",
    "echidna",
    "foundry",
}


# =============================================================================
# Category Helpers
# =============================================================================


def _normalize_category(category: str) -> str:
    """Normalize category to base form.

    Args:
        category: Raw category string

    Returns:
        Normalized category
    """
    cat_lower = category.lower().replace("_", "-")

    for base_cat, aliases in CATEGORY_ALIASES.items():
        if cat_lower in aliases or cat_lower == base_cat.replace("_", "-"):
            return base_cat

    return cat_lower


def _categories_similar(cat1: str, cat2: str) -> bool:
    """Check if two categories are similar.

    Args:
        cat1: First category
        cat2: Second category

    Returns:
        True if categories are similar
    """
    norm1 = _normalize_category(cat1)
    norm2 = _normalize_category(cat2)
    return norm1 == norm2


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DeduplicatedFinding:
    """A finding that may be reported by multiple tools.

    Aggregates findings from different tools that refer to the
    same location and similar vulnerability type.
    """

    file: str
    line: int
    function: Optional[str]
    category: str
    severity: str
    sources: List[str] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    agreement: bool = True
    confidence: float = 0.0
    vkg_pattern: Optional[str] = None

    @property
    def source_count(self) -> int:
        """Number of tools that found this issue."""
        return len(self.sources)

    @property
    def high_confidence(self) -> bool:
        """True if multiple tools agree or confidence is high."""
        return (self.source_count > 1 and self.agreement) or self.confidence >= 0.85

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "function": self.function,
            "category": self.category,
            "severity": self.severity,
            "sources": self.sources,
            "source_count": self.source_count,
            "agreement": self.agreement,
            "high_confidence": self.high_confidence,
            "confidence": round(self.confidence, 3),
            "vkg_pattern": self.vkg_pattern,
        }


@dataclass
class DeduplicationStats:
    """Statistics from deduplication process."""

    input_count: int
    output_count: int
    reduction_percent: float
    location_matches: int
    semantic_matches: int
    tool_agreement_boosts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "reduction_percent": round(self.reduction_percent, 1),
            "location_matches": self.location_matches,
            "semantic_matches": self.semantic_matches,
            "tool_agreement_boosts": self.tool_agreement_boosts,
        }


@dataclass
class DeduplicationResult:
    """Result of deduplication process."""

    findings: List[DeduplicatedFinding]
    stats: DeduplicationStats

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "findings": [f.to_dict() for f in self.findings],
            "stats": self.stats.to_dict(),
        }


# =============================================================================
# Semantic Deduplicator Class
# =============================================================================


class SemanticDeduplicator:
    """Two-stage deduplication: location + semantic similarity.

    Stage 1: Cluster findings by file and line proximity
    Stage 2: Further cluster by semantic similarity of descriptions

    Gracefully falls back to location-only if embeddings unavailable.

    Example:
        >>> dedup = SemanticDeduplicator(similarity_threshold=0.85)
        >>> findings, stats = dedup.deduplicate(all_findings)
        >>> print(f"Reduced {stats.input_count} to {stats.output_count}")
    """

    def __init__(
        self,
        use_embeddings: bool = True,
        similarity_threshold: float = 0.85,
        line_tolerance: int = 5,
    ):
        """Initialize the deduplicator.

        Args:
            use_embeddings: Whether to use semantic similarity (requires sentence-transformers)
            similarity_threshold: Cosine similarity threshold for matching (0.0-1.0)
            line_tolerance: Maximum line difference for location-based matching
        """
        self.use_embeddings = use_embeddings
        self.similarity_threshold = similarity_threshold
        self.line_tolerance = line_tolerance
        self._embedding_model = None
        self._embeddings_available: Optional[bool] = None

    @property
    def embedding_model(self) -> Any:
        """Lazy load embedding model.

        Returns:
            SentenceTransformer model or None if unavailable
        """
        if self._embeddings_available is False:
            return None

        if self._embedding_model is None and self.use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                self._embeddings_available = True
                logger.info("semantic_dedup_enabled", model="all-MiniLM-L6-v2")
            except ImportError:
                logger.warning(
                    "semantic_dedup_disabled",
                    reason="sentence-transformers not installed",
                )
                self.use_embeddings = False
                self._embeddings_available = False
            except Exception as e:
                logger.warning(
                    "semantic_dedup_disabled",
                    reason=str(e),
                )
                self.use_embeddings = False
                self._embeddings_available = False

        return self._embedding_model

    def deduplicate(
        self,
        findings: List[VKGFinding],
    ) -> Tuple[List[DeduplicatedFinding], DeduplicationStats]:
        """Deduplicate findings using two-stage approach.

        Args:
            findings: List of VKGFinding from all tools

        Returns:
            Tuple of (deduplicated findings, statistics)
        """
        if not findings:
            return [], DeduplicationStats(
                input_count=0,
                output_count=0,
                reduction_percent=0.0,
                location_matches=0,
                semantic_matches=0,
            )

        logger.info("dedup_starting", finding_count=len(findings))

        # Stage 1: Location-based clustering
        location_clusters = self._cluster_by_location(findings)
        location_match_count = sum(1 for c in location_clusters if len(c) > 1)

        # Stage 2: Semantic similarity within location clusters
        semantic_match_count = 0
        if self.use_embeddings and self.embedding_model:
            final_clusters: List[List[VKGFinding]] = []
            for cluster in location_clusters:
                if len(cluster) > 1:
                    # Check semantic similarity within cluster
                    semantic_subclusters = self._cluster_by_semantics(cluster)
                    final_clusters.extend(semantic_subclusters)
                    # Count merges from semantic matching
                    if len(semantic_subclusters) < len(cluster):
                        semantic_match_count += len(cluster) - len(semantic_subclusters)
                else:
                    final_clusters.append(cluster)
        else:
            final_clusters = location_clusters

        # Convert clusters to DeduplicatedFinding with confidence boosting
        results: List[DeduplicatedFinding] = []
        tool_boosts = 0

        for cluster in final_clusters:
            deduped, boosted = self._cluster_to_finding(cluster)
            results.append(deduped)
            if boosted:
                tool_boosts += 1

        # Sort by severity (critical > high > medium > low > info)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        results.sort(key=lambda x: severity_order.get(x.severity, 5))

        # Calculate stats
        stats = DeduplicationStats(
            input_count=len(findings),
            output_count=len(results),
            reduction_percent=round(
                100 * (1 - len(results) / max(len(findings), 1)), 1
            ),
            location_matches=location_match_count,
            semantic_matches=semantic_match_count,
            tool_agreement_boosts=tool_boosts,
        )

        logger.info(
            "dedup_complete",
            input=stats.input_count,
            output=stats.output_count,
            reduction_pct=stats.reduction_percent,
            location_matches=stats.location_matches,
            semantic_matches=stats.semantic_matches,
        )

        return results, stats

    def _cluster_by_location(
        self,
        findings: List[VKGFinding],
    ) -> List[List[VKGFinding]]:
        """Cluster findings by file and line proximity.

        Args:
            findings: All findings to cluster

        Returns:
            List of clusters (each cluster is list of findings)
        """
        # Group by file (using filename only for matching)
        by_file: Dict[str, List[VKGFinding]] = {}
        for f in findings:
            file_key = Path(f.file).name if f.file else "unknown"
            if file_key not in by_file:
                by_file[file_key] = []
            by_file[file_key].append(f)

        clusters: List[List[VKGFinding]] = []

        for file_key, file_findings in by_file.items():
            # Sort by line number
            file_findings.sort(key=lambda x: x.line or 0)

            # Cluster by proximity AND category similarity
            used: Set[int] = set()

            for i, finding in enumerate(file_findings):
                if i in used:
                    continue

                cluster = [finding]
                used.add(i)

                # Find nearby findings with similar categories
                for j, other in enumerate(file_findings):
                    if j in used:
                        continue

                    line_diff = abs((other.line or 0) - (finding.line or 0))
                    if line_diff <= self.line_tolerance:
                        # Check category similarity
                        if _categories_similar(
                            finding.category or "",
                            other.category or "",
                        ):
                            cluster.append(other)
                            used.add(j)

                clusters.append(cluster)

        return clusters

    def _cluster_by_semantics(
        self,
        findings: List[VKGFinding],
    ) -> List[List[VKGFinding]]:
        """Further cluster findings by semantic similarity.

        Args:
            findings: Findings already clustered by location

        Returns:
            Subclusters based on semantic similarity
        """
        if not self.embedding_model or len(findings) < 2:
            return [findings]

        try:
            # Get descriptions for embedding
            descriptions = [
                f"{f.title or ''} {f.description or ''}" for f in findings
            ]

            # Generate embeddings
            embeddings = self.embedding_model.encode(
                descriptions,
                show_progress_bar=False,
            )

            # Compute similarity matrix
            try:
                from sklearn.metrics.pairwise import cosine_similarity

                similarities = cosine_similarity(embeddings)
            except ImportError:
                # Fallback: manual cosine similarity
                import numpy as np

                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                normalized = embeddings / (norms + 1e-10)
                similarities = np.dot(normalized, normalized.T)

            # Cluster based on threshold
            clusters: List[List[VKGFinding]] = []
            used: Set[int] = set()

            for i, finding in enumerate(findings):
                if i in used:
                    continue

                cluster = [finding]
                used.add(i)

                for j in range(i + 1, len(findings)):
                    if j not in used and similarities[i][j] >= self.similarity_threshold:
                        cluster.append(findings[j])
                        used.add(j)

                clusters.append(cluster)

            return clusters

        except Exception as e:
            logger.warning("semantic_clustering_failed", error=str(e))
            return [findings]

    def _cluster_to_finding(
        self,
        cluster: List[VKGFinding],
    ) -> Tuple[DeduplicatedFinding, bool]:
        """Convert a cluster of findings to DeduplicatedFinding.

        Applies confidence boosting for multi-tool agreement.

        Args:
            cluster: List of similar findings

        Returns:
            Tuple of (DeduplicatedFinding, was_boosted)
        """
        sources = list(set(f.source for f in cluster if f.source))
        severities = set(f.severity for f in cluster if f.severity)
        categories = set(f.category for f in cluster if f.category)
        patterns = set(f.vkg_pattern for f in cluster if f.vkg_pattern)

        # Determine overall severity (most severe)
        severity_order = ["critical", "high", "medium", "low", "info"]
        overall_severity = "info"
        for sev in severity_order:
            if sev in severities:
                overall_severity = sev
                break

        # Normalize categories
        normalized_cats = set(_normalize_category(c) for c in categories if c)

        # Check agreement
        agreement = len(severities) <= 1 and len(normalized_cats) <= 1

        # Use first finding for base info
        first = cluster[0]
        category = (
            list(normalized_cats)[0]
            if len(normalized_cats) == 1
            else ", ".join(sorted(normalized_cats)) if normalized_cats else "unknown"
        )

        # Get best pattern match
        vkg_pattern = next(iter(patterns), None)

        # Calculate base confidence from first finding
        base_confidence = first.confidence or 0.5

        # Apply confidence boosting for tool agreement
        was_boosted = False
        if len(sources) > 1:
            was_boosted = True

            # Boost based on number of agreeing tools
            if len(sources) >= 3:
                base_confidence += 0.2
            elif len(sources) == 2:
                base_confidence += 0.1

            # Extra boost for high-confidence tools
            high_conf_count = sum(1 for s in sources if s in HIGH_CONFIDENCE_TOOLS)
            if high_conf_count >= 2:
                base_confidence += 0.1

            # Apply tool-specific precision boosts
            for f in cluster:
                if f.source and f.rule_id:
                    boost = get_confidence_boost(f.source, f.rule_id)
                    if boost > 0:
                        base_confidence = max(base_confidence, f.confidence or 0.5 + boost)

        # Clamp confidence to [0.0, 1.0]
        final_confidence = min(1.0, max(0.0, base_confidence))

        # Convert findings to dicts
        finding_dicts = [_finding_to_dict(f) for f in cluster]

        return (
            DeduplicatedFinding(
                file=first.file or "unknown",
                line=first.line or 0,
                function=first.function,
                category=category,
                severity=overall_severity,
                sources=sources,
                findings=finding_dicts,
                agreement=agreement,
                confidence=final_confidence,
                vkg_pattern=vkg_pattern,
            ),
            was_boosted,
        )


def _finding_to_dict(finding: VKGFinding) -> Dict[str, Any]:
    """Convert VKGFinding to dictionary.

    Args:
        finding: VKGFinding instance

    Returns:
        Dictionary representation
    """
    return {
        "source": finding.source,
        "rule_id": finding.rule_id,
        "title": finding.title,
        "description": finding.description,
        "severity": finding.severity,
        "category": finding.category,
        "file": finding.file,
        "line": finding.line,
        "function": finding.function,
        "confidence": finding.confidence,
        "vkg_pattern": finding.vkg_pattern,
    }


# =============================================================================
# Main Deduplication Function
# =============================================================================


def deduplicate_findings(
    all_findings: List[Dict[str, Any]],
    line_tolerance: int = 5,
    use_embeddings: bool = True,
    similarity_threshold: float = 0.85,
) -> List[DeduplicatedFinding]:
    """Deduplicate findings from multiple tools.

    Enhanced version using SemanticDeduplicator when available.
    Falls back to location-only deduplication if embeddings unavailable.

    Findings are considered duplicates if:
    1. Same file (by filename, not full path)
    2. Lines within tolerance
    3. Similar category (using category mapping)
    4. (Optional) Similar semantic content

    Args:
        all_findings: Normalized findings from all tools (as dicts)
        line_tolerance: Lines within this range are considered same location
        use_embeddings: Whether to use semantic similarity
        similarity_threshold: Threshold for semantic matching

    Returns:
        List of deduplicated findings sorted by severity
    """
    if not all_findings:
        return []

    # Convert dicts to VKGFinding if needed
    vkg_findings: List[VKGFinding] = []
    for f in all_findings:
        if isinstance(f, VKGFinding):
            vkg_findings.append(f)
        elif isinstance(f, dict):
            vkg_findings.append(
                VKGFinding(
                    source=f.get("source", "unknown"),
                    rule_id=f.get("rule_id", f.get("detector", "unknown")),
                    title=f.get("title", ""),
                    description=f.get("description", ""),
                    severity=f.get("severity", "medium"),
                    category=f.get("category", "unknown"),
                    file=f.get("file", "unknown"),
                    line=f.get("line", 0),
                    function=f.get("function"),
                    confidence=f.get("confidence", 0.5),
                    vkg_pattern=f.get("vkg_pattern"),
                    raw=f,
                )
            )

    # Use SemanticDeduplicator
    dedup = SemanticDeduplicator(
        use_embeddings=use_embeddings,
        similarity_threshold=similarity_threshold,
        line_tolerance=line_tolerance,
    )

    results, _stats = dedup.deduplicate(vkg_findings)
    return results


def deduplicate_with_stats(
    findings: List[VKGFinding],
    line_tolerance: int = 5,
    use_embeddings: bool = True,
    similarity_threshold: float = 0.85,
) -> DeduplicationResult:
    """Deduplicate findings and return full result with stats.

    Args:
        findings: List of VKGFinding instances
        line_tolerance: Lines within this range are considered same location
        use_embeddings: Whether to use semantic similarity
        similarity_threshold: Threshold for semantic matching

    Returns:
        DeduplicationResult with findings and statistics
    """
    dedup = SemanticDeduplicator(
        use_embeddings=use_embeddings,
        similarity_threshold=similarity_threshold,
        line_tolerance=line_tolerance,
    )

    results, stats = dedup.deduplicate(findings)
    return DeduplicationResult(findings=results, stats=stats)


# =============================================================================
# Utility Functions
# =============================================================================


def merge_findings(
    deduped: List[DeduplicatedFinding],
) -> Dict[str, List[DeduplicatedFinding]]:
    """Group deduplicated findings by category.

    Args:
        deduped: List of deduplicated findings

    Returns:
        Dictionary mapping category to findings
    """
    by_category: Dict[str, List[DeduplicatedFinding]] = {}
    for f in deduped:
        cat = _normalize_category(f.category)
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(f)
    return by_category


def get_disagreements(
    deduped: List[DeduplicatedFinding],
) -> List[DeduplicatedFinding]:
    """Get findings where tools disagree.

    Args:
        deduped: List of deduplicated findings

    Returns:
        Findings with disagreements (multiple sources, different severity/category)
    """
    return [f for f in deduped if not f.agreement and f.source_count > 1]


def get_unique_to_tool(
    deduped: List[DeduplicatedFinding],
    tool: str,
) -> List[DeduplicatedFinding]:
    """Get findings unique to a specific tool.

    Args:
        deduped: List of deduplicated findings
        tool: Tool name to filter by

    Returns:
        Findings only found by the specified tool
    """
    return [f for f in deduped if f.sources == [tool]]


def get_high_confidence_findings(
    deduped: List[DeduplicatedFinding],
    min_confidence: float = 0.8,
) -> List[DeduplicatedFinding]:
    """Get findings with high confidence.

    Args:
        deduped: List of deduplicated findings
        min_confidence: Minimum confidence threshold

    Returns:
        Findings above confidence threshold
    """
    return [f for f in deduped if f.confidence >= min_confidence]


def get_multi_tool_findings(
    deduped: List[DeduplicatedFinding],
) -> List[DeduplicatedFinding]:
    """Get findings confirmed by multiple tools.

    Args:
        deduped: List of deduplicated findings

    Returns:
        Findings found by 2+ tools
    """
    return [f for f in deduped if f.source_count >= 2]


def calculate_dedup_hash(finding: Dict[str, Any]) -> str:
    """Calculate hash for finding deduplication.

    Uses file, line range, and category for matching.

    Args:
        finding: Finding dictionary

    Returns:
        Hash string for deduplication
    """
    file_name = Path(finding.get("file", "")).name
    line = finding.get("line", 0)
    category = _normalize_category(finding.get("category", ""))

    # Create hash key
    key = f"{file_name}:{line}:{category}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


# =============================================================================
# Merge Pipeline v2 - Deterministic, Idempotent, Append-Only (Phase 5.10-10)
# =============================================================================


def merge_batch_deltas(
    batches: List["MergeBatch"],
    existing_deltas: Optional[List["DeltaEntry"]] = None,
) -> "MergeResult":
    """Merge deltas from multiple batches deterministically.

    This is the core merge function for the append-only pipeline.
    It implements:
    1. Deterministic ordering via ordering_key
    2. Conflict detection for same-target divergent deltas
    3. Idempotent replay (same inputs = same outputs)
    4. Full audit trail for debugging

    Args:
        batches: List of MergeBatch to merge
        existing_deltas: Optional existing deltas to merge with (for incremental)

    Returns:
        MergeResult with merged deltas, conflicts, and audit trail

    Usage:
        batches = [scout_batch, verifier_batch]
        result = merge_batch_deltas(batches)
        if result.conflicts:
            resolver_agent.handle(result.conflicts)

    Idempotency:
        merge_batch_deltas([A, B]) == merge_batch_deltas([A, B])  # Always true
        merge_batch_deltas([A, B]) == merge_batch_deltas([B, A])  # True (order-independent)
    """
    # Import schema types locally to avoid circular imports
    from alphaswarm_sol.orchestration.schemas import (
        DeltaEntry,
        MergeBatch,
        MergeConflict,
        MergeResult,
        ConflictType as MergeConflictType,
    )

    audit_trail: List[str] = []
    all_deltas: List[DeltaEntry] = []
    conflicts: List[MergeConflict] = []

    # Collect existing deltas
    if existing_deltas:
        all_deltas.extend(existing_deltas)
        audit_trail.append(f"Loaded {len(existing_deltas)} existing deltas")

    # Collect deltas from all batches
    for batch in batches:
        audit_trail.append(f"Processing batch {batch.batch_id} from {batch.source} with {len(batch.deltas)} deltas")
        all_deltas.extend(batch.deltas)

    if not all_deltas:
        return MergeResult(
            merged_deltas=[],
            conflicts=[],
            audit_trail=["No deltas to merge"],
            idempotent=True,
        )

    # Sort by ordering_key for deterministic order
    all_deltas.sort(key=lambda d: d.ordering_key)
    audit_trail.append(f"Sorted {len(all_deltas)} deltas by ordering_key")

    # Detect conflicts - deltas with same target_id but different evidence
    target_map: Dict[str, List[DeltaEntry]] = {}
    for delta in all_deltas:
        if delta.target_id not in target_map:
            target_map[delta.target_id] = []
        target_map[delta.target_id].append(delta)

    # Check for conflicts within each target group
    for target_id, target_deltas in target_map.items():
        if len(target_deltas) < 2:
            continue

        # Check pairwise for conflicts
        for i, delta_a in enumerate(target_deltas):
            for delta_b in target_deltas[i + 1:]:
                conflict = _detect_conflict(delta_a, delta_b)
                if conflict:
                    conflicts.append(conflict)
                    audit_trail.append(
                        f"Conflict detected: {conflict.conflict_id} between "
                        f"{delta_a.delta_id} and {delta_b.delta_id}"
                    )

    # Deduplicate by delta_id (idempotent - same delta appears once)
    seen_ids: Set[str] = set()
    merged_deltas: List[DeltaEntry] = []

    for delta in all_deltas:
        if delta.delta_id not in seen_ids:
            seen_ids.add(delta.delta_id)
            merged_deltas.append(delta)
        else:
            audit_trail.append(f"Duplicate delta {delta.delta_id} skipped (idempotent)")

    audit_trail.append(f"Final merged: {len(merged_deltas)} deltas, {len(conflicts)} conflicts")

    return MergeResult(
        merged_deltas=merged_deltas,
        conflicts=conflicts,
        audit_trail=audit_trail,
        idempotent=True,  # By construction
    )


def _detect_conflict(
    delta_a: "DeltaEntry",
    delta_b: "DeltaEntry",
) -> Optional["MergeConflict"]:
    """Detect if two deltas conflict.

    Conflicts occur when:
    1. Same target, different evidence IDs
    2. Same target, conflicting confidence claims
    3. Same target, divergent payloads

    Returns MergeConflict if conflict detected, None otherwise.
    """
    from alphaswarm_sol.orchestration.schemas import (
        MergeConflict,
        ConflictType as MergeConflictType,
    )

    # Same delta (by content hash) - not a conflict
    if delta_a.delta_id == delta_b.delta_id:
        return None

    # Different targets - not a conflict
    if delta_a.target_id != delta_b.target_id:
        return None

    # Check evidence mismatch
    evidence_a = set(delta_a.evidence_ids)
    evidence_b = set(delta_b.evidence_ids)

    if evidence_a and evidence_b and not evidence_a.intersection(evidence_b):
        # Disjoint evidence sets for same target
        return MergeConflict(
            conflict_type=MergeConflictType.EVIDENCE_MISMATCH,
            delta_a=delta_a,
            delta_b=delta_b,
            description=f"Disjoint evidence for target {delta_a.target_id}: "
                        f"{evidence_a} vs {evidence_b}",
        )

    # Check confidence conflict
    conf_a = delta_a.payload.get("confidence")
    conf_b = delta_b.payload.get("confidence")

    if conf_a is not None and conf_b is not None:
        # Significant confidence difference (> 0.3 gap)
        if isinstance(conf_a, (int, float)) and isinstance(conf_b, (int, float)):
            if abs(float(conf_a) - float(conf_b)) > 0.3:
                return MergeConflict(
                    conflict_type=MergeConflictType.CONFIDENCE_CONFLICT,
                    delta_a=delta_a,
                    delta_b=delta_b,
                    description=f"Confidence conflict for {delta_a.target_id}: "
                                f"{conf_a} vs {conf_b}",
                )

    # Check payload divergence (different verdicts/claims)
    verdict_a = delta_a.payload.get("is_vulnerable")
    verdict_b = delta_b.payload.get("is_vulnerable")

    if verdict_a is not None and verdict_b is not None and verdict_a != verdict_b:
        return MergeConflict(
            conflict_type=MergeConflictType.PAYLOAD_DIVERGENCE,
            delta_a=delta_a,
            delta_b=delta_b,
            description=f"Verdict divergence for {delta_a.target_id}: "
                        f"vulnerable={verdict_a} vs vulnerable={verdict_b}",
        )

    return None


def verify_merge_idempotency(
    batches: List["MergeBatch"],
    expected_hash: str,
) -> bool:
    """Verify that merging batches produces expected output hash.

    This function is used to verify that replay of the same batches
    produces bit-identical output.

    Args:
        batches: Batches to merge
        expected_hash: Expected output_hash from previous merge

    Returns:
        True if merge produces same hash, False otherwise
    """
    result = merge_batch_deltas(batches)
    return result.output_hash == expected_hash


def compute_merged_output_hash(deltas: List["DeltaEntry"]) -> str:
    """Compute stable hash for a set of merged deltas.

    Used for cache keys and idempotency verification.

    Args:
        deltas: List of merged deltas

    Returns:
        Stable hash string
    """
    # Sort by ordering_key for determinism
    sorted_deltas = sorted(deltas, key=lambda d: d.ordering_key)
    delta_ids = [d.delta_id for d in sorted_deltas]
    content = ",".join(delta_ids)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


__all__ = [
    "CATEGORY_ALIASES",
    "DeduplicatedFinding",
    "DeduplicationStats",
    "DeduplicationResult",
    "SemanticDeduplicator",
    "deduplicate_findings",
    "deduplicate_with_stats",
    "merge_findings",
    "get_disagreements",
    "get_unique_to_tool",
    "get_high_confidence_findings",
    "get_multi_tool_findings",
    "calculate_dedup_hash",
    # Merge pipeline v2 (Phase 5.10-10)
    "merge_batch_deltas",
    "verify_merge_idempotency",
    "compute_merged_output_hash",
]
