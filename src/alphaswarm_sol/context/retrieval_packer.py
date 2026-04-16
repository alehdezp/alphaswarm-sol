"""Retrieval Packer for Compact Evidence Bundles (Phase 7.1.3-03).

Compacts evidence bundles using TOON format while preserving evidence-first
traceability. Designed to reduce token footprint without losing:
- Exact code locations (file path + line anchors)
- Risk scores
- Evidence IDs

Usage:
    from alphaswarm_sol.context.retrieval_packer import (
        RetrievalPacker,
        PackedEvidenceBundle,
        EvidenceItem,
    )

    packer = RetrievalPacker(max_tokens=3000)

    # Pack evidence items
    items = [
        EvidenceItem(
            evidence_id="E-ABC123",
            file_path="contracts/Vault.sol",
            line_start=45,
            line_end=52,
            code_snippet="function withdraw() {...}",
            risk_score=0.85,
            operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
            metadata={"pattern": "reentrancy-classic"},
        ),
    ]

    packed = packer.pack(items)
    print(packed.toon_output)  # Compact TOON string

    # Unpack to verify fidelity
    unpacked = packer.unpack(packed.toon_output)
    assert unpacked[0].evidence_id == "E-ABC123"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import toons


def _toon_preprocess(obj: Any) -> Any:
    """Pre-process object for TOON encoding (avoid circular import).

    Handles datetime, Path, and objects with to_dict() method.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _toon_preprocess(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_toon_preprocess(item) for item in obj]
    if hasattr(obj, "to_dict"):
        return _toon_preprocess(obj.to_dict())
    raise TypeError(f"Object of type {type(obj).__name__} is not TOON serializable")


def toon_dumps(obj: Any) -> str:
    """Encode to TOON string (local to avoid circular import)."""
    return toons.dumps(_toon_preprocess(obj))


def toon_loads(s: str) -> Any:
    """Decode TOON string (local to avoid circular import)."""
    return toons.loads(s)


# Evidence ID patterns for validation
EVIDENCE_ID_PATTERNS = [
    re.compile(r"E-[A-Z0-9]{6,}"),       # E-ABCDEF style
    re.compile(r"EV-[a-f0-9]{8,}"),       # EV-hexhash style
    re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}"),  # UUID partial
]


@dataclass
class EvidenceItem:
    """Single evidence item with code location and risk signal.

    Attributes:
        evidence_id: Unique identifier (must be preserved)
        file_path: Path to source file
        line_start: Starting line number
        line_end: Ending line number (same as start if single line)
        code_snippet: Source code text (may be trimmed for budget)
        risk_score: Risk score 0.0-1.0
        operations: Semantic operations involved
        metadata: Additional metadata (pattern, vulnerability class, etc.)
        node_id: Optional graph node ID
    """

    evidence_id: str
    file_path: str
    line_start: int
    line_end: int = 0
    code_snippet: str = ""
    risk_score: float = 0.0
    operations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    node_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Set line_end to line_start if not specified."""
        if self.line_end == 0:
            self.line_end = self.line_start

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: Dict[str, Any] = {
            "id": self.evidence_id,
            "file": self.file_path,
            "lines": [self.line_start, self.line_end],
            "risk": self.risk_score,
        }
        if self.code_snippet:
            result["code"] = self.code_snippet
        if self.operations:
            result["ops"] = self.operations
        if self.metadata:
            result["meta"] = self.metadata
        if self.node_id:
            result["node"] = self.node_id
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceItem":
        """Create from dictionary."""
        lines = data.get("lines", [0, 0])
        line_start = lines[0] if lines else 0
        line_end = lines[1] if len(lines) > 1 else line_start

        return cls(
            evidence_id=data.get("id", ""),
            file_path=data.get("file", ""),
            line_start=line_start,
            line_end=line_end,
            code_snippet=data.get("code", ""),
            risk_score=float(data.get("risk", 0.0)),
            operations=list(data.get("ops", [])),
            metadata=dict(data.get("meta", {})),
            node_id=data.get("node"),
        )

    @property
    def location_anchor(self) -> str:
        """Human-readable location anchor (file:lines)."""
        if self.line_start == self.line_end:
            return f"{self.file_path}:{self.line_start}"
        return f"{self.file_path}:{self.line_start}-{self.line_end}"


@dataclass
class PackedEvidenceBundle:
    """Packed evidence bundle with TOON output and metadata.

    Attributes:
        toon_output: Compact TOON-encoded string
        evidence_ids: List of evidence IDs preserved in bundle
        total_items: Number of items in bundle
        estimated_tokens: Estimated token count
        trimmed_items: Number of items that had code snippets trimmed
        metadata: Bundle-level metadata
    """

    toon_output: str
    evidence_ids: List[str] = field(default_factory=list)
    total_items: int = 0
    estimated_tokens: int = 0
    trimmed_items: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "toon_output": self.toon_output,
            "evidence_ids": self.evidence_ids,
            "total_items": self.total_items,
            "estimated_tokens": self.estimated_tokens,
            "trimmed_items": self.trimmed_items,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackedEvidenceBundle":
        """Create from dictionary."""
        return cls(
            toon_output=data.get("toon_output", ""),
            evidence_ids=list(data.get("evidence_ids", [])),
            total_items=data.get("total_items", 0),
            estimated_tokens=data.get("estimated_tokens", 0),
            trimmed_items=data.get("trimmed_items", 0),
            metadata=dict(data.get("metadata", {})),
        )


class RetrievalPacker:
    """Pack evidence bundles into compact TOON format.

    Compacts evidence while preserving:
    1. Evidence IDs (always preserved, never trimmed)
    2. Code locations (file path + line anchors)
    3. Risk scores
    4. Operation sequences

    Code snippets are trimmed first when budget constraints apply.

    Usage:
        packer = RetrievalPacker(max_tokens=3000)

        # Pack with budget
        packed = packer.pack(evidence_items)

        # Unpack for verification
        unpacked = packer.unpack(packed.toon_output)

        # Pack with custom budget
        packed = packer.pack(evidence_items, max_bytes=8000)
    """

    # Token estimation: ~4 chars per token (consistent with context_budget.py)
    CHARS_PER_TOKEN = 4

    # Maximum code snippet length before trimming (chars)
    MAX_SNIPPET_CHARS = 500

    # Envelope fields (minimal metadata)
    ENVELOPE_VERSION = "1.0"

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        max_bytes: Optional[int] = None,
        trim_snippets: bool = True,
    ):
        """Initialize retrieval packer.

        Args:
            max_tokens: Maximum tokens for output (default 3000)
            max_bytes: Maximum bytes for output (overrides max_tokens if set)
            trim_snippets: Whether to trim code snippets to fit budget
        """
        self._max_tokens = max_tokens or 3000
        self._max_bytes = max_bytes
        self._trim_snippets = trim_snippets

    @property
    def max_tokens(self) -> int:
        """Maximum tokens allowed."""
        if self._max_bytes:
            return self._max_bytes // self.CHARS_PER_TOKEN
        return self._max_tokens

    @property
    def max_bytes(self) -> int:
        """Maximum bytes allowed."""
        if self._max_bytes:
            return self._max_bytes
        return self._max_tokens * self.CHARS_PER_TOKEN

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // self.CHARS_PER_TOKEN

    def pack(
        self,
        items: List[EvidenceItem],
        max_tokens: Optional[int] = None,
        max_bytes: Optional[int] = None,
        bundle_metadata: Optional[Dict[str, Any]] = None,
    ) -> PackedEvidenceBundle:
        """Pack evidence items into compact TOON format.

        Preserves evidence IDs and code locations. Trims code snippets
        if needed to fit within budget constraints.

        Args:
            items: Evidence items to pack
            max_tokens: Override max tokens for this pack call
            max_bytes: Override max bytes for this pack call
            bundle_metadata: Optional metadata to include in bundle

        Returns:
            PackedEvidenceBundle with TOON output
        """
        if not items:
            return PackedEvidenceBundle(
                toon_output="",
                evidence_ids=[],
                total_items=0,
                estimated_tokens=0,
                trimmed_items=0,
                metadata=bundle_metadata or {},
            )

        # Determine budget for this call
        effective_max_bytes = max_bytes or self._max_bytes
        effective_max_tokens = max_tokens or self._max_tokens

        if effective_max_bytes:
            budget_bytes = effective_max_bytes
        else:
            budget_bytes = effective_max_tokens * self.CHARS_PER_TOKEN

        # Build evidence data structure
        evidence_ids: List[str] = []
        evidence_data: List[Dict[str, Any]] = []
        trimmed_count = 0

        for item in items:
            evidence_ids.append(item.evidence_id)
            item_dict = item.to_dict()

            # Trim code snippet if needed and allowed
            if self._trim_snippets and item_dict.get("code"):
                snippet = item_dict["code"]
                if len(snippet) > self.MAX_SNIPPET_CHARS:
                    item_dict["code"] = snippet[: self.MAX_SNIPPET_CHARS] + "..."
                    trimmed_count += 1

            evidence_data.append(item_dict)

        # Build envelope with minimal metadata
        envelope: Dict[str, Any] = {
            "v": self.ENVELOPE_VERSION,
            "n": len(items),
            "ev": evidence_data,
        }

        if bundle_metadata:
            envelope["meta"] = bundle_metadata

        # Serialize to TOON
        toon_output = toon_dumps(envelope)

        # Check if within budget
        output_bytes = len(toon_output)
        if output_bytes > budget_bytes:
            # Need more aggressive trimming
            toon_output, trimmed_count = self._trim_to_budget(
                envelope, evidence_data, budget_bytes
            )
            output_bytes = len(toon_output)

        return PackedEvidenceBundle(
            toon_output=toon_output,
            evidence_ids=evidence_ids,
            total_items=len(items),
            estimated_tokens=self.estimate_tokens(toon_output),
            trimmed_items=trimmed_count,
            metadata=bundle_metadata or {},
        )

    def _trim_to_budget(
        self,
        envelope: Dict[str, Any],
        evidence_data: List[Dict[str, Any]],
        budget_bytes: int,
    ) -> Tuple[str, int]:
        """Trim evidence data to fit within budget.

        Trimming priority (first to be cut):
        1. Code snippets (truncated or removed)
        2. Metadata (removed)
        3. Operations (removed if desperate)

        Never removes: evidence IDs, file paths, line numbers, risk scores.

        Args:
            envelope: Full envelope dict
            evidence_data: List of evidence item dicts
            budget_bytes: Maximum bytes

        Returns:
            Tuple of (toon_output, trimmed_count)
        """
        trimmed_count = 0

        # Step 1: Truncate code snippets more aggressively
        for item in evidence_data:
            if "code" in item:
                snippet = item["code"]
                if len(snippet) > 200:
                    item["code"] = snippet[:200] + "..."
                    trimmed_count += 1

        envelope["ev"] = evidence_data
        toon_output = toon_dumps(envelope)

        if len(toon_output) <= budget_bytes:
            return toon_output, trimmed_count

        # Step 2: Remove code snippets entirely
        for item in evidence_data:
            if "code" in item:
                del item["code"]
                trimmed_count += 1

        envelope["ev"] = evidence_data
        toon_output = toon_dumps(envelope)

        if len(toon_output) <= budget_bytes:
            return toon_output, trimmed_count

        # Step 3: Remove metadata
        for item in evidence_data:
            if "meta" in item:
                del item["meta"]

        envelope["ev"] = evidence_data
        if "meta" in envelope:
            del envelope["meta"]

        toon_output = toon_dumps(envelope)

        if len(toon_output) <= budget_bytes:
            return toon_output, trimmed_count

        # Step 4: Remove operations (last resort)
        for item in evidence_data:
            if "ops" in item:
                del item["ops"]

        envelope["ev"] = evidence_data
        toon_output = toon_dumps(envelope)

        return toon_output, trimmed_count

    def unpack(self, toon_output: str) -> List[EvidenceItem]:
        """Unpack TOON output back to evidence items.

        Used for testing and verification of fidelity.

        Args:
            toon_output: TOON-encoded string from pack()

        Returns:
            List of EvidenceItem objects
        """
        if not toon_output:
            return []

        envelope = toon_loads(toon_output)

        if not isinstance(envelope, dict):
            return []

        evidence_data = envelope.get("ev", [])

        items: List[EvidenceItem] = []
        for item_dict in evidence_data:
            items.append(EvidenceItem.from_dict(item_dict))

        return items

    def validate_preservation(
        self,
        original: List[EvidenceItem],
        packed: PackedEvidenceBundle,
    ) -> Tuple[bool, List[str]]:
        """Validate that critical evidence data was preserved.

        Checks that evidence IDs, file paths, line numbers, and risk scores
        are intact after packing/unpacking.

        Args:
            original: Original evidence items
            packed: Packed bundle

        Returns:
            Tuple of (all_preserved: bool, issues: List[str])
        """
        issues: List[str] = []

        # Check evidence ID count
        if len(packed.evidence_ids) != len(original):
            issues.append(
                f"Evidence ID count mismatch: {len(packed.evidence_ids)} vs {len(original)}"
            )

        # Check all original IDs are present
        original_ids = {item.evidence_id for item in original}
        packed_ids = set(packed.evidence_ids)

        missing_ids = original_ids - packed_ids
        if missing_ids:
            issues.append(f"Missing evidence IDs: {missing_ids}")

        # Unpack and verify fidelity
        unpacked = self.unpack(packed.toon_output)

        if len(unpacked) != len(original):
            issues.append(
                f"Unpacked item count mismatch: {len(unpacked)} vs {len(original)}"
            )

        # Check each item's critical fields
        original_by_id = {item.evidence_id: item for item in original}
        for unpacked_item in unpacked:
            if unpacked_item.evidence_id not in original_by_id:
                issues.append(f"Unknown evidence ID in unpacked: {unpacked_item.evidence_id}")
                continue

            orig = original_by_id[unpacked_item.evidence_id]

            # File path must match
            if unpacked_item.file_path != orig.file_path:
                issues.append(
                    f"File path mismatch for {orig.evidence_id}: "
                    f"{unpacked_item.file_path} vs {orig.file_path}"
                )

            # Line numbers must match
            if unpacked_item.line_start != orig.line_start:
                issues.append(
                    f"Line start mismatch for {orig.evidence_id}: "
                    f"{unpacked_item.line_start} vs {orig.line_start}"
                )

            if unpacked_item.line_end != orig.line_end:
                issues.append(
                    f"Line end mismatch for {orig.evidence_id}: "
                    f"{unpacked_item.line_end} vs {orig.line_end}"
                )

            # Risk score must match (float comparison)
            if abs(unpacked_item.risk_score - orig.risk_score) > 0.001:
                issues.append(
                    f"Risk score mismatch for {orig.evidence_id}: "
                    f"{unpacked_item.risk_score} vs {orig.risk_score}"
                )

        return len(issues) == 0, issues


def pack_evidence_items(
    items: List[EvidenceItem],
    max_tokens: int = 3000,
) -> PackedEvidenceBundle:
    """Convenience function to pack evidence items.

    Args:
        items: Evidence items to pack
        max_tokens: Maximum tokens for output

    Returns:
        PackedEvidenceBundle with TOON output
    """
    packer = RetrievalPacker(max_tokens=max_tokens)
    return packer.pack(items)


def unpack_evidence_bundle(toon_output: str) -> List[EvidenceItem]:
    """Convenience function to unpack TOON evidence bundle.

    Args:
        toon_output: TOON-encoded string

    Returns:
        List of EvidenceItem objects
    """
    packer = RetrievalPacker()
    return packer.unpack(toon_output)


__all__ = [
    "EvidenceItem",
    "PackedEvidenceBundle",
    "RetrievalPacker",
    "pack_evidence_items",
    "unpack_evidence_bundle",
    "EVIDENCE_ID_PATTERNS",
]
