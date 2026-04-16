"""Centralized Detector-to-Pattern Mapping (Phase 5.1 Plan 05).

Single source of truth for mapping external tool detectors to VKG patterns.
Consolidates mappings from all adapters for cross-tool correlation and deduplication.

Tool coverage:
- Slither (90+ detectors)
- Aderyn (30+ detectors)
- Mythril (SWC IDs)
- Semgrep (Decurity rules)
- Echidna (property prefixes)
- Foundry (test prefixes)
- Halmos (assertion types)
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Set


class DetectorMapping(NamedTuple):
    """Mapping from a tool detector to VKG pattern.

    Attributes:
        vkg_pattern: VKG pattern ID this detector maps to
        category: Vulnerability category (reentrancy, access_control, etc.)
        confidence_boost: Added to tool's base confidence when matched
        tool_precision: How precise this tool is for this detector (0-1)
        notes: Additional context about the mapping
    """

    vkg_pattern: str
    category: str
    confidence_boost: float
    tool_precision: float
    notes: str = ""


# =============================================================================
# CENTRALIZED MAPPING: tool -> detector_id -> DetectorMapping
# =============================================================================

TOOL_DETECTOR_MAP: Dict[str, Dict[str, DetectorMapping]] = {
    # =========================================================================
    # SLITHER - Static Analysis (Tier 0)
    # https://github.com/crytic/slither/wiki/Detector-Documentation
    # =========================================================================
    "slither": {
        # --- Reentrancy detectors ---
        "reentrancy-eth": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.3,
            tool_precision=0.85,
            notes="High precision for ETH reentrancy",
        ),
        "reentrancy-no-eth": DetectorMapping(
            vkg_pattern="reentrancy-state",
            category="reentrancy",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Moderate precision, may include benign cases",
        ),
        "reentrancy-benign": DetectorMapping(
            vkg_pattern="reentrancy-benign",
            category="reentrancy",
            confidence_boost=0.1,
            tool_precision=0.60,
            notes="Often false positives, informational",
        ),
        "reentrancy-events": DetectorMapping(
            vkg_pattern="reentrancy-events",
            category="reentrancy",
            confidence_boost=0.1,
            tool_precision=0.65,
            notes="Event emission ordering issues",
        ),
        "reentrancy-unlimited-gas": DetectorMapping(
            vkg_pattern="reentrancy-unlimited-gas",
            category="reentrancy",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="Gas-based reentrancy detection",
        ),
        # --- Access control detectors ---
        "arbitrary-send-eth": DetectorMapping(
            vkg_pattern="access-control-permissive",
            category="access_control",
            confidence_boost=0.3,
            tool_precision=0.80,
            notes="Arbitrary ETH send detection",
        ),
        "arbitrary-send-erc20": DetectorMapping(
            vkg_pattern="access-control-permissive",
            category="access_control",
            confidence_boost=0.25,
            tool_precision=0.75,
            notes="Arbitrary ERC20 send",
        ),
        "arbitrary-send-erc20-permit": DetectorMapping(
            vkg_pattern="access-control-permissive",
            category="access_control",
            confidence_boost=0.25,
            tool_precision=0.75,
            notes="ERC20 permit-based arbitrary send",
        ),
        "protected-vars": DetectorMapping(
            vkg_pattern="access-control-missing",
            category="access_control",
            confidence_boost=0.2,
            tool_precision=0.70,
            notes="Unprotected state variables",
        ),
        "unprotected-upgrade": DetectorMapping(
            vkg_pattern="upgrade-unprotected",
            category="access_control",
            confidence_boost=0.35,
            tool_precision=0.90,
            notes="Critical: upgrade without access control",
        ),
        "suicidal": DetectorMapping(
            vkg_pattern="selfdestruct-unprotected",
            category="access_control",
            confidence_boost=0.35,
            tool_precision=0.90,
            notes="Critical: unprotected selfdestruct",
        ),
        "tx-origin": DetectorMapping(
            vkg_pattern="tx-origin-auth",
            category="access_control",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="tx.origin used for authentication",
        ),
        # --- Delegation detectors ---
        "controlled-delegatecall": DetectorMapping(
            vkg_pattern="delegatecall-injection",
            category="delegation",
            confidence_boost=0.35,
            tool_precision=0.90,
            notes="Critical: controllable delegatecall target",
        ),
        "delegatecall-loop": DetectorMapping(
            vkg_pattern="delegatecall-loop",
            category="delegation",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Delegatecall in loop",
        ),
        # --- Return value detectors ---
        "unchecked-transfer": DetectorMapping(
            vkg_pattern="unchecked-return",
            category="unchecked_return",
            confidence_boost=0.25,
            tool_precision=0.80,
            notes="Unchecked ERC20 transfer",
        ),
        "unchecked-lowlevel": DetectorMapping(
            vkg_pattern="unchecked-low-level",
            category="unchecked_return",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Unchecked low-level call",
        ),
        "unchecked-send": DetectorMapping(
            vkg_pattern="unchecked-send",
            category="unchecked_return",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Unchecked send",
        ),
        # --- Arithmetic detectors ---
        "divide-before-multiply": DetectorMapping(
            vkg_pattern="arithmetic-precision-loss",
            category="arithmetic",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Precision loss in math operations",
        ),
        "incorrect-shift": DetectorMapping(
            vkg_pattern="arithmetic-incorrect-shift",
            category="arithmetic",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Incorrect shift operations",
        ),
        # --- State detectors ---
        "write-after-write": DetectorMapping(
            vkg_pattern="state-double-write",
            category="state",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="Redundant state writes",
        ),
        "incorrect-equality": DetectorMapping(
            vkg_pattern="state-strict-equality",
            category="state",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Dangerous strict equality",
        ),
        "locked-ether": DetectorMapping(
            vkg_pattern="locked-funds",
            category="locked_funds",
            confidence_boost=0.25,
            tool_precision=0.80,
            notes="ETH locked in contract",
        ),
        "uninitialized-state": DetectorMapping(
            vkg_pattern="state-uninitialized",
            category="initialization",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Uninitialized state variables",
        ),
        "uninitialized-local": DetectorMapping(
            vkg_pattern="state-uninitialized-local",
            category="initialization",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="Uninitialized local variables",
        ),
        "uninitialized-storage": DetectorMapping(
            vkg_pattern="state-uninitialized-storage",
            category="initialization",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Uninitialized storage pointer",
        ),
        # --- Time manipulation detectors ---
        "timestamp": DetectorMapping(
            vkg_pattern="timestamp-dependence",
            category="time_manipulation",
            confidence_boost=0.15,
            tool_precision=0.65,
            notes="Block timestamp dependency",
        ),
        "weak-prng": DetectorMapping(
            vkg_pattern="weak-randomness",
            category="randomness",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Weak PRNG sources",
        ),
        "block-timestamp": DetectorMapping(
            vkg_pattern="timestamp-dependence",
            category="time_manipulation",
            confidence_boost=0.15,
            tool_precision=0.65,
            notes="Block timestamp used",
        ),
        # --- DOS detectors ---
        "calls-loop": DetectorMapping(
            vkg_pattern="dos-external-call-loop",
            category="dos",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="External calls in loop",
        ),
        "msg-value-loop": DetectorMapping(
            vkg_pattern="msg-value-loop",
            category="dos",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="msg.value used in loop",
        ),
        # --- ERC compliance detectors ---
        "erc20-interface": DetectorMapping(
            vkg_pattern="erc20-interface-violation",
            category="erc_compliance",
            confidence_boost=0.2,
            tool_precision=0.85,
            notes="ERC20 interface violation",
        ),
        "erc721-interface": DetectorMapping(
            vkg_pattern="erc721-interface-violation",
            category="erc_compliance",
            confidence_boost=0.2,
            tool_precision=0.85,
            notes="ERC721 interface violation",
        ),
        # --- Shadowing detectors ---
        "shadowing-state": DetectorMapping(
            vkg_pattern="state-shadowing",
            category="shadowing",
            confidence_boost=0.15,
            tool_precision=0.80,
            notes="State variable shadowing",
        ),
        "shadowing-local": DetectorMapping(
            vkg_pattern="local-shadowing",
            category="shadowing",
            confidence_boost=0.1,
            tool_precision=0.75,
            notes="Local variable shadowing",
        ),
        "shadowing-builtin": DetectorMapping(
            vkg_pattern="builtin-shadowing",
            category="shadowing",
            confidence_boost=0.1,
            tool_precision=0.80,
            notes="Built-in symbol shadowing",
        ),
        "shadowing-abstract": DetectorMapping(
            vkg_pattern="abstract-shadowing",
            category="shadowing",
            confidence_boost=0.1,
            tool_precision=0.75,
            notes="Abstract function shadowing",
        ),
        # --- Code quality detectors ---
        "naming-convention": DetectorMapping(
            vkg_pattern="naming-convention",
            category="code_style",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Naming convention violation",
        ),
        "similar-names": DetectorMapping(
            vkg_pattern="similar-names",
            category="code_style",
            confidence_boost=0.05,
            tool_precision=0.70,
            notes="Similar variable names",
        ),
        "assembly": DetectorMapping(
            vkg_pattern="assembly-usage",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.95,
            notes="Inline assembly usage",
        ),
        "dead-code": DetectorMapping(
            vkg_pattern="dead-code",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Unreachable code",
        ),
        "unused-state": DetectorMapping(
            vkg_pattern="unused-state",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Unused state variable",
        ),
        "unused-return": DetectorMapping(
            vkg_pattern="unused-return",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.80,
            notes="Unused return value",
        ),
        # --- Miscellaneous detectors ---
        "low-level-calls": DetectorMapping(
            vkg_pattern="low-level-call",
            category="external_calls",
            confidence_boost=0.1,
            tool_precision=0.90,
            notes="Low-level call usage",
        ),
        "missing-zero-check": DetectorMapping(
            vkg_pattern="missing-zero-check",
            category="validation",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Missing zero address check",
        ),
        "pragma": DetectorMapping(
            vkg_pattern="pragma-version",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Pragma version issues",
        ),
        "solc-version": DetectorMapping(
            vkg_pattern="solc-version",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Solidity version issues",
        ),
        "incorrect-return": DetectorMapping(
            vkg_pattern="return-incorrect",
            category="code_quality",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Incorrect return in assembly",
        ),
        "encode-packed-collision": DetectorMapping(
            vkg_pattern="encode-packed-collision",
            category="encoding",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="abi.encodePacked hash collision",
        ),
        "incorrect-modifier": DetectorMapping(
            vkg_pattern="modifier-incorrect",
            category="code_quality",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Incorrect modifier usage",
        ),
        "mapping-deletion": DetectorMapping(
            vkg_pattern="mapping-deletion",
            category="storage",
            confidence_boost=0.15,
            tool_precision=0.80,
            notes="Mapping deletion issues",
        ),
        "multiple-constructors": DetectorMapping(
            vkg_pattern="constructor-multiple",
            category="initialization",
            confidence_boost=0.2,
            tool_precision=0.90,
            notes="Multiple constructor definitions",
        ),
        "void-cst": DetectorMapping(
            vkg_pattern="void-constructor",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.85,
            notes="Empty constructor",
        ),
        "deprecated-standards": DetectorMapping(
            vkg_pattern="deprecated-standards",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.90,
            notes="Deprecated Solidity functions",
        ),
        "boolean-cst": DetectorMapping(
            vkg_pattern="boolean-constant",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Boolean constant comparison",
        ),
        "boolean-equal": DetectorMapping(
            vkg_pattern="boolean-equality",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Boolean equality comparison",
        ),
        "storage-array": DetectorMapping(
            vkg_pattern="storage-array-issue",
            category="storage",
            confidence_boost=0.15,
            tool_precision=0.80,
            notes="Storage array issues",
        ),
        "array-by-reference": DetectorMapping(
            vkg_pattern="array-reference-issue",
            category="storage",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Array passed by reference",
        ),
        "constant-function-asm": DetectorMapping(
            vkg_pattern="constant-function-asm",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.80,
            notes="Constant function with assembly",
        ),
        "constant-function-state": DetectorMapping(
            vkg_pattern="constant-function-state",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.80,
            notes="Constant function modifying state",
        ),
        "public-mappings-nested": DetectorMapping(
            vkg_pattern="public-mapping-nested",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Nested public mapping",
        ),
        "reused-constructor": DetectorMapping(
            vkg_pattern="constructor-reused",
            category="initialization",
            confidence_boost=0.1,
            tool_precision=0.80,
            notes="Reused constructor pattern",
        ),
        "rtlo": DetectorMapping(
            vkg_pattern="rtlo-character",
            category="code_quality",
            confidence_boost=0.3,
            tool_precision=0.95,
            notes="Right-to-left override character",
        ),
        "too-many-digits": DetectorMapping(
            vkg_pattern="too-many-digits",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.80,
            notes="Numeric literal clarity",
        ),
        "variable-scope": DetectorMapping(
            vkg_pattern="variable-scope",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.75,
            notes="Variable scope issues",
        ),
        "unimplemented-functions": DetectorMapping(
            vkg_pattern="unimplemented-functions",
            category="code_quality",
            confidence_boost=0.15,
            tool_precision=0.85,
            notes="Unimplemented interface functions",
        ),
    },
    # =========================================================================
    # ADERYN - Rust Static Analyzer (Tier 1)
    # https://github.com/Cyfrin/aderyn
    # =========================================================================
    "aderyn": {
        # --- Reentrancy detectors ---
        "state-change-after-external-call": DetectorMapping(
            vkg_pattern="reentrancy-state",
            category="reentrancy",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="State change after external call",
        ),
        "reentrancy": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.25,
            tool_precision=0.80,
            notes="General reentrancy detection",
        ),
        "reentrancy-state": DetectorMapping(
            vkg_pattern="reentrancy-state",
            category="reentrancy",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="State-based reentrancy",
        ),
        # --- Access control detectors ---
        "centralization-risk": DetectorMapping(
            vkg_pattern="access-control-centralized",
            category="access_control",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="Centralization risk detection",
        ),
        "unprotected-initializer": DetectorMapping(
            vkg_pattern="access-control-missing-initializer",
            category="access_control",
            confidence_boost=0.3,
            tool_precision=0.85,
            notes="Unprotected initializer function",
        ),
        "missing-access-control": DetectorMapping(
            vkg_pattern="access-control-missing",
            category="access_control",
            confidence_boost=0.25,
            tool_precision=0.75,
            notes="Missing access control",
        ),
        "unprotected-upgrade": DetectorMapping(
            vkg_pattern="upgrade-unprotected",
            category="access_control",
            confidence_boost=0.3,
            tool_precision=0.85,
            notes="Unprotected upgrade function",
        ),
        "selfdestruct": DetectorMapping(
            vkg_pattern="selfdestruct-unprotected",
            category="access_control",
            confidence_boost=0.3,
            tool_precision=0.85,
            notes="Selfdestruct usage",
        ),
        "tx-origin-auth": DetectorMapping(
            vkg_pattern="tx-origin-auth",
            category="access_control",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="tx.origin authentication",
        ),
        # --- Arithmetic detectors ---
        "unsafe-casting": DetectorMapping(
            vkg_pattern="arithmetic-unsafe-cast",
            category="arithmetic",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Unsafe type casting",
        ),
        "unchecked-math": DetectorMapping(
            vkg_pattern="arithmetic-unchecked",
            category="arithmetic",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Unchecked math operations",
        ),
        "divide-before-multiply": DetectorMapping(
            vkg_pattern="arithmetic-precision-loss",
            category="arithmetic",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Division before multiplication",
        ),
        "integer-overflow": DetectorMapping(
            vkg_pattern="arithmetic-overflow",
            category="arithmetic",
            confidence_boost=0.25,
            tool_precision=0.80,
            notes="Integer overflow detection",
        ),
        # --- Return value detectors ---
        "unchecked-return-value": DetectorMapping(
            vkg_pattern="unchecked-return",
            category="unchecked_return",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Unchecked return value",
        ),
        "unchecked-low-level": DetectorMapping(
            vkg_pattern="unchecked-low-level",
            category="unchecked_return",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Unchecked low-level call",
        ),
        "unchecked-send": DetectorMapping(
            vkg_pattern="unchecked-send",
            category="unchecked_return",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Unchecked send call",
        ),
        # --- Delegation detectors ---
        "delegatecall-in-loop": DetectorMapping(
            vkg_pattern="delegatecall-loop",
            category="delegation",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Delegatecall in loop",
        ),
        "controlled-delegatecall": DetectorMapping(
            vkg_pattern="delegatecall-injection",
            category="delegation",
            confidence_boost=0.3,
            tool_precision=0.85,
            notes="Controllable delegatecall",
        ),
        # --- External call detectors ---
        "external-call-in-loop": DetectorMapping(
            vkg_pattern="dos-external-call-loop",
            category="dos",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="External call in loop",
        ),
        "low-level-call": DetectorMapping(
            vkg_pattern="low-level-call",
            category="external_calls",
            confidence_boost=0.1,
            tool_precision=0.85,
            notes="Low-level call usage",
        ),
        # --- Storage detectors ---
        "uninitialized-storage": DetectorMapping(
            vkg_pattern="state-uninitialized-storage",
            category="initialization",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Uninitialized storage pointer",
        ),
        "uninitialized-state-variable": DetectorMapping(
            vkg_pattern="state-uninitialized",
            category="initialization",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Uninitialized state variable",
        ),
        "storage-collision": DetectorMapping(
            vkg_pattern="storage-collision",
            category="storage",
            confidence_boost=0.3,
            tool_precision=0.85,
            notes="Storage slot collision",
        ),
        # --- Time manipulation detectors ---
        "weak-randomness": DetectorMapping(
            vkg_pattern="weak-randomness",
            category="randomness",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Weak randomness source",
        ),
        "timestamp-dependence": DetectorMapping(
            vkg_pattern="timestamp-dependence",
            category="time_manipulation",
            confidence_boost=0.15,
            tool_precision=0.65,
            notes="Timestamp dependency",
        ),
        "block-timestamp": DetectorMapping(
            vkg_pattern="timestamp-dependence",
            category="time_manipulation",
            confidence_boost=0.15,
            tool_precision=0.65,
            notes="Block timestamp usage",
        ),
        # --- ERC compliance detectors ---
        "incorrect-erc20": DetectorMapping(
            vkg_pattern="erc20-interface-violation",
            category="erc_compliance",
            confidence_boost=0.2,
            tool_precision=0.85,
            notes="ERC20 compliance issue",
        ),
        "incorrect-erc721": DetectorMapping(
            vkg_pattern="erc721-interface-violation",
            category="erc_compliance",
            confidence_boost=0.2,
            tool_precision=0.85,
            notes="ERC721 compliance issue",
        ),
        "missing-erc20-return": DetectorMapping(
            vkg_pattern="erc20-missing-return",
            category="erc_compliance",
            confidence_boost=0.2,
            tool_precision=0.85,
            notes="Missing ERC20 return value",
        ),
        # --- Code quality detectors ---
        "dead-code": DetectorMapping(
            vkg_pattern="dead-code",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Dead code detection",
        ),
        "unused-import": DetectorMapping(
            vkg_pattern="unused-import",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Unused import statement",
        ),
        "unused-state-variable": DetectorMapping(
            vkg_pattern="unused-state",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Unused state variable",
        ),
        "shadowing": DetectorMapping(
            vkg_pattern="state-shadowing",
            category="shadowing",
            confidence_boost=0.15,
            tool_precision=0.80,
            notes="Variable shadowing",
        ),
        "magic-number": DetectorMapping(
            vkg_pattern="magic-number",
            category="code_style",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Magic number usage",
        ),
        "assembly-usage": DetectorMapping(
            vkg_pattern="assembly-usage",
            category="code_quality",
            confidence_boost=0.05,
            tool_precision=0.95,
            notes="Assembly block usage",
        ),
        "deprecated-functions": DetectorMapping(
            vkg_pattern="deprecated-standards",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.90,
            notes="Deprecated function usage",
        ),
        # --- Gas optimization detectors ---
        "gas-use-require-string": DetectorMapping(
            vkg_pattern="gas-require-string",
            category="gas_optimization",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Require with string message",
        ),
        "gas-use-immutable": DetectorMapping(
            vkg_pattern="gas-immutable",
            category="gas_optimization",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Should use immutable",
        ),
        "gas-use-constant": DetectorMapping(
            vkg_pattern="gas-constant",
            category="gas_optimization",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Should use constant",
        ),
        "gas-cache-array-length": DetectorMapping(
            vkg_pattern="gas-array-length",
            category="gas_optimization",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Cache array length in loop",
        ),
        "gas-state-variable-caching": DetectorMapping(
            vkg_pattern="gas-state-caching",
            category="gas_optimization",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="State variable caching",
        ),
        "push-zero-optimization": DetectorMapping(
            vkg_pattern="gas-push-zero",
            category="gas_optimization",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Push zero optimization",
        ),
        "public-vs-external": DetectorMapping(
            vkg_pattern="gas-public-external",
            category="gas_optimization",
            confidence_boost=0.05,
            tool_precision=0.85,
            notes="Public vs external visibility",
        ),
        # --- Miscellaneous detectors ---
        "missing-zero-address-check": DetectorMapping(
            vkg_pattern="missing-zero-check",
            category="validation",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Missing zero address validation",
        ),
        "floating-pragma": DetectorMapping(
            vkg_pattern="pragma-version",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.90,
            notes="Floating pragma version",
        ),
        "missing-natspec": DetectorMapping(
            vkg_pattern="missing-natspec",
            category="documentation",
            confidence_boost=0.05,
            tool_precision=0.90,
            notes="Missing NatSpec documentation",
        ),
    },
    # =========================================================================
    # MYTHRIL - Symbolic Execution (Tier 1)
    # Uses SWC (Smart Contract Weakness Classification) IDs
    # https://swcregistry.io/
    # =========================================================================
    "mythril": {
        "SWC-101": DetectorMapping(
            vkg_pattern="arithmetic-overflow",
            category="arithmetic",
            confidence_boost=0.3,
            tool_precision=0.90,
            notes="Integer overflow/underflow (symbolic)",
        ),
        "SWC-102": DetectorMapping(
            vkg_pattern="access-control-missing",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.70,
            notes="Outdated compiler version",
        ),
        "SWC-103": DetectorMapping(
            vkg_pattern="floating-pragma",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.90,
            notes="Floating pragma",
        ),
        "SWC-104": DetectorMapping(
            vkg_pattern="unchecked-return",
            category="unchecked_return",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Unchecked call return value",
        ),
        "SWC-105": DetectorMapping(
            vkg_pattern="access-control-missing",
            category="access_control",
            confidence_boost=0.3,
            tool_precision=0.85,
            notes="Unprotected ether withdrawal",
        ),
        "SWC-106": DetectorMapping(
            vkg_pattern="selfdestruct-unprotected",
            category="access_control",
            confidence_boost=0.35,
            tool_precision=0.90,
            notes="Unprotected SELFDESTRUCT",
        ),
        "SWC-107": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.35,
            tool_precision=0.90,
            notes="Reentrancy (symbolic execution proof)",
        ),
        "SWC-108": DetectorMapping(
            vkg_pattern="state-uninitialized",
            category="state",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="State variable default visibility",
        ),
        "SWC-109": DetectorMapping(
            vkg_pattern="state-uninitialized",
            category="state",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Uninitialized storage pointer",
        ),
        "SWC-110": DetectorMapping(
            vkg_pattern="assert-violation",
            category="assertion",
            confidence_boost=0.3,
            tool_precision=0.90,
            notes="Assert violation (symbolic proof)",
        ),
        "SWC-111": DetectorMapping(
            vkg_pattern="deprecated-standards",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.90,
            notes="Deprecated Solidity functions",
        ),
        "SWC-112": DetectorMapping(
            vkg_pattern="delegatecall-injection",
            category="delegation",
            confidence_boost=0.35,
            tool_precision=0.90,
            notes="Delegatecall to untrusted callee",
        ),
        "SWC-113": DetectorMapping(
            vkg_pattern="dos-gas-limit",
            category="dos",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="DoS with failed call",
        ),
        "SWC-114": DetectorMapping(
            vkg_pattern="dos-block-gas",
            category="frontrunning",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Transaction order dependence",
        ),
        "SWC-115": DetectorMapping(
            vkg_pattern="tx-origin-auth",
            category="access_control",
            confidence_boost=0.25,
            tool_precision=0.90,
            notes="Authorization through tx.origin",
        ),
        "SWC-116": DetectorMapping(
            vkg_pattern="timestamp-dependence",
            category="time_manipulation",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Block values as time proxy",
        ),
        "SWC-117": DetectorMapping(
            vkg_pattern="signature-malleability",
            category="signature",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Signature malleability",
        ),
        "SWC-118": DetectorMapping(
            vkg_pattern="constructor-typo",
            category="initialization",
            confidence_boost=0.25,
            tool_precision=0.90,
            notes="Incorrect constructor name",
        ),
        "SWC-119": DetectorMapping(
            vkg_pattern="shadowing-state",
            category="shadowing",
            confidence_boost=0.15,
            tool_precision=0.85,
            notes="Shadowing state variables",
        ),
        "SWC-120": DetectorMapping(
            vkg_pattern="weak-randomness",
            category="randomness",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Weak randomness source",
        ),
        "SWC-121": DetectorMapping(
            vkg_pattern="eip-compliance",
            category="signature",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Missing signature replay protection",
        ),
        "SWC-122": DetectorMapping(
            vkg_pattern="unchecked-return",
            category="signature",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Lack of signature verification",
        ),
        "SWC-123": DetectorMapping(
            vkg_pattern="eip-compliance",
            category="assertion",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Requirement violation",
        ),
        "SWC-124": DetectorMapping(
            vkg_pattern="write-to-arbitrary-storage",
            category="storage",
            confidence_boost=0.35,
            tool_precision=0.90,
            notes="Write to arbitrary storage",
        ),
        "SWC-125": DetectorMapping(
            vkg_pattern="arbitrary-jump",
            category="inheritance",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Incorrect inheritance order",
        ),
        "SWC-126": DetectorMapping(
            vkg_pattern="ether-lost",
            category="dos",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Insufficient gas griefing",
        ),
        "SWC-127": DetectorMapping(
            vkg_pattern="arbitrary-jump",
            category="control_flow",
            confidence_boost=0.3,
            tool_precision=0.85,
            notes="Arbitrary jump with function type",
        ),
        "SWC-128": DetectorMapping(
            vkg_pattern="dos-block-gas",
            category="dos",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="DoS with block gas limit",
        ),
        "SWC-129": DetectorMapping(
            vkg_pattern="constructor-typo",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.75,
            notes="Typographical error",
        ),
        "SWC-130": DetectorMapping(
            vkg_pattern="assert-state-change",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.90,
            notes="RTLO character",
        ),
        "SWC-131": DetectorMapping(
            vkg_pattern="shadowing-builtin",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.85,
            notes="Unused variables",
        ),
        "SWC-132": DetectorMapping(
            vkg_pattern="unexpected-ether",
            category="unexpected_state",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Unexpected ether balance",
        ),
        "SWC-133": DetectorMapping(
            vkg_pattern="hash-collision",
            category="encoding",
            confidence_boost=0.25,
            tool_precision=0.85,
            notes="Hash collision with variable length args",
        ),
        "SWC-134": DetectorMapping(
            vkg_pattern="msg-value-loop",
            category="dos",
            confidence_boost=0.2,
            tool_precision=0.80,
            notes="Hardcoded gas amount",
        ),
        "SWC-135": DetectorMapping(
            vkg_pattern="gas-price-manipulation",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.75,
            notes="Code with no effects",
        ),
        "SWC-136": DetectorMapping(
            vkg_pattern="unchecked-return",
            category="privacy",
            confidence_boost=0.1,
            tool_precision=0.70,
            notes="Unencrypted private data on-chain",
        ),
    },
    # =========================================================================
    # SEMGREP - Pattern Matching (Tier 1)
    # Decurity smart-contracts ruleset
    # https://github.com/Decurity/semgrep-smart-contracts
    # =========================================================================
    "semgrep": {
        # --- Reentrancy rules ---
        "solidity.security.reentrancy": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.1,
            tool_precision=0.60,
            notes="Pattern-based reentrancy detection",
        ),
        "solidity.security.reentrancy-eth": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.1,
            tool_precision=0.60,
            notes="ETH reentrancy pattern",
        ),
        "solidity.security.call-value-reentrancy": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.1,
            tool_precision=0.60,
            notes="Call value reentrancy",
        ),
        "solidity.security.cross-function-reentrancy": DetectorMapping(
            vkg_pattern="reentrancy-cross-function",
            category="reentrancy",
            confidence_boost=0.15,
            tool_precision=0.55,
            notes="Cross-function reentrancy",
        ),
        "solidity.security.read-only-reentrancy": DetectorMapping(
            vkg_pattern="reentrancy-read-only",
            category="reentrancy",
            confidence_boost=0.15,
            tool_precision=0.55,
            notes="Read-only reentrancy",
        ),
        # --- Access control rules ---
        "solidity.security.tx-origin": DetectorMapping(
            vkg_pattern="tx-origin-auth",
            category="access_control",
            confidence_boost=0.15,
            tool_precision=0.80,
            notes="tx.origin usage pattern",
        ),
        "solidity.security.tx-origin-auth": DetectorMapping(
            vkg_pattern="tx-origin-auth",
            category="access_control",
            confidence_boost=0.15,
            tool_precision=0.80,
            notes="tx.origin authentication",
        ),
        "solidity.security.missing-access-control": DetectorMapping(
            vkg_pattern="access-control-missing",
            category="access_control",
            confidence_boost=0.1,
            tool_precision=0.55,
            notes="Missing access control pattern",
        ),
        "solidity.security.unprotected-selfdestruct": DetectorMapping(
            vkg_pattern="selfdestruct-unprotected",
            category="access_control",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Unprotected selfdestruct",
        ),
        "solidity.security.arbitrary-send": DetectorMapping(
            vkg_pattern="access-control-permissive",
            category="access_control",
            confidence_boost=0.1,
            tool_precision=0.60,
            notes="Arbitrary ETH send",
        ),
        # --- Delegation rules ---
        "solidity.security.delegatecall": DetectorMapping(
            vkg_pattern="delegatecall-injection",
            category="delegation",
            confidence_boost=0.15,
            tool_precision=0.65,
            notes="Delegatecall usage",
        ),
        "solidity.security.delegatecall-to-arbitrary": DetectorMapping(
            vkg_pattern="delegatecall-injection",
            category="delegation",
            confidence_boost=0.2,
            tool_precision=0.70,
            notes="Arbitrary delegatecall target",
        ),
        # --- Unchecked return rules ---
        "solidity.security.unchecked-send": DetectorMapping(
            vkg_pattern="unchecked-return",
            category="unchecked_return",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Unchecked send",
        ),
        "solidity.security.unchecked-call": DetectorMapping(
            vkg_pattern="unchecked-return",
            category="unchecked_return",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Unchecked call",
        ),
        "solidity.security.unchecked-transfer": DetectorMapping(
            vkg_pattern="unchecked-return",
            category="unchecked_return",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Unchecked transfer",
        ),
        "solidity.security.unchecked-low-level-call": DetectorMapping(
            vkg_pattern="unchecked-low-level",
            category="unchecked_return",
            confidence_boost=0.15,
            tool_precision=0.75,
            notes="Unchecked low-level call",
        ),
        # --- Arithmetic rules ---
        "solidity.security.integer-overflow": DetectorMapping(
            vkg_pattern="arithmetic-overflow",
            category="arithmetic",
            confidence_boost=0.1,
            tool_precision=0.55,
            notes="Integer overflow pattern",
        ),
        "solidity.security.divide-before-multiply": DetectorMapping(
            vkg_pattern="arithmetic-precision-loss",
            category="arithmetic",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="Division before multiplication",
        ),
        # --- Oracle rules ---
        "solidity.security.oracle-stale-price": DetectorMapping(
            vkg_pattern="oracle-stale-data",
            category="oracle",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Stale oracle price",
        ),
        "solidity.security.chainlink-stale-data": DetectorMapping(
            vkg_pattern="oracle-stale-data",
            category="oracle",
            confidence_boost=0.2,
            tool_precision=0.75,
            notes="Chainlink stale data",
        ),
        "solidity.security.price-manipulation": DetectorMapping(
            vkg_pattern="oracle-manipulation",
            category="oracle",
            confidence_boost=0.15,
            tool_precision=0.60,
            notes="Price manipulation pattern",
        ),
        "solidity.security.spot-price-manipulation": DetectorMapping(
            vkg_pattern="oracle-manipulation",
            category="oracle",
            confidence_boost=0.15,
            tool_precision=0.60,
            notes="Spot price manipulation",
        ),
        # --- Flash loan rules ---
        "solidity.security.flash-loan-callback": DetectorMapping(
            vkg_pattern="flash-loan-callback",
            category="flash_loan",
            confidence_boost=0.1,
            tool_precision=0.55,
            notes="Flash loan callback pattern",
        ),
        # --- Time manipulation rules ---
        "solidity.security.timestamp-dependence": DetectorMapping(
            vkg_pattern="timestamp-dependence",
            category="time_manipulation",
            confidence_boost=0.1,
            tool_precision=0.60,
            notes="Timestamp dependency",
        ),
        "solidity.security.weak-randomness": DetectorMapping(
            vkg_pattern="weak-randomness",
            category="randomness",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="Weak randomness",
        ),
        # --- DOS rules ---
        "solidity.security.dos-gas-limit": DetectorMapping(
            vkg_pattern="dos-gas-limit",
            category="dos",
            confidence_boost=0.15,
            tool_precision=0.65,
            notes="Gas limit DOS",
        ),
        "solidity.security.call-in-loop": DetectorMapping(
            vkg_pattern="dos-external-call-loop",
            category="dos",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="External call in loop",
        ),
        "solidity.security.unbounded-loop": DetectorMapping(
            vkg_pattern="dos-unbounded-loop",
            category="dos",
            confidence_boost=0.15,
            tool_precision=0.65,
            notes="Unbounded loop",
        ),
        # --- ERC compliance rules ---
        "solidity.security.erc20-return-value": DetectorMapping(
            vkg_pattern="erc20-interface-violation",
            category="erc_compliance",
            confidence_boost=0.15,
            tool_precision=0.80,
            notes="ERC20 return value",
        ),
        "solidity.security.approve-race": DetectorMapping(
            vkg_pattern="erc20-approve-race",
            category="erc_compliance",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="ERC20 approve race condition",
        ),
        # --- Upgrade rules ---
        "solidity.security.unprotected-upgrade": DetectorMapping(
            vkg_pattern="upgrade-unprotected",
            category="access_control",
            confidence_boost=0.2,
            tool_precision=0.70,
            notes="Unprotected upgrade",
        ),
        "solidity.security.storage-collision": DetectorMapping(
            vkg_pattern="upgrade-storage-collision",
            category="upgrade",
            confidence_boost=0.2,
            tool_precision=0.70,
            notes="Storage collision",
        ),
        # --- Miscellaneous rules ---
        "solidity.security.locked-ether": DetectorMapping(
            vkg_pattern="locked-funds",
            category="locked_funds",
            confidence_boost=0.15,
            tool_precision=0.70,
            notes="Locked ether",
        ),
        "solidity.security.floating-pragma": DetectorMapping(
            vkg_pattern="floating-pragma",
            category="code_quality",
            confidence_boost=0.1,
            tool_precision=0.90,
            notes="Floating pragma",
        ),
    },
    # =========================================================================
    # ECHIDNA - Property-Based Fuzzing (Tier 2)
    # Maps property naming conventions to patterns
    # =========================================================================
    "echidna": {
        "echidna_no_reentrant": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Fuzzing found reentrancy",
        ),
        "echidna_no_reentrancy": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Reentrancy property violated",
        ),
        "echidna_balance_invariant": DetectorMapping(
            vkg_pattern="arithmetic-overflow",
            category="arithmetic",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Balance invariant violated",
        ),
        "echidna_no_overflow": DetectorMapping(
            vkg_pattern="arithmetic-overflow",
            category="arithmetic",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Overflow detected via fuzzing",
        ),
        "echidna_no_underflow": DetectorMapping(
            vkg_pattern="arithmetic-underflow",
            category="arithmetic",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Underflow detected via fuzzing",
        ),
        "echidna_owner": DetectorMapping(
            vkg_pattern="access-control-missing",
            category="access_control",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Owner property violated",
        ),
        "echidna_only_owner": DetectorMapping(
            vkg_pattern="access-control-missing",
            category="access_control",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Only owner property violated",
        ),
        "echidna_invariant": DetectorMapping(
            vkg_pattern="invariant-violation",
            category="invariant",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Invariant property violated",
        ),
        "echidna_no_drain": DetectorMapping(
            vkg_pattern="access-control-permissive",
            category="access_control",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Drain attack possible",
        ),
        "echidna_locked": DetectorMapping(
            vkg_pattern="locked-funds",
            category="locked_funds",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Funds locked property violated",
        ),
        "echidna_pause": DetectorMapping(
            vkg_pattern="pausable-bypass",
            category="access_control",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Pause mechanism bypassed",
        ),
    },
    # =========================================================================
    # FOUNDRY - Fuzz/Invariant Testing (Tier 2)
    # Maps test naming conventions to patterns
    # =========================================================================
    "foundry": {
        "invariant_": DetectorMapping(
            vkg_pattern="invariant-violation",
            category="invariant",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Invariant test failure (proven)",
        ),
        "test_exploit_": DetectorMapping(
            vkg_pattern="known-exploit",
            category="exploit",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Exploit proof-of-concept",
        ),
        "test_poc_": DetectorMapping(
            vkg_pattern="known-exploit",
            category="exploit",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="PoC test failure",
        ),
        "testFuzz_": DetectorMapping(
            vkg_pattern="fuzz-failure",
            category="fuzz",
            confidence_boost=0.35,
            tool_precision=0.95,
            notes="Fuzz test failure with counterexample",
        ),
    },
    # =========================================================================
    # HALMOS - Symbolic Testing (Tier 2)
    # Maps assertion types to patterns
    # =========================================================================
    "halmos": {
        "check_NoOverflow": DetectorMapping(
            vkg_pattern="arithmetic-overflow",
            category="arithmetic",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Formal proof of overflow",
        ),
        "check_NoUnderflow": DetectorMapping(
            vkg_pattern="arithmetic-underflow",
            category="arithmetic",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Formal proof of underflow",
        ),
        "check_Reentrancy": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Formal proof of reentrancy",
        ),
        "check_NoReentrancy": DetectorMapping(
            vkg_pattern="reentrancy-classic",
            category="reentrancy",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Reentrancy verification failure",
        ),
        "check_AccessControl": DetectorMapping(
            vkg_pattern="access-control-missing",
            category="access_control",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Formal proof of access control issue",
        ),
        "check_Invariant": DetectorMapping(
            vkg_pattern="invariant-violation",
            category="invariant",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Formal proof of invariant violation",
        ),
        "check_NoArbitrarySend": DetectorMapping(
            vkg_pattern="access-control-permissive",
            category="access_control",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Arbitrary send proof",
        ),
        "check_NoSelfdestruct": DetectorMapping(
            vkg_pattern="selfdestruct-unprotected",
            category="access_control",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Unprotected selfdestruct proof",
        ),
        "check_NoDelegateCall": DetectorMapping(
            vkg_pattern="delegatecall-injection",
            category="delegation",
            confidence_boost=0.4,
            tool_precision=1.0,
            notes="Delegatecall injection proof",
        ),
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_vkg_pattern(tool: str, detector: str) -> Optional[str]:
    """Get VKG pattern ID for a tool detector.

    Args:
        tool: Tool name (slither, aderyn, mythril, etc.)
        detector: Detector/rule ID

    Returns:
        VKG pattern ID or None if not mapped
    """
    tool_map = TOOL_DETECTOR_MAP.get(tool.lower())
    if not tool_map:
        return None

    mapping = tool_map.get(detector)
    if mapping:
        return mapping.vkg_pattern

    # For prefix-based tools (echidna, foundry, halmos), try prefix matching
    if tool.lower() in {"echidna", "foundry", "halmos"}:
        for prefix, mapping in tool_map.items():
            if detector.startswith(prefix):
                return mapping.vkg_pattern

    return None


def get_category(tool: str, detector: str) -> str:
    """Get category for a tool detector.

    Args:
        tool: Tool name
        detector: Detector/rule ID

    Returns:
        Category string or "unknown"
    """
    tool_map = TOOL_DETECTOR_MAP.get(tool.lower())
    if not tool_map:
        return "unknown"

    mapping = tool_map.get(detector)
    if mapping:
        return mapping.category

    # Prefix matching for fuzzing tools
    if tool.lower() in {"echidna", "foundry", "halmos"}:
        for prefix, mapping in tool_map.items():
            if detector.startswith(prefix):
                return mapping.category

    return "unknown"


def get_confidence_boost(tool: str, detector: str) -> float:
    """Get confidence boost for a tool detector.

    Args:
        tool: Tool name
        detector: Detector/rule ID

    Returns:
        Confidence boost value (0.0 to 0.5)
    """
    tool_map = TOOL_DETECTOR_MAP.get(tool.lower())
    if not tool_map:
        return 0.0

    mapping = tool_map.get(detector)
    if mapping:
        return mapping.confidence_boost

    # Prefix matching
    if tool.lower() in {"echidna", "foundry", "halmos"}:
        for prefix, mapping in tool_map.items():
            if detector.startswith(prefix):
                return mapping.confidence_boost

    return 0.0


def get_tool_precision(tool: str, detector: str) -> float:
    """Get tool precision for a detector.

    Args:
        tool: Tool name
        detector: Detector/rule ID

    Returns:
        Precision score (0.0 to 1.0)
    """
    tool_map = TOOL_DETECTOR_MAP.get(tool.lower())
    if not tool_map:
        return 0.5  # Default moderate precision

    mapping = tool_map.get(detector)
    if mapping:
        return mapping.tool_precision

    # Prefix matching
    if tool.lower() in {"echidna", "foundry", "halmos"}:
        for prefix, mapping in tool_map.items():
            if detector.startswith(prefix):
                return mapping.tool_precision

    return 0.5


def get_all_patterns_for_category(category: str) -> List[str]:
    """Get all VKG patterns in a category.

    Args:
        category: Category name (reentrancy, access_control, etc.)

    Returns:
        List of unique VKG pattern IDs
    """
    patterns: Set[str] = set()
    category_lower = category.lower().replace("-", "_")

    for tool_map in TOOL_DETECTOR_MAP.values():
        for mapping in tool_map.values():
            if mapping.category.lower().replace("-", "_") == category_lower:
                patterns.add(mapping.vkg_pattern)

    return sorted(patterns)


def get_tools_for_pattern(pattern: str) -> List[str]:
    """Get all tools that can detect a VKG pattern.

    Args:
        pattern: VKG pattern ID

    Returns:
        List of tool names
    """
    tools: Set[str] = set()

    for tool_name, tool_map in TOOL_DETECTOR_MAP.items():
        for mapping in tool_map.values():
            if mapping.vkg_pattern == pattern:
                tools.add(tool_name)
                break

    return sorted(tools)


def get_patterns_covered_by_tools(tools: List[str]) -> Dict[str, float]:
    """Get patterns covered by a set of tools with coverage scores.

    Coverage score is the maximum precision across all covering tools.
    Used to determine which VKG patterns can be skipped.

    Args:
        tools: List of tool names

    Returns:
        Dictionary of pattern -> max_precision_score
    """
    coverage: Dict[str, float] = {}

    for tool in tools:
        tool_lower = tool.lower()
        tool_map = TOOL_DETECTOR_MAP.get(tool_lower, {})

        for mapping in tool_map.values():
            pattern = mapping.vkg_pattern
            precision = mapping.tool_precision

            # Keep max precision across tools
            if pattern not in coverage or precision > coverage[pattern]:
                coverage[pattern] = precision

    return coverage


def get_detector_count_by_tool() -> Dict[str, int]:
    """Get count of mapped detectors per tool.

    Returns:
        Dictionary of tool -> detector count
    """
    return {tool: len(detectors) for tool, detectors in TOOL_DETECTOR_MAP.items()}


def validate_mapping() -> List[str]:
    """Validate the mapping for potential issues.

    Checks for:
    - VKG patterns that have no tool coverage
    - Duplicate patterns with conflicting categories

    Returns:
        List of warning messages
    """
    warnings: List[str] = []

    # Collect all patterns and their categories
    pattern_categories: Dict[str, Set[str]] = {}

    for tool_name, tool_map in TOOL_DETECTOR_MAP.items():
        for detector, mapping in tool_map.items():
            pattern = mapping.vkg_pattern
            if pattern not in pattern_categories:
                pattern_categories[pattern] = set()
            pattern_categories[pattern].add(mapping.category)

    # Check for patterns with multiple categories
    for pattern, categories in pattern_categories.items():
        if len(categories) > 1:
            cats = ", ".join(sorted(categories))
            warnings.append(
                f"Pattern '{pattern}' has inconsistent categories: {cats}"
            )

    return warnings


def get_all_supported_tools() -> List[str]:
    """Get list of all tools with mappings.

    Returns:
        Sorted list of tool names
    """
    return sorted(TOOL_DETECTOR_MAP.keys())


def get_all_mapped_patterns() -> List[str]:
    """Get all unique VKG patterns in the mapping.

    Returns:
        Sorted list of unique pattern IDs
    """
    patterns: Set[str] = set()

    for tool_map in TOOL_DETECTOR_MAP.values():
        for mapping in tool_map.values():
            patterns.add(mapping.vkg_pattern)

    return sorted(patterns)


def get_high_precision_detectors(
    min_precision: float = 0.80,
) -> Dict[str, List[str]]:
    """Get detectors with precision above threshold.

    Args:
        min_precision: Minimum precision threshold

    Returns:
        Dictionary of tool -> list of high-precision detectors
    """
    result: Dict[str, List[str]] = {}

    for tool_name, tool_map in TOOL_DETECTOR_MAP.items():
        high_prec = [
            detector
            for detector, mapping in tool_map.items()
            if mapping.tool_precision >= min_precision
        ]
        if high_prec:
            result[tool_name] = sorted(high_prec)

    return result


__all__ = [
    "DetectorMapping",
    "TOOL_DETECTOR_MAP",
    "get_vkg_pattern",
    "get_category",
    "get_confidence_boost",
    "get_tool_precision",
    "get_all_patterns_for_category",
    "get_tools_for_pattern",
    "get_patterns_covered_by_tools",
    "get_detector_count_by_tool",
    "validate_mapping",
    "get_all_supported_tools",
    "get_all_mapped_patterns",
    "get_high_precision_detectors",
]
