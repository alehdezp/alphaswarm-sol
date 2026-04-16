# BR.1: Extract Context Dataclasses

**Status:** TODO
**Priority:** MUST
**Estimated Hours:** 8-12h
**Depends On:** None (can start immediately)
**Unlocks:** BR.3

---

## Objective

Extract precomputed context objects from inline computations in builder.py. Currently, `_add_functions` recomputes the same contract-level data for every function. This task creates typed dataclasses to hold precomputed values.

---

## Current Problem (builder.py lines 511-580)

Every function iteration recomputes contract-level data:

```python
def _add_functions(self, graph: KnowledgeGraph, contract: Any, contract_node: Node) -> None:
    functions = getattr(contract, "functions", []) or []
    function_names = [fn.name for fn in functions if getattr(fn, "name", None)]
    lowered_function_names = [name.lower() for name in function_names]  # RECOMPUTED PER CONTRACT
    contract_is_proxy_like = "proxy" in contract.name.lower() or ...    # RECOMPUTED PER CONTRACT
    contract_has_upgrade_function = any(...)                            # RECOMPUTED PER CONTRACT
    # ... 70 more lines of contract-level computation BEFORE the for loop

    for fn in functions:  # Now we iterate 10-100 times with same context
        # Function-level work...
```

---

## Target State

Create `src/true_vkg/kg/contexts.py`:

```python
"""Typed context objects for BSKG builder.

These dataclasses hold precomputed data to avoid redundant computation
during graph construction. Contract-level context is computed once per
contract, function-level context is computed once per function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, FrozenSet, Dict, List, Set, Optional


@dataclass(frozen=True)
class ContractContext:
    """Precomputed contract-level signals.

    Computed once per contract, reused for all functions in that contract.
    """
    name: str
    name_lower: str

    # Function metadata
    function_names: FrozenSet[str]
    lowered_function_names: FrozenSet[str]

    # State variable metadata
    state_var_names: FrozenSet[str]
    lowered_state_var_names: FrozenSet[str]
    mapping_state_var_names: FrozenSet[str]
    array_state_var_names: FrozenSet[str]

    # Contract classification
    is_interface: bool
    is_library: bool
    is_proxy_like: bool
    is_implementation_contract: bool
    is_upgradeable: bool
    is_uups_proxy: bool
    is_beacon_proxy: bool
    is_diamond_proxy: bool

    # Feature flags
    has_upgrade_function: bool
    has_multicall: bool
    has_governance: bool
    has_timelock: bool
    has_multisig: bool
    has_withdraw: bool
    has_emergency_withdraw: bool
    has_emergency_pause: bool
    has_beacon_state: bool

    # Compiler info (from contract node)
    compiler_version_lt_08: bool
    uses_safemath: bool


@dataclass(frozen=True)
class FunctionContext:
    """Precomputed function-level signals.

    Computed once per function, passed to detector modules.
    """
    name: str
    name_lower: str
    label: str  # Contract.function format
    visibility: str

    # Parameters
    parameter_names: FrozenSet[str]
    parameter_types: tuple  # Immutable
    address_param_names: FrozenSet[str]
    array_param_names: FrozenSet[str]
    amount_param_names: FrozenSet[str]
    bytes_param_names: FrozenSet[str]

    # Modifiers
    modifiers: FrozenSet[str]
    access_gate_mods: FrozenSet[str]
    has_reentrancy_guard: bool
    has_only_owner: bool
    has_only_role: bool
    has_initializer_modifier: bool
    has_only_proxy_modifier: bool

    # Calls
    has_external_calls: bool
    has_internal_calls: bool
    uses_delegatecall: bool
    uses_call: bool
    external_call_count: int
    low_level_call_names: FrozenSet[str]

    # State access
    reads_state_names: FrozenSet[str]
    writes_state_names: FrozenSet[str]
    state_read_targets: Dict[str, FrozenSet[str]]  # var -> tags
    state_write_targets: Dict[str, FrozenSet[str]]
    writes_privileged_state: bool
    writes_sensitive_config: bool

    # Special variables
    uses_msg_sender: bool
    uses_tx_origin: bool
    uses_msg_value: bool
    uses_block_timestamp: bool
    uses_block_number: bool
    uses_ecrecover: bool

    # Source info
    file_path: str
    line_start: int
    line_end: int
    source_text: str
    source_text_lower: str


def build_contract_context(contract: Any, contract_node: "Node") -> ContractContext:
    """Build ContractContext from Slither contract object.

    Args:
        contract: Slither Contract object
        contract_node: Already-created contract node with properties

    Returns:
        Frozen ContractContext with all precomputed values
    """
    functions = getattr(contract, "functions", []) or []
    function_names = frozenset(fn.name for fn in functions if getattr(fn, "name", None))
    lowered_function_names = frozenset(name.lower() for name in function_names)

    state_vars = getattr(contract, "state_variables", []) or []
    state_var_names = frozenset(
        getattr(var, "name", "") for var in state_vars if getattr(var, "name", None)
    )
    lowered_state_var_names = frozenset(name.lower() for name in state_var_names)

    mapping_state_var_names = frozenset(
        getattr(var, "name", "")
        for var in state_vars
        if "mapping" in str(getattr(var, "type", "") or "").lower()
    )
    array_state_var_names = frozenset(
        getattr(var, "name", "")
        for var in state_vars
        if "[]" in str(getattr(var, "type", "") or "")
    )

    name_lower = contract.name.lower()

    is_proxy_like = "proxy" in name_lower or "upgradeable" in name_lower
    has_upgrade_function = any(name.startswith("upgrade") for name in lowered_function_names)
    is_implementation_contract = (
        not is_proxy_like and
        (has_upgrade_function or "implementation" in name_lower or "logic" in name_lower)
    )

    return ContractContext(
        name=contract.name,
        name_lower=name_lower,
        function_names=function_names,
        lowered_function_names=lowered_function_names,
        state_var_names=state_var_names,
        lowered_state_var_names=lowered_state_var_names,
        mapping_state_var_names=mapping_state_var_names,
        array_state_var_names=array_state_var_names,
        is_interface=getattr(contract, "is_interface", False),
        is_library=getattr(contract, "is_library", False),
        is_proxy_like=is_proxy_like,
        is_implementation_contract=is_implementation_contract,
        is_upgradeable=is_proxy_like or has_upgrade_function or is_implementation_contract,
        is_uups_proxy=contract_node.properties.get("proxy_type") == "uups",
        is_beacon_proxy=contract_node.properties.get("proxy_type") == "beacon",
        is_diamond_proxy="diamond" in name_lower,
        has_upgrade_function=has_upgrade_function,
        has_multicall=any("multicall" in name for name in lowered_function_names),
        has_governance=contract_node.properties.get("has_governance", False),
        has_timelock=contract_node.properties.get("has_timelock", False),
        has_multisig=contract_node.properties.get("has_multisig", False),
        has_withdraw=any(
            any(token in name for token in ("withdraw", "claim", "redeem", "release"))
            for name in lowered_function_names
        ),
        has_emergency_withdraw=any(
            "emergency" in name and any(token in name for token in ("withdraw", "rescue", "recover"))
            for name in lowered_function_names
        ),
        has_emergency_pause=any("pause" in name for name in lowered_function_names),
        has_beacon_state=any("beacon" in name for name in lowered_state_var_names),
        compiler_version_lt_08=contract_node.properties.get("compiler_version_lt_08", False),
        uses_safemath=contract_node.properties.get("uses_safemath", False),
    )


# build_function_context implementation follows similar pattern...
```

---

## Implementation Steps

### Step 1: Create the file (30 min)

```bash
# Create contexts.py
touch src/true_vkg/kg/contexts.py
```

### Step 2: Extract ContractContext fields (2h)

Look at builder.py lines 511-580. Every line that computes something BEFORE the `for fn in functions:` loop is a candidate for ContractContext.

Search patterns:
```bash
grep -n "contract_" src/true_vkg/kg/builder.py | head -50
```

### Step 3: Extract FunctionContext fields (3h)

Look at builder.py lines 581-1000. Every line inside the for loop that computes from `fn` is a FunctionContext candidate.

### Step 4: Write builder functions (2h)

Create `build_contract_context()` and `build_function_context()` that convert Slither objects to frozen dataclasses.

### Step 5: Test extraction correctness (2h)

Create test that:
1. Builds graph old way (inline)
2. Builds graph new way (with contexts)
3. Compares fingerprints

---

## Files to Modify

| File | Change |
|------|--------|
| `src/true_vkg/kg/contexts.py` | CREATE - New file |
| `src/true_vkg/kg/__init__.py` | MODIFY - Export contexts |
| `src/true_vkg/kg/builder.py` | MODIFY - Import contexts (NOT logic changes yet) |
| `tests/test_contexts.py` | CREATE - Unit tests |

---

## Validation Commands

```bash
# Before starting (baseline)
uv run pytest tests/test_fingerprint.py -v
cp /tmp/test-output.txt /tmp/baseline-output.txt

# After creating contexts.py
uv run pytest tests/test_contexts.py -v

# Verify no builder changes affected fingerprint
uv run pytest tests/test_fingerprint.py -v
diff /tmp/baseline-output.txt /tmp/test-output.txt  # Should be empty
```

---

## Acceptance Criteria

- [ ] `src/true_vkg/kg/contexts.py` exists with ContractContext and FunctionContext
- [ ] Both dataclasses are frozen (immutable)
- [ ] `build_contract_context()` and `build_function_context()` functions work
- [ ] Unit tests in `tests/test_contexts.py` pass
- [ ] NO changes to builder.py logic (only imports)
- [ ] Graph fingerprint identical to baseline
- [ ] All existing tests still pass

---

## Rollback Procedure

If anything breaks:

```bash
# Remove the new file
rm src/true_vkg/kg/contexts.py

# Revert any builder.py changes
git checkout HEAD -- src/true_vkg/kg/builder.py

# Verify clean state
uv run pytest tests/ -v
```

---

## What This Enables

After BR.1 is complete, BR.3 (Split Detectors) can use these context objects instead of passing around raw Slither objects. Each detector module will receive typed, precomputed data.

---

*Task BR.1 | Version 1.0 | 2026-01-07*
