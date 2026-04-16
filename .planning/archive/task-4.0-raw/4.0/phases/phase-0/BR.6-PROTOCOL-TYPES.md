# BR.6: Protocol Types for Slither Objects

**Status:** TODO
**Priority:** SHOULD
**Estimated Hours:** 6-10h
**Depends On:** None (can start immediately, parallel with BR.1, BR.2)
**Unlocks:** BR.3

---

## Objective

Eliminate `Any` type annotations for Slither objects. Currently builder.py has 116 uses of `Any`, primarily for Slither's undocumented types. This task creates Protocol types that document expected attributes.

---

## Current Problem

```python
# builder.py has 116 `Any` annotations like this:
def _add_contract(self, graph: KnowledgeGraph, contract: Any) -> Node:
    ...

def _source_location(self, entity: Any) -> tuple[str, int, int]:
    ...

def _classify_state_write_targets(self, state_vars: list[Any]) -> dict[str, list[str]]:
    ...
```

Problems:
1. **No static analysis** - Type checker can't catch attribute errors
2. **No documentation** - Unclear what attributes are expected
3. **Refactoring risk** - Typos in attribute access go unnoticed

---

## Target State

Create `src/true_vkg/kg/protocols.py`:

```python
"""Protocol types for Slither objects.

These protocols define the expected interface of Slither objects used by VKG.
They don't enforce types at runtime, but enable static analysis and serve
as documentation.

Note: These protocols are based on Slither v0.10.x. If Slither changes its
API, these protocols must be updated.
"""

from __future__ import annotations

from typing import Protocol, List, Optional, Any, Sequence, runtime_checkable


# =============================================================================
# BASIC TYPES
# =============================================================================

@runtime_checkable
class SourceMappingLike(Protocol):
    """Protocol for objects with source mapping."""

    @property
    def source_mapping(self) -> Optional["SourceMappingLike"]:
        """Source mapping with file and line info."""
        ...

    @property
    def filename(self) -> "FilenameLike":
        """File information."""
        ...

    @property
    def lines(self) -> List[int]:
        """Line numbers covered."""
        ...


class FilenameLike(Protocol):
    """Protocol for Slither filename objects."""

    @property
    def absolute(self) -> str:
        """Absolute file path."""
        ...

    @property
    def relative(self) -> str:
        """Relative file path."""
        ...


# =============================================================================
# VARIABLE TYPES
# =============================================================================

@runtime_checkable
class VariableLike(Protocol):
    """Protocol for Slither variable objects (local and state)."""

    @property
    def name(self) -> str:
        """Variable name."""
        ...

    @property
    def type(self) -> "TypeLike":
        """Variable type."""
        ...


@runtime_checkable
class StateVariableLike(VariableLike):
    """Protocol for Slither state variable objects."""

    @property
    def visibility(self) -> str:
        """Visibility: public, private, internal."""
        ...

    @property
    def is_constant(self) -> bool:
        """Whether variable is constant."""
        ...

    @property
    def is_immutable(self) -> bool:
        """Whether variable is immutable."""
        ...

    @property
    def expression(self) -> Optional["ExpressionLike"]:
        """Initial value expression if any."""
        ...


@runtime_checkable
class ParameterLike(VariableLike):
    """Protocol for Slither function parameter objects."""
    pass


class TypeLike(Protocol):
    """Protocol for Slither type objects."""

    def __str__(self) -> str:
        """String representation of type."""
        ...


# =============================================================================
# MODIFIER TYPES
# =============================================================================

@runtime_checkable
class ModifierLike(Protocol):
    """Protocol for Slither modifier objects."""

    @property
    def name(self) -> str:
        """Modifier name."""
        ...

    @property
    def parameters(self) -> List[ParameterLike]:
        """Modifier parameters."""
        ...


# =============================================================================
# CALL TYPES
# =============================================================================

class CallLike(Protocol):
    """Protocol for Slither call objects."""

    @property
    def name(self) -> str:
        """Called function name."""
        ...


class HighLevelCallLike(Protocol):
    """Protocol for high-level calls (contract.function())."""

    # High level calls are tuples: (contract, function)
    def __getitem__(self, index: int) -> Any:
        ...


class LowLevelCallLike(Protocol):
    """Protocol for low-level calls (call, delegatecall, etc.)."""

    @property
    def name(self) -> str:
        """Call type: call, delegatecall, staticcall."""
        ...

    @property
    def function_name(self) -> Optional[str]:
        """Function name if available."""
        ...


# =============================================================================
# FUNCTION TYPES
# =============================================================================

@runtime_checkable
class FunctionLike(Protocol):
    """Protocol for Slither function objects.

    This is the primary interface used throughout VKG. All attributes accessed
    from Slither functions should be listed here.
    """

    @property
    def name(self) -> str:
        """Function name."""
        ...

    @property
    def visibility(self) -> str:
        """Visibility: public, external, internal, private."""
        ...

    @property
    def is_constructor(self) -> bool:
        """Whether function is constructor."""
        ...

    @property
    def is_fallback(self) -> bool:
        """Whether function is fallback."""
        ...

    @property
    def is_receive(self) -> bool:
        """Whether function is receive."""
        ...

    @property
    def payable(self) -> bool:
        """Whether function is payable."""
        ...

    @property
    def view(self) -> bool:
        """Whether function is view."""
        ...

    @property
    def pure(self) -> bool:
        """Whether function is pure."""
        ...

    @property
    def parameters(self) -> List[ParameterLike]:
        """Function parameters."""
        ...

    @property
    def returns(self) -> List[VariableLike]:
        """Return variables."""
        ...

    @property
    def modifiers(self) -> List[ModifierLike]:
        """Applied modifiers."""
        ...

    @property
    def state_variables_read(self) -> List[StateVariableLike]:
        """State variables read by function."""
        ...

    @property
    def state_variables_written(self) -> List[StateVariableLike]:
        """State variables written by function."""
        ...

    @property
    def variables_read(self) -> List[VariableLike]:
        """All variables read (including locals)."""
        ...

    @property
    def variables_written(self) -> List[VariableLike]:
        """All variables written (including locals)."""
        ...

    @property
    def external_calls_as_expressions(self) -> List["ExpressionLike"]:
        """External call expressions."""
        ...

    @property
    def high_level_calls(self) -> List[HighLevelCallLike]:
        """High-level external calls."""
        ...

    @property
    def low_level_calls(self) -> List[LowLevelCallLike]:
        """Low-level calls (call, delegatecall)."""
        ...

    @property
    def internal_calls(self) -> List["FunctionLike"]:
        """Internal function calls."""
        ...

    @property
    def solidity_calls(self) -> List[Any]:
        """Solidity built-in calls."""
        ...

    @property
    def nodes(self) -> List["CFGNodeLike"]:
        """Control flow graph nodes."""
        ...

    @property
    def source_mapping(self) -> Optional[SourceMappingLike]:
        """Source location mapping."""
        ...


# =============================================================================
# CFG TYPES
# =============================================================================

class CFGNodeLike(Protocol):
    """Protocol for Slither CFG node objects."""

    @property
    def type(self) -> "NodeTypeLike":
        """Node type (ENTRY, EXIT, IF, etc.)."""
        ...

    @property
    def expression(self) -> Optional["ExpressionLike"]:
        """Expression at this node."""
        ...

    @property
    def sons(self) -> List["CFGNodeLike"]:
        """Child nodes in CFG."""
        ...

    @property
    def fathers(self) -> List["CFGNodeLike"]:
        """Parent nodes in CFG."""
        ...

    @property
    def internal_calls(self) -> List["FunctionLike"]:
        """Internal calls from this node."""
        ...

    @property
    def external_calls_as_expressions(self) -> List["ExpressionLike"]:
        """External call expressions from this node."""
        ...


class NodeTypeLike(Protocol):
    """Protocol for Slither node type enum."""

    @property
    def name(self) -> str:
        """Type name: ENTRY, EXIT, IF, EXPRESSION, etc."""
        ...


# =============================================================================
# CONTRACT TYPES
# =============================================================================

@runtime_checkable
class ContractLike(Protocol):
    """Protocol for Slither contract objects."""

    @property
    def name(self) -> str:
        """Contract name."""
        ...

    @property
    def is_interface(self) -> bool:
        """Whether contract is an interface."""
        ...

    @property
    def is_library(self) -> bool:
        """Whether contract is a library."""
        ...

    @property
    def functions(self) -> List[FunctionLike]:
        """All functions (including inherited)."""
        ...

    @property
    def functions_declared(self) -> List[FunctionLike]:
        """Functions declared in this contract."""
        ...

    @property
    def state_variables(self) -> List[StateVariableLike]:
        """State variables."""
        ...

    @property
    def inheritance(self) -> List["ContractLike"]:
        """Inherited contracts."""
        ...

    @property
    def modifiers(self) -> List[ModifierLike]:
        """Modifiers declared in this contract."""
        ...

    @property
    def events(self) -> List["EventLike"]:
        """Events declared in this contract."""
        ...

    @property
    def source_mapping(self) -> Optional[SourceMappingLike]:
        """Source location mapping."""
        ...


# =============================================================================
# EVENT TYPES
# =============================================================================

class EventLike(Protocol):
    """Protocol for Slither event objects."""

    @property
    def name(self) -> str:
        """Event name."""
        ...

    @property
    def parameters(self) -> List[ParameterLike]:
        """Event parameters."""
        ...


# =============================================================================
# EXPRESSION TYPES
# =============================================================================

class ExpressionLike(Protocol):
    """Protocol for Slither expression objects."""

    def __str__(self) -> str:
        """String representation."""
        ...


# =============================================================================
# TYPE ALIASES (for convenience)
# =============================================================================

# These can be used directly in type hints
Contract = ContractLike
Function = FunctionLike
StateVariable = StateVariableLike
Variable = VariableLike
Parameter = ParameterLike
Modifier = ModifierLike
CFGNode = CFGNodeLike
```

---

## Implementation Steps

### Step 1: Create protocols.py (2h)

Create the file with all Protocol definitions based on builder.py usage.

### Step 2: Identify all `Any` usages (1h)

```bash
grep -n ": Any" src/true_vkg/kg/builder.py | head -50
grep -n "-> Any" src/true_vkg/kg/builder.py
grep -n "list\[Any\]" src/true_vkg/kg/builder.py
```

### Step 3: Update builder.py type hints (3h)

Replace `Any` with appropriate Protocol types:

```python
# Before
def _add_contract(self, graph: KnowledgeGraph, contract: Any) -> Node:

# After
from true_vkg.kg.protocols import ContractLike
def _add_contract(self, graph: KnowledgeGraph, contract: ContractLike) -> Node:
```

### Step 4: Run type checker (2h)

```bash
# Install pyright if needed
uv add --dev pyright

# Run type check on builder.py
uv run pyright src/true_vkg/kg/builder.py --outputjson > /tmp/type-errors.json

# Count errors
cat /tmp/type-errors.json | jq '.generalDiagnostics | length'
```

### Step 5: Fix type errors (2h)

Address any type errors revealed by the checker.

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/true_vkg/kg/protocols.py` | CREATE |
| `src/true_vkg/kg/__init__.py` | MODIFY - Export protocols |
| `src/true_vkg/kg/builder.py` | MODIFY - Use protocol types |
| `pyproject.toml` | MODIFY - Add pyright config |

---

## pyproject.toml Addition

```toml
[tool.pyright]
include = ["src/true_vkg"]
exclude = ["**/__pycache__"]
reportMissingImports = true
reportMissingTypeStubs = false
pythonVersion = "3.10"
pythonPlatform = "All"
typeCheckingMode = "basic"
```

---

## Validation Commands

```bash
# Run type checker
uv run pyright src/true_vkg/kg/builder.py

# Verify no Any types for Slither (after completion)
grep -c ": Any\|list\[Any\]" src/true_vkg/kg/builder.py
# Target: 0 (or minimal for truly unknown types)

# Verify graph unchanged
uv run pytest tests/test_fingerprint.py -v

# Full test suite
uv run pytest tests/ -v
```

---

## Acceptance Criteria

- [ ] `src/true_vkg/kg/protocols.py` exists with all Protocol types
- [ ] No `Any` types for Slither objects in builder.py
- [ ] Type checker (pyright) passes on builder.py
- [ ] All Slither attributes documented via Protocol
- [ ] Graph fingerprint identical to baseline
- [ ] All tests pass

---

## Rollback Procedure

```bash
# Remove protocols file
rm src/true_vkg/kg/protocols.py

# Revert builder changes
git checkout HEAD -- src/true_vkg/kg/builder.py

# Verify
uv run pytest tests/ -v
```

---

## Notes on Protocol Design

1. **@runtime_checkable** - Added to key protocols for isinstance() checks
2. **Protocols are structural** - Don't require explicit inheritance
3. **Properties not attributes** - Protocols use @property for attributes
4. **Optional nesting** - Some protocols reference others (self-referential)

---

*Task BR.6 | Version 1.0 | 2026-01-07*
