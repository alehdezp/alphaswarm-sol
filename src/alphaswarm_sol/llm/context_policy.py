"""Context policy for data minimization.

Task 9.0: Data minimization security for LLM context.

This module enforces the principle of least privilege for LLM context.
The LLM should NEVER see more code than absolutely necessary for analysis.

Policy levels:
- STRICT: Only code directly referenced by finding
- STANDARD: Finding + 1-hop dependencies (DEFAULT)
- RELAXED: Full contract context (requires explicit opt-in)
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, List, Set

from .context import Context, ContextItem, Finding


class ContextPolicyLevel(Enum):
    """Context policy levels.

    STRICT: Only code directly referenced by finding (minimum exposure)
    STANDARD: Finding + 1-hop dependencies (DEFAULT - balanced)
    RELAXED: Full contract context (requires explicit opt-in)
    """

    STRICT = "strict"
    STANDARD = "standard"
    RELAXED = "relaxed"


@dataclass
class ContextAuditEntry:
    """Audit log entry for LLM context submission.

    Records what was sent to the LLM for security auditing.

    Attributes:
        timestamp: When the context was submitted
        finding_id: ID of the finding being analyzed
        policy_level: Policy level used
        bytes_sent: Size of filtered context in bytes
        items_included: IDs of items included in context
        items_filtered: IDs of items filtered out
    """

    timestamp: datetime
    finding_id: str
    policy_level: ContextPolicyLevel
    bytes_sent: int
    items_included: List[str]
    items_filtered: List[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "finding_id": self.finding_id,
            "policy_level": self.policy_level.value,
            "bytes_sent": self.bytes_sent,
            "items_included": self.items_included,
            "items_filtered": self.items_filtered,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextAuditEntry":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            finding_id=data["finding_id"],
            policy_level=ContextPolicyLevel(data["policy_level"]),
            bytes_sent=data["bytes_sent"],
            items_included=data["items_included"],
            items_filtered=data["items_filtered"],
        )


class ContextPolicy:
    """Enforce minimum context principle for LLM calls.

    This class filters context to only include what's necessary for
    analyzing a specific finding, following the principle of least privilege.

    Usage:
        policy = ContextPolicy(level=ContextPolicyLevel.STANDARD)
        filtered = policy.filter_context(full_context, finding)
        # filtered contains only necessary items
    """

    # Secret patterns to detect (pattern, description)
    SECRET_PATTERNS = [
        (r"PRIVATE_KEY", "private key variable"),
        (r"API_KEY", "API key variable"),
        (r"SECRET", "secret variable"),
        (r"PASSWORD", "password variable"),
        (r"0x[a-fA-F0-9]{64}", "64-char hex (possible private key)"),
        (r"-----BEGIN.*PRIVATE KEY-----", "PEM private key"),
    ]

    def __init__(
        self,
        level: ContextPolicyLevel = ContextPolicyLevel.STANDARD,
        enable_audit: bool = True,
        max_callers: int = 3,
        max_callees: int = 3,
    ):
        """Initialize context policy.

        Args:
            level: Policy level (STRICT, STANDARD, RELAXED)
            enable_audit: Whether to log context submissions
            max_callers: Maximum callers to include in STANDARD mode
            max_callees: Maximum callees to include in STANDARD mode
        """
        self.level = level
        self.enable_audit = enable_audit
        self.max_callers = max_callers
        self.max_callees = max_callees
        self.audit_log: List[ContextAuditEntry] = []

    def filter_context(self, context: Context, finding: Finding) -> Context:
        """Filter context to minimum necessary for finding.

        Args:
            context: Full context object with all items
            finding: The finding being analyzed

        Returns:
            Filtered context with only necessary items
        """
        if self.level == ContextPolicyLevel.STRICT:
            filtered = self._filter_strict(context, finding)
        elif self.level == ContextPolicyLevel.STANDARD:
            filtered = self._filter_standard(context, finding)
        else:  # RELAXED
            filtered = context.copy()

        if self.enable_audit:
            self._log_context(context, filtered, finding)

        return filtered

    def _filter_strict(self, context: Context, finding: Finding) -> Context:
        """Only include code directly referenced by finding.

        Includes:
        - The function containing the finding
        - State variables it reads/writes
        - External call targets (interface only)
        """
        relevant_ids: Set[str] = set()

        # The function with the finding
        relevant_ids.add(finding.function_id)

        # State variables it reads
        relevant_ids.update(finding.state_reads)

        # State variables it writes
        relevant_ids.update(finding.state_writes)

        # External call targets (just the signature)
        for call in finding.external_calls:
            relevant_ids.add(call.target_id)

        return context.filter_to_ids(relevant_ids)

    def _filter_standard(self, context: Context, finding: Finding) -> Context:
        """Include finding + 1-hop dependencies.

        Includes everything from STRICT plus:
        - Callers of the vulnerable function (max N)
        - Callees of the vulnerable function (max N)
        - Related modifiers
        """
        relevant_ids: Set[str] = set()

        # Start with strict set
        relevant_ids.add(finding.function_id)
        relevant_ids.update(finding.state_reads)
        relevant_ids.update(finding.state_writes)
        for call in finding.external_calls:
            relevant_ids.add(call.target_id)

        # Get the function item
        func = context.get(finding.function_id)
        if func and func.metadata:
            # Add 1-hop callers (max N)
            callers = func.metadata.get("callers", [])
            for caller_id in callers[: self.max_callers]:
                relevant_ids.add(caller_id)

            # Add 1-hop callees (max N)
            callees = func.metadata.get("callees", [])
            for callee_id in callees[: self.max_callees]:
                relevant_ids.add(callee_id)

            # Add modifiers
            modifiers = func.metadata.get("modifiers", [])
            relevant_ids.update(modifiers)

        return context.filter_to_ids(relevant_ids)

    def _log_context(
        self, full_context: Context, filtered_context: Context, finding: Finding
    ) -> None:
        """Log what was sent to LLM for audit."""
        full_ids = set(full_context.get_all_ids())
        filtered_ids = set(filtered_context.get_all_ids())
        excluded_ids = full_ids - filtered_ids

        entry = ContextAuditEntry(
            timestamp=datetime.now(),
            finding_id=finding.id,
            policy_level=self.level,
            bytes_sent=filtered_context.size_bytes(),
            items_included=sorted(filtered_ids),
            items_filtered=sorted(excluded_ids),
        )

        self.audit_log.append(entry)

    def get_audit_log(self) -> List[ContextAuditEntry]:
        """Get audit log of context submissions."""
        return self.audit_log.copy()

    def clear_audit_log(self) -> None:
        """Clear the audit log."""
        self.audit_log.clear()

    def validate_no_secrets(self, context: Context) -> List[str]:
        """Check context for potential secrets.

        Scans the context for common secret patterns that should not
        be sent to external LLM APIs.

        Args:
            context: Context to validate

        Returns:
            List of warnings if suspicious patterns found
        """
        warnings = []
        content = context.to_string()

        for pattern, description in self.SECRET_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potential {description} detected in context")

        return warnings

    def get_stats(self) -> dict:
        """Get statistics about context filtering."""
        if not self.audit_log:
            return {
                "total_submissions": 0,
                "total_bytes_sent": 0,
                "avg_bytes_per_submission": 0,
                "total_items_filtered": 0,
            }

        total_bytes = sum(e.bytes_sent for e in self.audit_log)
        total_filtered = sum(len(e.items_filtered) for e in self.audit_log)

        return {
            "total_submissions": len(self.audit_log),
            "total_bytes_sent": total_bytes,
            "avg_bytes_per_submission": total_bytes / len(self.audit_log),
            "total_items_filtered": total_filtered,
        }


def require_explicit_relaxed(func: Callable) -> Callable:
    """Decorator to require explicit opt-in for RELAXED policy.

    Functions decorated with this will raise ValueError if called with
    RELAXED policy without setting i_understand_risk=True.

    Usage:
        @require_explicit_relaxed
        def send_to_llm(context, policy, i_understand_risk=False):
            ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check for policy in kwargs or args
        policy = kwargs.get("policy")
        if policy is None and len(args) > 1:
            policy = args[1]

        if isinstance(policy, ContextPolicy):
            if policy.level == ContextPolicyLevel.RELAXED:
                understand_risk = kwargs.get("i_understand_risk", False)
                if not understand_risk:
                    raise ValueError(
                        "RELAXED context policy requires explicit "
                        "'i_understand_risk=True' parameter. "
                        "This sends full contract context to LLM."
                    )

        return func(*args, **kwargs)

    return wrapper


def get_policy(level: str = "standard") -> ContextPolicy:
    """Get a context policy by level name.

    Args:
        level: Policy level name ("strict", "standard", "relaxed")

    Returns:
        ContextPolicy instance

    Raises:
        ValueError: If level is unknown
    """
    try:
        policy_level = ContextPolicyLevel(level.lower())
    except ValueError:
        valid = [l.value for l in ContextPolicyLevel]
        raise ValueError(f"Unknown policy level: {level}. Valid: {valid}")

    return ContextPolicy(level=policy_level)


def validate_context_for_llm(
    context: Context, policy: ContextPolicy | None = None
) -> tuple[bool, List[str]]:
    """Validate context is safe to send to LLM.

    Args:
        context: Context to validate
        policy: Optional policy to use for validation

    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    if policy is None:
        policy = ContextPolicy()

    warnings = policy.validate_no_secrets(context)
    is_valid = len(warnings) == 0

    return is_valid, warnings


# =============================================================================
# Debug Slice Mode Support (Phase 5.9-07)
# =============================================================================


class SliceMode(Enum):
    """Slicing modes for context extraction.

    STANDARD: Normal mode with pruning and budget limits
    DEBUG: Debug mode that bypasses pruning for diagnosis
    """

    STANDARD = "standard"
    DEBUG = "debug"


@dataclass
class SlicePolicyConfig:
    """Configuration for slice-aware context policy.

    Attributes:
        mode: Slice mode (standard/debug)
        policy_level: Context policy level (strict/standard/relaxed)
        max_items: Maximum context items (bypassed in debug mode)
        include_omissions: Whether to include omission metadata in context
    """

    mode: SliceMode = SliceMode.STANDARD
    policy_level: ContextPolicyLevel = ContextPolicyLevel.STANDARD
    max_items: int = 50
    include_omissions: bool = True


@dataclass
class SlicedContextResult:
    """Result from slice-aware context policy.

    Contains the filtered context plus slice metadata.
    """

    context: Context
    slice_mode: SliceMode
    items_included: int
    items_filtered: int
    omissions_metadata: dict

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/serialization."""
        return {
            "slice_mode": self.slice_mode.value,
            "items_included": self.items_included,
            "items_filtered": self.items_filtered,
            "omissions_metadata": self.omissions_metadata,
        }


class SliceAwareContextPolicy:
    """Context policy with debug slice mode support.

    Extends ContextPolicy to support debug mode that bypasses pruning
    and annotates slice_mode in omissions metadata.

    Usage:
        policy = SliceAwareContextPolicy()

        # Standard mode
        result = policy.filter_with_slice_mode(context, finding)

        # Debug mode (no pruning)
        result = policy.filter_debug(context, finding)
    """

    def __init__(
        self,
        config: SlicePolicyConfig | None = None,
        base_policy: ContextPolicy | None = None,
    ):
        """Initialize slice-aware policy.

        Args:
            config: Slice policy configuration
            base_policy: Base context policy (uses default if None)
        """
        self.config = config or SlicePolicyConfig()
        self.base_policy = base_policy or ContextPolicy(
            level=self.config.policy_level
        )
        self._filter_history: List[SlicedContextResult] = []

    def filter_with_slice_mode(
        self,
        context: Context,
        finding: Finding,
        mode: SliceMode | None = None,
    ) -> SlicedContextResult:
        """Filter context with slice mode awareness.

        Args:
            context: Full context to filter
            finding: Finding being analyzed
            mode: Slice mode (uses config default if None)

        Returns:
            SlicedContextResult with filtered context and metadata
        """
        mode = mode or self.config.mode

        if mode == SliceMode.DEBUG:
            return self._filter_debug(context, finding)
        else:
            return self._filter_standard(context, finding)

    def filter_debug(
        self,
        context: Context,
        finding: Finding,
    ) -> SlicedContextResult:
        """Filter in debug mode (bypasses pruning).

        Debug mode:
        - Does NOT apply max_items limit
        - Does NOT apply strict filtering
        - DOES validate for secrets
        - Marks slice_mode: debug in omissions metadata

        Args:
            context: Full context
            finding: Finding being analyzed

        Returns:
            SlicedContextResult with full context for debugging
        """
        return self._filter_debug(context, finding)

    def _filter_standard(
        self,
        context: Context,
        finding: Finding,
    ) -> SlicedContextResult:
        """Standard filtering with pruning."""
        # Apply base policy filtering
        filtered = self.base_policy.filter_context(context, finding)

        # Track items
        original_ids = set(context.get_all_ids())
        filtered_ids = set(filtered.get_all_ids())
        excluded_ids = original_ids - filtered_ids

        # Build omissions metadata
        omissions_metadata = {
            "slice_mode": SliceMode.STANDARD.value,
            "coverage_score": len(filtered_ids) / len(original_ids) if original_ids else 1.0,
            "omitted_items": list(excluded_ids)[:20],  # Limit for logging
            "omitted_count": len(excluded_ids),
        }

        result = SlicedContextResult(
            context=filtered,
            slice_mode=SliceMode.STANDARD,
            items_included=len(filtered_ids),
            items_filtered=len(excluded_ids),
            omissions_metadata=omissions_metadata,
        )

        self._filter_history.append(result)
        return result

    def _filter_debug(
        self,
        context: Context,
        finding: Finding,
    ) -> SlicedContextResult:
        """Debug filtering (no pruning)."""
        # Still validate for secrets, but don't filter
        warnings = self.base_policy.validate_no_secrets(context)

        # Build omissions metadata marking debug mode
        omissions_metadata = {
            "slice_mode": SliceMode.DEBUG.value,
            "coverage_score": 1.0,  # Full coverage in debug
            "omitted_items": [],
            "omitted_count": 0,
            "debug_warnings": warnings,
            "debug_note": "Debug mode: pruning bypassed for diagnosis",
        }

        all_ids = context.get_all_ids()

        result = SlicedContextResult(
            context=context,  # Return full context
            slice_mode=SliceMode.DEBUG,
            items_included=len(all_ids),
            items_filtered=0,
            omissions_metadata=omissions_metadata,
        )

        self._filter_history.append(result)
        return result

    def get_filter_history(self) -> List[dict]:
        """Get history of filter operations."""
        return [r.to_dict() for r in self._filter_history]


def get_slice_aware_policy(
    mode: str = "standard",
    level: str = "standard",
) -> SliceAwareContextPolicy:
    """Get a slice-aware context policy.

    Args:
        mode: Slice mode ("standard" or "debug")
        level: Policy level ("strict", "standard", "relaxed")

    Returns:
        SliceAwareContextPolicy instance
    """
    slice_mode = SliceMode.DEBUG if mode == "debug" else SliceMode.STANDARD
    policy_level = ContextPolicyLevel(level.lower())

    config = SlicePolicyConfig(
        mode=slice_mode,
        policy_level=policy_level,
    )

    return SliceAwareContextPolicy(config)
