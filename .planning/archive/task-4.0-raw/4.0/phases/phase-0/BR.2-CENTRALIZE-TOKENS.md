# BR.2: Centralize Token Lists and Patterns

**Status:** TODO
**Priority:** MUST
**Estimated Hours:** 6-8h
**Depends On:** None (can start immediately, parallel with BR.1)
**Unlocks:** BR.3

---

## Objective

Extract all inline token lists, keyword sets, and regex patterns from builder.py into a centralized constants module. Currently, the same tokens are scattered across 6120 lines, making maintenance difficult.

---

## Current Problem (Examples from builder.py)

### Inline Token Lists (Scattered)

**Line 557-563:** Token names inline
```python
contract_has_multisig = contract_has_multisig or any(
    token in name
    for token in ("multisig", "multi_sig", "threshold", "signer", "signers", "owners")
    for name in lowered_state_var_names
)
```

**Line 588-594:** Repeated patterns
```python
has_only_owner = any(
    "onlyowner" in m.lower() or ("only" in m.lower() and "owner" in m.lower())
    for m in modifiers
)
```

**Line 661:** Nonce tokens inline
```python
NONCE_LIKE_NAMES = {"nonce", "counter", "sequence", "index", "txid", "txnid", "seqnum"}
```

### Problems

1. **Duplication** - Same tokens appear in multiple places
2. **No documentation** - Why these specific tokens?
3. **Hard to extend** - Adding a token requires finding all occurrences
4. **Not precompiled** - Regex patterns compiled at runtime every call

---

## Target State

Create `src/true_vkg/kg/constants.py`:

```python
"""Centralized security token lists and compiled patterns.

This module contains all keyword sets and regex patterns used for
security analysis. Changes here affect detection across the system.

WARNING: Modifying these constants may change detection behavior.
Run full test suite after any changes.
"""

from __future__ import annotations

import re
from typing import FrozenSet, Pattern


# =============================================================================
# ACCESS CONTROL TOKENS
# =============================================================================

#: Modifiers that indicate access control
ACCESS_MODIFIERS: FrozenSet[str] = frozenset({
    "onlyowner",
    "onlyadmin",
    "onlyrole",
    "onlyauthorized",
    "onlyminter",
    "onlygovernance",
    "onlyoperator",
    "onlyguardian",
    "onlykeeper",
    "requiresauth",
    "auth",
    "restricted",
})

#: Patterns indicating owner-only access
OWNER_MODIFIER_TOKENS: FrozenSet[str] = frozenset({
    "onlyowner",
    "only_owner",
    "owneronly",
    "owner_only",
})

#: Role-based access modifier tokens
ROLE_MODIFIER_TOKENS: FrozenSet[str] = frozenset({
    "onlyrole",
    "only_role",
    "hasrole",
    "has_role",
    "checkrole",
    "check_role",
})

#: Reentrancy guard modifier names
REENTRANCY_GUARD_MODIFIERS: FrozenSet[str] = frozenset({
    "nonreentrant",
    "non_reentrant",
    "noreentrancy",
    "no_reentrancy",
    "lock",
    "mutex",
})

#: Initializer modifier names (upgradeable contracts)
INITIALIZER_MODIFIERS: FrozenSet[str] = frozenset({
    "initializer",
    "reinitializer",
    "onlyinitializing",
    "only_initializing",
})

#: Proxy-only modifiers
PROXY_MODIFIERS: FrozenSet[str] = frozenset({
    "onlyproxy",
    "only_proxy",
    "proxydelegatecall",
    "notdelegatecall",
})


# =============================================================================
# STATE VARIABLE CLASSIFICATION TOKENS
# =============================================================================

#: Tokens indicating multisig functionality
MULTISIG_TOKENS: FrozenSet[str] = frozenset({
    "multisig",
    "multi_sig",
    "threshold",
    "signer",
    "signers",
    "owners",
    "requiredconfirmations",
    "required_confirmations",
})

#: Tokens indicating timelock functionality
TIMELOCK_TOKENS: FrozenSet[str] = frozenset({
    "timelock",
    "time_lock",
    "delay",
    "pending",
    "queue",
    "eta",
})

#: Tokens indicating governance functionality
GOVERNANCE_TOKENS: FrozenSet[str] = frozenset({
    "proposal",
    "vote",
    "voting",
    "quorum",
    "governance",
    "governor",
    "delegate",
    "ballot",
})

#: Tokens indicating nonce/sequence numbers
NONCE_TOKENS: FrozenSet[str] = frozenset({
    "nonce",
    "counter",
    "sequence",
    "sequencenumber",
    "sequence_number",
    "index",
    "txid",
    "txnid",
    "seqnum",
})

#: Tokens indicating privileged state variables
PRIVILEGED_STATE_TOKENS: FrozenSet[str] = frozenset({
    "owner",
    "admin",
    "role",
    "operator",
    "guardian",
    "keeper",
    "minter",
    "pauser",
    "authority",
})

#: Tokens indicating sensitive configuration
SENSITIVE_CONFIG_TOKENS: FrozenSet[str] = frozenset({
    "fee",
    "config",
    "reward",
    "collateral",
    "debt",
    "liquidity",
    "reserve",
    "cap",
    "oracle",
    "treasury",
    "governance",
    "pause",
    "allowlist",
    "denylist",
    "signer",
    "dependency",
})


# =============================================================================
# FUNCTION CLASSIFICATION TOKENS
# =============================================================================

#: Tokens indicating admin functions
ADMIN_FUNCTION_TOKENS: FrozenSet[str] = frozenset({
    "setowner",
    "set_owner",
    "transferownership",
    "transfer_ownership",
    "renounceownership",
    "renounce_ownership",
    "setadmin",
    "set_admin",
    "addadmin",
    "add_admin",
    "removeadmin",
    "remove_admin",
})

#: Tokens indicating emergency functions
EMERGENCY_FUNCTION_TOKENS: FrozenSet[str] = frozenset({
    "emergency",
    "pause",
    "unpause",
    "rescue",
    "recover",
    "shutdown",
    "kill",
})

#: Tokens indicating withdrawal functions
WITHDRAW_FUNCTION_TOKENS: FrozenSet[str] = frozenset({
    "withdraw",
    "claim",
    "redeem",
    "release",
    "harvest",
    "collect",
})

#: Role management function tokens
ROLE_GRANT_TOKENS: FrozenSet[str] = frozenset({
    "grant",
    "addrole",
    "add_role",
    "setrole",
    "set_role",
    "assignrole",
    "assign_role",
})

ROLE_REVOKE_TOKENS: FrozenSet[str] = frozenset({
    "revoke",
    "removerole",
    "remove_role",
    "revokerole",
    "revoke_role",
})


# =============================================================================
# ORACLE TOKENS
# =============================================================================

#: Chainlink oracle function names
ORACLE_FUNCTION_TOKENS: FrozenSet[str] = frozenset({
    "latestrounddata",
    "getrounddata",
    "latestanswer",
    "latestprice",
    "getprice",
    "get_price",
})

#: Tokens indicating TWAP usage
TWAP_TOKENS: FrozenSet[str] = frozenset({
    "twap",
    "observe",
    "consult",
    "gettwap",
    "get_twap",
    "timeweightedaverage",
})

#: Tokens for staleness checking
STALENESS_TOKENS: FrozenSet[str] = frozenset({
    "updatedat",
    "updated_at",
    "timestamp",
    "roundid",
    "round_id",
    "answeredinround",
})


# =============================================================================
# TOKEN INTERACTION TOKENS
# =============================================================================

#: ERC20 function names
ERC20_FUNCTION_TOKENS: FrozenSet[str] = frozenset({
    "transfer",
    "transferfrom",
    "transfer_from",
    "approve",
    "allowance",
    "balanceof",
    "balance_of",
    "totalsupply",
    "total_supply",
})

#: Safe transfer wrapper tokens
SAFE_ERC20_TOKENS: FrozenSet[str] = frozenset({
    "safetransfer",
    "safe_transfer",
    "safetransferfrom",
    "safe_transfer_from",
    "safeapprove",
    "safe_approve",
    "safeincreaseallowance",
    "safedecreaseallowance",
})


# =============================================================================
# COMPILED REGEX PATTERNS
# =============================================================================

#: Pattern for deadline-related parameters/checks
DEADLINE_PATTERN: Pattern[str] = re.compile(
    r"deadline|expir|valid(?:until|before)|timeout",
    re.IGNORECASE
)

#: Pattern for slippage-related parameters
SLIPPAGE_PATTERN: Pattern[str] = re.compile(
    r"slippage|minout|minamount|minreceived|maxin|maxamount|min_|max_",
    re.IGNORECASE
)

#: Pattern for balance/amount variables
BALANCE_PATTERN: Pattern[str] = re.compile(
    r"balance|amount|value|funds|deposit|stake",
    re.IGNORECASE
)

#: Pattern for callback function names
CALLBACK_PATTERN: Pattern[str] = re.compile(
    r"^on[A-Z]|callback|receive|hook",
    re.IGNORECASE
)

#: Pattern for swap-like function names
SWAP_PATTERN: Pattern[str] = re.compile(
    r"swap|exchange|trade|convert|sell|buy",
    re.IGNORECASE
)

#: Pattern for signature-related variables
SIGNATURE_PATTERN: Pattern[str] = re.compile(
    r"sig(?:nature)?|v|r|s|hash|digest",
    re.IGNORECASE
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def has_any_token(text: str, tokens: FrozenSet[str]) -> bool:
    """Check if text contains any of the tokens (case-insensitive).

    Args:
        text: String to search
        tokens: Set of tokens to find

    Returns:
        True if any token found in text (lowercased)
    """
    text_lower = text.lower()
    return any(token in text_lower for token in tokens)


def has_modifier_type(modifiers: list[str], modifier_tokens: FrozenSet[str]) -> bool:
    """Check if any modifier matches the token set.

    Args:
        modifiers: List of modifier names
        modifier_tokens: Set of tokens to match

    Returns:
        True if any modifier contains a token
    """
    for mod in modifiers:
        mod_lower = mod.lower()
        for token in modifier_tokens:
            if token in mod_lower:
                return True
    return False


def classify_modifier(modifier_name: str) -> str:
    """Classify a modifier by type.

    Args:
        modifier_name: Name of the modifier

    Returns:
        Classification: 'owner', 'role', 'reentrancy', 'initializer', 'proxy', 'unknown'
    """
    lower = modifier_name.lower()

    if any(t in lower for t in OWNER_MODIFIER_TOKENS):
        return "owner"
    if any(t in lower for t in ROLE_MODIFIER_TOKENS):
        return "role"
    if any(t in lower for t in REENTRANCY_GUARD_MODIFIERS):
        return "reentrancy"
    if any(t in lower for t in INITIALIZER_MODIFIERS):
        return "initializer"
    if any(t in lower for t in PROXY_MODIFIERS):
        return "proxy"

    return "unknown"
```

---

## Implementation Steps

### Step 1: Create constants.py (1h)

Create the file with the above structure. Include comprehensive docstrings.

### Step 2: Find all inline token lists (2h)

Search builder.py for patterns:

```bash
# Find inline tuples/sets
grep -n "for token in" src/true_vkg/kg/builder.py
grep -n 'frozenset\|set(' src/true_vkg/kg/builder.py
grep -n "in name for name in" src/true_vkg/kg/builder.py

# Find regex patterns
grep -n "re.compile\|re.search\|re.match" src/true_vkg/kg/builder.py
```

### Step 3: Extract to constants (2h)

For each inline list found:
1. Identify the category (access, oracle, token, etc.)
2. Add to appropriate section in constants.py
3. Document what the tokens detect

### Step 4: Update builder.py imports (1h)

```python
# At top of builder.py
from true_vkg.kg.constants import (
    ACCESS_MODIFIERS,
    MULTISIG_TOKENS,
    NONCE_TOKENS,
    # ... etc
)
```

### Step 5: Replace inline lists with constants (1h)

Find and replace, preserving exact behavior:

```python
# Before
NONCE_LIKE_NAMES = {"nonce", "counter", "sequence", ...}

# After
from true_vkg.kg.constants import NONCE_TOKENS
# Use NONCE_TOKENS directly
```

---

## Files to Modify

| File | Change |
|------|--------|
| `src/true_vkg/kg/constants.py` | CREATE - New file |
| `src/true_vkg/kg/__init__.py` | MODIFY - Export constants |
| `src/true_vkg/kg/builder.py` | MODIFY - Import and use constants |
| `tests/test_constants.py` | CREATE - Unit tests |

---

## Validation Commands

```bash
# Before (baseline)
uv run pytest tests/test_fingerprint.py tests/test_rename_resistance.py -v
uv run alphaswarm build-kg tests/contracts/BasicVault.sol --out /tmp/before-constants

# After changes
uv run pytest tests/test_constants.py -v
uv run pytest tests/test_fingerprint.py tests/test_rename_resistance.py -v
uv run alphaswarm build-kg tests/contracts/BasicVault.sol --out /tmp/after-constants

# Compare (MUST be identical)
diff <(jq -S . /tmp/before-constants/graph.json) <(jq -S . /tmp/after-constants/graph.json)
```

---

## Verification: No Inline Token Lists Remain

After completion, this should return 0 results:

```bash
# Should find NO inline token tuples
grep -c "for token in (" src/true_vkg/kg/builder.py
# Expected: 0

# Should find NO inline frozensets
grep -c 'frozenset({' src/true_vkg/kg/builder.py
# Expected: 0 (or only imports)
```

---

## Acceptance Criteria

- [ ] `src/true_vkg/kg/constants.py` exists with all token lists
- [ ] All token lists are `FrozenSet[str]` (immutable)
- [ ] All regex patterns are precompiled
- [ ] Unit tests in `tests/test_constants.py` pass
- [ ] No inline token lists remain in builder.py
- [ ] Graph fingerprint identical to baseline
- [ ] All existing tests still pass

---

## Rollback Procedure

```bash
# Remove new file
rm src/true_vkg/kg/constants.py

# Revert builder changes
git checkout HEAD -- src/true_vkg/kg/builder.py

# Verify
uv run pytest tests/ -v
```

---

*Task BR.2 | Version 1.0 | 2026-01-07*
