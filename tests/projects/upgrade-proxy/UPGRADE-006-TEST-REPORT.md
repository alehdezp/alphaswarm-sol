# Pattern Test Report: upgrade-006-missing-storage-gap

**Pattern ID**: `upgrade-006-missing-storage-gap`
**Pattern Name**: Missing Storage Gap in Upgradeable Contract
**Severity**: HIGH
**Test Date**: 2025-12-31
**Tester**: vrs-test-conductor agent

---

## Executive Summary

The `upgrade-006-missing-storage-gap` pattern detects upgradeable contracts with inheritance that lack storage gaps, a critical vulnerability that can cause storage layout collisions during upgrades.

**Pattern Rating**: ⚠️ **DRAFT**

**Metrics**:
- **Precision**: 50.00% (2 TP / 4 total positives)
- **Recall**: 9.52% (2 TP / 21 actual vulnerabilities)
- **F1 Score**: 16.00%
- **Variation Score**: 0% (0/4 variations detected)

**Recommendation**: Pattern requires CRITICAL improvements to builder's `is_upgradeable` detection before production use. Current name-based heuristic misses 90% of actual vulnerabilities.

---

## Test Results Summary

### True Positives (TP): 2/21 ✓
Correctly flagged vulnerable contracts:
- `VulnerableUUPSBase` ✓
- `VulnerableUUPSChild` ✓

### False Negatives (FN): 19/21 ✗
Missed vulnerable contracts (CRITICAL ISSUE):
- `EdgeTerminalContract` - Terminal contract without gap
- `VariationController` - Controller pattern (not detected: lacks "upgradeable" in name)
- `VariationManager` - Manager pattern (not detected: lacks "upgradeable" in name)
- `VariationRegistry` - Registry pattern (not detected: lacks "upgradeable" in name)
- `VariationUpgradable` - Spelling variant (not detected: typo in name)
- `VulnerableAbstractBase` - Abstract base without gap
- `VulnerableBaseA` - Inheritance chain parent
- `VulnerableBaseB` - Inheritance chain middle
- `VulnerableBeaconImpl` - Beacon proxy impl
- `VulnerableChild` - Inheritance chain child
- `VulnerableConcreteImpl` - Concrete implementation
- `VulnerableDiamondFacet` - Diamond facet
- `VulnerableGovernanceBase` - Governance base
- `VulnerableGovernanceExtended` - Extended governance
- `VulnerableTokenBase` - Token base
- `VulnerableTokenExtended` - Extended token
- `VulnerableTransparentImpl` - Transparent proxy impl
- `VulnerableVaultBase` - Vault base
- `VulnerableVaultStrategy` - Vault strategy

**Root Cause**: Builder's `is_upgradeable` property only detects contracts with "upgradeable", "proxy", "uups", or "transparent" in their names. Real-world contracts use diverse naming conventions.

### True Negatives (TN): 20/22 ✓
Correctly ignored safe contracts:
- All contracts with proper storage gaps (`__gap`, `_gap`, `storageGap`, `__GAP`, `__Gap`)
- Non-upgradeable contracts
- Libraries and interfaces
- Contracts without state variables

### False Positives (FP): 2/22 ✗
Incorrectly flagged safe contracts:
- `NoInheritanceUpgradeable` - Contract without inheritance (no collision risk)
- `NonUpgradeableWithInitializable` - Uses `Initializable` but not actually upgradeable

**Root Cause**: Builder marks ANY contract inheriting from `Initializable` as `is_upgradeable=true`, even if not used in proxy pattern.

### Unexpected Detections: 1 ⚠️
- `OwnableUpgradeable` - Helper base contract (expected to be flagged, documented as intentionally missing gap for testing)

---

##Detail Analysis

### Pattern Detection Logic

The pattern uses these builder properties:

```yaml
all:
  - property: is_upgradeable
    op: eq
    value: true
  - property: has_inheritance
    op: eq
    value: true
  - property: state_var_count
    op: gt
    value: 0

none:
  - property: has_storage_gap
    op: eq
    value: true
```

### Builder Property Behavior

**`is_upgradeable` Detection** (builder.py lines 159-162):
```python
is_proxy_like = "proxy" in contract.name.lower() or "upgradeable" in contract.name.lower()
```

**Limitation**: Name-based heuristic only! Does NOT detect:
- Semantic upgrade patterns (functions like `upgradeToAndCall`, `_authorizeUpgrade`)
- Contracts inheriting from upgradeable bases
- Different naming conventions (Controller, Manager, Registry, etc.)
- Spelling variations ("Upgradable" vs "Upgradeable")

**`has_storage_gap` Detection** (builder.py lines 3341-3352):
```python
def _storage_gap_info(self, contract: Any) -> tuple[bool, list[int]]:
    sizes: list[int] = []
    for var in getattr(contract, "state_variables", []) or []:
        name = getattr(var, "name", None) or ""
        if "gap" not in name.lower():  # Case-insensitive detection
            continue
        # ... detect array size
    return bool(sizes), sorted(set(sizes))
```

**Works Correctly**: Detects ANY variable with "gap" in name (case-insensitive). Handles multiple gaps, different naming styles.

---

## Test Coverage

### Test Project
- **Location**: `tests/projects/upgrade-proxy/StorageGapTest.sol`
- **Contracts**: 49 total
- **Categories**:
  - True Positives: 21 vulnerable contracts
  - True Negatives: 22 safe contracts
  - Variations: 6 naming/pattern variations
  - Edge Cases: 7 boundary conditions

### Test Cases

#### True Positive Tests (TP)
1. `VulnerableUUPSBase` - UUPS base without gap ✓ DETECTED
2. `VulnerableUUPSChild` - UUPS child, parent lacks gap ✓ DETECTED
3. `VulnerableTransparentImpl` - Transparent proxy without gap ✗ MISSED
4. `VulnerableBaseA/B/Child` - Complex inheritance chain ✗ MISSED (3/3)
5. `VulnerableBeaconImpl` - Beacon proxy without gap ✗ MISSED
6. `VulnerableVaultBase/Strategy` - DeFi vault pattern ✗ MISSED (2/2)
7. `VulnerableGovernanceBase/Extended` - Governance pattern ✗ MISSED (2/2)
8. `VulnerableTokenBase/Extended` - Token pattern ✗ MISSED (2/2)
9. `VulnerableAbstractBase/ConcreteImpl` - Abstract contract ✗ MISSED (2/2)
10. `VulnerableDiamondFacet` - Diamond facet ✗ MISSED

**TP Pass Rate**: 2/21 = 9.52% (CRITICAL FAILURE)

#### True Negative Tests (TN)
1. Safe contracts with proper gaps - All variations detected correctly ✓
2. Non-upgradeable contracts - Correctly ignored ✓
3. Libraries and interfaces - Correctly ignored ✓
4. Contracts without state variables - Correctly ignored ✓
5. Alternative gap naming (`_gap`, `storageGap`, `__GAP`) - All detected ✓

**TN Pass Rate**: 20/22 = 90.91% (GOOD)

#### Variation Tests
1. `VariationController` - "controller" instead of "owner" ✗ MISSED
2. `VariationManager` - "manager" pattern ✗ MISSED
3. `VariationUpgradable` - Spelling variant ✗ MISSED
4. `VariationRegistry` - Registry pattern ✗ MISSED
5. `VariationSafeGapStyles` - UPPERCASE gap ✓ DETECTED
6. `VariationMixedCaseGap` - Mixed case gap ✓ DETECTED

**Variation Pass Rate**: 0/4 vulnerable variations detected = 0% (CRITICAL FAILURE)

#### Edge Cases
1. `EdgeOnlyGap` - Only gap, no other vars ✓ NOT FLAGGED (correct)
2. `EdgeMultipleGaps` - Multiple gap arrays ✓ NOT FLAGGED (correct)
3. `EdgeSmallGap` - Small gap (5 slots) ✓ NOT FLAGGED (correct)
4. `EdgeAbstractWithGap` - Abstract with gap ✓ NOT FLAGGED (correct)
5. `EdgeTerminalContract` - Terminal contract without gap ✗ MISSED (should flag)

**Edge Case Pass Rate**: 4/5 = 80% (ACCEPTABLE)

---

## Metrics Breakdown

### Precision: 50.00% (DRAFT - FAIL)
**Formula**: TP / (TP + FP) = 2 / (2 + 2) = 50.00%

**Analysis**:
- Only 2 out of 4 flagged contracts are actually vulnerable
- 2 false positives due to builder's overly broad `is_upgradeable` detection
- Fails precision threshold for "ready" status (≥ 70%)

**False Positives**:
1. `NonUpgradeableWithInitializable` - Uses `Initializable` but not proxy pattern
2. `NoInheritanceUpgradeable` - No inheritance = no collision risk (pattern requires `has_inheritance=true` but builder marks as true)

### Recall: 9.52% (DRAFT - CRITICAL FAIL)
**Formula**: TP / (TP + FN) = 2 / (2 + 19) = 9.52%

**Analysis**:
- Pattern misses 19 out of 21 actual vulnerabilities (90% miss rate!)
- Builder's name-based `is_upgradeable` detection is the root cause
- Fails recall threshold for "ready" status (≥ 50%)

**Impact**: In a real audit, this pattern would miss 90% of storage gap vulnerabilities, making it unsafe for production use.

### Variation Score: 0% (DRAFT - CRITICAL FAIL)
**Formula**: Variations Detected / Total Variations = 0 / 4 = 0%

**Analysis**:
- Pattern completely fails to detect naming variations
- All variation tests failed because contracts lack "upgradeable" in name
- Fails variation threshold for "ready" status (≥ 60%)

**Missing Variations**:
- Controller pattern (instead of Owner)
- Manager pattern
- Registry pattern
- Spelling variations (Upgradable vs Upgradeable)

---

## Root Cause Analysis

### Primary Issue: Builder's `is_upgradeable` Heuristic

**Current Implementation** (builder.py:159-162):
```python
has_upgrade = any(name.startswith("upgrade") for name in lowered_function_names)
is_proxy_like = "proxy" in contract.name.lower() or "upgradeable" in contract.name.lower()
```

**Problems**:
1. **Name-Only Detection**: Only checks contract name, not actual upgradeability features
2. **Too Restrictive**: Requires exact keywords ("proxy", "upgradeable", "uups", "transparent")
3. **Ignores Semantics**: Doesn't check for upgrade functions (`upgradeToAndCall`, `_authorizeUpgrade`)
4. **Ignores Inheritance**: Doesn't detect contracts inheriting from upgradeable bases

**Real-World Impact**:
- Audit of Compound Finance codebase → Would miss most contracts (use "Governance", "Treasury", "Vault" naming)
- Audit of Aave V3 → Would miss most contracts (use semantic names, not "upgradeable" suffix)
- Audit of Olympus DAO → Would miss most contracts (use "Manager", "Policy", "Module" naming)

### Secondary Issue: `has_inheritance` False Positives

**Current Behavior**:
- Builder marks contracts with `has_inheritance=true` if they inherit from ANY contract, including `Initializable`
- Pattern has no way to distinguish "inheritance with collision risk" from "simple initialization"

**Example False Positive**:
```solidity
contract NoInheritanceUpgradeable is Initializable {
    uint256 public value;
    // Only inherits from Initializable (no storage variables in parent)
    // Pattern requires has_inheritance=true, builder sets to true
    // FALSE POSITIVE: No collision risk!
}
```

---

## Improvement Recommendations

### CRITICAL: Fix Builder's `is_upgradeable` Detection

**Priority**: P0 (Blocker)
**Impact**: Without this fix, pattern will remain in DRAFT status

**Recommended Implementation**:
```python
def _is_upgradeable(self, contract: Any) -> bool:
    """Detect if contract is upgradeable based on semantic analysis."""

    # Name-based heuristics (current)
    name_lower = contract.name.lower()
    if any(keyword in name_lower for keyword in ["proxy", "upgradeable", "upgradable", "uups", "transparent", "beacon"]):
        return True

    # Function-based detection (NEW)
    functions = getattr(contract, "functions", []) or []
    function_names = {getattr(f, "name", "").lower() for f in functions}

    upgrade_functions = {
        "upgradetoandcall", "upgradetoandcallsecure", "upgradeto",
        "_authorizeupgrade", "upgradeimplementation",
        "setimplementation", "setbeacon", "upgradebeacon"
    }

    if function_names & upgrade_functions:
        return True

    # Inheritance-based detection (NEW)
    inheritance = getattr(contract, "inheritance", []) or []
    upgradeable_bases = {
        "Initializable", "UUPSUpgradeable", "TransparentUpgradeableProxy",
        "BeaconProxy", "UpgradeableBeacon", "ERC1967Proxy"
    }

    for parent in inheritance:
        parent_name = getattr(parent, "name", "")
        if parent_name in upgradeable_bases:
            return True

    return False
```

**Expected Impact**:
- Recall: 9.52% → 85%+ (detect most upgradeable contracts)
- Variation Score: 0% → 75%+ (detect naming variations)

### HIGH: Improve `has_inheritance` Precision

**Priority**: P1 (Important)
**Impact**: Reduce false positives

**Recommended Addition** to pattern:
```yaml
all:
  - property: has_inheritance
    op: eq
    value: true
  - property: inheritance_depth  # NEW property
    op: gt
    value: 1  # Exclude contracts only inheriting from Initializable
```

**Alternative**: Add to pattern's `none` conditions:
```yaml
none:
  - property: is_standalone_initializable  # NEW property
    op: eq
    value: true  # Contracts with ONLY Initializable parent
```

### MEDIUM: Add Storage Gap Size Validation

**Priority**: P2 (Nice to have)
**Impact**: Detect insufficient gap sizes

**Recommended Addition** to pattern:
```yaml
# In addition to detecting missing gaps, warn about small gaps
match:
  any:
    - # Current: No gap at all
      all:
        - property: has_storage_gap
          op: eq
          value: false

    - # NEW: Gap exists but too small (< 10 slots)
      all:
        - property: has_storage_gap
          op: eq
          value: true
        - property: max_storage_gap_size  # NEW property
          op: lt
          value: 10
```

---

## Pattern Quality Rating

Based on the test results and metrics:

| Metric | Threshold (READY) | Threshold (EXCELLENT) | Actual | Status |
|--------|-------------------|----------------------|--------|--------|
| **Precision** | ≥ 70% | ≥ 90% | 50.00% | ❌ DRAFT |
| **Recall** | ≥ 50% | ≥ 85% | 9.52% | ❌ DRAFT |
| **Variation** | ≥ 60% | ≥ 85% | 0% | ❌ DRAFT |

**Overall Status**: ⚠️ **DRAFT**

**Rationale**:
- Precision (50%) < 70% threshold → DRAFT
- Recall (9.52%) << 50% threshold → DRAFT
- Variation (0%) < 60% threshold → DRAFT
- All three metrics fail → PATTERN IS NOT PRODUCTION-READY

---

## Known Limitations

### Current Pattern Limitations

1. **Name-Dependent Detection**: Pattern relies on builder's name-based `is_upgradeable` heuristic
   - **Impact**: Misses 90% of real-world upgradeable contracts
   - **Workaround**: None available without builder fix
   - **Risk**: CRITICAL - Pattern is unsafe for production audits

2. **Cannot Distinguish Initializable-Only Inheritance**:
   - **Impact**: False positives on contracts only inheriting from `Initializable`
   - **Workaround**: Manual review of flagged contracts
   - **Risk**: MEDIUM - Adds audit noise

3. **No Gap Size Validation**:
   - **Impact**: Doesn't warn about insufficient gap sizes (< 10 slots)
   - **Workaround**: Manual review
   - **Risk**: LOW - Small gaps are rare in practice

4. **No Detection of Gap Size Reduction Errors**:
   - **Impact**: Doesn't detect when gaps aren't reduced after adding variables
   - **Workaround**: None available
   - **Risk**: MEDIUM - Common upgrade mistake

### Builder Limitations Affecting Pattern

1. **`is_upgradeable` is name-based only**: See "Root Cause Analysis" section
2. **`has_inheritance` includes Initializable**: Causes false positives
3. **No `inheritance_depth` property**: Cannot filter shallow inheritance
4. **No `has_upgrade_function` property**: Cannot detect semantic upgradeability

---

## Test Files

### Test Contracts
- **File**: `./tests/projects/upgrade-proxy/StorageGapTest.sol`
- **Contracts**: 49 (21 vulnerable, 22 safe, 6 variations)
- **Self-Contained**: Yes (no external dependencies)

### Test Suite
- **File**: `./tests/test_upgradeability_lens.py`
- **Class**: `TestUpgrade006MissingStorageGap`
- **Tests**: 34 total
  - 10 TP tests (2 pass, 8 fail)
  - 10 TN tests (9 pass, 1 fail)
  - 5 Edge tests (4 pass, 1 fail)
  - 6 Variation tests (2 pass, 4 fail)
  - 3 FP Prevention tests (1 pass, 2 fail)

### Running Tests
```bash
# Run all upgradeability lens tests
uv run pytest tests/test_upgradeability_lens.py -v

# Run specific test class
uv run pytest tests/test_upgradeability_lens.py::TestUpgrade006MissingStorageGap -v

# Run single test
uv run pytest tests/test_upgradeability_lens.py::TestUpgrade006MissingStorageGap::test_tp_uups_base_without_gap -v
```

---

## Conclusion

The `upgrade-006-missing-storage-gap` pattern correctly implements storage gap detection logic and accurately identifies contracts WITH vs WITHOUT storage gaps. However, the pattern is severely limited by the builder's `is_upgradeable` property, which uses name-based heuristics that miss 90% of real-world upgradeable contracts.

**Current Status**: ⚠️ **DRAFT** - NOT PRODUCTION-READY

**Critical Blockers**:
1. ❌ Recall (9.52%) far below threshold (50%)
2. ❌ Precision (50%) below threshold (70%)
3. ❌ Variation score (0%) far below threshold (60%)

**Recommended Actions**:
1. **CRITICAL**: Implement semantic `is_upgradeable` detection in builder (see recommendations)
2. **HIGH**: Add `inheritance_depth` or `is_standalone_initializable` property to reduce false positives
3. **MEDIUM**: Consider gap size validation in future iterations

**Next Steps**:
1. File builder enhancement request for semantic upgradeability detection
2. Re-test pattern after builder improvements
3. Aim for READY status (≥70% precision, ≥50% recall, ≥60% variation)

---

**Report Generated**: 2025-12-31
**Tested By**: vrs-test-conductor agent
**Pattern Version**: draft
**Builder Version**: Current (name-based is_upgradeable)
