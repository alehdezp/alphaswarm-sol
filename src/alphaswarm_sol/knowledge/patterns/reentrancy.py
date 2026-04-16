"""
Reentrancy Attack Patterns

Patterns for detecting reentrancy vulnerabilities in various forms.
"""

from alphaswarm_sol.knowledge.adversarial_kg import (
    AttackPattern,
    AttackCategory,
    Severity,
)


# Classic Reentrancy (The DAO style)
REENTRANCY_CLASSIC = AttackPattern(
    id="reentrancy_classic",
    name="Classic Reentrancy",
    category=AttackCategory.REENTRANCY,
    severity=Severity.CRITICAL,
    description="External call before state update allows reentrant calls to drain funds",

    required_operations=["TRANSFERS_VALUE_OUT", "WRITES_USER_BALANCE"],
    operation_sequence=r".*X:out.*W:bal.*",
    supporting_operations=["READS_USER_BALANCE"],

    preconditions=["state_write_after_external_call"],
    false_positive_indicators=[
        "has_reentrancy_guard",
        "uses_checks_effects_interactions",
    ],

    violated_properties=["checks_effects_interactions"],
    cwes=["CWE-841"],  # Improper Enforcement of Behavioral Workflow

    detection_hints=[
        "Look for external calls before balance updates",
        "Check if state changes happen after call{value:}",
        "Verify no reentrancy guard modifier",
    ],

    remediation="Use checks-effects-interactions pattern: update state before external calls, or add reentrancy guard",

    known_exploits=["the_dao_2016"],
    related_patterns=["reentrancy_cross_function", "reentrancy_read_only"],
)


# Cross-Function Reentrancy
REENTRANCY_CROSS_FUNCTION = AttackPattern(
    id="reentrancy_cross_function",
    name="Cross-Function Reentrancy",
    category=AttackCategory.REENTRANCY,
    severity=Severity.HIGH,
    description="Reentrancy across different functions sharing state",

    required_operations=["CALLS_EXTERNAL", "WRITES_CRITICAL_STATE"],
    operation_sequence=r".*X:out.*W:.*",

    preconditions=["state_write_after_external_call"],
    false_positive_indicators=["has_reentrancy_guard"],

    violated_properties=["state_isolation"],
    cwes=["CWE-841"],

    detection_hints=[
        "Look for shared state between functions",
        "Check if callback can call other state-modifying functions",
        "Verify state updates happen after all external calls",
    ],

    remediation="Use contract-wide reentrancy guard or update all shared state before external calls",

    known_exploits=["cream_finance_2021"],
    related_patterns=["reentrancy_classic"],
)


# Read-Only Reentrancy
REENTRANCY_READ_ONLY = AttackPattern(
    id="reentrancy_read_only",
    name="Read-Only Reentrancy",
    category=AttackCategory.REENTRANCY,
    severity=Severity.MEDIUM,
    description="External call allows reentrant read of stale state",

    required_operations=["CALLS_EXTERNAL", "READS_EXTERNAL_VALUE"],
    supporting_operations=["WRITES_CRITICAL_STATE"],

    preconditions=["external_call_before_state_update"],
    false_positive_indicators=["has_reentrancy_guard", "read_only_function"],

    violated_properties=["view_function_safety"],
    cwes=["CWE-367"],  # Time-of-check Time-of-use

    detection_hints=[
        "Look for view functions called during state transitions",
        "Check if external calls happen before critical state updates",
        "Verify callers of view functions can't exploit stale reads",
    ],

    remediation="Update state before external calls, or use view function guards",

    known_exploits=[],
    related_patterns=["reentrancy_classic"],
)


# All reentrancy patterns
REENTRANCY_PATTERNS = [
    REENTRANCY_CLASSIC,
    REENTRANCY_CROSS_FUNCTION,
    REENTRANCY_READ_ONLY,
]
