"""Label taxonomy and relevance rules for learning overlays."""

from __future__ import annotations

from typing import FrozenSet, Optional, Set

ROLE_LABELS: FrozenSet[str] = frozenset(
    {
        # Access control
        "IS_ACCESS_GATE",
        "IS_OWNER_CHECK",
        "IS_ADMIN_CHECK",
        "IS_ROLE_CHECK",
        "IS_MULTISIG_REQUIRED",
        # Protection mechanisms
        "IS_REENTRANCY_GUARD",
        "IS_PAUSE_MECHANISM",
        "IS_RATE_LIMITER",
        "IS_COOLDOWN_ENFORCER",
        # Value handling
        "IS_FEE_COLLECTOR",
        "IS_TREASURY",
        "IS_USER_BALANCE_TRACKER",
        "IS_REWARD_DISTRIBUTOR",
        # Oracle/external integration
        "IS_PRICE_ORACLE",
        "IS_EXTERNAL_ADAPTER",
        "IS_CALLBACK_HANDLER",
    }
)

RELATIONSHIP_LABELS: FrozenSet[str] = frozenset(
    {
        # Protection relationships
        "GUARDS",
        "PROTECTED_BY",
        "BYPASSES",
        # Data flow
        "READS_FROM",
        "WRITES_TO",
        "DERIVES_FROM",
        # Control flow
        "MUST_CALL_BEFORE",
        "TRIGGERS",
        "FALLBACK_FOR",
        # Business logic
        "PERMISSION_FOR",
        "LIMIT_FOR",
        "FEE_FOR",
    }
)

CONTEXT_PREFIX = "CONTEXT:"

ALL_LABELS: FrozenSet[str] = ROLE_LABELS | RELATIONSHIP_LABELS

LABEL_CATEGORY_MAP: dict[str, Set[str]] = {
    # Access control
    "IS_ACCESS_GATE": {"access_control"},
    "IS_OWNER_CHECK": {"access_control"},
    "IS_ADMIN_CHECK": {"access_control"},
    "IS_ROLE_CHECK": {"access_control"},
    "IS_MULTISIG_REQUIRED": {"access_control", "governance"},
    "PERMISSION_FOR": {"access_control"},
    "LIMIT_FOR": {"access_control", "dos"},
    "IS_PAUSE_MECHANISM": {"access_control", "dos"},
    # Reentrancy
    "IS_REENTRANCY_GUARD": {"reentrancy"},
    "GUARDS": {"reentrancy", "access_control"},
    "PROTECTED_BY": {"reentrancy", "access_control"},
    "BYPASSES": {"reentrancy", "access_control"},
    # Oracle
    "IS_PRICE_ORACLE": {"oracle"},
    "DERIVES_FROM": {"oracle"},
    # Token/value
    "IS_FEE_COLLECTOR": {"token", "mev"},
    "IS_TREASURY": {"token", "governance"},
    "IS_USER_BALANCE_TRACKER": {"token", "reentrancy"},
    "IS_REWARD_DISTRIBUTOR": {"token", "mev"},
    "FEE_FOR": {"token", "mev"},
    # DoS/limits
    "IS_RATE_LIMITER": {"dos"},
    "IS_COOLDOWN_ENFORCER": {"dos"},
    # External adapters/callbacks
    "IS_EXTERNAL_ADAPTER": {"oracle", "mev", "token"},
    "IS_CALLBACK_HANDLER": {"reentrancy", "oracle", "mev"},
    # Generic relationships
    "READS_FROM": {"general"},
    "WRITES_TO": {"general"},
    "MUST_CALL_BEFORE": {"general"},
    "TRIGGERS": {"general"},
    "FALLBACK_FOR": {"general"},
}

CONTEXT_CATEGORY_MAP: dict[str, Set[str]] = {
    "PERMISSION": {"access_control"},
    "LIMIT": {"access_control", "dos"},
    "BUSINESS": {"general"},
    "INVARIANT": {"general"},
}


def normalize_category(category: Optional[str]) -> str:
    """Normalize category names to internal format."""
    if not category:
        return ""
    return category.lower().replace("-", "_").strip()


def is_valid_label(label: str) -> bool:
    """Check if a label is part of the allowed taxonomy."""
    if not label:
        return False
    if label in ALL_LABELS:
        return True
    if label.startswith(CONTEXT_PREFIX):
        return _is_valid_context_label(label)
    return False


def label_categories(label: str) -> Set[str]:
    """Return categories where a label is relevant."""
    if label in LABEL_CATEGORY_MAP:
        return set(LABEL_CATEGORY_MAP[label])
    if label.startswith(CONTEXT_PREFIX):
        return _context_label_categories(label)
    return {"general"}


def label_relevant_to_category(label: str, category: Optional[str]) -> bool:
    """Check if label should be included for a vulnerability category."""
    normalized = normalize_category(category)
    if not normalized:
        return True
    categories = label_categories(label)
    if "general" in categories:
        return True
    return normalized in categories


def _is_valid_context_label(label: str) -> bool:
    """Validate context label format."""
    parts = label.split(":")
    if len(parts) < 3:
        return False
    if parts[0] != "CONTEXT":
        return False
    category_key = parts[1].strip().upper()
    return bool(category_key)


def _context_label_categories(label: str) -> Set[str]:
    """Resolve categories for a context label."""
    parts = label.split(":")
    if len(parts) < 3:
        return {"general"}
    category_key = parts[1].strip().upper()
    return set(CONTEXT_CATEGORY_MAP.get(category_key, {"general"}))
