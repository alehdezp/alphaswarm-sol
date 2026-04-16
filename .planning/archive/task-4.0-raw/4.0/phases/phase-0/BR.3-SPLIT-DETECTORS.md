# BR.3: Split Detectors into Modules

**Status:** TODO
**Priority:** MUST
**Estimated Hours:** 40-60h (THIS IS THE LARGEST TASK)
**Depends On:** BR.1 (contexts), BR.2 (constants), BR.6 (protocols)
**Unlocks:** BR.4, BR.5

---

## WARNING: This Task is Complex

The `_add_functions` method is **1382 lines** (lines 511-1892). This single method does:

1. Contract-level precomputation (70 lines)
2. Function loop iteration
3. Parameter extraction
4. Modifier analysis
5. Call analysis
6. State access analysis
7. Security signal detection (access, reentrancy, oracle, token, etc.)
8. Node creation
9. Edge creation
10. Rich edge generation

This task extracts security signal detection into separate modules.

---

## Objective

Split the 1382-line `_add_functions` into:

```
src/true_vkg/kg/detectors/
├── __init__.py           # Registry and interface
├── base.py               # DetectorBase class
├── access_control.py     # has_access_gate, writes_privileged_state
├── reentrancy.py         # state_write_after_external_call
├── oracle.py             # reads_oracle_price, has_staleness_check
├── token.py              # uses_erc20_transfer, token_return_guarded
├── math.py               # has_unchecked_arithmetic
├── proxy.py              # is_proxy_like, proxy_type
├── mev.py                # swap_like, risk_missing_slippage
├── callback.py           # callback_chain_surface
├── loop.py               # has_unbounded_loop, external_calls_in_loop
├── crypto.py             # uses_ecrecover, signature analysis
└── external_call.py      # call target validation, low-level calls
```

---

## Current Structure (builder.py lines 511-1892)

```
_add_functions (1382 lines)
├── Contract context setup (lines 512-580, 68 lines)
├── Function loop start (line 581)
│   ├── Source location (582-583)
│   ├── Label/modifiers (584-600)
│   ├── Call extraction (596-641)
│   ├── Parameter extraction (642-710)
│   ├── State access (666-710)
│   ├── Access control signals (711-800) → access_control.py
│   ├── Reentrancy signals (800-900) → reentrancy.py
│   ├── Token signals (900-1000) → token.py
│   ├── Oracle signals (1000-1100) → oracle.py
│   ├── Loop signals (1100-1200) → loop.py
│   ├── MEV signals (1200-1300) → mev.py
│   ├── Proxy signals (1300-1400) → proxy.py
│   ├── External call signals (1400-1500) → external_call.py
│   ├── Callback signals (1500-1550) → callback.py
│   ├── Crypto signals (1550-1650) → crypto.py
│   ├── Node creation (1650-1800)
│   └── Edge creation (1800-1892)
```

---

## Detector Interface

Create `src/true_vkg/kg/detectors/base.py`:

```python
"""Base detector interface for BSKG signal extraction.

All detectors must implement this protocol. They receive typed context
objects and return property dictionaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Protocol, TypeVar, Generic

from true_vkg.kg.contexts import ContractContext, FunctionContext


class DetectorResult:
    """Result from a detector run."""

    def __init__(self):
        self.properties: Dict[str, Any] = {}
        self.evidence: List[Dict[str, Any]] = []
        self.warnings: List[str] = []

    def set_property(self, name: str, value: Any) -> None:
        """Set a property value."""
        self.properties[name] = value

    def add_evidence(
        self,
        property_name: str,
        source: str,
        line: int,
        evidence_type: str = "detection"
    ) -> None:
        """Add evidence for a property."""
        self.evidence.append({
            "property": property_name,
            "source": source,
            "line": line,
            "type": evidence_type,
        })


class Detector(Protocol):
    """Protocol for signal detectors.

    All detectors must implement:
    - name: Unique identifier
    - dependencies: List of detector names that must run first
    - detect: Main detection method
    """

    name: str
    dependencies: List[str]

    def detect(
        self,
        contract_ctx: ContractContext,
        function_ctx: FunctionContext,
        slither_fn: Any,  # Slither function object
    ) -> DetectorResult:
        """Run detection and return properties.

        Args:
            contract_ctx: Precomputed contract context
            function_ctx: Precomputed function context
            slither_fn: Raw Slither function for advanced analysis

        Returns:
            DetectorResult with properties and evidence
        """
        ...


class DetectorBase(ABC):
    """Base class for detectors with common utilities."""

    name: str = "base"
    dependencies: List[str] = []

    @abstractmethod
    def detect(
        self,
        contract_ctx: ContractContext,
        function_ctx: FunctionContext,
        slither_fn: Any,
    ) -> DetectorResult:
        """Run detection."""
        ...

    def _has_any_modifier(
        self,
        function_ctx: FunctionContext,
        modifier_names: frozenset
    ) -> bool:
        """Check if function has any of the specified modifiers."""
        return bool(function_ctx.modifiers & modifier_names)
```

---

## Example Detector: Access Control

Create `src/true_vkg/kg/detectors/access_control.py`:

```python
"""Access control signal detector.

Detects:
- has_access_gate: Function has access restriction
- writes_privileged_state: Modifies owner/admin/role state
- public_wrapper_without_access_gate: Public function calling internal without gate
- tx_origin_in_require: Uses tx.origin for auth (dangerous)
"""

from __future__ import annotations

from typing import Any, List

from true_vkg.kg.contexts import ContractContext, FunctionContext
from true_vkg.kg.constants import (
    ACCESS_MODIFIERS,
    OWNER_MODIFIER_TOKENS,
    ROLE_MODIFIER_TOKENS,
    PRIVILEGED_STATE_TOKENS,
)
from true_vkg.kg.detectors.base import Detector, DetectorBase, DetectorResult


class AccessControlDetector(DetectorBase):
    """Detect access control signals."""

    name = "access_control"
    dependencies: List[str] = []  # No dependencies, runs first

    def detect(
        self,
        contract_ctx: ContractContext,
        function_ctx: FunctionContext,
        slither_fn: Any,
    ) -> DetectorResult:
        result = DetectorResult()

        # has_access_gate: modifier-based or logic-based
        has_modifier_gate = bool(function_ctx.access_gate_mods)
        has_logic_gate = self._detect_logic_gate(function_ctx, slither_fn)
        has_access_gate = has_modifier_gate or has_logic_gate

        result.set_property("has_access_gate", has_access_gate)
        result.set_property("has_access_modifier", has_modifier_gate)

        if has_modifier_gate:
            result.add_evidence(
                "has_access_gate",
                f"Modifier: {function_ctx.access_gate_mods}",
                function_ctx.line_start,
                "modifier"
            )

        # has_only_owner
        result.set_property("has_only_owner", function_ctx.has_only_owner)

        # has_only_role
        result.set_property("has_only_role", function_ctx.has_only_role)

        # writes_privileged_state
        result.set_property(
            "writes_privileged_state",
            function_ctx.writes_privileged_state
        )

        # public_wrapper_without_access_gate
        is_public = function_ctx.visibility in ("public", "external")
        has_internal_calls = function_ctx.has_internal_calls
        public_wrapper_no_gate = is_public and has_internal_calls and not has_access_gate

        result.set_property(
            "public_wrapper_without_access_gate",
            public_wrapper_no_gate
        )

        # tx_origin_in_require (dangerous auth pattern)
        result.set_property(
            "uses_tx_origin",
            function_ctx.uses_tx_origin
        )

        # access_control_uses_or (weak pattern)
        result.set_property(
            "access_control_uses_or",
            self._detect_or_pattern(slither_fn)
        )

        return result

    def _detect_logic_gate(
        self,
        function_ctx: FunctionContext,
        slither_fn: Any
    ) -> bool:
        """Detect require(msg.sender == owner) style access control."""
        # Check for msg.sender comparisons in require statements
        source = function_ctx.source_text_lower
        if "msg.sender" not in source:
            return False

        # Look for require/assert with msg.sender comparison
        if "require" in source or "assert" in source:
            # Patterns: require(msg.sender == ...), require(... == msg.sender)
            if ("msg.sender ==" in source or "== msg.sender" in source):
                return True
            # HasRole pattern
            if "hasrole" in source:
                return True

        return False

    def _detect_or_pattern(self, slither_fn: Any) -> bool:
        """Detect require with OR (weak access control)."""
        # Implementation uses require expressions from slither
        # This is a placeholder - actual implementation needs slither IR
        return False
```

---

## Implementation Plan (7 Sub-Tasks)

### BR.3.1: Create detector base and interface (4h)

Files:
- `src/true_vkg/kg/detectors/__init__.py`
- `src/true_vkg/kg/detectors/base.py`

### BR.3.2: Extract access_control.py (6h)

Extract lines related to:
- `has_access_gate`
- `writes_privileged_state`
- `public_wrapper_without_access_gate`
- `tx_origin_in_require`
- `access_control_uses_or`

### BR.3.3: Extract reentrancy.py (5h)

Extract lines related to:
- `state_write_after_external_call`
- `has_reentrancy_guard`
- CEI pattern detection

### BR.3.4: Extract oracle.py (4h)

Extract lines related to:
- `reads_oracle_price`
- `has_staleness_check`
- `has_sequencer_uptime_check`

### BR.3.5: Extract token.py (5h)

Extract lines related to:
- `uses_erc20_transfer`
- `uses_safe_erc20`
- `token_return_guarded`
- `approves_infinite_amount`

### BR.3.6: Extract loop.py (4h)

Extract lines related to:
- `has_loops`
- `has_unbounded_loop`
- `external_calls_in_loop`
- `loop_bound_sources`

### BR.3.7: Extract remaining detectors (12h)

- `mev.py` - swap_like, slippage, deadline
- `proxy.py` - is_proxy_like, proxy_type
- `callback.py` - callback_chain_surface
- `crypto.py` - ecrecover, signature validation
- `external_call.py` - call target validation

---

## Validation Strategy

After each sub-task:

```bash
# Run fingerprint test
uv run pytest tests/test_fingerprint.py -v

# Run specific lens tests
uv run pytest tests/test_authority_lens.py -v  # For access_control.py
uv run pytest tests/test_reentrancy_lens.py -v  # For reentrancy.py

# Compare full graph output
uv run alphaswarm build-kg tests/contracts/BasicVault.sol --out /tmp/after-detector

# Verify identical
diff <(jq -S . /tmp/golden-baseline/graph.json) <(jq -S . /tmp/after-detector/graph.json)
```

---

## Files to Create

| File | Lines (Est.) | Purpose |
|------|--------------|---------|
| `detectors/__init__.py` | 100 | Registry, exports |
| `detectors/base.py` | 150 | Base class, interface |
| `detectors/access_control.py` | 200 | Access control signals |
| `detectors/reentrancy.py` | 150 | Reentrancy signals |
| `detectors/oracle.py` | 150 | Oracle signals |
| `detectors/token.py` | 200 | Token signals |
| `detectors/loop.py` | 150 | Loop signals |
| `detectors/mev.py` | 150 | MEV signals |
| `detectors/proxy.py` | 150 | Proxy signals |
| `detectors/callback.py` | 100 | Callback signals |
| `detectors/crypto.py` | 150 | Crypto signals |
| `detectors/external_call.py` | 150 | External call signals |

**Total new lines:** ~1700 (replacing ~1000 lines in builder.py)

---

## Files to Modify

| File | Change |
|------|--------|
| `src/true_vkg/kg/builder.py` | MODIFY - Import and use detectors |
| `tests/test_detectors.py` | CREATE - Unit tests for each detector |

---

## Acceptance Criteria

- [ ] All 11 detector modules exist
- [ ] Each detector has dedicated unit tests
- [ ] Builder.py imports and orchestrates detectors
- [ ] Graph fingerprint identical to baseline
- [ ] All existing tests pass
- [ ] Each detector can be tested independently

---

## Rollback Procedure

```bash
# Remove detector directory
rm -rf src/true_vkg/kg/detectors/

# Revert builder changes
git checkout HEAD -- src/true_vkg/kg/builder.py

# Verify
uv run pytest tests/ -v
```

---

## Key Insight: Behavior Preservation

The goal is NOT to improve detection. The goal is to move code without changing behavior. Every property value must be IDENTICAL before and after.

If any property changes, STOP and investigate. The refactor must be invisible to pattern matching.

---

*Task BR.3 | Version 1.0 | 2026-01-07*
