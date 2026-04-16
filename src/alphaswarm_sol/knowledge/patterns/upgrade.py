"""
Upgrade/Proxy Attack Patterns

Patterns for proxy and upgrade vulnerabilities.
"""

from alphaswarm_sol.knowledge.adversarial_kg import (
    AttackPattern,
    AttackCategory,
    Severity,
)


# Uninitialized Proxy
UNINITIALIZED_PROXY = AttackPattern(
    id="uninitialized_proxy",
    name="Uninitialized Proxy",
    category=AttackCategory.UPGRADE,
    severity=Severity.CRITICAL,
    description="Proxy implementation can be initialized by attacker",

    required_operations=["MODIFIES_CRITICAL_STATE"],
    supporting_operations=["MODIFIES_OWNER"],

    preconditions=["is_initializer", "proxy_like"],
    false_positive_indicators=["has_initializer_modifier", "already_initialized"],

    violated_properties=["initialization_safety"],
    cwes=["CWE-665"],  # Improper Initialization

    detection_hints=[
        "Look for initialize() functions in implementation",
        "Check if initializer modifier prevents reinitialization",
        "Verify proxy calls initialize on deployment",
    ],

    remediation="Use initializer modifier and call initialize in constructor/deployment script",

    known_exploits=["wormhole_2022"],
    related_patterns=["storage_collision"],
)


# Storage Collision
STORAGE_COLLISION = AttackPattern(
    id="storage_collision",
    name="Storage Collision",
    category=AttackCategory.UPGRADE,
    severity=Severity.HIGH,
    description="Proxy and implementation have overlapping storage slots",

    required_operations=["WRITES_CRITICAL_STATE"],

    preconditions=["proxy_like", "uses_storage_slot"],
    false_positive_indicators=["uses_storage_gap", "uses_erc1967_slots"],

    violated_properties=["storage_safety"],
    cwes=["CWE-662"],  # Improper Synchronization

    detection_hints=[
        "Look for storage variable declarations in proxy and implementation",
        "Check storage layout compatibility",
        "Verify ERC-1967 storage slots used for proxy state",
    ],

    remediation="Use ERC-1967 storage slots for proxy state, add __gap[] in base contracts",

    known_exploits=[],
    related_patterns=["missing_storage_gap"],
)


# Missing Storage Gap
MISSING_STORAGE_GAP = AttackPattern(
    id="missing_storage_gap",
    name="Missing Storage Gap",
    category=AttackCategory.UPGRADE,
    severity=Severity.MEDIUM,
    description="Upgradeable contract without storage gap risks future collisions",

    required_operations=["MODIFIES_CRITICAL_STATE"],

    preconditions=["upgradeable_without_storage_gap", "is_base_contract"],
    false_positive_indicators=["has_storage_gap"],

    violated_properties=["upgrade_safety"],
    cwes=["CWE-662"],

    detection_hints=[
        "Look for upgradeable base contracts",
        "Check for missing __gap[] array",
        "Verify storage layout leaves room for future variables",
    ],

    remediation="Add uint256[50] private __gap; to base contracts",

    known_exploits=[],
    related_patterns=["storage_collision"],
)


# Unprotected Upgrade
UNPROTECTED_UPGRADE = AttackPattern(
    id="unprotected_upgrade",
    name="Unprotected Upgrade Function",
    category=AttackCategory.UPGRADE,
    severity=Severity.CRITICAL,
    description="Upgrade function callable by anyone",

    required_operations=["MODIFIES_CRITICAL_STATE"],
    supporting_operations=["CALLS_EXTERNAL"],

    preconditions=["is_upgrade_function", "writes_implementation_address"],
    false_positive_indicators=["has_access_gate", "has_onlyOwner_modifier"],

    violated_properties=["upgrade_authorization"],
    cwes=["CWE-284"],  # Improper Access Control

    detection_hints=[
        "Look for upgradeTo/upgradeToAndCall functions",
        "Check for missing access control",
        "Verify only authorized roles can upgrade",
    ],

    remediation="Add onlyOwner or role-based access control to upgrade functions",

    known_exploits=[],
    related_patterns=["unprotected_privileged_function"],
)


# Delegatecall to Untrusted
DELEGATECALL_UNTRUSTED = AttackPattern(
    id="delegatecall_to_untrusted",
    name="Delegatecall to Untrusted Contract",
    category=AttackCategory.UPGRADE,
    severity=Severity.CRITICAL,
    description="Delegatecall to user-controlled address allows arbitrary code execution",

    required_operations=["CALLS_EXTERNAL"],

    preconditions=["uses_delegatecall", "untrusted_target"],
    false_positive_indicators=["trusted_implementation_only", "whitelist_check"],

    violated_properties=["delegatecall_safety"],
    cwes=["CWE-829"],  # Inclusion of Functionality from Untrusted Control Sphere

    detection_hints=[
        "Look for delegatecall usage",
        "Check if target address is user-controlled",
        "Verify whitelist or immutable implementation",
    ],

    remediation="Only delegatecall to trusted/whitelisted implementations",

    known_exploits=["parity_wallet_2017"],
    related_patterns=["unprotected_upgrade"],
)


# All upgrade patterns
UPGRADE_PATTERNS = [
    UNINITIALIZED_PROXY,
    STORAGE_COLLISION,
    MISSING_STORAGE_GAP,
    UNPROTECTED_UPGRADE,
    DELEGATECALL_UNTRUSTED,
]
