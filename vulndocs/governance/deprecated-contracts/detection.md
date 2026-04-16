# Detection: Deprecated Contracts

## Overview

Deprecated contracts that remain accessible represent a significant attack surface. These "zombie contracts" may lack security improvements implemented in successor versions while retaining ability to manipulate critical state.

## Graph Signals

| Property | Expected | Critical? |
|----------|----------|-----------|
| `is_deprecated` | true | YES |
| `has_successor_contract` | true | YES |
| `no_access_control` | true | YES |
| `last_audit_date` | > 12 months old | HIGH |
| `visibility` | public/external | YES |

## Operation Sequences

**VULNERABLE Pattern:**
```
DEPRECATED_CONTRACT → MINTS_UNBACKED_TOKENS → TRANSFERS_VALUE_OUT
```

**Detection Heuristic:**
- Contract has newer version deployed
- Old contract still accepts calls
- No pause mechanism or access gates
- Critical functions remain active

## Behavioral Indicators

1. **No Deprecation Guards:**
   - Functions callable without version checks
   - Missing "deprecated" or "paused" state
   - No redirects to new contract

2. **State Manipulation Capability:**
   - Can mint tokens without backing
   - Can modify balances or permissions
   - Can trigger value transfers

3. **Outdated Security:**
   - Audit predates known vulnerabilities
   - Missing patches from successor contract
   - Lacks modern safety checks

## Code Patterns

### VULNERABLE: No Deprecation Protection

```solidity
// Old CauldronV4 contract (no audit since 2023)
contract CauldronV4 {
    // No deprecation check
    function mint(address to, uint amount) public {
        // Missing access control that exists in V5
        _mint(to, amount);
    }
}
```

**Detection Signals:**
- `is_deprecated: true`
- `no_access_control: true`
- `MINTS_UNBACKED_TOKENS` operation

### SAFE: Proper Deprecation

```solidity
contract CauldronV4 {
    bool public deprecated = true;
    address public successor;

    modifier notDeprecated() {
        require(!deprecated, "Use successor contract");
        _;
    }

    function mint(address to, uint amount)
        public
        notDeprecated
    {
        _mint(to, amount);
    }
}
```

**Safety Signals:**
- `has_deprecation_guard: true`
- `has_successor_contract: true`
- Functions blocked when deprecated

## Automated Checks

1. **Version Comparison:**
   - Compare deployed contract bytecode with latest audited version
   - Flag contracts with no updates in 12+ months

2. **Successor Detection:**
   - Check for newer contracts with similar interface
   - Identify if old contract should be disabled

3. **Access Control Delta:**
   - Compare permissions between old and new versions
   - Flag missing access controls in old contract

4. **Activity Monitoring:**
   - Alert on unexpected calls to deprecated contracts
   - Monitor for privilege escalation attempts

## False Positive Indicators

- Contract intentionally kept active for legacy support
- Deprecation with explicit security review
- Limited functionality (view-only)
- Protected by external governance

## Manual Review Checklist

- [ ] Is there a newer version of this contract?
- [ ] Does the old contract have all security patches from new version?
- [ ] Can the old contract still mint/transfer/modify critical state?
- [ ] Is there a deprecation mechanism?
- [ ] Has the contract been audited recently?
- [ ] Is unexpected activity monitored?

## Related Vulnerabilities

- **access-control/missing-modifier**: Deprecated contracts often lack access controls added in newer versions
- **upgrade/storage-collision**: Migration issues between contract versions
- **governance/quorum-manipulation**: Old governance contracts with outdated rules

---

**Pattern ID:** gov-deprecated-001
**Severity:** MEDIUM to CRITICAL (depends on functionality)
**Created:** 2026-01-09
**Source:** Rekt News 2025, Abracadabra analysis
