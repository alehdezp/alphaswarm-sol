---
name: vrs-mutate-contract
description: |
  Contract mutation skill. Generates Solidity contract variants that
  preserve vulnerability semantics for testing robustness.

  Invoke when user wants to:
  - Generate mutations: "mutate this contract", "/vrs-mutate-contract"
  - Create test variants: "generate 10 variants", "mutation testing"
  - Test pattern robustness: "does detection work with renamed vars"

  This skill generates contract mutations:
  1. Analyze source contract
  2. Apply mutation operators
  3. Validate semantic preservation
  4. Output variant files

slash_command: vrs:mutate-contract
context: fork
disable-model-invocation: false

allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(solc*)
  - Bash(uv run*)
---

# VRS Mutate Contract - Contract Mutation Generation

You are the **VRS Mutate Contract** skill, responsible for generating Solidity contract mutations that preserve vulnerability semantics. This skill creates test variants for validating detection robustness.

## Philosophy

From Test Forge Context:
- **40% of corpus is mutations** - Volume for statistical significance
- **Semantic preservation** - Mutations must preserve vulnerability (or explicitly mark as safe)
- **Pattern robustness** - Detection should not depend on variable names
- **10x variants** - Generate 10 variants per known pattern

**Mutation Goal:** Test that vulnerability detection works regardless of:
- Variable/function naming
- Code structure
- Statement ordering
- Comment presence

## How to Invoke

```bash
/vrs-mutate-contract <contract-path>
/vrs-mutate-contract ./contracts/Vault.sol
/vrs-mutate-contract ./contracts/Vault.sol --count 10
/vrs-mutate-contract ./contracts/Vault.sol --type rename
```

---

## Mutation Types

### 1. Identifier Renaming
**What:** Change variable, function, and parameter names
**Purpose:** Test that detection uses semantics, not name heuristics

```solidity
// Original
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount);
    (bool success, ) = msg.sender.call{value: amount}("");
    balances[msg.sender] -= amount;
}

// Mutated (rename)
function executeTransfer(uint256 value) external {
    require(userFunds[msg.sender] >= value);
    (bool ok, ) = msg.sender.call{value: value}("");
    userFunds[msg.sender] -= value;
}
```

### 2. Code Reordering
**What:** Permute statement order where semantically equivalent
**Purpose:** Test that detection finds ordering issues regardless of surrounding code

```solidity
// Original
function deposit() external payable {
    emit Deposited(msg.sender, msg.value);
    balances[msg.sender] += msg.value;
    totalDeposits += msg.value;
}

// Mutated (reorder)
function deposit() external payable {
    totalDeposits += msg.value;
    balances[msg.sender] += msg.value;
    emit Deposited(msg.sender, msg.value);
}
```

### 3. Pattern Variation
**What:** Same vulnerability, different implementation
**Purpose:** Test that detection catches vulnerability regardless of implementation style

```solidity
// Original (explicit call)
(bool success, ) = msg.sender.call{value: amount}("");

// Mutated (using transfer)
payable(msg.sender).transfer(amount);

// Mutated (using send)
bool sent = payable(msg.sender).send(amount);
```

### 4. Structural Changes
**What:** Split functions, merge functions, extract modifiers
**Purpose:** Test that detection works across different code structures

```solidity
// Original
function withdraw(uint256 amount) external {
    require(balances[msg.sender] >= amount);
    (bool success, ) = msg.sender.call{value: amount}("");
    balances[msg.sender] -= amount;
}

// Mutated (extracted check)
function _checkBalance(address user, uint256 amount) internal view {
    require(balances[user] >= amount);
}

function withdraw(uint256 amount) external {
    _checkBalance(msg.sender, amount);
    (bool success, ) = msg.sender.call{value: amount}("");
    balances[msg.sender] -= amount;
}
```

---

## Usage Examples

### Basic Mutation (10 variants)
```bash
/vrs-mutate-contract ./contracts/Vault.sol

# Output:
# Mutation Generation
# ===================
# Source: contracts/Vault.sol
# Vulnerability: reentrancy-classic
# Variants: 10
#
# Generated:
# - mutations/Vault_rename_001.sol (identifier renaming)
# - mutations/Vault_rename_002.sol (identifier renaming)
# - mutations/Vault_reorder_001.sol (code reordering)
# - mutations/Vault_pattern_001.sol (pattern variation)
# - mutations/Vault_struct_001.sol (structural change)
# ...
#
# Validation:
# - Compiles: 10/10
# - Preserves vulnerability: 10/10
# - Ready for testing
```

### Specific Count
```bash
/vrs-mutate-contract ./contracts/Vault.sol --count 5

# Generates exactly 5 variants
```

### Specific Mutation Type
```bash
/vrs-mutate-contract ./contracts/Vault.sol --type rename

# Only generates identifier renaming mutations
```

### Safe Variant Generation
```bash
/vrs-mutate-contract ./contracts/Vault.sol --include-safe

# Also generates patched (safe) versions
# Useful for false positive testing
```

---

## Output Format

### Mutation Report
```markdown
# Mutation Report

**Source:** contracts/Vault.sol
**Vulnerability:** reentrancy-classic
**Severity:** critical

## Generated Variants

| File | Type | Valid | Vuln Preserved |
|------|------|-------|----------------|
| Vault_rename_001.sol | rename | YES | YES |
| Vault_rename_002.sol | rename | YES | YES |
| Vault_reorder_001.sol | reorder | YES | YES |
| Vault_pattern_001.sol | pattern | YES | YES |
| Vault_struct_001.sol | structural | YES | YES |

## Mutation Details

### Vault_rename_001.sol
**Type:** Identifier renaming
**Changes:**
- `withdraw` -> `executeTransfer`
- `amount` -> `value`
- `balances` -> `userFunds`

**Compilation:** PASS
**Vulnerability:** PRESERVED

### Vault_safe_001.sol
**Type:** Patched (safe)
**Changes:**
- Added ReentrancyGuard
- CEI pattern applied

**Compilation:** PASS
**Vulnerability:** REMOVED (safe variant)
```

---

## Semantic Preservation

### Validation Steps

1. **Compilation Check**
   ```bash
   solc --bin mutation.sol
   # Must compile without errors
   ```

2. **Vulnerability Check**
   - Run pattern detection on mutated contract
   - Same vulnerability must be detected
   - If not detected, mutation is flagged for review

3. **Manual Review (if needed)**
   - Complex structural changes require manual verification
   - Tool flags uncertain cases

### Safe Variants

Safe variants are explicitly marked and used for:
- False positive testing (should NOT trigger detection)
- Regression testing for patches
- Teaching models what "fixed" looks like

```yaml
# Mutation metadata
mutation_id: Vault_safe_001
source: Vault.sol
type: safe_variant
vulnerability_preserved: false
changes:
  - "Added nonReentrant modifier"
  - "Reordered to CEI pattern"
purpose: false_positive_test
```

---

## Output Location

Mutations are written to:
```
.vrs/testing/corpus/mutations/
├── {contract}_rename_001.sol
├── {contract}_rename_002.sol
├── {contract}_reorder_001.sol
├── {contract}_pattern_001.sol
├── {contract}_struct_001.sol
└── {contract}_safe_001.sol (if --include-safe)
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `/vrs-test-full` | Runs mutation tests in Phase 6 |
| `/vrs-benchmark-model` | Tests models against mutations |
| `/vrs-track-gap` | Records mutation coverage gaps |

---

## Write Boundaries

This skill is restricted to writing in:
- `.vrs/testing/corpus/mutations/` - Mutation output directory

All other directories are read-only.

---

## Notes

- Default count is 10 variants per source contract
- All mutations must compile successfully
- Vulnerability preservation is verified automatically
- Safe variants are optional and explicitly marked
- Complex structural changes may need manual validation
- This skill CAN be invoked by orchestrators (disable-model-invocation: false)
