// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// =============================================================================
// TEST CONTRACT: Semantic Privileged State Write Detection
// =============================================================================
//
// This contract demonstrates why SEMANTIC detection (writes_privileged_state)
// is superior to REGEX name matching (set*, update*, configure*, etc.).
//
// Pattern being tested: auth-003-unprotected-privileged-write
// Replaces: auth-012 (regex-based pattern)
//
// =============================================================================

contract SemanticPrivilegedStateTest {
    // Privileged state variables
    address public owner;
    address public admin;
    mapping(address => bool) public roles;
    address public treasury;
    uint256 public fee;
    address public implementation; // For upgradeable contracts
    bool public paused;

    // Non-privileged state
    uint256 public counter;
    string public name;

    constructor() {
        owner = msg.sender;
        admin = msg.sender;
    }

    // =============================================================================
    // TRUE POSITIVES: Should be CAUGHT by semantic pattern (7 functions)
    // =============================================================================

    // TP1: Obfuscated function name - MISSED by regex, CAUGHT by semantic
    // Writes privileged state (owner) without access control
    function fn_0x123abc(address newOwner) external {
        owner = newOwner; // VULNERABLE: writes_privileged_state=true, has_access_gate=false
    }

    // TP2: Alternative naming convention - MISSED by regex, CAUGHT by semantic
    // Doesn't match regex pattern (adjust*, alter*, shift*)
    function adjustControlAddress(address newAdmin) external {
        admin = newAdmin; // VULNERABLE: writes_privileged_state=true, has_access_gate=false
        // Note: 'admin' is tagged as 'owner' by heuristics
    }

    // TP3: Generic name - MISSED by regex, CAUGHT by semantic
    function changeIt(address newImpl) external {
        implementation = newImpl; // VULNERABLE: writes_privileged_state=true, has_access_gate=false
    }

    // TP4: Abbreviated name - MISSED by regex, CAUGHT by semantic
    function chg(address newTreasury) external {
        treasury = newTreasury; // VULNERABLE: writes_privileged_state=true, has_access_gate=false
    }

    // TP5: Role manipulation without "grant" prefix - MISSED by regex, CAUGHT by semantic
    function assignRole(address user) external {
        roles[user] = true; // VULNERABLE: writes_privileged_state=true, has_access_gate=false
    }

    // TP6: Pause state without "pause" prefix - MISSED by regex, CAUGHT by semantic
    function toggleEmergency(bool status) external {
        paused = status; // VULNERABLE: writes_privileged_state=true, has_access_gate=false
    }

    // TP7: Matches regex BUT ALSO writes privileged state - CAUGHT by BOTH
    function setOwner(address newOwner) external {
        owner = newOwner; // VULNERABLE: writes_privileged_state=true, has_access_gate=false
    }

    // =============================================================================
    // TRUE NEGATIVES: Should NOT be caught (safe patterns)
    // =============================================================================

    // TN1: Protected privileged write - onlyOwner modifier
    function setOwnerProtected(address newOwner) external {
        require(msg.sender == owner, "Not owner");
        owner = newOwner; // SAFE: has_access_gate=true
    }

    // TN2: Constructor - intentional setup
    // Should be excluded by pattern's none condition: is_constructor=true

    // TN3: Non-privileged state write (matches regex but not privileged)
    // Regex would catch this (FALSE POSITIVE), semantic pattern filters it out
    function setCounter(uint256 newCounter) external {
        counter = newCounter; // NOT privileged state, writes_privileged_state=false
    }

    // TN4: View function (can't modify state)
    function getOwner() external view returns (address) {
        return owner; // SAFE: is_view=true (excluded by none condition)
    }

    // =============================================================================
    // EDGE CASES: Complex scenarios
    // =============================================================================

    // EC1: Protected role grant
    function grantRoleProtected(address user) external {
        require(msg.sender == admin, "Not admin");
        roles[user] = true; // SAFE: has_access_gate=true
    }

    // EC2: Two-step ownership transfer (first step)
    address public pendingOwner;

    function transferOwnership(address newOwner) external {
        require(msg.sender == owner, "Not owner");
        pendingOwner = newOwner; // SAFE: has_access_gate=true
        // Note: pendingOwner is NOT tagged as privileged state
        // Only owner/admin/roles/etc are privileged
    }

    // EC3: Accept ownership (second step)
    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "Not pending owner");
        owner = pendingOwner; // SAFE: has_access_gate=true (via pendingOwner check)
        pendingOwner = address(0);
    }

    // EC4: Internal helper (not externally callable)
    // Pattern requires visibility in [public, external], so this is excluded
    function _updateOwnerInternal(address newOwner) internal {
        owner = newOwner; // SAFE: visibility=internal (not matched by pattern)
    }
}

// =============================================================================
// SUMMARY: Why Semantic Detection Wins
// =============================================================================
//
// REGEX PATTERN (auth-012) PROBLEMS:
// 1. MISSES: fn_0x123abc, adjustControlAddress, changeIt, chg, assignRole, toggleEmergency
// 2. FALSE POSITIVES: setCounter (matches "set*" but not privileged state)
//
// SEMANTIC PATTERN (auth-003) ADVANTAGES:
// 1. CATCHES ALL: All 7 vulnerable functions detected regardless of naming
// 2. NO FALSE POSITIVES: setCounter excluded (writes_privileged_state=false)
// 3. IMPLEMENTATION-AGNOSTIC: Works with any naming convention
// 4. OBFUSCATION-RESISTANT: Works with renamed/obfuscated code
//
// DETECTED VULNERABILITIES:
// - 3x owner writes (owner variable x2 + admin variable x1)
// - 1x treasury write
// - 1x upgrade write (implementation variable)
// - 1x role write (roles mapping)
// - 1x pause write (paused variable)
//
// NOTE: Privileged state categories in VKG are: owner, role, governance, upgrade,
// pause, allowlist, denylist, oracle, treasury, signer
//
// =============================================================================
