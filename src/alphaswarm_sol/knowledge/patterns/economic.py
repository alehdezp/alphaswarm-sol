"""
Economic Attack Patterns

Patterns for economic exploits and game theory attacks.
"""

from alphaswarm_sol.knowledge.adversarial_kg import (
    AttackPattern,
    AttackCategory,
    Severity,
)


# First Depositor / Inflation Attack
FIRST_DEPOSITOR_ATTACK = AttackPattern(
    id="first_depositor_attack",
    name="First Depositor Attack (ERC-4626 Inflation)",
    category=AttackCategory.ECONOMIC,
    severity=Severity.HIGH,
    description="First depositor can manipulate share price via donation",

    required_operations=["WRITES_USER_BALANCE", "PERFORMS_DIVISION"],
    supporting_operations=["TRANSFERS_VALUE_IN"],

    preconditions=["uses_share_calculation", "vault_like"],
    false_positive_indicators=["has_initial_deposit", "virtual_shares_offset"],

    violated_properties=["share_price_safety"],
    cwes=["CWE-682"],  # Incorrect Calculation

    detection_hints=[
        "Look for deposit/mint functions with share calculation",
        "Check if vault can start with zero shares",
        "Verify no initial deposit or virtual shares",
    ],

    remediation="Mint initial shares, use virtual shares offset, or require minimum deposit",

    known_exploits=["sentiment_protocol_2023"],
    related_patterns=["donation_attack"],
)


# MEV Sandwich Attack
MEV_SANDWICH_ATTACK = AttackPattern(
    id="mev_sandwich_attack",
    name="MEV Sandwich Attack",
    category=AttackCategory.MEV,
    severity=Severity.MEDIUM,
    description="Swap without slippage protection vulnerable to sandwiching",

    required_operations=["TRANSFERS_VALUE_OUT"],
    supporting_operations=["READS_ORACLE", "PERFORMS_DIVISION"],

    preconditions=["swap_like", "risk_missing_slippage_parameter"],
    false_positive_indicators=["has_slippage_parameter", "has_min_output"],

    violated_properties=["mev_protection"],
    cwes=["CWE-841"],  # Improper Enforcement of Behavioral Workflow

    detection_hints=[
        "Look for swap functions",
        "Check for missing minAmountOut parameter",
        "Verify no slippage tolerance",
    ],

    remediation="Add minAmountOut parameter and validate against actual output",

    known_exploits=[],
    related_patterns=["missing_deadline_check"],
)


# Missing Deadline Check
MISSING_DEADLINE_CHECK = AttackPattern(
    id="missing_deadline_check",
    name="Missing Transaction Deadline",
    category=AttackCategory.MEV,
    severity=Severity.LOW,
    description="Swap transaction without deadline can be delayed for better MEV extraction",

    required_operations=["TRANSFERS_VALUE_OUT"],
    supporting_operations=["READS_ORACLE"],

    preconditions=["swap_like", "risk_missing_deadline_check"],
    false_positive_indicators=["has_deadline_parameter", "checks_block_timestamp"],

    violated_properties=["transaction_timeliness"],
    cwes=["CWE-367"],  # Time-of-check Time-of-use

    detection_hints=[
        "Look for swap/trade functions",
        "Check for missing deadline parameter",
        "Verify no block.timestamp validation",
    ],

    remediation="Add deadline parameter and require(deadline >= block.timestamp)",

    known_exploits=[],
    related_patterns=["mev_sandwich_attack"],
)


# Flash Loan Governance Attack
FLASH_LOAN_GOVERNANCE = AttackPattern(
    id="flash_loan_governance_attack",
    name="Flash Loan Governance Attack",
    category=AttackCategory.GOVERNANCE,
    severity=Severity.CRITICAL,
    description="Governance voting based on token balance vulnerable to flash loans",

    required_operations=["READS_USER_BALANCE", "MODIFIES_CRITICAL_STATE"],
    supporting_operations=["CALLS_EXTERNAL"],

    preconditions=["governance_like", "snapshot_not_used"],
    false_positive_indicators=["uses_snapshot", "time_locked_voting"],

    violated_properties=["governance_safety"],
    cwes=["CWE-841"],

    detection_hints=[
        "Look for voting power based on current balance",
        "Check for missing snapshot mechanism",
        "Verify no time delay between proposal and vote",
    ],

    remediation="Use snapshot-based voting or time-locked voting power",

    known_exploits=["beanstalk_2022"],
    related_patterns=[],
)


# All economic patterns
ECONOMIC_PATTERNS = [
    FIRST_DEPOSITOR_ATTACK,
    MEV_SANDWICH_ATTACK,
    MISSING_DEADLINE_CHECK,
    FLASH_LOAN_GOVERNANCE,
]
