"""Label taxonomy definitions for semantic labeling.

This module defines the hierarchical label taxonomy used for semantic
function labeling. Labels follow the category.subcategory format.

Categories:
- ACCESS_CONTROL: Ownership, role-based access, permissions
- STATE_MUTATION: Critical state writes, initialization
- EXTERNAL_INTERACTION: External calls, untrusted calls, oracles
- VALUE_HANDLING: Value transfers, fee collection, balances
- INVARIANTS: Balance checks, supply invariants
- TEMPORAL: Timelocks, deadlines
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class LabelCategory(str, Enum):
    """Top-level label categories."""

    ACCESS_CONTROL = "access_control"
    STATE_MUTATION = "state_mutation"
    EXTERNAL_INTERACTION = "external_interaction"
    VALUE_HANDLING = "value_handling"
    INVARIANTS = "invariants"
    TEMPORAL = "temporal"


@dataclass
class LabelDefinition:
    """Definition of a semantic label.

    Attributes:
        id: Unique label ID in category.subcategory format
        category: Top-level category
        subcategory: Subcategory within the top-level
        description: Human-readable description
        examples: Code patterns that match this label
        anti_examples: Similar patterns that do NOT match
        negation_id: ID of the negating label (e.g., "no_restriction")
    """

    id: str
    category: LabelCategory
    subcategory: str
    description: str
    examples: List[str] = field(default_factory=list)
    anti_examples: List[str] = field(default_factory=list)
    negation_id: Optional[str] = None

    def __post_init__(self):
        """Validate label ID format."""
        expected_id = f"{self.category.value}.{self.subcategory}"
        if self.id != expected_id:
            raise ValueError(f"Label ID '{self.id}' must match '{expected_id}'")


# Core taxonomy - approximately 20 labels
CORE_TAXONOMY: List[LabelDefinition] = [
    # ACCESS_CONTROL labels
    LabelDefinition(
        id="access_control.owner_only",
        category=LabelCategory.ACCESS_CONTROL,
        subcategory="owner_only",
        description="Function restricted to contract owner only",
        examples=[
            "require(msg.sender == owner)",
            "onlyOwner modifier",
            "require(_msgSender() == _owner)",
        ],
        anti_examples=[
            "require(hasRole(ADMIN_ROLE, msg.sender))",
            "require(msg.sender == authorized[msg.sender])",
        ],
        negation_id="access_control.no_restriction",
    ),
    LabelDefinition(
        id="access_control.role_based",
        category=LabelCategory.ACCESS_CONTROL,
        subcategory="role_based",
        description="Function restricted to specific role(s)",
        examples=[
            "require(hasRole(ADMIN_ROLE, msg.sender))",
            "onlyRole(MINTER_ROLE)",
            "require(isMinter(msg.sender))",
        ],
        anti_examples=[
            "require(msg.sender == owner)",
            "require(msg.value > 0)",
        ],
        negation_id="access_control.no_restriction",
    ),
    LabelDefinition(
        id="access_control.permissioned",
        category=LabelCategory.ACCESS_CONTROL,
        subcategory="permissioned",
        description="Function requires explicit permission or allowance",
        examples=[
            "require(allowance[owner][msg.sender] >= amount)",
            "require(isApprovedOrOwner(msg.sender, tokenId))",
            "require(operators[msg.sender])",
        ],
        anti_examples=[
            "require(msg.sender == owner)",
            "require(hasRole(ADMIN_ROLE, msg.sender))",
        ],
        negation_id="access_control.no_restriction",
    ),
    LabelDefinition(
        id="access_control.no_restriction",
        category=LabelCategory.ACCESS_CONTROL,
        subcategory="no_restriction",
        description="Function has no access restrictions (public/open)",
        examples=[
            "function deposit() external payable",
            "function getBalance() external view returns (uint256)",
        ],
        anti_examples=[
            "function withdraw() external onlyOwner",
            "function mint() external onlyRole(MINTER_ROLE)",
        ],
        negation_id=None,
    ),
    # STATE_MUTATION labels
    LabelDefinition(
        id="state_mutation.writes_critical",
        category=LabelCategory.STATE_MUTATION,
        subcategory="writes_critical",
        description="Function writes to critical state variables (balances, ownership, roles)",
        examples=[
            "balances[msg.sender] -= amount",
            "owner = newOwner",
            "_grantRole(role, account)",
        ],
        anti_examples=[
            "lastUpdated = block.timestamp",
            "emit Transfer(from, to, amount)",
        ],
        negation_id="state_mutation.no_state_change",
    ),
    LabelDefinition(
        id="state_mutation.initializes_state",
        category=LabelCategory.STATE_MUTATION,
        subcategory="initializes_state",
        description="Function initializes contract state (constructor or initializer)",
        examples=[
            "constructor()",
            "function initialize() initializer",
            "function __MyContract_init()",
        ],
        anti_examples=[
            "function setConfig(uint256 value)",
            "function updateSettings()",
        ],
        negation_id="state_mutation.no_state_change",
    ),
    LabelDefinition(
        id="state_mutation.no_state_change",
        category=LabelCategory.STATE_MUTATION,
        subcategory="no_state_change",
        description="Function does not modify state (view/pure)",
        examples=[
            "function getBalance() external view",
            "function calculate() internal pure",
        ],
        anti_examples=[
            "function deposit() external",
            "function transfer() external",
        ],
        negation_id=None,
    ),
    # EXTERNAL_INTERACTION labels
    LabelDefinition(
        id="external_interaction.calls_trusted",
        category=LabelCategory.EXTERNAL_INTERACTION,
        subcategory="calls_trusted",
        description="Function calls trusted external contracts (known addresses)",
        examples=[
            "IERC20(USDC).transfer(to, amount)",
            "router.swapExactTokensForTokens(...)",
            "Address(factory).functionCall(...)",
        ],
        anti_examples=[
            "address(token).call(data)",
            "ICallback(msg.sender).onCallback()",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="external_interaction.calls_untrusted",
        category=LabelCategory.EXTERNAL_INTERACTION,
        subcategory="calls_untrusted",
        description="Function calls untrusted/user-provided addresses",
        examples=[
            "token.transfer(to, amount)",
            "ICallback(recipient).onReceive()",
            "to.call{value: amount}('')",
        ],
        anti_examples=[
            "IERC20(WETH).transfer(to, amount)",
            "oracle.getPrice()",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="external_interaction.reads_oracle",
        category=LabelCategory.EXTERNAL_INTERACTION,
        subcategory="reads_oracle",
        description="Function reads price/data from external oracle",
        examples=[
            "oracle.latestRoundData()",
            "priceFeed.getPrice()",
            "IChainlinkAggregator(feed).latestAnswer()",
        ],
        anti_examples=[
            "block.timestamp",
            "balanceOf[msg.sender]",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="external_interaction.no_external_calls",
        category=LabelCategory.EXTERNAL_INTERACTION,
        subcategory="no_external_calls",
        description="Function makes no external calls",
        examples=[
            "function calculate() internal pure",
            "function getConfig() external view returns (uint256)",
        ],
        anti_examples=[
            "token.transfer(to, amount)",
            "oracle.getPrice()",
        ],
        negation_id=None,
    ),
    # VALUE_HANDLING labels
    LabelDefinition(
        id="value_handling.transfers_value_out",
        category=LabelCategory.VALUE_HANDLING,
        subcategory="transfers_value_out",
        description="Function transfers ETH or tokens out of contract",
        examples=[
            "payable(to).transfer(amount)",
            "token.transfer(recipient, amount)",
            "to.call{value: amount}('')",
        ],
        anti_examples=[
            "require(msg.value >= amount)",
            "balances[msg.sender] += msg.value",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="value_handling.collects_fees",
        category=LabelCategory.VALUE_HANDLING,
        subcategory="collects_fees",
        description="Function collects protocol fees",
        examples=[
            "feeAmount = amount * feeRate / 10000",
            "protocolFees += fee",
            "treasury.transfer(feeAmount)",
        ],
        anti_examples=[
            "balances[to] += amount",
            "token.transfer(to, amount)",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="value_handling.handles_balance",
        category=LabelCategory.VALUE_HANDLING,
        subcategory="handles_balance",
        description="Function reads or writes user balances",
        examples=[
            "balances[msg.sender] -= amount",
            "uint256 balance = balanceOf[account]",
            "_mint(to, amount)",
        ],
        anti_examples=[
            "totalSupply += amount",
            "lastUpdated = block.timestamp",
        ],
        negation_id=None,
    ),
    # INVARIANTS labels
    LabelDefinition(
        id="invariants.enforces_balance_check",
        category=LabelCategory.INVARIANTS,
        subcategory="enforces_balance_check",
        description="Function enforces balance invariants",
        examples=[
            "require(balances[msg.sender] >= amount)",
            "require(address(this).balance >= withdrawAmount)",
            "assert(totalDeposits >= totalWithdrawals)",
        ],
        anti_examples=[
            "require(amount > 0)",
            "require(msg.sender != address(0))",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="invariants.enforces_supply_invariant",
        category=LabelCategory.INVARIANTS,
        subcategory="enforces_supply_invariant",
        description="Function enforces total supply invariants",
        examples=[
            "require(totalSupply + amount <= maxSupply)",
            "assert(totalMinted <= MAX_SUPPLY)",
        ],
        anti_examples=[
            "require(amount > 0)",
            "require(balances[msg.sender] >= amount)",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="invariants.no_invariant_check",
        category=LabelCategory.INVARIANTS,
        subcategory="no_invariant_check",
        description="Function has no explicit invariant enforcement",
        examples=[
            "function setConfig(uint256 value) external onlyOwner",
            "function pause() external onlyOwner",
        ],
        anti_examples=[
            "require(totalSupply + amount <= maxSupply)",
            "require(balances[msg.sender] >= amount)",
        ],
        negation_id=None,
    ),
    # TEMPORAL labels
    LabelDefinition(
        id="temporal.enforces_timelock",
        category=LabelCategory.TEMPORAL,
        subcategory="enforces_timelock",
        description="Function enforces timelock/delay requirements",
        examples=[
            "require(block.timestamp >= unlockTime)",
            "require(block.timestamp >= lastAction + delay)",
            "require(_timelockExpired(proposalId))",
        ],
        anti_examples=[
            "lastUpdated = block.timestamp",
            "emit Timestamp(block.timestamp)",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="temporal.checks_deadline",
        category=LabelCategory.TEMPORAL,
        subcategory="checks_deadline",
        description="Function checks transaction deadline",
        examples=[
            "require(block.timestamp <= deadline)",
            "require(deadline >= block.timestamp)",
            "if (block.timestamp > deadline) revert Expired()",
        ],
        anti_examples=[
            "require(block.timestamp >= unlockTime)",
            "lastUpdated = block.timestamp",
        ],
        negation_id=None,
    ),
    LabelDefinition(
        id="temporal.no_temporal_constraint",
        category=LabelCategory.TEMPORAL,
        subcategory="no_temporal_constraint",
        description="Function has no temporal constraints",
        examples=[
            "function transfer(address to, uint256 amount) external",
            "function approve(address spender, uint256 amount) external",
        ],
        anti_examples=[
            "require(block.timestamp <= deadline)",
            "require(block.timestamp >= unlockTime)",
        ],
        negation_id=None,
    ),
]

# Build lookup dictionaries
_LABELS_BY_ID: Dict[str, LabelDefinition] = {label.id: label for label in CORE_TAXONOMY}
_LABELS_BY_CATEGORY: Dict[LabelCategory, List[LabelDefinition]] = {}
for label in CORE_TAXONOMY:
    if label.category not in _LABELS_BY_CATEGORY:
        _LABELS_BY_CATEGORY[label.category] = []
    _LABELS_BY_CATEGORY[label.category].append(label)


def get_label_by_id(label_id: str) -> Optional[LabelDefinition]:
    """Get a label definition by its ID.

    Args:
        label_id: Label ID in category.subcategory format

    Returns:
        LabelDefinition if found, None otherwise
    """
    return _LABELS_BY_ID.get(label_id)


def get_labels_by_category(category: LabelCategory) -> List[LabelDefinition]:
    """Get all labels in a category.

    Args:
        category: Label category

    Returns:
        List of label definitions in the category
    """
    return _LABELS_BY_CATEGORY.get(category, [])


def is_valid_label(label_id: str) -> bool:
    """Check if a label ID is valid.

    Args:
        label_id: Label ID to validate

    Returns:
        True if label ID exists in taxonomy
    """
    return label_id in _LABELS_BY_ID


def get_negation(label_id: str) -> Optional[str]:
    """Get the negation label ID for a given label.

    Args:
        label_id: Label ID to find negation for

    Returns:
        Negation label ID if defined, None otherwise
    """
    label = _LABELS_BY_ID.get(label_id)
    return label.negation_id if label else None


def get_all_label_ids() -> List[str]:
    """Get all label IDs in the taxonomy.

    Returns:
        List of all valid label IDs
    """
    return list(_LABELS_BY_ID.keys())


__all__ = [
    "LabelCategory",
    "LabelDefinition",
    "CORE_TAXONOMY",
    "get_label_by_id",
    "get_labels_by_category",
    "is_valid_label",
    "get_negation",
    "get_all_label_ids",
]
