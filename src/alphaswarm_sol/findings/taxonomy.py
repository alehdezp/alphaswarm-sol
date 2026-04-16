"""
Pattern Taxonomy Mapping (Task 3.16)

Maps VKG patterns to standard vulnerability taxonomies:
- SWC (Smart Contract Weakness Classification): https://swcregistry.io/
- CWE (Common Weakness Enumeration): https://cwe.mitre.org/
- OWASP Smart Contract Top 10 (2025 Draft)

Philosophy: Every finding should be traceable to industry standards
for compliance, reporting, and cross-tool comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaxonomyMapping:
    """Maps a pattern to standard vulnerability classifications."""

    swc: list[str] = field(default_factory=list)  # SWC-XXX codes
    cwe: list[str] = field(default_factory=list)  # CWE-XXX codes
    owasp_sc: list[str] = field(default_factory=list)  # SC01-SC10 codes
    dasp: list[str] = field(default_factory=list)  # DASP Top 10 (legacy)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "swc": self.swc,
            "cwe": self.cwe,
            "owasp_sc": self.owasp_sc,
            "dasp": self.dasp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaxonomyMapping":
        """Create from dictionary."""
        return cls(
            swc=data.get("swc", []),
            cwe=data.get("cwe", []),
            owasp_sc=data.get("owasp_sc", []),
            dasp=data.get("dasp", []),
        )

    def primary_swc(self) -> str:
        """Return primary SWC code or empty string."""
        return self.swc[0] if self.swc else ""

    def primary_cwe(self) -> str:
        """Return primary CWE code or empty string."""
        return self.cwe[0] if self.cwe else ""


# =============================================================================
# TAXONOMY REGISTRY
# =============================================================================
# Comprehensive mapping of VKG patterns to standard classifications.
# Sources:
#   - SWC: https://swcregistry.io/
#   - CWE: https://cwe.mitre.org/data/definitions/
#   - OWASP Smart Contract Top 10: https://owasp.org/www-project-smart-contract-top-10/
#   - DASP: https://dasp.co/ (legacy, superseded by SWC)
#
# Format: pattern_id_or_prefix -> TaxonomyMapping
# =============================================================================

TAXONOMY_REGISTRY: dict[str, TaxonomyMapping] = {
    # =========================================================================
    # REENTRANCY PATTERNS
    # =========================================================================
    "reentrancy": TaxonomyMapping(
        swc=["SWC-107"],  # Reentrancy
        cwe=["CWE-841"],  # Improper Enforcement of Behavioral Workflow
        owasp_sc=["SC05"],  # Reentrancy
        dasp=["DASP-1"],  # Reentrancy
    ),
    "reentrancy-basic": TaxonomyMapping(
        swc=["SWC-107"],
        cwe=["CWE-841"],
        owasp_sc=["SC05"],
        dasp=["DASP-1"],
    ),
    "reentrancy-classic": TaxonomyMapping(
        swc=["SWC-107"],
        cwe=["CWE-841"],
        owasp_sc=["SC05"],
        dasp=["DASP-1"],
    ),
    "vm-001": TaxonomyMapping(  # Classic reentrancy
        swc=["SWC-107"],
        cwe=["CWE-841"],
        owasp_sc=["SC05"],
        dasp=["DASP-1"],
    ),
    "vm-001-classic": TaxonomyMapping(
        swc=["SWC-107"],
        cwe=["CWE-841"],
        owasp_sc=["SC05"],
        dasp=["DASP-1"],
    ),
    "state-write-after-call": TaxonomyMapping(
        swc=["SWC-107"],
        cwe=["CWE-841"],
        owasp_sc=["SC05"],
        dasp=["DASP-1"],
    ),
    "token-002-erc777-reentrancy": TaxonomyMapping(
        swc=["SWC-107"],
        cwe=["CWE-841"],
        owasp_sc=["SC05"],
        dasp=["DASP-1"],
    ),

    # =========================================================================
    # ACCESS CONTROL PATTERNS
    # =========================================================================
    "auth": TaxonomyMapping(
        swc=["SWC-105"],  # Unprotected Ether Withdrawal
        cwe=["CWE-284", "CWE-285"],  # Improper Access Control, Improper Authorization
        owasp_sc=["SC01"],  # Access Control
        dasp=["DASP-2"],  # Access Control
    ),
    "weak-access-control": TaxonomyMapping(
        swc=["SWC-105", "SWC-106"],  # + Unprotected SELFDESTRUCT
        cwe=["CWE-284", "CWE-285", "CWE-862"],  # + Missing Authorization
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "auth-001": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284", "CWE-862"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "auth-003-unprotected-privileged-write": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284", "CWE-862"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "auth-005-unprotected-list-management": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284", "CWE-862"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "initializer-no-gate": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284", "CWE-665"],  # + Improper Initialization
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),

    # =========================================================================
    # TX.ORIGIN PATTERNS
    # =========================================================================
    "tx-origin": TaxonomyMapping(
        swc=["SWC-115"],  # Authorization through tx.origin
        cwe=["CWE-477"],  # Use of Obsolete Function
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "tx-origin-auth": TaxonomyMapping(
        swc=["SWC-115"],
        cwe=["CWE-477"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "tx-origin-public": TaxonomyMapping(
        swc=["SWC-115"],
        cwe=["CWE-477"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),

    # =========================================================================
    # DELEGATECALL PATTERNS
    # =========================================================================
    "delegatecall": TaxonomyMapping(
        swc=["SWC-112"],  # Delegatecall to Untrusted Callee
        cwe=["CWE-829"],  # Inclusion of Functionality from Untrusted Control Sphere
        owasp_sc=["SC06"],  # Unchecked External Calls
        dasp=["DASP-3"],  # Bad Randomness (also covers delegate)
    ),
    "delegatecall-public": TaxonomyMapping(
        swc=["SWC-112"],
        cwe=["CWE-829"],
        owasp_sc=["SC06"],
        dasp=["DASP-6"],  # Bad Randomness / Delegatecall
    ),
    "delegatecall-no-gate": TaxonomyMapping(
        swc=["SWC-112"],
        cwe=["CWE-829"],
        owasp_sc=["SC06"],
        dasp=["DASP-6"],
    ),
    "upgrade-008-delegatecall-untrusted": TaxonomyMapping(
        swc=["SWC-112"],
        cwe=["CWE-829"],
        owasp_sc=["SC06"],
        dasp=["DASP-6"],
    ),
    "external-002-unprotected-delegatecall": TaxonomyMapping(
        swc=["SWC-112"],
        cwe=["CWE-829"],
        owasp_sc=["SC06"],
        dasp=["DASP-6"],
    ),

    # =========================================================================
    # LOW-LEVEL CALL PATTERNS
    # =========================================================================
    "low-level-call": TaxonomyMapping(
        swc=["SWC-104", "SWC-126"],  # Unchecked Call Return Value, Insufficient Gas Griefing
        cwe=["CWE-252", "CWE-754"],  # Unchecked Return Value, Improper Check for Unusual Conditions
        owasp_sc=["SC06"],
        dasp=["DASP-4"],  # Unchecked Return Values
    ),
    "low-level-call-public": TaxonomyMapping(
        swc=["SWC-104"],
        cwe=["CWE-252"],
        owasp_sc=["SC06"],
        dasp=["DASP-4"],
    ),
    "low-level-call-no-gate": TaxonomyMapping(
        swc=["SWC-104"],
        cwe=["CWE-252"],
        owasp_sc=["SC06"],
        dasp=["DASP-4"],
    ),
    "ext-001-unprotected-external-call": TaxonomyMapping(
        swc=["SWC-104"],
        cwe=["CWE-252"],
        owasp_sc=["SC06"],
        dasp=["DASP-4"],
    ),

    # =========================================================================
    # ORACLE PATTERNS
    # =========================================================================
    "oracle": TaxonomyMapping(
        swc=["SWC-120"],  # Weak Sources of Randomness (includes oracle manipulation)
        cwe=["CWE-330", "CWE-807"],  # Insufficient Randomness, Reliance on Untrusted Inputs
        owasp_sc=["SC02"],  # Oracle Manipulation
        dasp=["DASP-6"],  # Bad Randomness
    ),
    "oracle-manipulation": TaxonomyMapping(
        swc=["SWC-120"],
        cwe=["CWE-330", "CWE-807"],
        owasp_sc=["SC02"],
        dasp=["DASP-6"],
    ),
    "oracle-001-freshness-complete": TaxonomyMapping(
        swc=["SWC-120"],
        cwe=["CWE-807"],
        owasp_sc=["SC02"],
        dasp=["DASP-6"],
    ),
    "oracle-003-missing-staleness-check": TaxonomyMapping(
        swc=["SWC-120"],
        cwe=["CWE-807"],
        owasp_sc=["SC02"],
        dasp=["DASP-6"],
    ),
    "oracle-004-missing-sequencer-check": TaxonomyMapping(
        swc=["SWC-120"],
        cwe=["CWE-807"],
        owasp_sc=["SC02"],
        dasp=["DASP-6"],
    ),
    "oracle-005-twap-missing-window": TaxonomyMapping(
        swc=["SWC-120"],
        cwe=["CWE-807"],
        owasp_sc=["SC02"],
        dasp=["DASP-6"],
    ),

    # =========================================================================
    # ARITHMETIC PATTERNS
    # =========================================================================
    "arithmetic": TaxonomyMapping(
        swc=["SWC-101"],  # Integer Overflow and Underflow
        cwe=["CWE-190", "CWE-191"],  # Integer Overflow, Integer Underflow
        owasp_sc=["SC08"],  # Integer Overflow
        dasp=["DASP-5"],  # Arithmetic Issues
    ),
    "amount-division-without-precision-guard": TaxonomyMapping(
        swc=["SWC-101"],
        cwe=["CWE-190", "CWE-682"],  # + Incorrect Calculation
        owasp_sc=["SC08"],
        dasp=["DASP-5"],
    ),

    # =========================================================================
    # DoS PATTERNS
    # =========================================================================
    "dos": TaxonomyMapping(
        swc=["SWC-113", "SWC-128"],  # DoS with Failed Call, DoS with Block Gas Limit
        cwe=["CWE-400", "CWE-770"],  # Uncontrolled Resource Consumption, Allocation without Limits
        owasp_sc=["SC10"],  # DoS
        dasp=["DASP-7"],  # Denial of Service
    ),
    "dos-unbounded-loop": TaxonomyMapping(
        swc=["SWC-128"],
        cwe=["CWE-400", "CWE-770"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),
    "dos-unbounded-mass-operation": TaxonomyMapping(
        swc=["SWC-128"],
        cwe=["CWE-400", "CWE-770"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),
    "dos-unbounded-deletion": TaxonomyMapping(
        swc=["SWC-128"],
        cwe=["CWE-400"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),
    "dos-user-controlled-batch": TaxonomyMapping(
        swc=["SWC-128"],
        cwe=["CWE-400", "CWE-770"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),
    "dos-transfer-in-loop": TaxonomyMapping(
        swc=["SWC-113"],
        cwe=["CWE-400"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),
    "dos-strict-equality": TaxonomyMapping(
        swc=["SWC-132"],  # Unexpected Ether Balance
        cwe=["CWE-400"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),
    "dos-revert-failed-call": TaxonomyMapping(
        swc=["SWC-113"],
        cwe=["CWE-400"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),
    "dos-array-return-unbounded": TaxonomyMapping(
        swc=["SWC-128"],
        cwe=["CWE-400"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),

    # =========================================================================
    # SIGNATURE / CRYPTO PATTERNS
    # =========================================================================
    "crypto": TaxonomyMapping(
        swc=["SWC-117", "SWC-122"],  # Signature Malleability, Lack of Proper Signature Verification
        cwe=["CWE-347", "CWE-327"],  # Improper Verification of Crypto Signature, Use of Broken Crypto
        owasp_sc=["SC04"],  # Input Validation (includes signatures)
        dasp=["DASP-9"],  # Short Address Attack (crypto related)
    ),
    "crypto-signature-malleability": TaxonomyMapping(
        swc=["SWC-117"],
        cwe=["CWE-347"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "crypto-signature-replay": TaxonomyMapping(
        swc=["SWC-121"],  # Missing Protection against Signature Replay
        cwe=["CWE-294"],  # Authentication Bypass by Capture-replay
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "crypto-signature-incomplete": TaxonomyMapping(
        swc=["SWC-122"],
        cwe=["CWE-347"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "crypto-zero-address-check": TaxonomyMapping(
        swc=["SWC-122"],
        cwe=["CWE-20"],  # Improper Input Validation
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "crypto-missing-chainid": TaxonomyMapping(
        swc=["SWC-121"],
        cwe=["CWE-294"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "crypto-missing-deadline": TaxonomyMapping(
        swc=["SWC-121"],
        cwe=["CWE-613"],  # Insufficient Session Expiration
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "crypto-permit-incomplete": TaxonomyMapping(
        swc=["SWC-122"],
        cwe=["CWE-347"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),

    # =========================================================================
    # PROXY/UPGRADE PATTERNS
    # =========================================================================
    "proxy": TaxonomyMapping(
        swc=["SWC-112", "SWC-106"],  # Delegatecall, Unprotected SELFDESTRUCT
        cwe=["CWE-829", "CWE-665"],  # + Improper Initialization
        owasp_sc=["SC01", "SC06"],
        dasp=["DASP-2"],
    ),
    "proxy-upgrade-surface": TaxonomyMapping(
        swc=["SWC-112"],
        cwe=["CWE-829"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "proxy-uninitialized-implementation": TaxonomyMapping(
        swc=["SWC-109"],  # Uninitialized Storage Pointer
        cwe=["CWE-665"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "proxy-storage-collision-risk": TaxonomyMapping(
        swc=["SWC-124"],  # Write to Arbitrary Storage Location
        cwe=["CWE-787"],  # Out-of-bounds Write
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "proxy-selector-clash-risk": TaxonomyMapping(
        swc=["SWC-124"],
        cwe=["CWE-694"],  # Use of Multiple Resources with Duplicate Identifier
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "upgrade-004-unprotected-reinitializer": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284", "CWE-665"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "upgrade-005-unprotected-initializer": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284", "CWE-665"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "upgrade-007-unprotected-upgrade": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "upgrade-010-selfdestruct-in-implementation": TaxonomyMapping(
        swc=["SWC-106"],
        cwe=["CWE-749"],  # Exposed Dangerous Method or Function
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),

    # =========================================================================
    # MEV PATTERNS
    # =========================================================================
    "mev": TaxonomyMapping(
        swc=["SWC-114"],  # Transaction Order Dependence
        cwe=["CWE-362"],  # Concurrent Execution using Shared Resource with Improper Synchronization
        owasp_sc=["SC07"],  # Flash Loan Attacks (MEV related)
        dasp=["DASP-8"],  # Front-Running
    ),
    "mev-risk-high": TaxonomyMapping(
        swc=["SWC-114"],
        cwe=["CWE-362"],
        owasp_sc=["SC07"],
        dasp=["DASP-8"],
    ),
    "mev-risk-medium": TaxonomyMapping(
        swc=["SWC-114"],
        cwe=["CWE-362"],
        owasp_sc=["SC07"],
        dasp=["DASP-8"],
    ),
    "mev-missing-slippage-parameter": TaxonomyMapping(
        swc=["SWC-114"],
        cwe=["CWE-362"],
        owasp_sc=["SC07"],
        dasp=["DASP-8"],
    ),
    "mev-missing-deadline-parameter": TaxonomyMapping(
        swc=["SWC-114"],
        cwe=["CWE-613"],
        owasp_sc=["SC07"],
        dasp=["DASP-8"],
    ),

    # =========================================================================
    # TOKEN PATTERNS
    # =========================================================================
    "token": TaxonomyMapping(
        swc=["SWC-104"],  # Unchecked Call Return Value
        cwe=["CWE-252"],
        owasp_sc=["SC06"],
        dasp=["DASP-4"],
    ),
    "token-001-unhandled-fee-on-transfer": TaxonomyMapping(
        swc=["SWC-104"],
        cwe=["CWE-682"],  # Incorrect Calculation
        owasp_sc=["SC03"],  # Logic Errors
        dasp=["DASP-4"],
    ),
    "token-004-non-standard-return": TaxonomyMapping(
        swc=["SWC-104"],
        cwe=["CWE-252"],
        owasp_sc=["SC06"],
        dasp=["DASP-4"],
    ),
    "token-005-unchecked-return": TaxonomyMapping(
        swc=["SWC-104"],
        cwe=["CWE-252"],
        owasp_sc=["SC06"],
        dasp=["DASP-4"],
    ),
    "token-006-approval-race-condition": TaxonomyMapping(
        swc=["SWC-114"],
        cwe=["CWE-362"],
        owasp_sc=["SC07"],
        dasp=["DASP-8"],
    ),

    # =========================================================================
    # GOVERNANCE PATTERNS
    # =========================================================================
    "governance": TaxonomyMapping(
        swc=["SWC-114"],
        cwe=["CWE-362"],
        owasp_sc=["SC01", "SC07"],
        dasp=["DASP-2", "DASP-8"],
    ),
    "governance-vote-without-snapshot": TaxonomyMapping(
        swc=["SWC-114"],
        cwe=["CWE-362"],
        owasp_sc=["SC07"],
        dasp=["DASP-8"],
    ),

    # =========================================================================
    # MULTISIG PATTERNS
    # =========================================================================
    "multisig": TaxonomyMapping(
        swc=["SWC-121"],  # Missing Signature Replay Protection
        cwe=["CWE-294"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "multisig-001-execution-without-nonce": TaxonomyMapping(
        swc=["SWC-121"],
        cwe=["CWE-294"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "multisig-003-execution-without-signature-validation": TaxonomyMapping(
        swc=["SWC-122"],
        cwe=["CWE-347"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),

    # =========================================================================
    # INPUT VALIDATION PATTERNS
    # =========================================================================
    "input": TaxonomyMapping(
        swc=["SWC-100", "SWC-129"],  # Function Default Visibility, Typographical Error
        cwe=["CWE-20"],  # Improper Input Validation
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "array-length-missing-check": TaxonomyMapping(
        swc=["SWC-129"],
        cwe=["CWE-20", "CWE-131"],  # + Incorrect Calculation of Buffer Size
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "array-length-mismatch": TaxonomyMapping(
        swc=["SWC-129"],
        cwe=["CWE-20", "CWE-131"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "array-index-without-check": TaxonomyMapping(
        swc=["SWC-129"],
        cwe=["CWE-129"],  # Improper Validation of Array Index
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "calldata-slice-without-length-check": TaxonomyMapping(
        swc=["SWC-129"],
        cwe=["CWE-129"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "abi-decode-without-length-check": TaxonomyMapping(
        swc=["SWC-129"],
        cwe=["CWE-129"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),

    # =========================================================================
    # EMERGENCY / FALLBACK PATTERNS
    # =========================================================================
    "emergency": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "emergency-001-unprotected-recovery": TaxonomyMapping(
        swc=["SWC-105"],
        cwe=["CWE-284"],
        owasp_sc=["SC01"],
        dasp=["DASP-2"],
    ),
    "payable-fallback-receive": TaxonomyMapping(
        swc=["SWC-132"],  # Unexpected Ether Balance
        cwe=["CWE-400"],
        owasp_sc=["SC10"],
        dasp=["DASP-7"],
    ),

    # =========================================================================
    # MISC PATTERNS
    # =========================================================================
    "merkle-leaf-without-domain-separation": TaxonomyMapping(
        swc=["SWC-117"],
        cwe=["CWE-347"],
        owasp_sc=["SC04"],
        dasp=["DASP-9"],
    ),
    "invariant-touch-without-check": TaxonomyMapping(
        swc=["SWC-110"],  # Assert Violation
        cwe=["CWE-617"],  # Reachable Assertion
        owasp_sc=["SC03"],
        dasp=["DASP-5"],
    ),
}


# =============================================================================
# LOOKUP FUNCTIONS
# =============================================================================


def get_taxonomy(pattern_id: str) -> TaxonomyMapping:
    """
    Look up taxonomy mapping for a pattern ID.

    Supports exact matches and prefix-based fallback.

    Args:
        pattern_id: Pattern identifier (e.g., "auth-001", "reentrancy-basic")

    Returns:
        TaxonomyMapping with SWC/CWE/OWASP codes, or empty mapping if not found
    """
    # Try exact match first
    if pattern_id in TAXONOMY_REGISTRY:
        return TAXONOMY_REGISTRY[pattern_id]

    # Try prefix-based fallback (e.g., "auth-001" -> "auth")
    pattern_lower = pattern_id.lower()

    # Extract prefix from semantic pattern IDs (e.g., "vm-001" -> "vm")
    if "-" in pattern_id:
        prefix = pattern_id.split("-")[0]
        if prefix in TAXONOMY_REGISTRY:
            return TAXONOMY_REGISTRY[prefix]

    # Keyword-based fallback
    keyword_mappings = [
        ("reentrancy", "reentrancy"),
        ("reentrant", "reentrancy"),
        ("auth", "auth"),
        ("access", "auth"),
        ("delegatecall", "delegatecall"),
        ("oracle", "oracle"),
        ("price", "oracle"),
        ("dos", "dos"),
        ("unbounded", "dos"),
        ("crypto", "crypto"),
        ("signature", "crypto"),
        ("proxy", "proxy"),
        ("upgrade", "proxy"),
        ("mev", "mev"),
        ("slippage", "mev"),
        ("token", "token"),
        ("erc20", "token"),
        ("governance", "governance"),
        ("multisig", "multisig"),
        ("emergency", "emergency"),
        ("arithmetic", "arithmetic"),
    ]

    for keyword, registry_key in keyword_mappings:
        if keyword in pattern_lower:
            return TAXONOMY_REGISTRY.get(registry_key, TaxonomyMapping())

    # No match found, return empty mapping
    return TaxonomyMapping()


def get_swc(pattern_id: str) -> str:
    """Get primary SWC code for a pattern."""
    return get_taxonomy(pattern_id).primary_swc()


def get_cwe(pattern_id: str) -> str:
    """Get primary CWE code for a pattern."""
    return get_taxonomy(pattern_id).primary_cwe()


def get_owasp_sc(pattern_id: str) -> list[str]:
    """Get OWASP Smart Contract Top 10 codes for a pattern."""
    return get_taxonomy(pattern_id).owasp_sc


def get_dasp(pattern_id: str) -> list[str]:
    """Get DASP Top 10 codes for a pattern (legacy)."""
    return get_taxonomy(pattern_id).dasp


def enrich_finding_with_taxonomy(finding_dict: dict) -> dict:
    """
    Enrich a finding dictionary with taxonomy codes.

    Args:
        finding_dict: Finding dictionary with 'pattern_id' field

    Returns:
        Finding dictionary with added 'swc' and 'cwe' fields
    """
    pattern_id = finding_dict.get("pattern_id", "")
    taxonomy = get_taxonomy(pattern_id)

    finding_dict["swc"] = taxonomy.primary_swc()
    finding_dict["cwe"] = taxonomy.primary_cwe()
    finding_dict["taxonomy"] = taxonomy.to_dict()

    return finding_dict


# =============================================================================
# REFERENCE DATA
# =============================================================================

# SWC Registry Reference (partial, for documentation)
SWC_REFERENCE = {
    "SWC-100": "Function Default Visibility",
    "SWC-101": "Integer Overflow and Underflow",
    "SWC-104": "Unchecked Call Return Value",
    "SWC-105": "Unprotected Ether Withdrawal",
    "SWC-106": "Unprotected SELFDESTRUCT Instruction",
    "SWC-107": "Reentrancy",
    "SWC-109": "Uninitialized Storage Pointer",
    "SWC-110": "Assert Violation",
    "SWC-112": "Delegatecall to Untrusted Callee",
    "SWC-113": "DoS with Failed Call",
    "SWC-114": "Transaction Order Dependence",
    "SWC-115": "Authorization through tx.origin",
    "SWC-117": "Signature Malleability",
    "SWC-120": "Weak Sources of Randomness from Chain Attributes",
    "SWC-121": "Missing Protection against Signature Replay Attacks",
    "SWC-122": "Lack of Proper Signature Verification",
    "SWC-124": "Write to Arbitrary Storage Location",
    "SWC-126": "Insufficient Gas Griefing",
    "SWC-128": "DoS With Block Gas Limit",
    "SWC-129": "Typographical Error",
    "SWC-132": "Unexpected Ether Balance",
}

# OWASP Smart Contract Top 10 Reference
OWASP_SC_REFERENCE = {
    "SC01": "Access Control",
    "SC02": "Oracle Manipulation",
    "SC03": "Logic Errors",
    "SC04": "Input Validation",
    "SC05": "Reentrancy",
    "SC06": "Unchecked External Calls",
    "SC07": "Flash Loan Attacks",
    "SC08": "Integer Overflow",
    "SC09": "Randomness",
    "SC10": "Denial of Service",
}

# DASP Top 10 Reference (Legacy)
DASP_REFERENCE = {
    "DASP-1": "Reentrancy",
    "DASP-2": "Access Control",
    "DASP-3": "Arithmetic Issues",
    "DASP-4": "Unchecked Return Values",
    "DASP-5": "Denial of Service",
    "DASP-6": "Bad Randomness",
    "DASP-7": "Front-Running",
    "DASP-8": "Time Manipulation",
    "DASP-9": "Short Address Attack",
    "DASP-10": "Unknown Unknowns",
}
