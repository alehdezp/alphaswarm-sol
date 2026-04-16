"""
Oracle Manipulation Attack Patterns

Patterns for detecting oracle-related vulnerabilities.
"""

from alphaswarm_sol.knowledge.adversarial_kg import (
    AttackPattern,
    AttackCategory,
    Severity,
)


# Spot Price Manipulation
SPOT_PRICE_MANIPULATION = AttackPattern(
    id="spot_price_manipulation",
    name="Spot Price Manipulation",
    category=AttackCategory.ORACLE_MANIPULATION,
    severity=Severity.CRITICAL,
    description="Using spot price from DEX susceptible to flash loan manipulation",

    required_operations=["READS_ORACLE", "TRANSFERS_VALUE_OUT"],
    supporting_operations=["PERFORMS_DIVISION"],

    preconditions=["reads_oracle_price", "uses_spot_price"],
    false_positive_indicators=["uses_twap", "uses_chainlink"],

    violated_properties=["price_oracle_safety"],
    cwes=["CWE-682"],  # Incorrect Calculation

    detection_hints=[
        "Look for direct calls to pair.getReserves()",
        "Check if price comes from single block",
        "Verify no TWAP or external oracle used",
    ],

    remediation="Use TWAP (time-weighted average price) or Chainlink price feeds",

    known_exploits=["cream_finance_2021", "harvest_finance_2020"],
    related_patterns=["missing_twap_window"],
)


# Stale Oracle Data
STALE_ORACLE_DATA = AttackPattern(
    id="stale_oracle_data",
    name="Stale Oracle Data",
    category=AttackCategory.ORACLE_MANIPULATION,
    severity=Severity.HIGH,
    description="Using oracle price data without staleness check",

    required_operations=["READS_ORACLE"],
    supporting_operations=["TRANSFERS_VALUE_OUT", "PERFORMS_DIVISION"],

    preconditions=["reads_oracle_price"],
    false_positive_indicators=["has_staleness_check", "checks_updated_at"],

    violated_properties=["oracle_freshness"],
    cwes=["CWE-367"],  # Time-of-check Time-of-use

    detection_hints=[
        "Look for Chainlink price feed usage",
        "Check for missing updatedAt timestamp validation",
        "Verify no heartbeat/staleness threshold",
    ],

    remediation="Check updatedAt timestamp and compare against acceptable staleness threshold",

    known_exploits=["venus_protocol_2021"],
    related_patterns=["missing_sequencer_uptime"],
)


# Missing L2 Sequencer Uptime Check
MISSING_SEQUENCER_UPTIME = AttackPattern(
    id="missing_l2_sequencer_uptime_check",
    name="Missing L2 Sequencer Uptime Check",
    category=AttackCategory.ORACLE_MANIPULATION,
    severity=Severity.HIGH,
    description="L2 oracle usage without sequencer uptime validation",

    required_operations=["READS_ORACLE"],
    supporting_operations=["TRANSFERS_VALUE_OUT"],

    preconditions=["reads_oracle_price", "deployed_on_l2"],
    false_positive_indicators=["has_sequencer_uptime_check", "checks_sequencer_feed"],

    violated_properties=["l2_oracle_safety"],
    cwes=["CWE-367"],

    detection_hints=[
        "Look for Chainlink usage on Arbitrum/Optimism",
        "Check for missing sequencer uptime feed validation",
        "Verify no grace period after sequencer restart",
    ],

    remediation="Check sequencer uptime feed before using price data on L2",

    known_exploits=[],
    related_patterns=["stale_oracle_data"],
)


# Missing TWAP Window
MISSING_TWAP_WINDOW = AttackPattern(
    id="missing_twap_window",
    name="Insufficient TWAP Window",
    category=AttackCategory.ORACLE_MANIPULATION,
    severity=Severity.MEDIUM,
    description="TWAP window too short to prevent manipulation",

    required_operations=["READS_ORACLE"],
    supporting_operations=["PERFORMS_DIVISION"],

    preconditions=["uses_twap"],
    false_positive_indicators=["twap_window_sufficient"],

    violated_properties=["twap_safety"],
    cwes=["CWE-682"],

    detection_hints=[
        "Look for TWAP implementations",
        "Check window size (< 30 minutes risky)",
        "Verify observation count is sufficient",
    ],

    remediation="Use TWAP window >= 30 minutes with multiple observations",

    known_exploits=[],
    related_patterns=["spot_price_manipulation"],
)


# All oracle patterns
ORACLE_PATTERNS = [
    SPOT_PRICE_MANIPULATION,
    STALE_ORACLE_DATA,
    MISSING_SEQUENCER_UPTIME,
    MISSING_TWAP_WINDOW,
]
