"""Phase 13: Hierarchical Risk Tag System.

This module defines the risk tag taxonomy based on OpenSCV and common
smart contract vulnerability classifications.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Set


class RiskCategory(str, Enum):
    """Top-level risk categories."""
    ACCESS_CONTROL = "access_control"
    REENTRANCY = "reentrancy"
    ARITHMETIC = "arithmetic"
    ORACLE = "oracle"
    MEV = "mev"
    LOGIC = "logic"
    UPGRADE = "upgrade"
    DOS = "dos"
    CRYPTO = "crypto"
    TOKEN = "token"
    INITIALIZATION = "initialization"
    EXTERNAL = "external"


class RiskTag(str, Enum):
    """Specific risk tags within categories."""
    # Access Control
    OWNER_ONLY = "owner_only"
    ROLE_BASED = "role_based"
    PUBLIC_ACCESS = "public_access"
    TX_ORIGIN = "tx_origin"
    MISSING_ACCESS_CONTROL = "missing_access_control"
    WEAK_ACCESS_CONTROL = "weak_access_control"
    PRIVILEGED_WRITE = "privileged_write"

    # Reentrancy
    EXTERNAL_CALL = "external_call"
    CALLBACK = "callback"
    CROSS_FUNCTION = "cross_function"
    READ_ONLY_REENTRANCY = "read_only_reentrancy"
    CEI_VIOLATION = "cei_violation"
    STATE_AFTER_CALL = "state_after_call"

    # Arithmetic
    OVERFLOW = "overflow"
    UNDERFLOW = "underflow"
    DIVISION_BY_ZERO = "division_by_zero"
    PRECISION_LOSS = "precision_loss"
    UNSAFE_CAST = "unsafe_cast"
    ROUNDING_ERROR = "rounding_error"

    # Oracle
    STALE_PRICE = "stale_price"
    SINGLE_SOURCE = "single_source"
    MANIPULATION = "manipulation"
    NO_SEQUENCER_CHECK = "no_sequencer_check"
    TWAP_VULNERABLE = "twap_vulnerable"

    # MEV
    FRONT_RUN = "front_run"
    SANDWICH = "sandwich"
    SLIPPAGE = "slippage"
    NO_DEADLINE = "no_deadline"
    FLASHLOAN_VULNERABLE = "flashloan_vulnerable"

    # Logic
    BUSINESS_LOGIC = "business_logic"
    STATE_CORRUPTION = "state_corruption"
    RACE_CONDITION = "race_condition"
    UNEXPECTED_BEHAVIOR = "unexpected_behavior"
    INVARIANT_VIOLATION = "invariant_violation"

    # Upgrade
    STORAGE_COLLISION = "storage_collision"
    UNINITIALIZED_PROXY = "uninitialized_proxy"
    SELFDESTRUCT = "selfdestruct"
    DELEGATECALL_RISK = "delegatecall_risk"
    NO_STORAGE_GAP = "no_storage_gap"

    # DoS
    UNBOUNDED_LOOP = "unbounded_loop"
    EXTERNAL_IN_LOOP = "external_in_loop"
    GAS_GRIEFING = "gas_griefing"
    BLOCK_STUFFING = "block_stuffing"
    REVERT_DOS = "revert_dos"

    # Crypto
    WEAK_RANDOMNESS = "weak_randomness"
    SIGNATURE_MALLEABILITY = "signature_malleability"
    REPLAY_ATTACK = "replay_attack"
    HASH_COLLISION = "hash_collision"
    ECRECOVER_ZERO = "ecrecover_zero"

    # Token
    UNSAFE_TRANSFER = "unsafe_transfer"
    NO_RETURN_CHECK = "no_return_check"
    FEE_ON_TRANSFER = "fee_on_transfer"
    REBASING_TOKEN = "rebasing_token"
    APPROVAL_RACE = "approval_race"

    # Initialization
    UNPROTECTED_INIT = "unprotected_init"
    DOUBLE_INIT = "double_init"
    CONSTRUCTOR_SHADOW = "constructor_shadow"

    # External
    UNTRUSTED_CALL = "untrusted_call"
    RETURN_VALUE_IGNORED = "return_value_ignored"
    UNCHECKED_CALL = "unchecked_call"


# Hierarchical mapping: category -> list of tags
RISK_TAG_HIERARCHY: Dict[RiskCategory, List[RiskTag]] = {
    RiskCategory.ACCESS_CONTROL: [
        RiskTag.OWNER_ONLY,
        RiskTag.ROLE_BASED,
        RiskTag.PUBLIC_ACCESS,
        RiskTag.TX_ORIGIN,
        RiskTag.MISSING_ACCESS_CONTROL,
        RiskTag.WEAK_ACCESS_CONTROL,
        RiskTag.PRIVILEGED_WRITE,
    ],
    RiskCategory.REENTRANCY: [
        RiskTag.EXTERNAL_CALL,
        RiskTag.CALLBACK,
        RiskTag.CROSS_FUNCTION,
        RiskTag.READ_ONLY_REENTRANCY,
        RiskTag.CEI_VIOLATION,
        RiskTag.STATE_AFTER_CALL,
    ],
    RiskCategory.ARITHMETIC: [
        RiskTag.OVERFLOW,
        RiskTag.UNDERFLOW,
        RiskTag.DIVISION_BY_ZERO,
        RiskTag.PRECISION_LOSS,
        RiskTag.UNSAFE_CAST,
        RiskTag.ROUNDING_ERROR,
    ],
    RiskCategory.ORACLE: [
        RiskTag.STALE_PRICE,
        RiskTag.SINGLE_SOURCE,
        RiskTag.MANIPULATION,
        RiskTag.NO_SEQUENCER_CHECK,
        RiskTag.TWAP_VULNERABLE,
    ],
    RiskCategory.MEV: [
        RiskTag.FRONT_RUN,
        RiskTag.SANDWICH,
        RiskTag.SLIPPAGE,
        RiskTag.NO_DEADLINE,
        RiskTag.FLASHLOAN_VULNERABLE,
    ],
    RiskCategory.LOGIC: [
        RiskTag.BUSINESS_LOGIC,
        RiskTag.STATE_CORRUPTION,
        RiskTag.RACE_CONDITION,
        RiskTag.UNEXPECTED_BEHAVIOR,
        RiskTag.INVARIANT_VIOLATION,
    ],
    RiskCategory.UPGRADE: [
        RiskTag.STORAGE_COLLISION,
        RiskTag.UNINITIALIZED_PROXY,
        RiskTag.SELFDESTRUCT,
        RiskTag.DELEGATECALL_RISK,
        RiskTag.NO_STORAGE_GAP,
    ],
    RiskCategory.DOS: [
        RiskTag.UNBOUNDED_LOOP,
        RiskTag.EXTERNAL_IN_LOOP,
        RiskTag.GAS_GRIEFING,
        RiskTag.BLOCK_STUFFING,
        RiskTag.REVERT_DOS,
    ],
    RiskCategory.CRYPTO: [
        RiskTag.WEAK_RANDOMNESS,
        RiskTag.SIGNATURE_MALLEABILITY,
        RiskTag.REPLAY_ATTACK,
        RiskTag.HASH_COLLISION,
        RiskTag.ECRECOVER_ZERO,
    ],
    RiskCategory.TOKEN: [
        RiskTag.UNSAFE_TRANSFER,
        RiskTag.NO_RETURN_CHECK,
        RiskTag.FEE_ON_TRANSFER,
        RiskTag.REBASING_TOKEN,
        RiskTag.APPROVAL_RACE,
    ],
    RiskCategory.INITIALIZATION: [
        RiskTag.UNPROTECTED_INIT,
        RiskTag.DOUBLE_INIT,
        RiskTag.CONSTRUCTOR_SHADOW,
    ],
    RiskCategory.EXTERNAL: [
        RiskTag.UNTRUSTED_CALL,
        RiskTag.RETURN_VALUE_IGNORED,
        RiskTag.UNCHECKED_CALL,
    ],
}

# Descriptions for each tag
RISK_TAG_DESCRIPTIONS: Dict[RiskTag, str] = {
    # Access Control
    RiskTag.OWNER_ONLY: "Function restricted to contract owner",
    RiskTag.ROLE_BASED: "Function uses role-based access control",
    RiskTag.PUBLIC_ACCESS: "Function is publicly accessible without restrictions",
    RiskTag.TX_ORIGIN: "Uses tx.origin for authentication (vulnerable)",
    RiskTag.MISSING_ACCESS_CONTROL: "Function lacks necessary access control",
    RiskTag.WEAK_ACCESS_CONTROL: "Access control can be bypassed",
    RiskTag.PRIVILEGED_WRITE: "Writes to privileged state without proper checks",

    # Reentrancy
    RiskTag.EXTERNAL_CALL: "Contains external calls that may allow reentrancy",
    RiskTag.CALLBACK: "Vulnerable to callback-based reentrancy",
    RiskTag.CROSS_FUNCTION: "Cross-function reentrancy possible",
    RiskTag.READ_ONLY_REENTRANCY: "Read-only reentrancy vulnerability",
    RiskTag.CEI_VIOLATION: "Violates Checks-Effects-Interactions pattern",
    RiskTag.STATE_AFTER_CALL: "State modified after external call",

    # Arithmetic
    RiskTag.OVERFLOW: "Potential integer overflow",
    RiskTag.UNDERFLOW: "Potential integer underflow",
    RiskTag.DIVISION_BY_ZERO: "Potential division by zero",
    RiskTag.PRECISION_LOSS: "Precision loss in calculations",
    RiskTag.UNSAFE_CAST: "Unsafe type casting",
    RiskTag.ROUNDING_ERROR: "Rounding errors may cause issues",

    # Oracle
    RiskTag.STALE_PRICE: "Oracle price may be stale",
    RiskTag.SINGLE_SOURCE: "Single oracle source (manipulation risk)",
    RiskTag.MANIPULATION: "Price oracle can be manipulated",
    RiskTag.NO_SEQUENCER_CHECK: "Missing L2 sequencer uptime check",
    RiskTag.TWAP_VULNERABLE: "TWAP oracle vulnerable to manipulation",

    # MEV
    RiskTag.FRONT_RUN: "Transaction can be front-run",
    RiskTag.SANDWICH: "Vulnerable to sandwich attacks",
    RiskTag.SLIPPAGE: "Missing or weak slippage protection",
    RiskTag.NO_DEADLINE: "Missing transaction deadline",
    RiskTag.FLASHLOAN_VULNERABLE: "Vulnerable to flash loan attacks",

    # Logic
    RiskTag.BUSINESS_LOGIC: "Business logic flaw",
    RiskTag.STATE_CORRUPTION: "State may become corrupted",
    RiskTag.RACE_CONDITION: "Race condition possible",
    RiskTag.UNEXPECTED_BEHAVIOR: "May exhibit unexpected behavior",
    RiskTag.INVARIANT_VIOLATION: "Contract invariants may be violated",

    # Upgrade
    RiskTag.STORAGE_COLLISION: "Storage slot collision possible",
    RiskTag.UNINITIALIZED_PROXY: "Proxy may be uninitialized",
    RiskTag.SELFDESTRUCT: "Contains selfdestruct (risky)",
    RiskTag.DELEGATECALL_RISK: "Delegatecall to untrusted contract",
    RiskTag.NO_STORAGE_GAP: "Missing storage gap in upgradeable contract",

    # DoS
    RiskTag.UNBOUNDED_LOOP: "Unbounded loop may cause DoS",
    RiskTag.EXTERNAL_IN_LOOP: "External calls in loop (DoS risk)",
    RiskTag.GAS_GRIEFING: "Vulnerable to gas griefing",
    RiskTag.BLOCK_STUFFING: "Vulnerable to block stuffing",
    RiskTag.REVERT_DOS: "Reverts can cause denial of service",

    # Crypto
    RiskTag.WEAK_RANDOMNESS: "Weak or predictable randomness",
    RiskTag.SIGNATURE_MALLEABILITY: "Signature malleability vulnerability",
    RiskTag.REPLAY_ATTACK: "Vulnerable to replay attacks",
    RiskTag.HASH_COLLISION: "Hash collision possible",
    RiskTag.ECRECOVER_ZERO: "ecrecover may return zero address",

    # Token
    RiskTag.UNSAFE_TRANSFER: "Unsafe token transfer",
    RiskTag.NO_RETURN_CHECK: "Token return value not checked",
    RiskTag.FEE_ON_TRANSFER: "May not handle fee-on-transfer tokens",
    RiskTag.REBASING_TOKEN: "May not handle rebasing tokens",
    RiskTag.APPROVAL_RACE: "Token approval race condition",

    # Initialization
    RiskTag.UNPROTECTED_INIT: "Initializer not protected",
    RiskTag.DOUBLE_INIT: "May be initialized multiple times",
    RiskTag.CONSTRUCTOR_SHADOW: "Constructor shadows implementation",

    # External
    RiskTag.UNTRUSTED_CALL: "Call to untrusted external contract",
    RiskTag.RETURN_VALUE_IGNORED: "External call return value ignored",
    RiskTag.UNCHECKED_CALL: "Low-level call without success check",
}

# Reverse mapping: tag -> category
_TAG_TO_CATEGORY: Dict[RiskTag, RiskCategory] = {}
for category, tags in RISK_TAG_HIERARCHY.items():
    for tag in tags:
        _TAG_TO_CATEGORY[tag] = category


def get_tag_category(tag: RiskTag) -> RiskCategory:
    """Get the category for a tag.

    Args:
        tag: Risk tag

    Returns:
        Parent category
    """
    return _TAG_TO_CATEGORY.get(tag, RiskCategory.LOGIC)


def get_tags_in_category(category: RiskCategory) -> List[RiskTag]:
    """Get all tags in a category.

    Args:
        category: Risk category

    Returns:
        List of tags in the category
    """
    return RISK_TAG_HIERARCHY.get(category, [])


def get_all_tags() -> List[RiskTag]:
    """Get all defined risk tags.

    Returns:
        List of all risk tags
    """
    return list(RiskTag)


def is_valid_tag(tag_str: str) -> bool:
    """Check if a string is a valid tag.

    Args:
        tag_str: Tag string to check

    Returns:
        True if valid tag
    """
    try:
        RiskTag(tag_str)
        return True
    except ValueError:
        return False


def get_parent_category(tag: RiskTag) -> Optional[RiskCategory]:
    """Get the parent category of a tag.

    Args:
        tag: Risk tag

    Returns:
        Parent category or None
    """
    return _TAG_TO_CATEGORY.get(tag)


def get_tag_description(tag: RiskTag) -> str:
    """Get the description for a tag.

    Args:
        tag: Risk tag

    Returns:
        Tag description
    """
    return RISK_TAG_DESCRIPTIONS.get(tag, "")


def get_related_tags(tag: RiskTag) -> List[RiskTag]:
    """Get related tags (same category).

    Args:
        tag: Risk tag

    Returns:
        List of related tags
    """
    category = get_tag_category(tag)
    return [t for t in get_tags_in_category(category) if t != tag]


__all__ = [
    "RiskCategory",
    "RiskTag",
    "RISK_TAG_HIERARCHY",
    "RISK_TAG_DESCRIPTIONS",
    "get_tag_category",
    "get_tags_in_category",
    "get_all_tags",
    "is_valid_tag",
    "get_parent_category",
    "get_tag_description",
    "get_related_tags",
]
