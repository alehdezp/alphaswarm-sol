"""
Access Control Attack Patterns

Patterns for detecting missing or broken access controls.
"""

from alphaswarm_sol.knowledge.adversarial_kg import (
    AttackPattern,
    AttackCategory,
    Severity,
)


# Unprotected Privileged Function
UNPROTECTED_FUNCTION = AttackPattern(
    id="unprotected_privileged_function",
    name="Unprotected Privileged Function",
    category=AttackCategory.ACCESS_CONTROL,
    severity=Severity.CRITICAL,
    description="Public/external function modifies privileged state without access control",

    required_operations=["MODIFIES_CRITICAL_STATE"],
    supporting_operations=["MODIFIES_OWNER", "MODIFIES_ROLES", "TRANSFERS_VALUE_OUT"],

    preconditions=["writes_privileged_state"],
    false_positive_indicators=[
        "has_access_gate",
        "has_onlyOwner_modifier",
        "has_role_check",
    ],

    violated_properties=["access_control"],
    cwes=["CWE-284"],  # Improper Access Control

    detection_hints=[
        "Look for public/external functions writing to owner/admin/role state",
        "Check for missing onlyOwner/onlyRole modifiers",
        "Verify no require() checks for msg.sender permissions",
    ],

    remediation="Add access control modifiers (onlyOwner, onlyRole) or require() checks",

    known_exploits=["poly_network_2021"],
    related_patterns=["tx_origin_auth", "missing_zero_address"],
)


# tx.origin Authentication
TX_ORIGIN_AUTH = AttackPattern(
    id="tx_origin_authentication",
    name="tx.origin Authentication",
    category=AttackCategory.ACCESS_CONTROL,
    severity=Severity.HIGH,
    description="Using tx.origin for authentication vulnerable to phishing attacks",

    required_operations=["MODIFIES_CRITICAL_STATE"],
    supporting_operations=["TRANSFERS_VALUE_OUT"],

    preconditions=["uses_tx_origin"],
    false_positive_indicators=["uses_msg_sender_instead"],

    violated_properties=["secure_authentication"],
    cwes=["CWE-829"],  # Inclusion of Functionality from Untrusted Control Sphere

    detection_hints=[
        "Look for tx.origin in access control checks",
        "Check if tx.origin == owner pattern is used",
        "Verify msg.sender is used instead",
    ],

    remediation="Replace tx.origin with msg.sender for access control",

    known_exploits=[],
    related_patterns=["unprotected_privileged_function"],
)


# Missing Zero Address Check
MISSING_ZERO_ADDRESS = AttackPattern(
    id="missing_zero_address_check",
    name="Missing Zero Address Validation",
    category=AttackCategory.ACCESS_CONTROL,
    severity=Severity.MEDIUM,
    description="Critical address assignments without zero address validation",

    required_operations=["MODIFIES_OWNER"],
    supporting_operations=["MODIFIES_ROLES"],

    preconditions=["assigns_critical_address"],
    false_positive_indicators=["checks_zero_address"],

    violated_properties=["input_validation"],
    cwes=["CWE-20"],  # Improper Input Validation

    detection_hints=[
        "Look for owner/admin address assignments",
        "Check for missing address(0) validation",
        "Verify no require(addr != address(0))",
    ],

    remediation="Add require(newAddress != address(0)) before assignment",

    known_exploits=[],
    related_patterns=["unprotected_privileged_function"],
)


# Public Wrapper Without Access Gate
PUBLIC_WRAPPER_NO_GATE = AttackPattern(
    id="public_wrapper_without_access_gate",
    name="Public Wrapper Without Access Gate",
    category=AttackCategory.ACCESS_CONTROL,
    severity=Severity.HIGH,
    description="Public function wraps privileged operation without adding access control",

    required_operations=["WRITES_PRIVILEGED_STATE"],

    preconditions=["public_wrapper_without_access_gate"],
    false_positive_indicators=["has_access_gate"],

    violated_properties=["access_control"],
    cwes=["CWE-284"],

    detection_hints=[
        "Look for public functions calling internal privileged operations",
        "Check if wrapper adds any access control",
        "Verify no modifier or require() guards wrapper",
    ],

    remediation="Add access control to public wrapper or make it internal/private",

    known_exploits=[],
    related_patterns=["unprotected_privileged_function"],
)


# All access control patterns
ACCESS_CONTROL_PATTERNS = [
    UNPROTECTED_FUNCTION,
    TX_ORIGIN_AUTH,
    MISSING_ZERO_ADDRESS,
    PUBLIC_WRAPPER_NO_GATE,
]
