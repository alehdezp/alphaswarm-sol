"""Invariant registry for mined vs declared invariants.

Per 05.11-CONTEXT.md: Track invariants with their source (DECLARED, MINED, HYBRID)
and confidence scores. Enables automated invariant mining integration.

Key features:
- InvariantRecord: Individual invariant with source and confidence
- InvariantRegistry: Central registry for all protocol invariants
- Mined vs declared distinction for evidence gating
- would_prevent_exploits: Link invariants to known exploit IDs

Usage:
    from alphaswarm_sol.context.invariant_registry import (
        InvariantRegistry, InvariantRecord, InvariantSource
    )

    registry = InvariantRegistry()

    # Register a declared invariant (from docs)
    registry.register_declared(
        invariant_id="inv:supply:001",
        expression="totalSupply <= maxSupply",
        natural_language="Total supply must never exceed max supply",
        source_ref="whitepaper-v1.2",
        confidence=0.95
    )

    # Register a mined invariant (from trace analysis)
    registry.register_mined(
        invariant_id="inv:balance:002",
        expression="sum(balances) == totalSupply",
        natural_language="Sum of all balances equals total supply",
        mining_method="echidna",
        confidence=0.85
    )

    # Compare declared vs mined
    discrepancies = registry.compare_mined_vs_declared()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InvariantSource(Enum):
    """Source of an invariant.

    Per 05.11-CONTEXT.md: Distinguish between declared (authoritative),
    mined (discovered), and hybrid (both) invariants.
    """

    DECLARED = "declared"  # From official docs, specs, or governance
    MINED = "mined"  # Discovered through trace analysis, fuzzing
    HYBRID = "hybrid"  # Both declared and confirmed by mining


class InvariantCategory(Enum):
    """Invariant categories for classification."""

    SUPPLY = "supply"  # Token supply invariants
    BALANCE = "balance"  # Balance consistency
    ACCESS = "access"  # Access control invariants
    ECONOMIC = "economic"  # Economic constraints (ratios, caps)
    STATE = "state"  # State machine invariants
    SEQUENCE = "sequence"  # Operation ordering
    ARITHMETIC = "arithmetic"  # Arithmetic overflow/underflow


@dataclass
class InvariantRecord:
    """A single invariant with source and confidence tracking.

    Per 05.11-CONTEXT.md: Each invariant records its source (declared/mined/hybrid),
    confidence, and which known exploits it would prevent.

    Attributes:
        invariant_id: Unique identifier for this invariant
        expression: Formal/semi-formal expression (e.g., "totalSupply <= maxSupply")
        natural_language: Human-readable description
        source: How this invariant was discovered (declared/mined/hybrid)
        confidence: Confidence score 0.0-1.0
        category: Invariant category
        scope: Scope (protocol-wide, contract-specific, function-specific)
        would_prevent_exploits: List of known exploit IDs this would block
        source_ref: Reference to source document/trace
        mining_method: Mining method if mined (echidna, foundry, manual)
        validated_against_traces: Number of traces validated against
        created_at: When this record was created
        last_validated: When this invariant was last validated
        conflicts_with: List of conflicting invariant IDs
    """

    invariant_id: str
    expression: str
    natural_language: str
    source: InvariantSource = InvariantSource.DECLARED
    confidence: float = 0.5
    category: InvariantCategory = InvariantCategory.BALANCE
    scope: str = "contract-specific"
    would_prevent_exploits: List[str] = field(default_factory=list)
    source_ref: str = ""
    mining_method: str = ""
    validated_against_traces: int = 0
    created_at: str = ""
    last_validated: str = ""
    conflicts_with: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence range and initialize timestamps."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

        now = datetime.utcnow().isoformat() + "Z"
        if not self.created_at:
            self.created_at = now
        if not self.last_validated:
            self.last_validated = now

    @property
    def is_declared(self) -> bool:
        """Whether this invariant is declared (not purely mined)."""
        return self.source in (InvariantSource.DECLARED, InvariantSource.HYBRID)

    @property
    def is_mined(self) -> bool:
        """Whether this invariant was mined (not purely declared)."""
        return self.source in (InvariantSource.MINED, InvariantSource.HYBRID)

    @property
    def is_high_confidence(self) -> bool:
        """Whether this invariant has high confidence (>= 0.8)."""
        return self.confidence >= 0.8

    @property
    def has_exploit_prevention(self) -> bool:
        """Whether this invariant is known to prevent exploits."""
        return len(self.would_prevent_exploits) > 0

    @property
    def has_conflicts(self) -> bool:
        """Whether this invariant conflicts with others."""
        return len(self.conflicts_with) > 0

    def add_exploit_prevention(self, exploit_id: str) -> None:
        """Add an exploit ID that this invariant would prevent.

        Args:
            exploit_id: Exploit identifier
        """
        if exploit_id not in self.would_prevent_exploits:
            self.would_prevent_exploits.append(exploit_id)

    def add_conflict(self, other_invariant_id: str) -> None:
        """Mark conflict with another invariant.

        Args:
            other_invariant_id: Conflicting invariant ID
        """
        if other_invariant_id not in self.conflicts_with:
            self.conflicts_with.append(other_invariant_id)

    def upgrade_to_hybrid(self) -> None:
        """Upgrade this invariant to HYBRID if it was only declared or mined."""
        if self.source in (InvariantSource.DECLARED, InvariantSource.MINED):
            self.source = InvariantSource.HYBRID

    def validate_trace(self, passed: bool) -> None:
        """Record a trace validation result.

        Args:
            passed: Whether the trace validated successfully
        """
        self.validated_against_traces += 1
        self.last_validated = datetime.utcnow().isoformat() + "Z"

        # Adjust confidence based on validation
        if passed:
            self.confidence = min(1.0, self.confidence + 0.02)
        else:
            self.confidence = max(0.0, self.confidence - 0.1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "invariant_id": self.invariant_id,
            "expression": self.expression,
            "natural_language": self.natural_language,
            "source": self.source.value,
            "confidence": self.confidence,
            "category": self.category.value,
            "scope": self.scope,
            "would_prevent_exploits": self.would_prevent_exploits,
            "source_ref": self.source_ref,
            "mining_method": self.mining_method,
            "validated_against_traces": self.validated_against_traces,
            "created_at": self.created_at,
            "last_validated": self.last_validated,
            "conflicts_with": self.conflicts_with,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvariantRecord":
        """Create InvariantRecord from dictionary."""
        source = data.get("source", "declared")
        if isinstance(source, str):
            source = InvariantSource(source)

        category = data.get("category", "balance")
        if isinstance(category, str):
            category = InvariantCategory(category)

        return cls(
            invariant_id=str(data.get("invariant_id", "")),
            expression=str(data.get("expression", "")),
            natural_language=str(data.get("natural_language", "")),
            source=source,
            confidence=float(data.get("confidence", 0.5)),
            category=category,
            scope=str(data.get("scope", "contract-specific")),
            would_prevent_exploits=list(data.get("would_prevent_exploits", [])),
            source_ref=str(data.get("source_ref", "")),
            mining_method=str(data.get("mining_method", "")),
            validated_against_traces=int(data.get("validated_against_traces", 0)),
            created_at=str(data.get("created_at", "")),
            last_validated=str(data.get("last_validated", "")),
            conflicts_with=list(data.get("conflicts_with", [])),
        )


@dataclass
class InvariantDiscrepancy:
    """A discrepancy between declared and mined invariants.

    Captures differences for human review.
    """

    discrepancy_type: str  # "missing_declared", "missing_mined", "conflict"
    declared_id: Optional[str] = None
    mined_id: Optional[str] = None
    description: str = ""
    severity: str = "medium"  # low, medium, high
    resolution_hint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "discrepancy_type": self.discrepancy_type,
            "declared_id": self.declared_id,
            "mined_id": self.mined_id,
            "description": self.description,
            "severity": self.severity,
            "resolution_hint": self.resolution_hint,
        }


class InvariantRegistry:
    """Central registry for protocol invariants (mined and declared).

    Per 05.11-CONTEXT.md: Track all invariants with source attribution,
    enable comparison between declared and mined invariants, and
    link invariants to known exploits they would prevent.

    Usage:
        registry = InvariantRegistry()

        # Register invariants
        registry.register_declared("inv:001", "totalSupply <= maxSupply", ...)
        registry.register_mined("inv:002", "sum(balances) == totalSupply", ...)

        # Query invariants
        declared = registry.get_declared_invariants()
        mined = registry.get_mined_invariants()

        # Compare for discrepancies
        discrepancies = registry.compare_mined_vs_declared()

        # Validate against traces
        registry.validate_against_traces([trace1, trace2])
    """

    def __init__(self) -> None:
        """Initialize the invariant registry."""
        self._invariants: Dict[str, InvariantRecord] = {}
        self._by_category: Dict[InvariantCategory, List[str]] = {}
        self._by_scope: Dict[str, List[str]] = {}
        self._exploit_prevention_index: Dict[str, List[str]] = {}  # exploit_id -> invariant_ids

    def register_declared(
        self,
        invariant_id: str,
        expression: str,
        natural_language: str,
        source_ref: str,
        confidence: float = 0.9,
        category: InvariantCategory = InvariantCategory.BALANCE,
        scope: str = "contract-specific",
        would_prevent_exploits: Optional[List[str]] = None,
    ) -> InvariantRecord:
        """Register a declared invariant from documentation/specs.

        Args:
            invariant_id: Unique identifier
            expression: Formal expression
            natural_language: Human description
            source_ref: Reference to source document
            confidence: Confidence score
            category: Invariant category
            scope: Invariant scope
            would_prevent_exploits: Known exploits this would prevent

        Returns:
            Created InvariantRecord
        """
        record = InvariantRecord(
            invariant_id=invariant_id,
            expression=expression,
            natural_language=natural_language,
            source=InvariantSource.DECLARED,
            confidence=confidence,
            category=category,
            scope=scope,
            source_ref=source_ref,
            would_prevent_exploits=would_prevent_exploits or [],
        )

        self._add_record(record)
        return record

    def register_mined(
        self,
        invariant_id: str,
        expression: str,
        natural_language: str,
        mining_method: str,
        confidence: float = 0.7,
        category: InvariantCategory = InvariantCategory.BALANCE,
        scope: str = "contract-specific",
        validated_against_traces: int = 0,
    ) -> InvariantRecord:
        """Register a mined invariant from trace analysis.

        Args:
            invariant_id: Unique identifier
            expression: Formal expression
            natural_language: Human description
            mining_method: How this was mined (echidna, foundry, manual)
            confidence: Confidence score
            category: Invariant category
            scope: Invariant scope
            validated_against_traces: Number of traces validated

        Returns:
            Created InvariantRecord
        """
        record = InvariantRecord(
            invariant_id=invariant_id,
            expression=expression,
            natural_language=natural_language,
            source=InvariantSource.MINED,
            confidence=confidence,
            category=category,
            scope=scope,
            mining_method=mining_method,
            validated_against_traces=validated_against_traces,
        )

        self._add_record(record)
        return record

    def _add_record(self, record: InvariantRecord) -> None:
        """Add an invariant record to the registry.

        Args:
            record: InvariantRecord to add
        """
        # Check for existing record
        if record.invariant_id in self._invariants:
            existing = self._invariants[record.invariant_id]
            # If existing is declared and new is mined (or vice versa), upgrade to hybrid
            if (existing.source == InvariantSource.DECLARED and record.source == InvariantSource.MINED) or \
               (existing.source == InvariantSource.MINED and record.source == InvariantSource.DECLARED):
                existing.upgrade_to_hybrid()
                # Merge would_prevent_exploits
                for exploit in record.would_prevent_exploits:
                    existing.add_exploit_prevention(exploit)
                return

        self._invariants[record.invariant_id] = record

        # Update category index
        if record.category not in self._by_category:
            self._by_category[record.category] = []
        if record.invariant_id not in self._by_category[record.category]:
            self._by_category[record.category].append(record.invariant_id)

        # Update scope index
        if record.scope not in self._by_scope:
            self._by_scope[record.scope] = []
        if record.invariant_id not in self._by_scope[record.scope]:
            self._by_scope[record.scope].append(record.invariant_id)

        # Update exploit prevention index
        for exploit_id in record.would_prevent_exploits:
            if exploit_id not in self._exploit_prevention_index:
                self._exploit_prevention_index[exploit_id] = []
            if record.invariant_id not in self._exploit_prevention_index[exploit_id]:
                self._exploit_prevention_index[exploit_id].append(record.invariant_id)

    def get(self, invariant_id: str) -> Optional[InvariantRecord]:
        """Get an invariant by ID.

        Args:
            invariant_id: Invariant identifier

        Returns:
            InvariantRecord if found, None otherwise
        """
        return self._invariants.get(invariant_id)

    def get_all(self) -> List[InvariantRecord]:
        """Get all invariants.

        Returns:
            List of all InvariantRecord objects
        """
        return list(self._invariants.values())

    def get_declared_invariants(self) -> List[InvariantRecord]:
        """Get all declared invariants (including hybrids).

        Returns:
            List of declared InvariantRecord objects
        """
        return [inv for inv in self._invariants.values() if inv.is_declared]

    def get_mined_invariants(self) -> List[InvariantRecord]:
        """Get all mined invariants (including hybrids).

        Returns:
            List of mined InvariantRecord objects
        """
        return [inv for inv in self._invariants.values() if inv.is_mined]

    def get_by_category(self, category: InvariantCategory) -> List[InvariantRecord]:
        """Get invariants by category.

        Args:
            category: InvariantCategory to filter by

        Returns:
            List of InvariantRecord objects in this category
        """
        inv_ids = self._by_category.get(category, [])
        return [self._invariants[inv_id] for inv_id in inv_ids if inv_id in self._invariants]

    def get_by_scope(self, scope: str) -> List[InvariantRecord]:
        """Get invariants by scope.

        Args:
            scope: Scope string to filter by

        Returns:
            List of InvariantRecord objects in this scope
        """
        inv_ids = self._by_scope.get(scope, [])
        return [self._invariants[inv_id] for inv_id in inv_ids if inv_id in self._invariants]

    def get_preventing_exploit(self, exploit_id: str) -> List[InvariantRecord]:
        """Get invariants that would prevent a specific exploit.

        Args:
            exploit_id: Exploit identifier

        Returns:
            List of InvariantRecord objects that would prevent this exploit
        """
        inv_ids = self._exploit_prevention_index.get(exploit_id, [])
        return [self._invariants[inv_id] for inv_id in inv_ids if inv_id in self._invariants]

    def get_high_confidence_invariants(self, threshold: float = 0.8) -> List[InvariantRecord]:
        """Get high-confidence invariants.

        Args:
            threshold: Minimum confidence threshold

        Returns:
            List of high-confidence InvariantRecord objects
        """
        return [inv for inv in self._invariants.values() if inv.confidence >= threshold]

    def compare_mined_vs_declared(self) -> List[InvariantDiscrepancy]:
        """Compare mined vs declared invariants to find discrepancies.

        Per 05.11-CONTEXT.md: Detect discrepancies for human review.

        Returns:
            List of InvariantDiscrepancy objects
        """
        discrepancies = []

        declared = {inv.expression: inv for inv in self.get_declared_invariants() if inv.source == InvariantSource.DECLARED}
        mined = {inv.expression: inv for inv in self.get_mined_invariants() if inv.source == InvariantSource.MINED}

        # Find declared invariants not confirmed by mining
        for expr, inv in declared.items():
            if expr not in mined:
                discrepancies.append(InvariantDiscrepancy(
                    discrepancy_type="missing_mined",
                    declared_id=inv.invariant_id,
                    description=f"Declared invariant not confirmed by mining: {inv.natural_language}",
                    severity="medium",
                    resolution_hint="Run invariant mining to confirm or refute this invariant",
                ))

        # Find mined invariants not in declared docs
        for expr, inv in mined.items():
            if expr not in declared:
                discrepancies.append(InvariantDiscrepancy(
                    discrepancy_type="missing_declared",
                    mined_id=inv.invariant_id,
                    description=f"Mined invariant not in docs: {inv.natural_language}",
                    severity="low",
                    resolution_hint="Consider documenting this discovered invariant",
                ))

        # Find conflicts
        for inv in self._invariants.values():
            if inv.has_conflicts:
                for conflict_id in inv.conflicts_with:
                    discrepancies.append(InvariantDiscrepancy(
                        discrepancy_type="conflict",
                        declared_id=inv.invariant_id,
                        mined_id=conflict_id,
                        description=f"Invariant {inv.invariant_id} conflicts with {conflict_id}",
                        severity="high",
                        resolution_hint="Resolve conflict before trusting either invariant",
                    ))

        return discrepancies

    def validate_against_traces(
        self,
        traces: List[Dict[str, Any]],
        invariant_checker: Optional[callable] = None,
    ) -> Dict[str, int]:
        """Validate invariants against execution traces.

        Args:
            traces: List of execution trace dicts
            invariant_checker: Optional custom checker function

        Returns:
            Dict mapping invariant_id to pass count
        """
        results: Dict[str, int] = {}

        for inv in self._invariants.values():
            passed = 0
            for trace in traces:
                # Default checker: look for violations in trace
                if invariant_checker:
                    result = invariant_checker(inv.expression, trace)
                else:
                    # Simple default: check if expression appears in violations
                    violations = trace.get("violations", [])
                    result = inv.expression not in violations

                if result:
                    passed += 1
                    inv.validate_trace(True)
                else:
                    inv.validate_trace(False)

            results[inv.invariant_id] = passed

        return results

    def stats(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dict with counts and summaries
        """
        total = len(self._invariants)
        declared = len([i for i in self._invariants.values() if i.source == InvariantSource.DECLARED])
        mined = len([i for i in self._invariants.values() if i.source == InvariantSource.MINED])
        hybrid = len([i for i in self._invariants.values() if i.source == InvariantSource.HYBRID])
        high_conf = len(self.get_high_confidence_invariants())
        with_exploits = len([i for i in self._invariants.values() if i.has_exploit_prevention])

        return {
            "total_invariants": total,
            "declared": declared,
            "mined": mined,
            "hybrid": hybrid,
            "high_confidence": high_conf,
            "with_exploit_prevention": with_exploits,
            "categories": {cat.value: len(ids) for cat, ids in self._by_category.items()},
            "scopes": {scope: len(ids) for scope, ids in self._by_scope.items()},
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert registry to dictionary for serialization."""
        return {
            "invariants": {
                inv_id: inv.to_dict()
                for inv_id, inv in self._invariants.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvariantRegistry":
        """Create InvariantRegistry from dictionary."""
        registry = cls()

        for inv_id, inv_data in data.get("invariants", {}).items():
            record = InvariantRecord.from_dict(inv_data)
            registry._add_record(record)

        return registry


# Export all types
__all__ = [
    "InvariantSource",
    "InvariantCategory",
    "InvariantRecord",
    "InvariantDiscrepancy",
    "InvariantRegistry",
]
