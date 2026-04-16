"""
Quality Tracking and Fallback (Tasks 4.7-4.8)

Tracks test scaffold quality metrics and provides fallback mechanisms
when higher-tier generation fails.

Phase 7.2 Additions:
- Evidence debt tracking (I4): Block promotion when >25% findings lack strong evidence
- Plausibility scoring (I6): Compute priority-only scores (never hide findings)
- Economic context TTL (I5): 30-day TTL decay for context fields

Philosophy:
- Track compile rate, execution rate, and detection accuracy
- Provide graceful fallback from Tier 2 to Tier 1
- Never leave the user without a useful scaffold
- Maintain realistic expectations (30-40% compile rate)
- Evidence debt blocks pattern promotion, not findings
- Plausibility scores prioritize, never suppress
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import yaml

from alphaswarm_sol.testing.generator import TestScaffold, generate_tier1_scaffold, generate_tier2_scaffold
from alphaswarm_sol.testing.detection import ProjectConfig
from alphaswarm_sol.testing.tiers import TestTier, TIER_DEFINITIONS
from alphaswarm_sol.enterprise.reports import Finding


# =============================================================================
# Evidence Debt Tracking (Phase 7.2 Innovation I4)
# =============================================================================

class EvidenceStrength(str, Enum):
    """Evidence strength classification."""
    STRONG = "strong"       # Canonical audit/report/on-chain proof
    MEDIUM = "medium"       # Inferred from code patterns
    WEAK = "weak"           # Hypothesis or no evidence
    UNKNOWN = "unknown"     # Not yet classified


@dataclass
class EvidenceDebtEntry:
    """Single evidence debt entry for a pattern or finding.

    Evidence debt tracks findings that lack strong evidence references.
    If >25% of a pattern's findings have weak evidence, promotion is blocked.
    """
    pattern_id: str
    finding_id: str
    evidence_strength: EvidenceStrength
    evidence_refs: List[str] = field(default_factory=list)
    missing_evidence_type: Optional[str] = None  # What type of evidence is missing
    created_at: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "finding_id": self.finding_id,
            "evidence_strength": self.evidence_strength.value,
            "evidence_refs": self.evidence_refs,
            "missing_evidence_type": self.missing_evidence_type,
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass
class PatternEvidenceDebt:
    """Aggregate evidence debt for a pattern."""
    pattern_id: str
    total_findings: int = 0
    strong_evidence_count: int = 0
    medium_evidence_count: int = 0
    weak_evidence_count: int = 0
    unknown_evidence_count: int = 0
    debt_entries: List[EvidenceDebtEntry] = field(default_factory=list)

    @property
    def weak_evidence_ratio(self) -> float:
        """Calculate ratio of weak evidence findings."""
        if self.total_findings == 0:
            return 0.0
        return (self.weak_evidence_count + self.unknown_evidence_count) / self.total_findings

    @property
    def promotion_blocked(self) -> bool:
        """Check if promotion is blocked due to evidence debt.

        Per Phase 7.2 CONTEXT: >25% weak evidence blocks promotion.
        """
        return self.weak_evidence_ratio > 0.25

    @property
    def debt_level(self) -> str:
        """Human-readable debt level."""
        ratio = self.weak_evidence_ratio
        if ratio == 0:
            return "none"
        elif ratio <= 0.10:
            return "low"
        elif ratio <= 0.25:
            return "moderate"
        else:
            return "high"  # Promotion blocked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "total_findings": self.total_findings,
            "strong_evidence_count": self.strong_evidence_count,
            "medium_evidence_count": self.medium_evidence_count,
            "weak_evidence_count": self.weak_evidence_count,
            "unknown_evidence_count": self.unknown_evidence_count,
            "weak_evidence_ratio": round(self.weak_evidence_ratio, 3),
            "promotion_blocked": self.promotion_blocked,
            "debt_level": self.debt_level,
            "debt_entries": [e.to_dict() for e in self.debt_entries],
        }


class EvidenceDebtTracker:
    """Tracks evidence debt across patterns.

    Evidence debt is a measure of how many findings lack strong evidence
    references. High debt blocks pattern promotion to ready/excellent status.

    Per Phase 7.2 CONTEXT (I4):
    - Each finding must link to evidence IDs
    - If >25% of a pattern's findings lack high-confidence evidence IDs -> debt
    - Evidence debt gets logged and blocks promotion to "ready/excellent"

    Output: .vrs/corpus/metadata/evidence_debt.yaml
    """

    # Threshold for promotion blocking
    DEBT_THRESHOLD = 0.25  # >25% weak evidence blocks promotion

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize evidence debt tracker.

        Args:
            storage_path: Path to evidence_debt.yaml. Defaults to
                .vrs/corpus/metadata/evidence_debt.yaml
        """
        self.storage_path = storage_path or Path(".vrs/corpus/metadata/evidence_debt.yaml")
        self.pattern_debts: Dict[str, PatternEvidenceDebt] = {}

        if self.storage_path.exists():
            self._load()

    def classify_evidence_strength(
        self,
        evidence_refs: List[str],
        has_audit_ref: bool = False,
        has_code_location: bool = False,
        has_graph_node_id: bool = False,
    ) -> EvidenceStrength:
        """Classify evidence strength based on available references.

        Strong evidence requires:
        - Audit report reference OR
        - On-chain evidence OR
        - Multiple corroborating references

        Medium evidence requires:
        - Code location AND graph node ID OR
        - At least one reference

        Weak/Unknown otherwise.
        """
        if not evidence_refs:
            if has_code_location and has_graph_node_id:
                return EvidenceStrength.MEDIUM
            return EvidenceStrength.UNKNOWN

        # Check for strong evidence indicators
        strong_indicators = ["audit", "postmortem", "exploit", "poc", "cve"]
        for ref in evidence_refs:
            ref_lower = ref.lower()
            if any(ind in ref_lower for ind in strong_indicators):
                return EvidenceStrength.STRONG

        if has_audit_ref:
            return EvidenceStrength.STRONG

        # Multiple references suggest medium strength
        if len(evidence_refs) >= 2 or (has_code_location and has_graph_node_id):
            return EvidenceStrength.MEDIUM

        if evidence_refs or has_code_location:
            return EvidenceStrength.MEDIUM

        return EvidenceStrength.WEAK

    def record_finding_evidence(
        self,
        pattern_id: str,
        finding_id: str,
        evidence_refs: List[str],
        has_audit_ref: bool = False,
        has_code_location: bool = False,
        has_graph_node_id: bool = False,
        notes: str = "",
    ) -> EvidenceDebtEntry:
        """Record evidence status for a finding.

        Args:
            pattern_id: Pattern that produced the finding
            finding_id: Unique finding identifier
            evidence_refs: List of evidence reference IDs/URLs
            has_audit_ref: Whether finding has audit report reference
            has_code_location: Whether finding has code location
            has_graph_node_id: Whether finding has graph node ID
            notes: Additional notes

        Returns:
            EvidenceDebtEntry for the finding
        """
        strength = self.classify_evidence_strength(
            evidence_refs, has_audit_ref, has_code_location, has_graph_node_id
        )

        missing_type = None
        if strength in (EvidenceStrength.WEAK, EvidenceStrength.UNKNOWN):
            if not evidence_refs:
                missing_type = "no_references"
            elif not has_code_location:
                missing_type = "no_code_location"
            else:
                missing_type = "insufficient_provenance"

        entry = EvidenceDebtEntry(
            pattern_id=pattern_id,
            finding_id=finding_id,
            evidence_strength=strength,
            evidence_refs=evidence_refs,
            missing_evidence_type=missing_type,
            notes=notes,
        )

        # Update pattern aggregate
        if pattern_id not in self.pattern_debts:
            self.pattern_debts[pattern_id] = PatternEvidenceDebt(pattern_id=pattern_id)

        debt = self.pattern_debts[pattern_id]
        debt.total_findings += 1
        debt.debt_entries.append(entry)

        if strength == EvidenceStrength.STRONG:
            debt.strong_evidence_count += 1
        elif strength == EvidenceStrength.MEDIUM:
            debt.medium_evidence_count += 1
        elif strength == EvidenceStrength.WEAK:
            debt.weak_evidence_count += 1
        else:
            debt.unknown_evidence_count += 1

        return entry

    def get_pattern_debt(self, pattern_id: str) -> Optional[PatternEvidenceDebt]:
        """Get evidence debt summary for a pattern."""
        return self.pattern_debts.get(pattern_id)

    def is_promotion_blocked(self, pattern_id: str) -> bool:
        """Check if pattern promotion is blocked due to evidence debt."""
        debt = self.get_pattern_debt(pattern_id)
        if debt is None:
            return False
        return debt.promotion_blocked

    def get_blocked_patterns(self) -> List[str]:
        """Get list of patterns blocked from promotion."""
        return [pid for pid, debt in self.pattern_debts.items() if debt.promotion_blocked]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all evidence debt."""
        total_patterns = len(self.pattern_debts)
        blocked_patterns = len(self.get_blocked_patterns())

        total_findings = sum(d.total_findings for d in self.pattern_debts.values())
        weak_findings = sum(
            d.weak_evidence_count + d.unknown_evidence_count
            for d in self.pattern_debts.values()
        )

        return {
            "total_patterns_tracked": total_patterns,
            "patterns_with_debt": blocked_patterns,
            "total_findings": total_findings,
            "weak_evidence_findings": weak_findings,
            "overall_weak_ratio": round(weak_findings / total_findings, 3) if total_findings > 0 else 0,
            "debt_threshold": self.DEBT_THRESHOLD,
            "blocked_patterns": self.get_blocked_patterns(),
        }

    def save(self) -> Path:
        """Save evidence debt ledger to YAML."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "evidence_debt_ledger": {
                "generated_at": datetime.utcnow().isoformat(),
                "summary": self.get_summary(),
                "patterns": {
                    pid: debt.to_dict()
                    for pid, debt in self.pattern_debts.items()
                },
            }
        }

        self.storage_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        return self.storage_path

    def _load(self) -> None:
        """Load evidence debt from YAML."""
        try:
            data = yaml.safe_load(self.storage_path.read_text())
            if not data or "evidence_debt_ledger" not in data:
                return

            ledger = data["evidence_debt_ledger"]
            for pid, pdata in ledger.get("patterns", {}).items():
                debt = PatternEvidenceDebt(
                    pattern_id=pid,
                    total_findings=pdata.get("total_findings", 0),
                    strong_evidence_count=pdata.get("strong_evidence_count", 0),
                    medium_evidence_count=pdata.get("medium_evidence_count", 0),
                    weak_evidence_count=pdata.get("weak_evidence_count", 0),
                    unknown_evidence_count=pdata.get("unknown_evidence_count", 0),
                )
                # Note: We don't reload individual entries for performance
                self.pattern_debts[pid] = debt
        except Exception:
            pass


# =============================================================================
# Plausibility Scoring (Phase 7.2 Innovation I6)
# =============================================================================

@dataclass
class PlausibilityFactors:
    """Factors that contribute to exploit plausibility score.

    Per Phase 7.2 CONTEXT (I6):
    - Score factors: liquidity depth, capital requirement, time window, access barrier
    - Score never affects correctness, only ordering and review priority
    """
    liquidity_depth: float = 0.5       # 0-1: higher = more liquid, easier to exploit
    capital_requirement: float = 0.5    # 0-1: higher = less capital needed
    time_window: float = 0.5           # 0-1: higher = longer window
    access_barrier: float = 0.5        # 0-1: higher = lower barrier
    complexity: float = 0.5            # 0-1: higher = less complex attack

    def __post_init__(self):
        # Clamp all values to [0, 1]
        self.liquidity_depth = max(0.0, min(1.0, self.liquidity_depth))
        self.capital_requirement = max(0.0, min(1.0, self.capital_requirement))
        self.time_window = max(0.0, min(1.0, self.time_window))
        self.access_barrier = max(0.0, min(1.0, self.access_barrier))
        self.complexity = max(0.0, min(1.0, self.complexity))


@dataclass
class PlausibilityScore:
    """Plausibility score for a finding.

    IMPORTANT: This score is for PRIORITIZATION ONLY.
    It NEVER hides or suppresses findings.
    """
    finding_id: str
    pattern_id: str
    score: float                       # 0-1 composite score
    factors: PlausibilityFactors
    confidence: float = 0.5            # 0-1: how confident we are in the score
    severity_boost: float = 0.0        # Boost for critical/high severity
    computed_at: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.computed_at:
            self.computed_at = datetime.utcnow().isoformat()
        # Ensure score stays in [0, 1]
        self.score = max(0.0, min(1.0, self.score))

    @property
    def priority_tier(self) -> str:
        """Map score to priority tier for review ordering."""
        if self.score >= 0.8:
            return "P0"  # Immediate review
        elif self.score >= 0.6:
            return "P1"  # High priority
        elif self.score >= 0.4:
            return "P2"  # Normal priority
        else:
            return "P3"  # Lower priority (still reviewed!)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "pattern_id": self.pattern_id,
            "score": round(self.score, 3),
            "priority_tier": self.priority_tier,
            "confidence": round(self.confidence, 3),
            "severity_boost": round(self.severity_boost, 3),
            "computed_at": self.computed_at,
            "notes": self.notes,
            "factors": {
                "liquidity_depth": round(self.factors.liquidity_depth, 3),
                "capital_requirement": round(self.factors.capital_requirement, 3),
                "time_window": round(self.factors.time_window, 3),
                "access_barrier": round(self.factors.access_barrier, 3),
                "complexity": round(self.factors.complexity, 3),
            },
        }


class PlausibilityScorer:
    """Computes exploit plausibility scores for findings.

    Per Phase 7.2 CONTEXT (I6):
    - Score is for ordering only - never hides findings
    - Factors: liquidity depth, capital requirement, time window, access barrier

    Output: .vrs/corpus/metadata/plausibility_scores.yaml
    """

    # Factor weights (sum to 1.0)
    WEIGHTS = {
        "liquidity_depth": 0.20,
        "capital_requirement": 0.25,
        "time_window": 0.15,
        "access_barrier": 0.20,
        "complexity": 0.20,
    }

    # Severity boosts
    SEVERITY_BOOSTS = {
        "critical": 0.15,
        "high": 0.10,
        "medium": 0.05,
        "low": 0.0,
        "info": 0.0,
    }

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize plausibility scorer.

        Args:
            storage_path: Path to plausibility_scores.yaml. Defaults to
                .vrs/corpus/metadata/plausibility_scores.yaml
        """
        self.storage_path = storage_path or Path(".vrs/corpus/metadata/plausibility_scores.yaml")
        self.scores: Dict[str, PlausibilityScore] = {}  # finding_id -> score

        if self.storage_path.exists():
            self._load()

    def compute_score(
        self,
        finding_id: str,
        pattern_id: str,
        severity: str = "medium",
        factors: Optional[PlausibilityFactors] = None,
        notes: str = "",
    ) -> PlausibilityScore:
        """Compute plausibility score for a finding.

        Args:
            finding_id: Unique finding identifier
            pattern_id: Pattern that produced the finding
            severity: Finding severity level
            factors: Optional pre-computed factors (defaults computed otherwise)
            notes: Additional notes

        Returns:
            PlausibilityScore for the finding
        """
        if factors is None:
            factors = PlausibilityFactors()

        # Compute weighted score
        base_score = (
            factors.liquidity_depth * self.WEIGHTS["liquidity_depth"] +
            factors.capital_requirement * self.WEIGHTS["capital_requirement"] +
            factors.time_window * self.WEIGHTS["time_window"] +
            factors.access_barrier * self.WEIGHTS["access_barrier"] +
            factors.complexity * self.WEIGHTS["complexity"]
        )

        # Apply severity boost
        severity_boost = self.SEVERITY_BOOSTS.get(severity.lower(), 0.0)
        final_score = min(1.0, base_score + severity_boost)

        # Confidence based on how many non-default factors we have
        factor_values = [
            factors.liquidity_depth,
            factors.capital_requirement,
            factors.time_window,
            factors.access_barrier,
            factors.complexity,
        ]
        non_default = sum(1 for v in factor_values if v != 0.5)
        confidence = 0.3 + (non_default / 5) * 0.7  # 30% base, up to 100%

        score = PlausibilityScore(
            finding_id=finding_id,
            pattern_id=pattern_id,
            score=final_score,
            factors=factors,
            confidence=confidence,
            severity_boost=severity_boost,
            notes=notes,
        )

        self.scores[finding_id] = score
        return score

    def get_score(self, finding_id: str) -> Optional[PlausibilityScore]:
        """Get plausibility score for a finding."""
        return self.scores.get(finding_id)

    def get_prioritized_findings(self) -> List[str]:
        """Get finding IDs sorted by plausibility score (highest first)."""
        return sorted(
            self.scores.keys(),
            key=lambda fid: self.scores[fid].score,
            reverse=True,
        )

    def get_by_priority_tier(self, tier: str) -> List[str]:
        """Get findings in a specific priority tier."""
        return [
            fid for fid, score in self.scores.items()
            if score.priority_tier == tier
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of plausibility scores."""
        if not self.scores:
            return {
                "total_scored": 0,
                "by_priority_tier": {},
                "avg_score": 0.0,
                "avg_confidence": 0.0,
            }

        by_tier: Dict[str, int] = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for score in self.scores.values():
            by_tier[score.priority_tier] += 1

        avg_score = sum(s.score for s in self.scores.values()) / len(self.scores)
        avg_confidence = sum(s.confidence for s in self.scores.values()) / len(self.scores)

        return {
            "total_scored": len(self.scores),
            "by_priority_tier": by_tier,
            "avg_score": round(avg_score, 3),
            "avg_confidence": round(avg_confidence, 3),
        }

    def save(self) -> Path:
        """Save plausibility scores to YAML."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "plausibility_scores": {
                "generated_at": datetime.utcnow().isoformat(),
                "summary": self.get_summary(),
                "note": "Scores are for PRIORITIZATION ONLY - they NEVER hide findings",
                "scores": {
                    fid: score.to_dict()
                    for fid, score in self.scores.items()
                },
            }
        }

        self.storage_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        return self.storage_path

    def _load(self) -> None:
        """Load plausibility scores from YAML."""
        try:
            data = yaml.safe_load(self.storage_path.read_text())
            if not data or "plausibility_scores" not in data:
                return

            scores_data = data["plausibility_scores"].get("scores", {})
            for fid, sdata in scores_data.items():
                factors = PlausibilityFactors(
                    liquidity_depth=sdata.get("factors", {}).get("liquidity_depth", 0.5),
                    capital_requirement=sdata.get("factors", {}).get("capital_requirement", 0.5),
                    time_window=sdata.get("factors", {}).get("time_window", 0.5),
                    access_barrier=sdata.get("factors", {}).get("access_barrier", 0.5),
                    complexity=sdata.get("factors", {}).get("complexity", 0.5),
                )
                score = PlausibilityScore(
                    finding_id=fid,
                    pattern_id=sdata.get("pattern_id", ""),
                    score=sdata.get("score", 0.5),
                    factors=factors,
                    confidence=sdata.get("confidence", 0.5),
                    severity_boost=sdata.get("severity_boost", 0.0),
                    computed_at=sdata.get("computed_at", ""),
                    notes=sdata.get("notes", ""),
                )
                self.scores[fid] = score
        except Exception:
            pass


# =============================================================================
# Context TTL Decay (Phase 7.2 Innovation I5)
# =============================================================================

@dataclass
class ContextTTLEntry:
    """TTL tracking entry for an economic context field.

    Per Phase 7.2 CONTEXT (I5):
    - 30-day default TTL for economic context fields
    - Expired context decays to "unknown" (never "safe")
    """
    field_path: str                    # e.g., "protocol.tvl" or "oracle.price_source"
    value: Any
    source_id: str                     # Source document/reference
    source_date: str                   # When the source was published
    last_verified: str                 # When we last verified this
    expires_at: str                    # TTL expiration
    status: str = "active"             # active, expired, unknown
    decay_reason: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """Check if the context field has expired."""
        if not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.now(expires.tzinfo or None) > expires
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_path": self.field_path,
            "value": self.value,
            "source_id": self.source_id,
            "source_date": self.source_date,
            "last_verified": self.last_verified,
            "expires_at": self.expires_at,
            "status": self.status,
            "decay_reason": self.decay_reason,
            "is_expired": self.is_expired,
        }


class ContextTTLManager:
    """Manages TTL and decay for economic context fields.

    Per Phase 7.2 CONTEXT (I5):
    - Every economic-context field gets a 30-day TTL
    - Expired fields decay to "unknown" (never "safe")
    - This applies in validation/ingestion pipeline, not detection

    Output: .vrs/context/context_ttl.yaml
    """

    DEFAULT_TTL_DAYS = 30

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize context TTL manager.

        Args:
            storage_path: Path to context_ttl.yaml. Defaults to
                .vrs/context/context_ttl.yaml
        """
        self.storage_path = storage_path or Path(".vrs/context/context_ttl.yaml")
        self.entries: Dict[str, ContextTTLEntry] = {}  # field_path -> entry
        self.decay_log: List[Dict[str, Any]] = []  # Log of decay events

        if self.storage_path.exists():
            self._load()

    def register_context_field(
        self,
        field_path: str,
        value: Any,
        source_id: str,
        source_date: Optional[str] = None,
        ttl_days: Optional[int] = None,
    ) -> ContextTTLEntry:
        """Register a context field with TTL.

        Args:
            field_path: Dotted path to the field (e.g., "protocol.tvl")
            value: Current value of the field
            source_id: Source document/reference
            source_date: When the source was published (defaults to now)
            ttl_days: TTL in days (defaults to 30)

        Returns:
            ContextTTLEntry for the field
        """
        now = datetime.utcnow()
        ttl = ttl_days or self.DEFAULT_TTL_DAYS

        source_date = source_date or now.isoformat()
        expires_at = (now + timedelta(days=ttl)).isoformat()

        entry = ContextTTLEntry(
            field_path=field_path,
            value=value,
            source_id=source_id,
            source_date=source_date,
            last_verified=now.isoformat(),
            expires_at=expires_at,
            status="active",
        )

        self.entries[field_path] = entry
        return entry

    def refresh_field(
        self,
        field_path: str,
        new_value: Optional[Any] = None,
        new_source_id: Optional[str] = None,
        ttl_days: Optional[int] = None,
    ) -> Optional[ContextTTLEntry]:
        """Refresh a context field, extending its TTL.

        Args:
            field_path: Field to refresh
            new_value: Optional new value
            new_source_id: Optional new source
            ttl_days: New TTL (defaults to 30)

        Returns:
            Updated entry or None if field not found
        """
        entry = self.entries.get(field_path)
        if entry is None:
            return None

        now = datetime.utcnow()
        ttl = ttl_days or self.DEFAULT_TTL_DAYS

        if new_value is not None:
            entry.value = new_value
        if new_source_id:
            entry.source_id = new_source_id
            entry.source_date = now.isoformat()

        entry.last_verified = now.isoformat()
        entry.expires_at = (now + timedelta(days=ttl)).isoformat()
        entry.status = "active"
        entry.decay_reason = None

        return entry

    def check_and_decay_expired(self) -> List[str]:
        """Check all fields and decay expired ones to unknown.

        Returns:
            List of field paths that were decayed
        """
        decayed: List[str] = []
        now = datetime.utcnow()

        for field_path, entry in self.entries.items():
            if entry.status == "expired":
                continue

            if entry.is_expired:
                entry.status = "unknown"  # Decay to unknown, NEVER "safe"
                entry.decay_reason = f"TTL expired at {entry.expires_at}"
                decayed.append(field_path)

                # Log the decay event
                self.decay_log.append({
                    "field_path": field_path,
                    "decayed_at": now.isoformat(),
                    "previous_status": "active",
                    "new_status": "unknown",
                    "reason": entry.decay_reason,
                    "value_at_decay": entry.value,
                })

        return decayed

    def get_expired_fields(self) -> List[str]:
        """Get list of expired field paths."""
        return [
            fp for fp, entry in self.entries.items()
            if entry.is_expired or entry.status in ("expired", "unknown")
        ]

    def get_active_fields(self) -> List[str]:
        """Get list of active (non-expired) field paths."""
        return [
            fp for fp, entry in self.entries.items()
            if entry.status == "active" and not entry.is_expired
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of context TTL status."""
        total = len(self.entries)
        active = len(self.get_active_fields())
        expired = len(self.get_expired_fields())

        return {
            "total_fields": total,
            "active_fields": active,
            "expired_fields": expired,
            "decay_events": len(self.decay_log),
            "default_ttl_days": self.DEFAULT_TTL_DAYS,
        }

    def save(self) -> Path:
        """Save context TTL data to YAML."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "context_ttl": {
                "generated_at": datetime.utcnow().isoformat(),
                "summary": self.get_summary(),
                "note": "Expired fields decay to 'unknown', NEVER to 'safe'",
                "entries": {
                    fp: entry.to_dict()
                    for fp, entry in self.entries.items()
                },
                "decay_log": self.decay_log,
            }
        }

        self.storage_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        return self.storage_path

    def _load(self) -> None:
        """Load context TTL data from YAML."""
        try:
            data = yaml.safe_load(self.storage_path.read_text())
            if not data or "context_ttl" not in data:
                return

            ttl_data = data["context_ttl"]
            for fp, edata in ttl_data.get("entries", {}).items():
                entry = ContextTTLEntry(
                    field_path=fp,
                    value=edata.get("value"),
                    source_id=edata.get("source_id", ""),
                    source_date=edata.get("source_date", ""),
                    last_verified=edata.get("last_verified", ""),
                    expires_at=edata.get("expires_at", ""),
                    status=edata.get("status", "unknown"),
                    decay_reason=edata.get("decay_reason"),
                )
                self.entries[fp] = entry

            self.decay_log = ttl_data.get("decay_log", [])
        except Exception:
            pass


class CompilationStatus(str, Enum):
    """Status of scaffold compilation attempt."""
    NOT_ATTEMPTED = "not_attempted"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ExecutionStatus(str, Enum):
    """Status of test execution attempt."""
    NOT_ATTEMPTED = "not_attempted"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ScaffoldQualityRecord:
    """
    Quality record for a generated scaffold.

    Tracks compilation and execution attempts to measure real success rates.
    """
    scaffold_id: str
    finding_id: str
    tier: int
    generated_at: datetime
    filename: str
    confidence: float

    # Compilation tracking
    compilation_status: CompilationStatus = CompilationStatus.NOT_ATTEMPTED
    compilation_error: Optional[str] = None
    compilation_attempts: int = 0

    # Execution tracking
    execution_status: ExecutionStatus = ExecutionStatus.NOT_ATTEMPTED
    execution_error: Optional[str] = None
    execution_attempts: int = 0

    # Fallback tracking
    fell_back_from_tier: Optional[int] = None
    fallback_reason: Optional[str] = None

    def record_compilation_attempt(
        self,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record a compilation attempt."""
        self.compilation_attempts += 1
        if success:
            self.compilation_status = CompilationStatus.SUCCESS
            self.compilation_error = None
        else:
            self.compilation_status = CompilationStatus.FAILED
            self.compilation_error = error

    def record_execution_attempt(
        self,
        status: ExecutionStatus,
        error: Optional[str] = None,
    ) -> None:
        """Record a test execution attempt."""
        self.execution_attempts += 1
        self.execution_status = status
        if error:
            self.execution_error = error

    @property
    def compiled_successfully(self) -> bool:
        """Check if scaffold compiled successfully."""
        return self.compilation_status == CompilationStatus.SUCCESS

    @property
    def executed_successfully(self) -> bool:
        """Check if test executed successfully."""
        return self.execution_status in (ExecutionStatus.PASSED, ExecutionStatus.FAILED)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scaffold_id": self.scaffold_id,
            "finding_id": self.finding_id,
            "tier": self.tier,
            "generated_at": self.generated_at.isoformat(),
            "filename": self.filename,
            "confidence": self.confidence,
            "compilation_status": self.compilation_status.value,
            "compilation_error": self.compilation_error,
            "compilation_attempts": self.compilation_attempts,
            "execution_status": self.execution_status.value,
            "execution_error": self.execution_error,
            "execution_attempts": self.execution_attempts,
            "fell_back_from_tier": self.fell_back_from_tier,
            "fallback_reason": self.fallback_reason,
        }


@dataclass
class QualityMetrics:
    """
    Aggregate quality metrics for scaffolding.

    Tracks success rates to validate against tier targets.
    """
    total_generated: int = 0
    tier1_generated: int = 0
    tier2_generated: int = 0
    tier3_generated: int = 0

    # Compilation metrics
    compilation_attempts: int = 0
    compilation_successes: int = 0

    # Execution metrics
    execution_attempts: int = 0
    execution_successes: int = 0

    # Fallback metrics
    fallback_count: int = 0

    @property
    def compile_rate(self) -> float:
        """Calculate overall compile rate."""
        if self.compilation_attempts == 0:
            return 0.0
        return self.compilation_successes / self.compilation_attempts

    @property
    def execution_rate(self) -> float:
        """Calculate overall execution rate."""
        if self.execution_attempts == 0:
            return 0.0
        return self.execution_successes / self.execution_attempts

    @property
    def tier2_compile_rate(self) -> float:
        """Calculate Tier 2 compile rate (the key metric)."""
        # This is what we track against the 30-40% target
        # In practice, need per-tier tracking which requires records
        return self.compile_rate

    def meets_tier_target(self, tier: TestTier) -> bool:
        """Check if metrics meet the tier's minimum target."""
        defn = TIER_DEFINITIONS[tier]
        if tier == TestTier.TIER_1_TEMPLATE:
            return True  # Tier 1 always succeeds as template
        elif tier == TestTier.TIER_2_SMART:
            return self.compile_rate >= defn.success_rate_minimum
        else:
            return self.execution_rate >= defn.success_rate_minimum

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_generated": self.total_generated,
            "tier1_generated": self.tier1_generated,
            "tier2_generated": self.tier2_generated,
            "tier3_generated": self.tier3_generated,
            "compilation_attempts": self.compilation_attempts,
            "compilation_successes": self.compilation_successes,
            "compile_rate": self.compile_rate,
            "execution_attempts": self.execution_attempts,
            "execution_successes": self.execution_successes,
            "execution_rate": self.execution_rate,
            "fallback_count": self.fallback_count,
        }


class QualityTracker:
    """
    Tracks scaffold generation quality over time.

    Maintains records of scaffold generation and results to calculate
    success rates and validate against tier targets.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize quality tracker.

        Args:
            storage_path: Optional path to persist quality data
        """
        self.storage_path = storage_path
        self.records: Dict[str, ScaffoldQualityRecord] = {}
        self.metrics = QualityMetrics()

        # Load existing data if available
        if storage_path and storage_path.exists():
            self._load()

    def record_generation(self, scaffold: TestScaffold) -> ScaffoldQualityRecord:
        """
        Record a scaffold generation.

        Args:
            scaffold: The generated scaffold

        Returns:
            Quality record for the scaffold
        """
        record = ScaffoldQualityRecord(
            scaffold_id=scaffold.filename,
            finding_id=scaffold.finding_id,
            tier=scaffold.tier,
            generated_at=datetime.now(),
            filename=scaffold.filename,
            confidence=scaffold.confidence,
        )

        self.records[scaffold.filename] = record

        # Update metrics
        self.metrics.total_generated += 1
        if scaffold.tier == 1:
            self.metrics.tier1_generated += 1
        elif scaffold.tier == 2:
            self.metrics.tier2_generated += 1
        else:
            self.metrics.tier3_generated += 1

        self._save()
        return record

    def record_compilation(
        self,
        scaffold_id: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a compilation attempt.

        Args:
            scaffold_id: ID of the scaffold
            success: Whether compilation succeeded
            error: Error message if failed
        """
        record = self.records.get(scaffold_id)
        if record:
            record.record_compilation_attempt(success, error)
            self.metrics.compilation_attempts += 1
            if success:
                self.metrics.compilation_successes += 1
            self._save()

    def record_execution(
        self,
        scaffold_id: str,
        status: ExecutionStatus,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a test execution attempt.

        Args:
            scaffold_id: ID of the scaffold
            status: Execution status
            error: Error message if failed
        """
        record = self.records.get(scaffold_id)
        if record:
            record.record_execution_attempt(status, error)
            self.metrics.execution_attempts += 1
            if status in (ExecutionStatus.PASSED, ExecutionStatus.FAILED):
                self.metrics.execution_successes += 1
            self._save()

    def record_fallback(
        self,
        scaffold_id: str,
        from_tier: int,
        reason: str,
    ) -> None:
        """
        Record a tier fallback.

        Args:
            scaffold_id: ID of the scaffold
            from_tier: Tier that failed
            reason: Reason for fallback
        """
        record = self.records.get(scaffold_id)
        if record:
            record.fell_back_from_tier = from_tier
            record.fallback_reason = reason
            self.metrics.fallback_count += 1
            self._save()

    def get_metrics(self) -> QualityMetrics:
        """Get current quality metrics."""
        return self.metrics

    def get_record(self, scaffold_id: str) -> Optional[ScaffoldQualityRecord]:
        """Get quality record for a scaffold."""
        return self.records.get(scaffold_id)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of quality tracking."""
        return {
            "metrics": self.metrics.to_dict(),
            "total_records": len(self.records),
            "tier_targets": {
                "tier1": "100% (template always generated)",
                "tier2_target": "30-40% compile rate",
                "tier2_minimum": "25% compile rate",
                "tier3_target": "10% execution rate",
            },
            "current_performance": {
                "compile_rate": f"{self.metrics.compile_rate:.1%}",
                "execution_rate": f"{self.metrics.execution_rate:.1%}",
                "meets_tier2_target": self.metrics.meets_tier_target(TestTier.TIER_2_SMART),
            },
        }

    def _save(self) -> None:
        """Save tracking data to disk."""
        if self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "records": {k: v.to_dict() for k, v in self.records.items()},
                "metrics": self.metrics.to_dict(),
            }
            self.storage_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        """Load tracking data from disk."""
        if self.storage_path and self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                # Reconstruct records and metrics
                # For simplicity, we load metrics directly
                metrics_data = data.get("metrics", {})
                self.metrics = QualityMetrics(
                    total_generated=metrics_data.get("total_generated", 0),
                    tier1_generated=metrics_data.get("tier1_generated", 0),
                    tier2_generated=metrics_data.get("tier2_generated", 0),
                    tier3_generated=metrics_data.get("tier3_generated", 0),
                    compilation_attempts=metrics_data.get("compilation_attempts", 0),
                    compilation_successes=metrics_data.get("compilation_successes", 0),
                    execution_attempts=metrics_data.get("execution_attempts", 0),
                    execution_successes=metrics_data.get("execution_successes", 0),
                    fallback_count=metrics_data.get("fallback_count", 0),
                )
            except (json.JSONDecodeError, OSError):
                pass  # Start fresh on error


def generate_with_fallback(
    finding: Finding,
    target_tier: TestTier = TestTier.TIER_2_SMART,
    project_config: Optional[ProjectConfig] = None,
    tracker: Optional[QualityTracker] = None,
) -> TestScaffold:
    """
    Generate scaffold with automatic fallback to lower tier on failure.

    Attempts to generate at target tier, falls back to Tier 1 if needed.

    Args:
        finding: The finding to generate test for
        target_tier: Target tier to attempt
        project_config: Optional project configuration
        tracker: Optional quality tracker

    Returns:
        TestScaffold (always returns something useful)
    """
    scaffold: Optional[TestScaffold] = None
    fallback_reason: Optional[str] = None

    # Try target tier first
    if target_tier == TestTier.TIER_2_SMART:
        try:
            scaffold = generate_tier2_scaffold(finding, project_config)

            # If scaffold has low confidence, fall back
            if scaffold.confidence < 0.2:
                fallback_reason = f"Low confidence: {scaffold.confidence:.0%}"
                scaffold = None

        except Exception as e:
            fallback_reason = f"Tier 2 generation failed: {e}"
            scaffold = None

    # Fall back to Tier 1 if needed
    if scaffold is None:
        scaffold = generate_tier1_scaffold(finding)

        # Record fallback
        if tracker and fallback_reason:
            record = tracker.record_generation(scaffold)
            tracker.record_fallback(
                scaffold.filename,
                from_tier=target_tier.value,
                reason=fallback_reason,
            )
        elif tracker:
            tracker.record_generation(scaffold)

    elif tracker:
        tracker.record_generation(scaffold)

    return scaffold


def batch_generate_with_quality(
    findings: List[Finding],
    target_tier: TestTier = TestTier.TIER_2_SMART,
    project_config: Optional[ProjectConfig] = None,
    tracker: Optional[QualityTracker] = None,
) -> List[TestScaffold]:
    """
    Generate scaffolds for multiple findings with quality tracking.

    Args:
        findings: List of findings
        target_tier: Target tier
        project_config: Optional project configuration
        tracker: Optional quality tracker

    Returns:
        List of generated scaffolds
    """
    scaffolds = []
    for finding in findings:
        scaffold = generate_with_fallback(
            finding,
            target_tier=target_tier,
            project_config=project_config,
            tracker=tracker,
        )
        scaffolds.append(scaffold)

    return scaffolds
