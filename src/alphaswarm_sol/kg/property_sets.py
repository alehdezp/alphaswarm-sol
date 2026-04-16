"""Property sets per vulnerability category.

Task 9.A: Define category-relevant properties for graph slicing.

Each vulnerability category has a specific set of properties that are
relevant for LLM analysis. Slicing the graph to only these properties
reduces token usage by ~75% while maintaining detection accuracy.

Categories:
- reentrancy: CEI violations, reentrancy guards
- access_control: Auth gates, privileged state
- dos: Unbounded loops, gas griefing
- oracle: Price feeds, staleness checks
- mev: Slippage, deadlines, sandwich
- token: ERC20 transfers, return checks
- crypto: Signatures, malleability
- upgrade: Proxy patterns, initializers
- governance: Voting, timelocks, quorums
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Set


class VulnerabilityCategory(Enum):
    """Vulnerability categories for property set lookup."""

    REENTRANCY = "reentrancy"
    ACCESS_CONTROL = "access_control"
    DOS = "dos"
    ORACLE = "oracle"
    MEV = "mev"
    TOKEN = "token"
    CRYPTO = "crypto"
    UPGRADE = "upgrade"
    GOVERNANCE = "governance"
    GENERAL = "general"  # Fallback for unknown categories


@dataclass(frozen=True)
class PropertySet:
    """Set of properties relevant to a vulnerability category.

    Attributes:
        required: Properties that must be included
        optional: Properties that can provide additional context
        exclusions: Properties explicitly excluded from this category
    """

    required: FrozenSet[str]
    optional: FrozenSet[str] = field(default_factory=frozenset)
    exclusions: FrozenSet[str] = field(default_factory=frozenset)

    def all_properties(self) -> FrozenSet[str]:
        """Get all properties (required + optional)."""
        return self.required | self.optional

    def is_relevant(self, property_name: str) -> bool:
        """Check if a property is relevant for this category."""
        if property_name in self.exclusions:
            return False
        return property_name in self.required or property_name in self.optional


# Core structural properties always included
CORE_PROPERTIES: FrozenSet[str] = frozenset({
    # Identity
    "name",
    "full_name",
    "signature",
    "contract",
    # Structure
    "visibility",
    "modifiers",
    "parameters",
    "returns",
    # State interaction
    "reads_state",
    "writes_state",
    "state_variables_read",
    "state_variables_written",
    # Calls
    "has_external_calls",
    "external_call_count",
    "callers",
    "callees",
})


# Define property sets per category
PROPERTY_SETS: Dict[VulnerabilityCategory, PropertySet] = {
    VulnerabilityCategory.REENTRANCY: PropertySet(
        required=frozenset({
            # Core reentrancy properties
            "state_write_after_external_call",
            "state_write_before_external_call",
            "has_reentrancy_guard",
            # External calls
            "has_external_calls",
            "external_call_sites",
            "external_call_count",
            "uses_call",
            "uses_delegatecall",
            # State interaction
            "state_variables_written",
            "state_variables_read",
            # Access
            "visibility",
            "modifiers",
        }),
        optional=frozenset({
            # Call graph
            "callers",
            "callees",
            "cross_function_writes",
            # Value transfer
            "transfers_value",
            "uses_transfer",
            "uses_send",
        }),
        exclusions=frozenset({
            "reads_oracle_price",
            "has_staleness_check",
            "swap_like",
            "uses_ecrecover",
        }),
    ),
    VulnerabilityCategory.ACCESS_CONTROL: PropertySet(
        required=frozenset({
            # Core access properties
            "has_access_gate",
            "access_gate_logic",
            "access_gate_modifiers",
            "writes_privileged_state",
            # Sender checks
            "uses_tx_origin",
            "uses_msg_sender",
            # Visibility
            "visibility",
            "modifiers",
            # Privileged operations
            "public_wrapper_without_access_gate",
            "role_grant_like",
            "role_revoke_like",
            "uses_selfdestruct",
        }),
        optional=frozenset({
            # Role management
            "role_checks",
            "owner_comparisons",
            "caller_restrictions",
            # Call graph
            "callers",
            "callees",
            # State
            "state_variables_written",
        }),
    ),
    VulnerabilityCategory.DOS: PropertySet(
        required=frozenset({
            # Loop properties
            "has_loops",
            "loop_count",
            "has_unbounded_loop",
            "has_require_bounds",
            "external_calls_in_loop",
            "has_unbounded_deletion",
            # Gas issues
            "uses_transfer",
            "uses_send",
            "has_strict_equality_check",
            # External calls
            "has_external_calls",
            "external_call_count",
        }),
        optional=frozenset({
            # Call targets
            "external_call_sites",
            # Visibility
            "visibility",
            "modifiers",
            # State
            "state_variables_written",
        }),
    ),
    VulnerabilityCategory.ORACLE: PropertySet(
        required=frozenset({
            # Oracle interaction
            "reads_oracle_price",
            "oracle_sources",
            # Validation
            "has_staleness_check",
            "oracle_round_check",
            "oracle_freshness_ok",
            # L2 specifics
            "has_sequencer_uptime_check",
            "l2_oracle_context",
            # TWAP
            "reads_twap",
            "has_twap_window_parameter",
        }),
        optional=frozenset({
            # Price usage
            "price_deviation_check",
            "multiple_oracle_sources",
            # External calls
            "has_external_calls",
            "external_call_sites",
        }),
        exclusions=frozenset({
            "state_write_after_external_call",
            "has_reentrancy_guard",
        }),
    ),
    VulnerabilityCategory.MEV: PropertySet(
        required=frozenset({
            # Swap properties
            "swap_like",
            # Slippage
            "has_slippage_parameter",
            "has_slippage_check",
            "risk_missing_slippage_parameter",
            # Deadline
            "has_deadline_parameter",
            "has_deadline_check",
            "risk_missing_deadline_check",
            # TWAP
            "risk_missing_twap_window",
        }),
        optional=frozenset({
            # External calls
            "has_external_calls",
            "external_call_sites",
            # Parameters
            "parameters",
            # Visibility
            "visibility",
        }),
    ),
    VulnerabilityCategory.TOKEN: PropertySet(
        required=frozenset({
            # ERC20 operations
            "uses_erc20_transfer",
            "uses_erc20_transfer_from",
            "uses_erc20_approve",
            "uses_erc20_mint",
            "uses_erc20_burn",
            # Safety
            "token_return_guarded",
            "uses_safe_erc20",
        }),
        optional=frozenset({
            # External calls
            "has_external_calls",
            "external_call_sites",
            # State
            "state_variables_written",
            "state_variables_read",
            # Access
            "has_access_gate",
            "visibility",
        }),
    ),
    VulnerabilityCategory.CRYPTO: PropertySet(
        required=frozenset({
            # Signature verification
            "uses_ecrecover",
            "checks_zero_address",
            # Malleability
            "checks_sig_v",
            "checks_sig_s",
            # Replay protection
            "uses_chainid",
            "has_nonce_parameter",
            "reads_nonce_state",
            "writes_nonce_state",
            # EIP-712
            "uses_domain_separator",
            # Deadline
            "has_deadline_check",
            # Permit
            "is_permit_like",
        }),
        optional=frozenset({
            # Parameters
            "parameters",
            # State
            "state_variables_read",
            "state_variables_written",
            # Visibility
            "visibility",
        }),
    ),
    VulnerabilityCategory.UPGRADE: PropertySet(
        required=frozenset({
            # Proxy patterns
            "is_proxy_like",
            "proxy_type",
            "is_upgradeable",
            # Delegatecall
            "uses_delegatecall",
            # Storage
            "upgradeable_without_storage_gap",
            "has_storage_gap",
            # Initializer
            "is_initializer_like",
            "has_initializer_modifier",
            "initializer_can_reinit",
        }),
        optional=frozenset({
            # Access
            "has_access_gate",
            "visibility",
            "modifiers",
            # State
            "state_variables_written",
        }),
    ),
    VulnerabilityCategory.GOVERNANCE: PropertySet(
        required=frozenset({
            # Voting
            "governance_vote_without_snapshot",
            # Execution
            "governance_exec_without_timelock_check",
            "governance_exec_without_quorum_check",
            # Access
            "has_access_gate",
        }),
        optional=frozenset({
            # Multisig
            "multisig_threshold_change_without_gate",
            "multisig_signer_change_without_gate",
            "multisig_threshold_is_zero",
            # State
            "state_variables_written",
            # Visibility
            "visibility",
            "modifiers",
        }),
    ),
    VulnerabilityCategory.GENERAL: PropertySet(
        required=CORE_PROPERTIES,
        optional=frozenset(),
    ),
}


def get_property_set(category: VulnerabilityCategory | str) -> PropertySet:
    """Get property set for a vulnerability category.

    Args:
        category: Category enum or string name

    Returns:
        PropertySet for the category

    Raises:
        ValueError: If category is unknown
    """
    if isinstance(category, str):
        try:
            category = VulnerabilityCategory(category.lower())
        except ValueError:
            # Fall back to GENERAL for unknown categories
            category = VulnerabilityCategory.GENERAL

    return PROPERTY_SETS.get(category, PROPERTY_SETS[VulnerabilityCategory.GENERAL])


def get_relevant_properties(category: VulnerabilityCategory | str) -> Set[str]:
    """Get all relevant properties for a category (including core).

    Args:
        category: Category enum or string name

    Returns:
        Set of all relevant property names
    """
    prop_set = get_property_set(category)
    return set(prop_set.all_properties()) | set(CORE_PROPERTIES)


def is_property_relevant(
    property_name: str, category: VulnerabilityCategory | str
) -> bool:
    """Check if a property is relevant for a category.

    Args:
        property_name: Name of the property
        category: Category to check relevance for

    Returns:
        True if property is relevant
    """
    if property_name in CORE_PROPERTIES:
        return True

    prop_set = get_property_set(category)
    return prop_set.is_relevant(property_name)


def get_all_categories() -> List[VulnerabilityCategory]:
    """Get all defined vulnerability categories."""
    return list(PROPERTY_SETS.keys())


def get_category_from_pattern_id(pattern_id: str) -> VulnerabilityCategory:
    """Infer category from pattern ID prefix.

    Args:
        pattern_id: Pattern ID like "reentrancy-001" or "auth-basic"

    Returns:
        Inferred category
    """
    pattern_lower = pattern_id.lower()

    # Map pattern prefixes to categories
    prefix_map = {
        "reentrancy": VulnerabilityCategory.REENTRANCY,
        "reentry": VulnerabilityCategory.REENTRANCY,
        "access": VulnerabilityCategory.ACCESS_CONTROL,
        "auth": VulnerabilityCategory.ACCESS_CONTROL,
        "vm-": VulnerabilityCategory.ACCESS_CONTROL,  # vm = value movement
        "dos": VulnerabilityCategory.DOS,
        "gas": VulnerabilityCategory.DOS,
        "loop": VulnerabilityCategory.DOS,
        "oracle": VulnerabilityCategory.ORACLE,
        "price": VulnerabilityCategory.ORACLE,
        "mev": VulnerabilityCategory.MEV,
        "swap": VulnerabilityCategory.MEV,
        "slippage": VulnerabilityCategory.MEV,
        "token": VulnerabilityCategory.TOKEN,
        "erc20": VulnerabilityCategory.TOKEN,
        "transfer": VulnerabilityCategory.TOKEN,
        "crypto": VulnerabilityCategory.CRYPTO,
        "sig": VulnerabilityCategory.CRYPTO,
        "signature": VulnerabilityCategory.CRYPTO,
        "ecrecover": VulnerabilityCategory.CRYPTO,
        "upgrade": VulnerabilityCategory.UPGRADE,
        "proxy": VulnerabilityCategory.UPGRADE,
        "init": VulnerabilityCategory.UPGRADE,
        "gov": VulnerabilityCategory.GOVERNANCE,
        "vote": VulnerabilityCategory.GOVERNANCE,
        "timelock": VulnerabilityCategory.GOVERNANCE,
    }

    for prefix, category in prefix_map.items():
        if pattern_lower.startswith(prefix) or prefix in pattern_lower:
            return category

    return VulnerabilityCategory.GENERAL
